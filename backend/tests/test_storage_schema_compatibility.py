import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.storage import DeltaStore


def test_save_records_append_handles_schema_mismatch(tmp_path) -> None:
    store = DeltaStore(root_dir=tmp_path)

    initial_records = [
        {
            "id": "1",
            "name": "Old Pub",
            "address": "Address",
            "rating": 4.0,
            "district_post_code": "CM1",
            "district_name": "Chelmsford",
            "geo_location": "51.5,0.1",
            "website_link": "",
            "googleMaps_link": "",
        }
    ]
    store.save_records("pubs_all", initial_records, mode="overwrite")

    new_records = [
        {
            "id": "2",
            "name": "New Pub",
            "address": "Other Address",
            "rating": 4.5,
            "district_post_code": "CM1",
            "district_name": "Chelmsford",
            "geo_location": "51.6,0.2",
            "website_link": "",
            "googleMaps_link": "",
            "beverage_options": "beer",
        }
    ]

    store.save_records("pubs_all", new_records, mode="append")

    rows = store.query_table("pubs_all", "SELECT * FROM source")
    assert len(rows) == 2
    assert rows[1]["beverage_options"] == "beer"
