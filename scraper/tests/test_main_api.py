import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from scraper.app.main import app
from scraper.app.menu_service import MenuNotFoundError
from scraper.app.models import MenuItem
from scraper.app.web_fetcher import FetchError

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_extract_menu_saves_items_and_returns_response() -> None:
    fake_item = MenuItem(
        id="abc123",
        restaurant_url="https://trattoria-bella.com",
        restaurant_name="Trattoria Bella",
        item="Margherita Pizza",
        item_type="food",
        cuisine="italian",
        price=11.50,
        currency="£",
        section="Mains",
        source_url="https://trattoria-bella.com/menu",
    )

    with patch("scraper.app.main.extract_menu_items", return_value=([fake_item], ["https://trattoria-bella.com/menu"], "Trattoria Bella", "heuristic")), \
         patch("scraper.app.main.store.save_records") as mock_save:
        response = client.post("/menu/extract", json={"url": "https://trattoria-bella.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "saved"
    assert body["items_count"] == 1
    assert body["parser_used"] == "heuristic"
    mock_save.assert_called_once()


def test_extract_menu_returns_422_when_menu_not_found() -> None:
    with patch("scraper.app.main.extract_menu_items", side_effect=MenuNotFoundError("no menu")):
        response = client.post("/menu/extract", json={"url": "https://empty-site.com"})

    assert response.status_code == 422


def test_extract_menu_returns_502_on_fetch_error() -> None:
    with patch("scraper.app.main.extract_menu_items", side_effect=FetchError("boom")):
        response = client.post("/menu/extract", json={"url": "https://unreachable.com"})

    assert response.status_code == 502
