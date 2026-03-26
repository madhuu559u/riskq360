"""Adapter: convert upstream extraction assertions JSON into MemberEventStore.

The upstream extractor produces per-member JSON "assertions" with fields like:
- member demographics (DOB, gender)
- encounter/service dates
- diagnosis/assertion concepts
- codes (ICD-10-CM, CPT/HCPCS)
- vitals (BP, BMI)
- labs (A1c value/date)
- medications (name string)
- evidence anchors (pdf, page_number, exact_quote, offsets)
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from ..types import (
    CodeSystem,
    Demographics,
    DiagnosisEvent,
    DiagnosisStatus,
    EnrollmentPeriod,
    EncounterEvent,
    EncounterType,
    EvidenceRef,
    Gender,
    ImmunizationEvent,
    LabEvent,
    MedicationEvent,
    MemberEventStore,
    ProcedureEvent,
    VitalEvent,
    VitalType,
)


def _parse_date(val: Any) -> Optional[date]:
    """Parse a date from various string formats."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%m-%d-%Y", "%Y%m%d"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def _parse_gender(val: Any) -> Gender:
    if val is None:
        return Gender.UNKNOWN
    g = str(val).strip().lower()
    if g in ("m", "male"):
        return Gender.MALE
    if g in ("f", "female"):
        return Gender.FEMALE
    if g in ("o", "other"):
        return Gender.OTHER
    return Gender.UNKNOWN


def _parse_enrollment_period(item: dict[str, Any]) -> Optional[EnrollmentPeriod]:
    start = _parse_date(item.get("start_date", item.get("start")))
    end = _parse_date(item.get("end_date", item.get("end")))
    if start is None or end is None:
        return None
    return EnrollmentPeriod(start_date=start, end_date=end, source=str(item.get("source", "")))


def _parse_evidence_ref(item: dict[str, Any]) -> Optional[EvidenceRef]:
    pdf = item.get("pdf", item.get("source_pdf", ""))
    page = item.get("page_number", item.get("page"))
    quote = item.get("exact_quote", item.get("text", ""))
    start = item.get("char_start")
    end = item.get("char_end")
    if not pdf and page is None and not quote:
        return None
    return EvidenceRef(
        pdf=str(pdf) if pdf else "",
        page_number=int(page) if page is not None else None,
        exact_quote=str(quote) if quote else "",
        char_start=int(start) if start is not None else None,
        char_end=int(end) if end is not None else None,
    )


def _parse_code_system(val: Any) -> CodeSystem:
    if val is None:
        return CodeSystem.ICD10CM
    s = str(val).strip().lower().replace("-", "").replace("_", "")
    mapping = {
        "icd10cm": CodeSystem.ICD10CM,
        "icd10": CodeSystem.ICD10CM,
        "icd9cm": CodeSystem.ICD9CM,
        "icd9": CodeSystem.ICD9CM,
        "cpt": CodeSystem.CPT,
        "hcpcs": CodeSystem.HCPCS,
        "loinc": CodeSystem.LOINC,
        "rxnorm": CodeSystem.RXNORM,
        "ndc": CodeSystem.NDC,
        "snomed": CodeSystem.SNOMED,
        "cvx": CodeSystem.CVX,
    }
    return mapping.get(s, CodeSystem.ICD10CM)


def _parse_diagnosis_status(val: Any) -> DiagnosisStatus:
    if val is None:
        return DiagnosisStatus.ACTIVE
    s = str(val).strip().lower().replace(" ", "_")
    try:
        return DiagnosisStatus(s)
    except ValueError:
        return DiagnosisStatus.ACTIVE


def _parse_encounter_type(val: Any) -> EncounterType:
    if val is None:
        return EncounterType.OUTPATIENT
    s = str(val).strip().lower()
    mapping = {
        "outpatient": EncounterType.OUTPATIENT,
        "office": EncounterType.OUTPATIENT,
        "inpatient": EncounterType.INPATIENT,
        "hospital": EncounterType.INPATIENT,
        "emergency": EncounterType.ED,
        "ed": EncounterType.ED,
        "er": EncounterType.ED,
        "telehealth": EncounterType.TELEHEALTH,
        "virtual": EncounterType.TELEHEALTH,
        "home": EncounterType.HOME,
    }
    return mapping.get(s, EncounterType.OTHER)


def _classify_lab_type(concept: str) -> Optional[str]:
    """Classify a concept string into a standard lab type."""
    concept_lower = concept.lower()
    patterns = {
        "A1C": ["a1c", "hba1c", "hemoglobin a1c", "glycated hemoglobin", "hgba1c"],
        "LDL": ["ldl", "low-density lipoprotein", "ldl cholesterol"],
        "HDL": ["hdl", "high-density lipoprotein"],
        "TOTAL_CHOLESTEROL": ["total cholesterol"],
        "TRIGLYCERIDES": ["triglyceride"],
        "CREATININE": ["creatinine", "serum creatinine"],
        "EGFR": ["egfr", "estimated glomerular", "gfr"],
        "UACR": ["uacr", "albumin-to-creatinine", "urine albumin"],
        "TSH": ["tsh", "thyroid stimulating"],
        "PSA": ["psa", "prostate-specific"],
        "INR": ["inr"],
        "BUN": ["bun", "blood urea nitrogen"],
        "ALT": ["alt", "alanine aminotransferase"],
        "AST": ["ast", "aspartate aminotransferase"],
        "WBC": ["wbc", "white blood cell"],
        "HEMOGLOBIN": ["hemoglobin", "hgb"],
        "PLATELET": ["platelet"],
        "POTASSIUM": ["potassium"],
        "SODIUM": ["sodium"],
        "GLUCOSE": ["glucose", "blood sugar", "fasting glucose"],
    }
    for lab_type, keywords in patterns.items():
        for kw in keywords:
            if kw in concept_lower:
                return lab_type
    return None


def _classify_vital_type(concept: str) -> Optional[VitalType]:
    concept_lower = concept.lower().replace("_", " ")
    if any(k in concept_lower for k in ["blood pressure", "bp", "systolic", "diastolic"]):
        return VitalType.BP
    if any(k in concept_lower for k in ["bmi", "body mass index"]):
        return VitalType.BMI
    if any(k in concept_lower for k in ["weight"]):
        return VitalType.WEIGHT
    if any(k in concept_lower for k in ["height"]):
        return VitalType.HEIGHT
    if any(k in concept_lower for k in ["temperature", "temp"]):
        return VitalType.TEMPERATURE
    if any(k in concept_lower for k in ["heart rate", "pulse"]):
        return VitalType.HEART_RATE
    return None


def _classify_medication_class(name: str) -> str:
    """Attempt to classify medication into a therapeutic class."""
    name_lower = name.lower()
    classes = {
        "statin": ["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin",
                    "lovastatin", "fluvastatin", "pitavastatin", "statin"],
        "ace_inhibitor": ["lisinopril", "enalapril", "ramipril", "benazepril",
                          "captopril", "fosinopril", "quinapril", "ace inhibitor"],
        "arb": ["losartan", "valsartan", "irbesartan", "olmesartan", "candesartan",
                "telmisartan", "azilsartan"],
        "beta_blocker": ["metoprolol", "atenolol", "propranolol", "carvedilol",
                         "bisoprolol", "nebivolol", "beta blocker"],
        "metformin": ["metformin"],
        "insulin": ["insulin", "lantus", "humalog", "novolog", "levemir", "tresiba"],
        "sulfonylurea": ["glipizide", "glyburide", "glimepiride"],
        "sglt2": ["empagliflozin", "dapagliflozin", "canagliflozin", "sglt2"],
        "glp1": ["semaglutide", "liraglutide", "dulaglutide", "exenatide", "glp-1"],
        "aspirin": ["aspirin"],
        "anticoagulant": ["warfarin", "apixaban", "rivaroxaban", "dabigatran", "edoxaban"],
        "antidepressant": ["sertraline", "fluoxetine", "escitalopram", "citalopram",
                           "paroxetine", "venlafaxine", "duloxetine", "bupropion", "ssri", "snri"],
        "antipsychotic": ["quetiapine", "olanzapine", "risperidone", "aripiprazole"],
        "opioid": ["oxycodone", "hydrocodone", "morphine", "fentanyl", "tramadol", "codeine"],
        "ppi": ["omeprazole", "pantoprazole", "esomeprazole", "lansoprazole"],
        "thyroid": ["levothyroxine", "synthroid"],
        "diuretic": ["furosemide", "hydrochlorothiazide", "spironolactone", "chlorthalidone"],
        "ccb": ["amlodipine", "nifedipine", "diltiazem", "verapamil"],
    }
    for cls, keywords in classes.items():
        for kw in keywords:
            if kw in name_lower:
                return cls
    return ""


_VACCINE_PATTERNS = {
    "influenza": ["influenza", "flu shot", "flu vaccine"],
    "pneumococcal": ["pneumococcal", "pneumovax", "prevnar"],
    "tdap": ["tdap", "tetanus", "diphtheria", "pertussis"],
    "mmr": ["mmr", "measles", "mumps", "rubella"],
    "varicella": ["varicella", "chickenpox"],
    "hpv": ["hpv", "gardasil", "human papillomavirus"],
    "hepatitis_b": ["hepatitis b", "hep b", "hepb"],
    "hepatitis_a": ["hepatitis a", "hep a", "hepa"],
    "meningococcal": ["meningococcal", "menactra", "menveo"],
    "polio": ["polio", "ipv"],
    "rotavirus": ["rotavirus", "rotateq"],
    "zoster": ["zoster", "shingles", "shingrix"],
    "covid19": ["covid", "sars-cov-2", "pfizer", "moderna"],
    "dtap": ["dtap"],
    "hib": ["hib", "haemophilus influenzae"],
    "pcv13": ["pcv13", "prevnar 13"],
    "ppsv23": ["ppsv23", "pneumovax 23"],
}


def _classify_vaccine(concept: str) -> str:
    concept_lower = concept.lower()
    for vtype, keywords in _VACCINE_PATTERNS.items():
        for kw in keywords:
            if kw in concept_lower:
                return vtype
    return concept_lower.replace(" ", "_")


def _extract_bp(text: str) -> tuple[Optional[float], Optional[float]]:
    """Extract systolic/diastolic from text like '120/80' or 'BP 130/85 mmHg'."""
    m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", text)
    if m:
        s = float(m.group(1))
        d = float(m.group(2))
        if _is_plausible_bp_values(s, d):
            return s, d
    return None, None


def _extract_numeric(text: str) -> Optional[float]:
    """Extract a numeric value from text."""
    m = re.search(r"[\d]+\.?[\d]*", str(text))
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass
    return None


def _is_plausible_bp_values(systolic: Any, diastolic: Any) -> bool:
    try:
        s = float(systolic)
        d = float(diastolic)
    except Exception:
        return False
    if not (70 <= s <= 260 and 40 <= d <= 160):
        return False
    if s <= d:
        return False
    return True


# ---------------------------------------------------------------------------
# Main adapter
# ---------------------------------------------------------------------------

def adapt_assertions(data: dict[str, Any]) -> MemberEventStore:
    """Convert an upstream assertions JSON dict into a MemberEventStore.

    Handles both:
    - MiniMax format: {demographics: {dob, gender}, assertions: [...], meta: {pdf}}
    - Generic typed format: {diagnoses: [...], procedures: [...], ...}

    The adapter is intentionally lenient — it extracts what it can and
    skips malformed entries.
    """
    store = MemberEventStore()

    # Demographics — check multiple sources
    demo = data.get("demographics") or {}
    summary = data.get("summary") or {}
    meta = data.get("meta") or {}
    pdf_name = meta.get("pdf", "")

    # DOB: demographics.dob > summary.dob_dates_found[0]
    dob = _parse_date(demo.get("dob", demo.get("date_of_birth")))
    if dob is None:
        dob_dates = summary.get("dob_dates_found", [])
        if dob_dates:
            dob = _parse_date(dob_dates[0])

    # Gender: demographics.gender > scan assertions for gender mentions
    gender = _parse_gender(demo.get("gender", demo.get("sex")))

    store.demographics = Demographics(
        dob=dob,
        gender=gender,
        member_id=str(data.get("member_id", demo.get("member_id", ""))),
        race=str(demo.get("race", "")),
        ethnicity=str(demo.get("ethnicity", "")),
    )

    for period in data.get("enrollment_periods", demo.get("enrollment_periods", [])):
        if isinstance(period, dict):
            parsed = _parse_enrollment_period(period)
            if parsed is not None:
                store.enrollment_periods.append(parsed)

    # Process typed lists if present (generic format)
    for dx in data.get("diagnoses", []):
        store.diagnoses.append(_adapt_diagnosis(dx))

    for proc in data.get("procedures", []):
        store.procedures.append(_adapt_procedure(proc))

    for lab in data.get("labs", data.get("lab_results", [])):
        store.labs.append(_adapt_lab(lab))

    for vital in data.get("vitals", []):
        store.vitals.append(_adapt_vital(vital))

    for med in data.get("medications", []):
        store.medications.append(_adapt_medication(med))

    for enc in data.get("encounters", []):
        store.encounters.append(_adapt_encounter(enc))

    for imm in data.get("immunizations", []):
        store.immunizations.append(_adapt_immunization(imm))

    # Process generic "assertions" list — classify each assertion
    # Inject pdf name into each assertion so evidence refs carry it
    assertions = data.get("assertions", data.get("events", []))
    for assertion in assertions:
        if pdf_name and not assertion.get("pdf"):
            assertion["pdf"] = pdf_name
        _classify_and_add(assertion, store)

    # Also create diagnosis events for ALL ICD codes in multi-code assertions
    # This ensures the HEDIS engine sees every ICD code, not just the primary
    for assertion in assertions:
        cat = str(assertion.get("category", "")).lower()
        if cat not in ("diagnosis", "assessment"):
            continue
        all_icds = assertion.get("icd_codes") or []
        primary_icds = assertion.get("icd_codes_primary") or all_icds
        # If there are multiple ICD codes, add secondary ones too
        primary_codes = {c.get("code", "") for c in primary_icds}
        for c in all_icds:
            code_val = c.get("code", "")
            if code_val and code_val not in primary_codes:
                store.diagnoses.append(DiagnosisEvent(
                    code=code_val,
                    code_system=CodeSystem.ICD10CM,
                    description=c.get("description", ""),
                    event_date=_date_from_assertion(assertion),
                    status=_parse_diagnosis_status(assertion.get("status")),
                    evidence_ref=_evidence_ref_from_assertion(assertion),
                ))

    # Generate encounters from assertions with effective_date (for encounter-based measures)
    seen_encounter_dates: set[str] = set()
    for assertion in assertions:
        edate = _date_from_assertion(assertion)
        if edate and str(edate) not in seen_encounter_dates:
            seen_encounter_dates.add(str(edate))
            store.encounters.append(EncounterEvent(
                encounter_type=EncounterType.OUTPATIENT,
                event_date=edate,
                evidence_ref=_evidence_ref_from_assertion(assertion),
            ))

    return store


def _adapt_diagnosis(item: dict[str, Any]) -> DiagnosisEvent:
    return DiagnosisEvent(
        code=str(item.get("code", item.get("icd10_code", item.get("icd_code", "")))),
        code_system=_parse_code_system(item.get("code_system")),
        description=str(item.get("description", item.get("text", ""))),
        event_date=_parse_date(item.get("date", item.get("event_date", item.get("dos")))),
        status=_parse_diagnosis_status(item.get("status", item.get("polarity"))),
        evidence_ref=_parse_evidence_ref(item),
    )


def _adapt_procedure(item: dict[str, Any]) -> ProcedureEvent:
    return ProcedureEvent(
        code=str(item.get("code", item.get("cpt_code", item.get("hcpcs_code", "")))),
        code_system=_parse_code_system(item.get("code_system", "cpt")),
        description=str(item.get("description", "")),
        event_date=_parse_date(item.get("date", item.get("event_date", item.get("dos")))),
        evidence_ref=_parse_evidence_ref(item),
    )


def _adapt_lab(item: dict[str, Any]) -> LabEvent:
    test_type = item.get("test_type", item.get("type", item.get("name", "")))
    classified = _classify_lab_type(str(test_type))
    return LabEvent(
        test_type=classified or str(test_type).upper(),
        value=_extract_numeric(item.get("value", "")),
        unit=str(item.get("unit", "")),
        event_date=_parse_date(item.get("date", item.get("event_date"))),
        evidence_ref=_parse_evidence_ref(item),
    )


def _adapt_vital(item: dict[str, Any]) -> VitalEvent:
    vtype = _classify_vital_type(str(item.get("type", item.get("vital_type", ""))))
    systolic = None
    diastolic = None
    value = None

    if vtype == VitalType.BP:
        systolic = _extract_numeric(item.get("systolic", ""))
        diastolic = _extract_numeric(item.get("diastolic", ""))
        if systolic is None and diastolic is None:
            raw = str(item.get("value", ""))
            systolic, diastolic = _extract_bp(raw)
        if not _is_plausible_bp_values(systolic, diastolic):
            systolic = None
            diastolic = None
    else:
        value = _extract_numeric(item.get("value", ""))

    return VitalEvent(
        vital_type=vtype or VitalType.BP,
        systolic=systolic,
        diastolic=diastolic,
        value=value,
        unit=str(item.get("unit", "")),
        event_date=_parse_date(item.get("date", item.get("event_date"))),
        evidence_ref=_parse_evidence_ref(item),
    )


def _adapt_medication(item: dict[str, Any]) -> MedicationEvent:
    name = str(item.get("name", item.get("drug_name", item.get("medication", ""))))
    return MedicationEvent(
        name=name,
        normalized_class=_classify_medication_class(name),
        code=str(item.get("code", "")),
        code_system=_parse_code_system(item.get("code_system", "rxnorm")),
        start_date=_parse_date(item.get("start_date", item.get("date"))),
        end_date=_parse_date(item.get("end_date")),
        evidence_ref=_parse_evidence_ref(item),
    )


def _adapt_encounter(item: dict[str, Any]) -> EncounterEvent:
    return EncounterEvent(
        encounter_type=_parse_encounter_type(item.get("type", item.get("visit_type"))),
        event_date=_parse_date(item.get("date", item.get("event_date", item.get("dos")))),
        provider=str(item.get("provider", "")),
        facility=str(item.get("facility", "")),
        evidence_ref=_parse_evidence_ref(item),
    )


def _adapt_immunization(item: dict[str, Any]) -> ImmunizationEvent:
    vaccine = str(item.get("vaccine_type", item.get("type", item.get("name", ""))))
    return ImmunizationEvent(
        vaccine_type=_classify_vaccine(vaccine),
        code=str(item.get("code", "")),
        code_system=_parse_code_system(item.get("code_system", "cvx")),
        event_date=_parse_date(item.get("date", item.get("event_date"))),
        dose_number=item.get("dose_number"),
        evidence_ref=_parse_evidence_ref(item),
    )


def _classify_and_add(assertion: dict[str, Any], store: MemberEventStore) -> None:
    """Classify a generic assertion into the appropriate event type and add to store."""
    atype = str(assertion.get("type", assertion.get("category", ""))).lower()
    concept = str(assertion.get("canonical_concept", assertion.get("concept", "")))

    # Diagnosis (including assessment — assessments in clinical charts are diagnoses)
    if atype in ("diagnosis", "condition", "problem", "assessment"):
        store.diagnoses.append(_adapt_diagnosis_from_assertion(assertion))
        return

    # Procedure
    if atype in ("procedure", "surgery", "screening"):
        store.procedures.append(_adapt_procedure_from_assertion(assertion))
        return

    # Lab
    if atype in ("lab", "laboratory", "lab_result", "lab_order"):
        store.labs.append(_adapt_lab_from_assertion(assertion))
        return

    # Vital
    if atype in ("vital", "vital_sign", "vitals"):
        store.vitals.append(_adapt_vital_from_assertion(assertion))
        return

    # Medication
    if atype in ("medication", "drug", "prescription", "rx"):
        store.medications.append(_adapt_medication_from_assertion(assertion))
        return

    # Encounter
    if atype in ("encounter", "visit"):
        store.encounters.append(_adapt_encounter_from_assertion(assertion))
        return

    # Immunization
    if atype in ("immunization", "vaccine", "vaccination"):
        store.immunizations.append(_adapt_immunization_from_assertion(assertion))
        return

    # Auto-classify by concept content
    lab_type = _classify_lab_type(concept)
    if lab_type:
        assertion.setdefault("test_type", lab_type)
        store.labs.append(_adapt_lab_from_assertion(assertion))
        return

    vital_type = _classify_vital_type(concept)
    if vital_type:
        assertion.setdefault("vital_type", vital_type.value)
        store.vitals.append(_adapt_vital_from_assertion(assertion))
        return

    # Check for ICD codes — MiniMax assertions use icd_codes list
    icd_codes = assertion.get("icd_codes") or []
    if icd_codes:
        store.diagnoses.append(_adapt_diagnosis_from_assertion(assertion))
        return

    # Check for single code field as ICD indicator
    code = str(assertion.get("code", assertion.get("icd10_code", "")))
    if re.match(r"^[A-Z]\d{2}", code):
        store.diagnoses.append(_adapt_diagnosis_from_assertion(assertion))
        return


# ---------------------------------------------------------------------------
# MiniMax assertion-specific adapters
# ---------------------------------------------------------------------------
# MiniMax assertions differ from generic typed dicts — they use:
#   - "category" instead of "type"
#   - "effective_date" instead of "date"
#   - "icd_codes" list of {code, description}
#   - "codes" list of {system, code, description}
#   - "structured" dict with bp_systolic/bp_diastolic for vitals
#   - "exact_quote", "page_number", "char_start", "char_end" for evidence

def _evidence_ref_from_assertion(a: dict[str, Any]) -> Optional[EvidenceRef]:
    """Build EvidenceRef from a MiniMax assertion dict."""
    pdf = a.get("pdf", a.get("source_pdf", ""))
    page = a.get("page_number")
    quote = a.get("exact_quote", "")
    start = a.get("char_start")
    end = a.get("char_end")
    if page is None and not quote:
        return None
    return EvidenceRef(
        pdf=str(pdf) if pdf else "",
        page_number=int(page) if page is not None else None,
        exact_quote=str(quote)[:500] if quote else "",
        char_start=int(start) if start is not None else None,
        char_end=int(end) if end is not None else None,
    )


def _date_from_assertion(a: dict[str, Any]) -> Optional[date]:
    """Extract the best date from a MiniMax assertion."""
    return (
        _parse_date(a.get("effective_date"))
        or _parse_date(a.get("inferred_date"))
        or _parse_date(a.get("date"))
        or _parse_date(a.get("event_date"))
        or _parse_date(a.get("dos"))
    )


def _codes_from_assertion(a: dict[str, Any]) -> list[dict[str, str]]:
    """Get code entries from a MiniMax assertion."""
    # MiniMax has both "icd_codes" and "codes"
    result = []
    for c in (a.get("icd_codes") or []):
        result.append({
            "code": c.get("code", ""),
            "system": "icd10cm",
            "description": c.get("description", ""),
        })
    for c in (a.get("codes") or []):
        sys = c.get("system", "icd10cm")
        code_val = c.get("code", "")
        if not any(r["code"] == code_val and r["system"] == sys for r in result):
            result.append({
                "code": code_val,
                "system": sys,
                "description": c.get("description", ""),
            })
    for c in (a.get("cpt2_codes") or []):
        result.append({"code": str(c), "system": "cpt", "description": ""})
    for c in (a.get("hcpcs_codes") or []):
        result.append({"code": str(c), "system": "hcpcs", "description": ""})
    return result


def _adapt_diagnosis_from_assertion(a: dict[str, Any]) -> DiagnosisEvent:
    """Adapt a MiniMax assertion to DiagnosisEvent."""
    # Pick the primary ICD code if available
    primary_icds = a.get("icd_codes_primary") or a.get("icd_codes") or []
    code = ""
    code_system = CodeSystem.ICD10CM
    description = a.get("canonical_concept", a.get("concept", a.get("text", "")))

    if primary_icds:
        code = primary_icds[0].get("code", "")
        description = primary_icds[0].get("description", "") or description
    else:
        # Fallback to codes list
        for c in (a.get("codes") or []):
            sys = (c.get("system") or "").lower()
            if "icd10" in sys or "icd9" in sys:
                code = c.get("code", "")
                code_system = _parse_code_system(sys)
                description = c.get("description", "") or description
                break

    # Also create entries for additional ICD codes
    return DiagnosisEvent(
        code=code,
        code_system=code_system,
        description=str(description),
        event_date=_date_from_assertion(a),
        status=_parse_diagnosis_status(a.get("status")),
        evidence_ref=_evidence_ref_from_assertion(a),
    )


def _adapt_procedure_from_assertion(a: dict[str, Any]) -> ProcedureEvent:
    """Adapt a MiniMax assertion to ProcedureEvent."""
    code = ""
    code_system = CodeSystem.CPT
    for c in (a.get("codes") or []):
        sys = (c.get("system") or "").lower()
        if sys in ("cpt", "cpt2", "hcpcs"):
            code = c.get("code", "")
            code_system = _parse_code_system(sys)
            break
    if not code:
        for c in (a.get("cpt2_codes") or []):
            code = str(c)
            break
    if not code:
        for c in (a.get("hcpcs_codes") or []):
            code = str(c)
            code_system = CodeSystem.HCPCS
            break

    return ProcedureEvent(
        code=code,
        code_system=code_system,
        description=str(a.get("canonical_concept", a.get("concept", ""))),
        event_date=_date_from_assertion(a),
        evidence_ref=_evidence_ref_from_assertion(a),
    )


def _adapt_lab_from_assertion(a: dict[str, Any]) -> LabEvent:
    """Adapt a MiniMax assertion to LabEvent."""
    concept = str(a.get("canonical_concept", a.get("concept", "")))
    test_type = a.get("test_type") or _classify_lab_type(concept) or concept.upper()[:30]

    # Extract value from structured data or text
    value = None
    unit = ""
    structured = a.get("structured") or {}
    if "value" in structured:
        value = _extract_numeric(str(structured["value"]))
        unit = str(structured.get("unit", ""))
    if value is None:
        # Try extracting from text/clean_text
        text = a.get("clean_text") or a.get("text") or ""
        value = _extract_numeric(text)

    return LabEvent(
        test_type=test_type,
        value=value,
        unit=unit,
        event_date=_date_from_assertion(a),
        evidence_ref=_evidence_ref_from_assertion(a),
    )


def _adapt_vital_from_assertion(a: dict[str, Any]) -> VitalEvent:
    """Adapt a MiniMax assertion to VitalEvent, using structured data for BP."""
    concept = str(a.get("canonical_concept", a.get("concept", "")))
    vtype = _classify_vital_type(concept) or VitalType.BP

    systolic = None
    diastolic = None
    value = None
    unit = ""

    structured = a.get("structured") or {}

    if vtype == VitalType.BP:
        # MiniMax stores BP in structured.bp_systolic / bp_diastolic
        systolic = _extract_numeric(str(structured.get("bp_systolic", ""))) if structured.get("bp_systolic") else None
        diastolic = _extract_numeric(str(structured.get("bp_diastolic", ""))) if structured.get("bp_diastolic") else None
        if systolic is None or diastolic is None:
            # Fallback: extract from text
            text = a.get("exact_quote") or a.get("text") or ""
            s, d = _extract_bp(text)
            systolic = systolic or s
            diastolic = diastolic or d
        if not _is_plausible_bp_values(systolic, diastolic):
            systolic = None
            diastolic = None
    elif vtype == VitalType.BMI:
        bmi_val = structured.get("bmi") or structured.get("value")
        if bmi_val is not None:
            value = _extract_numeric(str(bmi_val))
        if value is None:
            text = a.get("clean_text") or a.get("text") or ""
            value = _extract_numeric(text)
    else:
        val = structured.get("value")
        if val is not None:
            value = _extract_numeric(str(val))
            unit = str(structured.get("unit", ""))
        if value is None:
            text = a.get("clean_text") or a.get("text") or ""
            value = _extract_numeric(text)

    return VitalEvent(
        vital_type=vtype,
        systolic=systolic,
        diastolic=diastolic,
        value=value,
        unit=unit,
        event_date=_date_from_assertion(a),
        evidence_ref=_evidence_ref_from_assertion(a),
    )


def _adapt_medication_from_assertion(a: dict[str, Any]) -> MedicationEvent:
    """Adapt a MiniMax assertion to MedicationEvent."""
    name = str(
        a.get("medication_normalized")
        or a.get("canonical_concept")
        or a.get("concept")
        or a.get("text")
        or ""
    )
    return MedicationEvent(
        name=name,
        normalized_class=_classify_medication_class(name),
        start_date=_date_from_assertion(a),
        evidence_ref=_evidence_ref_from_assertion(a),
    )


def _adapt_encounter_from_assertion(a: dict[str, Any]) -> EncounterEvent:
    """Adapt a MiniMax assertion to EncounterEvent."""
    return EncounterEvent(
        encounter_type=_parse_encounter_type(a.get("encounter_type")),
        event_date=_date_from_assertion(a),
        evidence_ref=_evidence_ref_from_assertion(a),
    )


def _adapt_immunization_from_assertion(a: dict[str, Any]) -> ImmunizationEvent:
    """Adapt a MiniMax assertion to ImmunizationEvent."""
    concept = str(a.get("canonical_concept", a.get("concept", "")))
    return ImmunizationEvent(
        vaccine_type=_classify_vaccine(concept),
        event_date=_date_from_assertion(a),
        evidence_ref=_evidence_ref_from_assertion(a),
    )


def load_assertions_file(path: str | Path) -> MemberEventStore:
    """Load a member assertions JSON file and convert to MemberEventStore."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return adapt_assertions(data)
