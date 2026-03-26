"""Main validate-and-enrich pipeline for raw LLM assertions.

Wires together quote validation, code classification, date inference,
enrichment, condition grouping, and HCC/HEDIS flag computation.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .quote_validator import find_quote_offset, normalize_ws
from .date_engine import (
    DateSpan, DateAnchor,
    extract_dates_from_page, extract_date_anchors,
    page_best_dos, fill_page_best_dos_nearest, best_guess_doc_dos,
    attach_dates_to_assertion, compute_effective_date, is_likely_dob,
)
from .code_classifier import (
    normalize_codes, extract_icd_from_quote, enrich_codes_near_quote,
    select_primary_icd_codes, get_grouping_icd_list,
)
from .vital_extractor import extract_structured_vitals_from_page
from .dx_harvester import harvest_coded_diagnoses_from_page, harvest_all_icd_codes_from_page
from .assertion_enricher import (
    normalize_assertion, clean_statement_text,
    split_mixed_polarity_physical_exam, force_admin_quarantine,
    is_administrative, apply_status_corrections, normalize_allergies,
    normalize_tobacco, sanitize_diagnosis_category, enforce_evidence_rank,
    attach_medication_normalization, normalize_concept, attach_canonical_concept,
    sanitize_dx_concept, is_garbage_concept_str,
)
from .condition_grouper import (
    assign_condition_groups, assign_condition_groups_v2,
    assign_condition_groups_v3, apply_contradiction_flags,
)
from .hcc_hedis_flags import compute_hcc_hedis_flags, compute_payable_hcc_candidate


# ── Drop tracking ──────────────────────────────────────────────────

_drops: List[Dict[str, Any]] = []


def get_drops() -> List[Dict[str, Any]]:
    return list(_drops)


def clear_drops() -> None:
    _drops.clear()


def record_drop(a: Dict[str, Any], reason: str) -> None:
    _drops.append({
        "reason": reason,
        "page_number": a.get("page_number"),
        "category": a.get("category"),
        "concept": a.get("concept"),
        "status": a.get("status"),
        "subject": a.get("subject"),
        "exact_quote": a.get("exact_quote"),
    })


# ── Deduplication ──────────────────────────────────────────────────

def dedupe_assertions(assertions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for a in assertions:
        key = (
            a.get("page_number"),
            normalize_ws(a.get("exact_quote", "")),
            normalize_ws(a.get("concept", "")),
            a.get("status"),
            a.get("subject"),
            a.get("category"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


# ── Merge chunk results ───────────────────────────────────────────

def merge_results(chunk_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for r in chunk_results:
        items = r.get("assertions", [])
        if isinstance(items, list):
            merged.extend(items)
    return merged


# ── Deterministic assertion harvesting ─────────────────────────────

def harvest_deterministic_assertions(
    pages_by_num: Dict[int, str],
) -> List[Dict[str, Any]]:
    """Run deterministic harvesters (ICD tags, inline codes, vitals) on every page."""
    deterministic: List[Dict[str, Any]] = []
    for pn, txt in pages_by_num.items():
        deterministic.extend(harvest_coded_diagnoses_from_page(pn, txt))
        deterministic.extend(harvest_all_icd_codes_from_page(pn, txt))
        from .vital_extractor import generate_vital_assertions_from_page
        deterministic.extend(generate_vital_assertions_from_page(pn, txt))
    return deterministic


# ── Date context preparation ───────────────────────────────────────

def prepare_date_context(
    pages_by_num: Dict[int, str],
) -> Tuple[
    Dict[int, List[DateSpan]],
    Dict[int, List[DateAnchor]],
    Dict[int, Optional[str]],
    Dict[int, Optional[str]],
    Optional[str],
]:
    """Extract dates and anchors from all pages. Returns (page_dates, page_anchors,
    page_best_dos_map, page_best_dos_map_nn, doc_dos)."""
    page_dates = {pn: extract_dates_from_page(txt) for pn, txt in pages_by_num.items()}
    page_anchors = {pn: extract_date_anchors(txt) for pn, txt in pages_by_num.items()}
    page_best_dos_map = {pn: page_best_dos(spans) for pn, spans in page_dates.items()}
    page_best_dos_map_nn = fill_page_best_dos_nearest(page_best_dos_map, page_count=len(pages_by_num))
    doc_dos = best_guess_doc_dos(page_dates)
    return page_dates, page_anchors, page_best_dos_map, page_best_dos_map_nn, doc_dos


# ── Vitals summary ─────────────────────────────────────────────────

def build_vitals_summary(pages_by_num: Dict[int, str]) -> Dict[str, Any]:
    vitals_summary: Dict[str, Any] = {}
    for pn, txt in pages_by_num.items():
        pv = extract_structured_vitals_from_page(txt) or {}
        for k, v in pv.items():
            if k not in vitals_summary:
                vitals_summary[k] = v
    return vitals_summary


# ── Main validate-and-enrich pipeline ──────────────────────────────

def validate_and_enrich(
    assertions: List[Dict[str, Any]],
    pages_by_num: Dict[int, str],
    page_dates: Dict[int, List[DateSpan]],
    page_anchors: Dict[int, List[DateAnchor]],
    page_best_dos_map: Dict[int, Optional[str]],
    page_best_dos_map_nn: Dict[int, Optional[str]],
    quote_min_similarity: float,
    doc_dos: Optional[str],
) -> List[Dict[str, Any]]:
    """Validate, enrich, and post-process raw assertions.

    Steps per assertion:
    1) Normalize defaults
    2) Validate page_number
    3) Split mixed-polarity PE findings
    4) Quote matching (strict → ws_normalized → approximate → token_rescue)
    5) Code classification + ICD extraction
    6) Admin quarantine + status corrections
    7) Date attachment + effective_date
    8) Text cleaning + concept normalization
    9) HCC/HEDIS flag computation
    10) Condition grouping + contradiction detection
    """
    # Collect DOB dates for effective_date avoidance
    dob_dates: List[str] = []
    for spans in page_dates.values():
        for span in spans:
            if span.kind == "dob" and is_likely_dob(span.iso):
                dob_dates.append(span.iso)

    audited: List[Dict[str, Any]] = []
    for raw in assertions:
        raw = normalize_assertion(raw)
        pn = raw.get("page_number")
        if not isinstance(pn, int) or pn not in pages_by_num:
            record_drop(raw, "invalid page_number")
            continue
        page_text = pages_by_num[pn]

        candidates = split_mixed_polarity_physical_exam(raw, page_text)
        for a in candidates:
            a = normalize_assertion(a)
            m = find_quote_offset(page_text, a.get("exact_quote", "") or "", min_similarity=quote_min_similarity)
            if m is None:
                record_drop(a, "exact_quote not found (strict/ws/approx failed)")
                continue

            start, end, verbatim, repaired, sim, method = m
            a["char_start"] = start
            a["char_end"] = end
            a["exact_quote"] = verbatim
            a["quote_repaired"] = bool(repaired)
            a["quote_similarity"] = float(sim) if sim is not None else None
            a["quote_match_method"] = method
            a["structured_page_vitals"] = extract_structured_vitals_from_page(page_text)

            # Code classification
            normalize_codes(a)
            extract_icd_from_quote(a)
            enrich_codes_near_quote(a, page_text)

            # Admin quarantine + category corrections
            force_admin_quarantine(a)
            if is_administrative(a.get("concept", ""), a.get("text", ""), a.get("exact_quote", "")):
                a["category"] = "administrative_code"
            apply_status_corrections(a)
            normalize_allergies(a)
            normalize_tobacco(a)
            sanitize_diagnosis_category(a)
            enforce_evidence_rank(a)

            # Date attachment
            attach_dates_to_assertion(
                a, page_text, page_dates.get(pn, []), page_anchors.get(pn, []),
                doc_dos=doc_dos, page_dos_val=page_best_dos_map.get(pn),
            )
            a["page_best_dos_nn"] = page_best_dos_map_nn.get(pn)
            compute_effective_date(a, dob_dates)

            # Text cleaning
            a["clean_text"] = clean_statement_text(a.get("text", "")) if a.get("text") else None
            if a.get("clean_text") is not None and len(str(a.get("clean_text")).strip()) < 3:
                ev = a.get("exact_quote") or ""
                a["clean_text"] = clean_statement_text(ev) if ev else a.get("clean_text")

            # Normalization
            attach_medication_normalization(a)
            normalize_concept(a)
            attach_canonical_concept(a)
            sanitize_dx_concept(a)
            select_primary_icd_codes(a)
            a["group_icd_codes"] = get_grouping_icd_list(a)

            # HCC/HEDIS flags
            compute_hcc_hedis_flags(a)
            compute_payable_hcc_candidate(a)

            audited.append(a)

    # Assign assertion IDs
    for i, a in enumerate(audited, start=1):
        pn = a.get("page_number", 0)
        a["assertion_id"] = f"p{pn:03d}_{i:06d}"

    # Group-level processing
    apply_contradiction_flags(audited)
    assign_condition_groups_v3(audited)
    assign_condition_groups(audited)
    assign_condition_groups_v2(audited)

    return audited


# ── Summary builder ────────────────────────────────────────────────

def build_summary(
    audited: List[Dict[str, Any]],
    vitals_summary: Dict[str, Any],
    doc_dos: Optional[str],
    all_page_dates: Dict[int, List[DateSpan]],
    page_anchors: Dict[int, List[DateAnchor]],
    page_best_dos_map: Dict[int, Optional[str]],
    page_best_dos_map_nn: Dict[int, Optional[str]],
    quote_min_similarity: float,
) -> Dict[str, Any]:
    by_cat: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    diagnoses: set = set()
    meds: set = set()
    icd: set = set()
    cpt2: set = set()
    hcpcs: set = set()
    dates_all = sorted({s.iso for spans in all_page_dates.values() for s in spans})
    dob_dates = sorted({
        s.iso for spans in all_page_dates.values() for s in spans
        if s.kind == "dob" and is_likely_dob(s.iso)
    })
    anchors_all: List[Dict[str, Any]] = []
    for pn, anchors in page_anchors.items():
        for a in anchors:
            anchors_all.append({"page_number": pn, "kind": a.kind, "start": a.start, "end": a.end, "text": a.text})

    hcc_count = 0
    hedis_count = 0
    quote_repairs = 0
    for a in audited:
        cat = a.get("category", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1
        st = a.get("status", "unknown")
        by_status[st] = by_status.get(st, 0) + 1
        if cat in {"diagnosis", "assessment"} and st == "active":
            diagnoses.add(a.get("concept", ""))
        if cat == "medication" and st == "active":
            meds.add(a.get("concept", ""))
        for c in a.get("icd_codes", []) or []:
            if c.get("code"):
                icd.add(c["code"])
        for c in a.get("cpt2_codes", []) or []:
            if c.get("code"):
                cpt2.add(c["code"])
        for c in a.get("hcpcs_codes", []) or []:
            if c.get("code"):
                hcpcs.add(c["code"])
        if a.get("is_hcc_candidate"):
            hcc_count += 1
        if a.get("is_hedis_evidence"):
            hedis_count += 1
        if a.get("quote_repaired"):
            quote_repairs += 1

    page_dos_list = [
        {"page_number": pn, "page_best_dos": dos}
        for pn, dos in sorted(page_best_dos_map.items()) if dos
    ]
    page_dos_nn_list = [
        {"page_number": pn, "page_best_dos_nn": dos}
        for pn, dos in sorted(page_best_dos_map_nn.items()) if dos
    ]

    return {
        "schema_version": "v28",
        "thresholds": {"quote_min_similarity": quote_min_similarity},
        "counts_by_category": dict(sorted(by_cat.items(), key=lambda x: (-x[1], x[0]))),
        "counts_by_status": dict(sorted(by_status.items(), key=lambda x: (-x[1], x[0]))),
        "unique_diagnoses": sorted(diagnoses),
        "unique_medications": sorted(meds),
        "icd9cm_codes_found": sorted({
            c.get("code", "").upper()
            for a in audited for c in (a.get("icd9_codes") or []) if c.get("code")
        }),
        "icd10cm_codes_found": sorted(icd),
        "cpt2_codes_found": sorted(cpt2),
        "hcpcs_codes_found": sorted(hcpcs),
        "structured_vitals_summary": vitals_summary,
        "best_guess_date_of_service": doc_dos,
        "page_best_dos": page_dos_list,
        "page_best_dos_nn": page_dos_nn_list,
        "dates_found": dates_all,
        "dob_dates_found": dob_dates,
        "page_date_anchors": anchors_all,
        "hcc_candidate_assertions": hcc_count,
        "hedis_evidence_assertions": hedis_count,
        "hedis_evidence_assertions_effective_date": sum(1 for a in audited if a.get("is_hedis_evidence_effective")),
        "payable_hcc_candidate_assertions": sum(1 for a in audited if a.get("is_payable_hcc_candidate")),
        "payable_ra_candidate_assertions": sum(1 for a in audited if a.get("is_payable_ra_candidate")),
        "effective_date_used_nn": sum(1 for a in audited if a.get("effective_date_used_nn")),
        "condition_groups": len({a.get("condition_group_id") for a in audited if a.get("condition_group_id")}),
        "condition_groups_v2": len({a.get("condition_group_id_v2") for a in audited if a.get("condition_group_id_v2")}),
        "condition_groups_v3": len({a.get("condition_group_id_v3") for a in audited if a.get("condition_group_id_v3")}),
        "diagnosis_groups_v3": len({
            a.get("condition_group_id_v3") for a in audited
            if a.get("condition_group_id_v3") and a.get("category") in {"diagnosis", "assessment"}
        }),
        "unique_canonical_diagnoses": sorted({
            a.get("canonical_concept") for a in audited
            if a.get("canonical_concept") and a.get("category") in {"diagnosis", "assessment"} and a.get("status") == "active"
        }),
        "quote_repairs": quote_repairs,
        "quote_token_rescues": sum(1 for a in audited if a.get("quote_match_method") == "token_rescue"),
        "primary_icd_assigned": sum(1 for a in audited if a.get("icd_codes_primary") and len(a.get("icd_codes_primary")) >= 1),
        "polluted_concepts": sum(
            1 for a in audited
            if a.get("category") in {"diagnosis", "assessment"}
            and a.get("concept")
            and (re.match(r"^[A-TV-Z][0-9]{2}(?:\.[0-9A-TV-Z]{1,4})?$", a.get("concept"), re.I)
                 or re.match(r"^\d{3}(?:\.\d{1,2})?$", a.get("concept")))
        ),
        "garbage_concepts": sum(
            1 for a in audited
            if a.get("category") in {"diagnosis", "assessment"} and is_garbage_concept_str(a.get("concept"))
        ),
    }
