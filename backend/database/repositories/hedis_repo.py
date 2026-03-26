"""Repository for HEDISResult and HEDISSummary tables."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import HEDISResult, HEDISSummary


class HEDISRepository:
    """Async CRUD for HEDIS results and summaries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- HEDISResult ----

    async def create_result(self, **kwargs: Any) -> HEDISResult:
        rec = HEDISResult(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def create_results_bulk(self, items: list[dict[str, Any]]) -> int:
        objects = [HEDISResult(**item) for item in items]
        self.session.add_all(objects)
        await self.session.flush()
        return len(objects)

    async def get_results_by_chart(
        self, chart_id: int, status: Optional[str] = None,
    ) -> Sequence[HEDISResult]:
        stmt = select(HEDISResult).where(HEDISResult.chart_id == chart_id)
        if status:
            stmt = stmt.where(HEDISResult.status == status)
        stmt = stmt.order_by(HEDISResult.measure_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_gaps(self, chart_id: int) -> Sequence[HEDISResult]:
        return await self.get_results_by_chart(chart_id, status="gap")

    async def get_met(self, chart_id: int) -> Sequence[HEDISResult]:
        return await self.get_results_by_chart(chart_id, status="met")

    async def get_applicable(self, chart_id: int) -> Sequence[HEDISResult]:
        stmt = (
            select(HEDISResult)
            .where(HEDISResult.chart_id == chart_id, HEDISResult.applicable.is_(True))
            .order_by(HEDISResult.measure_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_result_by_measure(
        self, chart_id: int, measure_id: str,
    ) -> Optional[HEDISResult]:
        stmt = select(HEDISResult).where(
            HEDISResult.chart_id == chart_id, HEDISResult.measure_id == measure_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_status(self, chart_id: int) -> dict[str, int]:
        stmt = (
            select(HEDISResult.status, func.count(HEDISResult.id))
            .where(HEDISResult.chart_id == chart_id)
            .group_by(HEDISResult.status)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def delete_results_by_chart(self, chart_id: int) -> int:
        stmt = delete(HEDISResult).where(HEDISResult.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    # ---- HEDISSummary ----

    async def create_summary(self, **kwargs: Any) -> HEDISSummary:
        rec = HEDISSummary(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_summary_by_chart(self, chart_id: int) -> Optional[HEDISSummary]:
        stmt = (
            select(HEDISSummary)
            .where(HEDISSummary.chart_id == chart_id)
            .order_by(HEDISSummary.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_summaries_by_chart(self, chart_id: int) -> int:
        stmt = delete(HEDISSummary).where(HEDISSummary.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    # ---- Cleanup ----

    async def delete_all_by_chart(self, chart_id: int) -> dict[str, int]:
        return {
            "results": await self.delete_results_by_chart(chart_id),
            "summaries": await self.delete_summaries_by_chart(chart_id),
        }
