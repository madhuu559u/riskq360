"""Pydantic schemas for HEDIS quality measure endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HEDISMeasureResult(BaseModel):
    measure_code: str
    measure_name: str
    eligible: bool = False
    status: str = "unknown"
    evidence: List[Dict[str, Any]] = []
    target: Optional[str] = None


class HEDISGapSchema(BaseModel):
    measure_code: str
    measure_name: str
    gap_description: str
    missing_evidence: Optional[str] = None
    recommended_action: Optional[str] = None
    priority: str = "standard"


class HEDISQualityPack(BaseModel):
    measurement_year: int
    measures: List[HEDISMeasureResult] = []
    gaps: List[HEDISGapSchema] = []
    total_eligible: int = 0
    total_met: int = 0
    total_gaps: int = 0
