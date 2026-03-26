"""Tests for enrollment-period ingestion in the assertion adapter."""

from datetime import date

from hedis_engine.adapters.assertion_adapter import adapt_assertions


def test_adapter_loads_enrollment_periods() -> None:
    store = adapt_assertions(
        {
            "demographics": {"dob": "1965-03-15", "gender": "female"},
            "enrollment_periods": [
                {"start_date": "2025-01-01", "end_date": "2025-12-31", "source": "eligibility_feed"}
            ],
            "assertions": [],
            "meta": {"pdf": "demo.pdf"},
        }
    )

    assert len(store.enrollment_periods) == 1
    assert store.enrollment_periods[0].start_date == date(2025, 1, 1)
    assert store.enrollment_periods[0].end_date == date(2025, 12, 31)
    assert store.enrollment_periods[0].source == "eligibility_feed"


def test_adapter_filters_implausible_bp_values() -> None:
    store = adapt_assertions(
        {
            "demographics": {"dob": "1965-03-15", "gender": "female"},
            "assertions": [
                {
                    "category": "vital_sign",
                    "concept": "BP 24/25",
                    "exact_quote": "7/24/25, 10:46 AM",
                    "effective_date": "1947-09-20",
                    "structured": {"bp_systolic": 24, "bp_diastolic": 25},
                    "page_number": 1,
                },
                {
                    "category": "vital_sign",
                    "concept": "BP 138/83",
                    "exact_quote": "138/83 mmHg",
                    "effective_date": "2025-01-27",
                    "structured": {"bp_systolic": 138, "bp_diastolic": 83},
                    "page_number": 2,
                },
            ],
            "meta": {"pdf": "demo.pdf"},
        }
    )

    bp_pairs = {(v.systolic, v.diastolic) for v in store.vitals if v.systolic is not None and v.diastolic is not None}
    assert (24.0, 25.0) not in bp_pairs
    assert (138.0, 83.0) in bp_pairs
