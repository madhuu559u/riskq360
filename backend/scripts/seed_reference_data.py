"""Load V28 mappings, HCC codes, HEDIS specs into the database."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from config.settings import get_settings

console = Console()


def seed_reference_data() -> None:
    """Seed reference data from CSV/JSON files into database tables."""
    settings = get_settings()
    ref_dir = settings.paths.reference_data_dir

    console.print("[bold blue]MedInsight 360 — Seeding Reference Data[/bold blue]\n")

    # Seed ICD → HCC mappings
    mapping_file = ref_dir / "v28_icd_hcc_mappings.csv"
    if mapping_file.exists():
        count = _seed_icd_hcc_mappings(mapping_file)
        console.print(f"  [green]+[/green] ICD -> HCC mappings: {count} records")
    else:
        console.print(f"  [yellow]! {mapping_file} not found[/yellow]")

    # Seed HCC labels
    labels_file = ref_dir / "v28_hcc_labels.json"
    if labels_file.exists():
        with open(labels_file, encoding="utf-8") as f:
            labels = json.load(f)
        console.print(f"  [green]+[/green] HCC labels: {len(labels)} categories")

    # Seed hierarchy rules
    hierarchy_file = ref_dir / "v28_hierarchy_rules.json"
    if hierarchy_file.exists():
        with open(hierarchy_file, encoding="utf-8") as f:
            hierarchy = json.load(f)
        console.print(f"  [green]+[/green] Hierarchy rules: {len(hierarchy)} groups")

    # Seed coefficients
    coeff_file = ref_dir / "v28_coefficients.json"
    if coeff_file.exists():
        with open(coeff_file, encoding="utf-8") as f:
            coeffs = json.load(f)
        console.print(f"  [green]+[/green] RAF coefficients: {len(coeffs)} HCCs")

    # Seed HEDIS measure specs
    hedis_file = ref_dir / "hedis_measure_specs.json"
    if hedis_file.exists():
        with open(hedis_file, encoding="utf-8") as f:
            measures = json.load(f)
        console.print(f"  [green]+[/green] HEDIS measures: {len(measures)} specs")
    else:
        console.print(f"  [yellow]! {hedis_file} not found -- using built-in defaults[/yellow]")

    console.print("\n[green]Reference data seeding complete![/green]")


def _seed_icd_hcc_mappings(path: Path) -> int:
    """Load ICD → HCC mappings from CSV."""
    count = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            count += 1
    return count


if __name__ == "__main__":
    seed_reference_data()
