"""Reviewer-facing lineage service for diagnosis candidates and decision traces."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.lineage_repo import LineageRepository


class LineageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LineageRepository(session)

    async def get_diagnosis_candidates(
        self,
        chart_id: int,
        lifecycle_state: Optional[str] = None,
        review_status: Optional[str] = None,
        icd10_code: Optional[str] = None,
        hcc_code: Optional[str] = None,
        include_evidence: bool = True,
        include_trace: bool = False,
        limit: int = 500,
        offset: int = 0,
    ) -> dict:
        rows = await self.repo.get_candidates(
            chart_id,
            lifecycle_state=lifecycle_state,
            review_status=review_status,
            icd10_code=icd10_code,
            hcc_code=hcc_code,
            limit=limit,
            offset=offset,
        )
        total = await self.repo.count_candidates(
            chart_id,
            lifecycle_state=lifecycle_state,
            review_status=review_status,
            icd10_code=icd10_code,
            hcc_code=hcc_code,
        )
        candidates = []
        for row in rows:
            item = self._serialize_candidate(row)
            if include_evidence:
                evidence = await self.repo.get_candidate_evidence(row.id)
                item["evidence"] = [self._serialize_evidence(ev) for ev in evidence]
            if include_trace:
                trace = await self.repo.get_trace_events(
                    chart_id,
                    entity_type="diagnosis_candidate",
                    entity_key=row.candidate_key,
                    limit=200,
                    offset=0,
                )
                item["trace"] = [self._serialize_trace(event) for event in trace]
            candidates.append(item)
        return {"diagnosis_candidates": candidates, "total": total}

    async def get_diagnosis_candidate(self, candidate_id: int) -> Optional[dict]:
        row = await self.repo.get_candidate(candidate_id)
        if not row:
            return None
        evidence = await self.repo.get_candidate_evidence(candidate_id)
        trace = await self.repo.get_trace_events(
            row.chart_id,
            entity_type="diagnosis_candidate",
            entity_key=row.candidate_key,
            limit=200,
            offset=0,
        )
        return {
            "candidate": self._serialize_candidate(row),
            "evidence": [self._serialize_evidence(ev) for ev in evidence],
            "trace": [self._serialize_trace(event) for event in trace],
        }

    async def get_decision_trace(
        self,
        chart_id: int,
        entity_type: Optional[str] = None,
        entity_key: Optional[str] = None,
        lifecycle_state: Optional[str] = None,
        reason_code: Optional[str] = None,
        measure_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> dict:
        rows = await self.repo.get_trace_events(
            chart_id,
            entity_type=entity_type,
            entity_key=entity_key,
            lifecycle_state=lifecycle_state,
            reason_code=reason_code,
            measure_id=measure_id,
            limit=limit,
            offset=offset,
        )
        total = await self.repo.count_trace_events(
            chart_id,
            entity_type=entity_type,
            entity_key=entity_key,
            lifecycle_state=lifecycle_state,
            reason_code=reason_code,
            measure_id=measure_id,
        )
        return {"decision_trace": [self._serialize_trace(row) for row in rows], "total": total}

    def _serialize_candidate(self, candidate: Any) -> dict:
        return {
            "id": candidate.id,
            "chart_id": candidate.chart_id,
            "patient_id": candidate.patient_id,
            "run_id": candidate.run_id,
            "assertion_id": candidate.assertion_id,
            "candidate_key": candidate.candidate_key,
            "icd10_code": candidate.icd10_code,
            "hcc_code": candidate.hcc_code,
            "source_type": candidate.source_type,
            "lifecycle_state": candidate.lifecycle_state,
            "reason_code": candidate.reason_code,
            "reason_text": candidate.reason_text,
            "confidence": candidate.confidence,
            "effective_date": str(candidate.effective_date) if candidate.effective_date else None,
            "provider_name": candidate.provider_name,
            "page_number": candidate.page_number,
            "exact_quote": candidate.exact_quote,
            "review_status": candidate.review_status,
            "payload": candidate.payload,
            "created_at": str(candidate.created_at) if candidate.created_at else None,
        }

    def _serialize_evidence(self, evidence: Any) -> dict:
        return {
            "id": evidence.id,
            "candidate_id": evidence.candidate_id,
            "chart_id": evidence.chart_id,
            "page_number": evidence.page_number,
            "char_start": evidence.char_start,
            "char_end": evidence.char_end,
            "exact_quote": evidence.exact_quote,
            "section_name": evidence.section_name,
            "is_primary": evidence.is_primary,
            "confidence": evidence.confidence,
            "created_at": str(evidence.created_at) if evidence.created_at else None,
        }

    def _serialize_trace(self, event: Any) -> dict:
        return {
            "id": event.id,
            "chart_id": event.chart_id,
            "patient_id": event.patient_id,
            "run_id": event.run_id,
            "entity_type": event.entity_type,
            "entity_key": event.entity_key,
            "lifecycle_state": event.lifecycle_state,
            "reason_code": event.reason_code,
            "reason_text": event.reason_text,
            "measure_id": event.measure_id,
            "icd10_code": event.icd10_code,
            "hcc_code": event.hcc_code,
            "event_date": str(event.event_date) if event.event_date else None,
            "payload": event.payload,
            "created_at": str(event.created_at) if event.created_at else None,
        }
