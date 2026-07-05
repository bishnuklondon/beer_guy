from pathlib import Path

from backend.app.ingestion import extract_district_code


def test_extract_district_code_handles_postcodes() -> None:
    assert extract_district_code("AB1 0AA") == "AB1"
    assert extract_district_code("B1  1AA") == "B1"
    assert extract_district_code("") == "UNK"
