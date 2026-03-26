"""HCC Bridge — maps ICD codes from MiniMax assertions to HCC codes via V28.

Extracts payable RA candidate assertions, maps their ICD-10 codes through the
V28 ICD→HCC mapping table, applies hierarchy suppression, and computes RAF scores.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)


def _candidate_record(assertion: Dict[str, Any], code_entry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a normalized candidate record for audit trails."""
    return {
        "assertion_id": assertion.get("assertion_id"),
        "concept": assertion.get("concept"),
        "canonical_concept": assertion.get("canonical_concept"),
        "page_number": assertion.get("page_number"),
        "exact_quote": (assertion.get("exact_quote") or "")[:500],
        "effective_date": assertion.get("effective_date"),
        "evidence_rank": assertion.get("evidence_rank"),
        "condition_group_id_v3": assertion.get("condition_group_id_v3"),
        "status": assertion.get("status"),
        "category": assertion.get("category"),
        "icd10_code": ((code_entry or {}).get("code") or "").upper().strip(),
        "description": (code_entry or {}).get("description", ""),
    }


def extract_payable_icds(assertions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract payable ICD-10 codes from assertions that are RA candidates.

    Returns a list of dicts with:
      icd10_code, description, assertion_id, concept, page_number, exact_quote,
      effective_date, evidence_rank, condition_group_id_v3
    """
    payable: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []
    seen_codes: set = set()

    for a in assertions:
        if not a.get("is_payable_ra_candidate"):
            if a.get("category") in ("diagnosis", "assessment"):
                trace.append({
                    **_candidate_record(a),
                    "candidate_state": "rejected_candidate",
                    "reason_code": "not_payable_ra_candidate",
                    "reason": "Assertion did not pass deterministic risk-adjustment gating.",
                })
            continue

        # Use primary ICDs if available (for run-on problem lists), else all icd_codes
        icds = a.get("icd_codes_primary") or a.get("icd_codes") or []
        if not icds:
            trace.append({
                **_candidate_record(a),
                "candidate_state": "rejected_candidate",
                "reason_code": "missing_icd_code",
                "reason": "Risk-adjustment candidate had no ICD-10 code to map.",
            })
            continue

        for code_entry in icds:
            record = _candidate_record(a, code_entry)
            code = record["icd10_code"]
            if not code:
                trace.append({
                    **record,
                    "candidate_state": "rejected_candidate",
                    "reason_code": "blank_icd_code",
                    "reason": "Risk-adjustment candidate contained a blank ICD code.",
                })
                continue
            # Skip Z-codes (administrative)
            if code.startswith("Z"):
                trace.append({
                    **record,
                    "candidate_state": "rejected_candidate",
                    "reason_code": "administrative_z_code",
                    "reason": "Administrative Z-codes are excluded from payable HCC mapping.",
                })
                continue
            if code in seen_codes:
                trace.append({
                    **record,
                    "candidate_state": "rejected_candidate",
                    "reason_code": "duplicate_icd_code",
                    "reason": "ICD code already captured from a stronger or earlier assertion.",
                })
                continue
            seen_codes.add(code)

            record["candidate_state"] = "supported_candidate"
            record["reason_code"] = "passed_ra_gating"
            record["reason"] = "Assertion passed payable RA gating and will be evaluated for HCC mapping."
            payable.append(record)
            trace.append(dict(record))

    return payable, trace


def map_icds_to_hccs(
    payable_icds: List[Dict[str, Any]],
    hcc_mapper: Any,
) -> Dict[str, Any]:
    """Map ICD-10 codes to HCCs and apply hierarchy suppression.

    Args:
        payable_icds: Output of extract_payable_icds()
        hcc_mapper: A decisioning.hcc_mapper.HCCMapper instance

    Returns:
        Dict with payable_hccs, suppressed_hccs, unmapped_icds, hierarchy_log
    """
    hcc_mapper._load()

    # Map each ICD to its HCC
    hcc_to_icds: Dict[str, List[Dict[str, Any]]] = {}
    unmapped: List[Dict[str, Any]] = []
    decision_trace: List[Dict[str, Any]] = []

    for icd_info in payable_icds:
        code = icd_info["icd10_code"]
        # Try both dotted and undotted formats
        mapping = hcc_mapper._icd_to_hcc.get(code)
        if not mapping:
            undotted = code.replace(".", "")
            mapping = hcc_mapper._icd_to_hcc.get(undotted)
        if not mapping:
            # Try with dot added after 3rd char
            if len(code) > 3 and "." not in code:
                dotted = code[:3] + "." + code[3:]
                mapping = hcc_mapper._icd_to_hcc.get(dotted)

        if not mapping:
            rejection = {
                **icd_info,
                "candidate_state": "rejected_candidate",
                "reason_code": "no_hcc_mapping_in_v28",
                "reason": "ICD code is supported clinically but has no payable CMS-HCC V28 mapping.",
            }
            unmapped.append(rejection)
            decision_trace.append(rejection)
            continue

        hcc_code = mapping.get("hcc_code", "")
        if not hcc_code:
            rejection = {
                **icd_info,
                "candidate_state": "rejected_candidate",
                "reason_code": "empty_hcc_mapping",
                "reason": "Reference mapping row exists but does not resolve to a payable HCC.",
            }
            unmapped.append(rejection)
            decision_trace.append(rejection)
            continue

        if hcc_code not in hcc_to_icds:
            hcc_to_icds[hcc_code] = []
        verified = {
            **icd_info,
            "candidate_state": "verified_candidate",
            "reason_code": "mapped_to_hcc",
            "reason": "ICD code maps to a payable CMS-HCC V28 category.",
            "hcc_code": hcc_code,
            "hcc_description": mapping.get("hcc_description", ""),
            "raf_weight": mapping.get("raf_weight", 0),
        }
        hcc_to_icds[hcc_code].append(verified)
        decision_trace.append(dict(verified))

    # Apply hierarchy suppression
    active_hccs = set(hcc_to_icds.keys())
    suppressed: Dict[str, str] = {}  # hcc → suppressed_by
    hierarchy_log: List[Dict[str, Any]] = []

    for group in hcc_mapper._hierarchy_groups:
        ordered = group.get("ordered_hccs", [])
        present_in_group = [h for h in ordered if h in active_hccs]
        if len(present_in_group) <= 1:
            continue

        # First in the ordered list is highest priority
        winner = present_in_group[0]
        for loser in present_in_group[1:]:
            if loser not in suppressed:
                suppressed[loser] = winner
                hierarchy_log.append({
                    "suppressed_hcc": loser,
                    "suppressed_by": winner,
                    "group": group.get("group_name", ""),
                })

    # Build payable HCC list
    payable_hccs: List[Dict[str, Any]] = []
    suppressed_hccs: List[Dict[str, Any]] = []

    for hcc_code, icd_list in hcc_to_icds.items():
        hcc_entry = {
            "hcc_code": hcc_code,
            "hcc_description": icd_list[0].get("hcc_description", ""),
            "raf_weight": icd_list[0].get("raf_weight", 0),
            "supported_icds": icd_list,
            "icd_count": len(icd_list),
        }
        if hcc_code in suppressed:
            hcc_entry["suppressed_by"] = suppressed[hcc_code]
            for icd in icd_list:
                decision_trace.append({
                    **icd,
                    "candidate_state": "suppressed_candidate",
                    "reason_code": "hierarchy_suppression",
                    "reason": f"Suppressed by {suppressed[hcc_code]} under CMS-HCC hierarchy.",
                    "suppressed_by": suppressed[hcc_code],
                })
            suppressed_hccs.append(hcc_entry)
        else:
            hcc_entry["hierarchy_applied"] = hcc_code in {h for g in hcc_mapper._hierarchy_groups for h in g.get("ordered_hccs", [])}
            for icd in icd_list:
                decision_trace.append({
                    **icd,
                    "candidate_state": "payable_candidate",
                    "reason_code": "payable_hcc",
                    "reason": f"Mapped to final payable {hcc_code} after hierarchy review.",
                })
            payable_hccs.append(hcc_entry)

    return {
        "payable_hccs": payable_hccs,
        "suppressed_hccs": suppressed_hccs,
        "unmapped_icds": unmapped,
        "hierarchy_log": hierarchy_log,
        "decision_trace": decision_trace,
        "total_icd_codes": len(payable_icds),
        "total_hcc_codes": len(hcc_to_icds),
        "payable_hcc_count": len(payable_hccs),
        "suppressed_hcc_count": len(suppressed_hccs),
    }


def compute_raf_summary(
    hcc_result: Dict[str, Any],
    demographics: Optional[Dict[str, Any]] = None,
    raf_calculator: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compute RAF score summary from HCC mapping result.

    If raf_calculator is provided, uses it for demographic adjustments.
    Otherwise, sums payable HCC weights directly.
    """
    payable_hccs = hcc_result.get("payable_hccs", [])
    hcc_raf = sum(h.get("raf_weight", 0) for h in payable_hccs)

    # Demographics RAF (placeholder — depends on age/gender/eligibility)
    demographic_raf = 0.0
    if raf_calculator and demographics:
        try:
            demo_result = raf_calculator.calculate(
                payable_hccs=payable_hccs,
                demographics=demographics,
            )
            demographic_raf = demo_result.get("demographic_raf", 0.0)
            hcc_raf = demo_result.get("hcc_raf", hcc_raf)
        except Exception as e:
            log.warning("RAF calculation failed, using sum of weights: %s", e)

    return {
        "total_raf_score": round(demographic_raf + hcc_raf, 4),
        "demographic_raf": round(demographic_raf, 4),
        "hcc_raf": round(hcc_raf, 4),
        "hcc_count": hcc_result.get("total_hcc_codes", 0),
        "payable_hcc_count": hcc_result.get("payable_hcc_count", 0),
        "suppressed_hcc_count": hcc_result.get("suppressed_hcc_count", 0),
        "unmapped_icd_count": len(hcc_result.get("unmapped_icds", [])),
    }


def build_hcc_pack(
    assertions: List[Dict[str, Any]],
    hcc_mapper: Any,
    raf_calculator: Optional[Any] = None,
    chart_id: str = "",
    demographics: Optional[Dict[str, Any]] = None,
    measurement_year: int = 2026,
) -> Dict[str, Any]:
    """Build the complete HCC pack from assertions.

    This is the main entry point for HCC processing from MiniMax output.
    """
    payable_icds, candidate_trace = extract_payable_icds(assertions)
    log.info("Extracted %d payable ICD codes from %d assertions",
             len(payable_icds),
             sum(1 for a in assertions if a.get("is_payable_ra_candidate")))

    hcc_result = map_icds_to_hccs(payable_icds, hcc_mapper)
    raf_summary = compute_raf_summary(hcc_result, demographics, raf_calculator)

    return {
        "chart_id": chart_id,
        "measurement_year": measurement_year,
        "payable_hccs": hcc_result["payable_hccs"],
        "suppressed_hccs": hcc_result["suppressed_hccs"],
        "unmapped_icds": hcc_result["unmapped_icds"],
        "hierarchy_log": hcc_result["hierarchy_log"],
        "decision_trace": candidate_trace + hcc_result.get("decision_trace", []),
        "candidate_summary": {
            "supported_candidate_count": len(payable_icds),
            "payable_candidate_count": len(hcc_result["payable_hccs"]),
            "suppressed_candidate_count": len(hcc_result["suppressed_hccs"]),
            "rejected_candidate_count": len(hcc_result["unmapped_icds"]),
        },
        "raf_summary": raf_summary,
        "payable_icd_count": len(payable_icds),
    }
