"""Build icd10_catalog.json from icd10_descriptions.csv and v28_icd_hcc_mappings.csv.

Reads the ICD-10 descriptions and HCC mapping files, joins them by ICD-10 code,
and outputs a JSON catalog suitable for TF-IDF retrieval.
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DESCRIPTIONS_CSV = PROJECT_ROOT / "ml_engine" / "models" / "icd10_descriptions.csv"
MAPPINGS_CSV = PROJECT_ROOT / "decisioning" / "reference" / "v28_icd_hcc_mappings.csv"
OUTPUT_JSON = PROJECT_ROOT / "ml_engine" / "models" / "icd10_catalog.json"


def normalize_icd_code(code: str) -> str:
    """Remove dots and whitespace to get a canonical key (e.g. 'E11.65' -> 'E1165')."""
    return re.sub(r"[.\s]", "", code.strip().upper())


def dotted_icd_code(raw: str) -> str:
    """Convert a raw ICD-10 code to dotted format (e.g. 'E1165' -> 'E11.65').

    ICD-10-CM codes have a dot after the 3rd character when code length > 3.
    """
    raw = raw.strip()
    # If it already has a dot, return as-is (uppercased)
    if "." in raw:
        return raw.upper()
    if len(raw) > 3:
        return f"{raw[:3]}.{raw[3:]}".upper()
    return raw.upper()


def main() -> None:
    if not DESCRIPTIONS_CSV.exists():
        print(f"ERROR: Descriptions CSV not found at {DESCRIPTIONS_CSV}")
        sys.exit(1)
    if not MAPPINGS_CSV.exists():
        print(f"ERROR: Mappings CSV not found at {MAPPINGS_CSV}")
        sys.exit(1)

    # ---- Step 1: Build HCC mapping lookup (normalized_code -> list of HCC codes) ----
    hcc_map: dict[str, list[str]] = defaultdict(list)
    hcc_count = 0

    with open(MAPPINGS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_code = row.get("icd10_code", "").strip()
            hcc_code = row.get("hcc_code", "").strip()
            if not raw_code or not hcc_code:
                continue
            key = normalize_icd_code(raw_code)
            if hcc_code not in hcc_map[key]:
                hcc_map[key].append(hcc_code)
            hcc_count += 1

    print(f"Loaded {hcc_count} HCC mapping rows covering {len(hcc_map)} unique ICD codes")

    # ---- Step 2: Read descriptions and merge ----
    catalog: list[dict] = []

    with open(DESCRIPTIONS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_code = row.get("icd10_code", "").strip()
            if not raw_code:
                continue

            code = dotted_icd_code(raw_code)
            key = normalize_icd_code(raw_code)

            # Pick the best available description
            description = (
                row.get("long_desc", "").strip()
                or row.get("description", "").strip()
                or row.get("short_desc", "").strip()
            )

            mapped_hccs = hcc_map.get(key, [])

            search_text = f"{code} {description}"

            entry: dict = {
                "code": code,
                "description": description,
                "synonyms": [],
                "mapped_hccs": mapped_hccs,
                "search_text": search_text,
            }
            catalog.append(entry)

    # ---- Step 3: Report HCC codes that had mappings but no description row ----
    desc_keys = {normalize_icd_code(e["code"]) for e in catalog}
    orphan_hcc_keys = set(hcc_map.keys()) - desc_keys
    if orphan_hcc_keys:
        print(
            f"NOTE: {len(orphan_hcc_keys)} ICD codes in HCC mappings have no description row. "
            "Creating stub entries for them."
        )
        for key in sorted(orphan_hcc_keys):
            code = dotted_icd_code(key)
            mapped_hccs = hcc_map[key]
            catalog.append({
                "code": code,
                "description": "",
                "synonyms": [],
                "mapped_hccs": mapped_hccs,
                "search_text": code,
            })

    # Sort by code for deterministic output
    catalog.sort(key=lambda e: e["code"])

    # ---- Step 4: Write output ----
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    total_with_hcc = sum(1 for e in catalog if e["mapped_hccs"])
    print(f"Wrote {len(catalog)} ICD-10 entries to {OUTPUT_JSON}")
    print(f"  - {total_with_hcc} codes have HCC mappings")
    print(f"  - {len(catalog) - total_with_hcc} codes have no HCC mapping")


if __name__ == "__main__":
    main()
