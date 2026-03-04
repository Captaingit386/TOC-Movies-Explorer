# TOC Movies Explorer — Wikipedia Crawler + Regex Extraction + Web App

TOC Movies Explorer is a full-stack web application that crawls Wikipedia film pages and extracts structured movie information using **Python regular expressions (`import re`)**.  
The dataset is served by a **FastAPI** backend and displayed in a **Next.js (TypeScript)** frontend with live search, advanced filters, sorting, a data-quality dashboard, and CSV export.

---

## Dataset (Final)
This repo includes a ready-to-use dataset of **150 movies** (no scraping needed to run the app):

- **United States:** 45  
- **United Kingdom:** 15  
- **India:** 30  
- **Japan:** 30  
- **South Korea:** 30  

Source: Wikipedia pages (infobox fields + regex extraction).

---

## Key Features
- **Wikipedia crawler + scraper** (100+ instances requirement satisfied)
- **Regex-based extraction** (7+ non-trivial patterns) for fields such as:
  - title, director, release date, runtime, country, language, budget, box office
- **Live search** (type-to-filter results)
- **Advanced search syntax** (examples below)
- **Sorting + pagination**
- **Dataset dashboard** with data quality metrics + charts
- **Export results to CSV**
- **GitHub link visible on homepage**

---

## Search Syntax (Examples)
You can type plain text (defaults to title search) or use filters:

- `h`  
- `title:Hulk`
- `director:"James Cameron"`
- `country:"Japan"`
- `language:"English"`
- `release:2003`
- `runtime>=120`
- `boxoffice>100M`

Notes:
- Short keywords (1–2 characters) use prefix matching for fast “starts with”.
- Missing values are handled gracefully (displayed as `—` / `-`).

---

## Tech Stack
- **Backend:** Python + FastAPI + `re` (regex)
- **Frontend:** Next.js (React) + TypeScript
- **Dataset:** `backend/movies.json` (final 150 movies)

---

## Run Locally

### 1) Backend (Terminal 1)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run API (uses backend/movies.json by default)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend(Terminal 2)
```bash
cd frontend
npm install
npm run dev
```


