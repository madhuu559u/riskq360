"""HEDIS Measure Engine — Rule evaluator.

Evaluates each measure definition against a MemberEventStore, producing
structured MeasureResult with full audit trace.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Optional

from .measure_def import (
    BPRule,
    DiagnosisRule,
    EncounterRule,
    ExclusionDef,
    ImmunizationRule,
    LabRule,
    MeasureDefinition,
    MedicationRule,
    NumeratorCriterion,
    NumeratorDef,
    ProcedureRule,
    VitalRule,
    load_all_measures,
    parse_measure_dict,
)
from .db_registry import load_measure_definition_dicts_from_db
from .primitives import (
    age_between,
    bp_controlled,
    continuous_enrollment,
    encounter_exists,
    extended_window,
    gender_in,
    has_any_diagnosis_code,
    has_any_procedure_code,
    has_diagnosis,
    has_procedure,
    immunization_by_valueset,
    immunization_count,
    lab_exists,
    lab_value_in_range,
    lookback_from_year_end,
    measurement_window,
    medication_present,
    vital_exists,
    bmi_in_range,
)
from .types import (
    ComplianceStatus,
    DiagnosisStatus,
    EvidenceUsed,
    GapDetail,
    Gender,
    MeasureResult,
    MeasureStatus,
    MemberEventStore,
    MemberHedisResults,
    TraceEntry,
    VitalType,
)

_DEFAULT_CATALOG = Path(__file__).parent / "catalog"


class HedisEngine:
    """Rule-based HEDIS measure evaluator."""

    def __init__(
        self,
        catalog_dir: Optional[Path] = None,
        measurement_year: int = 2025,
        require_enrollment_data: bool = False,
        prefer_db_catalog: Optional[bool] = None,
    ):
        self.measurement_year = measurement_year
        self.require_enrollment_data = require_enrollment_data
        self.catalog_dir = catalog_dir or _DEFAULT_CATALOG
        if prefer_db_catalog is None:
            self.prefer_db_catalog = (os.getenv("HEDIS_CATALOG_SOURCE") or "db_first").strip().lower() != "file_only"
        else:
            self.prefer_db_catalog = prefer_db_catalog
        self.measures: list[MeasureDefinition] = []
        self.reload_catalog()

    def reload_catalog(self) -> None:
        """Reload measure definitions from catalog directory."""
        measures: list[MeasureDefinition] = []

        if self.prefer_db_catalog:
            payloads = load_measure_definition_dicts_from_db(active_only=True) or []
            for payload in payloads:
                try:
                    measures.append(parse_measure_dict(payload))
                except Exception:
                    continue

        if not measures and self.catalog_dir.exists():
            measures = load_all_measures(self.catalog_dir)

        self.measures = measures

    def evaluate_member(
        self,
        store: MemberEventStore,
        measure_ids: Optional[list[str]] = None,
    ) -> MemberHedisResults:
        """Evaluate all (or selected) measures for a member.

        Args:
            store: Normalized member events.
            measure_ids: If provided, only evaluate these measure IDs.
        """
        results = MemberHedisResults(
            member_id=store.demographics.member_id,
            measurement_year=self.measurement_year,
        )

        for mdef in self.measures:
            if measure_ids and mdef.id not in measure_ids:
                continue
            result = self.evaluate_measure(mdef, store)
            results.measures.append(result)

        return results

    def evaluate_measure(
        self,
        mdef: MeasureDefinition,
        store: MemberEventStore,
    ) -> MeasureResult:
        """Evaluate a single measure against a member's events."""
        result = MeasureResult(
            measure_id=mdef.id,
            measure_name=mdef.name,
        )

        year = self.measurement_year
        my_start, my_end = measurement_window(year)

        # ------------------------------------------------------------------
        # Step 1: Eligibility (age + gender)
        # ------------------------------------------------------------------
        if not self._check_eligibility(mdef, store, result, my_end):
            result.applicable = False
            if result.status != MeasureStatus.INDETERMINATE:
                result.status = MeasureStatus.NOT_APPLICABLE
            return result

        # ------------------------------------------------------------------
        # Step 2: Denominator (condition/event required for measure)
        # ------------------------------------------------------------------
        if not self._check_denominator(mdef, store, result, my_start, my_end):
            result.applicable = False
            result.status = MeasureStatus.NOT_APPLICABLE
            result.eligibility_reason.append("Denominator criteria not met")
            return result

        result.applicable = True

        # ------------------------------------------------------------------
        # Step 3: Exclusions
        # ------------------------------------------------------------------
        if self._check_exclusions(mdef, store, result, my_start, my_end):
            result.status = MeasureStatus.EXCLUDED
            result.compliant = ComplianceStatus.UNKNOWN
            return result

        # ------------------------------------------------------------------
        # Step 4: Numerator (compliance)
        # ------------------------------------------------------------------
        self._check_numerator(mdef, store, result, my_start, my_end)

        # ------------------------------------------------------------------
        # Step 5: Confidence scoring
        # ------------------------------------------------------------------
        result.confidence = self._compute_confidence(result)

        return result

    # ------------------------------------------------------------------
    # Internal evaluation steps
    # ------------------------------------------------------------------

    def _check_eligibility(
        self,
        mdef: MeasureDefinition,
        store: MemberEventStore,
        result: MeasureResult,
        my_end: date,
    ) -> bool:
        """Check age and gender eligibility."""
        eligible = True

        # Age check
        if mdef.age:
            as_of_month, as_of_day = 12, 31
            if mdef.age.as_of:
                parts = mdef.age.as_of.split("-")
                if len(parts) == 2:
                    as_of_month, as_of_day = int(parts[0]), int(parts[1])
            as_of_date = date(self.measurement_year, as_of_month, as_of_day)

            matched, detail, _ = age_between(store, mdef.age.min_age, mdef.age.max_age, as_of_date)
            result.trace.append(TraceEntry(rule="age_check", result=matched, detail=detail))
            if matched:
                result.eligibility_reason.append(detail)
            else:
                result.eligibility_reason.append(f"Age not eligible: {detail}")
                eligible = False

        # Gender check
        if mdef.gender:
            allowed = {Gender(g) for g in mdef.gender if g in [e.value for e in Gender]}
            if allowed:
                matched, detail, _ = gender_in(store, allowed)
                result.trace.append(TraceEntry(rule="gender_check", result=matched, detail=detail))
                if matched:
                    result.eligibility_reason.append(detail)
                else:
                    result.eligibility_reason.append(f"Gender not eligible: {detail}")
                    eligible = False

        # Continuous enrollment stub
        if mdef.continuous_enrollment:
            my_start = date(self.measurement_year, 1, 1)
            matched, detail, _ = continuous_enrollment(store, my_start, my_end)
            result.trace.append(TraceEntry(rule="enrollment_check", result=matched, detail=detail))
            if matched:
                result.eligibility_reason.append(detail)
            elif store.enrollment_periods:
                result.eligibility_reason.append(f"Enrollment not eligible: {detail}")
                eligible = False
            elif not self.require_enrollment_data:
                result.eligibility_reason.append("Enrollment data unavailable — compatibility mode assumed enrolled")
            else:
                result.eligibility_reason.append(detail)
                result.missing_data.append("continuous_enrollment")
                result.status = MeasureStatus.INDETERMINATE
                return False

        return eligible

    def _check_denominator(
        self,
        mdef: MeasureDefinition,
        store: MemberEventStore,
        result: MeasureResult,
        my_start: date,
        my_end: date,
    ) -> bool:
        """Check denominator criteria — does the member qualify for this measure?"""
        if mdef.denominator_age_only:
            result.trace.append(TraceEntry(
                rule="denominator_age_only", result=True,
                detail="Denominator = age/gender eligible population",
            ))
            return True

        in_denom = True

        # Diagnosis-based denominator
        if mdef.denominator_diagnosis:
            dx_rule = mdef.denominator_diagnosis
            ws, we = self._window_from_months(dx_rule.lookback_months, my_end)
            statuses = {DiagnosisStatus(s) for s in dx_rule.status}

            if dx_rule.valueset:
                matched, detail, evidence = has_diagnosis(store, dx_rule.valueset, ws, we, statuses)
            elif dx_rule.codes:
                matched, detail, evidence = has_any_diagnosis_code(
                    store, set(dx_rule.codes), ws, we, statuses,
                )
            else:
                matched, detail, evidence = False, "No valueset or codes for denominator dx", []

            result.trace.append(TraceEntry(
                rule="denominator_diagnosis", result=matched, detail=detail,
                evidence=[e.to_dict() for e in evidence],
            ))
            result.evidence_used.extend(evidence)
            if not matched:
                in_denom = False

        # Procedure-based denominator
        if mdef.denominator_procedure:
            proc_rule = mdef.denominator_procedure
            ws, we = self._window_from_months(proc_rule.window_months, my_end)

            if proc_rule.valueset:
                matched, detail, evidence = has_procedure(store, proc_rule.valueset, ws, we)
            elif proc_rule.codes:
                matched, detail, evidence = has_any_procedure_code(
                    store, set(proc_rule.codes), ws, we,
                )
            else:
                matched, detail, evidence = False, "No valueset or codes for denominator proc", []

            result.trace.append(TraceEntry(
                rule="denominator_procedure", result=matched, detail=detail,
                evidence=[e.to_dict() for e in evidence],
            ))
            result.evidence_used.extend(evidence)
            if not matched:
                in_denom = False

        # Secondary diagnosis-based denominator (for dual-condition measures like SMC, SMD)
        if mdef.denominator_diagnosis_secondary:
            dx_rule2 = mdef.denominator_diagnosis_secondary
            ws, we = self._window_from_months(dx_rule2.lookback_months, my_end)
            statuses2 = {DiagnosisStatus(s) for s in dx_rule2.status}

            if dx_rule2.valueset:
                matched, detail, evidence = has_diagnosis(store, dx_rule2.valueset, ws, we, statuses2)
            elif dx_rule2.codes:
                matched, detail, evidence = has_any_diagnosis_code(
                    store, set(dx_rule2.codes), ws, we, statuses2,
                )
            else:
                matched, detail, evidence = False, "No valueset or codes for secondary dx", []

            result.trace.append(TraceEntry(
                rule="denominator_diagnosis_secondary", result=matched, detail=detail,
                evidence=[e.to_dict() for e in evidence],
            ))
            result.evidence_used.extend(evidence)
            if not matched:
                in_denom = False

        # Encounter-based denominator
        if mdef.denominator_encounter:
            enc_rule = mdef.denominator_encounter
            ws, we = self._window_from_months(enc_rule.window_months, my_end)
            enc_types = set(enc_rule.encounter_types) if enc_rule.encounter_types else None

            matched, detail, evidence = encounter_exists(store, enc_types, ws, we)
            result.trace.append(TraceEntry(
                rule="denominator_encounter", result=matched, detail=detail,
                evidence=[e.to_dict() for e in evidence],
            ))
            result.evidence_used.extend(evidence)
            if not matched:
                in_denom = False

        # Medication-based denominator (e.g., AMR requires asthma medication)
        if mdef.denominator_medication:
            med_rule = mdef.denominator_medication
            ws, we = self._window_from_months(med_rule.window_months, my_end)

            matched, detail, evidence = medication_present(
                store, med_rule.medication_class or med_rule.valueset, ws, we,
            )
            result.trace.append(TraceEntry(
                rule="denominator_medication", result=matched, detail=detail,
                evidence=[e.to_dict() for e in evidence],
            ))
            result.evidence_used.extend(evidence)
            if not matched:
                in_denom = False

        # If no denominator criteria defined, treat as age/gender only
        if (mdef.denominator_diagnosis is None
                and mdef.denominator_diagnosis_secondary is None
                and mdef.denominator_procedure is None
                and mdef.denominator_encounter is None
                and mdef.denominator_medication is None):
            result.trace.append(TraceEntry(
                rule="denominator_default", result=True,
                detail="No specific denominator criteria — population-based measure",
            ))

        return in_denom

    def _check_exclusions(
        self,
        mdef: MeasureDefinition,
        store: MemberEventStore,
        result: MeasureResult,
        my_start: date,
        my_end: date,
    ) -> bool:
        """Check exclusion criteria. Returns True if excluded."""
        for excl in mdef.exclusions:
            ws, we = self._window_from_months(excl.lookback_months, my_end)

            if excl.exclusion_type == "diagnosis":
                if excl.valueset:
                    matched, detail, evidence = has_diagnosis(store, excl.valueset, ws, we)
                elif excl.codes:
                    matched, detail, evidence = has_any_diagnosis_code(
                        store, set(excl.codes), ws, we,
                    )
                else:
                    continue
            elif excl.exclusion_type == "procedure":
                if excl.valueset:
                    matched, detail, evidence = has_procedure(store, excl.valueset, ws, we)
                elif excl.codes:
                    matched, detail, evidence = has_any_procedure_code(
                        store, set(excl.codes), ws, we,
                    )
                else:
                    continue
            elif excl.exclusion_type == "medication":
                class_name = excl.valueset or (excl.codes[0] if excl.codes else "")
                matched, detail, evidence = medication_present(store, class_name, ws, we)
            else:
                continue

            rule_name = f"exclusion_{excl.exclusion_type}_{excl.valueset or 'codes'}"
            result.trace.append(TraceEntry(
                rule=rule_name, result=matched, detail=detail,
                evidence=[e.to_dict() for e in evidence],
            ))

            if matched:
                desc = excl.description or f"Excluded by {excl.exclusion_type}: {excl.valueset}"
                result.exclusion_reason = desc
                result.evidence_used.extend(evidence)
                return True

        return False

    def _check_numerator(
        self,
        mdef: MeasureDefinition,
        store: MemberEventStore,
        result: MeasureResult,
        my_start: date,
        my_end: date,
    ) -> None:
        """Check numerator criteria — is the member compliant?

        When ``mdef.inverse`` is True the numerator describes an *undesirable*
        event.  Satisfaction of the numerator means the bad thing happened (gap),
        and non-satisfaction means it did not (met).
        """
        if mdef.numerator is None:
            result.compliant = ComplianceStatus.UNKNOWN
            result.status = MeasureStatus.INDETERMINATE
            result.missing_data.append("No numerator criteria defined")
            return

        ndef = mdef.numerator
        inverse = mdef.inverse

        # all_of: every criterion must be met
        if ndef.all_of:
            all_met = True
            for criterion in ndef.all_of:
                met, detail, evidence, gap = self._eval_criterion(criterion, store, my_start, my_end)
                result.trace.append(TraceEntry(
                    rule=f"numerator_all_{criterion.criterion_type}",
                    result=met, detail=detail,
                    evidence=[e.to_dict() for e in evidence],
                ))
                if met:
                    result.evidence_used.extend(evidence)
                    result.compliance_reason.append(detail)
                else:
                    all_met = False
                    if gap:
                        result.gaps.append(gap)
                    else:
                        result.gaps.append(GapDetail(
                            gap_type=f"missing_{criterion.criterion_type}",
                            description=detail,
                        ))

            if inverse:
                # Inverse: numerator satisfied = bad thing happened = gap
                if all_met:
                    result.compliant = ComplianceStatus.NON_COMPLIANT
                    result.status = MeasureStatus.GAP
                else:
                    result.compliant = ComplianceStatus.COMPLIANT
                    result.status = MeasureStatus.MET
                    result.gaps.clear()
            else:
                if all_met:
                    result.compliant = ComplianceStatus.COMPLIANT
                    result.status = MeasureStatus.MET
                else:
                    result.compliant = ComplianceStatus.NON_COMPLIANT
                    result.status = MeasureStatus.GAP

        # any_of: at least one criterion must be met
        elif ndef.any_of:
            any_met = False
            for criterion in ndef.any_of:
                met, detail, evidence, gap = self._eval_criterion(criterion, store, my_start, my_end)
                result.trace.append(TraceEntry(
                    rule=f"numerator_any_{criterion.criterion_type}",
                    result=met, detail=detail,
                    evidence=[e.to_dict() for e in evidence],
                ))
                if met:
                    any_met = True
                    result.evidence_used.extend(evidence)
                    result.compliance_reason.append(detail)
                else:
                    if gap:
                        result.gaps.append(gap)

            if inverse:
                # Inverse: any numerator criterion satisfied = bad thing happened = gap
                if any_met:
                    result.compliant = ComplianceStatus.NON_COMPLIANT
                    result.status = MeasureStatus.GAP
                else:
                    result.compliant = ComplianceStatus.COMPLIANT
                    result.status = MeasureStatus.MET
                    result.gaps.clear()
            else:
                if any_met:
                    result.compliant = ComplianceStatus.COMPLIANT
                    result.status = MeasureStatus.MET
                    result.gaps.clear()  # Clear gaps since one path succeeded
                else:
                    result.compliant = ComplianceStatus.NON_COMPLIANT
                    result.status = MeasureStatus.GAP

    def _eval_criterion(
        self,
        criterion: NumeratorCriterion,
        store: MemberEventStore,
        my_start: date,
        my_end: date,
    ) -> tuple[bool, str, list[EvidenceUsed], Optional[GapDetail]]:
        """Evaluate a single numerator criterion. Returns (met, detail, evidence, gap)."""
        ctype = criterion.criterion_type

        if ctype == "lab_exists" and criterion.lab:
            lab_rule = criterion.lab
            ws, we = self._window_from_months(lab_rule.window_months, my_end)
            matched, detail, evidence = lab_exists(store, lab_rule.lab, ws, we)
            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="missing_lab",
                    description=f"Missing {lab_rule.lab} lab test",
                    required_event=lab_rule.lab,
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        if ctype == "lab_value" and criterion.lab:
            lab_rule = criterion.lab
            ws, we = self._window_from_months(lab_rule.window_months, my_end)
            # First check if lab exists
            exists, _, _ = lab_exists(store, lab_rule.lab, ws, we)
            if not exists:
                gap = GapDetail(
                    gap_type="missing_lab",
                    description=f"Missing {lab_rule.lab} lab test",
                    required_event=lab_rule.lab,
                    window_start=ws, window_end=we,
                )
                return False, f"No {lab_rule.lab} lab found in window", [], gap

            matched, detail, evidence = lab_value_in_range(
                store, lab_rule.lab, lab_rule.comparator,
                lab_rule.threshold or 0, ws, we, lab_rule.use_latest,
            )
            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="value_out_of_range",
                    description=f"{lab_rule.lab} value not {lab_rule.comparator} {lab_rule.threshold}",
                    required_event=lab_rule.lab,
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        if ctype == "procedure" and criterion.procedure:
            proc_rule = criterion.procedure
            if proc_rule.lookback_years > 0:
                ws, we = extended_window(self.measurement_year, proc_rule.lookback_years)
            else:
                ws, we = self._window_from_months(proc_rule.window_months, my_end)

            if proc_rule.valueset:
                matched, detail, evidence = has_procedure(store, proc_rule.valueset, ws, we)
            elif proc_rule.codes:
                matched, detail, evidence = has_any_procedure_code(
                    store, set(proc_rule.codes), ws, we,
                )
            else:
                return False, "No valueset or codes for procedure criterion", [], None

            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="missing_procedure",
                    description=criterion.description or f"Missing procedure from {proc_rule.valueset}",
                    required_event=proc_rule.valueset,
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        if ctype == "diagnosis" and criterion.diagnosis:
            dx_rule = criterion.diagnosis
            ws, we = self._window_from_months(dx_rule.lookback_months, my_end)
            statuses = {DiagnosisStatus(s) for s in dx_rule.status}

            if dx_rule.valueset:
                matched, detail, evidence = has_diagnosis(store, dx_rule.valueset, ws, we, statuses)
            elif dx_rule.codes:
                matched, detail, evidence = has_any_diagnosis_code(
                    store, set(dx_rule.codes), ws, we, statuses,
                )
            else:
                return False, "No valueset or codes for diagnosis criterion", [], None

            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="missing_diagnosis",
                    description=criterion.description or f"No diagnosis from {dx_rule.valueset}",
                    required_event=dx_rule.valueset,
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        if ctype == "bp_controlled" and criterion.bp:
            bp_rule = criterion.bp
            ws, we = self._window_from_months(bp_rule.window_months, my_end)
            matched, detail, evidence = bp_controlled(
                store, bp_rule.systolic_threshold, bp_rule.diastolic_threshold,
                ws, we, bp_rule.use_latest,
            )
            gap = None
            if not matched:
                if not evidence:
                    gap = GapDetail(
                        gap_type="missing_vital",
                        description="No blood pressure reading found",
                        required_event="BP",
                        window_start=ws, window_end=we,
                    )
                else:
                    gap = GapDetail(
                        gap_type="value_out_of_range",
                        description=f"BP not controlled (<{bp_rule.systolic_threshold}/<{bp_rule.diastolic_threshold})",
                        required_event="BP_controlled",
                        window_start=ws, window_end=we,
                    )
            return matched, detail, evidence, gap

        if ctype == "medication" and criterion.medication:
            med_rule = criterion.medication
            ws, we = self._window_from_months(med_rule.window_months, my_end)
            class_name = med_rule.medication_class or med_rule.valueset
            matched, detail, evidence = medication_present(store, class_name, ws, we)
            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="missing_medication",
                    description=f"No {class_name} medication found",
                    required_event=class_name,
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        if ctype == "immunization" and criterion.immunization:
            imm_rule = criterion.immunization
            ws = None
            we = None
            if imm_rule.window_months:
                ws, we = self._window_from_months(imm_rule.window_months, my_end)

            if imm_rule.valueset:
                matched, detail, evidence = immunization_by_valueset(
                    store, imm_rule.valueset, imm_rule.min_count, ws, we,
                )
                # Fall back to vaccine_type matching if code-based match missed
                if not matched and imm_rule.vaccine_type:
                    matched, detail, evidence = immunization_count(
                        store, imm_rule.vaccine_type, imm_rule.min_count, ws, we,
                    )
            else:
                matched, detail, evidence = immunization_count(
                    store, imm_rule.vaccine_type, imm_rule.min_count, ws, we,
                )
            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="missing_immunization",
                    description=f"Missing {imm_rule.vaccine_type or imm_rule.valueset} immunization",
                    required_event=imm_rule.vaccine_type or imm_rule.valueset,
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        if ctype == "vital" and criterion.vital:
            vital_rule = criterion.vital
            ws, we = self._window_from_months(vital_rule.window_months, my_end)
            vtype_map = {
                "bp": VitalType.BP, "blood_pressure": VitalType.BP,
                "bmi": VitalType.BMI, "weight": VitalType.WEIGHT,
                "height": VitalType.HEIGHT,
            }
            vtype = vtype_map.get(vital_rule.vital_type.lower(), VitalType.BP)

            if vtype == VitalType.BMI and (vital_rule.min_value is not None or vital_rule.max_value is not None):
                matched, detail, evidence = bmi_in_range(
                    store, vital_rule.min_value, vital_rule.max_value, ws, we,
                )
            else:
                matched, detail, evidence = vital_exists(store, vtype, ws, we)

            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="missing_vital",
                    description=f"Missing {vital_rule.vital_type} reading",
                    required_event=vital_rule.vital_type,
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        if ctype == "encounter" and criterion.encounter:
            enc_rule = criterion.encounter
            ws, we = self._window_from_months(enc_rule.window_months, my_end)
            enc_types = set(enc_rule.encounter_types) if enc_rule.encounter_types else None
            matched, detail, evidence = encounter_exists(store, enc_types, ws, we)
            gap = None
            if not matched:
                gap = GapDetail(
                    gap_type="missing_encounter",
                    description=criterion.description or "Missing required encounter",
                    required_event="encounter",
                    window_start=ws, window_end=we,
                )
            return matched, detail, evidence, gap

        return False, f"Unknown criterion type: {ctype}", [], None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _window_from_months(self, months: int, end_date: date) -> tuple[date, date]:
        """Compute window start from months before end_date."""
        ws, we = lookback_from_year_end(self.measurement_year, months)
        return ws, end_date

    def _compute_confidence(self, result: MeasureResult) -> float:
        """Compute a deterministic confidence score based on evidence completeness.

        1.0 = full evidence, no missing data
        0.0 = no evidence at all
        """
        if not result.applicable:
            return 1.0
        if result.status == MeasureStatus.EXCLUDED:
            return 1.0
        if result.status == MeasureStatus.MET and result.evidence_used:
            return 1.0
        if result.status == MeasureStatus.GAP:
            # Confidence is lower if missing data vs. out-of-range values
            missing_count = len(result.missing_data)
            gap_count = len(result.gaps)
            if gap_count == 0:
                return 0.8
            missing_gaps = sum(1 for g in result.gaps if g.gap_type.startswith("missing_"))
            if missing_gaps > 0:
                return 0.5  # We're not sure — data may exist but wasn't extracted
            return 0.9  # Data exists but out of range — we're confident it's a gap
        return 0.5  # Indeterminate
