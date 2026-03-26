"""Audit service — audit logging, review workflow."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

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
