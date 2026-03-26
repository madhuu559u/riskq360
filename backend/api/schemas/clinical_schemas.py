"""Pydantic schemas for clinical data endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DiagnosisSchema(BaseModel):
    icd10_code: Optional[str] = None
    description: Optional[str] = None
    negation_status: str = "active"
    supporting_text: Optional[str] = None
    source_section: Optional[str] = None
    date_of_service: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[float] = None


class SentenceSchema(BaseModel):
    text: str
    category: Optional[str] = None
    negation_status: str = "active"
    is_negated: bool = False
    negation_trigger: Optional[str] = None


class EncounterSchema(BaseModel):
    date: Optional[str] = None
    provider: Optional[str] = None
    facility: Optional[str] = None
    encounter_type: Optional[str] = None
    chief_complaint: Optional[str] = None
    medications: List[Dict[str, Any]] = []
    procedures: List[Dict[str, Any]] = []
