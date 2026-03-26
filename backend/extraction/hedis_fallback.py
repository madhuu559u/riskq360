"""Deterministic HEDIS fallback extraction from page text.

Used when LLM extraction is unavailable or sparse. Produces evidence-grounded
records with exact quotes and page numbers for downstream HEDIS evaluation.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Tuple


_PAGE_HEADER_RE = re.compile(r"--- PAGE\s+(\d+)[^\n]*---", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}/\d{1,2}/(?:19|20)\d{2})\b")
_A1C_RE = re.compile(r"\b(?:a1c|hba1c|hemoglobin a1c)[^\d]{0,20}(\d{1,2}(?:\.\d+)?)\s*%?", re.IGNORECASE)
_EGFR_RE = re.compile(r"\begfr[^\d]{0,20}(\d{1,3}(?:\.\d+)?)\b", re.IGNORECASE)
_UACR_RE = re.compile(r"\b(?:uacr|albumin[ -]creatinine)[^\d]{0,24}(\d{1,4}(?:\.\d+)?)\b", re.IGNORECASE)
_DOB_RE = re.compile(r"\b(?:dob|date of birth)[:\s]*([0-9]{1,2}/[0-9]{1,2}/(?:19|20)[0-9]{2}|(?:19|20)[0-9]{2}-[0-9]{1,2}-[0-9]{1,2})\b", re.IGNORECASE)
_SEX_RE = re.compile(r"\b(?:sex|gender)[:\s]*(male|female|m|f)\b", re.IGNORECASE)
_ICD_RE = re.compile(r"\b([A-TV-Z][0-9][0-9](?:\.[0-9A-Z]{1,4})?)\b")
_BP_PAIR_RE = re.compile(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b")
_DOB_CONTEXT_RE = re.compile(r"\b(?:dob|date of birth|born)\b", re.IGNORECASE)
_EVENT_DATE_HINT_RE = re.compile(
    r"\b(?:dos|date of service|service date|encounter|visit|appointment|seen on|performed on|collected on|result date|signed)\b",
    re.IGNORECASE,
)
_ENCOUNTER_HINT_RE = re.compile(
    r"\b(?:encounter|office visit|follow up|follow-up|date of service|assessment\s*&\s*plan|history and physical|seen by|provider|chief complaint)\b",
    re.IGNORECASE,
)
_ENCOUNTER_ID_RE = re.compile(r"\bencounter\s*id\s*[:#]?\s*([A-Za-z0-9\-.]+)\b", re.IGNORECASE)
_DATE_OF_SERVICE_RE = re.compile(
    r"\b(?:date of service|dos|visit date|encounter date)\s*[:#]?\s*([0-9]{1,2}/[0-9]{1,2}/(?:19|20)?[0-9]{2}|(?:19|20)[0-9]{2}-[0-9]{1,2}-[0-9]{1,2})\b",
    re.IGNORECASE,
)
_ENCOUNTER_HEADER_RE = re.compile(
    r"\bencounter\s*-\s*([A-Za-z][A-Za-z /-]{2,40}?)\s+date of service\s*[:#]?\s*([0-9]{1,2}/[0-9]{1,2}/(?:19|20)?[0-9]{2}|(?:19|20)[0-9]{2}-[0-9]{1,2}-[0-9]{1,2})\b",
    re.IGNORECASE,
)
_ENCOUNTER_TYPE_LABELED_RE = re.compile(
    r"\b(?:visit type|encounter type)\s*[:#]?\s*([A-Za-z][A-Za-z /-]{2,40})\b",
    re.IGNORECASE,
)
_PROVIDER_PATTERNS = [
    re.compile(r"\bseen by\s*[:#]?\s*([A-Za-z][A-Za-z .,'-]{2,80})\b", re.IGNORECASE),
    re.compile(r"\bprovider\s*[:#]?\s*([A-Za-z][A-Za-z .,'-]{2,80})\b", re.IGNORECASE),
    re.compile(r"\battending\)?\s*[:#]?\s*([A-Za-z][A-Za-z .,'-]{2,80})\b", re.IGNORECASE),
    re.compile(r"\bsigned electronically by\s*([A-Za-z][A-Za-z .,'-]{2,80})\b", re.IGNORECASE),
]
_FACILITY_PATTERNS = [
    re.compile(r"\bfacility\s*[:#]?\s*([^\n]{3,100})", re.IGNORECASE),
    re.compile(r"\blocation\s*[:#]?\s*([^\n]{3,100})", re.IGNORECASE),
]
_CHIEF_COMPLAINT_RE = re.compile(r"\bchief complaint\s*[:#]?\s*([^\n]{3,200})", re.IGNORECASE)
_FACILITY_NAME_HINT_RE = re.compile(
    r"\b(?:family medicine|medical|clinic|health center|community|practice|hospital)\b",
    re.IGNORECASE,
)


def parse_pages_from_full_text(full_text: str) -> Dict[int, str]:
    """Parse `--- PAGE N ---` blocks into page -> text map."""
    if not full_text:
        return {}

    pages: Dict[int, str] = {}
    matches = list(_PAGE_HEADER_RE.finditer(full_text))
    for idx, m in enumerate(matches):
        page_num = int(m.group(1))
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
        page_text = full_text[start:end].strip()
        pages[page_num] = page_text
    return pages


def _parse_date_token(token: str) -> date | None:
    raw = (token or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _extract_dates_with_context(text: str) -> List[Tuple[date, str]]:
    out: List[Tuple[date, str]] = []
    for m in _DATE_RE.finditer(text or ""):
        parsed = _parse_date_token(m.group(1))
        if parsed is None:
            continue
        out.append((parsed, m.group(1)))
    return out


def _best_event_date(page_text: str, line_text: str | None = None) -> str | None:
    """Pick the best non-DOB event date for a page/line.

    Preference:
    1) dates on event-hint lines
    2) any non-DOB date on the specific line
    3) any non-DOB date on the page
    """
    candidates: List[date] = []

    def consider(text: str, prefer_event_hint: bool) -> None:
        if not text:
            return
        lower = text.lower()
        is_dob_context = bool(_DOB_CONTEXT_RE.search(lower))
        has_event_hint = bool(_EVENT_DATE_HINT_RE.search(lower))
        for dt, _raw in _extract_dates_with_context(text):
            if dt.year < 1990 or dt.year > 2100:
                continue
            if is_dob_context:
                continue
            if prefer_event_hint and not has_event_hint:
                continue
            candidates.append(dt)

    if line_text:
        consider(line_text, prefer_event_hint=True)
        consider(line_text, prefer_event_hint=False)
    consider(page_text, prefer_event_hint=True)
    consider(page_text, prefer_event_hint=False)

    if not candidates:
        return None
    return max(candidates).isoformat()


def _extract_bp_from_line(line: str) -> Tuple[int, int] | None:
    text = (line or "").strip()
    if not text:
        return None
    lower = text.lower()
    if _DOB_CONTEXT_RE.search(lower):
        return None

    has_bp_context = any(
        token in lower for token in ("bp", "blood pressure", "b/p", "mmhg", "systolic", "diastolic")
    )
    compact_line = re.sub(r"\s+", " ", text).strip()

    for m in _BP_PAIR_RE.finditer(text):
        sys_v = int(m.group(1))
        dia_v = int(m.group(2))
        if not (70 <= sys_v <= 260 and 40 <= dia_v <= 160):
            continue
        if sys_v <= dia_v:
            continue
        if not has_bp_context and len(compact_line) > 20:
            # Bare pairs are allowed only for short lines like "138/83".
            continue
        return sys_v, dia_v
    return None


def _mk_assertion(
    *,
    assertion_id: str,
    category: str,
    concept: str,
    quote: str,
    page_number: int,
    effective_date: str | None = None,
    code: str = "",
    code_system: str = "",
) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "assertion_id": assertion_id,
        "category": category,
        "type": category,
        "canonical_concept": concept,
        "concept": concept,
        "status": "active",
        "subject": "patient",
        "text": quote,
        "clean_text": quote,
        "exact_quote": quote[:500],
        "page_number": page_number,
    }
    if effective_date:
        data["effective_date"] = effective_date
    if code:
        data["codes"] = [{"system": code_system or "icd10cm", "code": code, "description": concept}]
        if (code_system or "").lower().startswith("icd"):
            data["icd_codes"] = [{"code": code, "description": concept}]
            data["icd_codes_primary"] = [{"code": code, "description": concept}]
    return data


def extract_fallback_demographics(pages: Dict[int, str]) -> Dict[str, Any]:
    demo: Dict[str, Any] = {}
    for page_num in sorted(pages.keys()):
        text = pages[page_num]
        if "dob" not in demo:
            dm = _DOB_RE.search(text)
            if dm:
                demo["dob"] = dm.group(1)
                demo["dob_source"] = {"page_number": page_num, "exact_quote": dm.group(0)}
        if "gender" not in demo:
            sm = _SEX_RE.search(text)
            if sm:
                g = sm.group(1).lower()
                demo["gender"] = "male" if g in ("male", "m") else "female"
                demo["gender_source"] = {"page_number": page_num, "exact_quote": sm.group(0)}
        if "dob" in demo and "gender" in demo:
            break
    return demo


def _diagnosis_keywords() -> List[Tuple[str, str, str]]:
    return [
        ("type 2 diabetes", "E11.9", "Type 2 diabetes mellitus"),
        ("diabetes mellitus", "E11.9", "Diabetes mellitus"),
        ("hypertension", "I10", "Essential hypertension"),
        ("asthma", "J45.909", "Asthma, unspecified"),
        ("osteoporosis", "M81.0", "Age-related osteoporosis"),
        ("depression", "F32.A", "Depression, unspecified"),
        ("opioid use disorder", "F11.20", "Opioid dependence, uncomplicated"),
    ]


def _clean_field(text: str | None, *, max_len: int = 120) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", str(text)).strip(" \t\r\n-:;,.")
    if not cleaned:
        return None
    return cleaned[:max_len]


def _normalize_encounter_type(text: str | None) -> str | None:
    raw = (text or "").strip().lower()
    if not raw:
        return None
    if "office" in raw:
        return "office"
    if "follow" in raw:
        return "follow_up"
    if "tele" in raw:
        return "telehealth"
    if "wellness" in raw:
        return "wellness"
    if "physical" in raw:
        return "physical"
    if "consult" in raw:
        return "consult"
    if "inpatient" in raw or "hospital" in raw:
        return "inpatient"
    if "emergency" in raw or " er " in f" {raw} ":
        return "emergency"
    return None


def _sanitize_provider(text: str | None) -> str | None:
    value = _clean_field(text, max_len=80)
    if not value:
        return None
    low = value.lower()
    if any(t in low for t in ("comment", "complaint", "summary", "assessment", "history")):
        return None
    tokens = re.findall(r"[A-Za-z]+", value)
    if len(tokens) < 2 or len(tokens) > 8:
        return None
    return value


def _sanitize_facility(text: str | None) -> str | None:
    value = _clean_field(text, max_len=100)
    if not value:
        return None
    low = value.lower()
    if any(
        t in low
        for t in (
            "improving",
            "intervention",
            "reduce health",
            "community-based lifestyle",
            "chief complaint",
            "practice fusion",
            "http",
            "www.",
        )
    ):
        return None
    if "{" in value or "}" in value:
        return None
    if len(value.split()) > 14:
        return None
    return value


def _encounter_quality_score(enc: Dict[str, Any]) -> int:
    score = 0
    for key in ("date", "encounter_id", "provider", "facility", "chief_complaint"):
        if enc.get(key):
            score += 2
    if enc.get("type") and enc.get("type") != "documented":
        score += 1
    if enc.get("evidence"):
        score += 1
    return score


def _next_value_after_label(lines: List[str], idx: int) -> str | None:
    stop_tokens = {
        "seen by",
        "provider",
        "attending",
        "facility",
        "location",
        "date",
        "date of service",
        "dos",
        "encounter",
        "visit type",
        "encounter type",
        "chief complaint",
        "dob",
    }
    for j in range(idx + 1, min(idx + 5, len(lines))):
        candidate = (lines[j] or "").strip()
        if not candidate:
            continue
        low = candidate.lower().strip(" :")
        if low in stop_tokens:
            continue
        return candidate
    return None


def extract_fallback_encounters(pages: Dict[int, str]) -> List[Dict[str, Any]]:
    best_by_key: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}

    for page_num in sorted(pages.keys()):
        page_text = pages[page_num] or ""
        if not _ENCOUNTER_HINT_RE.search(page_text):
            continue

        lines = [ln.strip() for ln in page_text.splitlines() if ln and ln.strip()]
        provider: str | None = None
        facility: str | None = None
        encounter_type: str | None = None
        encounter_id: str | None = None
        chief_complaint: str | None = None
        encounter_date: str | None = None
        evidence: str | None = None

        for ln in lines:
            lower = ln.lower()

            if evidence is None and _ENCOUNTER_HINT_RE.search(lower):
                evidence = ln

            if encounter_type is None or encounter_date is None:
                mh = _ENCOUNTER_HEADER_RE.search(ln)
                if mh:
                    if encounter_type is None:
                        encounter_type = _normalize_encounter_type(mh.group(1))
                    if encounter_date is None:
                        parsed = _parse_date_token(mh.group(2))
                        if parsed and 1990 <= parsed.year <= 2100:
                            encounter_date = parsed.isoformat()

            if encounter_id is None:
                m = _ENCOUNTER_ID_RE.search(ln)
                if m:
                    encounter_id = _clean_field(m.group(1), max_len=80)

            if encounter_date is None:
                m = _DATE_OF_SERVICE_RE.search(ln)
                if m:
                    parsed = _parse_date_token(m.group(1))
                    if parsed:
                        encounter_date = parsed.isoformat()

            if encounter_type is None:
                m = _ENCOUNTER_TYPE_LABELED_RE.search(ln)
                if m:
                    encounter_type = _normalize_encounter_type(m.group(1))

            if provider is None:
                for rx in _PROVIDER_PATTERNS:
                    m = rx.search(ln)
                    if m:
                        provider = _sanitize_provider(m.group(1))
                        if provider:
                            break

            if facility is None:
                for rx in _FACILITY_PATTERNS:
                    m = rx.search(ln)
                    if m:
                        facility = _sanitize_facility(m.group(1))
                        if facility:
                            break

            if chief_complaint is None:
                m = _CHIEF_COMPLAINT_RE.search(ln)
                if m:
                    chief_complaint = _clean_field(m.group(1), max_len=180)

        # Handle label/value pairs split across separate lines.
        for idx, ln in enumerate(lines):
            low = ln.lower().strip(" :")

            if provider is None and low in {"seen by", "provider", "attending"}:
                provider = _sanitize_provider(_next_value_after_label(lines, idx))

            if facility is None and low in {"facility", "location"}:
                facility = _sanitize_facility(_next_value_after_label(lines, idx))

            if chief_complaint is None and low in {"chief complaint", "reason for visit"}:
                chief_complaint = _clean_field(_next_value_after_label(lines, idx), max_len=180)

            if encounter_type is None and low in {"encounter", "visit type", "encounter type"}:
                encounter_type = _normalize_encounter_type(_next_value_after_label(lines, idx))

            if encounter_date is None and low in {"date of service", "dos", "encounter date", "visit date", "date"}:
                next_date = _next_value_after_label(lines, idx)
                parsed = _parse_date_token(next_date or "")
                if parsed and 1990 <= parsed.year <= 2100:
                    encounter_date = parsed.isoformat()

        if encounter_date is None:
            encounter_date = _best_event_date(page_text)

        if encounter_type is None:
            encounter_type = _normalize_encounter_type(evidence)
        if encounter_type is None:
            encounter_type = "office" if ("visit" in (evidence or "").lower()) else "documented"

        if facility is None:
            for ln in lines[:25]:
                if _FACILITY_NAME_HINT_RE.search(ln):
                    facility = _sanitize_facility(ln)
                    if facility:
                        break

        if evidence is None and lines:
            evidence = lines[0]

        if not any([encounter_date, encounter_id, provider, facility, chief_complaint]):
            continue

        candidate = {
            "date": encounter_date,
            "encounter_id": encounter_id,
            "provider": provider,
            "facility": facility,
            "type": encounter_type or "documented",
            "chief_complaint": chief_complaint,
            "page_number": page_num,
            "evidence": _clean_field(evidence, max_len=500),
            "medications": [],
            "lab_orders": [],
            "diagnoses": [],
            "procedures": [],
        }
        dedupe_key = (
            encounter_date or "",
            provider or "",
            facility or "",
            candidate["type"] or "",
        )
        prev = best_by_key.get(dedupe_key)
        if prev is None or _encounter_quality_score(candidate) > _encounter_quality_score(prev):
            best_by_key[dedupe_key] = candidate

    # Collapse repetitive same-day same-type stubs and keep richest evidence.
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for candidate in sorted(best_by_key.values(), key=_encounter_quality_score, reverse=True):
        key = (candidate.get("date") or "", candidate.get("type") or "documented")
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
            continue

        # Preserve multiple encounters on same day only when both have distinct named providers.
        existing_provider = existing.get("provider")
        candidate_provider = candidate.get("provider")
        if existing_provider and candidate_provider and existing_provider != candidate_provider:
            merged[(key[0], f"{key[1]}:{candidate_provider}")] = candidate
            continue

        for field in ("encounter_id", "provider", "facility", "chief_complaint", "evidence", "page_number"):
            if not existing.get(field) and candidate.get(field):
                existing[field] = candidate.get(field)

    encounters = list(merged.values())
    encounters.sort(key=lambda e: ((e.get("date") or ""), int(e.get("page_number") or 0)))
    return encounters


def extract_hedis_fallback_artifacts(
    full_text: str,
    pdf_name: str,
) -> Dict[str, Any]:
    pages = parse_pages_from_full_text(full_text)
    assertions: List[Dict[str, Any]] = []
    hedis_patch: Dict[str, Any] = {
        "blood_pressure_readings": [],
        "lab_results": [],
        "screenings": [],
        "medications_for_measures": [],
        "immunizations": [],
    }
    risk_patch: Dict[str, Any] = {"diagnoses": []}

    seen_keys: set[str] = set()
    idx = 0

    def add_assertion(item: Dict[str, Any]) -> None:
        nonlocal idx
        idx += 1
        item["assertion_id"] = item.get("assertion_id") or f"fallback_{idx}"
        item["pdf"] = pdf_name
        key = f"{item.get('category')}|{item.get('canonical_concept')}|{item.get('page_number')}|{item.get('exact_quote')}"
        if key in seen_keys:
            return
        seen_keys.add(key)
        assertions.append(item)

    for page_num, text in sorted(pages.items()):
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        page_date = _best_event_date(text)

        for ln in lines:
            lower = ln.lower()
            line_date = _best_event_date(text, ln) or page_date

            # ICD-coded diagnosis lines
            for icd in _ICD_RE.findall(ln):
                if re.match(r"^[A-TV-Z]\d{2}", icd):
                    add_assertion(
                        _mk_assertion(
                            assertion_id="",
                            category="diagnosis",
                            concept=f"Diagnosis code {icd}",
                            quote=ln,
                            page_number=page_num,
                            effective_date=line_date,
                            code=icd,
                            code_system="icd10cm",
                        )
                    )
                    risk_patch["diagnoses"].append(
                        {
                            "icd10_code": icd,
                            "description": ln[:180],
                            "negation_status": "active",
                            "supporting_text": ln[:400],
                            "page_number": page_num,
                            "date_of_service": line_date,
                        }
                    )

            # Keyword diagnosis fallback
            for kw, icd, desc in _diagnosis_keywords():
                if kw in lower:
                    add_assertion(
                        _mk_assertion(
                            assertion_id="",
                            category="diagnosis",
                            concept=desc,
                            quote=ln,
                            page_number=page_num,
                            effective_date=line_date,
                            code=icd,
                            code_system="icd10cm",
                        )
                    )
                    risk_patch["diagnoses"].append(
                        {
                            "icd10_code": icd,
                            "description": desc,
                            "negation_status": "active",
                            "supporting_text": ln[:400],
                            "page_number": page_num,
                            "date_of_service": line_date,
                        }
                    )

            # BP
            bp_pair = _extract_bp_from_line(ln)
            if bp_pair:
                sys_v, dia_v = bp_pair
                bp_assertion = _mk_assertion(
                    assertion_id="",
                    category="vital_sign",
                    concept="blood pressure",
                    quote=ln,
                    page_number=page_num,
                    effective_date=line_date,
                )
                bp_assertion["structured"] = {"bp_systolic": sys_v, "bp_diastolic": dia_v}
                add_assertion(
                    bp_assertion
                )
                hedis_patch["blood_pressure_readings"].append(
                    {
                        "systolic": sys_v,
                        "diastolic": dia_v,
                        "date": line_date,
                        "evidence": ln[:400],
                        "page_number": page_num,
                    }
                )

            # Labs
            am = _A1C_RE.search(ln)
            if am:
                val = am.group(1)
                add_assertion(
                    _mk_assertion(
                        assertion_id="",
                        category="lab",
                        concept="HbA1c",
                        quote=ln,
                        page_number=page_num,
                        effective_date=line_date,
                    )
                )
                hedis_patch["lab_results"].append(
                    {
                        "test_name": "HbA1c",
                        "result_value": val,
                        "result_date": line_date,
                        "evidence": ln[:400],
                        "page_number": page_num,
                    }
                )

            em = _EGFR_RE.search(ln)
            if em:
                add_assertion(
                    _mk_assertion(
                        assertion_id="",
                        category="lab",
                        concept="eGFR",
                        quote=ln,
                        page_number=page_num,
                        effective_date=line_date,
                    )
                )
                hedis_patch["lab_results"].append(
                    {
                        "test_name": "eGFR",
                        "result_value": em.group(1),
                        "result_date": line_date,
                        "evidence": ln[:400],
                        "page_number": page_num,
                    }
                )

            um = _UACR_RE.search(ln)
            if um:
                add_assertion(
                    _mk_assertion(
                        assertion_id="",
                        category="lab",
                        concept="UACR",
                        quote=ln,
                        page_number=page_num,
                        effective_date=line_date,
                    )
                )
                hedis_patch["lab_results"].append(
                    {
                        "test_name": "UACR",
                        "result_value": um.group(1),
                        "result_date": line_date,
                        "evidence": ln[:400],
                        "page_number": page_num,
                    }
                )

            # Screenings/procedures
            screening_terms = [
                "mammogram", "colonoscopy", "fit test", "cologuard",
                "pap smear", "cervical cancer screening", "retinal exam",
                "eye exam", "dexa", "bone density",
            ]
            if any(t in lower for t in screening_terms):
                add_assertion(
                    _mk_assertion(
                        assertion_id="",
                        category="procedure",
                        concept="screening/procedure",
                        quote=ln,
                        page_number=page_num,
                        effective_date=line_date,
                    )
                )
                hedis_patch["screenings"].append(
                    {
                        "screening_type": ln[:120],
                        "result": "documented",
                        "date": line_date,
                        "evidence": ln[:400],
                        "page_number": page_num,
                    }
                )

            # Medications
            med_terms = [
                "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin",
                "albuterol", "prednisone", "prednisolone",
                "metformin", "insulin", "semaglutide", "liraglutide",
                "oxycodone", "hydrocodone", "morphine", "fentanyl", "tramadol",
            ]
            if any(t in lower for t in med_terms):
                add_assertion(
                    _mk_assertion(
                        assertion_id="",
                        category="medication",
                        concept="medication",
                        quote=ln,
                        page_number=page_num,
                        effective_date=line_date,
                    )
                )
                hedis_patch["medications_for_measures"].append(
                    {
                        "medication_name": ln[:120],
                        "date": line_date,
                        "evidence": ln[:400],
                        "page_number": page_num,
                    }
                )

            # Immunizations
            if "influenza" in lower or "flu vaccine" in lower or "pneumococcal" in lower:
                vaccine = "Influenza" if ("influenza" in lower or "flu" in lower) else "Pneumococcal"
                add_assertion(
                    _mk_assertion(
                        assertion_id="",
                        category="immunization",
                        concept=vaccine,
                        quote=ln,
                        page_number=page_num,
                        effective_date=line_date,
                    )
                )
                hedis_patch["immunizations"].append(
                    {
                        "vaccine_type": vaccine,
                        "date": line_date,
                        "evidence": ln[:400],
                        "page_number": page_num,
                    }
                )

    return {
        "pages": pages,
        "demographics": extract_fallback_demographics(pages),
        "assertions": assertions,
        "hedis_patch": hedis_patch,
        "risk_patch": risk_patch,
        "encounters_patch": {"encounters": extract_fallback_encounters(pages)},
    }
