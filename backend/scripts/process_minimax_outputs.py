"""Process all existing MiniMax JSON outputs through the HCC and HEDIS bridges.

This script takes pre-generated MiniMax JSON files (from improve/MiniMax/out/)
and runs them through HCC mapping and HEDIS evaluation without requiring LLM calls.

Generates per-chart output directories with:
  - risk_adjustment.json  (HCC/ICD/RAF with evidence + page numbers)
  - hedis_quality.json    (measures with met/gap, evidence + page numbers)
  - clinical_data.json    (medications, vitals, labs, encounters with evidence)
  - evidence_index.json   (page-by-page evidence map)
  - summary.json          (overview)

Usage:
    python scripts/process_minimax_outputs.py
    python scripts/process_minimax_outputs.py --json-dir improve/MiniMax/out --output-dir outputs/processed
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typer
from rich.console import Console
from rich.table import Table

from core.hcc_bridge import build_hcc_pack
from core.hedis_bridge import evaluate_hedis_measures
from decisioning.hcc_mapper import HCCMapper

app = typer.Typer()
console = Console()


def _build_clinical_data(
    assertions: List[Dict[str, Any]],
    summary: Dict[str, Any],
    chart_id: str,
) -> Dict[str, Any]:
    """Build clinical data sub-JSON from assertions."""
    diagnoses = [a for a in assertions if a.get("category") in ("diagnosis", "assessment")]
    medications = [a for a in assertions if a.get("category") == "medication"]
    vitals = [a for a in assertions if a.get("category") == "vital_sign"]
    labs = [a for a in assertions if a.get("category") in ("lab_result", "lab_order")]
    procedures = [a for a in assertions if a.get("category") in ("procedure", "screening")]
    screenings = [a for a in assertions if a.get("is_hedis_evidence")]
    counseling = [a for a in assertions if a.get("category") == "counseling"]
    social_history = [a for a in assertions if a.get("category") == "social_history"]

    def _evidence_fields(a: Dict) -> Dict:
        return {
            "page_number": a.get("page_number"),
            "exact_quote": a.get("exact_quote", ""),
            "char_start": a.get("char_start"),
            "char_end": a.get("char_end"),
        }

    encounters_list = []
    seen_dates = set()
    for a in assertions:
        ed = a.get("effective_date")
        if ed and ed not in seen_dates:
            seen_dates.add(ed)
            encounters_list.append({
                "date": ed,
                "page_number": a.get("page_number"),
            })

    return {
        "chart_id": chart_id,
        "demographics": {
            "dob": summary.get("dob_dates_found", [None])[0] if summary.get("dob_dates_found") else None,
            "date_of_service": summary.get("best_guess_date_of_service"),
        },
        "medications": {
            "items": [{
                "name": a.get("medication_normalized") or a.get("canonical_concept") or a.get("concept"),
                "status": a.get("status"),
                "text": a.get("clean_text") or a.get("text"),
                "effective_date": a.get("effective_date"),
                **_evidence_fields(a),
            } for a in medications],
            "count": len(medications),
            "unique": summary.get("unique_medications", []),
        },
        "vitals": {
            "items": [{
                "concept": a.get("canonical_concept") or a.get("concept"),
                "text": a.get("clean_text") or a.get("text"),
                "systolic": (a.get("structured") or {}).get("bp_systolic"),
                "diastolic": (a.get("structured") or {}).get("bp_diastolic"),
                "effective_date": a.get("effective_date"),
                **_evidence_fields(a),
            } for a in vitals],
            "count": len(vitals),
            "summary": summary.get("structured_vitals_summary", {}),
        },
        "labs": {
            "items": [{
                "concept": a.get("canonical_concept") or a.get("concept"),
                "text": a.get("clean_text") or a.get("text"),
                "effective_date": a.get("effective_date"),
                **_evidence_fields(a),
            } for a in labs],
            "count": len(labs),
        },
        "procedures": {
            "items": [{
                "concept": a.get("canonical_concept") or a.get("concept"),
                "codes": a.get("codes", []),
                "effective_date": a.get("effective_date"),
                **_evidence_fields(a),
            } for a in procedures],
            "count": len(procedures),
        },
        "encounters": {
            "dates": encounters_list,
            "count": len(encounters_list),
        },
        "screenings": {
            "items": [{
                "concept": a.get("canonical_concept") or a.get("concept"),
                "effective_date": a.get("effective_date"),
                **_evidence_fields(a),
            } for a in screenings],
            "count": len(screenings),
        },
    }


def _build_risk_adjustment(
    assertions: List[Dict[str, Any]],
    summary: Dict[str, Any],
    hcc_pack: Dict[str, Any],
    chart_id: str,
    measurement_year: int,
) -> Dict[str, Any]:
    """Build risk adjustment sub-JSON from assertions and HCC pack."""
    diagnoses = [a for a in assertions if a.get("category") in ("diagnosis", "assessment")]
    dx_evidence = []
    for a in diagnoses:
        dx_evidence.append({
            "concept": a.get("canonical_concept") or a.get("concept"),
            "status": a.get("status"),
            "icd_codes": a.get("icd_codes", []),
            "icd_codes_primary": a.get("icd_codes_primary"),
            "effective_date": a.get("effective_date"),
            "page_number": a.get("page_number"),
            "exact_quote": a.get("exact_quote", ""),
            "char_start": a.get("char_start"),
            "char_end": a.get("char_end"),
            "is_payable_ra_candidate": a.get("is_payable_ra_candidate", False),
            "is_hcc_candidate": a.get("is_hcc_candidate", False),
            "condition_group_id_v3": a.get("condition_group_id_v3"),
            "evidence_rank": a.get("evidence_rank"),
        })

    return {
        "chart_id": chart_id,
        "measurement_year": measurement_year,
        "diagnoses": dx_evidence,
        "diagnoses_count": len(dx_evidence),
        "payable_ra_candidates": sum(1 for d in dx_evidence if d.get("is_payable_ra_candidate")),
        "hcc_candidates": sum(1 for d in dx_evidence if d.get("is_hcc_candidate")),
        "icd10_codes_found": summary.get("icd10cm_codes_found", []),
        "icd9_codes_found": summary.get("icd9cm_codes_found", []),
        "hcc_pack": hcc_pack,
        "raf_summary": hcc_pack.get("raf_summary", {}),
    }


def _build_evidence_index(
    assertions: List[Dict[str, Any]],
    chart_id: str,
    page_count: int,
) -> Dict[str, Any]:
    """Build page-level evidence index."""
    page_evidence: Dict[int, List[Dict]] = {}
    for a in assertions:
        pg = a.get("page_number")
        if pg is None:
            continue
        if pg not in page_evidence:
            page_evidence[pg] = []
        page_evidence[pg].append({
            "category": a.get("category"),
            "concept": a.get("canonical_concept") or a.get("concept"),
            "status": a.get("status"),
            "effective_date": a.get("effective_date"),
            "exact_quote": (a.get("exact_quote") or "")[:200],
            "icd_codes": [c.get("code") for c in (a.get("icd_codes") or [])],
            "is_ra_candidate": a.get("is_payable_ra_candidate", False),
            "is_hedis_evidence": a.get("is_hedis_evidence", False),
        })

    return {
        "chart_id": chart_id,
        "total_pages": page_count,
        "pages": {str(pg): items for pg, items in sorted(page_evidence.items())},
    }


@app.command()
def process(
    json_dir: str = typer.Option("improve/MiniMax/out", "--json-dir", help="Directory with MiniMax JSON files"),
    output_dir: str = typer.Option("outputs/processed", "--output-dir", help="Output directory"),
    pattern: str = typer.Option("*_v28.json", "--pattern", help="Glob pattern for JSON files"),
    dob: str = typer.Option(None, "--dob", help="Override DOB (YYYY-MM-DD)"),
    gender: str = typer.Option(None, "--gender", help="Override gender (male/female)"),
    measurement_year: int = typer.Option(2025, "--measurement-year", help="HEDIS measurement year"),
    limit: int = typer.Option(0, "--limit", help="Limit number of files (0 = all)"),
    persist_db: bool = typer.Option(False, "--persist-db", help="Store results in database"),
    db_url: str = typer.Option(None, "--db-url", help="DB URL (default: sqlite:///outputs/medinsight360.db, or 'postgres')"),
) -> None:
    """Process all MiniMax JSON outputs through HCC and HEDIS bridges."""
    json_path = Path(json_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    files = sorted(json_path.glob(pattern))
    if not files:
        console.print(f"[red]No files matching {pattern} in {json_dir}[/red]")
        raise typer.Exit(1)

    if limit > 0:
        files = files[:limit]

    console.print(f"[bold blue]MedInsight 360[/bold blue] -- Processing {len(files)} MiniMax outputs\n")

    # DB persistence setup
    db_engine = None
    if persist_db:
        from database.persist import init_db
        db_engine = init_db(db_url)
        db_label = db_url or f"sqlite:///outputs/medinsight360.db"
        console.print(f"[bold green]DB persistence ON:[/bold green] {db_label}\n")

    # Load HCC mapper once
    ref_dir = Path("decisioning/reference")
    mapper = HCCMapper(ref_dir)

    results_table = Table(title="Processing Results")
    results_table.add_column("File", style="cyan", max_width=30)
    results_table.add_column("Assert", justify="right")
    results_table.add_column("Dx", justify="right")
    results_table.add_column("ICD-10", justify="right")
    results_table.add_column("Pay ICDs", justify="right")
    results_table.add_column("HCCs", justify="right")
    results_table.add_column("RAF", justify="right")
    results_table.add_column("HEDIS Appl", justify="right")
    results_table.add_column("Met", justify="right", style="green")
    results_table.add_column("Gap", justify="right", style="red")
    results_table.add_column("Time", justify="right")

    totals = {
        "files": 0, "assertions": 0, "diagnoses": 0, "icd_codes": 0,
        "payable_icds": 0, "hccs": 0, "raf": 0.0,
        "hedis_applicable": 0, "hedis_met": 0, "hedis_gap": 0,
        "errors": 0,
    }

    for f in files:
        t0 = time.time()
        name = f.stem
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)

            assertions = data.get("assertions", [])
            summary = data.get("summary", {})
            meta = data.get("meta", {})
            page_count = meta.get("page_count", 0)

            diagnoses = [a for a in assertions if a.get("category") in ("diagnosis", "assessment")]

            # HCC mapping
            hcc_pack = build_hcc_pack(
                assertions=assertions,
                hcc_mapper=mapper,
                chart_id=name,
                measurement_year=measurement_year,
            )

            # HEDIS evaluation
            hedis_result = evaluate_hedis_measures(
                assertions=assertions,
                measurement_year=measurement_year,
                pdf_name=meta.get("pdf", name),
                summary=summary,
                dob=dob,
                gender=gender,
            )

            # Build sub-JSONs
            risk_adj = _build_risk_adjustment(assertions, summary, hcc_pack, name, measurement_year)
            clinical = _build_clinical_data(assertions, summary, name)
            evidence_idx = _build_evidence_index(assertions, name, page_count)

            # Save outputs
            chart_dir = out_path / name
            chart_dir.mkdir(parents=True, exist_ok=True)

            output_files = {
                "risk_adjustment.json": risk_adj,
                "hedis_quality.json": hedis_result,
                "clinical_data.json": clinical,
                "evidence_index.json": evidence_idx,
                "summary.json": {
                    "source_file": str(f),
                    "chart_id": name,
                    "assertions_count": len(assertions),
                    "diagnoses_count": len(diagnoses),
                    "icd10_codes": summary.get("icd10cm_codes_found", []),
                    "demographics": {
                        "dob": summary.get("dob_dates_found", [None])[0] if summary.get("dob_dates_found") else None,
                        "dos": summary.get("best_guess_date_of_service"),
                    },
                    "risk_adjustment": hcc_pack.get("raf_summary", {}),
                    "hedis": hedis_result.get("summary", {}),
                },
            }

            for fname, fdata in output_files.items():
                with open(chart_dir / fname, "w", encoding="utf-8") as fout:
                    json.dump(fdata, fout, indent=2, default=str)

            # Persist to database
            if db_engine is not None:
                from database.persist import persist_chart_results
                persist_chart_results(
                    engine=db_engine,
                    chart_name=name,
                    source_file=str(f),
                    assertions=assertions,
                    hcc_pack=hcc_pack,
                    hedis_result=hedis_result,
                    measurement_year=measurement_year,
                    page_count=page_count,
                    elapsed_seconds=round(time.time() - t0, 2),
                )

            # Metrics
            icd_count = len(summary.get("icd10cm_codes_found", []))
            payable_icds = hcc_pack.get("payable_icd_count", 0)
            hcc_count = len(hcc_pack.get("payable_hccs", []))
            raf_score = hcc_pack.get("raf_summary", {}).get("total_raf_score", 0)
            hs = hedis_result.get("summary", {})
            hedis_applicable = hs.get("applicable", 0)
            hedis_met = hs.get("met", 0)
            hedis_gap = hs.get("gap", 0)
            elapsed = round(time.time() - t0, 2)

            results_table.add_row(
                name[:30], str(len(assertions)), str(len(diagnoses)),
                str(icd_count), str(payable_icds), str(hcc_count),
                f"{raf_score:.3f}", str(hedis_applicable),
                str(hedis_met), str(hedis_gap), f"{elapsed}s",
            )

            totals["files"] += 1
            totals["assertions"] += len(assertions)
            totals["diagnoses"] += len(diagnoses)
            totals["icd_codes"] += icd_count
            totals["payable_icds"] += payable_icds
            totals["hccs"] += hcc_count
            totals["raf"] += raf_score
            totals["hedis_applicable"] += hedis_applicable
            totals["hedis_met"] += hedis_met
            totals["hedis_gap"] += hedis_gap

        except Exception as e:
            console.print(f"  [red]Error processing {name}: {e}[/red]")
            import traceback
            traceback.print_exc()
            totals["errors"] += 1
            results_table.add_row(name[:30], "ERR", "", "", "", "", "", "", "", "", "")

    console.print(results_table)
    console.print(f"\n[bold]Totals:[/bold]")
    console.print(f"  Files processed: {totals['files']} ({totals['errors']} errors)")
    console.print(f"  Total assertions: {totals['assertions']}")
    console.print(f"  Total diagnoses: {totals['diagnoses']}")
    console.print(f"  Total ICD-10 codes: {totals['icd_codes']}")
    console.print(f"  Total payable ICDs: {totals['payable_icds']}")
    console.print(f"  Total HCCs: {totals['hccs']}")
    console.print(f"  Total RAF: {totals['raf']:.3f}")
    console.print(f"  HEDIS applicable: {totals['hedis_applicable']}")
    console.print(f"  HEDIS met: {totals['hedis_met']}, gaps: {totals['hedis_gap']}")
    console.print(f"\n[dim]Outputs saved to: {out_path}[/dim]")

    # DB stats
    if db_engine is not None:
        from database.persist import get_db_stats
        stats = get_db_stats(db_engine)
        console.print(f"\n[bold green]Database Stats:[/bold green]")
        db_table = Table(title="Table Row Counts")
        db_table.add_column("Table", style="cyan")
        db_table.add_column("Rows", justify="right", style="green")
        for table_name, count in sorted(stats.items()):
            db_table.add_row(table_name, str(count))
        console.print(db_table)
        console.print()


if __name__ == "__main__":
    app()
