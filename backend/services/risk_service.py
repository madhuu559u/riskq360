"""Risk adjustment service — HCC pack, RAF scores, hierarchy, ML predictions, ICD retrievals."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Assertion, DiagnosisCandidate, PayableHCC
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

    async def get_ml_predictions(self, chart_id: int) -> dict:
        """Get ML prediction results — assertions flagged as HCC candidates with confidence scores."""
        stmt = (
            select(Assertion)
            .where(Assertion.chart_id == chart_id, Assertion.is_hcc_candidate.is_(True))
            .order_by(Assertion.page_number, Assertion.id)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        # Enrich with payable HCC data for ensemble confidence
        payable = await self.hccs.get_payable_by_chart(chart_id)
        payable_by_icd: dict[str, PayableHCC] = {}
        for p in payable:
            for icd_entry in (p.supported_icds or []):
                code = icd_entry.get("icd10_code") or icd_entry.get("code", "")
                if code:
                    payable_by_icd[code] = p

        predictions = []
        for a in rows:
            icd_list = a.icd_codes_primary or a.icd_codes or []
            primary_icd = ""
            if isinstance(icd_list, list) and icd_list:
                first = icd_list[0] if isinstance(icd_list[0], dict) else {}
                primary_icd = str(first.get("code") or "")

            matched_hcc = payable_by_icd.get(primary_icd)
            predictions.append({
                "assertion_id": a.id,
                "assertion_ext_id": a.assertion_id,
                "category": a.category,
                "concept": a.canonical_concept or a.concept,
                "icd_code": primary_icd,
                "page_number": a.page_number,
                "exact_quote": a.exact_quote,
                "evidence_rank": a.evidence_rank,
                "is_payable_hcc_candidate": a.is_payable_hcc_candidate,
                "is_payable_ra_candidate": a.is_payable_ra_candidate,
                "ml_confidence": float(matched_hcc.confidence) if matched_hcc and matched_hcc.confidence else None,
                "llm_confidence": float(matched_hcc.llm_confidence) if matched_hcc and matched_hcc.llm_confidence else None,
                "hcc_code": matched_hcc.hcc_code if matched_hcc else None,
                "raf_weight": float(matched_hcc.raf_weight) if matched_hcc and matched_hcc.raf_weight else None,
                "source": matched_hcc.source if matched_hcc else None,
            })

        return {
            "chart_id": chart_id,
            "predictions": predictions,
            "total": len(predictions),
        }

    async def get_icd_retrievals(self, chart_id: int) -> dict:
        """Get TF-IDF ICD retrieval results from diagnosis candidates."""
        stmt = (
            select(DiagnosisCandidate)
            .where(DiagnosisCandidate.chart_id == chart_id)
            .order_by(
                DiagnosisCandidate.page_number.asc().nullslast(),
                DiagnosisCandidate.candidate_key.asc(),
            )
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        retrievals = []
        for dc in rows:
            payload = dc.payload or {}
            retrievals.append({
                "candidate_id": dc.id,
                "candidate_key": dc.candidate_key,
                "icd10_code": dc.icd10_code,
                "hcc_code": dc.hcc_code,
                "source_type": dc.source_type,
                "lifecycle_state": dc.lifecycle_state,
                "confidence": dc.confidence,
                "tfidf_score": payload.get("tfidf_score"),
                "tfidf_rank": payload.get("tfidf_rank"),
                "cosine_similarity": payload.get("cosine_similarity"),
                "concept_text": payload.get("concept_text") or dc.exact_quote,
                "page_number": dc.page_number,
                "effective_date": str(dc.effective_date) if dc.effective_date else None,
                "reason_code": dc.reason_code,
                "reason_text": dc.reason_text,
            })

        return {
            "chart_id": chart_id,
            "icd_retrievals": retrievals,
            "total": len(retrievals),
        }

    async def get_verified_icds(self, chart_id: int) -> dict:
        """Get verified ICDs with MEAT (Monitor, Evaluate, Assess, Treat) evidence."""
        stmt = (
            select(DiagnosisCandidate)
            .where(
                DiagnosisCandidate.chart_id == chart_id,
                DiagnosisCandidate.lifecycle_state == "verified",
            )
            .order_by(
                DiagnosisCandidate.icd10_code.asc().nullslast(),
                DiagnosisCandidate.page_number.asc().nullslast(),
            )
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        verified = []
        for dc in rows:
            payload = dc.payload or {}
            meat_evidence = payload.get("meat_evidence", {})
            verified.append({
                "candidate_id": dc.id,
                "candidate_key": dc.candidate_key,
                "icd10_code": dc.icd10_code,
                "hcc_code": dc.hcc_code,
                "confidence": dc.confidence,
                "page_number": dc.page_number,
                "exact_quote": dc.exact_quote,
                "effective_date": str(dc.effective_date) if dc.effective_date else None,
                "provider_name": dc.provider_name,
                "review_status": dc.review_status,
                "meat_evidence": {
                    "monitored": meat_evidence.get("monitored", False),
                    "evaluated": meat_evidence.get("evaluated", False),
                    "assessed": meat_evidence.get("assessed", False),
                    "treated": meat_evidence.get("treated", False),
                    "meat_score": meat_evidence.get("meat_score", 0),
                    "details": meat_evidence.get("details", []),
                },
                "source_type": dc.source_type,
                "reason_code": dc.reason_code,
                "reason_text": dc.reason_text,
            })

        return {
            "chart_id": chart_id,
            "verified_icds": verified,
            "total": len(verified),
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
