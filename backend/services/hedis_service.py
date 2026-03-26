"""HEDIS service — measures, gaps, evidence."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.hedis_repo import HEDISRepository


class HEDISService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = HEDISRepository(session)

    async def get_measures(self, chart_id: int, status: Optional[str] = None) -> dict:
        results = await self.repo.get_results_by_chart(chart_id, status=status)
        serialized = [self._serialize(r) for r in results]
        summary = await self.get_summary(chart_id)
        preview_summary = self._summarize_preview(serialized, measurement_year=(summary or {}).get("measurement_year"))
        default_view_mode = "strict"
        if (summary or {}).get("applicable", 0) == 0 and preview_summary.get("applicable", 0) > 0:
            default_view_mode = "clinical_preview"
        return {
            "chart_id": chart_id,
            "measures": serialized,
            "summary": summary or {},
            "summary_preview": preview_summary,
            "default_view_mode": default_view_mode,
            "count": len(results),
        }

    async def get_gaps(self, chart_id: int) -> dict:
        gaps = await self.repo.get_gaps(chart_id)
        return {"chart_id": chart_id, "gaps": [self._serialize(g) for g in gaps], "count": len(gaps)}

    async def get_met(self, chart_id: int) -> dict:
        met = await self.repo.get_met(chart_id)
        return {"chart_id": chart_id, "met": [self._serialize(m) for m in met], "count": len(met)}

    async def get_measure_detail(self, chart_id: int, measure_id: str) -> Optional[dict]:
        result = await self.repo.get_result_by_measure(chart_id, measure_id)
        return self._serialize(result) if result else None

    async def get_summary(self, chart_id: int) -> Optional[dict]:
        summary = await self.repo.get_summary_by_chart(chart_id)
        rows = await self.repo.get_results_by_chart(chart_id)

        if summary:
            result = self._serialize_summary(summary)
            if rows:
                # Prefer row-derived counts for statuses not stored in legacy summary columns.
                status_counts: dict[str, int] = {
                    "met": 0,
                    "gap": 0,
                    "not_applicable": 0,
                    "excluded": 0,
                    "indeterminate": 0,
                    "inactive": 0,
                }
                applicable_count = 0
                for r in rows:
                    status = str(r.status or "")
                    if status in status_counts:
                        status_counts[status] += 1
                    if bool(r.applicable):
                        applicable_count += 1
                result.update(status_counts)
                result["applicable"] = applicable_count
                result["total_measures"] = len(rows)
            return result

        # Fallback: derive summary from hedis_results when summary row is missing.
        if not rows:
            return None

        counts = {
            "total_measures": len(rows),
            "met": 0,
            "gap": 0,
            "not_applicable": 0,
            "excluded": 0,
            "indeterminate": 0,
            "inactive": 0,
            "applicable": 0,
            "measurement_year": rows[0].measurement_year,
        }
        for r in rows:
            status = str(r.status or "")
            if status in counts:
                counts[status] += 1
            if bool(r.applicable):
                counts["applicable"] += 1
        return counts

    async def get_status_counts(self, chart_id: int) -> dict:
        return await self.repo.count_by_status(chart_id)

    def _serialize(self, r: Any) -> dict:
        trace = r.trace or []
        trace_out: list[Any] = []
        meta: dict[str, Any] = {}
        if isinstance(trace, list):
            for item in trace:
                if (
                    isinstance(item, dict)
                    and item.get("rule") == "__measure_payload__"
                    and isinstance(item.get("meta"), dict)
                ):
                    meta = item["meta"]
                    continue
                trace_out.append(item)
        else:
            trace_out = trace

        payload = {
            "id": r.id,
            "chart_id": r.chart_id,
            "measure_id": r.measure_id,
            "measure_name": r.measure_name,
            "status": r.status,
            "applicable": r.applicable,
            "compliant": r.compliant,
            "evidence_used": r.evidence_used or [],
            "gaps": r.gaps or [],
            "trace": trace_out,
            "measurement_year": r.measurement_year,
        }
        for key in (
            "measure_definition",
            "decision_reasoning",
            "eligibility_reason",
            "compliance_reason",
            "exclusion_reason",
            "missing_data",
            "confidence",
            "clinical_only_preview",
            "enrollment_dependency",
            "denominator_signal",
            "coding_opportunity",
            "llm_adjudication",
        ):
            if key in meta:
                payload[key] = meta.get(key)
        return payload

    def _serialize_summary(self, s: Any) -> dict:
        total = s.total_measures or 0
        applicable = s.applicable_count or 0
        inactive = max(total - applicable, 0)
        return {
            "total_measures": total,
            "applicable": applicable,
            "met": s.met_count or 0,
            "gap": s.gap_count or 0,
            "excluded": s.excluded_count or 0,
            "indeterminate": s.indeterminate_count or 0,
            "not_applicable": s.not_applicable_count or 0,
            "inactive": inactive,
            "measurement_year": s.measurement_year,
        }

    def _summarize_preview(self, measures: list[dict[str, Any]], measurement_year: Optional[int] = None) -> dict:
        summary = {
            "total_measures": len(measures),
            "applicable": 0,
            "met": 0,
            "gap": 0,
            "excluded": 0,
            "indeterminate": 0,
            "not_applicable": 0,
            "inactive": 0,
            "measurement_year": measurement_year,
        }
        for measure in measures:
            if measure.get("status") == "inactive":
                summary["inactive"] += 1
                continue
            selected = measure.get("clinical_only_preview") or measure
            if bool(selected.get("applicable")):
                summary["applicable"] += 1
            status = str(selected.get("status") or "")
            if status in summary:
                summary[status] += 1
        return summary
