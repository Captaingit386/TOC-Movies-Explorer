#!/usr/bin/env python3
import argparse
import json
import re
import time
import html as ihtml
from typing import Optional, List
from collections import deque
from urllib.parse import urljoin, urlparse, unquote

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) toc-movies-crawler/2.1"
}
WIKI_HOST = "en.wikipedia.org"


# ----------------------------
# Cleaning helpers
# ----------------------------
def clean_text(s: str) -> str:
    if not s:
        return ""
    s = ihtml.unescape(s)

    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)

    s = re.sub(r"\[\s*[0-9]+\s*\]", "", s)
    s = re.sub(r"\[\s*[a-zA-Z]+\s*\]", "", s)
    s = re.sub(r"\[\s*note\s*\d+\s*\]", "", s, flags=re.I)

    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_country_name(x: str) -> str:
    x = re.sub(r"\s+", " ", (x or "").strip())
    mapping = {
        "USA": "United States",
        "U.S.": "United States",
        "United States of America": "United States",
        "UK": "United Kingdom",
        "U.K.": "United Kingdom",
        "Republic of Korea": "South Korea",
        "Korea, South": "South Korea",
        "South Korea": "South Korea",
    }
    return mapping.get(x, x)


def extract_list_from_td(td_html: str) -> List[str]:
    """
    Convert <br> separated / comma separated values into a list of clean strings.
    """
    if not td_html:
        return []

    x = ihtml.unescape(td_html)
    x = re.sub(r"<\s*br\s*/?\s*>", ", ", x, flags=re.I)

    x = clean_text(x)
    x = re.sub(r"\s*;\s*", ",", x)
    x = re.sub(r"\s*,\s*", ",", x).strip(" ,")
    if not x:
        return []

    parts = [p.strip() for p in x.split(",") if p.strip()]
    out = []
    for p in parts:
        if p not in out:
            out.append(p)
    return out


def parse_box_office_usd(text: str) -> Optional[float]:
    if not text:
        return None

    s = clean_text(text)
    if not s:
        return None

    s = s.replace("US$", "$").replace("USD", "$").replace("usd", "$")
    s = re.sub(r"\s+", " ", s).strip()
    low = s.lower()
    t = low.replace("–", "-")  # always define (fixes occasional NameError)

    def to_dollars(num_str: str, unit: str) -> float:
        num = float(num_str.replace(",", ""))
        u = (unit or "").lower()
        if u in ("billion", "bn"):
            return num * 1_000_000_000
        if u in ("million", "m"):
            return num * 1_000_000
        if u in ("thousand", "k"):
            return num * 1_000
        return num

    FX_TO_USD = {
        "INR": 1.0 / 83.0,
        "KRW": 1.0 / 1350.0,
        "JPY": 1.0 / 150.0,
        "GBP": 1.0 / 0.79,
    }

    # Prefer USD inside parentheses
    m = re.search(
        r"\((?:\$)\s*([\d.,]+)\s*(billion|bn|million|m|thousand|k)?\b", s, re.I)
    if m:
        return to_dollars(m.group(1), m.group(2) or "")

    # USD anywhere (supports ranges; take max)
    m = re.search(
        r"\$\s*([\d.,]+)\s*(?:-\s*([\d.,]+))?\s*(billion|bn|million|m|thousand|k)?\b", t, re.I)
    if m:
        a = float(m.group(1).replace(",", ""))
        b = float(m.group(2).replace(",", "")) if m.group(2) else None
        unit = (m.group(3) or "").lower()
        num = max(a, b) if b is not None else a
        return to_dollars(str(num), unit)

    # INR
    if ("₹" in s) or ("inr" in low) or ("rupee" in low) or re.search(r"\brs\.?\b", low):
        m = re.search(
            r"([\d.]+)\s*(?:-\s*([\d.]+))?\s*(crore|crores|lakh|lakhs|billion|bn|million|m|thousand|k)\b", t, re.I)
        if not m:
            return None
        a = float(m.group(1))
        b = float(m.group(2)) if m.group(2) else None
        unit = (m.group(3) or "").lower()
        num = max(a, b) if b is not None else a
        if unit in ("crore", "crores"):
            inr = num * 10_000_000
        elif unit in ("lakh", "lakhs"):
            inr = num * 100_000
        elif unit in ("billion", "bn"):
            inr = num * 1_000_000_000
        elif unit in ("million", "m"):
            inr = num * 1_000_000
        elif unit in ("thousand", "k"):
            inr = num * 1_000
        else:
            inr = num
        return inr * FX_TO_USD["INR"]

    # KRW
    if ("₩" in s) or ("won" in low):
        m = re.search(
            r"([\d.,]+)\s*(billion|bn|million|m|thousand|k)?\b", t, re.I)
        if not m:
            return None
        krw = to_dollars(m.group(1), m.group(2) or "")
        return krw * FX_TO_USD["KRW"]

    # JPY
    if ("¥" in s) or ("yen" in low):
        m = re.search(
            r"([\d.,]+)\s*(billion|bn|million|m|thousand|k)?\b", t, re.I)
        if not m:
            return None
        jpy = to_dollars(m.group(1), m.group(2) or "")
        return jpy * FX_TO_USD["JPY"]

    # GBP
    if ("£" in s) or ("pound" in low):
        m = re.search(
            r"([\d.,]+)\s*(billion|bn|million|m|thousand|k)?\b", t, re.I)
        if not m:
            return None
        gbp = to_dollars(m.group(1), m.group(2) or "")
        return gbp * FX_TO_USD["GBP"]

    return None


def extract_infobox_fields(page_html: str) -> dict:
    if not page_html:
        return {}

    m = re.search(
        r'(<table[^>]+class="infobox[^"]*"[^>]*>.*?</table>)', page_html, flags=re.S | re.I)
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
    if m:
        months = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        month = months[m.group(1)]
        day = int(m.group(2))
        year = int(m.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # D Month YYYY  (UK style) ✅ added
    m2 = re.search(
        r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+((19|20)\d{2})\b",
        td_html
    )
    if m2:
        months = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        day = int(m2.group(1))
        month = months[m2.group(2)]
        year = int(m2.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    return ""


def extract_runtime_minutes(td_html: str):
    if not td_html:
        return None
    t = clean_text(td_html).lower()

    m = re.search(r"\b(\d{1,3})\s*minute", t)
    if m:
        return int(m.group(1))

    h = re.search(r"\b(\d{1,2})\s*h", t)
    mm = re.search(r"\b(\d{1,2})\s*m\b", t)
    if h:
        total = int(h.group(1)) * 60 + (int(mm.group(1)) if mm else 0)
        return total

    n = re.search(r"\b(\d{1,3})\b", t)
    return int(n.group(1)) if n else None


def extract_movie(page_html: str, url: str) -> dict:
    fields = extract_infobox_fields(page_html)

    title = ""
    h1 = re.search(r'<h1[^>]*id="firstHeading"[^>]*>(.*?)</h1>',
                   page_html, flags=re.S | re.I)
    if h1:
        title = clean_text(h1.group(1))

    director = clean_text(fields.get("directed by", "")
                          or fields.get("director", "")) or None

    release_raw = fields.get("release date", "") or fields.get(
        "release dates", "") or fields.get("released", "")
    release_date = pick_release_iso(release_raw) or None

    runtime = extract_runtime_minutes(fields.get(
        "running time", "") or fields.get("runtime", ""))

    country_list = extract_list_from_td(fields.get(
        "country", "") or fields.get("countries", ""))
    country_list = [normalize_country_name(x) for x in country_list]

    language_list = extract_list_from_td(fields.get(
        "language", "") or fields.get("languages", ""))

    country_primary = country_list[0] if country_list else None
    language_primary = language_list[0] if language_list else None

    budget = clean_text(fields.get("budget", "")) or None
    box_office = clean_text(fields.get("box office", "")) or None
    box_office_usd = parse_box_office_usd(box_office or "")

    return {
        "title": title or unquote(url.split("/wiki/")[-1]).replace("_", " "),
        "url": url,
        "director": director,
        "release_date": release_date,
        "running_time": runtime,
        "country": country_primary,
        "language": language_primary,
        "budget": budget,
        "box_office": box_office,
        "box_office_usd": box_office_usd,
        "_country_list": country_list,
        "_language_list": language_list,
        "_has_infobox": bool(fields),
    }


# ----------------------------
# Purity rules
# ----------------------------
def is_pure_target(movie: dict, target_country: str) -> bool:
    target_country = normalize_country_name(target_country)
    clist = movie.get("_country_list") or []
    clist = [normalize_country_name(
        x) for x in clist if isinstance(x, str) and x.strip()]
    return len(clist) == 1 and clist[0] == target_country


# ----------------------------
# Crawler (with retry/backoff)
# ----------------------------
def fetch(url: str, max_tries: int = 4) -> str:
    last_err = None
    for i in range(max_tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code in (429, 503, 502, 500):
                raise RuntimeError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            time.sleep(0.3 * (2 ** i))
    raise last_err


def is_valid_wiki_url(u: str) -> bool:
    if not u:
        return False
    parsed = urlparse(u)
    if parsed.netloc and parsed.netloc != WIKI_HOST:
        return False
    if not parsed.path.startswith("/wiki/"):
        return False

    # Allow Category pages and List pages
    if ":" in parsed.path:
        return parsed.path.startswith("/wiki/Category:")

    return True


def normalize_wiki_url(base: str, href: str) -> str:
    u = urljoin(base, href)
    parsed = urlparse(u)
    return parsed._replace(fragment="").geturl()


def looks_like_film_page(url: str) -> bool:
    path = unquote(urlparse(url).path)
    low = path.lower()

    if low.startswith("/wiki/category:"):
        return False
    if "in_film" in low:
        return False
    if low.startswith("/wiki/list_of_"):
        return False

    # Common film patterns
    if re.search(r"\(film\)", path, flags=re.I):
        return True
    if re.search(r"\(\d{4}\s*film\)", path, flags=re.I):
        return True
    if re.search(r"\(\d{4}_film\)", path, flags=re.I):
        return True

    # Extra: some film pages end with "_(movie)" or "_(motion_picture)" occasionally
    if re.search(r"\((movie|motion_picture)\)", path, flags=re.I):
        return True

    return False


def crawl_urls(start_url: str, crawl_target: int, sleep_sec: float) -> list:
    seen_pages = set()
    seen_movie_urls = set()
    movie_urls = []
    q = deque([start_url])

    print(
        f"[phase] CRAWL: start from {start_url} (target movie pages={crawl_target})", flush=True)

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

                if len(movie_urls) % 25 == 0 or len(movie_urls) == 1:
                    print(
                        f"[crawl] found {len(movie_urls)}/{crawl_target} movie pages", flush=True)

                if len(movie_urls) >= crawl_target:
                    break

            # Explore deeper but limit explosion
            if full not in seen_pages and len(seen_pages) < crawl_target * 20:
                q.append(full)

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    print(
        f"[phase] CRAWL: done (movie pages={len(movie_urls)}, pages_visited={len(seen_pages)})", flush=True)
    return movie_urls


def build_dataset(start_url: str, target: int, crawl_target: int, sleep_sec: float, target_country: str) -> list:
    urls = crawl_urls(start_url, crawl_target, sleep_sec)
    movies = []

    print(
        f"[phase] EXTRACT: start (urls={len(urls)}, target_movies={target}, pure_country={target_country})", flush=True)

    attempted = 0
    skipped = 0

    for url in urls:
        if len(movies) >= target:
            break

        attempted += 1
        if attempted % 25 == 0 or attempted == 1:
            print(
                f"[extract] attempted {attempted}/{len(urls)} | saved {len(movies)}/{target} | skipped {skipped}", flush=True)

        try:
            page_html = fetch(url)
            m = extract_movie(page_html, url)

            if not m.get("_has_infobox"):
                skipped += 1
                continue
            if not (m.get("director") or m.get("release_date") or m.get("running_time") is not None):
                skipped += 1
                continue

            if not is_pure_target(m, target_country):
                skipped += 1
                continue

            m["country"] = normalize_country_name(target_country)

            m.pop("_has_infobox", None)
            m.pop("_country_list", None)
            m.pop("_language_list", None)

            movies.append(m)
            print(
                f"[extract] saved {len(movies)}/{target} (last: {m.get('title')})", flush=True)

        except Exception:
            skipped += 1
            continue

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    print(
        f"[phase] EXTRACT: done (saved={len(movies)}, attempted={attempted}, skipped={skipped})", flush=True)
    return movies


def quality_report(movies: list):
    total = len(movies) if movies else 0
    print("=== DATA QUALITY ===")
    if total == 0:
        print("No movies collected.")
        return

    def pct(x: int) -> float:
        return round(100.0 * x / total, 1)

    has_director = sum(1 for m in movies if m.get("director"))
    has_release = sum(1 for m in movies if m.get("release_date"))
    has_runtime = sum(1 for m in movies if m.get("running_time") is not None)
    has_box = sum(1 for m in movies if m.get("box_office"))
    has_box_usd = sum(1 for m in movies if m.get("box_office_usd") is not None)

    print(f"director       : {has_director}/{total} ({pct(has_director)}%)")
    print(f"release_date   : {has_release}/{total} ({pct(has_release)}%)")
    print(f"running_time   : {has_runtime}/{total} ({pct(has_runtime)}%)")
    print(f"box_office     : {has_box}/{total} ({pct(has_box)}%)")
    print(f"box_office_usd : {has_box_usd}/{total} ({pct(has_box_usd)}%)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True,
                        help="Wikipedia start URL (https://...)")
    parser.add_argument("--country", required=True,
                        help='Pure country label (e.g., "Japan")')
    parser.add_argument("--target", type=int, default=30)
    parser.add_argument("--crawl", type=int, default=2500)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    movies = build_dataset(args.start, args.target,
                           args.crawl, args.sleep, args.country)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)

    quality_report(movies)

    print("==== DONE ====")
    print(f"Saved: {len(movies)} movies")
    print(f"Output file: {args.out}")


if __name__ == "__main__":
    main()
