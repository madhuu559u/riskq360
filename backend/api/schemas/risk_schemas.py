"""Pydantic schemas for risk adjustment endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MEATEvidenceSchema(BaseModel):
    monitored: bool = False
    monitoring_text: Optional[str] = None
    evaluated: bool = False
    evaluation_text: Optional[str] = None
    assessed: bool = False
    assessment_text: Optional[str] = None
    treated: bool = False
    treatment_text: Optional[str] = None


class EvidenceSpanSchema(BaseModel):
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class SupportedICDSchema(BaseModel):
    icd10_code: str
    icd10_description: Optional[str] = None
    confidence: float = 0.0
    ml_confidence: float = 0.0
    llm_confidence: float = 0.0
    polarity: str = "active"
    negation_method: Optional[str] = None
    meat_evidence: Optional[MEATEvidenceSchema] = None
    evidence_spans: List[EvidenceSpanSchema] = []
    date_of_service: Optional[str] = None
    provider: Optional[str] = None


class PayableHCCSchema(BaseModel):
    hcc_code: str
    hcc_description: Optional[str] = None
    raf_weight: float = 0.0
    hierarchy_applied: bool = False
    suppresses: List[str] = []
    supported_icds: List[SupportedICDSchema] = []
    audit_risk: str = "low"


class RAFSummarySchema(BaseModel):
    total_raf_score: float = 0.0
    demographic_raf: float = 0.0
    hcc_raf: float = 0.0
    hcc_count: int = 0
    payable_hcc_count: int = 0
    suppressed_hcc_count: int = 0


class HCCPackSchema(BaseModel):
    chart_id: str
    patient: Optional[Dict[str, Any]] = None
    measurement_year: int = 2026
    payable_hccs: List[PayableHCCSchema] = []
    unsupported_candidates: List[Dict[str, Any]] = []
    raf_summary: RAFSummarySchema = RAFSummarySchema()
    pipeline_metadata: Optional[Dict[str, Any]] = None
