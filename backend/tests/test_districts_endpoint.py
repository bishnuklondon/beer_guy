import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def test_districts_endpoint_filters_by_county() -> None:
    client = TestClient(app)

    all_response = client.get("/districts")
    assert all_response.status_code == 200
    all_data = all_response.json()
    assert all_data

    county = all_data[0]["county_name"]
    filtered_response = client.get("/districts", params={"county": county})

    assert filtered_response.status_code == 200
    filtered_data = filtered_response.json()
    assert filtered_data
    assert all(item["county_name"] == county for item in filtered_data)
