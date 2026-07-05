from pathlib import Path
from typing import Dict, List, Optional

import duckdb
import pyarrow as pa
from deltalake import write_deltalake
from .config import LAD_LOOKUP_PATH, POSTCODE_DATA_DIR, COUNTY_LOOKUP_PATH, DELTA_DIR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POSTCODE_DIR = POSTCODE_DATA_DIR
DEFAULT_LAD_LOOKUP_PATH = LAD_LOOKUP_PATH
DEFAULT_COUNTY_LOOKUP_PATH = COUNTY_LOOKUP_PATH
DEFAULT_OUTPUT_DIR = DELTA_DIR


def resolve_data_paths(postcode_dir: Optional[Path] = None, lad_lookup_path: Optional[Path] = None, county_lookup_path: Optional[Path] = None) -> tuple[Path, Path, Path]:
    candidates = []
    if postcode_dir is not None:
        candidates.append(Path(postcode_dir))
        candidates.extend(
            [
                POSTCODE_DATA_DIR
            ]
    )
    postcode_dir = next((candidate for candidate in candidates if candidate.exists()), None)
    if postcode_dir is None:
        postcode_dir = DEFAULT_POSTCODE_DIR

    lad_candidates = []
    if lad_lookup_path is not None:
        lad_candidates.append(Path(lad_lookup_path))
        lad_candidates.extend(
            [
                LAD_LOOKUP_PATH
            ]
    )
    lad_lookup_path = next((candidate for candidate in lad_candidates if candidate.exists()), None)
    if lad_lookup_path is None:
        lad_lookup_path = DEFAULT_LAD_LOOKUP_PATH

    county_candidates = []
    if county_lookup_path is not None:
        county_candidates.append(Path(county_lookup_path))
        county_candidates.extend(
            [
            COUNTY_LOOKUP_PATH
            ]
    )
    county_lookup_path = next((candidate for candidate in county_candidates if candidate.exists()), None)
    if county_lookup_path is None:
        county_lookup_path = DEFAULT_COUNTY_LOOKUP_PATH

    county_lookup_path = next((candidate for candidate in county_candidates if candidate.exists()), None)
    if county_lookup_path is None:
        county_lookup_path = DEFAULT_COUNTY_LOOKUP_PATH

    return postcode_dir, lad_lookup_path, county_lookup_path


def extract_district_code(postcode: str) -> str:
    if not postcode:
        return "UNK"
    first_token = str(postcode).strip().split()[0]
    cleaned = "".join(ch for ch in first_token.upper() if ch.isalnum())
    return cleaned[:3] if len(cleaned) >= 3 else cleaned or "UNK"


def load_postcodes_to_delta(
    postcode_dir: Optional[Path] = None,
    lad_lookup_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    table_name: str = "postcode_inventory",
    county_lookup_path: Optional[Path] = None,
) -> Path:
    postcode_dir, lad_lookup_path, county_lookup_path = resolve_data_paths(postcode_dir, lad_lookup_path, county_lookup_path)
    postcode_dir = Path(postcode_dir)
    lad_lookup_path = Path(lad_lookup_path)
    county_lookup_path = Path(county_lookup_path)
    output_dir = Path(output_dir or DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not postcode_dir.exists():
        raise FileNotFoundError(f"Postcode directory not found: {postcode_dir}")
    if not lad_lookup_path.exists():
        raise FileNotFoundError(f"LAD lookup file not found: {lad_lookup_path}")
    if not county_lookup_path.exists():
        raise FileNotFoundError(f"County lookup file not found: {county_lookup_path}")

    csv_files = sorted(str(path) for path in postcode_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No postcode CSV files found in {postcode_dir}")
    
    with duckdb.connect() as conn:
        conn.execute("CREATE OR REPLACE TEMP TABLE lad_lookup AS SELECT * FROM read_csv_auto(?)", [str(lad_lookup_path)])
        conn.execute("CREATE OR REPLACE TEMP TABLE county_lookup AS SELECT * FROM read_csv_auto(?)", [str(county_lookup_path)])

        union_sql = " UNION ALL ".join(
            f"SELECT pcd7, lat, long, lad25cd, CTY25CD FROM read_csv_auto('{path.replace(chr(39), chr(39) * 2)}')" for path in csv_files
        )
        conn.execute("CREATE OR REPLACE TEMP TABLE postcode_raw AS " + union_sql)

        rows = conn.execute(
            """
            SELECT
                p.pcd7,
                p.lat,
                p.long,
                p.lad25cd,
                l.LAD25NM AS district_name,
                c.column1 AS county_name
            FROM postcode_raw p
            LEFT JOIN lad_lookup l ON p.lad25cd = l.LAD25CD
            LEFT JOIN county_lookup c ON p.CTY25CD = c.column0
            """
        ).fetchdf()

    table = pa.Table.from_pandas(rows, preserve_index=False)
    district_post_codes = [extract_district_code(value) for value in table["pcd7"].to_pylist()]
    district_names = [str(value) if value is not None else "Unknown" for value in table["district_name"].to_pylist()]

    final_table = pa.table(
        {
            "pcd7": table["pcd7"],
            "district_post_code": pa.array(district_post_codes, type=pa.string()),
            "district_name": pa.array(district_names, type=pa.string()),
            "lat": table["lat"],
            "long": table["long"],
            "lad25cd": table["lad25cd"],
            "county_name": table["county_name"],
        }
    )

    target_path = output_dir / table_name
    write_deltalake(target_path, final_table, mode="overwrite")
    return target_path


if __name__ == "__main__":
    path = load_postcodes_to_delta()
    print(f"Saved postcode inventory to {path}")
