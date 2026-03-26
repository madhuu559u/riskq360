"""Patient demographics endpoints — derived from assertions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.assertion_service import AssertionService

router = APIRouter()


@router.get("/{chart_id}")
async def get_patient(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get patient demographics derived from assertion data."""
    svc = AssertionService(db)
    stats = await svc.get_category_stats(chart_id)
    diagnoses = await svc.get_diagnoses(chart_id)

    return {
        "chart_id": chart_id,
        "assertion_categories": stats.get("categories", {}),
        "diagnosis_count": diagnoses.get("count", 0),
    }
