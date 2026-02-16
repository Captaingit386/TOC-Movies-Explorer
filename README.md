# TOC Project — Movies Crawler + Regex Scraper + Web App

## Topic
Movies (Wikipedia)

## What this project does
1. **Crawler** collects 100+ movie page URLs from a Wikipedia portal page (category/list), following pagination if needed.
2. **Scraper** visits each movie page and uses **Python regex (`import re`)** to extract movie info.
3. Saves results to `backend/movies.json` (100 movies by default).
4. **Web app** displays the information (Next.js frontend + FastAPI backend).

## Requirements satisfied
- 100+ instances (default is 100 movies)
- Uses `import re` and includes **7 non-trivial regex patterns** (show these in your presentation)
- Displays data on a web application
- Homepage includes a visible GitHub link (edit `frontend/app/page.jsx`)

---

## Run locally

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Crawl + scrape (creates movies.json)
python scraper.py --start_url "https://en.wikipedia.org/wiki/Category:2020s_action_films" --target 100 --sleep 1.0 --out movies.json

# Start API
uvicorn main:app --reload --port 8000
```

Open: http://127.0.0.1:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:3000

---

## Configure frontend API URL (optional)
Create `frontend/.env.local`:
```txt
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```
Restart `npm run dev`.

---

## Notes for the 10-minute YouTube demo
- Show the crawler + scraper running and saving 100 movies.
- Show the regex patterns at the top of `backend/scraper.py`.
- Show backend `/docs` and test `/movies`.
- Show frontend homepage with GitHub link and the movie list.
- Click into a movie detail page.

---

## Deployment suggestion (simple)
- Backend: Render (FastAPI/uvicorn)
- Frontend: Vercel (Next.js)

Make sure the deployed frontend points to the deployed backend URL via `NEXT_PUBLIC_API_BASE`.
