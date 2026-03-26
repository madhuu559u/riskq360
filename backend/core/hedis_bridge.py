"""HEDIS Bridge — converts MiniMax assertions into HEDIS engine format.

Takes the assertion JSON output and feeds it through the HEDIS engine
(hedis.hedis_engine) to evaluate measures as met/gap/not-applicable.
All results include full evidence references (page numbers, exact quotes).
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


def _ensure_hedis_importable() -> None:
    """Ensure the hedis package is importable."""
    hedis_path = Path(__file__).resolve().parent.parent / "hedis"
    if str(hedis_path) not in sys.path:
        sys.path.insert(0, str(hedis_path))


def build_hedis_input(
    assertions: List[Dict[str, Any]],
    pdf_name: str = "",
    summary: Optional[Dict[str, Any]] = None,
    enrollment_periods: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build the input data structure expected by the HEDIS assertion_adapter.

    The adapter expects a dict with:
    - demographics: {dob, gender, ...}
    - assertions: list of assertion dicts
    - summary: dict (for DOB extraction)
    - meta: {pdf, ...}
    """
    dob = None
    gender = None

    if summary:
        dob_dates = summary.get("dob_dates_found", [])
        if dob_dates:
            dob = dob_dates[0]

    # Look for demographics in assertions themselves
    for a in assertions:
        concept = (a.get("concept") or "").lower()

        if "dob" in concept or "date of birth" in concept:
            if a.get("effective_date"):
                dob = dob or a["effective_date"]

        if "gender" in concept or "sex" in concept:
            text = (a.get("text") or "").lower()
            if "male" in text and "female" not in text:
                gender = "male"
            elif "female" in text:
                gender = "female"

    return {
        "demographics": {
            "dob": dob,
            "gender": gender,
        },
        "enrollment_periods": enrollment_periods or (summary or {}).get("enrollment_periods", []),
        "assertions": assertions,
        "summary": summary or {},
        "meta": {
            "pdf": pdf_name,
        },
    }


def _serialize_evidence(ev: Any) -> Dict[str, Any]:
    """Serialize an EvidenceUsed object with full source details."""
    d: Dict[str, Any] = {
        "type": getattr(ev, "event_type", "unknown"),
    }
    if getattr(ev, "code", ""):
        d["code"] = ev.code
    if getattr(ev, "code_system", ""):
        d["system"] = ev.code_system
    if getattr(ev, "value", None) is not None:
        d["value"] = ev.value
    if getattr(ev, "event_date", None):
        d["date"] = str(ev.event_date)

    # Full source reference with page numbers and exact quotes
    source = getattr(ev, "source", None)
    if source and isinstance(source, dict):
        d["source"] = source
        # Promote key fields for easy access
        if "page" in source:
            d["page_number"] = source["page"]
        if "exact_quote" in source:
            d["exact_quote"] = source["exact_quote"]
        if "pdf" in source:
            d["pdf"] = source["pdf"]
    return d


def _serialize_gap(g: Any) -> Dict[str, Any]:
    """Serialize a GapDetail with full info."""
    d: Dict[str, Any] = {
        "type": getattr(g, "gap_type", "unknown"),
        "description": getattr(g, "description", ""),
    }
    if getattr(g, "required_event", ""):
        d["required_event"] = g.required_event
    ws = getattr(g, "window_start", None)
    we = getattr(g, "window_end", None)
    if ws:
        d["window_start"] = str(ws)
    if we:
        d["window_end"] = str(we)
    if ws and we:
        d["window"] = f"{ws}..{we}"
    return d


def _serialize_trace(t: Any) -> Dict[str, Any]:
    """Serialize a TraceEntry."""
    d: Dict[str, Any] = {
        "rule": getattr(t, "rule", ""),
        "result": getattr(t, "result", False),
    }
    detail = getattr(t, "detail", "")
    if detail:
        d["detail"] = detail
    evidence = getattr(t, "evidence", [])
    if evidence:
        d["evidence"] = evidence
    return d


def evaluate_hedis_measures(
    assertions: List[Dict[str, Any]],
    measurement_year: int = 2025,
    pdf_name: str = "",
    summary: Optional[Dict[str, Any]] = None,
    dob: Optional[str] = None,
    gender: Optional[str] = None,
    measure_ids: Optional[List[str]] = None,
    enrollment_periods: Optional[List[Dict[str, Any]]] = None,
    require_enrollment_data: bool = True,
) -> Dict[str, Any]:
    """Evaluate HEDIS measures from MiniMax assertion output.

    Returns a dict with measure results including full evidence references
    (page numbers, exact quotes, char offsets) for every decision.
    """
    _ensure_hedis_importable()

    try:
        from hedis_engine.adapters.assertion_adapter import adapt_assertions
        from hedis_engine.engine import HedisEngine
        from hedis_engine.types import MemberEventStore
    except ImportError as e:
        log.warning("HEDIS engine not available: %s", e)
        return {
            "error": f"HEDIS engine import failed: {e}",
            "measures": [],
            "summary": {"total_measures": 0, "met": 0, "gap": 0, "not_applicable": 0},
        }

    # Build input data
    hedis_input = build_hedis_input(assertions, pdf_name, summary, enrollment_periods=enrollment_periods)

    # Override demographics if provided
    if dob:
        hedis_input["demographics"]["dob"] = dob
    if gender:
        hedis_input["demographics"]["gender"] = gender

    # Convert assertions to MemberEventStore via adapter
    try:
        store: MemberEventStore = adapt_assertions(hedis_input)
    except Exception as e:
        log.error("HEDIS adapter failed: %s", e)
        return {
            "error": f"HEDIS adapter failed: {e}",
            "measures": [],
            "summary": {"total_measures": 0, "met": 0, "gap": 0, "not_applicable": 0},
        }

    # Log store stats
    log.info(
        "HEDIS store: %d dx, %d procs, %d labs, %d vitals, %d meds, %d encounters, %d imm",
        len(store.diagnoses), len(store.procedures), len(store.labs),
        len(store.vitals), len(store.medications), len(store.encounters),
        len(store.immunizations),
    )

    # Run engine
    try:
        engine = HedisEngine(
            measurement_year=measurement_year,
            require_enrollment_data=require_enrollment_data,
        )
        results = engine.evaluate_member(store, measure_ids=measure_ids)
    except Exception as e:
        log.error("HEDIS engine evaluation failed: %s", e)
        return {
            "error": f"HEDIS evaluation failed: {e}",
            "measures": [],
            "summary": {"total_measures": 0, "met": 0, "gap": 0, "not_applicable": 0},
        }

    # Convert results to serializable format with full evidence
    measures_out: List[Dict[str, Any]] = []
    met_count = 0
    gap_count = 0
    na_count = 0
    excluded_count = 0
    indeterminate_count = 0

    for mr in results.measures:
        status = mr.status.value if hasattr(mr.status, "value") else str(mr.status)
        measure_dict: Dict[str, Any] = {
            "measure_id": mr.measure_id,
            "measure_name": mr.measure_name or mr.measure_id,
            "status": status,
            "applicable": mr.applicable,
            "compliant": status == "met",
            "confidence": mr.confidence,
            "eligibility_reason": mr.eligibility_reason,
            "compliance_reason": mr.compliance_reason,
        }

        if status == "met":
            met_count += 1
        elif status == "gap":
            gap_count += 1
        elif status == "excluded":
            excluded_count += 1
        elif status == "indeterminate":
            indeterminate_count += 1
        else:
            na_count += 1

        # Gaps with full details
        if mr.gaps:
            measure_dict["gaps"] = [_serialize_gap(g) for g in mr.gaps]

        # Evidence used with page numbers, exact quotes
        if mr.evidence_used:
            measure_dict["evidence_used"] = [_serialize_evidence(e) for e in mr.evidence_used]

        # Exclusion reason
        if mr.exclusion_reason:
            measure_dict["exclusion_reason"] = mr.exclusion_reason

        # Missing data
        if mr.missing_data:
            measure_dict["missing_data"] = mr.missing_data

        # Trace with evidence
        if mr.trace:
            measure_dict["trace"] = [_serialize_trace(t) for t in mr.trace]

        measures_out.append(measure_dict)

    # Sort: applicable measures first, then by status (met, gap, excluded, not_applicable)
    status_order = {"met": 0, "gap": 1, "excluded": 2, "indeterminate": 3, "not_applicable": 4}
    measures_out.sort(key=lambda m: (
        0 if m["applicable"] else 1,
        status_order.get(m["status"], 9),
        m["measure_id"],
    ))

    return {
        "measurement_year": measurement_year,
        "demographics": hedis_input["demographics"],
        "pdf": pdf_name,
        "measures": measures_out,
        "summary": {
            "total_measures": len(measures_out),
            "applicable": sum(1 for m in measures_out if m["applicable"]),
            "met": met_count,
            "gap": gap_count,
            "excluded": excluded_count,
            "indeterminate": indeterminate_count,
            "not_applicable": na_count,
        },
        "store_stats": {
            "diagnoses": len(store.diagnoses),
            "procedures": len(store.procedures),
            "labs": len(store.labs),
            "vitals": len(store.vitals),
            "medications": len(store.medications),
            "encounters": len(store.encounters),
            "immunizations": len(store.immunizations),
        },
    }
