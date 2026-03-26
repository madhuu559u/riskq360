from __future__ import annotations

from types import SimpleNamespace

from services.assertion_service import AssertionService


def _mk_assertion(*, concept: str, quote: str):
    return SimpleNamespace(
        id=1,
        chart_id=1,
        assertion_id="lab_1",
        category="lab_result",
        concept=concept,
        canonical_concept=concept,
        text=quote,
        clean_text=quote,
        status="active",
        subject="patient",
        evidence_rank=1,
        page_number=1,
        exact_quote=quote,
        char_start=None,
        char_end=None,
        icd_codes=None,
        icd_codes_primary=None,
        codes=None,
        effective_date="2025-01-01",
        structured={},
        medication_normalized=None,
        is_hcc_candidate=False,
        is_payable_ra_candidate=False,
        is_hedis_evidence=True,
        review_status="pending",
        condition_group_id_v3=None,
    )


def test_serialize_lab_prefers_a1c_value_over_unrelated_number() -> None:
    svc = AssertionService(session=None)  # type: ignore[arg-type]
    a = _mk_assertion(
        concept="HbA1c",
        quote="The following results are abnormal ldl 103 A1C 5.7% no dm",
    )
    lab = svc._serialize_lab(a)
    assert lab["test_name"] == "HbA1c"
    assert str(lab["value"]) == "5.7"
    assert lab["unit"] == "%"


def test_serialize_lab_extracts_egfr_with_unit() -> None:
    svc = AssertionService(session=None)  # type: ignore[arg-type]
    a = _mk_assertion(concept="eGFR", quote="eGFR 53 mL/min (Abnormal)")
    lab = svc._serialize_lab(a)
    assert lab["test_name"] == "eGFR"
    assert str(lab["value"]) == "53"
    assert str(lab["unit"]).lower() == "ml/min"
