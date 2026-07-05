import json
import re
from typing import Any, Dict, List, Optional

import pyarrow as pa
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import LAD_LOOKUP_PATH, POSTCODE_DATA_DIR
from .google_places import fetch_pub_records_from_google
from .ingestion import load_postcode_inventory
from .storage import DeltaStore

app = FastAPI(title="Beer Guy Pub Data API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DeltaStore()


class PubPayload(BaseModel):
    district_post_code: str
    limit: int


class CountyPubPayload(BaseModel):
    county_name: str
    limit: int


class MCPRequest(BaseModel):
    tool: str
    arguments: Optional[Dict[str, Any]] = None


def sanitize_table_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def ensure_seed_data() -> None:
    if "postcode_inventory" in store.list_tables():
        return
    postcode_table = load_postcode_inventory(POSTCODE_DATA_DIR, LAD_LOOKUP_PATH)
    store.save_arrow_table("postcode_inventory", postcode_table)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/districts/load-postcodes")
def load_postcodes() -> Dict[str, Any]:
    postcode_table = load_postcode_inventory(POSTCODE_DATA_DIR, LAD_LOOKUP_PATH)
    store.save_arrow_table("postcode_inventory", postcode_table, mode="overwrite")
    return {"status": "loaded", "rows": len(postcode_table)}


@app.get("/districts")
def list_districts(county: Optional[str] = Query(default=None)) -> List[Dict[str, Any]]:
    ensure_seed_data()
    query = "SELECT DISTINCT district_name, county_name FROM source"
    if county:
        safe_county = escape_sql_literal(county)
        query += f" WHERE lower(county_name) = lower('{safe_county}')"
    query += " ORDER BY district_post_code"
    return store.query_table("postcode_inventory", query)


def fetch_and_save_pubs_for_district(district_post_code: str, limit: int) -> Dict[str, Any]:
    district_summary = store.query_table(
        "postcode_inventory",
        f"SELECT DISTINCT district_post_code, district_name FROM source WHERE district_post_code = '{district_post_code.upper()}' LIMIT 1",
    )
    if not district_summary:
        raise HTTPException(status_code=404, detail=f"District {district_post_code} not found")
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

    pubs = fetch_pub_records_from_google(
        district["district_post_code"],
        district["district_name"],
        latitude,
        longitude,
        limit,
    )
    store.save_records("pubs_all", pubs, mode="append")
    return {"status": "saved", "table": "pubs_all", "count": len(pubs)}


@app.post("/pubs/fetch-and-save")
def fetch_and_save_pubs(payload: PubPayload) -> Dict[str, Any]:
    ensure_seed_data()
    return fetch_and_save_pubs_for_district(payload.district_post_code, payload.limit)


@app.post("/pubs/fetch-and-save-by-county")
def fetch_and_save_pubs_by_county(payload: CountyPubPayload) -> Dict[str, Any]:
    ensure_seed_data()
    district_rows = store.query_table(
        "postcode_inventory",
        f"SELECT DISTINCT district_post_code, district_name, county_name FROM source WHERE lower(county_name) = lower('{escape_sql_literal(payload.county_name)}') ORDER BY district_post_code",
    )
    if not district_rows:
        raise HTTPException(status_code=404, detail="County not found")

    processed_districts: List[str] = []
    errors: List[Dict[str, Any]] = []
    total_count = 0

    for district in district_rows:
        district_code = district.get("district_post_code", "")
        try:
            result = fetch_and_save_pubs_for_district(district_code, payload.limit)
            total_count += int(result.get("count", 0))
            processed_districts.append(district_code)
        except Exception as exc:  # pragma: no cover - defensive fallback
            errors.append({"district_post_code": district_code, "error": str(exc)})

    return {
        "status": "saved",
        "county": payload.county_name,
        "districts_processed": len(processed_districts),
        "count": total_count,
        "errors": errors,
    }


@app.get("/pubs")
def list_pubs(district_name: Optional[str] = Query(default=None), search: Optional[str] = None) -> List[Dict[str, Any]]:
    if district_name:
        table_name = f"pubs_all"
        try:
            rows = store.query_table(table_name, f"SELECT * FROM source WHERE lower(district_name) = lower('{escape_sql_literal(district_name)}')")
        except FileNotFoundError:
            rows = []
    else:
        try:
            rows = store.query_table("pubs_all", "SELECT * FROM source")
        except FileNotFoundError:
            rows = []

    if search:
        search = search.lower()
        rows = [row for row in rows if search in json.dumps(row).lower()]
    return rows


@app.delete("/tables/{table_name}")
def delete_table_rows(table_name: str) -> Dict[str, Any]:
    try:
        rows_deleted = store.delete_all_rows(table_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "table": table_name, "rows_deleted": rows_deleted}


@app.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    return store.get_schema(table_name)


@app.get("/tables/{table_name}")
def read_table(table_name: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    if query:
        return store.query_table(table_name, query)
    return store.query_table(table_name, "SELECT * FROM source")


@app.post("/mcp")
def mcp(request: MCPRequest) -> Dict[str, Any]:
    if request.tool == "list_tables":
        return {"result": store.list_tables()}
    if request.tool == "list_districts":
        return {"result": list_districts()}
    if request.tool == "fetch_and_save_pubs":
        payload = request.arguments or {}
        return fetch_and_save_pubs(
            PubPayload(
                district_post_code=str(payload.get("district_post_code", "")),
                limit=int(payload.get("limit", 50)),
            )
        )
    if request.tool == "read_table":
        table_name = str(request.arguments.get("table_name", "")) if request.arguments else ""
        query = str(request.arguments.get("query", "SELECT * FROM source")) if request.arguments else "SELECT * FROM source"
        return {"result": read_table(table_name, query)}
    if request.tool == "get_schema":
        table_name = str(request.arguments.get("table_name", "")) if request.arguments else ""
        return {"result": get_table_schema(table_name)}
    raise HTTPException(status_code=400, detail="Unsupported MCP tool")


@app.get("/mcp")
async def mcp_get_not_supported():
    return JSONResponse(
        status_code=405,
        content={"jsonrpc": "2.0", "error": {"code": -32000, "message": "Method not allowed."}, "id": None}
    )