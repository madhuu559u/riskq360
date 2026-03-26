"""Pydantic request/response schemas for chart endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChartUploadResponse(BaseModel):
    status: str
    filename: str
    file_path: str
    message: str


class ChartProcessResponse(BaseModel):
    chart_id: str
    run_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    raf_summary: Optional[Dict[str, Any]] = None


class ChartSummary(BaseModel):
    chart_id: str
    status: str
    run_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_seconds: Optional[float] = None
    pages_processed: Optional[int] = None
    mode: Optional[str] = None
    raf_summary: Optional[Dict[str, Any]] = None


class ChartListResponse(BaseModel):
    charts: List[ChartSummary]
    total: int
    offset: int
    limit: int
