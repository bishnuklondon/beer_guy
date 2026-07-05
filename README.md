# Beer Guy starter workspace

This workspace now contains three starter projects:

- Backend: FastAPI service with postcode ingestion, Delta-backed tables, REST endpoints, and an MCP-style tool endpoint.
- Scraper: a simple website scraper that updates pub menu/offer data and stores beverage rows.
- UI: a React/Vite web app for exploring pubs by district and searching beverages.

## Quick start

### Prerequisite:

- Download the UK post code data from https://geoportal.statistics.gov.uk/datasets/6fff67d204fd4f339591ed667a6e3642/about
- Create a new folder called "data" in the root project directory 
- Extract the downloaded zip file into the data folder 

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Scraper

```bash
cd scraper
pip install -r requirements.txt
python scraper.py
```

### UI

```bash
cd ui
npm install
npm run dev
```

The UI expects the backend to be running on port 8000.
