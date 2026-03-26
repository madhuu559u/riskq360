"""Repository for PayableHCC and SuppressedHCC tables."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PayableHCC, SuppressedHCC


class HCCRepository:
    """Async CRUD for payable and suppressed HCCs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- PayableHCC ----

    async def create_payable(self, **kwargs: Any) -> PayableHCC:
        rec = PayableHCC(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def create_payable_bulk(self, items: list[dict[str, Any]]) -> int:
        objects = [PayableHCC(**item) for item in items]
        self.session.add_all(objects)
        await self.session.flush()
        return len(objects)

    async def get_payable_by_chart(self, chart_id: int) -> Sequence[PayableHCC]:
        stmt = (
            select(PayableHCC)
            .where(PayableHCC.chart_id == chart_id)
            .order_by(PayableHCC.hcc_code)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_payable_by_id(self, hcc_id: int) -> Optional[PayableHCC]:
        stmt = select(PayableHCC).where(PayableHCC.id == hcc_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_payable(self, chart_id: int) -> int:
        stmt = select(func.count(PayableHCC.id)).where(PayableHCC.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_payable_by_chart(self, chart_id: int) -> int:
        stmt = delete(PayableHCC).where(PayableHCC.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    # ---- SuppressedHCC ----

    async def create_suppressed(self, **kwargs: Any) -> SuppressedHCC:
        rec = SuppressedHCC(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def create_suppressed_bulk(self, items: list[dict[str, Any]]) -> int:
        objects = [SuppressedHCC(**item) for item in items]
        self.session.add_all(objects)
        await self.session.flush()
        return len(objects)

    async def get_suppressed_by_chart(self, chart_id: int) -> Sequence[SuppressedHCC]:
        stmt = (
            select(SuppressedHCC)
            .where(SuppressedHCC.chart_id == chart_id)
            .order_by(SuppressedHCC.hcc_code)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_suppressed_by_chart(self, chart_id: int) -> int:
        stmt = delete(SuppressedHCC).where(SuppressedHCC.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    # ---- Cleanup ----

    async def delete_all_by_chart(self, chart_id: int) -> dict[str, int]:
        return {
            "payable": await self.delete_payable_by_chart(chart_id),
            "suppressed": await self.delete_suppressed_by_chart(chart_id),
        }
