"""Repository for Chart, ChartPage, and PipelineRun tables."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Chart, ChartPage, PipelineRun

log = logging.getLogger(__name__)


class ChartRepository:
    """Async CRUD operations for charts, pages, and pipeline runs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Chart CRUD ----

    async def create(self, **kwargs: Any) -> Chart:
        """Create a new chart record."""
        chart = Chart(**kwargs)
        self.session.add(chart)
        await self.session.flush()
        return chart

    async def get_by_id(self, chart_id: int) -> Optional[Chart]:
        """Fetch a chart by primary key with pages, pipeline runs, and patient."""
        stmt = (
            select(Chart)
            .options(
                selectinload(Chart.pages),
                selectinload(Chart.pipeline_runs),
                selectinload(Chart.patient),
            )
            .where(Chart.id == chart_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        offset: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> Sequence[Chart]:
        """Return a paginated list of charts, optionally filtered by status."""
        from database.models import Patient

        stmt = (
            select(Chart)
            .options(selectinload(Chart.patient))
            .order_by(Chart.created_at.desc())
        )
        if status:
            stmt = stmt.where(Chart.status == status)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, status: Optional[str] = None) -> int:
        """Return total chart count, optionally filtered by status."""
        stmt = select(func.count(Chart.id))
        if status:
            stmt = stmt.where(Chart.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, chart_id: int, **kwargs: Any) -> Optional[Chart]:
        """Update a chart record."""
        stmt = (
            update(Chart)
            .where(Chart.id == chart_id)
            .values(**kwargs)
            .returning(Chart)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def update_status(self, chart_id: int, status: str) -> Optional[Chart]:
        """Convenience method to update only chart status."""
        return await self.update(chart_id, status=status)

    async def delete(self, chart_id: int) -> bool:
        """Delete a chart and all related data comprehensively.

        SQLite does not enforce FK cascades by default, and even with
        ``PRAGMA foreign_keys=ON`` the raw ``DELETE`` bypasses SQLAlchemy ORM
        cascade rules.  We therefore manually delete related rows in
        dependency order (grandchildren first, then direct children, then the
        chart itself).
        """
        from database.models import (
            Chart,
            ChartPage,
            PipelineRun,
            PipelineLog,
            Assertion,
            ConditionGroup,
            PayableHCC,
            SuppressedHCC,
            RAFSummary,
            HEDISResult,
            HEDISSummary,
            ReviewAction,
            ProcessingStats,
            HCCHierarchyLog,
            APICallLog,
            Patient,
            PatientVital,
            Diagnosis,
            DiagnosisHCCMapping,
            Encounter,
            EncounterMedication,
            EncounterLabOrder,
            EncounterProcedure,
            EncounterReferral,
            EncounterDiagnosis,
            ClinicalSentence,
            HEDISBPReading,
            HEDISLabResult,
            HEDISScreening,
            HEDISDepressionScreening,
            HEDISFallsRisk,
            HEDISEligibility,
            HEDISMedication,
            ExtractionResult,
            DiagnosisCandidate,
            DiagnosisCandidateEvidence,
            DecisionTraceEvent,
            GoldenLabel,
            ReviewerDisagreement,
        )
        try:
            sub_run_ids = select(PipelineRun.id).where(PipelineRun.chart_id == chart_id)

            # ----------------------------------------------------------
            # 1. Detach Patient / PatientVital (they may survive the chart)
            #    NULL both chart_id AND run_id so they don't block deletes.
            # ----------------------------------------------------------
            await self.session.execute(
                update(Patient)
                .where(Patient.chart_id == chart_id)
                .values(chart_id=None, run_id=None)
            )
            await self.session.execute(
                update(PatientVital)
                .where(PatientVital.chart_id == chart_id)
                .values(chart_id=None)
            )

            # ----------------------------------------------------------
            # 2. Delete grandchildren (tables with FK to other children)
            # ----------------------------------------------------------

            # Encounter children -> Encounter (via encounter_id FK)
            sub_enc_ids = select(Encounter.id).where(Encounter.chart_id == chart_id)
            for enc_child in (
                EncounterMedication,
                EncounterLabOrder,
                EncounterProcedure,
                EncounterReferral,
                EncounterDiagnosis,
            ):
                await self.session.execute(
                    delete(enc_child).where(enc_child.encounter_id.in_(sub_enc_ids))
                )

            # DiagnosisHCCMapping -> Diagnosis (via diagnosis_id FK)
            sub_dx_ids = select(Diagnosis.id).where(Diagnosis.chart_id == chart_id)
            await self.session.execute(
                delete(DiagnosisHCCMapping).where(DiagnosisHCCMapping.diagnosis_id.in_(sub_dx_ids))
            )

            # DiagnosisCandidateEvidence -> DiagnosisCandidate (via candidate_id FK)
            sub_cand_ids = select(DiagnosisCandidate.id).where(DiagnosisCandidate.chart_id == chart_id)
            await self.session.execute(
                delete(DiagnosisCandidateEvidence).where(
                    DiagnosisCandidateEvidence.candidate_id.in_(sub_cand_ids)
                )
            )

            # ----------------------------------------------------------
            # 3. Delete ALL tables that have chart_id FK
            #    (delete before pipeline_runs since most also FK via run_id)
            # ----------------------------------------------------------
            chart_id_tables = [
                ChartPage,
                Assertion,
                ConditionGroup,
                PayableHCC,
                SuppressedHCC,
                RAFSummary,
                HEDISResult,
                HEDISSummary,
                ReviewAction,
                ProcessingStats,
                HCCHierarchyLog,
                APICallLog,
                Diagnosis,
                Encounter,
                ClinicalSentence,
                HEDISBPReading,
                HEDISLabResult,
                HEDISScreening,
                HEDISDepressionScreening,
                HEDISFallsRisk,
                HEDISEligibility,
                HEDISMedication,
                DiagnosisCandidate,
                DiagnosisCandidateEvidence,
                DecisionTraceEvent,
                GoldenLabel,
                ReviewerDisagreement,
            ]
            for model in chart_id_tables:
                await self.session.execute(
                    delete(model).where(model.chart_id == chart_id)
                )

            # ----------------------------------------------------------
            # 4. Delete run-only tables (no chart_id, only run_id FK)
            # ----------------------------------------------------------
            for model in (PipelineLog, ExtractionResult):
                await self.session.execute(
                    delete(model).where(model.run_id.in_(sub_run_ids))
                )

            # ----------------------------------------------------------
            # 5. Now safe to delete pipeline_runs (all FK refs removed)
            # ----------------------------------------------------------
            await self.session.execute(
                delete(PipelineRun).where(PipelineRun.chart_id == chart_id)
            )

            # ----------------------------------------------------------
            # 4. Delete the chart itself
            # ----------------------------------------------------------
            result = await self.session.execute(
                delete(Chart).where(Chart.id == chart_id)
            )
            return result.rowcount > 0

        except Exception:
            log.exception("Failed to delete chart %s", chart_id)
            raise

    # ---- ChartPage CRUD ----

    async def create_page(self, **kwargs: Any) -> ChartPage:
        """Create a new chart page record."""
        page = ChartPage(**kwargs)
        self.session.add(page)
        await self.session.flush()
        return page

    async def create_pages_bulk(self, pages: list[dict[str, Any]]) -> list[ChartPage]:
        """Bulk-insert multiple chart pages."""
        page_objects = [ChartPage(**p) for p in pages]
        self.session.add_all(page_objects)
        await self.session.flush()
        return page_objects

    async def get_pages_by_chart_id(
        self, chart_id: int
    ) -> Sequence[ChartPage]:
        """Get all pages for a chart, ordered by page number."""
        stmt = (
            select(ChartPage)
            .where(ChartPage.chart_id == chart_id)
            .order_by(ChartPage.page_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_page(self, chart_id: int, page_number: int) -> Optional[ChartPage]:
        """Get a specific page by chart id and page number."""
        stmt = select(ChartPage).where(
            ChartPage.chart_id == chart_id,
            ChartPage.page_number == page_number,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_page(self, page_id: int, **kwargs: Any) -> Optional[ChartPage]:
        """Update a chart page record."""
        stmt = (
            update(ChartPage)
            .where(ChartPage.id == page_id)
            .values(**kwargs)
            .returning(ChartPage)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    # ---- PipelineRun CRUD ----

    async def create_pipeline_run(self, **kwargs: Any) -> PipelineRun:
        """Create a new pipeline run record."""
        run = PipelineRun(**kwargs)
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_pipeline_run(self, run_id: int) -> Optional[PipelineRun]:
        """Fetch a pipeline run by id with logs."""
        stmt = (
            select(PipelineRun)
            .options(selectinload(PipelineRun.logs))
            .where(PipelineRun.id == run_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pipeline_runs_by_chart(
        self, chart_id: int
    ) -> Sequence[PipelineRun]:
        """Get all pipeline runs for a chart."""
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.chart_id == chart_id)
            .order_by(PipelineRun.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_pipeline_run(
        self, run_id: int, **kwargs: Any
    ) -> Optional[PipelineRun]:
        """Update a pipeline run record."""
        stmt = (
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .values(**kwargs)
            .returning(PipelineRun)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def complete_pipeline_run(
        self,
        run_id: int,
        status: str = "completed",
        duration_seconds: Optional[float] = None,
        total_tokens_used: int = 0,
        estimated_cost: float = 0.0,
        error_message: Optional[str] = None,
    ) -> Optional[PipelineRun]:
        """Mark a pipeline run as completed or failed."""
        values: dict[str, Any] = {
            "status": status,
            "completed_at": datetime.utcnow(),
        }
        if duration_seconds is not None:
            values["duration_seconds"] = duration_seconds
        if total_tokens_used:
            values["total_tokens_used"] = total_tokens_used
        if estimated_cost:
            values["estimated_cost"] = estimated_cost
        if error_message:
            values["error_message"] = error_message
        return await self.update_pipeline_run(run_id, **values)

    async def get_latest_run(self, chart_id: int) -> Optional[PipelineRun]:
        """Get the most recent pipeline run for a chart."""
        stmt = (
            select(PipelineRun)
            .where(PipelineRun.chart_id == chart_id)
            .order_by(PipelineRun.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
