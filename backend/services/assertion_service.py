"""Assertion service - clinical data queries (diagnoses, medications, vitals, labs, encounters)."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Encounter
from database.repositories.assertion_repo import AssertionRepository


class AssertionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssertionRepository(session)

    async def get_all(
        self, chart_id: int, category: Optional[str] = None,
        status: Optional[str] = None, limit: int = 1000, offset: int = 0,
    ) -> dict:
        rows = await self.repo.get_by_chart(chart_id, category=category, status=status, limit=limit, offset=offset)
        total = await self.repo.count_by_chart(chart_id)
        return {"assertions": [self._serialize(r) for r in rows], "total": total}

    async def get_diagnoses(self, chart_id: int) -> dict:
        rows = await self.repo.get_diagnoses(chart_id)
        return {"diagnoses": [self._serialize(r) for r in rows], "count": len(rows)}

    async def get_medications(self, chart_id: int) -> dict:
        rows = await self.repo.get_medications(chart_id)
        return {"medications": [self._serialize_med(r) for r in rows], "count": len(rows)}

    async def get_vitals(self, chart_id: int) -> dict:
        rows = await self.repo.get_vitals(chart_id)
        vitals: list[dict] = []
        seen: set[tuple[Any, ...]] = set()
        for r in rows:
            item = self._serialize_vital(r)
            if item is None:
                continue
            key = (
                item.get("page_number"),
                item.get("effective_date"),
                item.get("systolic"),
                item.get("diastolic"),
                (item.get("exact_quote") or item.get("text") or "")[:160],
            )
            if key in seen:
                continue
            seen.add(key)
            vitals.append(item)
        return {"vitals": vitals, "count": len(vitals)}

    async def get_labs(self, chart_id: int) -> dict:
        rows = await self.repo.get_labs(chart_id)
        labs = [self._serialize_lab(r) for r in rows]
        return {"labs": labs, "count": len(labs)}

    async def get_encounters(self, chart_id: int) -> dict:
        """Return encounter timeline with structured details and page-linked evidence."""
        all_assertions = await self.repo.get_by_chart(chart_id, limit=20000)
        assertions_by_date: dict[str, list[Any]] = defaultdict(list)
        for a in all_assertions:
            key = self._normalize_date_key(a.effective_date)
            if key:
                assertions_by_date[key].append(a)

        normalized_encounters = await self._load_normalized_encounters(chart_id)
        if normalized_encounters:
            encounters = [self._serialize_normalized_encounter(enc, assertions_by_date) for enc in normalized_encounters]
            encounters = [e for e in encounters if e]
            encounters.sort(key=lambda e: (e.get("date") or "", e.get("page_number") or 0), reverse=True)
            return {"encounters": encounters, "count": len(encounters)}

        grouped: dict[str, list[Any]] = defaultdict(list)
        undated_by_page: dict[str, list[Any]] = defaultdict(list)
        for a in all_assertions:
            key = self._normalize_date_key(a.effective_date)
            if key:
                grouped[key].append(a)
            else:
                page_key = f"undated_page_{a.page_number or 0}"
                undated_by_page[page_key].append(a)

        encounters: list[dict] = []
        for date_key, rows in grouped.items():
            evidence = self._build_encounter_evidence(rows)
            meds = [self._med_from_assertion(a) for a in rows if (a.category or "").lower() == "medication"]
            diagnoses = [self._dx_from_assertion(a) for a in rows if (a.category or "").lower() in {"diagnosis", "assessment"}]
            procedures = [self._proc_from_assertion(a) for a in rows if (a.category or "").lower() in {"procedure", "screening"}]
            categories = sorted({(a.category or "unknown") for a in rows})
            page_hint = min([ev.get("page_number") for ev in evidence if ev.get("page_number") is not None], default=None)
            encounters.append(
                {
                    "date": date_key,
                    "encounter_id": None,
                    "provider": self._first_non_empty(rows, "structured", "provider"),
                    "facility": self._first_non_empty(rows, "structured", "facility"),
                    "type": self._first_non_empty(rows, "structured", "encounter_type"),
                    "chief_complaint": self._first_non_empty(rows, "structured", "chief_complaint"),
                    "page_number": page_hint,
                    "assertion_count": len(rows),
                    "categories": categories,
                    "evidence": evidence[0]["exact_quote"] if evidence else None,
                    "evidence_items": evidence,
                    "medications": [m for m in meds if m],
                    "diagnoses": [d for d in diagnoses if d],
                    "procedures": [p for p in procedures if p],
                }
            )

        if not encounters and undated_by_page:
            for page_key, rows in sorted(undated_by_page.items()):
                evidence = self._build_encounter_evidence(rows)
                meds = [self._med_from_assertion(a) for a in rows if (a.category or "").lower() == "medication"]
                diagnoses = [self._dx_from_assertion(a) for a in rows if (a.category or "").lower() in {"diagnosis", "assessment"}]
                procedures = [self._proc_from_assertion(a) for a in rows if (a.category or "").lower() in {"procedure", "screening"}]
                page_hint = min([ev.get("page_number") for ev in evidence if ev.get("page_number") is not None], default=None)
                categories = sorted({(a.category or "unknown") for a in rows})
                encounters.append(
                    {
                        "date": "",
                        "encounter_id": page_key,
                        "provider": self._first_non_empty(rows, "structured", "provider"),
                        "facility": self._first_non_empty(rows, "structured", "facility"),
                        "type": "documented",
                        "chief_complaint": None,
                        "page_number": page_hint,
                        "assertion_count": len(rows),
                        "categories": categories,
                        "evidence": evidence[0]["exact_quote"] if evidence else None,
                        "evidence_items": evidence,
                        "medications": [m for m in meds if m],
                        "diagnoses": [d for d in diagnoses if d],
                        "procedures": [p for p in procedures if p],
                    }
                )

        encounters.sort(key=lambda e: (e.get("date") or "", e.get("page_number") or 0), reverse=True)
        return {"encounters": encounters, "count": len(encounters)}

    async def get_hedis_evidence(self, chart_id: int) -> dict:
        rows = await self.repo.get_hedis_evidence(chart_id)
        return {"hedis_evidence": [self._serialize(r) for r in rows], "count": len(rows)}

    async def get_ra_candidates(self, chart_id: int) -> dict:
        rows = await self.repo.get_ra_candidates(chart_id)
        return {"ra_candidates": [self._serialize(r) for r in rows], "count": len(rows)}

    async def get_category_stats(self, chart_id: int) -> dict:
        counts = await self.repo.count_by_category(chart_id)
        return {"categories": {cat: cnt for cat, cnt in counts}}

    async def get_pending_reviews(self, chart_id: Optional[int] = None) -> dict:
        rows = await self.repo.get_pending_review(chart_id)
        return {"pending": [self._serialize(r) for r in rows], "count": len(rows)}

    async def update_review(
        self, assertion_id: int, review_status: str,
        reviewed_by: str, review_notes: Optional[str] = None,
    ) -> Optional[dict]:
        row = await self.repo.update_review(assertion_id, review_status, reviewed_by, review_notes)
        return self._serialize(row) if row else None

    async def _load_normalized_encounters(self, chart_id: int) -> list[Encounter]:
        stmt = (
            select(Encounter)
            .where(Encounter.chart_id == chart_id)
            .order_by(Encounter.encounter_date, Encounter.id)
            .options(
                selectinload(Encounter.medications),
                selectinload(Encounter.procedures),
                selectinload(Encounter.lab_orders),
                selectinload(Encounter.diagnoses_list),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _serialize_normalized_encounter(self, enc: Encounter, assertions_by_date: dict[str, list[Any]]) -> dict:
        date_key = self._normalize_date_key(enc.encounter_date)
        linked_assertions = assertions_by_date.get(date_key, []) if date_key else []
        evidence = self._build_encounter_evidence(linked_assertions)
        page_hint = min([ev.get("page_number") for ev in evidence if ev.get("page_number") is not None], default=None)

        return {
            "date": date_key or enc.encounter_date,
            "encounter_id": enc.encounter_ext_id,
            "provider": enc.provider,
            "facility": enc.facility,
            "type": enc.encounter_type,
            "chief_complaint": enc.chief_complaint,
            "page_number": page_hint,
            "assertion_count": len(linked_assertions),
            "categories": sorted({(a.category or "unknown") for a in linked_assertions}),
            "evidence": evidence[0]["exact_quote"] if evidence else None,
            "evidence_items": evidence,
            "medications": [
                {
                    "name": m.name,
                    "dose_form": m.dose_form,
                    "instructions": m.instructions,
                    "indication": m.indication,
                    "action": m.action,
                    "page_number": page_hint,
                    "evidence": evidence[0]["exact_quote"] if evidence else None,
                }
                for m in (enc.medications or [])
            ],
            "lab_orders": [
                {
                    "test_name": l.test_name,
                    "status": l.status,
                    "result": l.result,
                    "date_ordered": l.date_ordered,
                    "date_resulted": l.date_resulted,
                }
                for l in (enc.lab_orders or [])
            ],
            "diagnoses": [
                {
                    "icd10_code": d.icd10_code,
                    "description": d.description,
                    "negation_status": "active",
                    "supporting_text": evidence[0]["exact_quote"] if evidence else None,
                }
                for d in (enc.diagnoses_list or [])
            ],
            "procedures": [
                {
                    "name": p.name,
                    "cpt_code": p.cpt_code,
                    "status": p.status,
                    "result": p.result,
                }
                for p in (enc.procedures or [])
            ],
        }

    def _build_encounter_evidence(self, rows: list[Any]) -> list[dict]:
        evidence: list[dict] = []
        seen: set[tuple[Any, ...]] = set()
        for a in rows:
            quote = (a.exact_quote or a.text or "").strip()
            if not quote:
                continue
            key = (a.page_number, quote[:180], a.category)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "category": a.category,
                    "concept": a.canonical_concept or a.concept,
                    "page_number": a.page_number,
                    "exact_quote": quote[:600],
                }
            )
            if len(evidence) >= 8:
                break
        return evidence

    def _med_from_assertion(self, a: Any) -> dict:
        normalized = a.medication_normalized or {}
        return {
            "name": normalized.get("name") or a.canonical_concept or a.concept,
            "dose_form": normalized.get("dose_form"),
            "instructions": normalized.get("sig") or a.text,
            "indication": normalized.get("indication"),
            "action": normalized.get("action"),
            "page_number": a.page_number,
            "evidence": a.exact_quote or a.text,
        }

    def _dx_from_assertion(self, a: Any) -> dict:
        code = ""
        icds = a.icd_codes_primary or a.icd_codes or []
        if isinstance(icds, list) and icds:
            first = icds[0] if isinstance(icds[0], dict) else {}
            code = str(first.get("code") or "")
        return {
            "icd10_code": code,
            "description": a.canonical_concept or a.concept or a.text,
            "negation_status": a.status or "active",
            "supporting_text": a.exact_quote or a.text,
            "page_number": a.page_number,
        }

    def _proc_from_assertion(self, a: Any) -> dict:
        cpt = ""
        codes = a.codes or []
        if isinstance(codes, list):
            for c in codes:
                if not isinstance(c, dict):
                    continue
                system = str(c.get("system") or "").lower()
                if system in {"cpt", "cpt2", "hcpcs"}:
                    cpt = str(c.get("code") or "")
                    break
        return {
            "name": a.canonical_concept or a.concept or a.text,
            "cpt_code": cpt,
            "status": "documented",
            "result": None,
            "page_number": a.page_number,
            "evidence": a.exact_quote or a.text,
        }

    def _first_non_empty(self, rows: list[Any], field: str, key: str) -> Optional[str]:
        for a in rows:
            blob = getattr(a, field, None)
            if isinstance(blob, dict):
                val = blob.get(key)
                if val:
                    return str(val)
        return None

    def _normalize_date_key(self, raw: Any) -> Optional[str]:
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text).date().isoformat()
        except Exception:
            return text

    def _is_plausible_bp(self, systolic: Any, diastolic: Any) -> bool:
        try:
            s = float(systolic)
            d = float(diastolic)
        except Exception:
            return False
        if not (70 <= s <= 260 and 40 <= d <= 160):
            return False
        if s <= d:
            return False
        return True

    def _extract_bp_from_text(self, text: str) -> tuple[Optional[int], Optional[int]]:
        if not text:
            return None, None
        m = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", text)
        if not m:
            return None, None
        s = int(m.group(1))
        d = int(m.group(2))
        if not self._is_plausible_bp(s, d):
            return None, None
        return s, d

    def _serialize(self, a: Any) -> dict:
        return {
            "id": a.id,
            "chart_id": a.chart_id,
            "assertion_id": a.assertion_id,
            "category": a.category,
            "concept": a.concept,
            "canonical_concept": a.canonical_concept,
            "text": a.text,
            "clean_text": a.clean_text,
            "status": a.status,
            "subject": a.subject,
            "evidence_rank": a.evidence_rank,
            "page_number": a.page_number,
            "exact_quote": a.exact_quote,
            "char_start": a.char_start,
            "char_end": a.char_end,
            "icd_codes": a.icd_codes,
            "icd_codes_primary": a.icd_codes_primary,
            "codes": a.codes,
            "effective_date": a.effective_date,
            "structured": a.structured,
            "medication_normalized": a.medication_normalized,
            "is_hcc_candidate": a.is_hcc_candidate,
            "is_payable_ra_candidate": a.is_payable_ra_candidate,
            "is_hedis_evidence": a.is_hedis_evidence,
            "review_status": a.review_status,
            "condition_group_id_v3": a.condition_group_id_v3,
        }

    def _serialize_med(self, a: Any) -> dict:
        base = self._serialize(a)
        base["medication_normalized"] = a.medication_normalized
        return base

    def _serialize_lab(self, a: Any) -> dict:
        base = self._serialize(a)
        structured = a.structured or {}
        quote = str(a.exact_quote or a.text or "")
        concept = str(a.canonical_concept or a.concept or "").strip()

        test_name = str(structured.get("test_name") or concept or "Lab").strip()
        if not test_name or test_name.lower() in {"lab", "lab_result", "screening/lab"}:
            m_name = re.search(r"\b([A-Za-z][A-Za-z0-9()/%\- ]{1,40})\s*[:=]?\s*[<>]?\d", quote)
            if m_name:
                test_name = m_name.group(1).strip()
        if not test_name:
            test_name = "Lab"

        value = structured.get("value") or structured.get("result_value")
        unit = structured.get("unit")
        if value is None:
            ql = quote.lower()
            tl = test_name.lower()
            m_val = None
            if "a1c" in tl:
                m_val = re.search(r"\b(?:a1c|hba1c|hemoglobin a1c)[^\d]{0,16}([<>]?\d{1,2}(?:\.\d+)?)\s*%?", ql, re.IGNORECASE)
                if m_val:
                    value = m_val.group(1)
                    unit = unit or "%"
            elif "egfr" in tl:
                m_val = re.search(r"\begfr[^\d]{0,16}([<>]?\d{1,3}(?:\.\d+)?)\s*([A-Za-z%/]+)?", quote, re.IGNORECASE)
                if m_val:
                    value = m_val.group(1)
                    unit = unit or m_val.group(2)
            elif "uacr" in tl:
                m_val = re.search(
                    r"\b(?:uacr|albumin[ -]?creatinine)[^\d]{0,16}([<>]?\d{1,4}(?:\.\d+)?)\s*([A-Za-z%/]+)?",
                    quote,
                    re.IGNORECASE,
                )
                if m_val:
                    value = m_val.group(1)
                    unit = unit or m_val.group(2)
            if value is None:
                m_val = re.search(r"\b([<>]?\d+(?:\.\d+)?)\s*([A-Za-z%/]+)?\b", quote)
                if m_val:
                    value = m_val.group(1)
                    unit = unit or m_val.group(2)

        abnormal_flag = structured.get("abnormal_flag")
        ql = quote.lower()
        if not abnormal_flag:
            if "abnormal" in ql or "high" in ql or "elevated" in ql:
                abnormal_flag = "high"
            elif "low" in ql or "decreased" in ql:
                abnormal_flag = "low"

        base["test_name"] = test_name
        base["value"] = value
        base["unit"] = unit
        base["result_value"] = value
        base["result_date"] = a.effective_date
        base["abnormal_flag"] = abnormal_flag
        base["reference_range"] = structured.get("reference_range")
        return base

    def _serialize_vital(self, a: Any) -> Optional[dict]:
        base = self._serialize(a)
        structured = a.structured or {}

        systolic = structured.get("bp_systolic")
        diastolic = structured.get("bp_diastolic")
        if self._is_plausible_bp(systolic, diastolic):
            systolic = int(float(systolic))
            diastolic = int(float(diastolic))
        else:
            systolic, diastolic = self._extract_bp_from_text(str(a.exact_quote or a.text or ""))

        base["systolic"] = systolic
        base["diastolic"] = diastolic
        base["bp_systolic"] = systolic
        base["bp_diastolic"] = diastolic
        base["blood_pressure"] = f"{systolic}/{diastolic}" if systolic and diastolic else None
        base["weight"] = structured.get("weight") or structured.get("weight_lbs")
        base["height"] = structured.get("height") or structured.get("height_inches")
        base["bmi"] = structured.get("bmi")
        base["pulse"] = structured.get("pulse")
        base["temperature"] = structured.get("temperature") or structured.get("temp_f") or structured.get("temp_c")
        base["oxygen_saturation"] = structured.get("oxygen_saturation") or structured.get("spo2")

        has_signal = any(
            base.get(k) is not None
            for k in (
                "systolic",
                "diastolic",
                "weight",
                "height",
                "bmi",
                "pulse",
                "temperature",
                "oxygen_saturation",
            )
        )
        if not has_signal:
            return None
        return base
