from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from .config import DELTA_DIR


class DeltaStore:
    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = Path(root_dir) if root_dir else DELTA_DIR
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _table_path(self, table_name: str) -> Path:
        return self.root_dir / table_name

    def list_tables(self) -> List[str]:
        return [path.name for path in self.root_dir.iterdir() if path.is_dir()]

    def save_arrow_table(self, table_name: str, table: pa.Table, mode: str = "overwrite") -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        schema_mode = "merge" if mode == "append" else "overwrite"
        write_deltalake(self._table_path(table_name), table, mode=mode, schema_mode=schema_mode)
        return self._table_path(table_name)

    def save_records(self, table_name: str, records: List[Dict[str, Any]], mode: str = "overwrite") -> Path:
        if not records:
            table = pa.table({"id": pa.array([], type=pa.string())})
            return self.save_arrow_table(table_name, table, mode=mode)

        if mode == "append" and self._table_path(table_name).exists():
            existing_table = self.read_arrow_table(table_name)
            existing_rows = existing_table.to_pylist()
            field_names = [field.name for field in existing_table.schema]
            for record in records:
                for key in record.keys():
                    if key not in field_names:
                        field_names.append(key)

            combined_rows = []
            for row in existing_rows:
                combined_rows.append({field: row.get(field) for field in field_names})
            for record in records:
                combined_rows.append({field: record.get(field) for field in field_names})

            table = pa.Table.from_pylist(combined_rows)
            return self.save_arrow_table(table_name, table, mode="overwrite")

        table = pa.Table.from_pylist(records)
        return self.save_arrow_table(table_name, table, mode=mode)

    def delete_all_rows(self, table_name: str) -> int:
        path = self._table_path(table_name)
        if not path.exists():
            raise FileNotFoundError(f"Table {table_name} was not found")

        table = self.read_arrow_table(table_name)
        rows_deleted = len(table)
        empty_table = pa.table({field.name: pa.array([], type=field.type) for field in table.schema})
        self.save_arrow_table(table_name, empty_table, mode="overwrite")
        return rows_deleted

    def read_arrow_table(self, table_name: str) -> pa.Table:
        path = self._table_path(table_name)
        if not path.exists():
            raise FileNotFoundError(f"Table {table_name} was not found")
        return DeltaTable(path).to_pyarrow_table()

    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        schema = self.read_arrow_table(table_name).schema
        return [{"name": field.name, "type": str(field.type)} for field in schema]

    def query_table(self, table_name: str, sql: str) -> List[Dict[str, Any]]:
        table = self.read_arrow_table(table_name)
        connection = duckdb.connect()
        connection.register("source", table)
        result = connection.execute(sql).fetchdf()
        return result.to_dict(orient="records")
