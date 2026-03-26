"""Reusable rule primitives for HEDIS measure evaluation.

All primitives are pure functions that operate on MemberEventStore and return
(bool, detail_string, matched_evidence_list) tuples for audit traceability.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .types import (
    CodeSystem,
    DiagnosisStatus,
    EvidenceRef,
    EvidenceUsed,
    Gender,
    LabEvent,
    MemberEventStore,
    VitalEvent,
    VitalType,
)
from .valuesets.loader import load_valueset

# Type alias for primitive results: (matched, detail_str, evidence_list)
PrimitiveResult = tuple[bool, str, list[EvidenceUsed]]


def _normalize_code(code: str) -> str:
    return code.strip().upper().replace(".", "")


def _ref_to_source(ref: Optional[EvidenceRef]) -> Optional[dict]:
    if ref is None:
        return None
    return ref.to_dict() or None


# ---------------------------------------------------------------------------
# Demographics
# ---------------------------------------------------------------------------

def age_as_of(dob: Optional[date], as_of: date) -> Optional[int]:
    """Calculate age in years as of a given date."""
    if dob is None:
        return None
    age = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        age -= 1
    return age


def age_between(
    store: MemberEventStore,
    min_age: int,
    max_age: int,
    as_of: date,
) -> PrimitiveResult:
    """Check if member age is in [min_age, max_age] as of a date."""
    age = age_as_of(store.demographics.dob, as_of)
    if age is None:
        return False, "DOB unknown — cannot determine age", []
    matched = min_age <= age <= max_age
    detail = f"Age {age} as of {as_of} ({'within' if matched else 'outside'} {min_age}-{max_age})"
    return matched, detail, []


def gender_in(
    store: MemberEventStore,
    allowed: set[Gender],
) -> PrimitiveResult:
    """Check if member gender matches allowed set.

    When the allowed set includes BOTH male and female, the measure applies to
    the general population. In this case, UNKNOWN gender is also accepted
    (the measure does not gate on a specific sex).
    """
    g = store.demographics.gender
    # If both male and female are allowed, this is a population-level measure
    both_allowed = {Gender.MALE, Gender.FEMALE}.issubset(allowed)
    if both_allowed:
        matched = True
        detail = f"Gender {g.value} — measure applies to all genders"
    else:
        matched = g in allowed
        detail = f"Gender {g.value} {'matches' if matched else 'does not match'} {[a.value for a in allowed]}"
    return matched, detail, []


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

def has_diagnosis(
    store: MemberEventStore,
    valueset_id: str,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
    allowed_statuses: Optional[set[DiagnosisStatus]] = None,
) -> PrimitiveResult:
    """Check if any diagnosis code in the value set exists within the time window.

    Default allowed_statuses: {ACTIVE, HISTORICAL} (not negated, family_history, etc.)
    """
    if allowed_statuses is None:
        allowed_statuses = {DiagnosisStatus.ACTIVE, DiagnosisStatus.HISTORICAL}

    vs = load_valueset(valueset_id)
    evidence: list[EvidenceUsed] = []

    for dx in store.diagnoses:
        if dx.status not in allowed_statuses:
            continue
        norm = _normalize_code(dx.code)
        if norm not in vs:
            continue
        if window_start and dx.event_date and dx.event_date < window_start:
            continue
        if window_end and dx.event_date and dx.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="diagnosis",
            code=dx.code,
            code_system=dx.code_system.value,
            event_date=dx.event_date,
            source=_ref_to_source(dx.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} matching dx in {valueset_id}", evidence
    return False, f"No matching diagnosis in {valueset_id}", []


def has_any_diagnosis_code(
    store: MemberEventStore,
    codes: set[str],
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
    allowed_statuses: Optional[set[DiagnosisStatus]] = None,
) -> PrimitiveResult:
    """Check for diagnosis by explicit code set (not value set file)."""
    if allowed_statuses is None:
        allowed_statuses = {DiagnosisStatus.ACTIVE, DiagnosisStatus.HISTORICAL}

    norm_codes = {_normalize_code(c) for c in codes}
    evidence: list[EvidenceUsed] = []

    for dx in store.diagnoses:
        if dx.status not in allowed_statuses:
            continue
        if _normalize_code(dx.code) not in norm_codes:
            continue
        if window_start and dx.event_date and dx.event_date < window_start:
            continue
        if window_end and dx.event_date and dx.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="diagnosis",
            code=dx.code,
            code_system=dx.code_system.value,
            event_date=dx.event_date,
            source=_ref_to_source(dx.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} matching dx codes", evidence
    return False, "No matching diagnosis codes found", []


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------

def has_procedure(
    store: MemberEventStore,
    valueset_id: str,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check if any procedure code in the value set exists within the time window."""
    vs = load_valueset(valueset_id)
    evidence: list[EvidenceUsed] = []

    for proc in store.procedures:
        norm = _normalize_code(proc.code)
        if norm not in vs:
            continue
        if window_start and proc.event_date and proc.event_date < window_start:
            continue
        if window_end and proc.event_date and proc.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="procedure",
            code=proc.code,
            code_system=proc.code_system.value,
            event_date=proc.event_date,
            source=_ref_to_source(proc.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} matching procedures in {valueset_id}", evidence
    return False, f"No matching procedure in {valueset_id}", []


def has_any_procedure_code(
    store: MemberEventStore,
    codes: set[str],
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check for procedure by explicit code set."""
    norm_codes = {_normalize_code(c) for c in codes}
    evidence: list[EvidenceUsed] = []

    for proc in store.procedures:
        if _normalize_code(proc.code) not in norm_codes:
            continue
        if window_start and proc.event_date and proc.event_date < window_start:
            continue
        if window_end and proc.event_date and proc.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="procedure",
            code=proc.code,
            code_system=proc.code_system.value,
            event_date=proc.event_date,
            source=_ref_to_source(proc.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} matching procedure codes", evidence
    return False, "No matching procedure codes found", []


# ---------------------------------------------------------------------------
# Labs
# ---------------------------------------------------------------------------

def lab_exists(
    store: MemberEventStore,
    test_type: str,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check if a lab test of the given type exists within the time window."""
    test_upper = test_type.upper()
    evidence: list[EvidenceUsed] = []

    for lab in store.labs:
        if lab.test_type.upper() != test_upper:
            continue
        if window_start and lab.event_date and lab.event_date < window_start:
            continue
        if window_end and lab.event_date and lab.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="lab",
            code=lab.test_type,
            value=str(lab.value) if lab.value is not None else None,
            event_date=lab.event_date,
            source=_ref_to_source(lab.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} {test_type} lab(s)", evidence
    return False, f"No {test_type} lab found", []


def lab_value_in_range(
    store: MemberEventStore,
    test_type: str,
    comparator: str,  # "lt", "le", "gt", "ge", "eq"
    threshold: float,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
    use_latest: bool = True,
) -> PrimitiveResult:
    """Check if a lab value meets a threshold within the time window.

    If use_latest=True, only the most recent lab in the window is considered.
    """
    test_upper = test_type.upper()
    candidates: list[LabEvent] = []

    for lab in store.labs:
        if lab.test_type.upper() != test_upper:
            continue
        if lab.value is None:
            continue
        if window_start and lab.event_date and lab.event_date < window_start:
            continue
        if window_end and lab.event_date and lab.event_date > window_end:
            continue
        candidates.append(lab)

    if not candidates:
        return False, f"No {test_type} lab with value found in window", []

    if use_latest:
        # Sort by date descending, pick most recent (None dates go last)
        candidates.sort(key=lambda l: l.event_date or date.min, reverse=True)
        candidates = [candidates[0]]

    _ops = {
        "lt": lambda v, t: v < t,
        "le": lambda v, t: v <= t,
        "gt": lambda v, t: v > t,
        "ge": lambda v, t: v >= t,
        "eq": lambda v, t: v == t,
    }
    op = _ops.get(comparator)
    if op is None:
        return False, f"Unknown comparator: {comparator}", []

    for lab in candidates:
        assert lab.value is not None
        if op(lab.value, threshold):
            ev = EvidenceUsed(
                event_type="lab",
                code=lab.test_type,
                value=str(lab.value),
                event_date=lab.event_date,
                source=_ref_to_source(lab.evidence_ref),
            )
            detail = f"{test_type} value {lab.value} {comparator} {threshold} = True"
            return True, detail, [ev]

    lab = candidates[0]
    detail = f"{test_type} value {lab.value} {comparator} {threshold} = False"
    return False, detail, []


# ---------------------------------------------------------------------------
# Vitals / Blood Pressure
# ---------------------------------------------------------------------------

def bp_controlled(
    store: MemberEventStore,
    systolic_threshold: float,
    diastolic_threshold: float,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
    use_latest: bool = True,
) -> PrimitiveResult:
    """Check if blood pressure is controlled (below thresholds).

    By default uses the latest BP reading in the window.
    Controlled = systolic < systolic_threshold AND diastolic < diastolic_threshold.
    """
    candidates: list[VitalEvent] = []

    for v in store.vitals:
        if v.vital_type != VitalType.BP:
            continue
        if v.systolic is None or v.diastolic is None:
            continue
        if window_start and v.event_date and v.event_date < window_start:
            continue
        if window_end and v.event_date and v.event_date > window_end:
            continue
        candidates.append(v)

    if not candidates:
        return False, "No BP readings found in window", []

    if use_latest:
        candidates.sort(key=lambda v: v.event_date or date.min, reverse=True)
        candidates = [candidates[0]]

    bp = candidates[0]
    assert bp.systolic is not None and bp.diastolic is not None
    controlled = bp.systolic < systolic_threshold and bp.diastolic < diastolic_threshold
    ev = EvidenceUsed(
        event_type="vital",
        code="BP",
        value=f"{bp.systolic}/{bp.diastolic}",
        event_date=bp.event_date,
        source=_ref_to_source(bp.evidence_ref),
    )
    detail = (
        f"BP {bp.systolic}/{bp.diastolic} vs <{systolic_threshold}/<{diastolic_threshold} "
        f"= {'controlled' if controlled else 'uncontrolled'}"
    )
    return controlled, detail, [ev]


def vital_exists(
    store: MemberEventStore,
    vital_type: VitalType,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check if a vital reading of the given type exists in the window."""
    evidence: list[EvidenceUsed] = []

    for v in store.vitals:
        if v.vital_type != vital_type:
            continue
        if window_start and v.event_date and v.event_date < window_start:
            continue
        if window_end and v.event_date and v.event_date > window_end:
            continue
        val = str(v.value) if v.value is not None else f"{v.systolic}/{v.diastolic}"
        evidence.append(EvidenceUsed(
            event_type="vital",
            code=vital_type.value,
            value=val,
            event_date=v.event_date,
            source=_ref_to_source(v.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} {vital_type.value} reading(s)", evidence
    return False, f"No {vital_type.value} reading found", []


def bmi_in_range(
    store: MemberEventStore,
    min_bmi: Optional[float] = None,
    max_bmi: Optional[float] = None,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check if BMI is within a given range."""
    candidates: list[VitalEvent] = []

    for v in store.vitals:
        if v.vital_type != VitalType.BMI:
            continue
        if v.value is None:
            continue
        if window_start and v.event_date and v.event_date < window_start:
            continue
        if window_end and v.event_date and v.event_date > window_end:
            continue
        candidates.append(v)

    if not candidates:
        return False, "No BMI readings found in window", []

    candidates.sort(key=lambda v: v.event_date or date.min, reverse=True)
    bmi = candidates[0]
    assert bmi.value is not None
    in_range = True
    if min_bmi is not None and bmi.value < min_bmi:
        in_range = False
    if max_bmi is not None and bmi.value > max_bmi:
        in_range = False

    ev = EvidenceUsed(
        event_type="vital", code="BMI", value=str(bmi.value),
        event_date=bmi.event_date, source=_ref_to_source(bmi.evidence_ref),
    )
    return in_range, f"BMI {bmi.value} range [{min_bmi}-{max_bmi}]", [ev]


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------

def medication_present(
    store: MemberEventStore,
    class_or_valueset: str,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
    check_class: bool = True,
    check_valueset: bool = True,
) -> PrimitiveResult:
    """Check if a medication matching a class name or value set is present.

    Matches on normalized_class (e.g., "statin") or code in value set.
    Also does a case-insensitive substring match on medication name for flexibility.
    """
    # Medication class aliases — maps a search class to all classes it should match
    _CLASS_ALIASES: dict[str, set[str]] = {
        "ace_arb": {"ace_inhibitor", "arb", "ace_arb"},
        "antihypertensive": {"ace_inhibitor", "arb", "beta_blocker", "ccb", "diuretic", "antihypertensive"},
        "diabetes_med": {"metformin", "insulin", "sulfonylurea", "sglt2", "glp1", "diabetes_med"},
        "antipsychotic": {"antipsychotic", "atypical_antipsychotic", "typical_antipsychotic"},
        "adhd_med": {"adhd_med", "stimulant", "amphetamine", "methylphenidate", "atomoxetine", "guanfacine"},
        "antidepressant": {"antidepressant", "ssri", "snri", "tca", "maoi", "bupropion", "mirtazapine"},
        "osteoporosis_med": {"osteoporosis_med", "bisphosphonate", "denosumab", "teriparatide", "raloxifene"},
        "inhaled_corticosteroid": {"inhaled_corticosteroid", "ics", "laba_ics"},
        "antibiotic": {"antibiotic", "amoxicillin", "azithromycin", "cephalexin", "ciprofloxacin", "doxycycline", "levofloxacin", "metronidazole", "clindamycin", "trimethoprim", "sulfamethoxazole", "nitrofurantoin", "penicillin"},
        "systemic_corticosteroid": {"systemic_corticosteroid", "prednisone", "prednisolone", "methylprednisolone", "dexamethasone", "hydrocortisone"},
        "bronchodilator": {"bronchodilator", "albuterol", "levalbuterol", "ipratropium", "tiotropium", "formoterol", "salmeterol", "arformoterol", "umeclidinium"},
        "opioid": {"opioid", "codeine", "hydrocodone", "oxycodone", "morphine", "fentanyl", "tramadol", "hydromorphone", "oxymorphone", "meperidine", "methadone", "tapentadol"},
        "oud_pharmacotherapy": {"oud_pharmacotherapy", "buprenorphine", "naltrexone", "methadone", "suboxone", "vivitrol", "sublocade"},
        "benzodiazepine": {"benzodiazepine", "alprazolam", "clonazepam", "diazepam", "lorazepam", "temazepam", "triazolam", "midazolam"},
        "nsaid": {"nsaid", "ibuprofen", "naproxen", "diclofenac", "celecoxib", "meloxicam", "indomethacin", "piroxicam", "ketorolac"},
        "anticholinergic": {"anticholinergic", "diphenhydramine", "hydroxyzine", "oxybutynin", "tolterodine", "solifenacin", "benztropine", "trihexyphenidyl", "scopolamine"},
        "cns_active": {"cns_active", "benzodiazepine", "opioid", "antipsychotic", "hypnotic", "zolpidem", "eszopiclone", "suvorexant"},
        "high_risk_elderly": {"high_risk_elderly", "benzodiazepine", "anticholinergic", "barbiturate", "meprobamate", "carisoprodol", "chlorzoxazone", "metaxalone", "methocarbamol", "orphenadrine"},
        "muscle_relaxant": {"muscle_relaxant", "cyclobenzaprine", "carisoprodol", "chlorzoxazone", "metaxalone", "methocarbamol", "orphenadrine", "tizanidine", "baclofen"},
        "asthma": {"asthma", "asthma_controller", "asthma_reliever", "inhaled_corticosteroid", "ics", "laba_ics", "montelukast", "zafirlukast", "fluticasone", "budesonide", "beclomethasone", "mometasone", "ciclesonide", "salmeterol", "formoterol", "omalizumab", "mepolizumab", "benralizumab", "dupilumab", "albuterol", "levalbuterol", "ipratropium"},
        "asthma_controller": {"asthma_controller", "inhaled_corticosteroid", "ics", "laba_ics", "montelukast", "zafirlukast", "fluticasone", "budesonide", "beclomethasone", "mometasone", "ciclesonide", "salmeterol", "formoterol", "omalizumab", "mepolizumab", "benralizumab", "dupilumab"},
        "asthma_reliever": {"asthma_reliever", "albuterol", "levalbuterol", "ipratropium", "short_acting_beta_agonist", "saba"},
        "beta_blocker": {"beta_blocker", "metoprolol", "atenolol", "carvedilol", "bisoprolol", "propranolol", "nadolol", "nebivolol", "labetalol"},
    }

    evidence: list[EvidenceUsed] = []
    class_lower = class_or_valueset.lower()

    vs_codes: set[str] = set()
    if check_valueset:
        vs_codes = load_valueset(class_or_valueset)

    # Resolve class aliases
    match_classes = _CLASS_ALIASES.get(class_lower, {class_lower})

    for med in store.medications:
        matched = False
        # Check normalized_class (with alias expansion)
        if check_class and med.normalized_class.lower() in match_classes:
            matched = True
        # Check value set
        if not matched and vs_codes and _normalize_code(med.code) in vs_codes:
            matched = True
        # Check name substring as fallback
        if not matched and class_lower in med.name.lower():
            matched = True

        if not matched:
            continue

        # Date window check
        if window_start:
            end = med.end_date or med.start_date
            if end and end < window_start:
                continue
        if window_end and med.start_date and med.start_date > window_end:
            continue

        evidence.append(EvidenceUsed(
            event_type="medication",
            code=med.name,
            value=med.normalized_class or None,
            event_date=med.start_date,
            source=_ref_to_source(med.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} matching medication(s) for {class_or_valueset}", evidence
    return False, f"No matching medication for {class_or_valueset}", []


# ---------------------------------------------------------------------------
# Immunizations
# ---------------------------------------------------------------------------

def immunization_count(
    store: MemberEventStore,
    vaccine_type: str,
    min_count: int = 1,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check if the member has at least min_count immunizations of the given type."""
    vaccine_upper = vaccine_type.upper()
    evidence: list[EvidenceUsed] = []

    for imm in store.immunizations:
        if imm.vaccine_type.upper() != vaccine_upper:
            continue
        if window_start and imm.event_date and imm.event_date < window_start:
            continue
        if window_end and imm.event_date and imm.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="immunization",
            code=imm.code or imm.vaccine_type,
            code_system=imm.code_system.value,
            event_date=imm.event_date,
            source=_ref_to_source(imm.evidence_ref),
        ))

    met = len(evidence) >= min_count
    detail = f"Found {len(evidence)}/{min_count} {vaccine_type} immunization(s)"
    return met, detail, evidence


def immunization_by_valueset(
    store: MemberEventStore,
    valueset_id: str,
    min_count: int = 1,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check immunizations by value set of CVX/CPT codes."""
    vs = load_valueset(valueset_id)
    evidence: list[EvidenceUsed] = []

    for imm in store.immunizations:
        if _normalize_code(imm.code) not in vs:
            continue
        if window_start and imm.event_date and imm.event_date < window_start:
            continue
        if window_end and imm.event_date and imm.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="immunization",
            code=imm.code,
            code_system=imm.code_system.value,
            event_date=imm.event_date,
            source=_ref_to_source(imm.evidence_ref),
        ))

    met = len(evidence) >= min_count
    detail = f"Found {len(evidence)}/{min_count} immunizations matching {valueset_id}"
    return met, detail, evidence


# ---------------------------------------------------------------------------
# Encounters
# ---------------------------------------------------------------------------

def encounter_exists(
    store: MemberEventStore,
    encounter_types: Optional[set[str]] = None,
    window_start: Optional[date] = None,
    window_end: Optional[date] = None,
) -> PrimitiveResult:
    """Check if an encounter of the given type(s) exists in the window."""
    evidence: list[EvidenceUsed] = []

    for enc in store.encounters:
        if encounter_types:
            if enc.encounter_type.value not in encounter_types:
                continue
        if window_start and enc.event_date and enc.event_date < window_start:
            continue
        if window_end and enc.event_date and enc.event_date > window_end:
            continue
        evidence.append(EvidenceUsed(
            event_type="encounter",
            code=enc.encounter_type.value,
            event_date=enc.event_date,
            source=_ref_to_source(enc.evidence_ref),
        ))

    if evidence:
        return True, f"Found {len(evidence)} encounter(s)", evidence
    return False, "No matching encounter found", []


# ---------------------------------------------------------------------------
# Enrollment stub
# ---------------------------------------------------------------------------

def continuous_enrollment(
    store: MemberEventStore,
    window_start: date,
    window_end: date,
) -> PrimitiveResult:
    """Check whether enrollment periods cover the requested window.

    Returns False when enrollment data is unavailable so the caller can mark
    the measure as indeterminate instead of silently assuming coverage.
    """
    periods = sorted(store.enrollment_periods, key=lambda p: (p.start_date, p.end_date))
    if not periods:
        return False, "Enrollment data unavailable", []

    coverage_end = window_start
    for period in periods:
        if period.end_date < coverage_end:
            continue
        if period.start_date > coverage_end:
            return False, f"Enrollment gap before {period.start_date.isoformat()}", []
        if period.end_date >= window_end:
            source = f" via {period.source}" if period.source else ""
            return True, f"Continuous enrollment verified{source}", []
        coverage_end = period.end_date

    return False, f"Enrollment ends before {window_end.isoformat()}", []


# ---------------------------------------------------------------------------
# Composite helpers
# ---------------------------------------------------------------------------

def measurement_window(year: int) -> tuple[date, date]:
    """Return (start, end) of the measurement year."""
    return date(year, 1, 1), date(year, 12, 31)


def lookback_window(end_date: date, months: int) -> tuple[date, date]:
    """Return (start, end) for a lookback window of N months ending at end_date.

    Uses calendar-accurate month subtraction (not days * 30).
    """
    year_offset, month_offset = divmod(months, 12)
    start_month = end_date.month - month_offset
    start_year = end_date.year - year_offset
    if start_month <= 0:
        start_month += 12
        start_year -= 1
    # Clamp day to valid range for the target month
    import calendar
    max_day = calendar.monthrange(start_year, start_month)[1]
    start_day = min(end_date.day, max_day)
    start = date(start_year, start_month, start_day)
    return start, end_date


def lookback_from_year_end(year: int, months: int) -> tuple[date, date]:
    """Lookback N months from end of measurement year."""
    end = date(year, 12, 31)
    return lookback_window(end, months)


def extended_window(year: int, lookback_years: int) -> tuple[date, date]:
    """Extended window: lookback_years before the measurement year through year-end."""
    return date(year - lookback_years, 1, 1), date(year, 12, 31)
