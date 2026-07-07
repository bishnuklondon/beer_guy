from bs4 import BeautifulSoup

NOISE_TAGS = ["script", "style", "noscript", "svg", "header", "footer", "nav"]


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""
