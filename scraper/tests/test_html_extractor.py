import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper.app.html_extractor import extract_title, extract_visible_text

SAMPLE_HTML = """
<html>
<head><title>The Test Kitchen</title><style>body { color: red; }</style></head>
<body>
<nav>Home | About | Contact</nav>
<header>Welcome banner</header>
<main>
<h1>Our Menu</h1>
<p>Margherita Pizza £11.50</p>
<script>console.log('tracking');</script>
</main>
<footer>Copyright 2026</footer>
</body>
</html>
"""


def test_extract_title() -> None:
    assert extract_title(SAMPLE_HTML) == "The Test Kitchen"


def test_extract_visible_text_strips_noise_tags() -> None:
    text = extract_visible_text(SAMPLE_HTML)
    assert "Margherita Pizza" in text
    assert "Our Menu" in text
    assert "console.log" not in text
    assert "Welcome banner" not in text
    assert "Copyright 2026" not in text
    assert "Home | About | Contact" not in text
