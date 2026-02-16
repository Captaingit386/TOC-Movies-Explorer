#!/usr/bin/env python3
import argparse
import json
import re
import time
import html as ihtml
from collections import deque
from urllib.parse import urljoin, urlparse, unquote

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) toc-movies-crawler/1.0"
}
WIKI_HOST = "en.wikipedia.org"


# ----------------------------
# Cleaning helpers
# ----------------------------
def clean_text(s: str) -> str:
    if not s:
        return ""
    s = ihtml.unescape(s)  # convert &#91; etc -> [

    # remove script/style blocks
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S | re.I)

    # remove tags
    s = re.sub(r"<[^>]+>", " ", s)

    # remove wikipedia reference markers: [1], [ 1 ], [a], [ a ], [note 1]
    s = re.sub(r"\[\s*[0-9]+\s*\]", "", s)
    s = re.sub(r"\[\s*[a-zA-Z]+\s*\]", "", s)
    s = re.sub(r"\[\s*note\s*\d+\s*\]", "", s, flags=re.I)

    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_infobox_fields(page_html: str) -> dict:
    if not page_html:
        return {}

    m = re.search(
        r'(<table[^>]+class="infobox[^"]*"[^>]*>.*?</table>)',
        page_html,
        flags=re.S | re.I
    )
    if not m:
        return {}

    infobox = m.group(1)
    fields = {}

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", infobox, flags=re.S | re.I)
    for row in rows:
        th = re.search(r"<th[^>]*>(.*?)</th>", row, flags=re.S | re.I)
        td = re.search(r"<td[^>]*>(.*?)</td>", row, flags=re.S | re.I)
        if not th or not td:
            continue

        label = clean_text(th.group(1)).lower().strip(":")
        label = re.sub(r"\s+", " ", label)
        td_html = td.group(1).strip()
        if label:
            fields[label] = td_html

    return fields


def pick_release_iso(td_html: str) -> str:
    if not td_html:
        return ""

    td_html = ihtml.unescape(td_html)

    # ISO date
    iso = re.search(r"\b(19|20)\d{2}-\d{2}-\d{2}\b", td_html)
    if iso:
        return iso.group(0)

    # Month D, YYYY
    m = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+((19|20)\d{2})\b",
        td_html
    )
    if not m:
        return ""

    months = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    month = months[m.group(1)]
    day = int(m.group(2))
    year = int(m.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"


def extract_runtime_minutes(td_html: str):
    """
    Return runtime as integer minutes.
    Examples:
      '97 minutes' -> 97
      '1h 40m' -> 100 (best-effort)
    """
    if not td_html:
        return None
    t = clean_text(td_html).lower()

    # common: "xxx minutes"
    m = re.search(r"\b(\d{1,3})\s*minute", t)
    if m:
        return int(m.group(1))

    # hours/minutes format: "1 h 40 m"
    h = re.search(r"\b(\d{1,2})\s*h", t)
    mm = re.search(r"\b(\d{1,2})\s*m\b", t)
    if h:
        total = int(h.group(1)) * 60 + (int(mm.group(1)) if mm else 0)
        return total

    # fallback: first number
    n = re.search(r"\b(\d{1,3})\b", t)
    return int(n.group(1)) if n else None


def extract_movie(page_html: str, url: str) -> dict:
    fields = extract_infobox_fields(page_html)

    # Title from <h1>
    title = ""
    h1 = re.search(r'<h1[^>]*id="firstHeading"[^>]*>(.*?)</h1>',
                   page_html, flags=re.S | re.I)
    if h1:
        title = clean_text(h1.group(1))

    director = clean_text(fields.get("directed by", "")
                          or fields.get("director", "")) or None

    release_raw = (
        fields.get("release date", "")
        or fields.get("release dates", "")
        or fields.get("released", "")
    )
    release_date = pick_release_iso(release_raw) or None

    runtime = extract_runtime_minutes(fields.get(
        "running time", "") or fields.get("runtime", ""))

    country = clean_text(fields.get("country", "")) or None
    language = clean_text(fields.get("language", "")) or None

    budget = clean_text(fields.get("budget", "")) or None
    box_office = clean_text(fields.get("box office", "")) or None

    return {
        "title": title or unquote(url.split("/wiki/")[-1]).replace("_", " "),
        "url": url,
        "director": director,
        "release_date": release_date,
        "running_time": runtime,  # integer minutes
        "country": country,
        "language": language,
        "budget": budget,
        "box_office": box_office,
        "_has_infobox": bool(fields),
        "_raw_fields": list(fields.keys())[:10],
    }


# ----------------------------
# Crawler
# ----------------------------
def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def is_valid_wiki_url(u: str) -> bool:
    if not u:
        return False
    parsed = urlparse(u)
    if parsed.netloc and parsed.netloc != WIKI_HOST:
        return False
    if not parsed.path.startswith("/wiki/"):
        return False
    if ":" in parsed.path:  # Special: pages
        return False
    return True


def normalize_wiki_url(base: str, href: str) -> str:
    u = urljoin(base, href)
    parsed = urlparse(u)
    return parsed._replace(fragment="").geturl()


def looks_like_film_page(url: str) -> bool:
    path = unquote(urlparse(url).path)

    # Exclude obvious non-movie patterns
    if "in_film" in path.lower():
        return False
    if path.lower().startswith("/wiki/list_of_"):
        return False

    # Accept common movie-page patterns
    if re.search(r"\(film\)", path, flags=re.I):
        return True
    if re.search(r"\(\d{4}\s*film\)", path, flags=re.I):
        return True
    if re.search(r"\(\d{4}_film\)", path, flags=re.I):
        return True

    return False


def crawl_urls(start_url: str, crawl_target: int, sleep_sec: float) -> list:
    seen_pages = set()
    seen_movie_urls = set()
    movie_urls = []
    q = deque([start_url])

    while q and len(movie_urls) < crawl_target:
        url = q.popleft()
        if url in seen_pages:
            continue
        seen_pages.add(url)

        try:
            html = fetch(url)
        except Exception:
            continue

        hrefs = re.findall(r'href="([^"]+)"', html, flags=re.I)
        for href in hrefs:
            if href.startswith("#") or href.startswith("/w/"):
                continue
            full = normalize_wiki_url(url, href)
            if not is_valid_wiki_url(full):
                continue

            if looks_like_film_page(full) and full not in seen_movie_urls:
                seen_movie_urls.add(full)
                movie_urls.append(full)
                if len(movie_urls) >= crawl_target:
                    break

            if full not in seen_pages and len(seen_pages) < crawl_target * 5:
                q.append(full)

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    return movie_urls


def build_dataset(start_url: str, target: int, crawl_target: int, sleep_sec: float) -> list:
    urls = crawl_urls(start_url, crawl_target, sleep_sec)
    movies = []

    for url in urls:
        if len(movies) >= target:
            break

        try:
            page_html = fetch(url)
            m = extract_movie(page_html, url)

            # HARD FILTER: must have infobox and at least one real field
            if not m.get("_has_infobox"):
                continue
            if not (m.get("director") or m.get("release_date") or m.get("running_time")):
                continue

            # cleanup internal debug keys
            m.pop("_has_infobox", None)
            m.pop("_raw_fields", None)

            movies.append(m)

        except Exception:
            continue

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    return movies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True,
                        help="Wikipedia start URL (https://...)")
    parser.add_argument("--target", type=int, default=120)
    parser.add_argument("--crawl", type=int, default=800)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--out", default="movies.json")
    args = parser.parse_args()

    movies = build_dataset(args.start, args.target, args.crawl, args.sleep)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)

    print("==== DONE ====")
    print(f"Saved: {len(movies)} movies")
    print(f"Output file: {args.out}")


if __name__ == "__main__":
    main()
