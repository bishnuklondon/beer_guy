import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main


def test_fetch_and_save_by_county_fetches_all_districts(monkeypatch) -> None:
    client = TestClient(main.app)

    def fake_query_table(table_name: str, sql: str):
        if "SELECT DISTINCT district_post_code, district_name, county_name" in sql:
            return [
                {"district_post_code": "CM1", "district_name": "Chelmsford", "county_name": "Essex"},
                {"district_post_code": "SS1", "district_name": "Southend", "county_name": "Essex"},
            ]
        if "SELECT lat, long" in sql:
            return [{"lat": 51.5, "long": 0.1}]
        if "SELECT DISTINCT district_post_code, district_name FROM source WHERE district_post_code" in sql:
            return [{"district_post_code": "CM1", "district_name": "Chelmsford"}]
        return []

    saved = []

    monkeypatch.setattr(main, "ensure_seed_data", lambda: None)
    monkeypatch.setattr(main.store, "query_table", fake_query_table)
    monkeypatch.setattr(main.store, "save_records", lambda table_name, records, mode="overwrite": saved.append((table_name, records, mode)))

    def fake_fetch_pub_records_from_google(district_post_code: str, district_name: str, latitude: float, longitude: float, limit: int):
        return [{"id": f"{district_post_code}-{limit}", "name": district_name}]

    monkeypatch.setattr(main, "fetch_pub_records_from_google", fake_fetch_pub_records_from_google)

    response = client.post(
        "/pubs/fetch-and-save-by-county",
        json={"county_name": "Essex", "limit": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "saved"
    assert body["county"] == "Essex"
    assert body["districts_processed"] == 2
    assert body["count"] == 2
    assert len(saved) == 2
