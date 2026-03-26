"""Review Service — Full CRUD for coder/abstractor review workflow.

Supports accept/reject/add/update/delete for:
  - Diagnoses (ICD codes)
  - HCC codes
  - HEDIS measure results

Tracks source (ai | coder | rule) and review history with comments.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Assertion,
    AuditLog,
    Chart,
    HEDISResult,
    PayableHCC,
    RAFSummary,
    ReviewAction,
    SuppressedHCC,
)


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # =========================================================================
    # DIAGNOSIS / ICD CODE REVIEW
    # =========================================================================

    async def accept_diagnosis(
        self, assertion_id: int, reviewer: str, notes: Optional[str] = None,
        date_of_service: Optional[str] = None,
    ) -> Optional[dict]:
        """Accept a diagnosis assertion."""
        return await self._update_assertion_review(
            assertion_id, "approved", reviewer, notes, date_of_service,
        )

    async def reject_diagnosis(
        self, assertion_id: int, reviewer: str, notes: Optional[str] = None,
    ) -> Optional[dict]:
        """Reject a diagnosis assertion."""
        return await self._update_assertion_review(
            assertion_id, "rejected", reviewer, notes,
        )

    async def add_diagnosis(
        self, chart_id: int, icd10_code: str, description: str,
        reviewer: str, notes: Optional[str] = None,
        date_of_service: Optional[str] = None,
        page_number: Optional[int] = None,
        exact_quote: Optional[str] = None,
        hcc_code: Optional[str] = None,
        status: str = "active",
    ) -> dict:
        """Add a new diagnosis assertion (coder-added)."""
        assertion = Assertion(
            chart_id=chart_id,
            category="diagnosis",
            concept=description,
            canonical_concept=description,
            text=f"[Coder-added] {description}",
            clean_text=description,
            status=status,
            subject="patient",
            evidence_rank=1,
            page_number=page_number,
            exact_quote=exact_quote or f"[Manually added by {reviewer}]",
            icd_codes=[{"code": icd10_code, "description": description}],
            effective_date=date_of_service,
            is_hcc_candidate=True,
            is_payable_hcc_candidate=bool(hcc_code),
            is_payable_ra_candidate=bool(hcc_code),
            review_status="approved",
            reviewed_by=reviewer,
            reviewed_at=datetime.utcnow(),
            review_notes=notes or "Manually added by coder",
        )
        self.session.add(assertion)
        await self.session.flush()

        await self._log_audit(
            "add_diagnosis", "assertion", assertion.id, reviewer,
            {"icd10_code": icd10_code, "description": description, "notes": notes},
        )
        await self._log_review(
            chart_id, "assertion", assertion.id, "added",
            reviewer, notes, new_value={"icd10_code": icd10_code, "description": description},
        )
        return self._serialize_assertion(assertion)

    async def update_diagnosis(
        self, assertion_id: int, reviewer: str,
        icd10_code: Optional[str] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        date_of_service: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[dict]:
        """Update an existing diagnosis assertion."""
        stmt = select(Assertion).where(Assertion.id == assertion_id)
        result = await self.session.execute(stmt)
        assertion = result.scalar_one_or_none()
        if not assertion:
            return None

        previous = {
            "icd_codes": assertion.icd_codes,
            "concept": assertion.concept,
            "effective_date": assertion.effective_date,
            "status": assertion.status,
        }

        if icd10_code is not None:
            assertion.icd_codes = [{"code": icd10_code, "description": description or assertion.concept}]
        if description is not None:
            assertion.concept = description
            assertion.canonical_concept = description
        if date_of_service is not None:
            assertion.effective_date = date_of_service
        if status is not None:
            assertion.status = status

        assertion.review_status = "approved"
        assertion.reviewed_by = reviewer
        assertion.reviewed_at = datetime.utcnow()
        assertion.review_notes = notes

        await self.session.flush()

        await self._log_audit(
            "update_diagnosis", "assertion", assertion_id, reviewer,
            {"previous": previous, "notes": notes},
        )
        await self._log_review(
            assertion.chart_id, "assertion", assertion_id, "modified",
            reviewer, notes, previous_value=previous,
            new_value={"icd_codes": assertion.icd_codes, "concept": assertion.concept},
        )
        return self._serialize_assertion(assertion)

    async def delete_diagnosis(
        self, assertion_id: int, reviewer: str, notes: Optional[str] = None,
    ) -> bool:
        """Soft-delete a diagnosis (mark as rejected with reason)."""
        stmt = select(Assertion).where(Assertion.id == assertion_id)
        result = await self.session.execute(stmt)
        assertion = result.scalar_one_or_none()
        if not assertion:
            return False

        previous = self._serialize_assertion(assertion)
        assertion.review_status = "rejected"
        assertion.reviewed_by = reviewer
        assertion.reviewed_at = datetime.utcnow()
        assertion.review_notes = notes or "Deleted by coder"

        await self.session.flush()
        await self._log_audit(
            "delete_diagnosis", "assertion", assertion_id, reviewer,
            {"notes": notes, "previous_concept": assertion.concept},
        )
        await self._log_review(
            assertion.chart_id, "assertion", assertion_id, "rejected",
            reviewer, notes, previous_value=previous,
        )
        return True

    # =========================================================================
    # HCC CODE REVIEW
    # =========================================================================

    async def accept_hcc(
        self, hcc_id: int, reviewer: str, notes: Optional[str] = None,
    ) -> Optional[dict]:
        """Accept a payable HCC."""
        stmt = select(PayableHCC).where(PayableHCC.id == hcc_id)
        result = await self.session.execute(stmt)
        hcc = result.scalar_one_or_none()
        if not hcc:
            return None

        # Store review in review_actions
        await self._log_review(
            hcc.chart_id, "hcc", hcc_id, "approved", reviewer, notes,
        )
        await self._log_audit(
            "accept_hcc", "payable_hcc", hcc_id, reviewer,
            {"hcc_code": hcc.hcc_code, "notes": notes},
        )
        return self._serialize_hcc(hcc)

    async def reject_hcc(
        self, hcc_id: int, reviewer: str, notes: Optional[str] = None,
    ) -> bool:
        """Reject a payable HCC (remove from payable list)."""
        stmt = select(PayableHCC).where(PayableHCC.id == hcc_id)
        result = await self.session.execute(stmt)
        hcc = result.scalar_one_or_none()
        if not hcc:
            return False

        previous = self._serialize_hcc(hcc)
        await self._log_review(
            hcc.chart_id, "hcc", hcc_id, "rejected", reviewer, notes,
            previous_value=previous,
        )
        await self._log_audit(
            "reject_hcc", "payable_hcc", hcc_id, reviewer,
            {"hcc_code": hcc.hcc_code, "notes": notes},
        )

        # Move to suppressed
        suppressed = SuppressedHCC(
            chart_id=hcc.chart_id,
            run_id=hcc.run_id,
            hcc_code=hcc.hcc_code,
            hcc_description=hcc.hcc_description,
            suppressed_by="coder_rejected",
            hierarchy_group="manual_review",
            supported_icds=hcc.supported_icds,
        )
        self.session.add(suppressed)

        await self.session.execute(delete(PayableHCC).where(PayableHCC.id == hcc_id))
        await self.session.flush()
        return True

    async def add_hcc(
        self, chart_id: int, hcc_code: str, hcc_description: str,
        raf_weight: float, reviewer: str, notes: Optional[str] = None,
        supported_icds: Optional[list[dict]] = None,
        measurement_year: Optional[int] = None,
    ) -> dict:
        """Add a new payable HCC (coder-added)."""
        hcc = PayableHCC(
            chart_id=chart_id,
            hcc_code=hcc_code,
            hcc_description=hcc_description,
            raf_weight=raf_weight,
            source="coder",
            confidence=1.0,
            hierarchy_applied=False,
            supported_icds=supported_icds or [],
            icd_count=len(supported_icds) if supported_icds else 0,
            measurement_year=measurement_year or datetime.utcnow().year,
        )
        self.session.add(hcc)
        await self.session.flush()

        await self._log_audit(
            "add_hcc", "payable_hcc", hcc.id, reviewer,
            {"hcc_code": hcc_code, "raf_weight": raf_weight, "notes": notes},
        )
        await self._log_review(
            chart_id, "hcc", hcc.id, "added", reviewer, notes,
            new_value={"hcc_code": hcc_code, "raf_weight": raf_weight},
        )
        return self._serialize_hcc(hcc)

    # =========================================================================
    # HEDIS MEASURE REVIEW
    # =========================================================================

    async def accept_hedis(
        self, hedis_id: int, reviewer: str, notes: Optional[str] = None,
    ) -> Optional[dict]:
        """Accept a HEDIS measure result."""
        stmt = select(HEDISResult).where(HEDISResult.id == hedis_id)
        result = await self.session.execute(stmt)
        hedis = result.scalar_one_or_none()
        if not hedis:
            return None

        await self._log_review(
            hedis.chart_id, "hedis", hedis_id, "approved", reviewer, notes,
        )
        await self._log_audit(
            "accept_hedis", "hedis_result", hedis_id, reviewer,
            {"measure_id": hedis.measure_id, "status": hedis.status, "notes": notes},
        )
        return self._serialize_hedis(hedis)

    async def reject_hedis(
        self, hedis_id: int, reviewer: str, notes: Optional[str] = None,
    ) -> bool:
        """Reject a HEDIS measure result."""
        stmt = select(HEDISResult).where(HEDISResult.id == hedis_id)
        result = await self.session.execute(stmt)
        hedis = result.scalar_one_or_none()
        if not hedis:
            return False

        await self._log_review(
            hedis.chart_id, "hedis", hedis_id, "rejected", reviewer, notes,
            previous_value=self._serialize_hedis(hedis),
        )
        await self._log_audit(
            "reject_hedis", "hedis_result", hedis_id, reviewer,
            {"measure_id": hedis.measure_id, "notes": notes},
        )
        hedis.status = "rejected"
        await self.session.flush()
        return True

    async def update_hedis(
        self, hedis_id: int, reviewer: str,
        status: Optional[str] = None,
        evidence: Optional[list[dict]] = None,
        notes: Optional[str] = None,
    ) -> Optional[dict]:
        """Update a HEDIS measure result."""
        stmt = select(HEDISResult).where(HEDISResult.id == hedis_id)
        result = await self.session.execute(stmt)
        hedis = result.scalar_one_or_none()
        if not hedis:
            return None

        previous = self._serialize_hedis(hedis)
        if status:
            hedis.status = status
            hedis.compliant = status == "met"
        if evidence is not None:
            hedis.evidence_used = evidence

        await self.session.flush()
        await self._log_review(
            hedis.chart_id, "hedis", hedis_id, "modified", reviewer, notes,
            previous_value=previous,
            new_value={"status": hedis.status, "evidence": hedis.evidence_used},
        )
        return self._serialize_hedis(hedis)

    async def add_hedis(
        self, chart_id: int, measure_id: str, measure_name: str,
        status: str, reviewer: str, notes: Optional[str] = None,
        evidence: Optional[list[dict]] = None,
        measurement_year: Optional[int] = None,
    ) -> dict:
        """Add a new HEDIS measure result (coder-added)."""
        hedis = HEDISResult(
            chart_id=chart_id,
            measure_id=measure_id,
            measure_name=measure_name,
            status=status,
            applicable=True,
            compliant=status == "met",
            evidence_used=evidence or [],
            gaps=[],
            trace=[{"source": "coder", "reviewer": reviewer, "notes": notes}],
            measurement_year=measurement_year or datetime.utcnow().year,
        )
        self.session.add(hedis)
        await self.session.flush()

        await self._log_audit(
            "add_hedis", "hedis_result", hedis.id, reviewer,
            {"measure_id": measure_id, "status": status, "notes": notes},
        )
        await self._log_review(
            chart_id, "hedis", hedis.id, "added", reviewer, notes,
            new_value={"measure_id": measure_id, "status": status},
        )
        return self._serialize_hedis(hedis)

    # =========================================================================
    # SAVE DOCUMENT — Export all reviewed data as JSON
    # =========================================================================

    async def save_document(
        self, chart_id: int, reviewer: str, comments: Optional[str] = None,
    ) -> dict:
        """Save all reviewed info for a chart as a structured document."""
        # Get chart
        stmt = select(Chart).where(Chart.id == chart_id)
        result = await self.session.execute(stmt)
        chart = result.scalar_one_or_none()
        if not chart:
            return {"error": "Chart not found"}

        # Get reviewed assertions
        stmt = select(Assertion).where(
            Assertion.chart_id == chart_id,
            Assertion.review_status.in_(["approved", "rejected"]),
        ).order_by(Assertion.id)
        result = await self.session.execute(stmt)
        reviewed_assertions = result.scalars().all()

        # Get all review actions
        stmt = select(ReviewAction).where(
            ReviewAction.chart_id == chart_id,
        ).order_by(ReviewAction.created_at)
        result = await self.session.execute(stmt)
        review_actions = result.scalars().all()

        # Get payable HCCs
        stmt = select(PayableHCC).where(PayableHCC.chart_id == chart_id)
        result = await self.session.execute(stmt)
        hccs = result.scalars().all()

        # Get HEDIS results
        stmt = select(HEDISResult).where(HEDISResult.chart_id == chart_id)
        result = await self.session.execute(stmt)
        hedis_results = result.scalars().all()

        # Get RAF summary
        stmt = select(RAFSummary).where(RAFSummary.chart_id == chart_id)
        result = await self.session.execute(stmt)
        raf = result.scalar_one_or_none()

        document = {
            "chart_id": chart_id,
            "filename": chart.filename,
            "saved_at": datetime.utcnow().isoformat(),
            "saved_by": reviewer,
            "comments": comments,
            "reviewed_diagnoses": {
                "approved": [
                    self._serialize_assertion(a) for a in reviewed_assertions
                    if a.review_status == "approved" and a.category in ("diagnosis", "assessment")
                ],
                "rejected": [
                    self._serialize_assertion(a) for a in reviewed_assertions
                    if a.review_status == "rejected" and a.category in ("diagnosis", "assessment")
                ],
            },
            "payable_hccs": [self._serialize_hcc(h) for h in hccs],
            "hedis_results": [self._serialize_hedis(h) for h in hedis_results],
            "raf_summary": {
                "total_raf_score": float(raf.total_raf_score) if raf else 0,
                "demographic_raf": float(raf.demographic_raf) if raf else 0,
                "hcc_raf": float(raf.hcc_raf) if raf else 0,
                "payable_hcc_count": raf.payable_hcc_count if raf else 0,
            },
            "review_history": [
                {
                    "entity_type": ra.entity_type,
                    "entity_id": ra.entity_id,
                    "action": ra.action,
                    "reviewer": ra.reviewer,
                    "notes": ra.notes,
                    "created_at": str(ra.created_at) if ra.created_at else None,
                }
                for ra in review_actions
            ],
        }

        await self._log_audit(
            "save_document", "chart", chart_id, reviewer,
            {"comments": comments, "diagnosis_count": len(reviewed_assertions)},
        )
        return document

    # =========================================================================
    # GET REVIEW SUMMARY FOR A CHART
    # =========================================================================

    async def get_review_summary(self, chart_id: int) -> dict:
        """Get summary of all review actions for a chart."""
        stmt = select(ReviewAction).where(
            ReviewAction.chart_id == chart_id,
        ).order_by(ReviewAction.created_at.desc())
        result = await self.session.execute(stmt)
        actions = result.scalars().all()

        return {
            "chart_id": chart_id,
            "total_actions": len(actions),
            "actions": [
                {
                    "id": a.id,
                    "entity_type": a.entity_type,
                    "entity_id": a.entity_id,
                    "action": a.action,
                    "reviewer": a.reviewer,
                    "notes": a.notes,
                    "previous_value": a.previous_value,
                    "new_value": a.new_value,
                    "created_at": str(a.created_at) if a.created_at else None,
                }
                for a in actions
            ],
        }

    # =========================================================================
    # HELPERS
    # =========================================================================

    async def _update_assertion_review(
        self, assertion_id: int, review_status: str, reviewer: str,
        notes: Optional[str] = None, date_of_service: Optional[str] = None,
    ) -> Optional[dict]:
        stmt = select(Assertion).where(Assertion.id == assertion_id)
        result = await self.session.execute(stmt)
        assertion = result.scalar_one_or_none()
        if not assertion:
            return None

        assertion.review_status = review_status
        assertion.reviewed_by = reviewer
        assertion.reviewed_at = datetime.utcnow()
        assertion.review_notes = notes
        if date_of_service:
            assertion.effective_date = date_of_service

        await self.session.flush()
        await self._log_audit(
            f"review_{review_status}", "assertion", assertion_id, reviewer,
            {"notes": notes},
        )
        await self._log_review(
            assertion.chart_id, "assertion", assertion_id, review_status,
            reviewer, notes,
        )
        return self._serialize_assertion(assertion)

    async def _log_audit(
        self, action: str, entity_type: str, entity_id: int,
        user_name: str, details: Optional[dict] = None,
    ) -> None:
        log = AuditLog(
            user_name=user_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        self.session.add(log)

    async def _log_review(
        self, chart_id: int, entity_type: str, entity_id: int,
        action: str, reviewer: str, notes: Optional[str] = None,
        previous_value: Any = None, new_value: Any = None,
    ) -> None:
        ra = ReviewAction(
            chart_id=chart_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            reviewer=reviewer,
            notes=notes,
            previous_value=previous_value if isinstance(previous_value, dict) else None,
            new_value=new_value if isinstance(new_value, dict) else None,
        )
        self.session.add(ra)

    def _serialize_assertion(self, a: Assertion) -> dict:
        return {
            "id": a.id,
            "chart_id": a.chart_id,
            "assertion_id": a.assertion_id,
            "category": a.category,
            "concept": a.concept,
            "canonical_concept": a.canonical_concept,
            "text": a.text,
            "status": a.status,
            "icd_codes": a.icd_codes,
            "effective_date": a.effective_date,
            "page_number": a.page_number,
            "exact_quote": a.exact_quote,
            "evidence_rank": a.evidence_rank,
            "is_payable_ra_candidate": a.is_payable_ra_candidate,
            "review_status": a.review_status,
            "reviewed_by": a.reviewed_by,
            "reviewed_at": str(a.reviewed_at) if a.reviewed_at else None,
            "review_notes": a.review_notes,
            "source": "coder" if "[Coder-added]" in (a.text or "") else "ai",
        }

    def _serialize_hcc(self, h: PayableHCC) -> dict:
        return {
            "id": h.id,
            "chart_id": h.chart_id,
            "hcc_code": h.hcc_code,
            "hcc_description": h.hcc_description,
            "raf_weight": float(h.raf_weight) if h.raf_weight else 0,
            "confidence": float(h.confidence) if h.confidence else 0,
            "source": h.source or "ai",
            "supported_icds": h.supported_icds,
            "icd_count": h.icd_count,
            "hierarchy_applied": h.hierarchy_applied,
            "measurement_year": h.measurement_year,
        }

    def _serialize_hedis(self, h: HEDISResult) -> dict:
        return {
            "id": h.id,
            "chart_id": h.chart_id,
            "measure_id": h.measure_id,
            "measure_name": h.measure_name,
            "status": h.status,
            "applicable": h.applicable,
            "compliant": h.compliant,
            "evidence_used": h.evidence_used,
            "gaps": h.gaps,
            "measurement_year": h.measurement_year,
        }
