from pathlib import Path
from typing import Dict, List

import pyarrow as pa

from .load_postcodes_to_delta import load_postcodes_to_delta
from .storage import DeltaStore

store = DeltaStore()


def extract_district_code(postcode: str) -> str:
    if not postcode:
        return "UNK"

    first_token = str(postcode).strip().split()[0]
    cleaned = "".join(ch for ch in first_token.upper() if ch.isalnum())
    return cleaned[:3] if len(cleaned) >= 3 else cleaned or "UNK"


def read_lad_lookup(path: Path) -> Dict[str, str]:
    raise NotImplementedError("Use load_postcodes_to_delta for full ingestion")


def load_postcode_inventory(postcode_dir: Path, lad_lookup_path: Path) -> pa.Table:
    output_path = load_postcodes_to_delta(postcode_dir=postcode_dir, lad_lookup_path=lad_lookup_path, output_dir=store.root_dir)
    return store.read_arrow_table("postcode_inventory") if output_path.exists() else pa.table({"pcd7": [], "district_post_code": [], "district_name": [], "lat": [], "long": [], "lad25cd": []})
