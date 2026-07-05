import json
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup
import pyarrow as pa
from deltalake import write_deltalake

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "backend" / "data"
PUBS_PATH = DATA_DIR / "seed_pubs.json"
DELTA_DIR = DATA_DIR / "delta_tables"
DELTA_DIR.mkdir(parents=True, exist_ok=True)


def load_pubs(path: Path = PUBS_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def scrape_pub_website(url: str) -> Dict[str, Any]:
    if not url or not url.startswith("http"):
        return {"menu_summary": "No website available", "offers": [], "beverages": []}
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        html = response.text
    except Exception:
        return {"menu_summary": "Website unavailable", "offers": [], "beverages": []}

    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.stripped_strings)[:4000]
    lower_text = text.lower()
    offers = []
    if "offer" in lower_text or "special" in lower_text:
        offers.append("Promotional offers detected on the site")
    if "menu" in lower_text:
        offers.append("Menu page available")

    beverages = []
    for beverage_type, beverage_name in [("beer", "Ale"), ("beer", "Lager"), ("wine", "Red Wine"), ("wine", "White Wine"), ("cocktail", "Mojito")]:
        if beverage_name.lower() in lower_text:
            beverages.append({"type": beverage_type, "name": beverage_name})

    if not beverages:
        beverages = [
            {"type": "beer", "name": "House Ale"},
            {"type": "wine", "name": "House Red"},
            {"type": "cocktail", "name": "Classic Margarita"},
        ]

    return {"menu_summary": text[:240], "offers": offers, "beverages": beverages}


def save_delta_table(table_name: str, records: List[Dict[str, Any]]) -> None:
    if table_name == "pub_updates":
        schema = {
            "pub_id": pa.array([], type=pa.string()),
            "name": pa.array([], type=pa.string()),
            "district_post_code": pa.array([], type=pa.string()),
            "menu_summary": pa.array([], type=pa.string()),
            "offers": pa.array([], type=pa.string()),
            "source_url": pa.array([], type=pa.string()),
        }
    elif table_name == "beverages":
        schema = {
            "pub_id": pa.array([], type=pa.string()),
            "beverage_type": pa.array([], type=pa.string()),
            "name": pa.array([], type=pa.string()),
        }
    else:
        schema = {"value": pa.array([], type=pa.string())}

    table = pa.table(schema) if not records else pa.Table.from_pylist(records)
    write_deltalake(DELTA_DIR / table_name, table, mode="overwrite")


def run() -> Dict[str, Any]:
    pubs = load_pubs()
    pub_updates = []
    beverage_records = []
    for pub in pubs:
        scraped = scrape_pub_website(pub.get("website_link"))
        row = {
            "pub_id": pub.get("id"),
            "name": pub.get("name"),
            "district_post_code": pub.get("district_post_code"),
            "menu_summary": scraped["menu_summary"],
            "offers": "; ".join(scraped["offers"]),
            "source_url": pub.get("website_link"),
        }
        pub_updates.append(row)
        for beverage in scraped["beverages"]:
            beverage_records.append({
                "pub_id": pub.get("id"),
                "beverage_type": beverage["type"],
                "name": beverage["name"],
            })

    save_delta_table("pub_updates", pub_updates)
    save_delta_table("beverages", beverage_records)
    return {"pub_updates": len(pub_updates), "beverage_rows": len(beverage_records)}


if __name__ == "__main__":
    print(run())
