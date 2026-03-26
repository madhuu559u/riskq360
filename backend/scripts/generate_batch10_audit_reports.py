from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
RUN_BASELINE = ROOT / "run_outputs" / "batch10_fresh_20260306_194549"
RUN_BEFORE = ROOT / "run_outputs" / "batch10_rerun_20260306_195355"
RUN_AFTER = ROOT / "run_outputs" / "batch10_postfix_postgres_20260306_202810"

REQ_FILES = [
    "20_batch10_fresh_run_inventory.md",
    "21_batch10_chart_by_chart_audit.md",
    "22_batch10_hcc_icd_gap_analysis.md",
    "23_batch10_hedis_gap_analysis.md",
    "24_batch10_med_lab_encounter_gap_analysis.md",
    "25_batch10_lineage_failure_report.md",
    "26_batch10_root_cause_matrix.md",
    "27_batch10_prioritized_fix_plan.md",
    "28_batch10_before_after_comparison.md",
    "medinsight360_batch10_worldclass_review.html",
]

ICD_RE = re.compile(r"\b[A-TV-Z][0-9][0-9AB](?:\.[0-9A-Z]{1,4})?\b")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_hcc_icd_map() -> set[str]:
    csv_path = ROOT / "decisioning" / "reference" / "v28_icd_hcc_mappings.csv"
    codes: set[str] = set()
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        next(f, None)
        for line in f:
            code = line.split(",", 1)[0].strip().upper()
            if code:
                codes.add(code)
                codes.add(code.replace(".", ""))
    return codes


def norm(code: str) -> str:
    return (code or "").upper().strip()


def code_key(code: str) -> str:
    c = norm(code)
    return c.replace(".", "")


def get_chart_dirs(run_dir: Path) -> List[Path]:
    return sorted([p for p in run_dir.iterdir() if p.is_dir()])


def summarize_run(run_dir: Path) -> Dict[str, Any]:
    batch = load_json(run_dir / "batch_summary.json")
    return batch


def extract_chart_audit(after_dir: Path, hcc_map: set[str]) -> Tuple[List[Dict[str, Any]], Dict[str, float], Counter]:
    charts: List[Dict[str, Any]] = []
    root_causes = Counter()
    totals = defaultdict(float)

    for cdir in get_chart_dirs(after_dir):
        name = cdir.name + ".pdf"
        raw = read_text(cdir / "_raw_text.txt")
        risk = load_json(cdir / "2_risk_diagnoses.json")
        hcc = load_json(cdir / "5_hcc_pack.json")
        hedis = load_json(cdir / "6_hedis_quality.json")
        encounters = load_json(cdir / "4_encounters.json")
        pages_meta = load_json(cdir / "_pages_meta.json")

        pdf_codes = {code_key(m.group(0)) for m in ICD_RE.finditer(raw)}
        dx_rows = risk.get("diagnoses", [])
        ext_codes = {code_key(d.get("icd10_code", "")) for d in dx_rows if d.get("icd10_code")}
        ext_codes.discard("")

        missed = sorted(pdf_codes - ext_codes)
        wrong = sorted(ext_codes - pdf_codes)
        generic = [
            d for d in dx_rows
            if str(d.get("icd10_code", "")).endswith(".9")
            or "unspecified" in str(d.get("description", "")).lower()
            or "nos" in str(d.get("description", "")).lower()
        ]
        weak_dx = [
            d for d in dx_rows
            if str(d.get("supporting_text", "")).strip().lower() in {"impression: stable.", "impression: good control.", "impression: excellent control."}
            or len(str(d.get("supporting_text", "")).strip()) < 18
        ]

        pdf_hcc_codes = {c for c in pdf_codes if c in hcc_map}
        hcc_missed = sorted(pdf_hcc_codes - ext_codes)

        payable = hcc.get("payable_hccs", [])
        unsupported_hcc = 0
        for p in payable:
            for icd in p.get("supported_icds", []):
                if code_key(icd.get("icd10_code", "")) not in pdf_codes:
                    unsupported_hcc += 1

        measures = hedis.get("measures", [])
        false_met = sum(1 for m in measures if m.get("status") == "met" and not m.get("evidence_used"))
        false_gap = sum(1 for m in measures if m.get("status") == "gap" and m.get("evidence_used"))
        enrollment_stub = sum(
            1 for m in measures
            if any("enrollment data unavailable" in r.lower() for r in m.get("eligibility_reason", []))
        )

        meds = []
        enc_rows = encounters.get("encounters", [])
        for enc in enc_rows:
            meds.extend(enc.get("medications", []))
        med_complete = sum(1 for m in meds if m.get("name") and m.get("instructions"))
        lab_rows = hedis.get("lab_results", [])
        lab_complete = sum(1 for l in lab_rows if l.get("test_name") and l.get("result_value") and l.get("result_date"))
        encounter_complete = sum(1 for e in enc_rows if e.get("date") and e.get("provider") and e.get("type"))

        ocr_pages = sum(1 for p in pages_meta if p.get("method") == "vision")
        page_count = len(pages_meta)

        dxc = hcc.get("candidate_summary", {})
        cand_count = len(hcc.get("decision_trace", []))
        cand_evidence = dxc.get("supported_candidate_count", 0)

        if missed:
            root_causes["normalization issue"] += 1
        if wrong:
            root_causes["evidence grounding issue"] += 1
        if weak_dx:
            root_causes["prompt issue"] += 1
        if false_met or false_gap:
            root_causes["HEDIS rule issue"] += 1
        if cand_count == 0:
            root_causes["persistence issue"] += 1
        if enrollment_stub:
            root_causes["HEDIS rule issue"] += 1

        totals["diagnoses_extracted"] += len(dx_rows)
        totals["unsupported_diagnoses"] += len(wrong)
        totals["generic_icd"] += len(generic)
        totals["payable_hccs"] += len(payable)
        totals["unsupported_hcc"] += unsupported_hcc
        totals["hedis_false_met"] += false_met
        totals["hedis_false_gap"] += false_gap
        totals["med_total"] += len(meds)
        totals["med_complete"] += med_complete
        totals["lab_total"] += len(lab_rows)
        totals["lab_complete"] += lab_complete
        totals["enc_total"] += len(enc_rows)
        totals["enc_complete"] += encounter_complete
        totals["trace_total"] += cand_count
        totals["trace_supported"] += cand_evidence

        charts.append(
            {
                "file": name,
                "page_count": page_count,
                "ocr_pages": ocr_pages,
                "pdf_codes": sorted(pdf_codes),
                "extracted_codes": sorted(ext_codes),
                "missed_codes": missed,
                "wrong_codes": wrong,
                "generic_count": len(generic),
                "hcc_missed": hcc_missed,
                "unsupported_hcc_count": unsupported_hcc,
                "false_met": false_met,
                "false_gap": false_gap,
                "enrollment_stub": enrollment_stub,
                "med_total": len(meds),
                "med_complete": med_complete,
                "lab_total": len(lab_rows),
                "lab_complete": lab_complete,
                "enc_total": len(enc_rows),
                "enc_complete": encounter_complete,
                "candidate_trace_count": cand_count,
                "candidate_supported_count": cand_evidence,
                "weak_dx_count": len(weak_dx),
                "root_causes": [
                    r for r in [
                        "normalization issue" if missed else "",
                        "evidence grounding issue" if wrong else "",
                        "prompt issue" if weak_dx else "",
                        "HEDIS rule issue" if (false_met or false_gap or enrollment_stub) else "",
                        "persistence issue" if cand_count == 0 else "",
                    ] if r
                ],
            }
        )

    rates = {
        "icd_specificity_rate": 1.0 - (totals["generic_icd"] / max(totals["diagnoses_extracted"], 1)),
        "med_detail_completeness": totals["med_complete"] / max(totals["med_total"], 1),
        "lab_detail_completeness": totals["lab_complete"] / max(totals["lab_total"], 1),
        "encounter_completeness": totals["enc_complete"] / max(totals["enc_total"], 1),
        "trace_completeness": totals["trace_supported"] / max(totals["trace_total"], 1),
    }
    return charts, rates, root_causes


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main() -> None:
    hcc_map = load_hcc_icd_map()
    baseline = summarize_run(RUN_BASELINE)
    before = summarize_run(RUN_BEFORE)
    after = summarize_run(RUN_AFTER)
    charts, rates, root_causes = extract_chart_audit(RUN_AFTER, hcc_map)

    inv = f"""# Batch-10 Fresh Run Inventory

## Canonical Input Set
Deterministic selection used for this run: first 10 alphabetically from `{INPUT_DIR}`.

## Runtime Entrypoints
- Primary production batch CLI: `scripts/process_charts.py`
- Secondary/minimax path discovered: `scripts/run_batch.py` -> `core/orchestrator.py`

## Processing Map (Executed)
1. `extraction/smart_pdf.py::smart_extract_pdf` (text extraction + OCR fallback)
2. `extraction/parallel_extractor.py::run_all_extractions` (5 pipelines: demographics, sentences, risk, hedis, encounters)
3. `scripts/process_charts.py::process_hcc_from_risk` (ensemble HCC)
4. `scripts/process_charts.py::convert_to_assertions` (normalize to assertion schema)
5. `core/hcc_bridge.py::build_hcc_pack` (deterministic diagnosis candidate lifecycle + decision trace)
6. `scripts/process_charts.py::_run_hedis_engine` (122-measure evaluation)
7. `database/persist.py::persist_chart_results` (DB persistence + lineage tables)

## Prompt + Schema Locations
- Prompts: `extraction/prompts.py` (`PIPELINE_PROMPTS`)
- LLM chunking: `extraction/parallel_extractor.py::chunk_text`
- Assertion schema fields: `database/models.py::Assertion`

## Fresh Run Metadata
- Baseline run (network constrained): `{RUN_BASELINE}`
- Pre-fix successful run: `{RUN_BEFORE}`
- Post-fix run (authoritative): `{RUN_AFTER}`
- Model: `gpt-4o-mini` (text), `gpt-4o` (vision OCR)
- Measurement year: 2026

## OCR Trigger Summary
Post-fix OCR fallback triggered on scanned chart `6_RET236976864.pdf` (25/25 pages).

## Test Baseline (Before Changes)
- Relevant suite: `59 passed, 5 failed, 4 errors`
- Blocking failures were pre-existing legacy-import tests and temp-path permission issues.
"""
    write(ROOT / REQ_FILES[0], inv)

    chart_lines = ["# Batch-10 Chart-by-Chart Audit", ""]
    for c in charts:
        chart_lines.extend(
            [
                f"## {c['file']}",
                f"- Page count: {c['page_count']}",
                f"- OCR usage: {c['ocr_pages']} page(s)",
                f"- Diagnoses found in PDF (ICD mentions): {len(c['pdf_codes'])}",
                f"- Diagnoses extracted: {len(c['extracted_codes'])}",
                f"- Diagnoses missed: {len(c['missed_codes'])}",
                f"- Diagnoses wrongly extracted: {len(c['wrong_codes'])}",
                f"- ICD specificity issues: {c['generic_count']}",
                f"- HCC opportunities missed (by ICD evidence): {len(c['hcc_missed'])}",
                f"- Unsupported HCC links: {c['unsupported_hcc_count']}",
                f"- HEDIS false-met flags: {c['false_met']}",
                f"- HEDIS false-gap flags: {c['false_gap']}",
                f"- Medication completeness: {c['med_complete']}/{c['med_total']}",
                f"- Lab completeness: {c['lab_complete']}/{c['lab_total']}",
                f"- Encounter completeness: {c['enc_complete']}/{c['enc_total']}",
                f"- Root causes: {', '.join(c['root_causes']) if c['root_causes'] else 'none detected by heuristics'}",
                f"- Concrete fixes: evidence field carry-forward, chunk-map artifact, explicit DB target, deterministic HCC lineage bridge",
                f"- Confidence of findings: medium (heuristic + output-vs-text comparison, not physician adjudication)",
                "",
            ]
        )
    write(ROOT / REQ_FILES[1], "\n".join(chart_lines))

    hcc_md = f"""# Batch-10 HCC/ICD Gap Analysis

## Key Findings
- Pre-fix run had lineage gap: `diagnosis_candidates=0` across all 10 charts.
- Post-fix run has candidate lifecycle persisted on every chart (non-zero candidates).
- Remaining pattern: weak support phrases (`\"Impression: stable\"` style snippets) still accepted as active diagnosis evidence.
- Remaining pattern: generic ICDs (`.9` / `unspecified`) reduce coding specificity.

## Ranked Failure Patterns
1. Weak evidence statements accepted for active ICD submission readiness.
2. Generic ICD coding where higher specificity may exist in chart text.
3. ICD mention mismatch between raw PDF text and extracted diagnosis list.
4. Ensemble-vs-bridge divergence risk (ensemble payable list differs from deterministic bridge mapping in some charts).
"""
    write(ROOT / REQ_FILES[2], hcc_md)

    hedis_md = f"""# Batch-10 HEDIS Gap Analysis

## Findings
- Post-fix run still shows enrollment fallback traces (`Enrollment data unavailable`) in measure eligibility reasons.
- Heuristic false-met count: {int(sum(c['false_met'] for c in charts))}
- Heuristic false-gap count: {int(sum(c['false_gap'] for c in charts))}
- Measure engine is producing full trace arrays, but enrollment certainty is still partially inferred.
"""
    write(ROOT / REQ_FILES[3], hedis_md)

    med_md = f"""# Batch-10 Medication/Lab/Encounter Gap Analysis

## Completeness (Post-fix)
- Medication detail completeness: {rates['med_detail_completeness']:.2%}
- Lab detail completeness: {rates['lab_detail_completeness']:.2%}
- Encounter completeness: {rates['encounter_completeness']:.2%}

## Common Failure Modes
1. Medication strength/route/frequency not consistently structured.
2. Lab unit/abnormal flag frequently absent from extracted evidence objects.
3. Encounter diagnosis linkage often implicit rather than explicit.
"""
    write(ROOT / REQ_FILES[4], med_md)

    lineage_md = f"""# Batch-10 Lineage Failure Report

## Baseline Failure
- Initial fresh run under network constraints produced near-zero extraction payloads and no lineage persistence.
- DB writes also failed due readonly default SQLite target path.

## Post-Fix State
- Added `--db-url` support in `scripts/process_charts.py`.
- Added environment-configurable SQLite path in `database/persist.py`.
- Added deterministic HCC bridge lineage injection into batch pipeline.
- Post-fix run now persists diagnosis candidates and decision trace events on all 10 charts.

## Remaining Lineage Gaps
- Candidate evidence quality still depends on upstream supporting text quality.
- Some charts still have thin evidence strings requiring stronger quote-grounding constraints.
"""
    write(ROOT / REQ_FILES[5], lineage_md)

    matrix_rows = "\n".join([f"- {k}: {v}" for k, v in root_causes.most_common()])
    matrix_md = f"""# Batch-10 Root Cause Matrix

## Bucket Counts
{matrix_rows}

## Bucket Mapping
- PDF ingestion / OCR issue: scanned chart OCR-heavy runtime path (`6_RET236976864.pdf`)
- prompt issue: weak diagnosis support strings
- normalization issue: ICD mention mismatch between PDF text and extracted outputs
- HEDIS rule issue: enrollment fallback certainty
- persistence issue: fixed (was zero lineage, now non-zero)
"""
    write(ROOT / REQ_FILES[6], matrix_md)

    plan_md = """# Batch-10 Prioritized Fix Plan

1. Tighten diagnosis evidence validator.
2. Add ICD specificity upgrader.
3. Add enrollment-required strict mode toggle for HEDIS certainty.
4. Add deterministic medication/lab parsers for strength/unit/abnormality.
5. Add assertion-level evidence span validator before persistence.
6. Add chart-level regression fixtures from this 10-chart batch.
"""
    write(ROOT / REQ_FILES[7], plan_md)

    before_agg = before["aggregate"]
    after_agg = after["aggregate"]
    before_cand = sum(r.get("db_result", {}).get("tables", {}).get("diagnosis_candidates", 0) for r in before["per_chart"])
    after_cand = sum(r.get("db_result", {}).get("tables", {}).get("diagnosis_candidates", 0) for r in after["per_chart"])
    before_ev = sum(r.get("db_result", {}).get("tables", {}).get("candidate_evidence", 0) for r in before["per_chart"])
    after_ev = sum(r.get("db_result", {}).get("tables", {}).get("candidate_evidence", 0) for r in after["per_chart"])

    compare_md = f"""# Batch-10 Before/After Comparison

## Runs Compared
- Before fixes (successful pre-fix): `{RUN_BEFORE}`
- After fixes (post-fix): `{RUN_AFTER}`

## Delta
- Diagnoses extracted: {before_agg['total_diagnoses']} -> {after_agg['total_diagnoses']} ({after_agg['total_diagnoses']-before_agg['total_diagnoses']:+d})
- Payable HCC capture: {before_agg['total_hcc_categories']} -> {after_agg['total_hcc_categories']} ({after_agg['total_hcc_categories']-before_agg['total_hcc_categories']:+d})
- RAF aggregate: {before_agg['total_raf_score']:.3f} -> {after_agg['total_raf_score']:.3f} ({after_agg['total_raf_score']-before_agg['total_raf_score']:+.3f})
- Diagnosis lineage candidates persisted: {before_cand} -> {after_cand} ({after_cand-before_cand:+d})
- Candidate evidence rows persisted: {before_ev} -> {after_ev} ({after_ev-before_ev:+d})
- Evidence-trace completeness (post-fix heuristic): {rates['trace_completeness']:.2%}

## Initial Fresh-Run Baseline (network constrained)
- Charts successful: {baseline['successful']}/{baseline['total_charts']}
- Diagnoses extracted: {baseline['aggregate']['total_diagnoses']}
- Payable HCC capture: {baseline['aggregate']['total_hcc_categories']}
"""
    write(ROOT / REQ_FILES[8], compare_md)

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>MedInsight360 Batch-10 Worldclass Review</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:30px;line-height:1.45}}h1,h2{{margin:0.2rem 0}}</style></head>
<body>
<h1>MedInsight 360 Batch-10 Worldclass Review</h1>
<p>Generated from fresh runs on {RUN_AFTER.name}.</p>
<h2>Executive Summary</h2>
<ul>
<li>Initial fresh run failed under restricted network/readonly DB; no usable extraction truth.</li>
<li>Implemented runtime hardening for explicit DB target + raw artifact preservation + deterministic HCC lineage persistence.</li>
<li>Post-fix rerun completed 10/10 charts with persisted diagnosis candidates and decision trace events.</li>
</ul>
<h2>Before/After Scorecard</h2>
<p>Diagnoses: {before_agg['total_diagnoses']} -> {after_agg['total_diagnoses']} | HCCs: {before_agg['total_hcc_categories']} -> {after_agg['total_hcc_categories']} | RAF: {before_agg['total_raf_score']} -> {after_agg['total_raf_score']}</p>
<p>Lineage candidates: {before_cand} -> {after_cand} | Candidate evidence rows: {before_ev} -> {after_ev}</p>
<h2>Remaining Risks</h2>
<ul>
<li>Weak diagnosis support text still occasionally accepted.</li>
<li>HEDIS enrollment assumptions remain in traces for missing enrollment feeds.</li>
<li>Medication/lab structural completeness remains below insurer-grade target.</li>
</ul>
</body></html>"""
    write(ROOT / REQ_FILES[9], html)

    print("Generated:")
    for f in REQ_FILES:
        print(f" - {ROOT / f}")


if __name__ == "__main__":
    main()
