"""Measure definition schema — loads YAML measure definitions into evaluable structures.

A measure YAML looks like:

    id: "CDC-A1C-TEST"
    name: "Diabetes Care - HbA1c Testing"
    version: "2025"
    domain: "diabetes"
    description: "Percentage of members with diabetes who had an HbA1c test"
    eligibility:
      age: {min: 18, max: 75, as_of: "12-31"}
      gender: ["male", "female"]
      continuous_enrollment: true
    denominator:
      requires_diagnosis:
        valueset: "VS_DIABETES_ICD10"
        lookback_months: 24
    exclusions:
      - type: "diagnosis"
        valueset: "VS_HOSPICE"
      - type: "diagnosis"
        valueset: "VS_PREGNANCY_ICD10"
    numerator:
      any_of:
        - type: "lab_exists"
          lab: "A1C"
          window_months: 12
    valuesets_needed:
      - VS_DIABETES_ICD10
      - VS_HOSPICE
      - VS_PREGNANCY_ICD10
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class AgeRule:
    min_age: int = 0
    max_age: int = 150
    as_of: str = "12-31"  # MM-DD within measurement year


@dataclass
class DiagnosisRule:
    valueset: str = ""
    codes: list[str] = field(default_factory=list)
    lookback_months: int = 12
    status: list[str] = field(default_factory=lambda: ["active", "historical"])


@dataclass
class ProcedureRule:
    valueset: str = ""
    codes: list[str] = field(default_factory=list)
    window_months: int = 12
    lookback_years: int = 0  # for extended windows


@dataclass
class LabRule:
    lab: str = ""
    window_months: int = 12
    comparator: str = ""  # lt, le, gt, ge, eq
    threshold: Optional[float] = None
    use_latest: bool = True


@dataclass
class BPRule:
    systolic_threshold: float = 140.0
    diastolic_threshold: float = 90.0
    window_months: int = 12
    use_latest: bool = True


@dataclass
class MedicationRule:
    medication_class: str = ""
    valueset: str = ""
    window_months: int = 12


@dataclass
class ImmunizationRule:
    vaccine_type: str = ""
    valueset: str = ""
    min_count: int = 1
    window_months: Optional[int] = None  # None = any time


@dataclass
class VitalRule:
    vital_type: str = ""
    window_months: int = 12
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class EncounterRule:
    encounter_types: list[str] = field(default_factory=list)
    window_months: int = 12


@dataclass
class NumeratorCriterion:
    """A single numerator criterion — one thing that must be met."""
    criterion_type: str = ""  # "lab_exists", "lab_value", "procedure", "diagnosis",
                               # "bp_controlled", "medication", "immunization",
                               # "vital", "encounter"
    lab: Optional[LabRule] = None
    procedure: Optional[ProcedureRule] = None
    diagnosis: Optional[DiagnosisRule] = None
    bp: Optional[BPRule] = None
    medication: Optional[MedicationRule] = None
    immunization: Optional[ImmunizationRule] = None
    vital: Optional[VitalRule] = None
    encounter: Optional[EncounterRule] = None
    description: str = ""


@dataclass
class NumeratorDef:
    """Numerator definition — all_of or any_of criteria."""
    all_of: list[NumeratorCriterion] = field(default_factory=list)
    any_of: list[NumeratorCriterion] = field(default_factory=list)


@dataclass
class ExclusionDef:
    """A single exclusion criterion."""
    exclusion_type: str = ""  # "diagnosis", "procedure", "medication", "age"
    valueset: str = ""
    codes: list[str] = field(default_factory=list)
    lookback_months: int = 12
    description: str = ""


@dataclass
class MeasureDefinition:
    """Complete measure definition loaded from YAML."""
    id: str = ""
    name: str = ""
    version: str = "2025"
    domain: str = ""
    description: str = ""

    # Eligibility
    age: Optional[AgeRule] = None
    gender: list[str] = field(default_factory=lambda: ["male", "female"])
    continuous_enrollment: bool = False

    # Denominator
    denominator_diagnosis: Optional[DiagnosisRule] = None
    denominator_diagnosis_secondary: Optional[DiagnosisRule] = None
    denominator_procedure: Optional[ProcedureRule] = None
    denominator_encounter: Optional[EncounterRule] = None
    denominator_medication: Optional[MedicationRule] = None
    denominator_age_only: bool = False  # true = age+gender is the denominator

    # Exclusions
    exclusions: list[ExclusionDef] = field(default_factory=list)

    # Numerator
    numerator: Optional[NumeratorDef] = None

    # Behaviour
    inverse: bool = False  # When True, numerator = undesirable event; NOT satisfied = "met"

    # Metadata
    valuesets_needed: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------

def _parse_age_rule(data: dict[str, Any]) -> AgeRule:
    return AgeRule(
        min_age=int(data.get("min", 0)),
        max_age=int(data.get("max", 150)),
        as_of=str(data.get("as_of", "12-31")),
    )


def _parse_diagnosis_rule(data: dict[str, Any]) -> DiagnosisRule:
    return DiagnosisRule(
        valueset=str(data.get("valueset", "")),
        codes=data.get("codes", []),
        lookback_months=int(data.get("lookback_months", 12)),
        status=data.get("status", ["active", "historical"]),
    )


def _parse_procedure_rule(data: dict[str, Any]) -> ProcedureRule:
    return ProcedureRule(
        valueset=str(data.get("valueset", "")),
        codes=data.get("codes", []),
        window_months=int(data.get("window_months", 12)),
        lookback_years=int(data.get("lookback_years", 0)),
    )


def _parse_lab_rule(data: dict[str, Any]) -> LabRule:
    return LabRule(
        lab=str(data.get("lab", "")),
        window_months=int(data.get("window_months", 12)),
        comparator=str(data.get("comparator", "")),
        threshold=data.get("threshold"),
        use_latest=data.get("use_latest", True),
    )


def _parse_bp_rule(data: dict[str, Any]) -> BPRule:
    return BPRule(
        systolic_threshold=float(data.get("systolic_threshold", 140)),
        diastolic_threshold=float(data.get("diastolic_threshold", 90)),
        window_months=int(data.get("window_months", 12)),
        use_latest=data.get("use_latest", True),
    )


def _parse_medication_rule(data: dict[str, Any]) -> MedicationRule:
    return MedicationRule(
        medication_class=str(data.get("medication_class", "")),
        valueset=str(data.get("valueset", "")),
        window_months=int(data.get("window_months", 12)),
    )


def _parse_immunization_rule(data: dict[str, Any]) -> ImmunizationRule:
    return ImmunizationRule(
        vaccine_type=str(data.get("vaccine_type", "")),
        valueset=str(data.get("valueset", "")),
        min_count=int(data.get("min_count", 1)),
        window_months=data.get("window_months"),
    )


def _parse_vital_rule(data: dict[str, Any]) -> VitalRule:
    return VitalRule(
        vital_type=str(data.get("vital_type", "")),
        window_months=int(data.get("window_months", 12)),
        min_value=data.get("min_value"),
        max_value=data.get("max_value"),
    )


def _parse_encounter_rule(data: dict[str, Any]) -> EncounterRule:
    return EncounterRule(
        encounter_types=data.get("encounter_types", []),
        window_months=int(data.get("window_months", 12)),
    )


def _parse_numerator_criterion(data: dict[str, Any]) -> NumeratorCriterion:
    ctype = str(data.get("type", ""))
    # Normalize aliases
    if ctype == "vaccine":
        ctype = "immunization"
    criterion = NumeratorCriterion(
        criterion_type=ctype,
        description=str(data.get("description", "")),
    )

    if ctype == "lab_exists":
        criterion.lab = LabRule(
            lab=str(data.get("lab", "")),
            window_months=int(data.get("window_months", 12)),
        )
    elif ctype == "lab_value":
        criterion.lab = _parse_lab_rule(data)
    elif ctype == "procedure":
        criterion.procedure = _parse_procedure_rule(data)
    elif ctype == "diagnosis":
        criterion.diagnosis = _parse_diagnosis_rule(data)
    elif ctype == "bp_controlled":
        criterion.bp = _parse_bp_rule(data)
    elif ctype == "medication":
        criterion.medication = _parse_medication_rule(data)
    elif ctype == "immunization":
        criterion.immunization = _parse_immunization_rule(data)
    elif ctype == "vital":
        criterion.vital = _parse_vital_rule(data)
    elif ctype == "encounter":
        criterion.encounter = _parse_encounter_rule(data)

    return criterion


def _parse_numerator(data: dict[str, Any]) -> NumeratorDef:
    ndef = NumeratorDef()
    for item in data.get("all_of", []):
        ndef.all_of.append(_parse_numerator_criterion(item))
    for item in data.get("any_of", []):
        ndef.any_of.append(_parse_numerator_criterion(item))
    # Single criterion shorthand
    if "type" in data:
        ndef.all_of.append(_parse_numerator_criterion(data))
    return ndef


def _parse_exclusion(data: dict[str, Any]) -> ExclusionDef:
    return ExclusionDef(
        exclusion_type=str(data.get("type", "")),
        valueset=str(data.get("valueset", "")),
        codes=data.get("codes", []),
        lookback_months=int(data.get("lookback_months", 12)),
        description=str(data.get("description", "")),
    )


def load_measure_yaml(path: Path) -> MeasureDefinition:
    """Load a measure definition from a YAML file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parse_measure_dict(data)


def parse_measure_dict(data: dict[str, Any]) -> MeasureDefinition:
    """Parse a measure definition from a dict (from YAML or JSON)."""
    mdef = MeasureDefinition(
        id=str(data.get("id", "")),
        name=str(data.get("name", "")),
        version=str(data.get("version", "2025")),
        domain=str(data.get("domain", "")),
        description=str(data.get("description", "")),
        valuesets_needed=data.get("valuesets_needed", []),
        data_sources=data.get("data_sources", []),
        inverse=bool(data.get("inverse", False)),
    )

    # Eligibility
    elig = data.get("eligibility", {})
    if "age" in elig:
        mdef.age = _parse_age_rule(elig["age"])
    mdef.gender = elig.get("gender", ["male", "female"])
    mdef.continuous_enrollment = elig.get("continuous_enrollment", False)

    # Denominator
    denom = data.get("denominator", {})
    if "requires_diagnosis" in denom:
        mdef.denominator_diagnosis = _parse_diagnosis_rule(denom["requires_diagnosis"])
    if "requires_diagnosis_secondary" in denom:
        mdef.denominator_diagnosis_secondary = _parse_diagnosis_rule(denom["requires_diagnosis_secondary"])
    if "requires_procedure" in denom:
        mdef.denominator_procedure = _parse_procedure_rule(denom["requires_procedure"])
    if "requires_encounter" in denom:
        mdef.denominator_encounter = _parse_encounter_rule(denom["requires_encounter"])
    if "requires_medication" in denom:
        mdef.denominator_medication = _parse_medication_rule(denom["requires_medication"])
    mdef.denominator_age_only = denom.get("age_only", False)

    # Exclusions
    for excl in data.get("exclusions", []):
        mdef.exclusions.append(_parse_exclusion(excl))

    # Numerator
    if "numerator" in data:
        mdef.numerator = _parse_numerator(data["numerator"])

    return mdef


def load_all_measures(catalog_dir: Path) -> list[MeasureDefinition]:
    """Load all YAML measure definitions from a catalog directory."""
    measures: list[MeasureDefinition] = []
    for path in sorted(catalog_dir.glob("*.yaml")):
        try:
            measures.append(load_measure_yaml(path))
        except Exception as e:
            print(f"Warning: Failed to load measure {path.name}: {e}")
    for path in sorted(catalog_dir.glob("*.yml")):
        try:
            measures.append(load_measure_yaml(path))
        except Exception as e:
            print(f"Warning: Failed to load measure {path.name}: {e}")
    return measures
