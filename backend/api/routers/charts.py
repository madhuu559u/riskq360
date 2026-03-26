"""Chart management endpoints - upload, process, status, list, delete."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from database.session import async_session_factory, get_db
from scripts.process_charts import process_single_pdf
from services.chart_service import ChartService

router = APIRouter()
log = logging.getLogger(__name__)


class ProcessRequest(BaseModel):
    mode: str = "full"
    enable_ml: Optional[bool] = None
    enable_ocr: Optional[bool] = None
    measurement_year: Optional[int] = None


def _resolve_db_url_for_processing() -> Optional[str]:
    # Keep script persistence in sync with API runtime DB backend.
    settings = get_settings()
    if (settings.db_backend or "").lower() == "postgres":
        return "postgres"
    if os.getenv("POSTGRES_HOST"):
        return "postgres"
    return None


async def _run_chart_processing(chart_id: int, req: ProcessRequest) -> None:
    settings = get_settings()

    async with async_session_factory() as db:
        svc = ChartService(db)
        chart = await svc.get_chart(chart_id)
        if not chart:
            return
        await svc.update_status(chart_id, "processing")
        await db.commit()

    try:
        async with async_session_factory() as db:
            svc = ChartService(db)
            chart = await svc.get_chart(chart_id)
            if not chart:
                return
            pdf_path = Path(chart["file_path"])
            if not pdf_path.exists():
                await svc.update_status(chart_id, "failed")
                await db.commit()
                return

        api_key = settings.llm.openai.api_key or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            log.error("Chart %s processing failed: OPENAI_API_KEY is not configured", chart_id)
            async with async_session_factory() as db:
                svc = ChartService(db)
                await svc.update_status(chart_id, "failed")
                await db.commit()
            return

        output_dir = settings.paths.output_dir / "frontend_runs" / f"chart_{chart_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir.mkdir(parents=True, exist_ok=True)

        client = OpenAI(
            api_key=api_key,
            timeout=float(settings.llm.llm_timeout),
            base_url=settings.llm.openai.base_url or None,
        )
        db_url = _resolve_db_url_for_processing()

        result = await asyncio.to_thread(
            process_single_pdf,
            str(pdf_path),
            client,
            settings.llm.active_llm_model,
            "gpt-4o",
            settings.pipeline.quality_threshold,
            bool(req.enable_ocr if req.enable_ocr is not None else settings.features.ocr_fallback),
            settings.pipeline.chunk_size,
            str(output_dir),
            True,
            db_url,
            chart_id,
            "api",
        )
        if not result or result.get("status") != "success" or not result.get("db_result"):
            raise RuntimeError(f"Chart processing did not persist DB results for chart_id={chart_id}")

        async with async_session_factory() as db:
            svc = ChartService(db)
            await svc.update_status(chart_id, "completed")
            await db.commit()
    except Exception:
        log.exception("Chart processing failed for chart_id=%s", chart_id)
        async with async_session_factory() as db:
            svc = ChartService(db)
            await svc.update_status(chart_id, "failed")
            await db.commit()


@router.post("/upload")
async def upload_chart(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF chart."""
    settings = get_settings()
    upload_dir = settings.paths.chart_upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    svc = ChartService(db)
    chart = await svc.create_chart(
        filename=file.filename,
        file_path=str(file_path),
        file_size_bytes=file_path.stat().st_size,
        upload_source="api",
        status="uploaded",
    )
    # Ensure the chart row is committed before background processing starts.
    await db.commit()
    if auto_process:
        background_tasks.add_task(_run_chart_processing, chart["id"], ProcessRequest())
    return {
        **chart,
        "processing_started": auto_process,
        "message": "Chart uploaded and processing started." if auto_process else "Chart uploaded. Call POST /api/charts/{id}/process.",
    }


@router.post("/{chart_id}/process")
async def process_chart(
    chart_id: int,
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Start chart processing for an uploaded chart."""
    svc = ChartService(db)
    chart = await svc.get_chart(chart_id)
    if not chart:
        raise HTTPException(404, f"Chart not found: {chart_id}")
    if chart["status"] == "processing":
        return {"chart_id": chart_id, "status": "processing", "message": "Processing already in progress"}

    background_tasks.add_task(_run_chart_processing, chart_id, request)
    return {"chart_id": chart_id, "status": "processing", "message": "Processing started"}


@router.post("/process/{chart_id}")
async def process_chart_legacy(
    chart_id: int,
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Legacy path alias for frontend compatibility."""
    return await process_chart(chart_id, request, background_tasks, db)


@router.get("")
async def list_charts(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all charts with pagination."""
    svc = ChartService(db)
    return await svc.list_charts(offset=offset, limit=limit, status=status)


@router.get("/{chart_id}")
async def get_chart(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get chart details with summary stats."""
    svc = ChartService(db)
    try:
        result = await svc.get_chart_summary(chart_id)
    except Exception:
        log.exception("Error fetching chart summary for chart_id=%s", chart_id)
        raise HTTPException(500, f"Internal error fetching chart {chart_id}")
    if not result:
        raise HTTPException(404, f"Chart not found: {chart_id}")
    return result


@router.get("/{chart_id}/file")
async def get_chart_file(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Stream the original PDF for a chart using the persisted file path."""
    svc = ChartService(db)
    chart = await svc.get_chart(chart_id)
    if not chart:
        raise HTTPException(404, f"Chart not found: {chart_id}")

    file_path = Path(chart["file_path"])
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"Chart file not found on disk: {file_path}")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=chart.get("filename") or file_path.name,
    )


@router.get("/{chart_id}/pages")
async def get_chart_pages(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Get page-level data for a chart."""
    from database.repositories.chart_repo import ChartRepository
    repo = ChartRepository(db)
    pages = await repo.get_pages_by_chart_id(chart_id)
    return {
        "chart_id": chart_id,
        "pages": [
            {"page_number": p.page_number, "text_length": p.text_length,
             "quality_score": p.quality_score, "extraction_method": p.extraction_method}
            for p in pages
        ],
        "count": len(pages),
    }


@router.delete("/{chart_id}")
async def delete_chart(chart_id: int, db: AsyncSession = Depends(get_db)):
    """Delete chart and all related data."""
    svc = ChartService(db)
    try:
        deleted = await svc.delete_chart(chart_id)
    except Exception:
        log.exception("Error deleting chart_id=%s", chart_id)
        raise HTTPException(500, f"Internal error deleting chart {chart_id}")
    if not deleted:
        raise HTTPException(404, f"Chart not found: {chart_id}")
    return {"status": "deleted", "chart_id": chart_id}
