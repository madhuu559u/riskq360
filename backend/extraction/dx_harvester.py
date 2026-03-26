"""Deterministic diagnosis harvesting from page text.

Catches ICD codes in labeled tags ([ICD-10: ...]) and inline codes
that the LLM might miss.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .quote_validator import normalize_ws
from .code_classifier import _ICD_TAG_RE, get_icd_description


def harvest_coded_diagnoses_from_page(page_number: int, page_text: str) -> List[Dict[str, Any]]:
    """Extract diagnoses from lines containing [ICD-10: ...] labels."""
    out: List[Dict[str, Any]] = []
    if not page_text:
        return out
    bad_concepts = {"unspecified", "unspecified disorder", "unspecified disease", "unspecified cause"}
    for line in page_text.splitlines():
        if "ICD" not in line and "icd" not in line:
            continue
        tags = list(_ICD_TAG_RE.finditer(line))
        if not tags:
            continue
        for tm in tags:
            code_str = tm.group(1).upper()
            left = line[:tm.start()]
            if re.search(r"\bdiagnosis\b\s*[:\-]?", left, flags=re.I):
                left = re.split(r"\bdiagnosis\b\s*[:\-]?", left, flags=re.I)[-1]
            left = re.sub(r"\bSNOMED\s*[:#]?\s*\d+\]?\s*", "", left, flags=re.I)
            left = normalize_ws(left)
            parts = re.split(r"[;|•\u2022]", left)
            cand = normalize_ws(parts[-1] if parts else left)
            cand = re.split(r"\b(ICD|CPT|HCPCS)\b", cand, flags=re.I)[0].strip()
            cand = re.sub(r"[\[\]\(\)]", "", cand).strip()
            if not cand:
                continue
            cand_l = cand.lower()
            if cand_l in bad_concepts or cand_l.startswith("unspecified "):
                if len(parts) >= 2:
                    cand2 = normalize_ws(parts[-2])
                    cand2_l = cand2.lower()
                    if cand2 and cand2_l not in bad_concepts and not cand2_l.startswith("unspecified "):
                        cand = cand2
                    else:
                        continue
                else:
                    continue
            quote = normalize_ws(line)
            out.append({
                "category": "diagnosis", "concept": cand, "text": f"{cand}.",
                "status": "active", "subject": "patient", "page_number": page_number,
                "exact_quote": quote, "evidence_rank": 1, "structured": {},
            })
    return out


def harvest_all_icd_codes_from_page(page_number: int, page_text: str) -> List[Dict[str, Any]]:
    """Find ICD codes even without explicit [ICD-10: ...] labels."""
    out: List[Dict[str, Any]] = []
    if not page_text:
        return out
    icd_pattern = re.compile(r'\b([A-TV-Z]\d{2,3}(?:\.\d{1,4})?)\b')
    found_codes: Dict[str, str] = {}
    for m in icd_pattern.finditer(page_text):
        code = m.group(1).upper()
        if len(code) < 3:
            continue
        start = max(0, m.start() - 200)
        end = min(len(page_text), m.end() + 200)
        context = page_text[start:end]
        if code not in found_codes:
            found_codes[code] = context

    for code, context in found_codes.items():
        lines = context.split('\n')
        best_line = None
        for line in lines:
            if code in line:
                best_line = line
                break
        if not best_line:
            best_line = context[:200]
        concept_line = re.sub(r'\b' + code + r'\b', '', best_line, flags=re.I).strip()
        concept_line = re.sub(r'[\[\]\(\)]', '', concept_line).strip()
        concept_line = re.sub(r'^[:\-,\.]+', '', concept_line).strip()
        concept_line = re.sub(r'[:\-,\.]+$', '', concept_line).strip()
        concept = concept_line if concept_line else get_icd_description(code)
        out.append({
            "category": "diagnosis",
            "concept": concept[:100] if concept else f"Diagnosis {code}",
            "text": f"{concept[:100] if concept else f'Diagnosis {code}'}.",
            "status": "active", "subject": "patient", "page_number": page_number,
            "exact_quote": best_line[:500] if best_line else context[:500],
            "evidence_rank": 1, "structured": {},
            "icd_codes": [{"code": code, "description": ""}],
            "codes": [{"system": "icd10cm", "code": code, "description": ""}],
        })
    return out
