# backend/merge_movies.py
import json
import os
import re
import random
from typing import Any, Dict, List
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUTS = {
    "United States": "movies_us.json",
    "United Kingdom": "movies_uk.json",
    "India": "movies_india.json",
    "Japan": "movies_japan.json",
    "South Korea": "movies_korea.json",
}

TARGET = {
    "United States": 45,
    "United Kingdom": 15,
    "India": 30,
    "Japan": 30,
    "South Korea": 30,
}

OUT_FILE = "movies.json"
SEED = 42


def norm(s: Any) -> str:
    if s is None:
        return ""
    if isinstance(s, list):
        s = " ".join([str(x) for x in s if x is not None])
    return re.sub(r"\s+", " ", str(s).strip()).lower()


def stable_id(m: Dict[str, Any]) -> str:
    url = m.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    title = m.get("title")
    if isinstance(title, str) and title.strip():
        return norm(title)
    return json.dumps(m, sort_keys=True, ensure_ascii=False)


def load_list(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("movies"), list):
        data = data["movies"]
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def quality_ok(m: Dict[str, Any]) -> bool:
    # Good-quality rule: must have infobox-extracted useful data
    score = 0
    if m.get("director"):
        score += 1
    if m.get("release_date"):
        score += 1
    if m.get("running_time") is not None:
        score += 1
    return score >= 2  # at least 2 of 3


def dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for m in items:
        k = stable_id(m)
        if k in seen:
            continue
        seen.add(k)
        out.append(m)
    return out


def pick(items: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    items = [m for m in items if quality_ok(m)]
    items = dedup(items)
    random.shuffle(items)
    return items[:n]


def main() -> None:
    random.seed(SEED)

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for country, fn in INPUTS.items():
        path = os.path.join(BASE_DIR, fn)
        if not os.path.exists(path):
            buckets[country] = []
            continue
        data = load_list(path)
        # Force clean country label
        for m in data:
            m["country"] = country
        buckets[country] = data

    selected: List[Dict[str, Any]] = []
    shortages = []

    for country, need in TARGET.items():
        got = pick(buckets.get(country, []), need)
        if len(got) < need:
            shortages.append(f"{country}: {len(got)}/{need}")
        selected.extend(got)

    selected = dedup(selected)

    out_path = os.path.join(BASE_DIR, OUT_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    cnt = Counter([m.get("country")
                  for m in selected if isinstance(m.get("country"), str)])
    print(f"Wrote {OUT_FILE}: {len(selected)} movies")
    print("Countries:", cnt)

    # Quality summary
    total = len(selected)
    if total:
        has_dir = sum(1 for m in selected if m.get("director"))
        has_rel = sum(1 for m in selected if m.get("release_date"))
        has_run = sum(1 for m in selected if m.get("running_time") is not None)
        print(
            f"Quality: director {has_dir}/{total}, release {has_rel}/{total}, runtime {has_run}/{total}")

    if shortages:
        print("\nWARNING: Not enough movies after quality filter:")
        for s in shortages:
            print("-", s)
        print("Fix: rerun scraper for the missing country with higher --crawl.")


if __name__ == "__main__":
    main()
