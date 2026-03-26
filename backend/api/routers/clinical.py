"""Clinical data endpoints - diagnoses, medications, vitals, labs, encounters."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.assertion_service import AssertionService
from services.lineage_service import LineageService

router = APIRouter()


@router.get("/{chart_id}/assertions")
async def get_assertions(
    chart_id: int,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get all assertions for a chart, with optional filters."""
    svc = AssertionService(db)
    return await svc.get_all(chart_id, category=category, status=status, limit=limit, offset=offset)


@router.get("/{chart_id}/diagnoses")
async def get_diagnoses(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get all diagnoses with ICD codes and evidence."""
    svc = AssertionService(db)
    return await svc.get_diagnoses(chart_id)


@router.get("/{chart_id}/diagnosis-candidates")
async def get_diagnosis_candidates(
    chart_id: int,
    lifecycle_state: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    icd10_code: Optional[str] = Query(None),
    hcc_code: Optional[str] = Query(None),
    include_evidence: bool = Query(True),
    include_trace: bool = Query(False),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get persisted diagnosis candidates with lifecycle, evidence, and optional trace."""
    svc = LineageService(db)
    return await svc.get_diagnosis_candidates(
        chart_id,
        lifecycle_state=lifecycle_state,
        review_status=review_status,
        icd10_code=icd10_code,
        hcc_code=hcc_code,
        include_evidence=include_evidence,
        include_trace=include_trace,
        limit=limit,
        offset=offset,
    )


@router.get("/{chart_id}/medications")
async def get_medications(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get all medications."""
    svc = AssertionService(db)
    return await svc.get_medications(chart_id)


@router.get("/{chart_id}/vitals")
async def get_vitals(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get vital signs including blood pressure."""
    svc = AssertionService(db)
    return await svc.get_vitals(chart_id)


@router.get("/{chart_id}/labs")
async def get_labs(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get lab results."""
    svc = AssertionService(db)
    return await svc.get_labs(chart_id)


@router.get("/{chart_id}/encounters")
async def get_encounters(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get encounter timeline derived from assertion dates."""
    svc = AssertionService(db)
    return await svc.get_encounters(chart_id)


@router.get("/{chart_id}/categories")
async def get_category_stats(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get assertion counts by category."""
    svc = AssertionService(db)
    return await svc.get_category_stats(chart_id)


@router.get("/{chart_id}/ra-candidates")
async def get_ra_candidates(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get payable RA candidate assertions."""
    svc = AssertionService(db)
    return await svc.get_ra_candidates(chart_id)
