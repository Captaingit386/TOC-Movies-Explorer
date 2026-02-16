# TOC-Movies-Explorer

A full-stack **Theory of Computation (TOC)** project that builds a searchable movie dataset by crawling **Wikipedia film pages** and extracting structured information using **Python Regular Expressions (`re`)**. The extracted dataset is served through a **FastAPI** backend and displayed in a **Next.js** web application with a Netflix-inspired UI.

---

## Project Overview

This project demonstrates how theoretical concepts from TOC—especially **pattern matching and formal language recognition**—can be applied to a real-world data pipeline:

1. **Web crawler** collects Wikipedia film pages.
2. **Regex-based extractor (`import re`)** parses relevant fields from the HTML/infobox.
3. **Dataset generation** produces a structured JSON dataset (100+ instances).
4. **Web application** provides browsing, search, and pagination for users.

---

## Key Features

### ✅ Data Collection (Crawler)
- Crawls Wikipedia film pages starting from a seed URL.
- Collects at least **100+ movie instances** (current dataset: **120+**).
- Avoids non-film pages and irrelevant links.

### ✅ Regex Extraction (Most Important Requirement)
All core fields are extracted using **Python regex patterns** (`re.search`, `re.findall`, `re.sub`), including:
- **Title**
- **Director**
- **Release date** (normalized to ISO format when possible)
- **Runtime** (converted to minutes)
- **Country**
- **Language**
- **Budget**
- **Box office**

The extractor is designed to handle common Wikipedia variations and cleans HTML content before parsing.

### ✅ Search & Filtering
- Keyword search across multiple fields (title, director, country, language, budget, box office).
- Numeric search support for easier filtering of runtime and box office, e.g.:
  - `runtime>=100`
  - `runtime<90`
  - `boxoffice>100M`
  - `runtime>=120 boxoffice>100M`

### ✅ Web Application (Next.js)
- Netflix-inspired layout with modern UI styling.
- Browse results with pagination.
- Direct link to the project’s GitHub repository on the homepage.

---

## Tech Stack

**Backend**
- Python
- FastAPI (REST API)
- Requests (HTTP client)
- Regular Expressions (`import re`)

**Frontend**
- Next.js (React)
- TypeScript
- Custom CSS (Netflix-inspired theme)

**Data**
- JSON dataset (generated from Wikipedia infobox extraction)

---

## Dataset

- Minimum requirement: **100+ instances**
- Current dataset size: **120+ movies**
- Output format: `movies.json`

Each record includes structured fields such as:

- `title`, `director`, `release_date`, `running_time`, `country`, `language`, `budget`, `box_office`, `url`

---

## How to Run Locally

### 1) Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
