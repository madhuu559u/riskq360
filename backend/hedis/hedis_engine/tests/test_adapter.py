"""Tests for the assertion adapter."""

from datetime import date

from hedis_engine.adapters.assertion_adapter import adapt_assertions
from hedis_engine.types import (
    CodeSystem,
    DiagnosisStatus,
    Gender,
    VitalType,
)


def test_adapt_basic_demographics():
    data = {
        "member_id": "M001",
        "demographics": {
            "dob": "1965-03-15",
            "gender": "female",
        },
    }
    store = adapt_assertions(data)
    assert store.demographics.member_id == "M001"
    assert store.demographics.dob == date(1965, 3, 15)
    assert store.demographics.gender == Gender.FEMALE


def test_adapt_demographics_alt_format():
    data = {
        "member_id": "M002",
        "demographics": {
            "date_of_birth": "03/15/1965",
            "sex": "M",
        },
    }
    store = adapt_assertions(data)
    assert store.demographics.dob == date(1965, 3, 15)
    assert store.demographics.gender == Gender.MALE


def test_adapt_diagnosis():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "diagnoses": [
            {
                "code": "E11.9",
                "code_system": "icd10cm",
                "description": "Type 2 DM",
                "date": "2025-03-10",
                "status": "active",
                "pdf": "chart.pdf",
                "page_number": 3,
                "exact_quote": "Type 2 diabetes",
            }
        ],
    }
    store = adapt_assertions(data)
    assert len(store.diagnoses) == 1
    dx = store.diagnoses[0]
    assert dx.code == "E11.9"
    assert dx.code_system == CodeSystem.ICD10CM
    assert dx.status == DiagnosisStatus.ACTIVE
    assert dx.event_date == date(2025, 3, 10)
    assert dx.evidence_ref is not None
    assert dx.evidence_ref.pdf == "chart.pdf"
    assert dx.evidence_ref.page_number == 3


def test_adapt_negated_diagnosis():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "diagnoses": [
            {"code": "I10", "status": "negated", "date": "2025-01-01"},
        ],
    }
    store = adapt_assertions(data)
    assert store.diagnoses[0].status == DiagnosisStatus.NEGATED


def test_adapt_labs():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "labs": [
            {"test_type": "HbA1c", "value": 7.8, "unit": "%", "date": "2025-09-15"},
            {"test_type": "LDL", "value": 95, "unit": "mg/dL", "date": "2025-09-15"},
        ],
    }
    store = adapt_assertions(data)
    assert len(store.labs) == 2
    a1c = next(l for l in store.labs if l.test_type == "A1C")
    assert a1c.value == 7.8
    assert a1c.event_date == date(2025, 9, 15)


def test_adapt_vitals_bp():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "vitals": [
            {
                "type": "blood_pressure",
                "systolic": 128,
                "diastolic": 82,
                "date": "2025-09-15",
            }
        ],
    }
    store = adapt_assertions(data)
    assert len(store.vitals) == 1
    bp = store.vitals[0]
    assert bp.vital_type == VitalType.BP
    assert bp.systolic == 128.0
    assert bp.diastolic == 82.0


def test_adapt_vitals_bmi():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "vitals": [
            {"type": "bmi", "value": 28.5, "date": "2025-09-15"},
        ],
    }
    store = adapt_assertions(data)
    bmi = store.vitals[0]
    assert bmi.vital_type == VitalType.BMI
    assert bmi.value == 28.5


def test_adapt_medications():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "medications": [
            {"name": "Atorvastatin 40mg daily", "date": "2025-04-20"},
            {"name": "Metformin 1000mg BID", "date": "2025-03-10"},
        ],
    }
    store = adapt_assertions(data)
    assert len(store.medications) == 2
    statin = next(m for m in store.medications if "atorvastatin" in m.name.lower())
    assert statin.normalized_class == "statin"
    metformin = next(m for m in store.medications if "metformin" in m.name.lower())
    assert metformin.normalized_class == "metformin"


def test_adapt_encounters():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "encounters": [
            {"type": "outpatient", "date": "2025-03-10", "provider": "Dr. Smith"},
        ],
    }
    store = adapt_assertions(data)
    assert len(store.encounters) == 1


def test_adapt_immunizations():
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "immunizations": [
            {"vaccine_type": "influenza", "code": "158", "code_system": "cvx", "date": "2025-10-01"},
        ],
    }
    store = adapt_assertions(data)
    assert len(store.immunizations) == 1
    assert store.immunizations[0].vaccine_type == "influenza"


def test_adapt_generic_assertions():
    """Generic assertions should be auto-classified."""
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "assertions": [
            {"type": "diagnosis", "code": "E11.9", "status": "active", "date": "2025-01-01"},
            {"type": "medication", "name": "Lisinopril 20mg", "date": "2025-01-01"},
            {"type": "lab", "test_type": "A1C", "value": 7.5, "date": "2025-06-01"},
        ],
    }
    store = adapt_assertions(data)
    assert len(store.diagnoses) == 1
    assert len(store.medications) == 1
    assert len(store.labs) == 1


def test_adapt_empty_data():
    """Engine should not crash on empty data."""
    data = {"member_id": "M001"}
    store = adapt_assertions(data)
    assert store.demographics.member_id == "M001"
    assert store.diagnoses == []


def test_adapt_missing_dates():
    """Should handle missing dates gracefully."""
    data = {
        "member_id": "M001",
        "demographics": {"dob": "1965-01-01", "gender": "male"},
        "diagnoses": [
            {"code": "E11.9", "status": "active"},
        ],
    }
    store = adapt_assertions(data)
    assert store.diagnoses[0].event_date is None
