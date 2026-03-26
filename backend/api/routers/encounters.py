"""Encounter timeline endpoints — derived from assertions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.assertion_service import AssertionService

router = APIRouter()


@router.get("/{chart_id}")
async def get_encounters(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get encounter timeline derived from assertion dates."""
    svc = AssertionService(db)
    return await svc.get_encounters(chart_id)
