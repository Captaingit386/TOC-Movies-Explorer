# TOC Movies Explorer — Wikipedia Crawler + Regex Extraction + Web App

## Overview
TOC Movies Explorer is a full-stack web application that crawls Wikipedia movie pages and extracts structured movie information using **Python regular expressions (`import re`)**. The extracted dataset (100+ movies) is served through a **FastAPI** backend and displayed in a modern **Next.js (TypeScript)** frontend with powerful search filters, sorting, a data-quality dashboard, and CSV export.

## Key Features
- **Wikipedia crawler + scraper** to collect and extract movie data (100+ instances)
- **Regex-based extraction** (7+ non-trivial patterns) for structured fields
- **Advanced search syntax** (e.g., `title:b`, `director:"James Cameron"`, `runtime>=120`, `boxoffice>100M`)
- **Sorting + pagination** for browsing results
- **Dataset dashboard** with data-quality metrics and charts
- **Export filtered results to CSV** for Excel/Google Sheets
- **GitHub link visible on the homepage** (`frontend/app/page.tsx`)

## Tech Stack
- **Backend:** Python + FastAPI + `re` (regex)
- **Frontend:** Next.js (React) + TypeScript
- **Data:** `backend/movies.json`

---

## Run Locally

### Backend (Terminal 1)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: regenerate dataset (use your script flags)
python scraper.py --help

uvicorn main:app --reload --host 0.0.0.0 --port 8000
