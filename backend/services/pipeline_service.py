"""Pipeline service — runs, logs, processing stats."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.pipeline_repo import PipelineRepository


class PipelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PipelineRepository(session)

    async def list_runs(
        self, offset: int = 0, limit: int = 50, status: Optional[str] = None,
    ) -> dict:
        runs = await self.repo.list_runs(offset=offset, limit=limit, status=status)
        total = await self.repo.count_runs(status=status)
        return {
            "runs": [self._serialize_run(r) for r in runs],
            "total": total,
        }

    async def get_run(self, run_id: int) -> Optional[dict]:
        run = await self.repo.get_run_by_id(run_id)
        if not run:
            return None
        result = self._serialize_run(run)
        result["logs"] = [
            {"step": l.step, "message": l.message, "level": l.log_level,
             "duration": l.duration_seconds, "created_at": str(l.created_at)}
            for l in (run.logs or [])
        ]
        return result

    async def get_runs_by_chart(self, chart_id: int) -> dict:
        runs = await self.repo.get_runs_by_chart(chart_id)
        return {"runs": [self._serialize_run(r) for r in runs], "count": len(runs)}

    async def get_stats(self, chart_id: int) -> Optional[dict]:
        stats = await self.repo.get_stats_by_chart(chart_id)
        if not stats:
            return None
        return {
            "chart_id": stats.chart_id,
            "total_processing_seconds": stats.total_processing_seconds,
            "extraction_seconds": stats.extraction_seconds,
            "hcc_mapping_seconds": stats.hcc_mapping_seconds,
            "hedis_evaluation_seconds": stats.hedis_evaluation_seconds,
            "pages_processed": stats.pages_processed,
            "ocr_pages": stats.ocr_pages,
            "assertions_raw": stats.assertions_raw,
            "assertions_audited": stats.assertions_audited,
            "model_used": stats.model_used,
        }

    async def get_run_logs(self, run_id: int) -> dict:
        """Get pipeline logs for a specific run."""
        logs = await self.repo.get_logs_by_run(run_id)
        run = await self.repo.get_run_by_id(run_id)
        return {
            "run_id": run_id,
            "run_status": run.status if run else "not_found",
            "chart_id": run.chart_id if run else None,
            "logs": [
                {
                    "id": l.id,
                    "step": l.step,
                    "message": l.message,
                    "level": l.log_level,
                    "details": l.details,
                    "duration_seconds": l.duration_seconds,
                    "created_at": str(l.created_at) if l.created_at else None,
                }
                for l in logs
            ],
            "total": len(logs),
        }

    async def rerun_pipeline(self, run_id: int) -> dict:
        """Create a new pipeline run by re-running from an existing run's configuration."""
        original_run = await self.repo.get_run_by_id(run_id)
        if not original_run:
            return None

        # Determine next run number for this chart
        chart_runs = await self.repo.get_runs_by_chart(original_run.chart_id)
        next_run_number = max((r.run_number or 0 for r in chart_runs), default=0) + 1

        new_run = await self.repo.create_run(
            chart_id=original_run.chart_id,
            run_number=next_run_number,
            status="running",
            mode=original_run.mode,
            model=original_run.model,
            config_snapshot=original_run.config_snapshot,
        )

        # Log the rerun initiation
        await self.repo.create_log(
            run_id=new_run.id,
            log_level="INFO",
            step="rerun_init",
            message=f"Re-run initiated from run #{run_id}",
            details={"original_run_id": run_id, "original_status": original_run.status},
        )

        await self.session.commit()

        return {
            "new_run": self._serialize_run(new_run),
            "original_run_id": run_id,
            "message": f"Pipeline re-run created (run #{next_run_number}) from original run #{run_id}",
        }

    async def get_avg_processing_time(self) -> Optional[float]:
        return await self.repo.get_avg_processing_time()

    def _serialize_run(self, r: Any) -> dict:
        return {
            "id": r.id,
            "chart_id": r.chart_id,
            "run_number": r.run_number,
            "status": r.status,
            "mode": r.mode,
            "model": r.model,
            "chunk_count": r.chunk_count,
            "started_at": str(r.started_at) if r.started_at else None,
            "completed_at": str(r.completed_at) if r.completed_at else None,
            "duration_seconds": r.duration_seconds,
            "assertions_raw": r.assertions_raw,
            "assertions_audited": r.assertions_audited,
            "error_message": r.error_message,
        }
