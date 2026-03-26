"""Core data types for the HEDIS measure engine."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class CodeSystem(str, enum.Enum):
    ICD10CM = "icd10cm"
    ICD9CM = "icd9cm"
    CPT = "cpt"
    HCPCS = "hcpcs"
    LOINC = "loinc"
    RXNORM = "rxnorm"
    NDC = "ndc"
    SNOMED = "snomed"
    CVX = "cvx"


class DiagnosisStatus(str, enum.Enum):
    ACTIVE = "active"
    NEGATED = "negated"
    RESOLVED = "resolved"
    HISTORICAL = "historical"
    FAMILY_HISTORY = "family_history"
    UNCERTAIN = "uncertain"


class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class MeasureStatus(str, enum.Enum):
    MET = "met"
    GAP = "gap"
    NOT_APPLICABLE = "not_applicable"
    EXCLUDED = "excluded"
    INDETERMINATE = "indeterminate"


class VitalType(str, enum.Enum):
    BP = "blood_pressure"
    BMI = "bmi"
    WEIGHT = "weight"
    HEIGHT = "height"
    TEMPERATURE = "temperature"
    HEART_RATE = "heart_rate"
    RESPIRATORY_RATE = "respiratory_rate"
    O2_SAT = "o2_saturation"


class EncounterType(str, enum.Enum):
    OUTPATIENT = "outpatient"
    INPATIENT = "inpatient"
    ED = "emergency"
    TELEHEALTH = "telehealth"
    HOME = "home"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Evidence reference — points back to source document
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceRef:
    """Reference to the source document location for an event."""
    pdf: str = ""
    page_number: Optional[int] = None
    exact_quote: str = ""
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.pdf:
            d["pdf"] = self.pdf
        if self.page_number is not None:
            d["page"] = self.page_number
        if self.exact_quote:
            d["exact_quote"] = self.exact_quote
        if self.char_start is not None:
            d["char_start"] = self.char_start
        if self.char_end is not None:
            d["char_end"] = self.char_end
        return d


# ---------------------------------------------------------------------------
# Normalized clinical events
# ---------------------------------------------------------------------------

@dataclass
class DiagnosisEvent:
    code: str
    code_system: CodeSystem = CodeSystem.ICD10CM
    description: str = ""
    event_date: Optional[date] = None
    status: DiagnosisStatus = DiagnosisStatus.ACTIVE
    evidence_ref: Optional[EvidenceRef] = None


@dataclass
class ProcedureEvent:
    code: str
    code_system: CodeSystem = CodeSystem.CPT
    description: str = ""
    event_date: Optional[date] = None
    evidence_ref: Optional[EvidenceRef] = None


@dataclass
class LabEvent:
    test_type: str  # e.g. "A1C", "LDL", "CREATININE"
    value: Optional[float] = None
    unit: str = ""
    event_date: Optional[date] = None
    evidence_ref: Optional[EvidenceRef] = None


@dataclass
class VitalEvent:
    vital_type: VitalType = VitalType.BP
    systolic: Optional[float] = None
    diastolic: Optional[float] = None
    value: Optional[float] = None  # for BMI, weight, etc.
    unit: str = ""
    event_date: Optional[date] = None
    evidence_ref: Optional[EvidenceRef] = None


@dataclass
class MedicationEvent:
    name: str
    normalized_class: str = ""  # e.g. "statin", "ace_inhibitor"
    code: str = ""
    code_system: CodeSystem = CodeSystem.RXNORM
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    evidence_ref: Optional[EvidenceRef] = None


@dataclass
class EncounterEvent:
    encounter_type: EncounterType = EncounterType.OUTPATIENT
    event_date: Optional[date] = None
    provider: str = ""
    facility: str = ""
    evidence_ref: Optional[EvidenceRef] = None


@dataclass
class Demographics:
    dob: Optional[date] = None
    gender: Gender = Gender.UNKNOWN
    member_id: str = ""
    race: str = ""
    ethnicity: str = ""


@dataclass
class EnrollmentPeriod:
    """Coverage span used for continuous enrollment checks."""
    start_date: date
    end_date: date
    source: str = ""


@dataclass
class ImmunizationEvent:
    vaccine_type: str = ""  # e.g. "influenza", "pneumococcal", "tdap"
    code: str = ""
    code_system: CodeSystem = CodeSystem.CVX
    event_date: Optional[date] = None
    dose_number: Optional[int] = None
    evidence_ref: Optional[EvidenceRef] = None


# ---------------------------------------------------------------------------
# Member event store — all normalized events for one member
# ---------------------------------------------------------------------------

@dataclass
class MemberEventStore:
    """All normalized clinical events for a single member."""
    demographics: Demographics = field(default_factory=Demographics)
    enrollment_periods: list[EnrollmentPeriod] = field(default_factory=list)
    diagnoses: list[DiagnosisEvent] = field(default_factory=list)
    procedures: list[ProcedureEvent] = field(default_factory=list)
    labs: list[LabEvent] = field(default_factory=list)
    vitals: list[VitalEvent] = field(default_factory=list)
    medications: list[MedicationEvent] = field(default_factory=list)
    encounters: list[EncounterEvent] = field(default_factory=list)
    immunizations: list[ImmunizationEvent] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rule evaluation trace / result types
# ---------------------------------------------------------------------------

@dataclass
class TraceEntry:
    """Single step in the evaluation trace."""
    rule: str
    result: bool
    detail: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"rule": self.rule, "result": self.result}
        if self.detail:
            d["detail"] = self.detail
        if self.evidence:
            d["evidence"] = self.evidence
        return d


@dataclass
class GapDetail:
    """Describes a single gap (missing compliance element)."""
    gap_type: str  # e.g. "missing_lab", "missing_procedure", "value_out_of_range"
    description: str = ""
    required_event: str = ""  # what was expected
    window_start: Optional[date] = None
    window_end: Optional[date] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.gap_type}
        if self.description:
            d["description"] = self.description
        if self.required_event:
            d["required_event"] = self.required_event
        if self.window_start:
            d["window"] = f"{self.window_start}..{self.window_end}"
        return d


@dataclass
class EvidenceUsed:
    """An evidence item that contributed to a decision."""
    event_type: str  # "diagnosis", "procedure", "lab", "vital", "medication", etc.
    code: str = ""
    code_system: str = ""
    value: Optional[str] = None
    event_date: Optional[date] = None
    source: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.event_type}
        if self.code:
            d["code"] = self.code
        if self.code_system:
            d["system"] = self.code_system
        if self.value is not None:
            d["value"] = self.value
        if self.event_date:
            d["date"] = self.event_date.isoformat()
        if self.source:
            d["source"] = self.source
        return d


@dataclass
class MeasureResult:
    """Evaluation result for a single HEDIS measure for a single member."""
    measure_id: str
    measure_name: str = ""
    applicable: bool = False
    compliant: ComplianceStatus = ComplianceStatus.UNKNOWN
    status: MeasureStatus = MeasureStatus.NOT_APPLICABLE
    eligibility_reason: list[str] = field(default_factory=list)
    compliance_reason: list[str] = field(default_factory=list)
    gaps: list[GapDetail] = field(default_factory=list)
    evidence_used: list[EvidenceUsed] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    exclusion_reason: str = ""
    confidence: float = 1.0  # deterministic confidence based on evidence completeness
    trace: list[TraceEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.measure_id,
            "name": self.measure_name,
            "applicable": self.applicable,
            "compliant": self.compliant == ComplianceStatus.COMPLIANT if self.applicable else None,
            "status": self.status.value,
            "eligibility_reason": self.eligibility_reason,
            "compliance_reason": self.compliance_reason,
            "gaps": [g.to_dict() for g in self.gaps],
            "evidence_used": [e.to_dict() for e in self.evidence_used],
            "missing_data": self.missing_data,
            "confidence": self.confidence,
            "trace": [t.to_dict() for t in self.trace],
        }
        if self.exclusion_reason:
            d["exclusion_reason"] = self.exclusion_reason
        return d


@dataclass
class MemberHedisResults:
    """All HEDIS measure results for a single member."""
    member_id: str
    measurement_year: int
    measures: list[MeasureResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_id": self.member_id,
            "measurement_year": self.measurement_year,
            "measures": [m.to_dict() for m in self.measures],
        }

    @property
    def summary(self) -> dict[str, int]:
        counts = {"applicable": 0, "met": 0, "gap": 0, "excluded": 0, "indeterminate": 0, "not_applicable": 0}
        for m in self.measures:
            counts[m.status.value] = counts.get(m.status.value, 0) + 1
            if m.applicable:
                counts["applicable"] += 1
        return counts
