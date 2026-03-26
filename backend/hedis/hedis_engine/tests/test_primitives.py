"""Tests for rule primitives."""

from datetime import date

from hedis_engine.primitives import (
    age_as_of,
    age_between,
    bp_controlled,
    continuous_enrollment,
    encounter_exists,
    gender_in,
    has_any_diagnosis_code,
    has_diagnosis,
    immunization_count,
    lab_exists,
    lab_value_in_range,
    lookback_from_year_end,
    measurement_window,
    medication_present,
    vital_exists,
    bmi_in_range,
)
from hedis_engine.types import (
    CodeSystem,
    Demographics,
    DiagnosisEvent,
    DiagnosisStatus,
    EnrollmentPeriod,
    EncounterEvent,
    EncounterType,
    Gender,
    ImmunizationEvent,
    LabEvent,
    MedicationEvent,
    MemberEventStore,
    VitalEvent,
    VitalType,
)


def _make_store(**kwargs) -> MemberEventStore:
    return MemberEventStore(**kwargs)


# ---------------------------------------------------------------------------
# Age
# ---------------------------------------------------------------------------

def test_age_as_of():
    assert age_as_of(date(1990, 6, 15), date(2025, 12, 31)) == 35
    assert age_as_of(date(1990, 6, 15), date(2025, 6, 14)) == 34
    assert age_as_of(date(1990, 6, 15), date(2025, 6, 15)) == 35
    assert age_as_of(None, date(2025, 12, 31)) is None


def test_age_between_in_range():
    store = _make_store(demographics=Demographics(dob=date(1965, 3, 15)))
    matched, detail, _ = age_between(store, 18, 75, date(2025, 12, 31))
    assert matched is True
    assert "60" in detail


def test_age_between_out_of_range():
    store = _make_store(demographics=Demographics(dob=date(2020, 1, 1)))
    matched, detail, _ = age_between(store, 18, 75, date(2025, 12, 31))
    assert matched is False
    assert "5" in detail


def test_age_between_unknown_dob():
    store = _make_store(demographics=Demographics(dob=None))
    matched, detail, _ = age_between(store, 18, 75, date(2025, 12, 31))
    assert matched is False
    assert "unknown" in detail.lower()


def test_age_between_edge_min():
    store = _make_store(demographics=Demographics(dob=date(2007, 12, 31)))
    matched, _, _ = age_between(store, 18, 75, date(2025, 12, 31))
    assert matched is True  # Exactly 18


def test_age_between_edge_max():
    store = _make_store(demographics=Demographics(dob=date(1950, 1, 1)))
    matched, _, _ = age_between(store, 18, 75, date(2025, 12, 31))
    assert matched is True  # 75


# ---------------------------------------------------------------------------
# Gender
# ---------------------------------------------------------------------------

def test_gender_matches():
    store = _make_store(demographics=Demographics(gender=Gender.FEMALE))
    matched, _, _ = gender_in(store, {Gender.FEMALE})
    assert matched is True


def test_gender_no_match():
    store = _make_store(demographics=Demographics(gender=Gender.MALE))
    matched, _, _ = gender_in(store, {Gender.FEMALE})
    assert matched is False


def test_gender_both():
    store = _make_store(demographics=Demographics(gender=Gender.MALE))
    matched, _, _ = gender_in(store, {Gender.MALE, Gender.FEMALE})
    assert matched is True


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

def test_has_any_diagnosis_code_found():
    store = _make_store(diagnoses=[
        DiagnosisEvent(code="E11.9", code_system=CodeSystem.ICD10CM,
                       status=DiagnosisStatus.ACTIVE, event_date=date(2025, 3, 1)),
    ])
    matched, _, evidence = has_any_diagnosis_code(store, {"E11.9"})
    assert matched is True
    assert len(evidence) == 1
    assert evidence[0].code == "E11.9"


def test_has_any_diagnosis_code_not_found():
    store = _make_store(diagnoses=[
        DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE),
    ])
    matched, _, _ = has_any_diagnosis_code(store, {"I10"})
    assert matched is False


def test_diagnosis_negated_excluded():
    store = _make_store(diagnoses=[
        DiagnosisEvent(code="E11.9", status=DiagnosisStatus.NEGATED, event_date=date(2025, 3, 1)),
    ])
    matched, _, _ = has_any_diagnosis_code(store, {"E11.9"})
    assert matched is False  # Negated = not matched by default


def test_diagnosis_historical_included():
    store = _make_store(diagnoses=[
        DiagnosisEvent(code="E11.9", status=DiagnosisStatus.HISTORICAL, event_date=date(2025, 3, 1)),
    ])
    matched, _, _ = has_any_diagnosis_code(store, {"E11.9"})
    assert matched is True


def test_diagnosis_family_history_excluded():
    store = _make_store(diagnoses=[
        DiagnosisEvent(code="E11.9", status=DiagnosisStatus.FAMILY_HISTORY, event_date=date(2025, 3, 1)),
    ])
    matched, _, _ = has_any_diagnosis_code(store, {"E11.9"})
    assert matched is False


def test_diagnosis_window_filter():
    store = _make_store(diagnoses=[
        DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE, event_date=date(2020, 1, 1)),
    ])
    matched, _, _ = has_any_diagnosis_code(store, {"E11.9"},
                                            window_start=date(2025, 1, 1), window_end=date(2025, 12, 31))
    assert matched is False  # Too old


def test_diagnosis_code_normalization():
    """Codes are normalized (stripped, uppercased, dots removed)."""
    store = _make_store(diagnoses=[
        DiagnosisEvent(code="e11.9", status=DiagnosisStatus.ACTIVE),
    ])
    matched, _, _ = has_any_diagnosis_code(store, {"E119"})
    assert matched is True


# ---------------------------------------------------------------------------
# Lab
# ---------------------------------------------------------------------------

def test_lab_exists_found():
    store = _make_store(labs=[
        LabEvent(test_type="A1C", value=7.8, event_date=date(2025, 9, 1)),
    ])
    matched, _, evidence = lab_exists(store, "A1C",
                                       window_start=date(2025, 1, 1), window_end=date(2025, 12, 31))
    assert matched is True
    assert len(evidence) == 1


def test_lab_exists_not_found():
    store = _make_store(labs=[])
    matched, _, _ = lab_exists(store, "A1C")
    assert matched is False


def test_lab_exists_wrong_type():
    store = _make_store(labs=[
        LabEvent(test_type="LDL", value=95, event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = lab_exists(store, "A1C")
    assert matched is False


def test_lab_value_in_range_lt():
    store = _make_store(labs=[
        LabEvent(test_type="A1C", value=7.8, event_date=date(2025, 9, 1)),
    ])
    matched, detail, _ = lab_value_in_range(store, "A1C", "lt", 8.0)
    assert matched is True
    assert "7.8" in detail


def test_lab_value_in_range_gt_fail():
    store = _make_store(labs=[
        LabEvent(test_type="A1C", value=7.8, event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = lab_value_in_range(store, "A1C", "gt", 9.0)
    assert matched is False


def test_lab_value_latest():
    """When use_latest=True, only the most recent lab is checked."""
    store = _make_store(labs=[
        LabEvent(test_type="A1C", value=9.5, event_date=date(2025, 3, 1)),
        LabEvent(test_type="A1C", value=7.2, event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = lab_value_in_range(store, "A1C", "lt", 8.0, use_latest=True)
    assert matched is True  # Latest (7.2) is < 8.0


def test_lab_value_no_value():
    store = _make_store(labs=[
        LabEvent(test_type="A1C", value=None, event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = lab_value_in_range(store, "A1C", "lt", 8.0)
    assert matched is False


# ---------------------------------------------------------------------------
# Blood Pressure
# ---------------------------------------------------------------------------

def test_bp_controlled_yes():
    store = _make_store(vitals=[
        VitalEvent(vital_type=VitalType.BP, systolic=128, diastolic=82,
                   event_date=date(2025, 9, 1)),
    ])
    matched, detail, evidence = bp_controlled(store, 140, 90)
    assert matched is True
    assert "controlled" in detail
    assert len(evidence) == 1


def test_bp_controlled_no_systolic_high():
    store = _make_store(vitals=[
        VitalEvent(vital_type=VitalType.BP, systolic=145, diastolic=82,
                   event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = bp_controlled(store, 140, 90)
    assert matched is False


def test_bp_controlled_no_diastolic_high():
    store = _make_store(vitals=[
        VitalEvent(vital_type=VitalType.BP, systolic=128, diastolic=95,
                   event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = bp_controlled(store, 140, 90)
    assert matched is False


def test_bp_no_readings():
    store = _make_store(vitals=[])
    matched, detail, _ = bp_controlled(store, 140, 90)
    assert matched is False
    assert "No BP" in detail


def test_bp_uses_latest():
    store = _make_store(vitals=[
        VitalEvent(vital_type=VitalType.BP, systolic=150, diastolic=95,
                   event_date=date(2025, 3, 1)),  # High
        VitalEvent(vital_type=VitalType.BP, systolic=125, diastolic=78,
                   event_date=date(2025, 9, 1)),  # Controlled
    ])
    matched, _, _ = bp_controlled(store, 140, 90, use_latest=True)
    assert matched is True  # Uses latest (Sep)


# ---------------------------------------------------------------------------
# BMI
# ---------------------------------------------------------------------------

def test_bmi_in_range():
    store = _make_store(vitals=[
        VitalEvent(vital_type=VitalType.BMI, value=25.0, event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = bmi_in_range(store, min_bmi=18.5, max_bmi=30.0)
    assert matched is True


def test_bmi_out_of_range():
    store = _make_store(vitals=[
        VitalEvent(vital_type=VitalType.BMI, value=35.0, event_date=date(2025, 9, 1)),
    ])
    matched, _, _ = bmi_in_range(store, min_bmi=18.5, max_bmi=30.0)
    assert matched is False


# ---------------------------------------------------------------------------
# Medication
# ---------------------------------------------------------------------------

def test_medication_class_match():
    store = _make_store(medications=[
        MedicationEvent(name="Atorvastatin 40mg", normalized_class="statin",
                        start_date=date(2025, 4, 1)),
    ])
    matched, _, evidence = medication_present(store, "statin")
    assert matched is True
    assert len(evidence) == 1


def test_medication_name_substring_match():
    store = _make_store(medications=[
        MedicationEvent(name="Atorvastatin 40mg", normalized_class="",
                        start_date=date(2025, 4, 1)),
    ])
    matched, _, _ = medication_present(store, "atorvastatin")
    assert matched is True


def test_medication_no_match():
    store = _make_store(medications=[
        MedicationEvent(name="Metformin 1000mg", normalized_class="metformin",
                        start_date=date(2025, 4, 1)),
    ])
    matched, _, _ = medication_present(store, "statin")
    assert matched is False


# ---------------------------------------------------------------------------
# Immunization
# ---------------------------------------------------------------------------

def test_immunization_count_met():
    store = _make_store(immunizations=[
        ImmunizationEvent(vaccine_type="influenza", event_date=date(2025, 10, 1)),
    ])
    matched, detail, evidence = immunization_count(store, "influenza", min_count=1)
    assert matched is True


def test_immunization_count_not_met():
    store = _make_store(immunizations=[
        ImmunizationEvent(vaccine_type="influenza", event_date=date(2025, 10, 1)),
    ])
    matched, _, _ = immunization_count(store, "influenza", min_count=2)
    assert matched is False


def test_immunization_series():
    store = _make_store(immunizations=[
        ImmunizationEvent(vaccine_type="dtap", event_date=date(2023, 2, 1)),
        ImmunizationEvent(vaccine_type="dtap", event_date=date(2023, 4, 1)),
        ImmunizationEvent(vaccine_type="dtap", event_date=date(2023, 6, 1)),
        ImmunizationEvent(vaccine_type="dtap", event_date=date(2024, 1, 1)),
    ])
    matched, _, _ = immunization_count(store, "dtap", min_count=4)
    assert matched is True


def test_immunization_wrong_type():
    store = _make_store(immunizations=[
        ImmunizationEvent(vaccine_type="influenza", event_date=date(2025, 10, 1)),
    ])
    matched, _, _ = immunization_count(store, "pneumococcal", min_count=1)
    assert matched is False


# ---------------------------------------------------------------------------
# Encounter
# ---------------------------------------------------------------------------

def test_encounter_exists():
    store = _make_store(encounters=[
        EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2025, 6, 1)),
    ])
    matched, _, _ = encounter_exists(store, {"outpatient"})
    assert matched is True


def test_encounter_wrong_type():
    store = _make_store(encounters=[
        EncounterEvent(encounter_type=EncounterType.INPATIENT, event_date=date(2025, 6, 1)),
    ])
    matched, _, _ = encounter_exists(store, {"outpatient"})
    assert matched is False


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

def test_continuous_enrollment_missing_data():
    store = _make_store()
    matched, detail, _ = continuous_enrollment(store, date(2025, 1, 1), date(2025, 12, 31))
    assert matched is False
    assert "unavailable" in detail.lower()


def test_continuous_enrollment_full_coverage():
    store = _make_store(
        enrollment_periods=[EnrollmentPeriod(date(2025, 1, 1), date(2025, 12, 31), source="test_feed")]
    )
    matched, detail, _ = continuous_enrollment(store, date(2025, 1, 1), date(2025, 12, 31))
    assert matched is True
    assert "verified" in detail.lower()


def test_continuous_enrollment_gap_detected():
    store = _make_store(
        enrollment_periods=[
            EnrollmentPeriod(date(2025, 1, 1), date(2025, 6, 30)),
            EnrollmentPeriod(date(2025, 7, 2), date(2025, 12, 31)),
        ]
    )
    matched, detail, _ = continuous_enrollment(store, date(2025, 1, 1), date(2025, 12, 31))
    assert matched is False
    assert "gap" in detail.lower()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_measurement_window():
    start, end = measurement_window(2025)
    assert start == date(2025, 1, 1)
    assert end == date(2025, 12, 31)


def test_lookback_from_year_end():
    start, end = lookback_from_year_end(2025, 12)
    assert end == date(2025, 12, 31)
    # Calendar-accurate: 12 months back from Dec 31 = Dec 31 prior year
    assert start == date(2024, 12, 31)
