"""Risk adjustment endpoints — HCC pack, RAF, hierarchy."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from services.risk_service import RiskService

router = APIRouter()


@router.get("/{chart_id}/hcc-pack")
async def get_hcc_pack(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get the complete Payable HCC Pack for a chart."""
    svc = RiskService(db)
    return await svc.get_hcc_pack(chart_id)


@router.get("/{chart_id}/raf-summary")
async def get_raf_summary(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get RAF score breakdown for a chart."""
    svc = RiskService(db)
    result = await svc.get_raf_summary(chart_id)
    if not result:
        raise HTTPException(404, f"No RAF data for chart: {chart_id}")
    return result


@router.get("/{chart_id}/hierarchy")
async def get_hierarchy(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get HCC hierarchy suppression details."""
    svc = RiskService(db)
    return await svc.get_hierarchy(chart_id)


@router.get("/{chart_id}/ml-predictions")
async def get_ml_predictions(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get ML prediction results — assertions flagged as HCC candidates with confidence scores."""
    svc = RiskService(db)
    return await svc.get_ml_predictions(chart_id)


@router.get("/{chart_id}/icd-retrievals")
async def get_icd_retrievals(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get TF-IDF ICD retrieval results from diagnosis candidates."""
    svc = RiskService(db)
    return await svc.get_icd_retrievals(chart_id)


@router.get("/{chart_id}/verified-icds")
async def get_verified_icds(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get verified ICDs with MEAT (Monitor, Evaluate, Assess, Treat) evidence."""
    svc = RiskService(db)
    return await svc.get_verified_icds(chart_id)
