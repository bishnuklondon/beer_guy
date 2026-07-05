import pyarrow as pa
from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.storage import DeltaStore


def test_delete_table_rows_truncates_table(tmp_path) -> None:
    main_module.store = DeltaStore(tmp_path)
    client = TestClient(main_module.app)

    table = pa.table({"id": ["a", "b"], "name": ["x", "y"]})
    main_module.store.save_arrow_table("demo", table)

    response = client.delete("/tables/demo")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "table": "demo", "rows_deleted": 2}
    assert main_module.store.query_table("demo", "SELECT * FROM source") == []
