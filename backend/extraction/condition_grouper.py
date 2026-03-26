"""Condition grouping and contradiction detection for clinical assertions."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .quote_validator import normalize_ws
from .code_classifier import _ICD_TAG_RE


def condition_group_key(a: Dict[str, Any]) -> str:
    concept = normalize_ws(a.get("concept", "")).lower()
    icds = sorted({(c.get("code") or "").upper() for c in (a.get("icd_codes") or []) if c.get("code")})
    icd_part = ",".join(icds) if icds else ""
    return f"{concept}|{icd_part}"


def condition_group_key_v2(a: Dict[str, Any]) -> str:
    icds = sorted({(c.get("code") or "").upper() for c in (a.get("icd_codes") or []) if c.get("code")})
    if icds:
        return "ICD:" + ",".join(icds)
    concept = normalize_ws(a.get("concept", "")).lower()
    return "C:" + concept


def condition_group_key_v3(a: Dict[str, Any]) -> str:
    icds = sorted({(c.get("code") or "").upper() for c in (a.get("icd_codes") or []) if c.get("code")})
    if icds:
        return "ICD:" + ",".join(icds)
    can = normalize_ws(a.get("canonical_concept") or "").lower()
    if can:
        return "CAN:" + can
    return "CON:" + normalize_ws(a.get("concept", "")).lower()


def _group_score(x: Dict[str, Any], pref_cat: Dict[str, int], pref_status: Dict[str, int]) -> Tuple[int, int, int]:
    try:
        er = int(x.get("evidence_rank", 3))
    except Exception:
        er = 3
    er_score = 4 - er
    cat_score = pref_cat.get((x.get("category") or "").lower(), 0)
    st_score = pref_status.get((x.get("status") or "").lower(), 0)
    return (er_score, cat_score, st_score)


def assign_condition_groups(assertions: List[Dict[str, Any]]) -> None:
    pref_cat = {"diagnosis": 3, "assessment": 2}
    pref_status = {"active": 3, "historical": 2, "resolved": 1, "uncertain": 0, "negated": -1, "family_history": 0}
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for a in assertions:
        k = condition_group_key(a)
        a["condition_group_key"] = k
        groups.setdefault(k, []).append(a)
    keys_sorted = sorted(groups.keys())
    key_to_id = {k: f"c{idx + 1:04d}" for idx, k in enumerate(keys_sorted)}
    for k, items in groups.items():
        gid = key_to_id[k]
        for a in items:
            a["condition_group_id"] = gid
            a["is_condition_best_evidence"] = False
        winner = max(items, key=lambda x: _group_score(x, pref_cat, pref_status))
        winner["is_condition_best_evidence"] = True


def assign_condition_groups_v2(assertions: List[Dict[str, Any]]) -> None:
    pref_cat = {"diagnosis": 3, "assessment": 2}
    pref_status = {"active": 3, "historical": 2, "resolved": 1, "uncertain": 0, "negated": -1, "family_history": 0}
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for a in assertions:
        k = condition_group_key_v2(a)
        a["condition_group_key_v2"] = k
        groups.setdefault(k, []).append(a)
    keys_sorted = sorted(groups.keys())
    key_to_id = {k: f"c2{idx + 1:04d}" for idx, k in enumerate(keys_sorted)}
    for k, items in groups.items():
        gid = key_to_id[k]
        for a in items:
            a["condition_group_id_v2"] = gid
            a["is_condition_best_evidence_v2"] = False

        def score_v2(x: Dict[str, Any]) -> Tuple[int, int, int, int]:
            try:
                er = int(x.get("evidence_rank", 3))
            except Exception:
                er = 3
            return (4 - er, 1 if x.get("icd_codes") else 0,
                    pref_cat.get((x.get("category") or "").lower(), 0),
                    pref_status.get((x.get("status") or "").lower(), 0))

        winner = max(items, key=score_v2)
        winner["is_condition_best_evidence_v2"] = True


def assign_condition_groups_v3(assertions: List[Dict[str, Any]]) -> None:
    pref_cat = {"diagnosis": 3, "assessment": 2}
    pref_status = {"active": 3, "historical": 2, "resolved": 1, "uncertain": 0, "negated": -1, "family_history": 0}
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for a in assertions:
        k = condition_group_key_v3(a)
        a["condition_group_key_v3"] = k
        groups.setdefault(k, []).append(a)
    keys_sorted = sorted(groups.keys())
    key_to_id = {k: f"g{idx + 1:04d}" for idx, k in enumerate(keys_sorted)}

    def score_v3(x: Dict[str, Any]) -> Tuple[int, int, int, int]:
        try:
            er = int(x.get("evidence_rank", 3))
        except Exception:
            er = 3
        return (4 - er,
                pref_cat.get((x.get("category") or "").lower(), 0),
                pref_status.get((x.get("status") or "").lower(), 0),
                1 if x.get("icd_codes") else 0)

    for k, items in groups.items():
        gid = key_to_id[k]
        for a in items:
            a["condition_group_id_v3"] = gid
            a["is_condition_best_evidence_v3"] = False
        winner = max(items, key=score_v3)
        winner["is_condition_best_evidence_v3"] = True


def contradiction_key(a: Dict[str, Any]) -> str:
    return f"{normalize_ws(a.get('concept', '')).lower()}|{a.get('subject', '')}|{a.get('category', '')}"


def apply_contradiction_flags(assertions: List[Dict[str, Any]]) -> None:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for a in assertions:
        buckets.setdefault(contradiction_key(a), []).append(a)
    for _, items in buckets.items():
        if not (any(x.get("status") == "active" for x in items) and any(x.get("status") == "negated" for x in items)):
            continue

        def score(x: Dict[str, Any]) -> Tuple[int, int]:
            try:
                ev_i = int(x.get("evidence_rank", 3))
            except Exception:
                ev_i = 3
            ev_score = 4 - ev_i
            cat = (x.get("category") or "").lower()
            cat_bonus = 1 if cat in {"assessment", "diagnosis", "plan", "lab_result", "lab_order"} else 0
            return (ev_score, cat_bonus)

        winner = max(items, key=score)
        for x in items:
            x["contradicted"] = (x is not winner)
