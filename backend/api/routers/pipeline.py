"""Pipeline management endpoints - runs, logs, stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.session import get_db
from services.pipeline_service import PipelineService

router = APIRouter()


@router.get("/runs")
async def list_runs(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all pipeline runs."""
    svc = PipelineService(db)
    return await svc.list_runs(offset=offset, limit=limit, status=status)


@router.get("/runs/chart/{chart_id}")
async def get_runs_by_chart(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get all pipeline runs for a chart."""
    svc = PipelineService(db)
    return await svc.get_runs_by_chart(chart_id)


@router.get("/runs/{run_id}/logs")
async def get_run_logs(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get pipeline run logs for a specific run."""
    svc = PipelineService(db)
    result = await svc.get_run_logs(run_id)
    if result["run_status"] == "not_found":
        raise HTTPException(404, f"Pipeline run not found: {run_id}")
    return result


@router.post("/runs/{run_id}/rerun")
async def rerun_pipeline(run_id: int, db: AsyncSession = Depends(get_db)):
    """Re-run a pipeline from an existing run's configuration."""
    svc = PipelineService(db)
    result = await svc.rerun_pipeline(run_id)
    if not result:
        raise HTTPException(404, f"Original pipeline run not found: {run_id}")
    return result


@router.get("/runs/{run_id}")
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific pipeline run with logs."""
    svc = PipelineService(db)
    result = await svc.get_run(run_id)
    if not result:
        return {"id": run_id, "status": "not_found", "logs": []}
    return result


@router.get("/stats/{chart_id}")
async def get_processing_stats(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get processing stats for a chart."""
    svc = PipelineService(db)
    result = await svc.get_stats(chart_id)
    if result:
        return result
    return {
        "chart_id": chart_id,
        "total_processing_seconds": None,
        "extraction_seconds": None,
        "hcc_mapping_seconds": None,
        "hedis_evaluation_seconds": None,
        "pages_processed": 0,
        "ocr_pages": 0,
        "assertions_raw": 0,
        "assertions_audited": 0,
        "model_used": None,
        "missing": True,
    }
