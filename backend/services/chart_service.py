"""Chart lifecycle service — create, list, get, delete, with full DB backing."""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.chart_repo import ChartRepository
from database.repositories.assertion_repo import AssertionRepository
from database.repositories.hcc_repo import HCCRepository
from database.repositories.hedis_repo import HEDISRepository
from database.repositories.raf_repo import RAFRepository

log = logging.getLogger(__name__)


class ChartService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.charts = ChartRepository(session)

    async def create_chart(self, **kwargs: Any) -> dict:
        chart = await self.charts.create(**kwargs)
        return self._serialize(chart)

    async def get_chart(self, chart_id: int) -> Optional[dict]:
        chart = await self.charts.get_by_id(chart_id)
        if not chart:
            return None
        return self._serialize(chart)

    async def list_charts(
        self, offset: int = 0, limit: int = 50, status: Optional[str] = None,
    ) -> dict:
        charts = await self.charts.list_all(offset=offset, limit=limit, status=status)
        total = await self.charts.count(status=status)

        # Enrich each chart with raf_summary + hedis_summary data so the
        # frontend can show scores on the chart list without separate requests.
        raf_repo = RAFRepository(self.session)
        hedis_repo = HEDISRepository(self.session)
        serialized: list[dict] = []
        for c in charts:
            data = self._serialize(c)
            if c.status == "completed":
                try:
                    raf_summary = await raf_repo.get_summary_by_chart(c.id)
                    if raf_summary:
                        data["raf_summary"] = {
                            "total_raf_score": float(raf_summary.total_raf_score) if raf_summary.total_raf_score else 0,
                            "hcc_raf": float(raf_summary.hcc_raf) if raf_summary.hcc_raf else 0,
                            "payable_hcc_count": raf_summary.payable_hcc_count or 0,
                            "hcc_count": raf_summary.hcc_count or 0,
                        }
                except Exception:
                    log.debug("Could not fetch raf_summary for chart %s", c.id, exc_info=True)
                try:
                    hedis_summary = await hedis_repo.get_summary_by_chart(c.id)
                    if hedis_summary:
                        data["hedis_summary"] = {
                            "total_measures": hedis_summary.total_measures or 0,
                            "met_count": hedis_summary.met_count or 0,
                            "gap_count": hedis_summary.gap_count or 0,
                        }
                except Exception:
                    log.debug("Could not fetch hedis_summary for chart %s", c.id, exc_info=True)
            serialized.append(data)

        return {
            "charts": serialized,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def update_status(self, chart_id: int, status: str) -> Optional[dict]:
        chart = await self.charts.update_status(chart_id, status)
        return self._serialize(chart) if chart else None

    async def delete_chart(self, chart_id: int) -> bool:
        return await self.charts.delete(chart_id)

    async def get_chart_summary(self, chart_id: int) -> Optional[dict]:
        """Get a full chart summary including assertion counts, RAF, HEDIS."""
        chart = await self.charts.get_by_id(chart_id)
        if not chart:
            return None

        base = self._serialize(chart)

        # Build summary sub-sections individually so a single repo failure
        # does not bring down the entire endpoint with a 500.
        assertions_count = 0
        category_counts: dict = {}
        risk_adjustment: dict = {"payable_hcc_count": 0, "total_raf_score": 0, "hcc_raf": 0}
        hedis_data: dict = {"total_measures": 0, "met": 0, "gap": 0}

        try:
            assertions = AssertionRepository(self.session)
            assertions_count = await assertions.count_by_chart(chart_id)
            category_counts = {cat: cnt for cat, cnt in await assertions.count_by_category(chart_id)}
        except Exception:
            log.warning("Could not load assertion data for chart %s", chart_id, exc_info=True)

        try:
            hccs = HCCRepository(self.session)
            raf = RAFRepository(self.session)
            payable_hcc_count = await hccs.count_payable(chart_id)
            raf_summary = await raf.get_summary_by_chart(chart_id)
            risk_adjustment = {
                "payable_hcc_count": payable_hcc_count,
                "total_raf_score": float(raf_summary.total_raf_score) if raf_summary else 0,
                "hcc_raf": float(raf_summary.hcc_raf) if raf_summary else 0,
            }
        except Exception:
            log.warning("Could not load risk adjustment data for chart %s", chart_id, exc_info=True)

        try:
            hedis = HEDISRepository(self.session)
            hedis_summary = await hedis.get_summary_by_chart(chart_id)
            hedis_data = {
                "total_measures": hedis_summary.total_measures if hedis_summary else 0,
                "met": hedis_summary.met_count if hedis_summary else 0,
                "gap": hedis_summary.gap_count if hedis_summary else 0,
            }
        except Exception:
            log.warning("Could not load HEDIS data for chart %s", chart_id, exc_info=True)

        return {
            **base,
            "assertions_count": assertions_count,
            "category_counts": category_counts,
            "risk_adjustment": risk_adjustment,
            "hedis": hedis_data,
        }

    def _serialize(self, chart: Any) -> dict:
        patient = getattr(chart, "patient", None)
        return {
            "id": chart.id,
            "filename": chart.filename,
            "file_path": chart.file_path,
            "file_size_bytes": chart.file_size_bytes,
            "page_count": chart.page_count,
            "pages_with_text": chart.pages_with_text,
            "total_chars": chart.total_chars,
            "upload_source": chart.upload_source,
            "status": chart.status,
            "quality_score_avg": chart.quality_score_avg,
            "created_at": str(chart.created_at) if chart.created_at else None,
            "updated_at": str(chart.updated_at) if chart.updated_at else None,
            "patient_name": patient.patient_name if patient else None,
            "patient_dob": patient.date_of_birth if patient else None,
        }
