"""Deterministic vital sign extraction from clinical text."""

from __future__ import annotations

import re
from typing import Any, Dict, List

VITAL_PATTERNS = [
    ("bmi", re.compile(r"\bBMI\b(?:\s*\(.*?\))?\s*[:=]?\s*([0-9]{1,3}(?:\.[0-9]+)?)", re.I)),
    ("bp", re.compile(r"\b(?:BP|B\/P|Blood Pressure)\b\s*[:=]?\s*([0-9]{2,3})\s*/\s*([0-9]{2,3})", re.I)),
    ("pulse", re.compile(r"\b(?:Pulse|HR|Heart Rate)\b\s*[:=]?\s*([0-9]{2,3})\b", re.I)),
    ("temp_f", re.compile(r"\b(?:Temp|Temperature)\b\s*[:=]?\s*([0-9]{2,3}(?:\.[0-9]+)?)\s*F\b", re.I)),
    ("temp_c", re.compile(r"\b(?:Temp|Temperature)\b\s*[:=]?\s*([0-9]{2,3}(?:\.[0-9]+)?)\s*C\b", re.I)),
    ("spo2", re.compile(r"\b(?:SpO2|O2\s*Sat|O2\s*Saturation|Pulse\s*Ox)\b\s*[:=]?\s*([0-9]{2,3})\s*%?", re.I)),
    ("resp", re.compile(r"\b(?:Resp|RR|Respirations)\b\s*[:=]?\s*([0-9]{1,3})\b", re.I)),
    ("height_inches", re.compile(r"\b(?:Height|Ht)\b\s*[:=]?\s*([0-9]{1,3})\s*(?:in|inch|inches)\b", re.I)),
    ("height_cm", re.compile(r"\b(?:Height|Ht)\b\s*[:=]?\s*([0-9]{2,3}(?:\.[0-9]+)?)\s*(?:cm)\b", re.I)),
    ("weight_lbs", re.compile(r"\b(?:Weight|Wt)\b\s*[:=]?\s*([0-9]{2,3}(?:\.[0-9]+)?)\s*(?:lb|lbs|pounds)\b", re.I)),
    ("weight_kg", re.compile(r"\b(?:Weight|Wt)\b\s*[:=]?\s*([0-9]{2,3}(?:\.[0-9]+)?)\s*(?:kg)\b", re.I)),
]

_RANGE_BOUNDS = {
    "bmi": (8, 90), "bp_systolic": (50, 260), "bp_diastolic": (30, 160),
    "pulse": (25, 250), "temp_f": (90, 110), "temp_c": (30, 45),
    "spo2": (50, 100), "resp": (4, 80), "height_inches": (40, 90),
    "height_cm": (100, 250), "weight_lbs": (30, 800), "weight_kg": (15, 400),
}


def _in_range(key: str, v: float) -> bool:
    lo, hi = _RANGE_BOUNDS.get(key, (-float("inf"), float("inf")))
    return lo <= v <= hi


def extract_structured_vitals_from_page(page_text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not page_text:
        return out
    for key, rx in VITAL_PATTERNS:
        m = rx.search(page_text)
        if not m:
            continue
        if key == "bp":
            sys_v = int(m.group(1))
            dia_v = int(m.group(2))
            if _in_range("bp_systolic", sys_v) and _in_range("bp_diastolic", dia_v):
                out["bp_systolic"] = sys_v
                out["bp_diastolic"] = dia_v
        elif key in ("pulse", "spo2", "resp", "height_inches"):
            v = int(float(m.group(1)))
            if _in_range(key, v):
                out[key] = v
        elif key == "height_cm":
            v = float(m.group(1))
            if _in_range("height_cm", v):
                out["height_cm"] = v
        elif key == "weight_kg":
            v = float(m.group(1))
            if _in_range("weight_kg", v):
                out["weight_kg"] = v
        elif key == "weight_lbs":
            v = float(m.group(1))
            if _in_range("weight_lbs", v):
                out[key] = v
        else:
            v = float(m.group(1))
            if _in_range(key, v):
                out[key] = v
    if "height_cm" in out and "height_inches" not in out:
        out["height_inches"] = round(out["height_cm"] / 2.54, 2)
    if "weight_kg" in out and "weight_lbs" not in out:
        out["weight_lbs"] = round(out["weight_kg"] * 2.20462, 2)
    return out


def generate_vital_assertions_from_page(page_number: int, page_text: str) -> List[Dict[str, Any]]:
    if not page_text:
        return []
    asserted: List[Dict[str, Any]] = []
    for m in re.finditer(r"\b(?:BP|B\/P|Blood Pressure)\b\s*[:=]?\s*([0-9]{2,3})\s*/\s*([0-9]{2,3})", page_text, flags=re.I):
        sys_v = int(m.group(1))
        dia_v = int(m.group(2))
        if not (_in_range("bp_systolic", sys_v) and _in_range("bp_diastolic", dia_v)):
            continue
        asserted.append({
            "category": "vital_sign", "concept": "blood pressure",
            "text": f"Blood pressure {sys_v}/{dia_v}.",
            "status": "active", "subject": "patient", "page_number": page_number,
            "exact_quote": m.group(0), "evidence_rank": 2,
            "structured": {"bp_systolic": sys_v, "bp_diastolic": dia_v},
        })
        break
    for m in re.finditer(r"\bBMI\b(?:\s*\(.*?\))?\s*[:=]?\s*([0-9]{1,3}(?:\.[0-9]+)?)", page_text, flags=re.I):
        bmi = float(m.group(1))
        if not _in_range("bmi", bmi):
            continue
        asserted.append({
            "category": "vital_sign", "concept": "body mass index",
            "text": f"BMI {bmi}.",
            "status": "active", "subject": "patient", "page_number": page_number,
            "exact_quote": m.group(0), "evidence_rank": 2,
            "structured": {"bmi": bmi},
        })
        break
    for m in re.finditer(r"\b(?:Pulse|HR|Heart Rate)\b\s*[:=]?\s*([0-9]{2,3})\b", page_text, flags=re.I):
        v = int(m.group(1))
        if not _in_range("pulse", v):
            continue
        asserted.append({
            "category": "vital_sign", "concept": "pulse",
            "text": f"Pulse {v} bpm.",
            "status": "active", "subject": "patient", "page_number": page_number,
            "exact_quote": m.group(0), "evidence_rank": 2,
            "structured": {"pulse": v},
        })
        break
    for m in re.finditer(r"\b(?:SpO2|O2\s*Sat|O2\s*Saturation|Pulse\s*Ox)\b\s*[:=]?\s*([0-9]{2,3})\s*%?", page_text, flags=re.I):
        v = int(m.group(1))
        if not _in_range("spo2", v):
            continue
        asserted.append({
            "category": "vital_sign", "concept": "oxygen saturation",
            "text": f"SpO2 {v}%.",
            "status": "active", "subject": "patient", "page_number": page_number,
            "exact_quote": m.group(0), "evidence_rank": 2,
            "structured": {"spo2": v},
        })
        break
    for m in re.finditer(r"\b(?:Weight|Wt)\b\s*[:=]?\s*([0-9]{2,3}(?:\.[0-9]+)?)\s*(?:lb|lbs|pounds)\b", page_text, flags=re.I):
        v = float(m.group(1))
        if not _in_range("weight_lbs", v):
            continue
        asserted.append({
            "category": "vital_sign", "concept": "weight",
            "text": f"Weight {v} lb.",
            "status": "active", "subject": "patient", "page_number": page_number,
            "exact_quote": m.group(0), "evidence_rank": 2,
            "structured": {"weight_lbs": v},
        })
        break
    for m in re.finditer(r"\b(?:Height|Ht)\b\s*[:=]?\s*([0-9]{1,3})\s*(?:in|inch|inches)\b", page_text, flags=re.I):
        v = float(m.group(1))
        if not _in_range("height_inches", v):
            continue
        asserted.append({
            "category": "vital_sign", "concept": "height",
            "text": f"Height {v} inches.",
            "status": "active", "subject": "patient", "page_number": page_number,
            "exact_quote": m.group(0), "evidence_rank": 2,
            "structured": {"height_inches": v},
        })
        break
    return asserted
