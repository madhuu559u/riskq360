"""ICD/CPT/HCPCS code classification and extraction from clinical text."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .quote_validator import normalize_ws

_ICD_TAG_LABELED_RE = re.compile(
    r"\[(ICD\s*-?\s*10|ICD\s*-?\s*9|ICD)\s*:\s*([A-TV-Z0-9][A-TV-Z0-9\.]{2,8})\]", re.I
)
_ICD10_RE = re.compile(r"\b([A-TV-Z]\d{2,3}(?:\.\d{1,4})?)\b")
_CPT2_RE = re.compile(r"\b(\d{4}F)\b")
_HCPCS_RE = re.compile(r"\b([A-Z]\d{4})\b")
_ICD_TAG_RE = re.compile(r"(?:ICD[-\s]?10(?:-CM)?\s*[:#]?\s*)([A-TV-Z]\d{2,3}(?:\.\d{1,4})?)", re.I)

# Common ICD-10 descriptions for deterministic harvesting
ICD_DESCRIPTIONS: Dict[str, str] = {
    "E11.9": "Type 2 diabetes mellitus without complications",
    "E11.65": "Type 2 diabetes mellitus with hyperglycemia",
    "E11.69": "Type 2 diabetes mellitus with other specified complication",
    "E11.51": "Type 2 diabetes mellitus with diabetic peripheral angiopathy without gangrene",
    "E11.42": "Type 2 diabetes mellitus with diabetic neuropathy",
    "E11.29": "Type 2 diabetes mellitus with other kidney complication",
    "E11.40": "Type 2 diabetes mellitus with neuropathy",
    "E11.339": "Type 2 diabetes mellitus with diabetic retinopathy without macular edema",
    "I10": "Essential (primary) hypertension",
    "I11.0": "Hypertensive heart failure with heart failure",
    "I13.11": "Hypertensive heart and chronic kidney disease without heart failure",
    "I25.10": "Arteriosclerotic cardiovascular disease",
    "I48.0": "Paroxysmal atrial fibrillation",
    "I50.32": "Chronic diastolic heart failure",
    "I63.9": "Cerebral infarction, unspecified",
    "I70.0": "Atherosclerosis of aorta",
    "E78.5": "Hyperlipidemia, unspecified",
    "E78.00": "Pure hypercholesterolemia, unspecified",
    "E78.2": "Mixed hyperlipidemia",
    "E03.9": "Hypothyroidism, unspecified",
    "E46": "Unspecified protein-calorie malnutrition",
    "D64.9": "Anemia, unspecified",
    "D50.9": "Iron deficiency anemia, unspecified",
    "N18.30": "Chronic kidney disease, stage 3",
    "N18.31": "Chronic kidney disease, stage 3a",
    "N40.0": "Benign prostatic hyperplasia without lower urinary tract symptoms",
    "F32.0": "Major depressive disorder, single episode, mild",
    "F32.1": "Major depressive disorder, single episode, moderate",
    "F33.9": "Major depressive disorder, recurrent, unspecified",
    "F03.90": "Unspecified dementia without behavioral disturbance",
    "F41.9": "Anxiety disorder, unspecified",
    "F41.0": "Generalized anxiety disorder",
    "G20": "Parkinson disease",
    "G47.00": "Insomnia, unspecified",
    "G62.9": "Polyneuropathy, unspecified",
    "J42": "Unspecified chronic bronchitis",
    "J45.909": "Unspecified asthma, uncomplicated",
    "M17.2": "Osteoarthritis of knee",
    "M19.90": "Osteoarthritis, unspecified site",
    "M79.7": "Fibromyalgia",
    "R51.9": "Headache, unspecified",
    "Z00.00": "Encounter for general adult medical examination without abnormal findings",
    "Z23": "Encounter for immunization",
    "Z79.4": "Long term (current) use of insulin",
}


def get_icd_description(code: str) -> str:
    return ICD_DESCRIPTIONS.get(code.upper(), f"Diagnosis code {code}")


def classify_codes(text: str) -> List[Dict[str, str]]:
    """Classify codes found in text into typed system entries (icd10cm, icd9cm, cpt2, hcpcs)."""
    combined = text or ""
    found: List[Dict[str, str]] = []
    seen: set = set()

    for m in _ICD_TAG_LABELED_RE.finditer(combined):
        label = re.sub(r"\s+", "", m.group(1).upper())
        code = m.group(2).upper()
        if not code or code in seen:
            continue
        if label in {"ICD-9", "ICD9"}:
            sys = "icd9cm"
        else:
            sys = "icd10cm"
        seen.add(code)
        found.append({"system": sys, "code": code, "description": ""})

    for m in _ICD10_RE.finditer(combined):
        code = m.group(1).upper()
        if not code or code in seen:
            continue
        if re.search(r"ICD\s*-?\s*9\s*:\s*%s" % re.escape(code), combined, flags=re.I):
            continue
        seen.add(code)
        found.append({"system": "icd10cm", "code": code, "description": ""})

    for m in _CPT2_RE.finditer(combined):
        code = m.group(1).upper()
        if not code or code in seen:
            continue
        seen.add(code)
        found.append({"system": "cpt2", "code": code, "description": ""})

    for m in _HCPCS_RE.finditer(combined):
        code = m.group(1).upper()
        if not code or code in seen:
            continue
        if _ICD10_RE.fullmatch(code):
            continue
        seen.add(code)
        found.append({"system": "hcpcs", "code": code, "description": ""})

    return found


def normalize_codes(a: Dict[str, Any]) -> None:
    blob = " ".join([str(a.get("concept", "")), str(a.get("text", "")), str(a.get("exact_quote", ""))])
    typed = classify_codes(blob)
    a["codes"] = typed
    a["icd_codes"] = [{"code": c["code"], "description": ""} for c in typed if c["system"] == "icd10cm"]
    a["icd9_codes"] = [{"code": c["code"], "description": ""} for c in typed if c["system"] == "icd9cm"]
    a["cpt2_codes"] = [{"code": c["code"], "description": ""} for c in typed if c["system"] == "cpt2"]
    a["hcpcs_codes"] = [{"code": c["code"], "description": ""} for c in typed if c["system"] == "hcpcs"]


def extract_icd_from_quote(a: Dict[str, Any]) -> None:
    """Extract ICD codes from exact_quote that LLM may have missed."""
    quote = a.get("exact_quote", "")
    if not quote:
        return
    existing_codes = {c.get("code", "").upper() for c in a.get("icd_codes", []) if c.get("code")}
    icd_pattern = re.compile(r'\b([A-TV-Z]\d{2,3}(?:\.\d{1,4})?)\b')
    found_codes: List[Dict[str, str]] = []
    for m in icd_pattern.finditer(quote):
        code = m.group(1).upper()
        if code in existing_codes:
            continue
        skip = False
        for existing in existing_codes:
            if code.startswith(existing) or existing.startswith(code):
                skip = True
                break
        if skip:
            continue
        found_codes.append({"code": code, "description": ""})
    if found_codes:
        a["icd_codes"] = a.get("icd_codes", []) + found_codes
        for fc in found_codes:
            a["codes"] = a.get("codes", []) + [{"system": "icd10cm", "code": fc["code"], "description": ""}]


def enrich_codes_near_quote(a: Dict[str, Any], page_text: str, window: int = 600) -> None:
    """Find ICD tags near the assertion quote for context (non-authoritative)."""
    try:
        s = int(a.get("char_start", 0))
        e = int(a.get("char_end", 0))
    except Exception:
        return
    lo = max(0, min(s, e) - window)
    hi = min(len(page_text), max(s, e) + window)
    region = page_text[lo:hi]
    tags = sorted({m.group(1).upper() for m in _ICD_TAG_RE.finditer(region)})
    if not tags:
        return
    a["icd_tags_near_quote"] = tags
    a["icd_codes_near_quote"] = [{"code": t, "description": ""} for t in tags]


def select_primary_icd_codes(a: Dict[str, Any]) -> None:
    """For run-on problem lists, select the ICD codes closest to this concept."""
    cat = (a.get("category") or "").lower()
    if cat not in {"diagnosis", "assessment"}:
        return
    codes = a.get("icd_codes") or []
    if len(codes) <= 1:
        if len(codes) == 1:
            a["icd_codes_primary"] = codes
        return

    q = a.get("exact_quote") or ""
    concept = (a.get("concept") or "").strip()
    if not q or not concept:
        a["icd_codes_primary"] = [codes[0]]
        return

    m = re.search(re.escape(concept), q, flags=re.I)
    if not m:
        cc = (a.get("canonical_concept") or "").strip()
        if cc:
            m = re.search(re.escape(cc), q, flags=re.I)
    if not m:
        a["icd_codes_primary"] = [codes[0]]
        return

    start, end = m.start(), m.end()
    tags = [(tm.group(1).upper(), tm.start(), tm.end()) for tm in _ICD_TAG_RE.finditer(q)]
    if not tags:
        a["icd_codes_primary"] = [codes[0]]
        return

    window = 90
    near = [c for c, s, e in tags if (abs(s - start) <= window or abs(s - end) <= window)]
    if not near:
        after = [c for c, s, e in tags if s >= end]
        near = after[:1] if after else [tags[0][0]]

    out: List[str] = []
    for c in near:
        if c not in out:
            out.append(c)
    a["icd_codes_primary"] = [{"code": c, "description": ""} for c in out]


def get_grouping_icd_list(a: Dict[str, Any]) -> List[str]:
    """Use primary ICDs for grouping dx/assessment; otherwise use icd_codes."""
    cat = (a.get("category") or "").lower()
    if cat in {"diagnosis", "assessment"}:
        prim = a.get("icd_codes_primary") or []
        if prim:
            return [c.get("code", "").upper() for c in prim if c.get("code")]
    icds = a.get("icd_codes") or []
    return [c.get("code", "").upper() for c in icds if c.get("code")]
