"""Regression tests for the HCC bridge audit trail."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.hcc_bridge import build_hcc_pack
from decisioning.hcc_mapper import HCCMapper


def _mapper() -> HCCMapper:
    return HCCMapper(PROJECT_ROOT / "decisioning" / "reference")


def test_hcc_pack_includes_decision_trace_and_candidate_summary() -> None:
    pack = build_hcc_pack(
        assertions=[
            {
                "assertion_id": 1,
                "category": "diagnosis",
                "concept": "Type 2 diabetes mellitus with hyperglycemia",
                "status": "active",
                "is_payable_ra_candidate": True,
                "icd_codes_primary": [{"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia"}],
                "page_number": 3,
                "exact_quote": "Type 2 diabetes mellitus with hyperglycemia (E11.65)",
                "effective_date": "2025-08-15",
            },
            {
                "assertion_id": 2,
                "category": "diagnosis",
                "concept": "Essential hypertension",
                "status": "active",
                "is_payable_ra_candidate": True,
                "icd_codes_primary": [{"code": "I10", "description": "Essential hypertension"}],
                "page_number": 4,
                "exact_quote": "Essential hypertension (I10)",
                "effective_date": "2025-08-15",
            },
            {
                "assertion_id": 3,
                "category": "diagnosis",
                "concept": "Administrative screening",
                "status": "active",
                "is_payable_ra_candidate": True,
                "icd_codes_primary": [{"code": "Z13.31", "description": "Encounter for depression screening"}],
                "page_number": 5,
                "exact_quote": "Screening for depression (Z13.31)",
                "effective_date": "2025-08-15",
            },
        ],
        hcc_mapper=_mapper(),
        chart_id="test_chart",
        measurement_year=2025,
    )

    assert "decision_trace" in pack
    assert "candidate_summary" in pack
    assert any(item["candidate_state"] == "payable_candidate" for item in pack["decision_trace"])
    assert any(item["reason_code"] == "no_hcc_mapping_in_v28" for item in pack["decision_trace"])
    assert any(item["reason_code"] == "administrative_z_code" for item in pack["decision_trace"])
    assert pack["candidate_summary"]["supported_candidate_count"] == 2

