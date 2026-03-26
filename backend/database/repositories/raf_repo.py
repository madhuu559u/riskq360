"""Repository for RAFSummary and HCCHierarchyLog tables."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import HCCHierarchyLog, RAFSummary


class RAFRepository:
    """Async CRUD for RAF summaries and HCC hierarchy logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- RAFSummary ----

    async def create_summary(self, **kwargs: Any) -> RAFSummary:
        rec = RAFSummary(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_summary_by_chart(self, chart_id: int) -> Optional[RAFSummary]:
        stmt = (
            select(RAFSummary)
            .where(RAFSummary.chart_id == chart_id)
            .order_by(RAFSummary.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_summaries(self, offset: int = 0, limit: int = 50) -> Sequence[RAFSummary]:
        stmt = select(RAFSummary).order_by(RAFSummary.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_chart(self, chart_id: int) -> int:
        stmt = delete(RAFSummary).where(RAFSummary.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    # ---- HCCHierarchyLog ----

    async def create_hierarchy_log(self, **kwargs: Any) -> HCCHierarchyLog:
        rec = HCCHierarchyLog(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def create_hierarchy_logs_bulk(self, items: list[dict[str, Any]]) -> int:
        objects = [HCCHierarchyLog(**item) for item in items]
        self.session.add_all(objects)
        await self.session.flush()
        return len(objects)

    async def get_hierarchy_by_chart(self, chart_id: int) -> Sequence[HCCHierarchyLog]:
        stmt = (
            select(HCCHierarchyLog)
            .where(HCCHierarchyLog.chart_id == chart_id)
            .order_by(HCCHierarchyLog.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_hierarchy_by_chart(self, chart_id: int) -> int:
        stmt = delete(HCCHierarchyLog).where(HCCHierarchyLog.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.rowcount
