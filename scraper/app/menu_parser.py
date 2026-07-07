import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

PRICE_PATTERN = re.compile(
    r"(?P<currency>£|\$|€|GBP|USD|EUR)\s?(?P<price>\d{1,4}(?:[.,]\d{1,2})?)\s*$"
)
# Some sites render each menu item as its own block of lines (name, then
# description/allergens/kcal, then a bare price with no currency symbol on its
# own line) rather than "name .... £price" on one line. Match that separately.
PRICE_LINE_PATTERN = re.compile(
    r"^(?P<currency>£|\$|€|GBP|USD|EUR)?\s?(?P<price>\d{1,3}\.\d{2})$"
)
SECTION_HEADER_PATTERN = re.compile(r"^[A-Z][A-Za-z &'/-]{2,40}$")

NOISE_LINE_PATTERNS = [
    re.compile(r"^contains:", re.IGNORECASE),
    re.compile(r"^may contain", re.IGNORECASE),
    re.compile(r"^\d+\s*kcal$", re.IGNORECASE),
    re.compile(r"^\(.*\)$"),
]
# Common allergen-checklist words that would otherwise look like short
# title-case "section headers" on many UK restaurant menu pages.
ALLERGEN_WORDS = {
    "crustaceans", "molluscs", "eggs", "fish", "peanuts", "celery", "milk",
    "milk / lactose", "mustard", "sesame", "lupin", "soybeans",
    "sulphur dioxide / sulphites", "cereals containing gluten", "tree nuts",
}
MAX_BUFFERED_LINE_LENGTH = 150

BEVERAGE_KEYWORDS = {
    "beer", "beers", "lager", "lagers", "ale", "ales", "cider", "ciders", "wine", "wines",
    "cocktail", "cocktails", "spirit", "spirits", "gin", "vodka", "whisky", "whiskey",
    "rum", "soda", "coffee", "tea", "juice", "juices", "drink", "drinks", "beverage",
    "beverages", "prosecco", "champagne", "liqueur", "shot", "shots", "brandy", "tequila",
}
DESSERT_KEYWORDS = {
    "dessert", "desserts", "cake", "cakes", "ice cream", "pudding", "puddings",
    "sweet", "sweets", "sorbet", "sorbets", "gelato",
}
STARTER_KEYWORDS = {
    "starter", "starters", "appetizer", "appetizers", "appetiser", "appetisers",
    "small plates", "sharer", "sharers", "nibble", "nibbles",
}

CUISINE_KEYWORDS: Dict[str, List[str]] = {
    "italian": ["italian", "pizza", "pasta", "risotto", "bruschetta"],
    "indian": ["indian", "curry", "tandoori", "masala", "biryani", "naan"],
    "chinese": ["chinese", "dim sum", "szechuan", "cantonese", "wonton"],
    "thai": ["thai", "pad thai", "tom yum", "green curry"],
    "japanese": ["japanese", "sushi", "ramen", "tempura", "sashimi"],
    "mexican": ["mexican", "taco", "burrito", "quesadilla", "nachos"],
    "french": ["french", "bistro", "baguette", "croissant"],
    "british": ["british", "pub", "fish and chips", "sunday roast", "pie"],
    "american": ["american", "burger", "bbq", "barbecue", "diner"],
    "mediterranean": ["mediterranean", "greek", "falafel", "hummus", "gyro"],
    "spanish": ["spanish", "tapas", "paella", "chorizo"],
    "lebanese": ["lebanese", "shawarma", "kebab"],
}


def _compile_keyword_pattern(keywords) -> re.Pattern:
    escaped = sorted((re.escape(keyword) for keyword in keywords), key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)


_BEVERAGE_PATTERN = _compile_keyword_pattern(BEVERAGE_KEYWORDS)
_DESSERT_PATTERN = _compile_keyword_pattern(DESSERT_KEYWORDS)
_STARTER_PATTERN = _compile_keyword_pattern(STARTER_KEYWORDS)
_CUISINE_PATTERNS = {
    cuisine: _compile_keyword_pattern(keywords) for cuisine, keywords in CUISINE_KEYWORDS.items()
}


def _classify_item_type(section: str, item_name: str) -> str:
    # Word-boundary matching avoids false positives like "rum" inside "rump".
    haystack = f"{section} {item_name}"
    if _BEVERAGE_PATTERN.search(haystack):
        return "beverage"
    if _DESSERT_PATTERN.search(haystack):
        return "dessert"
    if _STARTER_PATTERN.search(haystack):
        return "starter"
    return "food"


def guess_cuisine(text: str) -> str:
    best_cuisine = "unknown"
    best_score = 0
    for cuisine, pattern in _CUISINE_PATTERNS.items():
        score = len(pattern.findall(text))
        if score > best_score:
            best_score = score
            best_cuisine = cuisine
    return best_cuisine


def _is_noise_line(line: str) -> bool:
    if line.lower() in ALLERGEN_WORDS:
        return True
    return any(pattern.match(line) for pattern in NOISE_LINE_PATTERNS)


def _split_name_and_description(pending_lines: List[str]) -> Tuple[str, str]:
    if not pending_lines:
        return "", ""
    name = pending_lines[0].rstrip(",")
    description = " ".join(pending_lines[1:]).strip()
    return name, description


def parse_menu_heuristic(raw_text: str) -> List[Dict[str, Any]]:
    """Regex-driven fallback parser. Handles two common layouts:
    1. 'Item name .... £12.50' on a single line.
    2. A block of lines (name, then description/allergens/kcal) closed off by
       a bare price on its own line, often with no currency symbol.
    Short title-case lines with no price are treated as section headers."""
    items: List[Dict[str, Any]] = []
    current_section = ""
    pending_lines: List[str] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip(" .•-–")
        if not line or _is_noise_line(line):
            continue

        price_line_match = PRICE_LINE_PATTERN.fullmatch(line)
        if price_line_match:
            name, description = _split_name_and_description(pending_lines)
            pending_lines = []
            if name and len(name) >= 2:
                items.append(
                    {
                        "item": name,
                        "section": current_section,
                        "item_type": _classify_item_type(current_section, name),
                        "price": float(price_line_match.group("price")),
                        "currency": price_line_match.group("currency") or "",
                        "description": description,
                    }
                )
            continue

        inline_price_match = PRICE_PATTERN.search(line)
        if inline_price_match:
            name = line[: inline_price_match.start()].strip(" .•-–")
            pending_lines = []
            if not name or len(name) < 2:
                continue
            price_str = inline_price_match.group("price").replace(",", ".")
            try:
                price: Optional[float] = float(price_str)
            except ValueError:
                price = None
            items.append(
                {
                    "item": name,
                    "section": current_section,
                    "item_type": _classify_item_type(current_section, name),
                    "price": price,
                    "currency": inline_price_match.group("currency"),
                    "description": "",
                }
            )
            continue

        if SECTION_HEADER_PATTERN.match(line) and len(line.split()) <= 6:
            current_section = line.title()
            pending_lines = []
            continue

        if len(line) <= MAX_BUFFERED_LINE_LENGTH:
            pending_lines.append(line)

    return items


LLM_SYSTEM_PROMPT = (
    "You extract structured menu data from raw restaurant menu text scraped from a "
    "website or PDF. Respond with ONLY a JSON array (no prose, no markdown fences). "
    "Each element must be an object with exactly these fields: "
    "item (string, the dish/drink name), "
    "item_type (one of: food, beverage, dessert, starter, side, alcohol), "
    "cuisine (a single best-guess word/phrase such as italian, indian, british, mexican, "
    "unknown), "
    "price (number or null if not listed), "
    "currency (e.g. GBP, USD, EUR, or empty string if unknown), "
    "section (the menu section/category this item appeared under, empty string if none), "
    "description (short string, empty if none). "
    "Skip lines that are not actual menu items (headers, addresses, opening hours, etc.)."
)


def is_llm_available() -> bool:
    return bool(ANTHROPIC_API_KEY)


def _parse_json_array(text: str) -> Optional[List[Dict[str, Any]]]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def parse_menu_with_llm(raw_text: str, context_hint: str = "") -> Optional[List[Dict[str, Any]]]:
    if not is_llm_available():
        return None
    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    truncated_text = raw_text[:20000]
    user_content = f"Restaurant context: {context_hint}\n\nRaw menu text:\n{truncated_text}"

    try:
        message = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=LLM_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception:
        return None

    response_text = "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    )
    return _parse_json_array(response_text)


def parse_menu(raw_text: str, context_hint: str = "") -> Tuple[List[Dict[str, Any]], str]:
    llm_items = parse_menu_with_llm(raw_text, context_hint)
    if llm_items:
        return llm_items, "llm"
    return parse_menu_heuristic(raw_text), "heuristic"
