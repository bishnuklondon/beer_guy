from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data"
DELTA_DIR = DATA_DIR / "delta_tables"
POSTCODE_DATA_DIR = DATA_DIR / "POST_CODE_INVENTORY_ONSPD_FEB_2026" / "Data" / "multi_csv"
LAD_LOOKUP_PATH = DATA_DIR / "POST_CODE_INVENTORY_ONSPD_FEB_2026" / "Data" / "LAD Local Authority District names and codes UK as at 04_25.csv"
COUNTY_LOOKUP_PATH = DATA_DIR / "POST_CODE_INVENTORY_ONSPD_FEB_2026" / "Data" / "CTY County names and codes UK as at 05_25.csv"
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_API_KEY", "")
