# Restaurant Menu Scraper

A standalone FastAPI service. Give it a restaurant's website URL, and it will:

1. Fetch the homepage and look for a menu — following links whose text/href
   mentions "menu", "food menu", "wine list", etc., and falling back to common
   paths like `/menu`, `/our-menu`, `/menu.pdf`.
2. If the menu is a PDF (linked or the URL itself), extract its text with
   `pdfplumber`. If it's an HTML page, strip nav/scripts/styles and pull the
   visible text.
3. Parse the raw menu text into structured items (`item`, `item_type`,
   `cuisine`, `price`, `currency`, `section`, `description`). If
   `ANTHROPIC_API_KEY` is set, this uses Claude for higher-quality extraction;
   otherwise it falls back to a regex/keyword heuristic parser.
4. Save the rows to a Delta table (`menu_items`) alongside the rest of this
   repo's data lake.

## Setup

```
cd scraper
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # optionally set ANTHROPIC_API_KEY for LLM parsing
```

## Run

```
uvicorn app.main:app --reload --port 8001
```

## API

- `POST /menu/extract` — body `{"url": "https://example-restaurant.com"}`.
  Locates the menu, parses items, saves them, and returns them.
- `GET /menu/items?restaurant_url=...` — read back saved rows (all rows if
  `restaurant_url` is omitted).
- `GET /tables/{table_name}` / `GET /tables/{table_name}/schema` — generic
  Delta table read/schema, for debugging.
- `DELETE /tables/{table_name}` — clear all rows from a table.
- `GET /health`

## Tests

```
pytest scraper/tests
```

## Notes / limitations

- The heuristic parser assumes prices are at the end of a line (e.g.
  `Bruschetta £5.50`) and infers cuisine from keyword frequency across the
  page — it won't be perfect on every site. Setting `ANTHROPIC_API_KEY`
  gives much more robust extraction for irregular menu layouts.
- Only the first `SCRAPER_MAX_CANDIDATES` menu-like links found on the
  homepage are fetched, and menu text sent to the LLM is capped at 20k
  characters, to bound cost/latency per request.
