import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import LAD_LOOKUP_PATH, POSTCODE_DATA_DIR
from app.google_places import fetch_pub_records_from_google
from app.ingestion import load_postcode_inventory
from app.storage import DeltaStore
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Beer Guy Pub MCP")
store = DeltaStore()


def sanitize_table_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def ensure_seed_data() -> None:
    if "postcode_inventory" in store.list_tables():
        return
    postcode_table = load_postcode_inventory(POSTCODE_DATA_DIR, LAD_LOOKUP_PATH)
    store.save_arrow_table("postcode_inventory", postcode_table)


@mcp.tool(description="List all available UK postcode districts and their names from the postcode inventory.")
def list_districts() -> List[Dict[str, Any]]:
    ensure_seed_data()
    return store.query_table(
        "postcode_inventory",
        "SELECT DISTINCT district_post_code, district_name FROM source ORDER BY district_post_code LIMIT 200",
    )


@mcp.tool(description="List the Delta tables currently available in the Beer Guy store.")
def list_tables() -> List[str]:
    return store.list_tables()


@mcp.tool(description="Generate and store pub records for a given district postcode and return the created table info.")
def fetch_and_save_pubs(district_post_code: str, limit: int = 5) -> Dict[str, Any]:
    ensure_seed_data()
    district_summary = store.query_table(
        "postcode_inventory",
        f"SELECT DISTINCT district_post_code, district_name FROM source WHERE district_post_code = '{district_post_code.upper()}' LIMIT 1",
    )
    if not district_summary:
        raise ValueError(f"District {district_post_code} was not found")

    district = district_summary[0]
    postcode_rows = store.query_table(
        "postcode_inventory",
        f"SELECT lat, long FROM source WHERE district_post_code = '{district_post_code.upper()}' LIMIT 1",
    )
    if postcode_rows:
        first_postcode = postcode_rows[0]
        latitude = float(first_postcode.get("lat", 0.0) or 0.0)
        longitude = float(first_postcode.get("long", 0.0) or 0.0)
    else:
        latitude = 0.0
        longitude = 0.0

    table_name = f"pubs_{sanitize_table_name(district['district_post_code'])}"
    records = fetch_pub_records_from_google(
        district["district_post_code"],
        district["district_name"],
        latitude,
        longitude,
        limit,
    )
    store.save_records(table_name, records, mode="overwrite")
    store.save_records("pubs_all", records, mode="overwrite")
    return {"status": "saved", "table": table_name, "count": len(records)}


@mcp.tool(description="Return the schema definition for a Delta-backed table in the Beer Guy store.")
def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    return store.get_schema(table_name)


@mcp.tool(description="Read rows from a Delta-backed table, optionally using a DuckDB SQL query.")
def read_table(table_name: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    if query:
        return store.query_table(table_name, query)
    return store.query_table(table_name, "SELECT * FROM source")


if __name__ == "__main__":
    mcp.run(transport="stdio")
