"""Dashboard data endpoints — stats, metrics, activity."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Assertion, Chart, HEDISResult, HEDISSummary, PayableHCC,
    PipelineRun, ProcessingStats, RAFSummary, SuppressedHCC,
)
from database.session import get_db
from services.chart_service import ChartService
from services.pipeline_service import PipelineService

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Overall system statistics from database."""
    total = (await db.execute(select(func.count(Chart.id)))).scalar_one()
    completed = (await db.execute(select(func.count(Chart.id)).where(Chart.status == "completed"))).scalar_one()
    failed = (await db.execute(select(func.count(Chart.id)).where(Chart.status == "failed"))).scalar_one()
    assertions = (await db.execute(select(func.count(Assertion.id)))).scalar_one()
    hccs = (await db.execute(select(func.count(PayableHCC.id)))).scalar_one()
    avg_time = (await db.execute(select(func.avg(ProcessingStats.total_processing_seconds)))).scalar_one()

    return {
        "total_charts": total,
        "completed": completed,
        "failed": failed,
        "success_rate": round(completed / max(total, 1) * 100, 1),
        "total_assertions": assertions,
        "total_payable_hccs": hccs,
        "avg_processing_seconds": round(avg_time or 0, 2),
    }


@router.get("/db-stats")
async def get_db_stats(db: AsyncSession = Depends(get_db)):
    """Database table row counts."""
    tables = {}
    for model in [Chart, PipelineRun, Assertion, PayableHCC, SuppressedHCC,
                  RAFSummary, HEDISResult, HEDISSummary, ProcessingStats]:
        count = (await db.execute(select(func.count()).select_from(model))).scalar_one()
        tables[model.__tablename__] = count
    return {"tables": tables}


@router.get("/processing-metrics")
async def get_processing_metrics(db: AsyncSession = Depends(get_db)):
    """Processing time and success rate metrics."""
    svc = PipelineService(db)
    avg = await svc.get_avg_processing_time()
    runs = await svc.list_runs(limit=10)
    return {"avg_processing_seconds": round(avg or 0, 2), "recent_runs": runs["runs"]}


@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    """Recent chart processing activity."""
    svc = ChartService(db)
    result = await svc.list_charts(limit=20)
    return {"recent_activity": result["charts"]}


@router.get("/top-raf")
async def get_top_raf(db: AsyncSession = Depends(get_db)):
    """Top charts by RAF score."""
    stmt = (
        select(RAFSummary, Chart.filename)
        .join(Chart, Chart.id == RAFSummary.chart_id)
        .where(RAFSummary.total_raf_score > 0)
        .order_by(RAFSummary.total_raf_score.desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return {
        "top_raf": [
            {
                "chart_id": r[0].chart_id,
                "filename": r[1],
                "total_raf_score": float(r[0].total_raf_score),
                "payable_hcc_count": r[0].payable_hcc_count,
            }
            for r in rows
        ]
    }
