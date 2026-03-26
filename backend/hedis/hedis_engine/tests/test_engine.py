"""Tests for the HEDIS engine — evaluating measures against synthetic member data."""

from datetime import date

import pytest

from hedis_engine.engine import HedisEngine
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
    MeasureStatus,
    MedicationEvent,
    MemberEventStore,
    ProcedureEvent,
    VitalEvent,
    VitalType,
)


@pytest.fixture
def engine():
    return HedisEngine(measurement_year=2025, require_enrollment_data=False)


def _diabetic_adult(gender=Gender.FEMALE, age_year=1965) -> MemberEventStore:
    """60-year-old adult with diabetes."""
    return MemberEventStore(
        demographics=Demographics(dob=date(age_year, 3, 15), gender=gender, member_id="TEST"),
        diagnoses=[
            DiagnosisEvent(code="E11.9", code_system=CodeSystem.ICD10CM,
                           status=DiagnosisStatus.ACTIVE, event_date=date(2025, 3, 1)),
        ],
    )


def _hypertensive_adult() -> MemberEventStore:
    """55-year-old adult with hypertension."""
    return MemberEventStore(
        demographics=Demographics(dob=date(1970, 6, 1), gender=Gender.MALE, member_id="TEST"),
        diagnoses=[
            DiagnosisEvent(code="I10", code_system=CodeSystem.ICD10CM,
                           status=DiagnosisStatus.ACTIVE, event_date=date(2025, 1, 15)),
        ],
    )


def _child_2yo() -> MemberEventStore:
    """2-year-old child."""
    return MemberEventStore(
        demographics=Demographics(dob=date(2023, 6, 1), gender=Gender.MALE, member_id="CHILD01"),
    )


def _teen_13yo() -> MemberEventStore:
    """13-year-old adolescent."""
    return MemberEventStore(
        demographics=Demographics(dob=date(2012, 3, 1), gender=Gender.FEMALE, member_id="TEEN01"),
    )


# =========================================================================
# Diabetes Care Measures
# =========================================================================

class TestCDCA1CTest:
    def test_indeterminate_when_continuous_enrollment_missing(self, engine):
        store = _diabetic_adult()
        strict_engine = HedisEngine(measurement_year=2025, require_enrollment_data=True)
        result = strict_engine.evaluate_measure(
            next(m for m in strict_engine.measures if m.id == "CDC-A1C-TEST"), store,
        )
        assert result.applicable is False
        assert result.status == MeasureStatus.INDETERMINATE
        assert "continuous_enrollment" in result.missing_data

    def test_compliant_with_a1c_lab(self, engine):
        store = _diabetic_adult()
        store.enrollment_periods.append(
            EnrollmentPeriod(date(2025, 1, 1), date(2025, 12, 31), source="test_feed")
        )
        store.labs.append(LabEvent(test_type="A1C", value=7.8, event_date=date(2025, 9, 1)))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-TEST"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_gap_no_a1c_lab(self, engine):
        store = _diabetic_adult()
        store.enrollment_periods.append(
            EnrollmentPeriod(date(2025, 1, 1), date(2025, 12, 31), source="test_feed")
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-TEST"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.GAP
        assert any("A1C" in g.description or "A1C" in g.required_event for g in result.gaps)

    def test_not_applicable_no_diabetes(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1965, 3, 15), gender=Gender.FEMALE, member_id="T"),
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-TEST"), store,
        )
        assert result.applicable is False
        assert result.status == MeasureStatus.NOT_APPLICABLE

    def test_not_applicable_wrong_age(self, engine):
        """Too young for CDC measures."""
        store = MemberEventStore(
            demographics=Demographics(dob=date(2015, 1, 1), gender=Gender.FEMALE, member_id="T"),
            diagnoses=[DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE)],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-TEST"), store,
        )
        assert result.applicable is False


class TestCDCA1CControl:
    def test_controlled_under_8(self, engine):
        store = _diabetic_adult()
        store.labs.append(LabEvent(test_type="A1C", value=7.2, event_date=date(2025, 9, 1)))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-CONTROL-8"), store,
        )
        assert result.status == MeasureStatus.MET

    def test_uncontrolled_above_8(self, engine):
        store = _diabetic_adult()
        store.labs.append(LabEvent(test_type="A1C", value=8.5, event_date=date(2025, 9, 1)))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-CONTROL-8"), store,
        )
        assert result.status == MeasureStatus.GAP


class TestCDCA1CPoor:
    def test_poor_control_above_9(self, engine):
        store = _diabetic_adult()
        store.labs.append(LabEvent(test_type="A1C", value=9.5, event_date=date(2025, 9, 1)))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-POOR-9"), store,
        )
        # Inverse measure: A1C > 9 = numerator satisfied = bad thing happened = GAP
        assert result.status == MeasureStatus.GAP

    def test_good_control_not_poor(self, engine):
        store = _diabetic_adult()
        store.labs.append(LabEvent(test_type="A1C", value=7.5, event_date=date(2025, 9, 1)))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-POOR-9"), store,
        )
        # Inverse measure: A1C < 9 = numerator NOT satisfied = good = MET
        assert result.status == MeasureStatus.MET


class TestCDCEye:
    def test_eye_exam_met(self, engine):
        store = _diabetic_adult()
        store.procedures.append(ProcedureEvent(
            code="92014", code_system=CodeSystem.CPT, event_date=date(2025, 5, 1),
        ))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-EYE"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_eye_exam_gap(self, engine):
        store = _diabetic_adult()
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-EYE"), store,
        )
        assert result.status == MeasureStatus.GAP


class TestCDCStatin:
    def test_statin_present(self, engine):
        store = _diabetic_adult(age_year=1970)  # 55 years, within 40-75
        store.medications.append(MedicationEvent(
            name="Atorvastatin 40mg", normalized_class="statin",
            start_date=date(2025, 1, 1),
        ))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-STATIN"), store,
        )
        assert result.status == MeasureStatus.MET

    def test_statin_missing(self, engine):
        store = _diabetic_adult(age_year=1970)
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-STATIN"), store,
        )
        assert result.status == MeasureStatus.GAP

    def test_too_young_for_statin_measure(self, engine):
        store = _diabetic_adult(age_year=1995)  # 30 years old, below 40
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-STATIN"), store,
        )
        assert result.applicable is False


# =========================================================================
# Blood Pressure Control
# =========================================================================

class TestCBP:
    def test_bp_controlled(self, engine):
        store = _hypertensive_adult()
        store.vitals.append(VitalEvent(
            vital_type=VitalType.BP, systolic=128, diastolic=82,
            event_date=date(2025, 9, 1),
        ))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CBP"), store,
        )
        assert result.status == MeasureStatus.MET

    def test_bp_uncontrolled(self, engine):
        store = _hypertensive_adult()
        store.vitals.append(VitalEvent(
            vital_type=VitalType.BP, systolic=150, diastolic=95,
            event_date=date(2025, 9, 1),
        ))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CBP"), store,
        )
        assert result.status == MeasureStatus.GAP

    def test_no_bp_reading(self, engine):
        store = _hypertensive_adult()
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CBP"), store,
        )
        assert result.status == MeasureStatus.GAP
        assert any("BP" in g.required_event or "blood" in g.description.lower()
                    for g in result.gaps)


# =========================================================================
# Preventive Screening
# =========================================================================

class TestCOL:
    def test_colonoscopy_met(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        store.procedures.append(ProcedureEvent(
            code="45378", code_system=CodeSystem.CPT, event_date=date(2020, 6, 1),
        ))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "COL"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_too_young(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(2000, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "COL"), store,
        )
        assert result.applicable is False


class TestBCS:
    def test_mammogram_met(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1965, 1, 1), gender=Gender.FEMALE, member_id="T"),
        )
        store.procedures.append(ProcedureEvent(
            code="77067", code_system=CodeSystem.CPT, event_date=date(2025, 1, 15),
        ))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "BCS"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_male_not_applicable(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1965, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "BCS"), store,
        )
        assert result.applicable is False


class TestCCS:
    def test_female_applicable(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1980, 1, 1), gender=Gender.FEMALE, member_id="T"),
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CCS"), store,
        )
        assert result.applicable is True

    def test_male_not_applicable(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1980, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CCS"), store,
        )
        assert result.applicable is False


# =========================================================================
# Immunization — Adult
# =========================================================================

class TestFLU:
    def test_flu_vaccinated(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE, member_id="T"),
            immunizations=[
                ImmunizationEvent(vaccine_type="influenza", event_date=date(2025, 10, 1)),
            ],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "FLU"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_flu_not_vaccinated(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "FLU"), store,
        )
        assert result.status == MeasureStatus.GAP


class TestPNU:
    def test_pnu_vaccinated_any_time(self, engine):
        """PNU has no time window — any-time vaccination counts."""
        store = MemberEventStore(
            demographics=Demographics(dob=date(1955, 1, 1), gender=Gender.MALE, member_id="T"),
            immunizations=[
                ImmunizationEvent(vaccine_type="pneumococcal", event_date=date(2020, 3, 1)),
            ],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "PNU"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_pnu_too_young(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "PNU"), store,
        )
        assert result.applicable is False


# =========================================================================
# Immunization — Childhood
# =========================================================================

class TestChildhoodImmunizations:
    def test_dtap_4_doses_met(self, engine):
        store = _child_2yo()
        # All doses within 24-month lookback window from end of 2025
        for d in [date(2024, 2, 1), date(2024, 4, 1), date(2024, 6, 1), date(2024, 12, 1)]:
            store.immunizations.append(ImmunizationEvent(
                vaccine_type="dtap", event_date=d,
            ))
        mdef = next((m for m in engine.measures if m.id == "CIS-DTAP"), None)
        if mdef is None:
            pytest.skip("CIS-DTAP measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_dtap_insufficient_doses(self, engine):
        store = _child_2yo()
        store.immunizations.append(ImmunizationEvent(
            vaccine_type="dtap", event_date=date(2023, 8, 1),
        ))
        mdef = next((m for m in engine.measures if m.id == "CIS-DTAP"), None)
        if mdef is None:
            pytest.skip("CIS-DTAP measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is True
        assert result.status == MeasureStatus.GAP

    def test_mmr_1_dose_met(self, engine):
        store = _child_2yo()
        store.immunizations.append(ImmunizationEvent(
            vaccine_type="mmr", event_date=date(2024, 6, 1),
        ))
        mdef = next((m for m in engine.measures if m.id == "CIS-MMR"), None)
        if mdef is None:
            pytest.skip("CIS-MMR measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_child_wrong_age(self, engine):
        """10-year-old should not be in CIS measures (age 2 only)."""
        store = MemberEventStore(
            demographics=Demographics(dob=date(2015, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        mdef = next((m for m in engine.measures if m.id == "CIS-DTAP"), None)
        if mdef is None:
            pytest.skip("CIS-DTAP measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is False


# =========================================================================
# Immunization — Adolescent
# =========================================================================

class TestAdolescentImmunizations:
    def test_ima_tdap_met(self, engine):
        store = _teen_13yo()
        store.immunizations.append(ImmunizationEvent(
            vaccine_type="tdap", event_date=date(2024, 9, 1),
        ))
        mdef = next((m for m in engine.measures if m.id == "IMA-TDAP"), None)
        if mdef is None:
            pytest.skip("IMA-TDAP measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is True
        assert result.status == MeasureStatus.MET


# =========================================================================
# Depression & Behavioral Health
# =========================================================================

class TestDSF:
    def test_dsf_with_screening(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.FEMALE, member_id="T"),
            encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2025, 6, 1))],
            procedures=[ProcedureEvent(code="96127", code_system=CodeSystem.CPT, event_date=date(2025, 6, 1))],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "DSF"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET


class TestAMM:
    def test_amm_acute_with_antidepressant(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.FEMALE, member_id="T"),
            diagnoses=[DiagnosisEvent(code="F33.0", status=DiagnosisStatus.ACTIVE, event_date=date(2025, 1, 1))],
            medications=[MedicationEvent(
                name="Sertraline 100mg", normalized_class="antidepressant",
                start_date=date(2025, 10, 1),
            )],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "AMM-ACUTE"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET


# =========================================================================
# Tobacco and BMI
# =========================================================================

class TestTSC:
    def test_tobacco_screening_met(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE, member_id="T"),
            procedures=[ProcedureEvent(code="99406", code_system=CodeSystem.CPT, event_date=date(2025, 3, 1))],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "TSC"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET


class TestBMI:
    def test_bmi_documented(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.FEMALE, member_id="T"),
            encounters=[EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2025, 6, 1))],
            vitals=[VitalEvent(vital_type=VitalType.BMI, value=25.0, event_date=date(2025, 6, 1))],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "BMI"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET


# =========================================================================
# Well-Child / Adolescent
# =========================================================================

class TestWCV:
    def test_wcv_with_visit(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(2018, 6, 1), gender=Gender.MALE, member_id="T"),
            procedures=[ProcedureEvent(code="99393", code_system=CodeSystem.CPT, event_date=date(2025, 8, 1))],
        )
        mdef = next((m for m in engine.measures if m.id == "WCV"), None)
        if mdef is None:
            pytest.skip("WCV measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_wcv_adult_not_applicable(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1990, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        mdef = next((m for m in engine.measures if m.id == "WCV"), None)
        if mdef is None:
            pytest.skip("WCV measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is False


# =========================================================================
# Osteoporosis
# =========================================================================

class TestOMW:
    def test_omw_applicable_female_67_plus(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1955, 1, 1), gender=Gender.FEMALE, member_id="T"),
            procedures=[ProcedureEvent(code="77080", code_system=CodeSystem.CPT, event_date=date(2025, 3, 1))],
        )
        mdef = next((m for m in engine.measures if m.id == "OMW"), None)
        if mdef is None:
            pytest.skip("OMW measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_omw_male_not_applicable(self, engine):
        store = MemberEventStore(
            demographics=Demographics(dob=date(1955, 1, 1), gender=Gender.MALE, member_id="T"),
        )
        mdef = next((m for m in engine.measures if m.id == "OMW"), None)
        if mdef is None:
            pytest.skip("OMW measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is False


# =========================================================================
# Follow-up after Hospitalization
# =========================================================================

class TestFUH:
    def test_fuh7_with_followup(self, engine):
        # FUH-7 uses a 1-month window from year-end; place encounters in December
        store = MemberEventStore(
            demographics=Demographics(dob=date(1970, 1, 1), gender=Gender.MALE, member_id="T"),
            diagnoses=[DiagnosisEvent(code="F32.9", status=DiagnosisStatus.ACTIVE, event_date=date(2025, 12, 1))],
            encounters=[
                EncounterEvent(encounter_type=EncounterType.INPATIENT, event_date=date(2025, 12, 1)),
                EncounterEvent(encounter_type=EncounterType.OUTPATIENT, event_date=date(2025, 12, 5)),
            ],
        )
        mdef = next((m for m in engine.measures if m.id == "FUH-7"), None)
        if mdef is None:
            pytest.skip("FUH-7 measure not found")
        result = engine.evaluate_measure(mdef, store)
        assert result.applicable is True
        assert result.status == MeasureStatus.MET


# =========================================================================
# Edge Cases
# =========================================================================

class TestEdgeCases:
    def test_empty_member(self, engine):
        """Engine should handle empty member without crashing."""
        store = MemberEventStore()
        results = engine.evaluate_member(store)
        # All measures should either be not-applicable or have appropriate results
        assert isinstance(results.measures, list)
        for m in results.measures:
            assert m.status in {MeasureStatus.NOT_APPLICABLE, MeasureStatus.GAP,
                                MeasureStatus.MET, MeasureStatus.EXCLUDED,
                                MeasureStatus.INDETERMINATE}

    def test_no_dob(self, engine):
        """Member with no DOB — all age-gated measures should be not applicable."""
        store = MemberEventStore(
            demographics=Demographics(dob=None, gender=Gender.FEMALE, member_id="T"),
        )
        results = engine.evaluate_member(store)
        for m in results.measures:
            assert m.applicable is False

    def test_conflicting_evidence(self, engine):
        """Member with both active and negated diabetes — active should win."""
        store = MemberEventStore(
            demographics=Demographics(dob=date(1965, 1, 1), gender=Gender.FEMALE, member_id="T"),
            diagnoses=[
                DiagnosisEvent(code="E11.9", status=DiagnosisStatus.NEGATED, event_date=date(2025, 1, 1)),
                DiagnosisEvent(code="E11.9", status=DiagnosisStatus.ACTIVE, event_date=date(2025, 6, 1)),
            ],
            labs=[LabEvent(test_type="A1C", value=7.2, event_date=date(2025, 9, 1))],
        )
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-TEST"), store,
        )
        assert result.applicable is True
        assert result.status == MeasureStatus.MET

    def test_measure_filter(self, engine):
        """evaluate_member with measure_ids should only return selected measures."""
        store = MemberEventStore(
            demographics=Demographics(dob=date(1965, 1, 1), gender=Gender.FEMALE, member_id="T"),
        )
        results = engine.evaluate_member(store, measure_ids=["CDC-A1C-TEST", "CBP"])
        assert len(results.measures) == 2
        ids = {m.measure_id for m in results.measures}
        assert ids == {"CDC-A1C-TEST", "CBP"}

    def test_audit_trace_populated(self, engine):
        """Every evaluation should produce a non-empty trace."""
        store = _diabetic_adult()
        store.labs.append(LabEvent(test_type="A1C", value=7.2, event_date=date(2025, 9, 1)))
        result = engine.evaluate_measure(
            next(m for m in engine.measures if m.id == "CDC-A1C-TEST"), store,
        )
        assert len(result.trace) > 0
        assert all(isinstance(t.rule, str) for t in result.trace)

    def test_results_to_dict(self, engine):
        """Results serialization should produce valid dict."""
        store = _diabetic_adult()
        store.labs.append(LabEvent(test_type="A1C", value=7.2, event_date=date(2025, 9, 1)))
        results = engine.evaluate_member(store, measure_ids=["CDC-A1C-TEST"])
        d = results.to_dict()
        assert "member_id" in d
        assert "measurement_year" in d
        assert "measures" in d
        assert len(d["measures"]) == 1
        m = d["measures"][0]
        assert m["id"] == "CDC-A1C-TEST"
        assert "trace" in m
        assert "evidence_used" in m
