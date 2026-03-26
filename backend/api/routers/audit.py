"""Audit trail and review workflow endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.audit_service import AuditService
from services.assertion_service import AssertionService
from services.lineage_service import LineageService

router = APIRouter()


class ReviewRequest(BaseModel):
    action: str  # approved | rejected
    reviewer: str
    notes: Optional[str] = None


@router.get("/logs")
async def get_audit_logs(
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get system audit logs."""
    svc = AuditService(db)
    return await svc.get_logs(entity_type=entity_type, limit=limit, offset=offset)


@router.get("/{chart_id}/reviews")
async def get_chart_reviews(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get review actions for a chart."""
    svc = AuditService(db)
    return await svc.get_reviews_by_chart(chart_id)


@router.get("/{chart_id}/decision-trace")
async def get_chart_decision_trace(
    chart_id: int,
    entity_type: Optional[str] = Query(None),
    entity_key: Optional[str] = Query(None),
    lifecycle_state: Optional[str] = Query(None),
    reason_code: Optional[str] = Query(None),
    measure_id: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get deterministic decision trace events for a chart."""
    svc = LineageService(db)
    return await svc.get_decision_trace(
        chart_id,
        entity_type=entity_type,
        entity_key=entity_key,
        lifecycle_state=lifecycle_state,
        reason_code=reason_code,
        measure_id=measure_id,
        limit=limit,
        offset=offset,
    )


@router.get("/diagnosis-candidates/{candidate_id}")
async def get_diagnosis_candidate(candidate_id: int, db: AsyncSession = Depends(get_db)):
    """Get one persisted diagnosis candidate with its evidence and trace."""
    svc = LineageService(db)
    result = await svc.get_diagnosis_candidate(candidate_id)
    if not result:
        raise HTTPException(404, f"Diagnosis candidate not found: {candidate_id}")
    return result


@router.put("/review/assertion/{assertion_id}")
async def review_assertion(
    assertion_id: int, request: ReviewRequest, db: AsyncSession = Depends(get_db),
):
    """Accept or reject an assertion."""
    svc = AssertionService(db)
    result = await svc.update_review(
        assertion_id, request.action, request.reviewer, request.notes,
    )
    if not result:
        raise HTTPException(404, f"Assertion not found: {assertion_id}")

    audit = AuditService(db)
    await audit.log_action(
        action=f"review_{request.action}", entity_type="assertion",
        entity_id=assertion_id, user_name=request.reviewer,
        details={"notes": request.notes},
    )
    return result


@router.get("/pending")
async def get_pending_reviews(
    chart_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get all assertions pending review."""
    svc = AssertionService(db)
    return await svc.get_pending_reviews(chart_id)
