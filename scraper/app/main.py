from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import MENU_ITEMS_TABLE
from .menu_service import MenuNotFoundError, extract_menu_items
from .models import ExtractMenuRequest, ExtractMenuResponse
from .storage import DeltaStore
from .web_fetcher import FetchError

app = FastAPI(title="Restaurant Menu Scraper API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DeltaStore()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/menu/extract", response_model=ExtractMenuResponse)
def extract_menu(payload: ExtractMenuRequest) -> ExtractMenuResponse:
    try:
        items, source_urls, restaurant_name, parser_used = extract_menu_items(payload.url)
    except FetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except MenuNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if payload.restaurant_name:
        for item in items:
            item.restaurant_name = payload.restaurant_name

    if items:
        store.save_records(MENU_ITEMS_TABLE, [item.model_dump() for item in items], mode="append")

    return ExtractMenuResponse(
        status="saved" if items else "no_items_found",
        restaurant_url=payload.url,
        source_urls=source_urls,
        parser_used=parser_used,
        items_count=len(items),
        items=items,
    )


@app.get("/menu/items")
def list_menu_items(restaurant_url: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        if restaurant_url:
            safe_url = restaurant_url.replace("'", "''")
            return store.query_table(
                MENU_ITEMS_TABLE,
                f"SELECT * FROM source WHERE restaurant_url = '{safe_url}'",
            )
        return store.query_table(MENU_ITEMS_TABLE, "SELECT * FROM source")
    except FileNotFoundError:
        return []


@app.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    return store.get_schema(table_name)


@app.get("/tables/{table_name}")
def read_table(table_name: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    if query:
        return store.query_table(table_name, query)
    return store.query_table(table_name, "SELECT * FROM source")


@app.delete("/tables/{table_name}")
def delete_table_rows(table_name: str) -> Dict[str, Any]:
    try:
        rows_deleted = store.delete_all_rows(table_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "table": table_name, "rows_deleted": rows_deleted}
