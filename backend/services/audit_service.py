"""Audit service — audit logging, review workflow, audit packs, risk scores."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Assertion, PayableHCC, RAFSummary
from database.repositories.audit_repo import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuditRepository(session)

    async def log_action(
        self, action: str, entity_type: str, entity_id: int,
        user_name: str = "system", details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        log = await self.repo.create_log(
            action=action, entity_type=entity_type, entity_id=entity_id,
            user_name=user_name, details=details, ip_address=ip_address,
        )
        return {"id": log.id, "action": action, "entity_type": entity_type, "entity_id": entity_id}

    async def get_logs(
        self, entity_type: Optional[str] = None, limit: int = 100, offset: int = 0,
    ) -> dict:
        logs = await self.repo.get_logs(entity_type=entity_type, limit=limit, offset=offset)
        total = await self.repo.count_logs()
        return {
            "logs": [
                {
                    "id": l.id, "action": l.action, "entity_type": l.entity_type,
                    "entity_id": l.entity_id, "user_name": l.user_name,
                    "details": l.details, "created_at": str(l.created_at),
                }
                for l in logs
            ],
            "total": total,
        }

    async def create_review(
        self, chart_id: int, entity_type: str, entity_id: int,
        action: str, reviewer: str, notes: Optional[str] = None,
        previous_value: Optional[dict] = None, new_value: Optional[dict] = None,
    ) -> dict:
        review = await self.repo.create_review(
            chart_id=chart_id, entity_type=entity_type, entity_id=entity_id,
            action=action, reviewer=reviewer, notes=notes,
            previous_value=previous_value, new_value=new_value,
        )
        return {"id": review.id, "action": action, "entity_type": entity_type}

    async def get_reviews_by_chart(self, chart_id: int) -> dict:
        reviews = await self.repo.get_reviews_by_chart(chart_id)
        return {
            "reviews": [
                {
                    "id": r.id, "entity_type": r.entity_type, "entity_id": r.entity_id,
                    "action": r.action, "reviewer": r.reviewer, "notes": r.notes,
                    "created_at": str(r.created_at),
                }
                for r in reviews
            ],
            "count": len(reviews),
        }

    async def get_audit_pack(self, chart_id: int) -> dict:
        """Consolidate audit logs and review actions into a single audit pack for a chart."""
        # Get audit logs related to this chart's entities
        all_logs = await self.repo.get_logs(limit=500, offset=0)
        chart_logs = [
            log for log in all_logs
            if log.entity_type in ("assertion", "hcc", "hedis", "chart")
        ]

        # Get review actions for the chart
        reviews = await self.repo.get_reviews_by_chart(chart_id)

        # Get assertion review summary
        stmt = select(Assertion).where(Assertion.chart_id == chart_id)
        result = await self.session.execute(stmt)
        assertions = result.scalars().all()

        total_assertions = len(assertions)
        reviewed_count = sum(1 for a in assertions if a.review_status in ("approved", "rejected"))
        pending_count = sum(1 for a in assertions if a.review_status == "pending")
        approved_count = sum(1 for a in assertions if a.review_status == "approved")
        rejected_count = sum(1 for a in assertions if a.review_status == "rejected")

        return {
            "chart_id": chart_id,
            "audit_logs": [
                {
                    "id": l.id, "action": l.action, "entity_type": l.entity_type,
                    "entity_id": l.entity_id, "user_name": l.user_name,
                    "details": l.details, "created_at": str(l.created_at),
                }
                for l in chart_logs
            ],
            "review_actions": [
                {
                    "id": r.id, "entity_type": r.entity_type, "entity_id": r.entity_id,
                    "action": r.action, "reviewer": r.reviewer, "notes": r.notes,
                    "previous_value": r.previous_value, "new_value": r.new_value,
                    "created_at": str(r.created_at),
                }
                for r in reviews
            ],
            "summary": {
                "total_assertions": total_assertions,
                "reviewed_count": reviewed_count,
                "pending_count": pending_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "review_completion_pct": round(
                    (reviewed_count / total_assertions * 100) if total_assertions > 0 else 0, 1
                ),
                "total_audit_events": len(chart_logs),
                "total_review_actions": len(reviews),
            },
        }

    async def get_risk_scores(self, chart_id: int) -> dict:
        """Get per-diagnosis audit risk scores from assertions with risk metadata."""
        # Get diagnosis assertions with HCC/RA flags
        stmt = (
            select(Assertion)
            .where(
                Assertion.chart_id == chart_id,
                Assertion.category.in_(["diagnosis", "assessment"]),
            )
            .order_by(Assertion.page_number, Assertion.id)
        )
        result = await self.session.execute(stmt)
        diagnosis_assertions = result.scalars().all()

        # Get payable HCCs for cross-referencing
        hcc_stmt = select(PayableHCC).where(PayableHCC.chart_id == chart_id)
        hcc_result = await self.session.execute(hcc_stmt)
        payable_hccs = hcc_result.scalars().all()
        hcc_by_code: dict[str, PayableHCC] = {h.hcc_code: h for h in payable_hccs}

        # Get RAF summary
        raf_stmt = (
            select(RAFSummary)
            .where(RAFSummary.chart_id == chart_id)
            .order_by(RAFSummary.created_at.desc())
            .limit(1)
        )
        raf_result = await self.session.execute(raf_stmt)
        raf_summary = raf_result.scalar_one_or_none()

        risk_scores = []
        for a in diagnosis_assertions:
            icd_list = a.icd_codes_primary or a.icd_codes or []
            primary_icd = ""
            if isinstance(icd_list, list) and icd_list:
                first = icd_list[0] if isinstance(icd_list[0], dict) else {}
                primary_icd = str(first.get("code") or "")

            # Determine audit risk level based on evidence quality and flags
            risk_level = "low"
            risk_factors = []

            if a.evidence_rank and a.evidence_rank >= 3:
                risk_level = "high"
                risk_factors.append("weak_evidence")
            elif a.evidence_rank and a.evidence_rank == 2:
                risk_level = "medium"
                risk_factors.append("moderate_evidence")

            if a.status in ("uncertain", "historical"):
                risk_level = "high"
                risk_factors.append(f"status_{a.status}")

            if a.is_hcc_candidate and not a.is_payable_hcc_candidate:
                risk_factors.append("hcc_candidate_not_payable")

            if a.payable_hcc_exclusion_reason:
                risk_factors.append(f"excluded:{a.payable_hcc_exclusion_reason}")

            if a.review_status == "rejected":
                risk_level = "high"
                risk_factors.append("reviewer_rejected")

            if a.contradicted:
                risk_level = "high"
                risk_factors.append("contradicted")

            risk_scores.append({
                "assertion_id": a.id,
                "concept": a.canonical_concept or a.concept,
                "icd_code": primary_icd,
                "page_number": a.page_number,
                "status": a.status,
                "evidence_rank": a.evidence_rank,
                "is_hcc_candidate": a.is_hcc_candidate,
                "is_payable_ra_candidate": a.is_payable_ra_candidate,
                "review_status": a.review_status,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "payable_hcc_exclusion_reason": a.payable_hcc_exclusion_reason,
            })

        return {
            "chart_id": chart_id,
            "risk_scores": risk_scores,
            "total_diagnoses": len(risk_scores),
            "high_risk_count": sum(1 for s in risk_scores if s["risk_level"] == "high"),
            "medium_risk_count": sum(1 for s in risk_scores if s["risk_level"] == "medium"),
            "low_risk_count": sum(1 for s in risk_scores if s["risk_level"] == "low"),
            "raf_summary": {
                "total_raf_score": float(raf_summary.total_raf_score) if raf_summary and raf_summary.total_raf_score else 0,
                "hcc_count": raf_summary.hcc_count if raf_summary else 0,
                "payable_hcc_count": raf_summary.payable_hcc_count if raf_summary else 0,
            } if raf_summary else None,
        }
