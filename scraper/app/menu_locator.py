import re
from typing import List

from bs4 import BeautifulSoup

from .web_fetcher import FetchedResource, resolve

MENU_KEYWORD_PATTERN = re.compile(
    r"\bmenus?\b|\bfood\s*menu\b|\bdrinks?\s*menu\b|\bwine\s*list\b|\ba\s*la\s*carte\b|\bspeisekarte\b|\bcarte\b",
    re.IGNORECASE,
)

COMMON_MENU_PATHS = [
    "/menu",
    "/menus",
    "/our-menu",
    "/food-menu",
    "/menu.html",
    "/menu.pdf",
    "/menus/food-menu",
    "/dine/menu",
    "/wine-list",
    "/drinks-menu",
]


def find_menu_candidates(base_url: str, homepage: FetchedResource, max_candidates: int) -> List[str]:
    """Look at the homepage for links that plausibly point at a menu (HTML page or PDF),
    prioritizing PDF links, falling back to a list of common menu URL paths."""
    seen = set()
    scored_links = []

    soup = BeautifulSoup(homepage.text or "", "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith(("mailto:", "tel:", "javascript:")):
            continue
        text = anchor.get_text(" ", strip=True) or ""
        haystack = f"{text} {href}"
        if MENU_KEYWORD_PATTERN.search(haystack):
            absolute = resolve(base_url, href)
            score = 2 if href.lower().split("?")[0].endswith(".pdf") else 1
            scored_links.append((score, absolute))

    scored_links.sort(key=lambda pair: pair[0], reverse=True)

    candidates: List[str] = []
    for _, link in scored_links:
        if link not in seen:
            seen.add(link)
            candidates.append(link)
        if len(candidates) >= max_candidates:
            return candidates

    for path in COMMON_MENU_PATHS:
        if len(candidates) >= max_candidates:
            break
        link = resolve(base_url, path)
        if link not in seen:
            seen.add(link)
            candidates.append(link)

    return candidates[:max_candidates]
