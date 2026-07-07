from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from .config import REQUEST_TIMEOUT, USER_AGENT


class FetchError(Exception):
    pass


@dataclass
class FetchedResource:
    url: str
    content_type: str
    content: bytes
    is_pdf: bool
    text: Optional[str] = None


def normalize_url(url: str) -> str:
    url = url.strip()
    if not urlparse(url).scheme:
        url = f"https://{url}"
    return url


def fetch(url: str) -> FetchedResource:
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        raise FetchError(f"Failed to fetch {url}: {exc}") from exc

    if response.status_code >= 400:
        raise FetchError(f"Failed to fetch {url}: HTTP {response.status_code}")

    content_type = response.headers.get("Content-Type", "").lower()
    if "charset" not in content_type:
        # requests defaults to ISO-8859-1 per HTTP spec when a server omits the
        # charset, which mangles UTF-8 pages (e.g. "£" -> "Â£"). Detect instead.
        response.encoding = response.apparent_encoding
    is_pdf = "application/pdf" in content_type or response.url.lower().split("?")[0].endswith(".pdf")
    return FetchedResource(
        url=response.url,
        content_type=content_type,
        content=response.content,
        is_pdf=is_pdf,
        text=None if is_pdf else response.text,
    )


class RenderedFetcher:
    """Fetches pages through a headless browser instead of a plain HTTP
    request, for sites that load their content (e.g. a menu widget) entirely
    via client-side JavaScript with nothing usable in the raw HTML response.
    Reuses one browser across all fetch() calls make it usable to also crawl
    a rendered page's own links without relaunching a browser per URL."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None

    def __enter__(self) -> "RenderedFetcher":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch()
        return self

    def __exit__(self, *exc_info) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def fetch(self, url: str) -> FetchedResource:
        assert self._browser is not None, "RenderedFetcher must be used as a context manager"
        page = self._browser.new_page(user_agent=USER_AGENT)
        try:
            response = page.goto(url, wait_until="networkidle", timeout=REQUEST_TIMEOUT * 1000)
            if response is not None and response.status >= 400:
                raise FetchError(f"Failed to fetch {url}: HTTP {response.status}")
            html = page.content()
            final_url = page.url
        except PlaywrightError as exc:
            raise FetchError(f"Failed to fetch {url}: {exc}") from exc
        finally:
            page.close()
        return FetchedResource(url=final_url, content_type="text/html", content=html.encode("utf-8"), is_pdf=False, text=html)


def resolve(base_url: str, link: str) -> str:
    return urljoin(base_url, link)


def _bare_domain(netloc: str) -> str:
    netloc = netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def same_domain(url_a: str, url_b: str) -> bool:
    return _bare_domain(urlparse(url_a).netloc) == _bare_domain(urlparse(url_b).netloc)
