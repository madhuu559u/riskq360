"""Risk adjustment service — HCC pack, RAF scores, hierarchy."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.hcc_repo import HCCRepository
from database.repositories.raf_repo import RAFRepository


class RiskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.hccs = HCCRepository(session)
        self.raf = RAFRepository(session)

    async def get_hcc_pack(self, chart_id: int) -> dict:
        payable = await self.hccs.get_payable_by_chart(chart_id)
        suppressed = await self.hccs.get_suppressed_by_chart(chart_id)
        raf_summary = await self.raf.get_summary_by_chart(chart_id)
        hierarchy = await self.raf.get_hierarchy_by_chart(chart_id)

        return {
            "chart_id": chart_id,
            "payable_hccs": [self._serialize_hcc(h) for h in payable],
            "suppressed_hccs": [self._serialize_suppressed(s) for s in suppressed],
            "raf_summary": self._serialize_raf(raf_summary) if raf_summary else {},
            "hierarchy_log": [
                {"suppressed": h.suppressed_hcc, "by": h.suppressed_by, "group": h.group_name}
                for h in hierarchy
            ],
            "payable_hcc_count": len(payable),
            "suppressed_hcc_count": len(suppressed),
        }

    async def get_raf_summary(self, chart_id: int) -> Optional[dict]:
        raf = await self.raf.get_summary_by_chart(chart_id)
        return self._serialize_raf(raf) if raf else None

    async def get_hierarchy(self, chart_id: int) -> dict:
        hierarchy = await self.raf.get_hierarchy_by_chart(chart_id)
        payable = await self.hccs.get_payable_by_chart(chart_id)
        return {
            "chart_id": chart_id,
            "hierarchy_details": [
                {"suppressed": h.suppressed_hcc, "by": h.suppressed_by, "group": h.group_name}
                for h in hierarchy
            ],
            "payable_with_hierarchy": [
                {
                    "hcc_code": h.hcc_code,
                    "hierarchy_applied": h.hierarchy_applied,
                    "raf_weight": float(h.raf_weight) if h.raf_weight else 0,
                }
                for h in payable if h.hierarchy_applied
            ],
        }

    def _serialize_hcc(self, h: Any) -> dict:
        return {
            "id": h.id,
            "hcc_code": h.hcc_code,
            "hcc_description": h.hcc_description,
            "raf_weight": float(h.raf_weight) if h.raf_weight else 0,
            "hierarchy_applied": h.hierarchy_applied,
            "supported_icds": h.supported_icds or [],
            "icd_count": h.icd_count,
            "measurement_year": h.measurement_year,
        }

    def _serialize_suppressed(self, s: Any) -> dict:
        return {
            "hcc_code": s.hcc_code,
            "hcc_description": s.hcc_description,
            "suppressed_by": s.suppressed_by,
            "hierarchy_group": s.hierarchy_group,
            "supported_icds": s.supported_icds or [],
        }

    def _serialize_raf(self, r: Any) -> dict:
        return {
            "total_raf_score": float(r.total_raf_score) if r.total_raf_score else 0,
            "demographic_raf": float(r.demographic_raf) if r.demographic_raf else 0,
            "hcc_raf": float(r.hcc_raf) if r.hcc_raf else 0,
            "hcc_count": r.hcc_count,
            "payable_hcc_count": r.payable_hcc_count,
            "suppressed_hcc_count": r.suppressed_hcc_count,
            "unmapped_icd_count": r.unmapped_icd_count,
            "total_payable_icds": r.total_payable_icds,
            "measurement_year": r.measurement_year,
        }
