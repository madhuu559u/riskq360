from __future__ import annotations

from scripts.process_charts import (
    TOP_25_HEDIS_MEASURE_IDS,
    _build_chunk_map,
    _run_hedis_engine,
    _sanitize_hedis_extraction_payload,
    convert_to_assertions,
)


def test_build_chunk_map_covers_text_ranges() -> None:
    text = "A" * 12050 + "\n\n" + "B" * 250
    chunk_map = _build_chunk_map(text, chunk_size=6000)

    assert len(chunk_map) >= 2
    assert chunk_map[0]["start_char"] == 0
    assert chunk_map[-1]["end_char"] <= len(text)
    for entry in chunk_map:
        assert entry["length"] > 0
        assert entry["start_char"] <= entry["end_char"]
        assert isinstance(entry["preview"], str)


def test_convert_to_assertions_preserves_evidence_fields() -> None:
    extraction_results = {
        "risk": {
            "diagnoses": [
                {
                    "icd10_code": "E11.9",
                    "description": "Type 2 diabetes mellitus without complications",
                    "negation_status": "active",
                    "supporting_text": "Diabetes listed in assessment.",
                    "date_of_service": "2025-01-01",
                    "page_number": 3,
                }
            ]
        },
        "hedis": {
            "blood_pressure_readings": [
                {"systolic": 130, "diastolic": 80, "date": "2025-02-01", "evidence": "BP 130/80", "page_number": 5}
            ],
            "lab_results": [
                {"test_name": "HbA1c", "result_value": "7.2%", "result_date": "2025-02-01", "evidence": "A1c 7.2%", "page_number": 6}
            ],
            "screenings": [
                {"screening_type": "Mammogram", "result": "Completed", "date": "2025-03-01", "evidence": "Mammogram done", "page_number": 7}
            ],
        },
        "encounters": {
            "encounters": [
                {
                    "type": "Office",
                    "date": "2025-01-10",
                    "provider": "Dr. X",
                    "page_number": 2,
                    "evidence": "Office follow-up",
                    "medications": [
                        {"name": "Metformin", "instructions": "500 mg BID", "page_number": 2, "evidence": "Metformin 500 mg BID"}
                    ],
                }
            ]
        },
        "demographics": {},
        "sentences": {"sentences": []},
    }

    assertions = convert_to_assertions(extraction_results, hcc_data={})
    dx = next(a for a in assertions if a["category"] == "diagnosis")
    bp = next(a for a in assertions if a["assertion_id"].startswith("hedis_bp_"))
    med = next(a for a in assertions if a["category"] == "medication")

    assert dx["exact_quote"] == "Diabetes listed in assessment."
    assert dx["page_number"] == 3
    assert bp["exact_quote"] == "BP 130/80"
    assert bp["page_number"] == 5
    assert med["exact_quote"] == "Metformin 500 mg BID"
    assert med["page_number"] == 2


def test_top25_hedis_profile_has_exactly_25_unique_ids() -> None:
    assert len(TOP_25_HEDIS_MEASURE_IDS) == 25
    assert len(set(TOP_25_HEDIS_MEASURE_IDS)) == 25


def test_convert_to_assertions_filters_implausible_bp_values() -> None:
    extraction_results = {
        "hedis": {
            "blood_pressure_readings": [
                {"systolic": 24, "diastolic": 25, "date": "09/20/1947", "evidence": "7/24/25, 10:46 AM", "page_number": 1},
                {"systolic": 138, "diastolic": 83, "date": "09/20/1947", "evidence": "138/83 mmHg", "page_number": 1},
            ]
        }
    }
    assertions = convert_to_assertions(extraction_results, hcc_data={})
    bp_assertions = [a for a in assertions if a.get("assertion_id", "").startswith("hedis_bp_")]
    assert len(bp_assertions) == 1
    bp = bp_assertions[0]
    assert bp["structured"]["bp_systolic"] == 138
    assert bp["structured"]["bp_diastolic"] == 83
    # DOB-like date should be scrubbed when not a plausible event date.
    assert bp.get("effective_date") in (None, "2025-07-24")


def test_sanitize_hedis_extraction_payload_drops_bp_noise() -> None:
    payload = {
        "blood_pressure_readings": [
            {"systolic": 9, "diastolic": 20, "date": "09/20/1947", "evidence": "09/20/1947", "page_number": 1},
            {"systolic": 138, "diastolic": 83, "date": "09/20/1947", "evidence": "138/83 mmHg", "page_number": 1},
        ],
        "lab_results": [],
        "screenings": [],
    }
    sanitized = _sanitize_hedis_extraction_payload(payload, measurement_year=2026)
    bp = sanitized.get("blood_pressure_readings", [])
    assert len(bp) == 1
    assert bp[0]["systolic"] == 138
    assert bp[0]["diastolic"] == 83
    assert bp[0]["date"] is None


def test_run_hedis_engine_marks_non_profile_measures_inactive() -> None:
    extraction_results = {
        "demographics": {"dob": "1980-01-01", "gender": "female"},
        "hedis": {},
        "risk": {"diagnoses": []},
        "encounters": {"encounters": []},
    }
    assertions = []

    hedis_data = _run_hedis_engine(
        extraction_results=extraction_results,
        assertions=assertions,
        pdf_name="sample.pdf",
        measurement_year=2026,
    )

    profile = hedis_data.get("measure_profile", {})
    assert len(profile.get("active_measure_ids", [])) == 25
    assert len(profile.get("inactive_measure_ids", [])) > 0

    measures = hedis_data.get("measures", [])
    inactive = [m for m in measures if m.get("status") == "inactive"]
    assert inactive, "Expected non-top25 measures to be emitted as inactive"

    active = [m for m in measures if m.get("status") != "inactive"]
    assert all("decision_reasoning" in m for m in active)
    assert all(m.get("id") == m.get("measure_id") for m in active)
    assert any("clinical_only_preview" in m for m in active)


def test_run_hedis_engine_adds_cbp_denominator_signal_without_icd() -> None:
    extraction_results = {
        "demographics": {
            "dob": "1970-01-01",
            "gender": "male",
            "enrollment_periods": [{"start_date": "2026-01-01", "end_date": "2026-12-31", "source": "test"}],
        },
        "hedis": {},
        "risk": {"diagnoses": []},
        "encounters": {"encounters": []},
    }
    assertions = [
        {
            "category": "vital_sign",
            "concept": "BP",
            "text": "Blood pressure 152/96",
            "exact_quote": "BP 152/96",
            "page_number": 2,
            "effective_date": "2026-03-01",
            "structured": {"bp_systolic": 152, "bp_diastolic": 96},
        },
        {
            "category": "vital_sign",
            "concept": "BP",
            "text": "Blood pressure 148/94",
            "exact_quote": "BP 148/94",
            "page_number": 3,
            "effective_date": "2026-04-01",
            "structured": {"bp_systolic": 148, "bp_diastolic": 94},
        },
        {
            "category": "medication",
            "concept": "Losartan",
            "text": "Continue losartan 50 mg daily",
            "exact_quote": "Losartan 50 mg daily",
            "page_number": 4,
            "effective_date": "2026-04-01",
        },
    ]

    hedis_data = _run_hedis_engine(
        extraction_results=extraction_results,
        assertions=assertions,
        pdf_name="signal_test.pdf",
        measurement_year=2026,
    )
    cbp = next(m for m in hedis_data.get("measures", []) if m.get("measure_id") == "CBP")
    assert cbp.get("denominator_signal", {}).get("suspected_denominator") is True
    preview = cbp.get("clinical_only_preview", {})
    assert preview.get("status") == "indeterminate"
    assert preview.get("applicable") is True


def test_run_hedis_engine_humanizes_gap_descriptions_and_includes_rule_snapshot() -> None:
    extraction_results = {
        "demographics": {
            "dob": "1966-01-01",
            "gender": "female",
            "enrollment_periods": [{"start_date": "2026-01-01", "end_date": "2026-12-31"}],
        },
        "hedis": {},
        "risk": {"diagnoses": []},
        "encounters": {"encounters": []},
    }
    assertions: list[dict[str, object]] = []

    hedis_data = _run_hedis_engine(
        extraction_results=extraction_results,
        assertions=assertions,
        pdf_name="gap_humanization_test.pdf",
        measurement_year=2026,
        active_measure_ids_override=["COL"],
    )
    col = next(m for m in hedis_data.get("measures", []) if m.get("measure_id") == "COL")
    assert col.get("status") in {"gap", "indeterminate"}
    assert isinstance(col.get("measure_definition"), dict)
    assert isinstance(col["measure_definition"].get("denominator_rules"), list)
    gaps = col.get("gaps", []) or col.get("clinical_only_preview", {}).get("gaps", [])
    assert gaps, "COL should have a gap when no screening evidence exists"
    assert any(g.get("actionable_reason") for g in gaps if isinstance(g, dict))
    assert all("VS_" not in str(g.get("description", "")) for g in gaps if isinstance(g, dict))
