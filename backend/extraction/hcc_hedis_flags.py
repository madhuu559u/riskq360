"""Compute HCC candidate and HEDIS evidence flags for assertions."""

from __future__ import annotations

import re
from typing import Any, Dict, List

_HCC_BLOCK_Z = re.compile(r"\bZ(00|01|02|11|13|23|68|71|91)\b", re.I)
_PAYABLE_HCC_EXCLUDE_ICD_PREFIX = re.compile(r"^Z", re.I)
_PAYABLE_HCC_EXCLUDE_CODES = {"Z71.2"}


def compute_hcc_hedis_flags(a: Dict[str, Any]) -> None:
    cat = (a.get("category") or "").lower()
    st = (a.get("status") or "").lower()
    er = int(a.get("evidence_rank") or 3)
    is_admin = cat == "administrative_code"
    hcc = (cat in {"diagnosis", "assessment"} and st == "active" and er == 1 and not is_admin)
    if hcc and any(_HCC_BLOCK_Z.search(c.get("code", "").upper()) for c in (a.get("icd_codes") or [])):
        hcc = False
    a["is_hcc_candidate"] = bool(hcc)
    hedis_cat = cat in {"vital_sign", "lab_result", "screening", "medication", "procedure", "immunization", "functional_status"}
    dc = (a.get("inferred_date_confidence") or "low")
    src = (a.get("inferred_date_source") or "none")
    doc_match = bool(a.get("inferred_date_doc_match"))
    hedis = hedis_cat and (dc in {"medium", "high"} or src == "anchor" or doc_match)
    if is_admin:
        hedis = False
    a["is_hedis_evidence"] = bool(hedis)
    eff = bool(a.get("effective_date"))
    a["is_hedis_evidence_effective"] = bool(hedis_cat and eff and not is_admin)


def compute_payable_hcc_candidate(a: Dict[str, Any]) -> None:
    a["is_payable_hcc_candidate"] = False
    a["payable_hcc_exclusion_reason"] = None
    a["is_payable_ra_candidate"] = False
    a["ra_candidate_exclusion_reason"] = None

    cat = (a.get("category") or "").lower()
    st = (a.get("status") or "").lower()
    try:
        er = int(a.get("evidence_rank") or 3)
    except Exception:
        er = 3

    if cat not in {"diagnosis", "assessment"}:
        a["payable_hcc_exclusion_reason"] = "not_dx_or_assessment"
        a["ra_candidate_exclusion_reason"] = "not_dx_or_assessment"
        return
    if st != "active":
        a["payable_hcc_exclusion_reason"] = "not_active"
        a["ra_candidate_exclusion_reason"] = "not_active"
        return
    if er != 1:
        a["payable_hcc_exclusion_reason"] = "weak_evidence_rank"
        a["ra_candidate_exclusion_reason"] = "weak_evidence_rank"
        return

    icds = [c.get("code", "").upper() for c in (a.get("icd_codes") or []) if c.get("code")]
    if not icds:
        a["payable_hcc_exclusion_reason"] = "no_icd10cm_code"
        a["ra_candidate_exclusion_reason"] = "no_icd10cm_code"
        return

    kept: List[str] = []
    for c in icds:
        if c in _PAYABLE_HCC_EXCLUDE_CODES:
            continue
        if _PAYABLE_HCC_EXCLUDE_ICD_PREFIX.match(c):
            continue
        kept.append(c)

    if not kept:
        a["payable_hcc_exclusion_reason"] = "only_excluded_icd10cm_codes"
        a["ra_candidate_exclusion_reason"] = "only_excluded_icd10cm_codes"
        return

    a["is_payable_hcc_candidate"] = True
    a["payable_hcc_exclusion_reason"] = None
    a["is_payable_ra_candidate"] = True
    a["ra_candidate_exclusion_reason"] = None
