"""Repository for AuditLog and ReviewAction tables."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditLog, ReviewAction


class AuditRepository:
    """Async CRUD for audit logs and review actions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- AuditLog ----

    async def create_log(self, **kwargs: Any) -> AuditLog:
        rec = AuditLog(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_logs(
        self, entity_type: Optional[str] = None,
        limit: int = 100, offset: int = 0,
    ) -> Sequence[AuditLog]:
        stmt = select(AuditLog)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_logs_by_entity(self, entity_type: str, entity_id: int) -> Sequence[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_logs(self) -> int:
        result = await self.session.execute(select(func.count(AuditLog.id)))
        return result.scalar_one()

    # ---- ReviewAction ----

    async def create_review(self, **kwargs: Any) -> ReviewAction:
        rec = ReviewAction(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_reviews_by_chart(self, chart_id: int) -> Sequence[ReviewAction]:
        stmt = (
            select(ReviewAction)
            .where(ReviewAction.chart_id == chart_id)
            .order_by(ReviewAction.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
