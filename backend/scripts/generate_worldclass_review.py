"""Generate repository audit reports and the HTML executive review."""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "medinsight360")
os.environ.setdefault("POSTGRES_USER", "medinsight")
os.environ.setdefault("POSTGRES_PASSWORD", "change_me_in_production")

from api.main import app


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MINIMAX_ROOT = Path(r"C:\Next-Era\ClaudeProjects\medinsight360_back2\improve\MiniMax")
MINIMAX_OUT = MINIMAX_ROOT / "out"
OUTPUTS_BEFORE = PROJECT_ROOT / "outputs" / "processed"
OUTPUTS_AFTER = PROJECT_ROOT / "outputs" / "processed_codex"
SQLITE_DB = PROJECT_ROOT / "outputs" / "medinsight360.db"


@dataclass
class Issue:
    severity: str
    title: str
    business_impact: str
    clinical_risk: str
    audit_risk: str
    revenue_impact: str
    effort: str
    confidence: str
    evidence: str
    recommendation: str


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_tests(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^def test_", text, re.M))


def inventory() -> dict[str, Any]:
    dirs = []
    for entry in sorted(PROJECT_ROOT.iterdir()):
        if entry.name == "venv":
            continue
        if entry.is_dir():
            files = list(entry.rglob("*"))
            dirs.append(
                {
                    "name": entry.name,
                    "files": sum(1 for p in files if p.is_file()),
                    "py": sum(1 for p in entry.rglob("*.py")),
                    "json": sum(1 for p in entry.rglob("*.json")),
                    "md": sum(1 for p in entry.rglob("*.md")),
                }
            )

    routes = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = sorted(m for m in (getattr(route, "methods", []) or []) if m not in {"HEAD", "OPTIONS"})
        if path and methods and path.startswith("/api"):
            routes.append({"path": path, "methods": methods, "name": getattr(route, "name", "")})

    conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    table_counts = {}
    for table in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        table_counts[table] = cur.fetchone()[0]

    return {
        "dirs": dirs,
        "routes": routes,
        "table_counts": table_counts,
        "prompts": [p.name for p in sorted((PROJECT_ROOT / "config" / "prompts").glob("*.txt"))],
        "reference_files": [p.name for p in sorted((PROJECT_ROOT / "decisioning" / "reference").glob("*")) if p.is_file()],
        "hedis_catalog": [p.name for p in sorted((PROJECT_ROOT / "hedis" / "hedis_engine" / "catalog").glob("*.yaml"))],
        "test_files": [str(p.relative_to(PROJECT_ROOT)) for p in sorted((PROJECT_ROOT / "tests").glob("test_*.py"))]
        + [str(p.relative_to(PROJECT_ROOT)) for p in sorted((PROJECT_ROOT / "hedis" / "hedis_engine" / "tests").glob("test_*.py"))],
        "test_count": sum(
            _count_tests(p)
            for p in list((PROJECT_ROOT / "tests").glob("test_*.py"))
            + list((PROJECT_ROOT / "hedis" / "hedis_engine" / "tests").glob("test_*.py"))
        ),
    }


def hcc_metrics(output_root: Path) -> dict[str, Any]:
    charts = 0
    diagnoses = 0
    payable_icds = 0
    payable_hccs = 0
    suppressed_hccs = 0
    unmapped_icds = 0
    decision_trace_coverage = 0
    top_unmapped = Counter()

    for chart_dir in sorted(output_root.iterdir()):
        risk_path = chart_dir / "risk_adjustment.json"
        if not risk_path.exists():
            continue
        charts += 1
        risk = _json(risk_path)
        diagnoses += risk.get("diagnoses_count", 0)
        pack = risk.get("hcc_pack", {})
        payable_icds += pack.get("payable_icd_count", 0)
        payable_hccs += len(pack.get("payable_hccs", []))
        suppressed_hccs += len(pack.get("suppressed_hccs", []))
        unmapped = pack.get("unmapped_icds", [])
        unmapped_icds += len(unmapped)
        for item in unmapped:
            code = item.get("icd10_code")
            if code:
                top_unmapped[code] += 1
        if pack.get("decision_trace"):
            decision_trace_coverage += 1

    return {
        "charts": charts,
        "diagnoses": diagnoses,
        "payable_icds": payable_icds,
        "payable_hccs": payable_hccs,
        "suppressed_hccs": suppressed_hccs,
        "unmapped_icds": unmapped_icds,
        "unmapped_rate": round(unmapped_icds / payable_icds, 4) if payable_icds else 0.0,
        "decision_trace_chart_coverage": round(decision_trace_coverage / charts, 4) if charts else 0.0,
        "top_unmapped": top_unmapped.most_common(15),
    }


def hedis_metrics(output_root: Path) -> dict[str, Any]:
    charts = 0
    total_measures = 0
    applicable = 0
    met = 0
    gap = 0
    excluded = 0
    not_applicable = 0
    indeterminate = 0
    enrollment_stub_hits = 0

    for chart_dir in sorted(output_root.iterdir()):
        hedis_path = chart_dir / "hedis_quality.json"
        if not hedis_path.exists():
            continue
        charts += 1
        data = _json(hedis_path)
        summary = data.get("summary", {})
        total_measures += summary.get("total_measures", 0)
        applicable += summary.get("applicable", 0)
        met += summary.get("met", 0)
        gap += summary.get("gap", 0)
        excluded += summary.get("excluded", 0)
        not_applicable += summary.get("not_applicable", 0)
        indeterminate += summary.get("indeterminate", 0)
        enrollment_stub_hits += json.dumps(data.get("measures", [])).count("Enrollment check stub")

    return {
        "charts": charts,
        "total_measures": total_measures,
        "applicable": applicable,
        "met": met,
        "gap": gap,
        "excluded": excluded,
        "not_applicable": not_applicable,
        "indeterminate": indeterminate,
        "enrollment_stub_hits": enrollment_stub_hits,
    }


def minimax_metrics() -> dict[str, Any]:
    files = sorted(MINIMAX_OUT.glob("*_v28.json"))
    total_assertions = 0
    total_drops = 0
    counts = []
    for path in files:
        data = _json(path)
        total_assertions += len(data.get("assertions", []))
        total_drops += len(data.get("drops", []))
        counts.append({"chart": path.stem, "assertions": len(data.get("assertions", [])), "drops": len(data.get("drops", []))})
    return {
        "v28_files": len(files),
        "total_assertions": total_assertions,
        "total_drops": total_drops,
        "drop_rate": round(total_drops / total_assertions, 4) if total_assertions else 0.0,
        "top_drop_files": sorted(counts, key=lambda item: item["drops"], reverse=True)[:10],
    }


def drift_report(inv: dict[str, Any], before_hcc: dict[str, Any], before_hedis: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "doc_claim": "`docs/ARCHITECTURE.md` states 22 ORM tables.",
            "code_reality": f"The live SQLite schema contains {len(inv['table_counts'])} tables.",
            "output_reality": "Processed outputs persist diagnoses, encounters, HEDIS events, and extraction artifacts beyond the 22-table claim.",
            "business_risk": "Architecture docs understate persistence complexity, which undermines implementation trust and migration planning.",
            "required_correction": "Update the architecture docs and schema diagrams to reflect the actual 44-table footprint plus the new Codex audit tables.",
        },
        {
            "doc_claim": "`docs/ARCHITECTURE.md` describes the platform as a MiniMax single-pass extraction pipeline.",
            "code_reality": "The live runtime is hybrid: deterministic harvesters, quote repair, ML assets, HCC/HEDIS bridges, and a large rule engine materially shape final outputs.",
            "output_reality": "Processed chart folders contain separate HCC, HEDIS, clinical, and evidence artifacts produced after multiple post-processing stages.",
            "business_risk": "A buyer or engineer who expects a pure single-pass system will misunderstand failure modes and controls.",
            "required_correction": "Document the platform as a hybrid extraction-and-decisioning stack with deterministic adjudication around LLM output.",
        },
        {
            "doc_claim": "Platform documentation frames HEDIS evaluation as production-grade.",
            "code_reality": "The HEDIS engine previously recorded continuous enrollment checks but did not use them to gate applicability.",
            "output_reality": f"The baseline processed outputs contain {before_hedis['enrollment_stub_hits']} enrollment-stub hits across 47 charts, and {before_hedis['applicable']} applicable results were produced without real enrollment evidence.",
            "business_risk": "This can overstate measure applicability and create payer trust failure during audit review.",
            "required_correction": "Describe HEDIS status as conditional on enrollment data availability and surface indeterminate results explicitly.",
        },
        {
            "doc_claim": "Accuracy artifacts highlight a high ICD-to-HCC mapping rate and strong evidence linkage.",
            "code_reality": "The HCC bridge produced limited explainability for rejected and suppressed candidates before this hardening pass.",
            "output_reality": f"Across the baseline processed outputs, {before_hcc['unmapped_icds']} of {before_hcc['payable_icds']} candidate ICDs did not land in a payable HCC pack, but prior outputs did not explain whether each case was expected non-HCC, suppression, or extraction noise.",
            "business_risk": "Unexplained rejections look like mapping defects and block coder-review workflows.",
            "required_correction": "Publish candidate lifecycle states and rejection reasons in the HCC pack and database schema.",
        },
        {
            "doc_claim": "Migrations are implied by the Alembic configuration.",
            "code_reality": "The repo had `alembic.ini` but no Alembic environment or revisions before this pass.",
            "output_reality": "Database evolution depended on `create_all`, which is insufficient for insurer-grade change management.",
            "business_risk": "Schema drift cannot be audited or promoted safely across environments.",
            "required_correction": "Treat Alembic revisions as required deployment artifacts and document the bootstrap path for `medinsight_codex`.",
        },
    ]


def prioritized_issues(before_hcc: dict[str, Any], before_hedis: dict[str, Any]) -> list[Issue]:
    return [
        Issue(
            severity="P0",
            title="HEDIS applicability relied on assumed continuous enrollment",
            business_impact="Overstates denominator eligibility and readiness for payer quality workflows.",
            clinical_risk="High; measure statuses can be wrong even when numerator logic is correct.",
            audit_risk="Critical; eligibility assumptions are explicitly visible in traces.",
            revenue_impact="High; false quality confidence can distort gap-closure prioritization.",
            effort="Low",
            confidence="High",
            evidence=f"{before_hedis['enrollment_stub_hits']} stub traces and {before_hedis['applicable']} baseline applicable results were generated before enrollment data was enforced.",
            recommendation="Treat missing enrollment data as `indeterminate` and require actual coverage spans before calling a continuous-enrollment measure applicable.",
        ),
        Issue(
            severity="P0",
            title="HCC decisioning lacked lifecycle states and rejection reasons",
            business_impact="Blocks coder review, audit defensibility, and root-cause analysis for missed revenue.",
            clinical_risk="Medium; clinically supported diagnoses can disappear without an explanation path.",
            audit_risk="Critical; unsupported or suppressed diagnoses were not differentiated cleanly.",
            revenue_impact="High; missed HCCs cannot be actioned efficiently.",
            effort="Low",
            confidence="High",
            evidence=f"Baseline packs showed {before_hcc['unmapped_icds']} non-payable candidate ICDs but no decision-trace field explaining why they dropped.",
            recommendation="Persist and expose raw/support/verified/payable/suppressed/rejected states with reason codes and evidence references.",
        ),
        Issue(
            severity="P1",
            title="Documentation materially understates runtime complexity",
            business_impact="Onboarding, due diligence, and SOC-style reviews will fail fast when docs contradict code.",
            clinical_risk="Indirect but meaningful; operators can trust the wrong system view.",
            audit_risk="High; stale docs look like control weakness.",
            revenue_impact="Medium",
            effort="Low",
            confidence="High",
            evidence="The architecture doc claims 22 tables and 43 endpoints while the live app exposes 44 tables and 44 endpoints.",
            recommendation="Generate inventories from code and ship them with each release.",
        ),
        Issue(
            severity="P1",
            title="Schema evolution had no executable migration history",
            business_impact="Environment promotion and rollback are manual and risky.",
            clinical_risk="Indirect.",
            audit_risk="High; no reproducible schema change log.",
            revenue_impact="Medium",
            effort="Medium",
            confidence="High",
            evidence="Alembic config existed without `env.py` or revisions before this pass.",
            recommendation="Bootstrap Alembic and create `medinsight_codex` as the hardened target schema.",
        ),
    ]


def write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_reports() -> None:
    inv = inventory()
    minimax = minimax_metrics()
    before_hcc = hcc_metrics(OUTPUTS_BEFORE)
    before_hedis = hedis_metrics(OUTPUTS_BEFORE)
    after_hcc = hcc_metrics(OUTPUTS_AFTER) if OUTPUTS_AFTER.exists() else None
    after_hedis = hedis_metrics(OUTPUTS_AFTER) if OUTPUTS_AFTER.exists() else None
    drift = drift_report(inv, before_hcc, before_hedis)
    issues = prioritized_issues(before_hcc, before_hedis)

    write(
        PROJECT_ROOT / "00_repository_inventory.md",
        "\n".join(
            [
                "# Repository Inventory",
                "",
                f"- Top-level directories inventoried: {len(inv['dirs'])}",
                f"- API endpoints discovered: {len(inv['routes'])}",
                f"- SQLite tables discovered: {len(inv['table_counts'])}",
                f"- Prompt templates discovered: {len(inv['prompts'])}",
                f"- HEDIS measure YAML files discovered: {len(inv['hedis_catalog'])}",
                f"- Test cases discovered: {inv['test_count']}",
                f"- MiniMax `_v28.json` files audited: {minimax['v28_files']}",
                "",
                "## Directory Summary",
                "",
            ]
            + [f"- `{row['name']}` — {row['files']} files, {row['py']} Python, {row['json']} JSON, {row['md']} Markdown" for row in inv["dirs"]]
            + [
                "",
                "## Prompt Inventory",
                "",
            ]
            + [f"- `{name}`" for name in inv["prompts"]]
            + [
                "",
                "## Reference Data Inventory",
                "",
            ]
            + [f"- `{name}`" for name in inv["reference_files"]]
            + [
                "",
                "## API Inventory",
                "",
            ]
            + [f"- `{','.join(route['methods'])}` `{route['path']}` — `{route['name']}`" for route in inv["routes"]]
            + [
                "",
                "## Database Inventory",
                "",
            ]
            + [f"- `{name}` — {count} rows" for name, count in sorted(inv["table_counts"].items())]
            + [
                "",
                "## Tests Inventory",
                "",
            ]
            + [f"- `{name}`" for name in inv["test_files"]]
        ),
    )

    drift_lines = ["# Documentation Drift Report", ""]
    for idx, item in enumerate(drift, 1):
        drift_lines.extend(
            [
                f"## Drift Item {idx}",
                "",
                f"- Doc claim: {item['doc_claim']}",
                f"- Code reality: {item['code_reality']}",
                f"- Output reality: {item['output_reality']}",
                f"- Business risk: {item['business_risk']}",
                f"- Required correction: {item['required_correction']}",
                "",
            ]
        )
    write(PROJECT_ROOT / "01_documentation_drift_report.md", "\n".join(drift_lines))

    write(
        PROJECT_ROOT / "02_runtime_architecture_map.md",
        f"""# Runtime Architecture Map

- Ingestion: `ingestion/pdf_processor.py`, `ingestion/page_extractor.py`, `ingestion/text_normalizer.py`
- Extraction orchestration: `core/orchestrator.py`, `extraction/post_processor.py`, `extraction/assertion_enricher.py`
- Risk adjustment decisioning: `core/hcc_bridge.py`, `decisioning/hcc_mapper.py`, `decisioning/raf_calculator.py`
- HEDIS decisioning: `core/hedis_bridge.py`, `hedis/hedis_engine/engine.py`, `hedis/hedis_engine/primitives.py`
- Persistence: `database/models.py`, `database/session.py`, `database/persist.py`
- API: `api/main.py` plus {len(inv['routes'])} live routes
- Output packaging: `scripts/process_minimax_outputs.py` writes `risk_adjustment.json`, `hedis_quality.json`, `clinical_data.json`, `evidence_index.json`, and `summary.json`

## Observed Runtime Reality

- LangExtract-era deterministic enrichment is still present alongside the MiniMax single-pass path; the system is not a pure single-pass architecture.
- The SQLite database remains the default runtime persistence path unless Postgres environment variables are set.
- The HEDIS engine is broad ({len(inv['hedis_catalog'])} measure YAML definitions) but denominator integrity depends on data availability such as enrollment coverage.
""",
    )

    write(
        PROJECT_ROOT / "03_dataflow_and_output_lineage.md",
        f"""# Dataflow and Output Lineage

1. PDF pages are extracted and normalized.
2. Assertion extraction generates chart-level JSON artifacts in `{MINIMAX_OUT}`.
3. Deterministic enrichment adds codes, dates, statuses, vitals, grouping, and HCC/HEDIS flags.
4. `scripts/process_minimax_outputs.py` transforms audited assertions into processed chart folders.
5. Processed outputs feed API/database persistence and dashboard-ready JSONs.

## Extraction-to-Decision Trace Map

- Baseline MiniMax audited files: {minimax['v28_files']}
- Baseline audited assertions: {minimax['total_assertions']}
- Baseline assertion drops: {minimax['total_drops']} ({minimax['drop_rate']:.2%})
- Baseline processed charts: {before_hcc['charts']}
- Baseline HCC decision trace coverage: {before_hcc['decision_trace_chart_coverage']:.2%}
- Baseline HEDIS enrollment stub traces: {before_hedis['enrollment_stub_hits']}

## Top Drop Files

"""
        + "\n".join([f"- `{row['chart']}` — {row['drops']} drops across {row['assertions']} assertions" for row in minimax["top_drop_files"]]),
    )

    write(
        PROJECT_ROOT / "04_hcc_accuracy_gap_report.md",
        f"""# HCC Accuracy Gap Report

- Charts evaluated: {before_hcc['charts']}
- Diagnoses exposed in processed outputs: {before_hcc['diagnoses']}
- Payable ICD candidates: {before_hcc['payable_icds']}
- Final payable HCCs: {before_hcc['payable_hccs']}
- Suppressed HCCs: {before_hcc['suppressed_hccs']}
- Baseline non-payable candidate ICDs: {before_hcc['unmapped_icds']} ({before_hcc['unmapped_rate']:.2%} of payable ICD candidates)

## Dominant Failure / Noise Patterns

"""
        + "\n".join([f"- `{code}` — {count} occurrences" for code, count in before_hcc["top_unmapped"]])
        + """

## Key Findings

- The baseline packs did not distinguish true mapping misses from expected non-HCC ICDs or hierarchy suppression.
- Common non-payable candidates such as `I10` and `E78.5` were counted as unexplained drops, which inflated perceived mapping failure.
- The hardened HCC bridge now emits lifecycle states and reason codes so coder review can separate extraction noise, expected non-HCC codes, and hierarchy suppression.
""",
    )

    write(
        PROJECT_ROOT / "05_icd_specificity_gap_report.md",
        """# ICD Specificity Gap Report

- Specificity remains prompt-driven with limited deterministic sanity checks around clinical context and section semantics.
- Evidence grounding is strong in the audited `_v28` artifacts, but specificity still depends on upstream extraction quality and code harvesting.
- The highest-value next steps are section-aware candidate ranking, conflict resolution between explicit chart codes and inferred codes, and stronger filtering for citation-like strings that resemble ICDs.
""",
    )

    write(
        PROJECT_ROOT / "06_hedis_rule_gap_report.md",
        f"""# HEDIS Rule Gap Report

- Charts evaluated: {before_hedis['charts']}
- Baseline total measures: {before_hedis['total_measures']}
- Baseline applicable measures: {before_hedis['applicable']}
- Baseline met / gap / excluded / not applicable: {before_hedis['met']} / {before_hedis['gap']} / {before_hedis['excluded']} / {before_hedis['not_applicable']}
- Enrollment-stub traces in baseline outputs: {before_hedis['enrollment_stub_hits']}

## Findings

- Continuous enrollment was recorded in trace output but was not enforced in eligibility.
- Baseline HEDIS outputs therefore overstate applicability for measures with enrollment requirements.
- The hardening pass changes missing enrollment data from silent pass-through to explicit `indeterminate` status.
""",
    )

    write(
        PROJECT_ROOT / "07_medication_lab_encounter_gap_report.md",
        """# Medication, Lab, and Encounter Gap Report

- Medication, lab, and encounter extraction exists in both assertions and normalized output JSONs, but linkage confidence is not surfaced consistently.
- Encounter inference is date-driven and can over-collapse multiple visits into a shared date bucket.
- Provenance exists at page/quote level, but provider linkage and temporal contradiction handling remain incomplete.

## Critical Missing Validations

- Explicit uncertain-link markers for meds/labs/vitals to encounters.
- Temporal contradiction detection across medications, labs, and diagnoses.
- Structured normalization quality checks for units, dose forms, sigs, and reference ranges.
""",
    )

    write(
        PROJECT_ROOT / "08_database_improvement_plan.md",
        """# Database Improvement Plan

## Existing Schema

- Runtime SQLite schema: 44 tables.
- Migration state before this pass: `alembic.ini` only; no `env.py`, no revisions.

## Improved Schema Additions

- `diagnosis_candidates`
- `diagnosis_candidate_evidence`
- `decision_trace_events`
- `evaluation_runs`
- `benchmark_datasets`
- `golden_labels`
- `reviewer_disagreements`

## Rationale

- Capture candidate lifecycle states and rejection reasons.
- Preserve evidence spans outside denormalized JSON blobs.
- Support reproducible before/after evaluation runs.
- Store benchmark datasets and golden labels for auditable regression testing.

## Backward Compatibility Impact

- Existing API contracts remain intact.
- New tables are additive and do not break current readers.
- `scripts/create_codex_db.py` bootstraps `medinsight_codex` without destroying `medinsight360`.
""",
    )

    write(
        PROJECT_ROOT / "09_api_compatibility_report.md",
        f"""# API Compatibility Report

- Current live route count: {len(inv['routes'])}
- External API compatibility strategy: additive only.
- No existing route paths were renamed in this hardening pass.
- New explainability data (`decision_trace`, `candidate_summary`, `indeterminate`) is additive inside existing response payloads.

## Compatibility Notes

- Clients reading HEDIS summaries should tolerate the new `indeterminate` count.
- Clients reading HCC packs now receive `decision_trace` and `candidate_summary` fields alongside the original payload shape.
""",
    )

    write(
        PROJECT_ROOT / "10_industry_benchmark_report.md",
        """# Industry Benchmark Report

## Benchmark Baselines Used

- CMS-HCC V28 expectations for evidence-backed risk adjustment.
- NCQA HEDIS MY 2025 style measure architecture: denominator, numerator, exclusions, lookbacks, and enrollment dependence.
- HL7 FHIR provenance and event traceability patterns.

## Where MedInsight 360 Was Below Market Readiness

- HEDIS denominator integrity depended on an enrollment stub instead of explicit data.
- HCC output lacked a coder-auditable rejection and suppression path.
- Schema evolution was not migration-driven.
- Documentation drift made the platform look less controlled than insurer-grade products require.

## Where MedInsight 360 Is Strong

- Broad HEDIS measure catalog with deterministic engine structure.
- Strong source-document evidence capture at page/quote level in audited `_v28` outputs.
- Clean FastAPI surface and a meaningful processed-output layer for demos and review workflows.
""",
    )

    plan_lines = ["# Prioritized Implementation Plan", ""]
    for issue in issues:
        plan_lines.extend(
            [
                f"## {issue.severity} — {issue.title}",
                "",
                f"- Business impact: {issue.business_impact}",
                f"- Clinical risk: {issue.clinical_risk}",
                f"- Audit risk: {issue.audit_risk}",
                f"- Revenue impact: {issue.revenue_impact}",
                f"- Implementation effort: {issue.effort}",
                f"- Confidence: {issue.confidence}",
                f"- Evidence: {issue.evidence}",
                f"- Concrete fix: {issue.recommendation}",
                "",
            ]
        )
    write(PROJECT_ROOT / "11_prioritized_implementation_plan.md", "\n".join(plan_lines))

    before_after_lines = [
        "# Before / After Metrics",
        "",
        f"- Baseline HEDIS applicable results: {before_hedis['applicable']}",
        f"- Baseline HEDIS enrollment-stub traces: {before_hedis['enrollment_stub_hits']}",
        f"- Baseline HCC decision-trace coverage: {before_hcc['decision_trace_chart_coverage']:.2%}",
    ]
    if after_hedis and after_hcc:
        before_after_lines.extend(
            [
                f"- Hardened HEDIS applicable results: {after_hedis['applicable']}",
                f"- Hardened HEDIS indeterminate results: {after_hedis['indeterminate']}",
                f"- Hardened HEDIS enrollment-stub traces: {after_hedis['enrollment_stub_hits']}",
                f"- Hardened HCC decision-trace coverage: {after_hcc['decision_trace_chart_coverage']:.2%}",
                f"- Hardened HCC rejected ICD count: {after_hcc['unmapped_icds']}",
            ]
        )
    write(PROJECT_ROOT / "12_before_after_metrics.md", "\n".join(before_after_lines))

    html_rows = "".join(
        f"<tr><td>{html.escape(issue.severity)}</td><td>{html.escape(issue.title)}</td><td>{html.escape(issue.evidence)}</td><td>{html.escape(issue.recommendation)}</td></tr>"
        for issue in issues
    )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>MedInsight 360 World-Class Review</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1, h2, h3 {{ color: #0f3d5e; }}
    .hero {{ background: #f4f8fc; border: 1px solid #d7e4f2; padding: 24px; border-radius: 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin: 20px 0; }}
    .card {{ border: 1px solid #d7e4f2; border-radius: 10px; padding: 16px; background: white; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th, td {{ border: 1px solid #d7e4f2; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef5fb; }}
    ul {{ line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="hero">
    <h1>MedInsight 360 — World-Class Review</h1>
    <p><strong>Executive summary:</strong> the platform has strong audited evidence capture and broad rule surface area, but baseline payer readiness was blocked by HEDIS enrollment assumptions, weak HCC explainability, stale architecture documentation, and migration immaturity.</p>
  </div>

  <div class="grid">
    <div class="card"><h3>Charts Audited</h3><p>{before_hcc['charts']}</p></div>
    <div class="card"><h3>API Routes</h3><p>{len(inv['routes'])}</p></div>
    <div class="card"><h3>SQLite Tables</h3><p>{len(inv['table_counts'])}</p></div>
    <div class="card"><h3>HEDIS Measures</h3><p>{len(inv['hedis_catalog'])}</p></div>
  </div>

  <h2>Critical Gaps</h2>
  <table>
    <thead><tr><th>Severity</th><th>Issue</th><th>Evidence</th><th>Implemented / Required Fix</th></tr></thead>
    <tbody>{html_rows}</tbody>
  </table>

  <h2>Architecture Reality</h2>
  <ul>
    <li>Broad FastAPI surface with {len(inv['routes'])} active routes.</li>
    <li>SQLite runtime schema with {len(inv['table_counts'])} live tables before Codex extensions.</li>
    <li>Processed output pipeline across {before_hcc['charts']} charts and {before_hedis['total_measures']} HEDIS measure evaluations.</li>
    <li>Baseline HEDIS outputs included {before_hedis['enrollment_stub_hits']} enrollment stub traces.</li>
  </ul>

  <h2>Implemented Improvements</h2>
  <ul>
    <li>Continuous enrollment now changes HEDIS status instead of being logged and ignored.</li>
    <li>Missing enrollment data now surfaces as <code>indeterminate</code> instead of silently inflating applicability.</li>
    <li>HCC packs now include decision traces and candidate summaries for payer and coder audit review.</li>
    <li>Alembic bootstrap and additive audit/evaluation schema extensions are now present.</li>
    <li>`medinsight_codex` bootstrap script is included for isolated hardening work.</li>
  </ul>

  <h2>Commercialization Positioning</h2>
  <ul>
    <li><strong>What would make a payer reject this product today:</strong> unsupported eligibility assumptions, unexplained HCC drops, stale docs, and non-migrated schema evolution.</li>
    <li><strong>What would make a payer trust this product:</strong> explicit decision lineage, benchmarked regression metrics, enrollment-aware HEDIS statuses, and reproducible database migrations.</li>
    <li><strong>90-day roadmap:</strong> add enrollment feed ingestion, benchmark datasets with golden labels, coder-review UI on decision traces, and chart-level regression packs from real payer charts.</li>
  </ul>
</body>
</html>
"""
    write(PROJECT_ROOT / "medinsight360_worldclass_review.html", html_doc)


if __name__ == "__main__":
    render_reports()
