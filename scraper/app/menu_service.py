import hashlib
import uuid
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

from .config import MAX_CRAWL_CANDIDATES
from .html_extractor import extract_title, extract_visible_text
from .menu_locator import find_menu_candidates
from .menu_parser import guess_cuisine, parse_menu
from .models import MenuItem
from .pdf_extractor import extract_text_from_pdf
from .web_fetcher import FetchedResource, FetchError, RenderedFetcher, fetch, normalize_url


class MenuNotFoundError(Exception):
    pass


def _resource_text(resource: FetchedResource) -> str:
    if resource.is_pdf:
        return extract_text_from_pdf(resource.content)
    return extract_visible_text(resource.text or "")


def _fetch_candidate(candidate_url: str, fetch_fn: Callable[[str], FetchedResource]) -> FetchedResource:
    # PDFs should always go through the plain HTTP fetch: a headless browser
    # would just download/render the file rather than giving back its bytes.
    if candidate_url.lower().split("?")[0].endswith(".pdf"):
        return fetch(candidate_url)
    return fetch_fn(candidate_url)


def _collect_candidate_texts(
    base_url: str, homepage: FetchedResource, fetch_fn: Callable[[str], FetchedResource]
) -> Tuple[List[str], List[str]]:
    """Crawls menu-like links starting from `homepage` (up to two hops, since
    menu "hub" pages often just link out to separate PDFs rather than
    containing the menu itself), collecting deduplicated page/PDF text."""
    candidates = find_menu_candidates(base_url, homepage, MAX_CRAWL_CANDIDATES)

    collected_texts: List[str] = []
    used_urls: List[str] = []
    seen_resolved_urls = set()
    seen_text_hashes = set()
    queue: List[str] = list(candidates)
    queued_urls = set(queue)
    max_total_fetches = MAX_CRAWL_CANDIDATES * 3
    fetch_count = 0

    while queue and fetch_count < max_total_fetches:
        candidate_url = queue.pop(0)
        fetch_count += 1
        try:
            resource = _fetch_candidate(candidate_url, fetch_fn)
        except FetchError:
            continue
        if resource.url in seen_resolved_urls:
            continue

        candidate_text = _resource_text(resource)
        if candidate_text and len(candidate_text.strip()) > 40:
            text_hash = hashlib.sha256(candidate_text.strip().encode("utf-8")).hexdigest()
            if text_hash not in seen_text_hashes:
                seen_resolved_urls.add(resource.url)
                seen_text_hashes.add(text_hash)
                collected_texts.append(candidate_text)
                used_urls.append(resource.url)

        if not resource.is_pdf:
            deeper_links = find_menu_candidates(resource.url, resource, MAX_CRAWL_CANDIDATES)
            for link in deeper_links:
                if link not in queued_urls:
                    queued_urls.add(link)
                    queue.append(link)

    return collected_texts, used_urls


def locate_and_extract_menu_text(
    url: str, fetch_fn: Optional[Callable[[str], FetchedResource]] = None
) -> Tuple[str, List[str], str]:
    """Fetches the given URL, then browses the homepage looking for a menu
    (HTML page or PDF), returning the raw menu text, the source URL(s) it came
    from, and a best-effort restaurant name from the page title."""
    # `fetch_fn` defaults to the module-level `fetch` looked up here (rather
    # than as a default argument) so that tests patching `menu_service.fetch`
    # still take effect — a default argument would bind the pre-patch
    # function object at definition time instead.
    if fetch_fn is None:
        fetch_fn = fetch
    base_url = normalize_url(url)
    homepage = fetch_fn(base_url)

    if homepage.is_pdf:
        return extract_text_from_pdf(homepage.content), [homepage.url], ""

    restaurant_name = extract_title(homepage.text or "")
    homepage_text = extract_visible_text(homepage.text or "")

    collected_texts, used_urls = _collect_candidate_texts(base_url, homepage, fetch_fn)
    if collected_texts:
        return "\n\n".join(collected_texts), used_urls, restaurant_name

    if len(homepage_text.strip()) > 80:
        return homepage_text, [homepage.url], restaurant_name

    raise MenuNotFoundError(f"Could not locate menu content for {url}")


def _parsed_items(raw_text: str, restaurant_name: str, url: str):
    context_hint = f"Restaurant name: {restaurant_name or 'unknown'}. Homepage URL: {url}."
    return parse_menu(raw_text, context_hint)


def extract_menu_items(url: str) -> Tuple[List[MenuItem], List[str], str, str]:
    raw_text = source_urls = restaurant_name = parsed_items = parser_used = None
    try:
        raw_text, source_urls, restaurant_name = locate_and_extract_menu_text(url)
        parsed_items, parser_used = _parsed_items(raw_text, restaurant_name, url)
    except (MenuNotFoundError, FetchError):
        parsed_items = []

    if not parsed_items:
        # Some sites (often third-party menu widgets) load their menu
        # entirely via client-side JavaScript, leaving nothing usable — or
        # just boilerplate with no actual items — in the raw HTTP response.
        # As a last resort, retry with a headless browser so JS gets to run.
        try:
            with RenderedFetcher() as rendered_fetcher:
                rendered_text, rendered_sources, rendered_name = locate_and_extract_menu_text(
                    url, rendered_fetcher.fetch
                )
                rendered_items, rendered_parser_used = _parsed_items(rendered_text, rendered_name, url)
        except (MenuNotFoundError, FetchError):
            rendered_items = []

        if rendered_items:
            raw_text, source_urls, restaurant_name = rendered_text, rendered_sources, rendered_name
            parsed_items, parser_used = rendered_items, rendered_parser_used

    if not parsed_items:
        raise MenuNotFoundError(f"Could not locate menu content for {url}")

    fallback_cuisine = guess_cuisine(f"{raw_text} {restaurant_name}") if parser_used == "heuristic" else "unknown"
    primary_source = source_urls[0] if source_urls else url
    scraped_at = datetime.now(timezone.utc).isoformat()

    menu_items: List[MenuItem] = []
    for raw_item in parsed_items:
        item_name = str(raw_item.get("item", "")).strip()
        if not item_name:
            continue

        price_value = raw_item.get("price")
        try:
            price = float(price_value) if price_value not in (None, "") else None
        except (TypeError, ValueError):
            price = None

        item_cuisine = str(raw_item.get("cuisine") or "").strip() or fallback_cuisine

        menu_items.append(
            MenuItem(
                id=str(uuid.uuid4()),
                restaurant_url=url,
                restaurant_name=restaurant_name,
                item=item_name,
                item_type=str(raw_item.get("item_type") or "food"),
                cuisine=item_cuisine or "unknown",
                price=price,
                currency=str(raw_item.get("currency") or ""),
                section=str(raw_item.get("section") or ""),
                description=str(raw_item.get("description") or ""),
                source_url=str(raw_item.get("source_url") or primary_source),
                scraped_at=scraped_at,
            )
        )
    return menu_items, source_urls, restaurant_name, parser_used
