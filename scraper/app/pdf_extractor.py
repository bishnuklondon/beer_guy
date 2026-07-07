import io
import re

import pdfplumber

PRICE_TOKEN_RE = re.compile(r"^[£$€]?\d+(\.\d{1,2})?$")


def _group_words_into_lines(words, tolerance=3):
    lines = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        for line in lines:
            if abs(line[0]["top"] - word["top"]) <= tolerance:
                line.append(word)
                break
        else:
            lines.append([word])
    lines.sort(key=lambda line: line[0]["top"])
    return lines


def _split_line_by_columns(words, page_width):
    """Splits a reconstructed text line at any sufficiently wide horizontal gap,
    which usually marks a column boundary in multi-column menu layouts —
    plain extract_text() reads straight across columns, merging two unrelated
    dishes onto one row. A gap is skipped (segments stay merged) when the
    segment after it is just a lone trailing price, since that's the normal
    dot-leader/right-aligned-price pattern within a single item, not a new
    column."""
    words = sorted(words, key=lambda w: w["x0"])
    min_gap = max(24, page_width * 0.03)
    segments = [[words[0]]]
    for prev_word, word in zip(words, words[1:]):
        if word["x0"] - prev_word["x1"] > min_gap:
            segments.append([])
        segments[-1].append(word)

    merged_segments = []
    for segment in segments:
        tokens = [w["text"] for w in segment]
        if merged_segments and len(tokens) <= 2 and PRICE_TOKEN_RE.match(tokens[-1].replace(",", "")):
            merged_segments[-1].extend(segment)
        else:
            merged_segments.append(segment)
    return merged_segments


def _extract_page_text(page) -> str:
    try:
        words = list(page.extract_words())
    except Exception:
        words = []

    if not words:
        return page.extract_text() or ""

    lines = _group_words_into_lines(words)
    if not lines:
        return page.extract_text() or ""

    out_lines = []
    for line in lines:
        for segment in _split_line_by_columns(line, page.width):
            out_lines.append(" ".join(w["text"] for w in segment))
    return "\n".join(out_lines)


def extract_text_from_pdf(content: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = _extract_page_text(page)
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)
