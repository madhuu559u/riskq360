"""Validate processed chart outputs for completeness and evidence quality.

Checks that all sub-JSON files exist and contain expected fields,
evidence has page numbers and quotes, and measures have proper evidence chains.

Usage:
    python scripts/validate_outputs.py
    python scripts/validate_outputs.py --output-dir outputs/processed
    python scripts/validate_outputs.py --chart 1_RET235214388_v28
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()


def validate_chart(chart_dir: Path) -> dict:
    """Validate a single chart's output directory."""
    result = {
        "chart_id": chart_dir.name,
        "files_present": [],
        "files_missing": [],
        "issues": [],
        "stats": {},
    }

    expected_files = [
        "risk_adjustment.json",
        "hedis_quality.json",
        "clinical_data.json",
        "evidence_index.json",
        "summary.json",
    ]

    for fname in expected_files:
        if (chart_dir / fname).exists():
            result["files_present"].append(fname)
        else:
            result["files_missing"].append(fname)

    # Validate risk_adjustment.json
    ra_path = chart_dir / "risk_adjustment.json"
    if ra_path.exists():
        ra = json.loads(ra_path.read_text(encoding="utf-8"))
        dx_count = ra.get("diagnoses_count", 0)
        result["stats"]["diagnoses"] = dx_count

        # Check evidence quality
        dx_with_page = sum(1 for d in ra.get("diagnoses", []) if d.get("page_number") is not None)
        dx_with_quote = sum(1 for d in ra.get("diagnoses", []) if d.get("exact_quote"))
        dx_with_icd = sum(1 for d in ra.get("diagnoses", []) if d.get("icd_codes"))
        dx_with_date = sum(1 for d in ra.get("diagnoses", []) if d.get("effective_date"))

        if dx_count > 0:
            page_pct = dx_with_page / dx_count * 100
            quote_pct = dx_with_quote / dx_count * 100
            date_pct = dx_with_date / dx_count * 100
            result["stats"]["dx_page_coverage"] = round(page_pct, 1)
            result["stats"]["dx_quote_coverage"] = round(quote_pct, 1)
            result["stats"]["dx_date_coverage"] = round(date_pct, 1)
            if page_pct < 80:
                result["issues"].append(f"Low page coverage in diagnoses: {page_pct:.0f}%")

        # HCC pack
        pack = ra.get("hcc_pack", {})
        result["stats"]["payable_hccs"] = pack.get("raf_summary", {}).get("payable_hcc_count", 0)
        result["stats"]["raf_score"] = pack.get("raf_summary", {}).get("total_raf_score", 0)

        # Check HCC evidence
        for h in pack.get("payable_hccs", []):
            for icd in h.get("supported_icds", []):
                if not icd.get("page_number") and not icd.get("exact_quote"):
                    result["issues"].append(
                        f"HCC {h['hcc_code']} ICD {icd['icd10_code']} missing page/quote evidence"
                    )

    # Validate hedis_quality.json
    hedis_path = chart_dir / "hedis_quality.json"
    if hedis_path.exists():
        hedis = json.loads(hedis_path.read_text(encoding="utf-8"))
        summary = hedis.get("summary", {})
        result["stats"]["hedis_total"] = summary.get("total_measures", 0)
        result["stats"]["hedis_applicable"] = summary.get("applicable", 0)
        result["stats"]["hedis_met"] = summary.get("met", 0)
        result["stats"]["hedis_gap"] = summary.get("gap", 0)

        # Check met measures have evidence
        met_measures = [m for m in hedis.get("measures", []) if m.get("status") == "met"]
        met_with_evidence = sum(1 for m in met_measures if m.get("evidence_used"))
        if met_measures:
            ev_pct = met_with_evidence / len(met_measures) * 100
            result["stats"]["met_evidence_coverage"] = round(ev_pct, 1)
            if ev_pct < 80:
                result["issues"].append(f"Low evidence in met measures: {ev_pct:.0f}%")

        # Check evidence has page numbers
        for m in hedis.get("measures", []):
            for e in m.get("evidence_used", []):
                if e.get("page_number") is None and not (e.get("source", {}) or {}).get("page"):
                    result["issues"].append(
                        f"Measure {m['measure_id']} evidence missing page number"
                    )
                    break

    # Validate clinical_data.json
    clin_path = chart_dir / "clinical_data.json"
    if clin_path.exists():
        clin = json.loads(clin_path.read_text(encoding="utf-8"))
        result["stats"]["medications"] = clin.get("medications", {}).get("count", 0)
        result["stats"]["vitals"] = clin.get("vitals", {}).get("count", 0)
        result["stats"]["labs"] = clin.get("labs", {}).get("count", 0)
        result["stats"]["encounters"] = clin.get("encounters", {}).get("count", 0)

        # Check evidence in clinical data
        for section in ["medications", "vitals", "labs"]:
            items = clin.get(section, {}).get("items", [])
            with_page = sum(1 for i in items if i.get("page_number") is not None)
            if items:
                pct = with_page / len(items) * 100
                if pct < 80:
                    result["issues"].append(f"Low page coverage in {section}: {pct:.0f}%")

    # Validate evidence_index.json
    ei_path = chart_dir / "evidence_index.json"
    if ei_path.exists():
        ei = json.loads(ei_path.read_text(encoding="utf-8"))
        result["stats"]["evidence_pages"] = len(ei.get("pages", {}))
        result["stats"]["total_pages"] = ei.get("total_pages", 0)

    return result


@app.command()
def validate(
    output_dir: str = typer.Option("outputs/processed", "--output-dir", help="Output directory"),
    chart: str = typer.Option(None, "--chart", help="Specific chart to validate"),
) -> None:
    """Validate all processed chart outputs."""
    out_path = Path(output_dir)
    if not out_path.exists():
        console.print(f"[red]Output directory not found: {output_dir}[/red]")
        raise typer.Exit(1)

    if chart:
        charts = [out_path / chart]
    else:
        charts = sorted(p for p in out_path.iterdir() if p.is_dir())

    if not charts:
        console.print("[yellow]No chart directories found[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold blue]MedInsight 360[/bold blue] -- Validating {len(charts)} chart outputs\n")

    table = Table(title="Validation Results")
    table.add_column("Chart", style="cyan", max_width=25)
    table.add_column("Files", justify="center")
    table.add_column("Dx", justify="right")
    table.add_column("HCCs", justify="right")
    table.add_column("RAF", justify="right")
    table.add_column("HEDIS", justify="right")
    table.add_column("Met", justify="right", style="green")
    table.add_column("Gap", justify="right", style="red")
    table.add_column("Pg%", justify="right")
    table.add_column("Issues", justify="right")

    total_issues = 0
    total_charts = 0

    for chart_dir in charts:
        if not chart_dir.is_dir():
            continue
        result = validate_chart(chart_dir)
        total_charts += 1
        total_issues += len(result["issues"])

        s = result["stats"]
        files_ok = f"{len(result['files_present'])}/{len(result['files_present']) + len(result['files_missing'])}"
        page_pct = str(s.get("dx_page_coverage", "?"))
        issue_count = str(len(result["issues"]))

        table.add_row(
            result["chart_id"][:25],
            files_ok,
            str(s.get("diagnoses", 0)),
            str(s.get("payable_hccs", 0)),
            f"{s.get('raf_score', 0):.3f}",
            str(s.get("hedis_applicable", 0)),
            str(s.get("hedis_met", 0)),
            str(s.get("hedis_gap", 0)),
            page_pct,
            issue_count if int(issue_count) > 0 else "",
        )

    console.print(table)
    console.print(f"\n[bold]Summary: {total_charts} charts, {total_issues} total issues[/bold]")

    if total_issues > 0:
        console.print(f"\n[yellow]Charts with issues:[/yellow]")
        for chart_dir in charts:
            if not chart_dir.is_dir():
                continue
            result = validate_chart(chart_dir)
            if result["issues"]:
                console.print(f"  [cyan]{result['chart_id']}[/cyan]:")
                for issue in result["issues"][:5]:
                    console.print(f"    - {issue}")


if __name__ == "__main__":
    app()
