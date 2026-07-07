import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper.app.menu_parser import guess_cuisine, parse_menu_heuristic


SAMPLE_MENU = """
Starters
Bruschetta £5.50
Garlic Bread £4.00

Mains
Margherita Pizza £11.50
Spaghetti Carbonara £12.00

Drinks
House Red Wine £6.50
Espresso £2.50
"""


def test_parse_menu_heuristic_extracts_items_with_price_and_currency() -> None:
    items = parse_menu_heuristic(SAMPLE_MENU)

    names = [item["item"] for item in items]
    assert "Bruschetta" in names
    assert "Margherita Pizza" in names
    assert "House Red Wine" in names

    bruschetta = next(item for item in items if item["item"] == "Bruschetta")
    assert bruschetta["price"] == 5.50
    assert bruschetta["currency"] == "£"
    assert bruschetta["section"] == "Starters"
    assert bruschetta["item_type"] == "starter"


def test_parse_menu_heuristic_classifies_beverages() -> None:
    items = parse_menu_heuristic(SAMPLE_MENU)
    wine = next(item for item in items if item["item"] == "House Red Wine")
    assert wine["item_type"] == "beverage"
    assert wine["section"] == "Drinks"


def test_parse_menu_heuristic_ignores_blank_and_header_only_lines() -> None:
    items = parse_menu_heuristic("\n\nJust some text with no prices\n\n")
    assert items == []


def test_guess_cuisine_matches_keywords() -> None:
    assert guess_cuisine("Our pizza and pasta are made fresh, classic italian trattoria") == "italian"
    assert guess_cuisine("Tandoori chicken curry with naan bread") == "indian"
    assert guess_cuisine("nothing relevant here") == "unknown"


def test_parse_menu_heuristic_handles_bare_price_line_blocks() -> None:
    # Real-world layout: name line(s), then allergen/kcal metadata, then a
    # bare price with no currency symbol on its own line.
    block_menu = """
Starters and Nibbles
Broccoli and stilton soup with toasted almonds,
warm seeded roll
(v, gfa)
503 kcal
7.45
Contains: Tree nuts, Milk / Lactose

Mains
9oz rump heart steak
650 kcal
28.95
"""
    items = parse_menu_heuristic(block_menu)
    names = {item["item"]: item for item in items}

    assert names["Broccoli and stilton soup with toasted almonds"]["price"] == 7.45
    assert names["Broccoli and stilton soup with toasted almonds"]["description"] == "warm seeded roll"

    steak = names["9oz rump heart steak"]
    assert steak["price"] == 28.95
    # Regression: "rum" is a beverage keyword and must not match inside "rump".
    assert steak["item_type"] == "food"
