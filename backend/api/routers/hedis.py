"""HEDIS quality measure endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.hedis_service import HEDISService

router = APIRouter()


@router.get("/{chart_id}/measures")
async def get_measures(
    chart_id: int,
    status: Optional[str] = Query(None, description="Filter: met, gap, not_applicable, excluded"),
    db: AsyncSession = Depends(get_db),
):
    """Get HEDIS measure results with evidence."""
    svc = HEDISService(db)
    return await svc.get_measures(chart_id, status=status)


@router.get("/{chart_id}/gaps")
async def get_gaps(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get identified HEDIS care gaps."""
    svc = HEDISService(db)
    return await svc.get_gaps(chart_id)


@router.get("/{chart_id}/evidence")
async def get_evidence(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get HEDIS met measures with evidence."""
    svc = HEDISService(db)
    return await svc.get_met(chart_id)


@router.get("/{chart_id}/summary")
async def get_hedis_summary(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get aggregate HEDIS summary."""
    svc = HEDISService(db)
    result = await svc.get_summary(chart_id)
    if not result:
        return {
            "total_measures": 0,
            "met": 0,
            "gap": 0,
            "not_applicable": 0,
            "excluded": 0,
            "indeterminate": 0,
            "inactive": 0,
            "applicable": 0,
            "measurement_year": None,
        }
    return result
