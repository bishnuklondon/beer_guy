import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper.app.pdf_extractor import extract_text_from_pdf


def test_extract_text_from_pdf_joins_page_text() -> None:
    page_one = MagicMock()
    page_one.extract_text.return_value = "Starters\nBruschetta £5.50"
    page_two = MagicMock()
    page_two.extract_text.return_value = "Mains\nMargherita Pizza £11.50"

    mock_pdf = MagicMock()
    mock_pdf.pages = [page_one, page_two]
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdf.__exit__.return_value = False

    with patch("scraper.app.pdf_extractor.pdfplumber.open", return_value=mock_pdf):
        text = extract_text_from_pdf(b"%PDF-1.4 fake content")

    assert "Bruschetta £5.50" in text
    assert "Margherita Pizza £11.50" in text


def test_extract_text_from_pdf_handles_pages_with_no_text() -> None:
    blank_page = MagicMock()
    blank_page.extract_text.return_value = None

    mock_pdf = MagicMock()
    mock_pdf.pages = [blank_page]
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdf.__exit__.return_value = False

    with patch("scraper.app.pdf_extractor.pdfplumber.open", return_value=mock_pdf):
        text = extract_text_from_pdf(b"%PDF-1.4 fake content")

    assert text == ""
