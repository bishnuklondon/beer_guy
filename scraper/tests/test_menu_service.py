import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper.app.menu_service import MenuNotFoundError, extract_menu_items
from scraper.app.web_fetcher import FetchedResource, FetchError

HOMEPAGE_HTML = """
<html><head><title>Trattoria Bella</title></head><body>
<a href="/menu">View Menu</a>
</body></html>
"""

MENU_PAGE_HTML = """
<html><body>
<h2>Mains</h2>
<p>Margherita Pizza £11.50</p>
<p>Spaghetti Carbonara £12.00</p>
</body></html>
"""


def _fake_fetch(url: str) -> FetchedResource:
    if url.rstrip("/") == "https://trattoria-bella.com":
        return FetchedResource("https://trattoria-bella.com/", "text/html", HOMEPAGE_HTML.encode(), False, HOMEPAGE_HTML)
    if url.rstrip("/") == "https://trattoria-bella.com/menu":
        return FetchedResource("https://trattoria-bella.com/menu", "text/html", MENU_PAGE_HTML.encode(), False, MENU_PAGE_HTML)
    raise FetchError(f"not found: {url}")


def test_extract_menu_items_uses_heuristic_parser_and_tags_cuisine() -> None:
    with patch("scraper.app.menu_service.fetch", side_effect=_fake_fetch):
        items, source_urls, restaurant_name, parser_used = extract_menu_items("https://trattoria-bella.com")

    assert parser_used == "heuristic"
    assert restaurant_name == "Trattoria Bella"
    assert source_urls == ["https://trattoria-bella.com/menu"]
    assert len(items) == 2
    assert {item.item for item in items} == {"Margherita Pizza", "Spaghetti Carbonara"}
    assert all(item.cuisine == "italian" for item in items)
    assert all(item.restaurant_url == "https://trattoria-bella.com" for item in items)


def test_extract_menu_items_raises_when_no_menu_found() -> None:
    def _fetch_no_menu(url: str) -> FetchedResource:
        html = "<html><head><title>Empty Site</title></head><body>short</body></html>"
        return FetchedResource(url, "text/html", html.encode(), False, html)

    with patch("scraper.app.menu_service.fetch", side_effect=_fetch_no_menu):
        with pytest.raises(MenuNotFoundError):
            extract_menu_items("https://empty-site.com")
