"""Tests for newly added HEDIS measures (BPD, COA, WCC, LSC, AIS, SPR, PPC, W30, TRC, DRR, APM, FUM, ADD, KED)."""

from datetime import date
from pathlib import Path

from hedis_engine.engine import HedisEngine
from hedis_engine.types import (
    CodeSystem, Demographics, DiagnosisEvent, DiagnosisStatus,
    EncounterEvent, EncounterType, Gender, ImmunizationEvent,
    LabEvent, MedicationEvent, MemberEventStore, ProcedureEvent,
    VitalEvent, VitalType, EvidenceRef,
)

_CATALOG = Path(__file__).parent.parent / "catalog"


def _engine(year: int = 2024) -> HedisEngine:
    return HedisEngine(catalog_dir=_CATALOG, measurement_year=year)


def _store(**kwargs) -> MemberEventStore:
    return MemberEventStore(**kwargs)


# ---------------------------------------------------------------------------
# BPD — Blood Pressure Control for Patients with Diabetes
# ---------------------------------------------------------------------------

def test_bpd_met():
    """Diabetic with controlled BP should meet BPD."""
    store = _store(
        demographics=Demographics(dob=date(1970, 3, 15), gender=Gender.FEMALE),
        diagnoses=[DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 6, 1))],
        vitals=[VitalEvent(vital_type=VitalType.BP, systolic=130, diastolic=82, event_date=date(2024, 10, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["BPD"])
    assert r.measures[0].status.value == "met"


def test_bpd_gap_uncontrolled():
    """Diabetic with high BP should have gap."""
    store = _store(
        demographics=Demographics(dob=date(1970, 3, 15), gender=Gender.MALE),
        diagnoses=[DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 6, 1))],
        vitals=[VitalEvent(vital_type=VitalType.BP, systolic=155, diastolic=92, event_date=date(2024, 10, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["BPD"])
    assert r.measures[0].status.value == "gap"


def test_bpd_na_no_diabetes():
    """Non-diabetic should be N/A for BPD."""
    store = _store(
        demographics=Demographics(dob=date(1970, 3, 15), gender=Gender.MALE),
        diagnoses=[DiagnosisEvent(code="I10", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 6, 1))],
        vitals=[VitalEvent(vital_type=VitalType.BP, systolic=120, diastolic=80, event_date=date(2024, 10, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["BPD"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# COA — Care for Older Adults
# ---------------------------------------------------------------------------

def test_coa_med_review_met():
    """Senior with medication review procedure should meet."""
    store = _store(
        demographics=Demographics(dob=date(1950, 1, 1), gender=Gender.FEMALE),
        procedures=[ProcedureEvent(code="99605", code_system=CodeSystem.CPT, event_date=date(2024, 8, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["COA-MED-REVIEW"])
    assert r.measures[0].status.value == "met"


def test_coa_func_status_gap():
    """Senior without functional assessment should have gap."""
    store = _store(
        demographics=Demographics(dob=date(1950, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["COA-FUNC-STATUS"])
    assert r.measures[0].status.value == "gap"


def test_coa_na_too_young():
    """Under 66 should be N/A for COA."""
    store = _store(
        demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["COA-MED-REVIEW"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# WCC — Weight Assessment and Counseling for Children
# ---------------------------------------------------------------------------

def test_wcc_bmi_met():
    """Child with BMI documented and outpatient visit should meet WCC-BMI."""
    store = _store(
        demographics=Demographics(dob=date(2014, 6, 15), gender=Gender.FEMALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 9, 1))],
        vitals=[VitalEvent(vital_type=VitalType.BMI, value=18.5, event_date=date(2024, 9, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["WCC-BMI"])
    assert r.measures[0].status.value == "met"


def test_wcc_nutrition_gap():
    """Child without nutrition counseling should have gap."""
    store = _store(
        demographics=Demographics(dob=date(2014, 6, 15), gender=Gender.MALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 9, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["WCC-NUTRITION"])
    assert r.measures[0].status.value == "gap"


def test_wcc_na_too_old():
    """Adult should be N/A for WCC."""
    store = _store(
        demographics=Demographics(dob=date(2000, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["WCC-BMI"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# LSC — Lead Screening in Children
# ---------------------------------------------------------------------------

def test_lsc_met():
    """2-year-old with lead test should meet LSC."""
    store = _store(
        demographics=Demographics(dob=date(2022, 6, 15), gender=Gender.MALE),
        labs=[LabEvent(test_type="LEAD", value=2.0, unit="ug/dL", event_date=date(2024, 3, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["LSC"])
    assert r.measures[0].status.value == "met"


def test_lsc_gap_no_test():
    """2-year-old without lead test should have gap."""
    store = _store(
        demographics=Demographics(dob=date(2022, 6, 15), gender=Gender.FEMALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["LSC"])
    assert r.measures[0].status.value == "gap"


def test_lsc_na_wrong_age():
    """5-year-old should be N/A for LSC."""
    store = _store(
        demographics=Demographics(dob=date(2019, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["LSC"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# AIS — Adult Immunization Status
# ---------------------------------------------------------------------------

def test_ais_flu_met():
    """Adult with flu vaccine should meet AIS-FLU."""
    store = _store(
        demographics=Demographics(dob=date(1985, 4, 20), gender=Gender.FEMALE),
        immunizations=[ImmunizationEvent(vaccine_type="influenza", event_date=date(2024, 10, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["AIS-FLU"])
    assert r.measures[0].status.value == "met"


def test_ais_zoster_met():
    """Adult 50+ with 2 zoster doses should meet AIS-ZOSTER."""
    store = _store(
        demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE),
        immunizations=[
            ImmunizationEvent(vaccine_type="zoster", event_date=date(2023, 1, 1)),
            ImmunizationEvent(vaccine_type="zoster", event_date=date(2023, 4, 1)),
        ],
    )
    r = _engine().evaluate_member(store, measure_ids=["AIS-ZOSTER"])
    assert r.measures[0].status.value == "met"


def test_ais_zoster_gap_one_dose():
    """Adult 50+ with only 1 zoster dose should have gap."""
    store = _store(
        demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE),
        immunizations=[ImmunizationEvent(vaccine_type="zoster", event_date=date(2023, 1, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["AIS-ZOSTER"])
    assert r.measures[0].status.value == "gap"


def test_ais_pneumo_na_young():
    """Under 65 should be N/A for AIS-PNEUMO."""
    store = _store(
        demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["AIS-PNEUMO"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# SPR — Statin Therapy for Patients with Cardiovascular Disease
# ---------------------------------------------------------------------------

def test_spr_met():
    """Patient with ASCVD + statin should meet SPR."""
    store = _store(
        demographics=Demographics(dob=date(1964, 1, 31), gender=Gender.FEMALE),
        diagnoses=[DiagnosisEvent(code="I25.10", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 6, 1))],
        medications=[MedicationEvent(name="atorvastatin 40mg", normalized_class="statin", start_date=date(2024, 1, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["SPR"])
    assert r.measures[0].status.value == "met"


def test_spr_gap_no_statin():
    """Patient with ASCVD but no statin should have gap."""
    store = _store(
        demographics=Demographics(dob=date(1965, 5, 15), gender=Gender.MALE),
        diagnoses=[DiagnosisEvent(code="I25.10", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 6, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["SPR"])
    assert r.measures[0].status.value == "gap"


def test_spr_na_no_ascvd():
    """Patient without ASCVD should be N/A for SPR."""
    store = _store(
        demographics=Demographics(dob=date(1965, 5, 15), gender=Gender.MALE),
        diagnoses=[DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 6, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["SPR"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# PPC — Prenatal and Postpartum Care
# ---------------------------------------------------------------------------

def test_ppc_na_male():
    """Male should be N/A for PPC."""
    store = _store(
        demographics=Demographics(dob=date(1990, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["PPC-PRENATAL"])
    assert r.measures[0].status.value == "not_applicable"


def test_ppc_na_no_delivery():
    """Female without delivery codes should be N/A."""
    store = _store(
        demographics=Demographics(dob=date(1990, 1, 1), gender=Gender.FEMALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["PPC-PRENATAL"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# W30 — Well-Child Visits
# ---------------------------------------------------------------------------

def test_w30_15_na_wrong_age():
    """5-year-old should be N/A for W30-15."""
    store = _store(
        demographics=Demographics(dob=date(2019, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["W30-15"])
    assert r.measures[0].status.value == "not_applicable"


def test_w30_30_met():
    """2-year-old with outpatient visit should meet W30-30."""
    store = _store(
        demographics=Demographics(dob=date(2022, 6, 15), gender=Gender.FEMALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 9, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["W30-30"])
    assert r.measures[0].status.value == "met"


# ---------------------------------------------------------------------------
# TRC — Transitions of Care
# ---------------------------------------------------------------------------

def test_trc_engagement_met():
    """Patient with inpatient stay + outpatient follow-up should meet TRC."""
    store = _store(
        demographics=Demographics(dob=date(1960, 1, 1), gender=Gender.MALE),
        encounters=[
            EncounterEvent(encounter_type=EncounterType.INPATIENT, event_date=date(2024, 8, 1)),
            EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 8, 20)),
        ],
    )
    r = _engine().evaluate_member(store, measure_ids=["TRC-ENGAGEMENT"])
    assert r.measures[0].status.value == "met"


def test_trc_na_no_inpatient():
    """Patient without inpatient stay should be N/A for TRC."""
    store = _store(
        demographics=Demographics(dob=date(1960, 1, 1), gender=Gender.MALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 8, 20))],
    )
    r = _engine().evaluate_member(store, measure_ids=["TRC-ENGAGEMENT"])
    assert r.measures[0].status.value == "not_applicable"


def test_trc_med_recon_met():
    """Patient with inpatient + med reconciliation should meet."""
    store = _store(
        demographics=Demographics(dob=date(1960, 1, 1), gender=Gender.FEMALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.INPATIENT, event_date=date(2024, 8, 1))],
        procedures=[ProcedureEvent(code="99495", code_system=CodeSystem.CPT, event_date=date(2024, 8, 10))],
    )
    r = _engine().evaluate_member(store, measure_ids=["TRC-MED-RECON"])
    assert r.measures[0].status.value == "met"


# ---------------------------------------------------------------------------
# DRR — Depression Remission or Response
# ---------------------------------------------------------------------------

def test_drr_followup_met():
    """Patient with depression Dx + PHQ-9 score should meet DRR-FOLLOWUP."""
    store = _store(
        demographics=Demographics(dob=date(1980, 1, 1), gender=Gender.FEMALE),
        diagnoses=[DiagnosisEvent(code="F32.1", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 3, 1))],
        labs=[LabEvent(test_type="PHQ9", value=3.0, event_date=date(2024, 9, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["DRR-FOLLOWUP"])
    assert r.measures[0].status.value == "met"


def test_drr_remission_met():
    """Patient with depression Dx + PHQ-9 < 5 should meet DRR-REMISSION."""
    store = _store(
        demographics=Demographics(dob=date(1980, 1, 1), gender=Gender.FEMALE),
        diagnoses=[DiagnosisEvent(code="F32.1", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 3, 1))],
        labs=[LabEvent(test_type="PHQ9", value=3.0, event_date=date(2024, 9, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["DRR-REMISSION"])
    assert r.measures[0].status.value == "met"


def test_drr_remission_gap_high_score():
    """PHQ-9 >= 5 should not be remission."""
    store = _store(
        demographics=Demographics(dob=date(1980, 1, 1), gender=Gender.MALE),
        diagnoses=[DiagnosisEvent(code="F33.0", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 3, 1))],
        labs=[LabEvent(test_type="PHQ9", value=8.0, event_date=date(2024, 9, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["DRR-REMISSION"])
    assert r.measures[0].status.value == "gap"


def test_drr_na_no_depression():
    """No depression Dx = N/A for DRR."""
    store = _store(
        demographics=Demographics(dob=date(1980, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["DRR-FOLLOWUP"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# APM — Metabolic Monitoring for Children on Antipsychotics
# ---------------------------------------------------------------------------

def test_apm_glucose_met():
    """Child with outpatient visit + glucose lab should meet APM-GLUCOSE."""
    store = _store(
        demographics=Demographics(dob=date(2012, 6, 15), gender=Gender.MALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 5, 1))],
        labs=[LabEvent(test_type="GLUCOSE", value=95.0, event_date=date(2024, 7, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["APM-GLUCOSE"])
    assert r.measures[0].status.value == "met"


def test_apm_glucose_met_via_a1c():
    """Child with outpatient visit + A1C lab should also meet APM-GLUCOSE."""
    store = _store(
        demographics=Demographics(dob=date(2012, 6, 15), gender=Gender.FEMALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 5, 1))],
        labs=[LabEvent(test_type="A1C", value=5.2, event_date=date(2024, 7, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["APM-GLUCOSE"])
    assert r.measures[0].status.value == "met"


def test_apm_cholesterol_gap():
    """Child with outpatient visit but no cholesterol test should have gap."""
    store = _store(
        demographics=Demographics(dob=date(2012, 6, 15), gender=Gender.MALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 5, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["APM-CHOLESTEROL"])
    assert r.measures[0].status.value == "gap"


def test_apm_na_adult():
    """Adult should be N/A for APM."""
    store = _store(
        demographics=Demographics(dob=date(1990, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["APM-GLUCOSE"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# FUM — Follow-Up After ED Visit for Mental Illness
# ---------------------------------------------------------------------------

def test_fum_7_met():
    """Patient with ED visit + outpatient follow-up should meet FUM-7."""
    store = _store(
        demographics=Demographics(dob=date(2000, 1, 1), gender=Gender.FEMALE),
        encounters=[
            EncounterEvent(encounter_type=EncounterType.ED, event_date=date(2024, 9, 1)),
            EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 9, 5)),
        ],
    )
    r = _engine().evaluate_member(store, measure_ids=["FUM-7"])
    assert r.measures[0].status.value == "met"


def test_fum_na_no_ed_visit():
    """No ED visit should be N/A for FUM."""
    store = _store(
        demographics=Demographics(dob=date(2000, 1, 1), gender=Gender.MALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 9, 5))],
    )
    r = _engine().evaluate_member(store, measure_ids=["FUM-7"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# ADD — Follow-Up Care for ADHD Medication
# ---------------------------------------------------------------------------

def test_add_initiation_met():
    """Child 6-12 with outpatient encounter should meet ADD-INITIATION."""
    store = _store(
        demographics=Demographics(dob=date(2015, 3, 1), gender=Gender.MALE),
        encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2024, 7, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["ADD-INITIATION"])
    assert r.measures[0].status.value == "met"


def test_add_na_too_old():
    """Teenager >12 should be N/A for ADD."""
    store = _store(
        demographics=Demographics(dob=date(2008, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["ADD-INITIATION"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# KED — Kidney Health Evaluation for Patients with Diabetes
# ---------------------------------------------------------------------------

def test_ked_met():
    """Diabetic with both eGFR and uACR should meet KED."""
    store = _store(
        demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE),
        diagnoses=[DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 5, 1))],
        labs=[
            LabEvent(test_type="EGFR", value=75.0, unit="mL/min", event_date=date(2024, 6, 1)),
            LabEvent(test_type="UACR", value=25.0, unit="mg/g", event_date=date(2024, 6, 1)),
        ],
    )
    r = _engine().evaluate_member(store, measure_ids=["KED"])
    assert r.measures[0].status.value == "met"


def test_ked_gap_missing_uacr():
    """Diabetic with eGFR but no uACR should have gap."""
    store = _store(
        demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.FEMALE),
        diagnoses=[DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE, event_date=date(2024, 5, 1))],
        labs=[LabEvent(test_type="EGFR", value=75.0, event_date=date(2024, 6, 1))],
    )
    r = _engine().evaluate_member(store, measure_ids=["KED"])
    assert r.measures[0].status.value == "gap"


def test_ked_na_no_diabetes():
    """Non-diabetic should be N/A for KED."""
    store = _store(
        demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE),
    )
    r = _engine().evaluate_member(store, measure_ids=["KED"])
    assert r.measures[0].status.value == "not_applicable"


# ---------------------------------------------------------------------------
# Cross-measure coverage: verify all user-requested measure IDs load
# ---------------------------------------------------------------------------

def test_all_requested_measures_present():
    """Verify all user-requested measure IDs are present in the catalog."""
    engine = _engine()
    loaded_ids = {m.id for m in engine.measures}

    # User requested these measure families
    required_families = {
        "CBP": ["CBP"],
        "BPD": ["BPD"],
        "COL": ["COL"],
        "CCS": ["CCS"],
        "COA": ["COA-MED-REVIEW", "COA-FUNC-STATUS"],
        "WCC": ["WCC-BMI", "WCC-NUTRITION", "WCC-ACTIVITY"],
        "CIS": ["CIS-DTAP", "CIS-POLIO", "CIS-MMR", "CIS-HIB", "CIS-HEPB", "CIS-VZV", "CIS-PCV", "CIS-HEPA", "CIS-RV"],
        "IMA": ["IMA-HPV", "IMA-MENING", "IMA-TDAP"],
        "LSC": ["LSC"],
        "AIS": ["AIS-FLU", "AIS-TDAP", "AIS-ZOSTER", "AIS-PNEUMO", "AIS-HEPB"],
        "OMW": ["OMW"],
        "SPR": ["SPR"],
        "CDC": ["CDC-A1C-TEST", "CDC-A1C-CONTROL-8", "CDC-A1C-POOR-9", "CDC-EYE", "CDC-NEPHROPATHY", "CDC-STATIN"],
        "PPC": ["PPC-PRENATAL", "PPC-POSTPARTUM"],
        "W30": ["W30-15", "W30-30"],
        "TRC": ["TRC-ENGAGEMENT", "TRC-MED-RECON"],
        "DRR": ["DRR-FOLLOWUP", "DRR-REMISSION", "DRR-RESPONSE"],
        "APM": ["APM-GLUCOSE", "APM-CHOLESTEROL"],
        "FUM": ["FUM-7", "FUM-30"],
        "ADD": ["ADD-INITIATION", "ADD-CONTINUATION"],
        "AWC": ["AWC"],
    }

    for family, measure_ids in required_families.items():
        for mid in measure_ids:
            assert mid in loaded_ids, f"Missing measure {mid} from family {family}. Loaded: {sorted(loaded_ids)}"


def test_total_measure_count():
    """Verify we have at least 64 measures loaded."""
    engine = _engine()
    assert len(engine.measures) >= 64, f"Expected >= 64 measures, got {len(engine.measures)}"
