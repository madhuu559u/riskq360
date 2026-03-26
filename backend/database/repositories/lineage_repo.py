"""Repository for diagnosis candidate lineage and deterministic decision traces."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import DiagnosisCandidate, DiagnosisCandidateEvidence, DecisionTraceEvent


class LineageRepository:
    """Async read access for reviewer-facing lineage surfaces."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_candidates(
        self,
        chart_id: int,
        lifecycle_state: Optional[str] = None,
        review_status: Optional[str] = None,
        icd10_code: Optional[str] = None,
        hcc_code: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> Sequence[DiagnosisCandidate]:
        stmt = select(DiagnosisCandidate).where(DiagnosisCandidate.chart_id == chart_id)
        if lifecycle_state:
            stmt = stmt.where(DiagnosisCandidate.lifecycle_state == lifecycle_state)
        if review_status:
            stmt = stmt.where(DiagnosisCandidate.review_status == review_status)
        if icd10_code:
            stmt = stmt.where(DiagnosisCandidate.icd10_code == icd10_code)
        if hcc_code:
            stmt = stmt.where(DiagnosisCandidate.hcc_code == hcc_code)
        stmt = (
            stmt.order_by(
                DiagnosisCandidate.page_number.asc().nullslast(),
                DiagnosisCandidate.candidate_key.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_candidates(
        self,
        chart_id: int,
        lifecycle_state: Optional[str] = None,
        review_status: Optional[str] = None,
        icd10_code: Optional[str] = None,
        hcc_code: Optional[str] = None,
    ) -> int:
        stmt = select(func.count(DiagnosisCandidate.id)).where(DiagnosisCandidate.chart_id == chart_id)
        if lifecycle_state:
            stmt = stmt.where(DiagnosisCandidate.lifecycle_state == lifecycle_state)
        if review_status:
            stmt = stmt.where(DiagnosisCandidate.review_status == review_status)
        if icd10_code:
            stmt = stmt.where(DiagnosisCandidate.icd10_code == icd10_code)
        if hcc_code:
            stmt = stmt.where(DiagnosisCandidate.hcc_code == hcc_code)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_candidate(self, candidate_id: int) -> Optional[DiagnosisCandidate]:
        result = await self.session.execute(
            select(DiagnosisCandidate).where(DiagnosisCandidate.id == candidate_id)
        )
        return result.scalar_one_or_none()

    async def get_candidate_evidence(self, candidate_id: int) -> Sequence[DiagnosisCandidateEvidence]:
        stmt = (
            select(DiagnosisCandidateEvidence)
            .where(DiagnosisCandidateEvidence.candidate_id == candidate_id)
            .order_by(
                DiagnosisCandidateEvidence.is_primary.desc(),
                DiagnosisCandidateEvidence.page_number.asc().nullslast(),
                DiagnosisCandidateEvidence.id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_trace_events(
        self,
        chart_id: int,
        entity_type: Optional[str] = None,
        entity_key: Optional[str] = None,
        lifecycle_state: Optional[str] = None,
        reason_code: Optional[str] = None,
        measure_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> Sequence[DecisionTraceEvent]:
        stmt = select(DecisionTraceEvent).where(DecisionTraceEvent.chart_id == chart_id)
        if entity_type:
            stmt = stmt.where(DecisionTraceEvent.entity_type == entity_type)
        if entity_key:
            stmt = stmt.where(DecisionTraceEvent.entity_key == entity_key)
        if lifecycle_state:
            stmt = stmt.where(DecisionTraceEvent.lifecycle_state == lifecycle_state)
        if reason_code:
            stmt = stmt.where(DecisionTraceEvent.reason_code == reason_code)
        if measure_id:
            stmt = stmt.where(DecisionTraceEvent.measure_id == measure_id)
        stmt = (
            stmt.order_by(
                DecisionTraceEvent.event_date.desc().nullslast(),
                DecisionTraceEvent.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_trace_events(
        self,
        chart_id: int,
        entity_type: Optional[str] = None,
        entity_key: Optional[str] = None,
        lifecycle_state: Optional[str] = None,
        reason_code: Optional[str] = None,
        measure_id: Optional[str] = None,
    ) -> int:
        stmt = select(func.count(DecisionTraceEvent.id)).where(DecisionTraceEvent.chart_id == chart_id)
        if entity_type:
            stmt = stmt.where(DecisionTraceEvent.entity_type == entity_type)
        if entity_key:
            stmt = stmt.where(DecisionTraceEvent.entity_key == entity_key)
        if lifecycle_state:
            stmt = stmt.where(DecisionTraceEvent.lifecycle_state == lifecycle_state)
        if reason_code:
            stmt = stmt.where(DecisionTraceEvent.reason_code == reason_code)
        if measure_id:
            stmt = stmt.where(DecisionTraceEvent.measure_id == measure_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
