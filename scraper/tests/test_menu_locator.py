import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper.app.menu_locator import find_menu_candidates
from scraper.app.web_fetcher import FetchedResource

HOMEPAGE_HTML = """
<html><body>
<nav>
<a href="/about">About</a>
<a href="/menu">Our Menu</a>
<a href="https://cdn.example.com/files/dinner-menu.pdf">Download Menu (PDF)</a>
<a href="/contact">Contact</a>
</nav>
</body></html>
"""


def _homepage_resource() -> FetchedResource:
    return FetchedResource(
        url="https://example-restaurant.com/",
        content_type="text/html",
        content=HOMEPAGE_HTML.encode(),
        is_pdf=False,
        text=HOMEPAGE_HTML,
    )


def test_find_menu_candidates_prioritizes_pdf_links() -> None:
    candidates = find_menu_candidates("https://example-restaurant.com/", _homepage_resource(), max_candidates=5)

    assert candidates[0] == "https://cdn.example.com/files/dinner-menu.pdf"
    assert "https://example-restaurant.com/menu" in candidates
    assert not any("about" in candidate or "contact" in candidate for candidate in candidates)


def test_find_menu_candidates_falls_back_to_common_paths() -> None:
    empty_homepage = FetchedResource(
        url="https://no-links-restaurant.com/",
        content_type="text/html",
        content=b"<html><body>No links here</body></html>",
        is_pdf=False,
        text="<html><body>No links here</body></html>",
    )

    candidates = find_menu_candidates("https://no-links-restaurant.com/", empty_homepage, max_candidates=3)

    assert len(candidates) == 3
    assert all(candidate.startswith("https://no-links-restaurant.com/") for candidate in candidates)
