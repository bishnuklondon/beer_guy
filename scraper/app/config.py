import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

_delta_dir_override = os.getenv("SCRAPER_DELTA_DIR", "")
DELTA_DIR = Path(_delta_dir_override) if _delta_dir_override else DATA_DIR / "delta_tables"

REQUEST_TIMEOUT = int(os.getenv("SCRAPER_REQUEST_TIMEOUT", "20"))
MAX_CRAWL_CANDIDATES = int(os.getenv("SCRAPER_MAX_CANDIDATES", "5"))
USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

MENU_ITEMS_TABLE = "menu_items"
