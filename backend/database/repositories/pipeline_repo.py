"""Repository for PipelineRun, PipelineLog, ProcessingStats, APICallLog."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import APICallLog, PipelineLog, PipelineRun, ProcessingStats


class PipelineRepository:
    """Async CRUD for pipeline runs, logs, stats, and API call tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- PipelineRun ----

    async def create_run(self, **kwargs: Any) -> PipelineRun:
        run = PipelineRun(**kwargs)
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_run_by_id(self, run_id: int) -> Optional[PipelineRun]:
        stmt = (
            select(PipelineRun)
            .options(selectinload(PipelineRun.logs))
            .where(PipelineRun.id == run_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_runs_by_chart(self, chart_id: int) -> Sequence[PipelineRun]:
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.chart_id == chart_id)
            .order_by(PipelineRun.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_runs(
        self, offset: int = 0, limit: int = 50,
        status: Optional[str] = None,
    ) -> Sequence[PipelineRun]:
        stmt = select(PipelineRun)
        if status:
            stmt = stmt.where(PipelineRun.status == status)
        stmt = stmt.order_by(PipelineRun.started_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def complete_run(
        self, run_id: int, status: str = "completed",
        duration_seconds: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Optional[PipelineRun]:
        values: dict[str, Any] = {"status": status, "completed_at": datetime.utcnow()}
        if duration_seconds is not None:
            values["duration_seconds"] = duration_seconds
        if error_message:
            values["error_message"] = error_message
        stmt = update(PipelineRun).where(PipelineRun.id == run_id).values(**values).returning(PipelineRun)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def count_runs(self, status: Optional[str] = None) -> int:
        stmt = select(func.count(PipelineRun.id))
        if status:
            stmt = stmt.where(PipelineRun.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ---- PipelineLog ----

    async def create_log(self, **kwargs: Any) -> PipelineLog:
        log = PipelineLog(**kwargs)
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_logs_by_run(self, run_id: int) -> Sequence[PipelineLog]:
        stmt = select(PipelineLog).where(PipelineLog.run_id == run_id).order_by(PipelineLog.created_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ---- ProcessingStats ----

    async def create_stats(self, **kwargs: Any) -> ProcessingStats:
        rec = ProcessingStats(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_stats_by_chart(self, chart_id: int) -> Optional[ProcessingStats]:
        stmt = (
            select(ProcessingStats)
            .where(ProcessingStats.chart_id == chart_id)
            .order_by(ProcessingStats.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_avg_processing_time(self) -> Optional[float]:
        stmt = select(func.avg(ProcessingStats.total_processing_seconds))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ---- APICallLog ----

    async def create_api_log(self, **kwargs: Any) -> APICallLog:
        rec = APICallLog(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_api_logs_by_run(self, run_id: int) -> Sequence[APICallLog]:
        stmt = select(APICallLog).where(APICallLog.run_id == run_id).order_by(APICallLog.created_at)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_token_usage(self, run_id: int) -> dict[str, int]:
        stmt = select(
            func.coalesce(func.sum(APICallLog.input_tokens), 0),
            func.coalesce(func.sum(APICallLog.output_tokens), 0),
            func.coalesce(func.sum(APICallLog.total_tokens), 0),
        ).where(APICallLog.run_id == run_id)
        result = await self.session.execute(stmt)
        row = result.one()
        return {"input_tokens": row[0], "output_tokens": row[1], "total_tokens": row[2]}
