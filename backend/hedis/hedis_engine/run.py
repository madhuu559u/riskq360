"""CLI runner for the HEDIS measure engine.

Usage:
    python -m hedis_engine.run --input ./member_assertions.json --year 2025 --out ./hedis_results.json
    python -m hedis_engine.run --input ./member_assertions.json --year 2025 --measures CDC-A1C-TEST,CBP
    python -m hedis_engine.run --input ./member_assertions.json --year 2025 --summary
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .adapters.assertion_adapter import load_assertions_file
from .engine import HedisEngine
from .types import MemberHedisResults


def format_summary(results: MemberHedisResults) -> str:
    """Generate a human-readable markdown summary."""
    lines: list[str] = []
    lines.append(f"# HEDIS Results Summary")
    lines.append(f"**Member**: {results.member_id}")
    lines.append(f"**Measurement Year**: {results.measurement_year}")
    lines.append(f"**Evaluation Date**: {date.today().isoformat()}")
    lines.append("")

    counts = results.summary
    lines.append(f"## Overall")
    lines.append(f"- Total measures evaluated: {len(results.measures)}")
    lines.append(f"- Applicable: {counts.get('applicable', 0)}")
    lines.append(f"- Met: {counts.get('met', 0)}")
    lines.append(f"- Gaps: {counts.get('gap', 0)}")
    lines.append(f"- Excluded: {counts.get('excluded', 0)}")
    lines.append(f"- Indeterminate: {counts.get('indeterminate', 0)}")
    lines.append(f"- Not applicable: {counts.get('not_applicable', 0)}")
    lines.append("")

    # Group by status
    for status_label, status_val in [("Met", "met"), ("Gaps", "gap"), ("Excluded", "excluded"),
                                      ("Indeterminate", "indeterminate"), ("Not Applicable", "not_applicable")]:
        measures_in_status = [m for m in results.measures if m.status.value == status_val]
        if measures_in_status:
            lines.append(f"## {status_label} ({len(measures_in_status)})")
            for m in measures_in_status:
                lines.append(f"- **{m.measure_id}** — {m.measure_name}")
                if m.gaps:
                    for g in m.gaps:
                        lines.append(f"  - Gap: {g.description}")
                if m.evidence_used:
                    for e in m.evidence_used:
                        val = f" = {e.value}" if e.value else ""
                        dt = f" ({e.event_date.isoformat()})" if e.event_date else ""
                        lines.append(f"  - Evidence: {e.event_type} {e.code}{val}{dt}")
            lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HEDIS Measure Engine — evaluate member eligibility, compliance, and gaps",
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to member assertions JSON file",
    )
    parser.add_argument(
        "--year", "-y", type=int, default=2025,
        help="Measurement year (default: 2025)",
    )
    parser.add_argument(
        "--out", "-o", default=None,
        help="Output path for hedis_results.json (default: stdout)",
    )
    parser.add_argument(
        "--catalog", "-c", default=None,
        help="Path to catalog directory with measure YAML files",
    )
    parser.add_argument(
        "--measures", "-m", default=None,
        help="Comma-separated list of measure IDs to evaluate (default: all)",
    )
    parser.add_argument(
        "--summary", "-s", action="store_true",
        help="Also print a human-readable summary to stderr",
    )
    parser.add_argument(
        "--summary-out", default=None,
        help="Write summary to this file path",
    )

    args = parser.parse_args(argv)

    # Load member data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    store = load_assertions_file(input_path)

    # Initialize engine
    catalog_dir = Path(args.catalog) if args.catalog else None
    engine = HedisEngine(catalog_dir=catalog_dir, measurement_year=args.year)

    if not engine.measures:
        print("Warning: No measure definitions found in catalog", file=sys.stderr)

    # Parse measure IDs filter
    measure_ids = None
    if args.measures:
        measure_ids = [m.strip() for m in args.measures.split(",")]

    # Evaluate
    results = engine.evaluate_member(store, measure_ids=measure_ids)

    # Output JSON
    output_json = json.dumps(results.to_dict(), indent=2, default=str)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json, encoding="utf-8")
        print(f"Results written to {out_path}", file=sys.stderr)
    else:
        print(output_json)

    # Summary
    if args.summary or args.summary_out:
        summary_text = format_summary(results)
        if args.summary:
            print(summary_text, file=sys.stderr)
        if args.summary_out:
            Path(args.summary_out).write_text(summary_text, encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
