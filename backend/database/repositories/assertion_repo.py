"""Repository for Assertions and ConditionGroups — the central clinical data tables."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Assertion, ConditionGroup


class AssertionRepository:
    """Async CRUD for assertions (the central clinical data table)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Assertion CRUD ----

    async def create(self, **kwargs: Any) -> Assertion:
        obj = Assertion(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def create_bulk(self, items: list[dict[str, Any]]) -> int:
        objects = [Assertion(**item) for item in items]
        self.session.add_all(objects)
        await self.session.flush()
        return len(objects)

    async def get_by_id(self, assertion_id: int) -> Optional[Assertion]:
        stmt = select(Assertion).where(Assertion.id == assertion_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_chart(
        self, chart_id: int, category: Optional[str] = None,
        status: Optional[str] = None, limit: int = 1000, offset: int = 0,
    ) -> Sequence[Assertion]:
        stmt = select(Assertion).where(Assertion.chart_id == chart_id)
        if category:
            stmt = stmt.where(Assertion.category == category)
        if status:
            stmt = stmt.where(Assertion.status == status)
        stmt = stmt.order_by(Assertion.page_number, Assertion.id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_diagnoses(self, chart_id: int) -> Sequence[Assertion]:
        stmt = (
            select(Assertion)
            .where(Assertion.chart_id == chart_id)
            .where(Assertion.category.in_(["diagnosis", "assessment"]))
            .order_by(Assertion.page_number, Assertion.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_medications(self, chart_id: int) -> Sequence[Assertion]:
        stmt = (
            select(Assertion)
            .where(Assertion.chart_id == chart_id, Assertion.category == "medication")
            .order_by(Assertion.page_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_vitals(self, chart_id: int) -> Sequence[Assertion]:
        stmt = (
            select(Assertion)
            .where(Assertion.chart_id == chart_id, Assertion.category == "vital_sign")
            .order_by(Assertion.page_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_labs(self, chart_id: int) -> Sequence[Assertion]:
        stmt = (
            select(Assertion)
            .where(Assertion.chart_id == chart_id)
            .where(Assertion.category.in_(["lab_result", "lab_order"]))
            .order_by(Assertion.page_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_hedis_evidence(self, chart_id: int) -> Sequence[Assertion]:
        stmt = (
            select(Assertion)
            .where(Assertion.chart_id == chart_id, Assertion.is_hedis_evidence.is_(True))
            .order_by(Assertion.page_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_ra_candidates(self, chart_id: int) -> Sequence[Assertion]:
        stmt = (
            select(Assertion)
            .where(Assertion.chart_id == chart_id, Assertion.is_payable_ra_candidate.is_(True))
            .order_by(Assertion.page_number)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_pending_review(self, chart_id: Optional[int] = None) -> Sequence[Assertion]:
        stmt = select(Assertion).where(Assertion.review_status == "pending")
        if chart_id:
            stmt = stmt.where(Assertion.chart_id == chart_id)
        stmt = stmt.order_by(Assertion.id).limit(200)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_review(
        self, assertion_id: int, review_status: str,
        reviewed_by: str, review_notes: Optional[str] = None,
    ) -> Optional[Assertion]:
        from datetime import datetime
        stmt = (
            update(Assertion)
            .where(Assertion.id == assertion_id)
            .values(
                review_status=review_status,
                reviewed_by=reviewed_by,
                reviewed_at=datetime.utcnow(),
                review_notes=review_notes,
            )
            .returning(Assertion)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def count_by_chart(self, chart_id: int) -> int:
        stmt = select(func.count(Assertion.id)).where(Assertion.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_category(self, chart_id: int) -> list[tuple[str, int]]:
        stmt = (
            select(Assertion.category, func.count(Assertion.id))
            .where(Assertion.chart_id == chart_id)
            .group_by(Assertion.category)
            .order_by(func.count(Assertion.id).desc())
        )
        result = await self.session.execute(stmt)
        return result.all()

    async def delete_by_chart(self, chart_id: int) -> int:
        stmt = delete(Assertion).where(Assertion.chart_id == chart_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    # ---- ConditionGroup CRUD ----

    async def create_condition_group(self, **kwargs: Any) -> ConditionGroup:
        obj = ConditionGroup(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_condition_groups(self, chart_id: int) -> Sequence[ConditionGroup]:
        stmt = (
            select(ConditionGroup)
            .where(ConditionGroup.chart_id == chart_id)
            .order_by(ConditionGroup.group_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
