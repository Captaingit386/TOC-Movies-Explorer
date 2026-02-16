from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import re
from typing import Any, Dict, List, Tuple, Optional

app = FastAPI(title="TOC Movies Explorer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOVIES_PATH = os.path.join(os.path.dirname(__file__), "movies.json")


def load_movies() -> List[Dict[str, Any]]:
    if not os.path.exists(MOVIES_PATH):
        return []
    with open(MOVIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


MOVIES = load_movies()


def parse_runtime_minutes(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().lower()
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def parse_money_to_usd(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None

    s = s.replace(",", "")
    s = s.replace("us$", "$")

    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)

    m = re.search(r"(\d+(\.\d+)?)\s*(billion|bn|million|m)?", s)
    if not m:
        return None

    num = float(m.group(1))
    unit = (m.group(3) or "").lower()

    if unit in ("billion", "bn"):
        return num * 1_000_000_000
    if unit in ("million", "m"):
        return num * 1_000_000
    return num


def compare(op: str, left: float, right: float) -> bool:
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    return left == right


def extract_filters(q: str) -> Tuple[Dict[str, Tuple[str, float]], str]:
    if not q:
        return {}, ""

    text = q.strip()
    filters: Dict[str, Tuple[str, float]] = {}

    rt = re.search(
        r"\bruntime\s*(>=|<=|>|<|=)\s*(\d{1,3})\b", text, flags=re.I)
    if rt:
        filters["runtime"] = (rt.group(1), float(int(rt.group(2))))
        text = re.sub(
            r"\bruntime\s*(>=|<=|>|<|=)\s*\d{1,3}\b", " ", text, flags=re.I)

    bo = re.search(
        r"\bboxoffice\s*(>=|<=|>|<|=)\s*([\d\.]+)\s*(billion|bn|million|m)?\b",
        text,
        flags=re.I,
    )
    if bo:
        op = bo.group(1)
        num = float(bo.group(2))
        unit = (bo.group(3) or "").lower()
        if unit in ("billion", "bn"):
            money = num * 1_000_000_000
        elif unit in ("million", "m"):
            money = num * 1_000_000
        else:
            money = num
        filters["box_office"] = (op, float(money))
        text = re.sub(
            r"\bboxoffice\s*(>=|<=|>|<|=)\s*[\d\.]+\s*(billion|bn|million|m)?\b",
            " ",
            text,
            flags=re.I,
        )

    text = re.sub(r"\s+", " ", text).strip()
    return filters, text


def matches_text(movie: Dict[str, Any], qq: str) -> bool:
    if not qq:
        return True
    qq = qq.lower().strip()
    hay = " ".join(
        [
            str(movie.get("title", "")),
            str(movie.get("director", "")),
            str(movie.get("release_date", "")),
            str(movie.get("running_time", "")),
            str(movie.get("country", "")),
            str(movie.get("language", "")),
            str(movie.get("budget", "")),
            str(movie.get("box_office", "")),
        ]
    ).lower()
    return qq in hay


def matches_filters(movie: Dict[str, Any], filters: Dict[str, Tuple[str, float]]) -> bool:
    if "runtime" in filters:
        op, val = filters["runtime"]
        rt = parse_runtime_minutes(movie.get("running_time"))
        if rt is None:
            return False
        if not compare(op, float(rt), float(val)):
            return False

    if "box_office" in filters:
        op, val = filters["box_office"]
        bo = parse_money_to_usd(movie.get("box_office"))
        if bo is None:
            return False
        if not compare(op, float(bo), float(val)):
            return False

    return True


@app.get("/health")
def health():
    return {"ok": True, "total_movies": len(MOVIES)}


@app.get("/movies")
def list_movies(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    q: str = Query("", max_length=200),
):
    filters, text_q = extract_filters(q or "")

    filtered = [
        m for m in MOVIES
        if matches_filters(m, filters) and matches_text(m, text_q)
    ]

    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    items = filtered[start:end]

    return {"total": total, "items": items, "page": page, "limit": limit}
