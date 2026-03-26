#!/usr/bin/env python3
"""
Atomic, auditable clinical assertion extractor.

Fixes vs your last version:
- Generates globally unique assertion_id post-merge (ignores model IDs).
- Quarantines admin/billing encounter statements into category=administrative_code.
- Flags contradictions using evidence_rank + polarity (A/P beats ROS).
- Extracts structured vitals deterministically (BMI/BP/etc) from page text.
- Enforces quote audit + char offsets; unverifiable outputs are dropped.
- Makes empty-text PDFs obvious (common for scanned PDFs); no silent garbage.

Install:
  pip install pymupdf openai

Run:
  set OPENAI_API_KEY=...
  python test_sentences.py input.pdf -o clean_assertions.json --model gpt-4.1-mini
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from openai import OpenAI


SYSTEM_PROMPT = r"""
You output ONLY valid JSON.

Task: Convert clinical chart text into AUDITABLE, ATOMIC clinical assertions for downstream ICD/HCC/ML.

Non-negotiables:
1) ATOMICITY: one clinical assertion per item. Split mixed facts, mixed polarity, mixed subject.
2) PROVENANCE: every item MUST include:
   - page_number
   - exact_quote that appears verbatim in the supplied page text
   If exact_quote is not verbatim, do not output the item.
3) SUBJECT: patient | family_member | provider_plan | generic_education
4) STATUS: active | negated | historical | resolved | uncertain | family_history
   Negated applies ONLY to the clinical concept denied/absent.
5) SECTION/EVIDENCE:
   evidence_rank must be:
   1 = Assessment/Diagnosis/Problem List/Plan/Orders/Results
   2 = HPI/Chief Complaint/Objective narrative
   3 = ROS templates / boilerplate / education
6) ADMIN/BILLING QUARANTINE:
   If the text is primarily an encounter/billing/admin description (e.g., “Encounter for…”, Z-codes for screening, pre-op exam phrasing),
   set category = "administrative_code" and do NOT phrase it as a disease.
7) ALLERGIES:
   “NKDA”, “No known drug allergies” -> category "allergy", concept "drug allergy", status "negated", allergy_none=true.

Schema:
{
  "assertions":[
    {
      "category":"one of: chief_complaint, history_present_illness, review_of_systems, physical_exam, assessment, diagnosis, plan, medication, lab_result, lab_order, referral, procedure, screening, counseling, social_history, family_history, preventive_care, mental_health, symptom, vital_sign, allergy, imaging, administrative_code",
      "concept":"short normalized clinical concept",
      "text":"clean atomic assertion in plain clinical English, minimal but faithful",
      "status":"active|negated|historical|resolved|uncertain|family_history",
      "subject":"patient|family_member|provider_plan|generic_education",
      "page_number":integer,
      "exact_quote":"verbatim substring from page text",
      "evidence_rank":1|2|3,
      "negation_trigger":string|null,
      "allergy_none":bool
    }
  ]
}
""".strip()


@dataclass
class PageText:
    page_number: int
    text: str


def extract_pages(pdf_path: str) -> List[PageText]:
    doc = fitz.open(pdf_path)
    pages: List[PageText] = []
    for i in range(len(doc)):
        t = doc[i].get_text("text") or ""
        t = t.replace("\x00", "")
        pages.append(PageText(page_number=i + 1, text=t))
    doc.close()
    return pages


def chunk_pages_by_chars(pages: List[PageText], max_chars: int) -> List[Tuple[int, int]]:
    ranges = []
    n = len(pages)
    i = 0
    while i < n:
        total = 0
        j = i
        while j < n and total + len(pages[j].text) <= max_chars:
            total += len(pages[j].text)
            j += 1
        if j == i:
            j = i + 1
        ranges.append((i, j))
        i = j
    return ranges


def build_chunk_payload(pages: List[PageText], start_idx: int, end_idx: int) -> str:
    parts = []
    for p in pages[start_idx:end_idx]:
        parts.append(f"\n\n=== PAGE {p.page_number} START ===\n{p.text}\n=== PAGE {p.page_number} END ===\n")
    return "".join(parts).strip()


def call_llm(client: OpenAI, model: str, chunk_text: str) -> Dict[str, Any]:
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chunk_text},
        ],
        temperature=0,
    )
    out_text = resp.output_text.strip()
    try:
        return json.loads(out_text)
    except json.JSONDecodeError:
        out_text2 = re.sub(r"^```(?:json)?\s*|\s*```$", "", out_text, flags=re.MULTILINE).strip()
        return json.loads(out_text2)


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def find_quote_offset(page_text: str, exact_quote: str) -> Optional[Tuple[int, int]]:
    if not exact_quote:
        return None
    idx = page_text.find(exact_quote)
    if idx >= 0:
        return idx, idx + len(exact_quote)
    return None  # do not lie with fuzzy offsets


def merge_results(chunk_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for r in chunk_results:
        items = r.get("assertions", [])
        if isinstance(items, list):
            merged.extend(items)
    return merged


def normalize_assertion(a: Dict[str, Any]) -> Dict[str, Any]:
    a = dict(a)
    a.setdefault("negation_trigger", None)
    a.setdefault("allergy_none", False)
    a.setdefault("evidence_rank", 3)
    return a


def dedupe_assertions(assertions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for a in assertions:
        key = (
            a.get("page_number"),
            normalize_ws(a.get("exact_quote", "") or ""),
            normalize_ws(a.get("concept", "") or ""),
            a.get("status"),
            a.get("subject"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


# ---------- deterministic structured extraction (vitals) ----------
VITAL_PATTERNS = [
    ("bmi", re.compile(r"\bBMI\b\s*[:=]?\s*([0-9]{1,3}(?:\.[0-9]+)?)", re.IGNORECASE)),
    ("bp", re.compile(r"\b(?:BP|Blood Pressure)\b\s*[:=]?\s*([0-9]{2,3})\s*/\s*([0-9]{2,3})", re.IGNORECASE)),
    ("pulse", re.compile(r"\b(?:Pulse|HR|Heart Rate)\b\s*[:=]?\s*([0-9]{2,3})\b", re.IGNORECASE)),
    ("temp_f", re.compile(r"\b(?:Temp|Temperature)\b\s*[:=]?\s*([0-9]{2,3}(?:\.[0-9]+)?)\s*F\b", re.IGNORECASE)),
    ("spo2", re.compile(r"\b(?:SpO2|O2 Sat)\b\s*[:=]?\s*([0-9]{2,3})\s*%?", re.IGNORECASE)),
    ("resp", re.compile(r"\b(?:Resp|RR|Respirations)\b\s*[:=]?\s*([0-9]{1,3})\b", re.IGNORECASE)),
]


def extract_structured_vitals_from_page(page_text: str) -> Dict[str, Any]:
    structured: Dict[str, Any] = {}
    for key, pat in VITAL_PATTERNS:
        m = pat.search(page_text)
        if not m:
            continue
        if key == "bp":
            structured["bp_systolic"] = int(m.group(1))
            structured["bp_diastolic"] = int(m.group(2))
        elif key in ("pulse", "spo2", "resp"):
            structured[key] = int(float(m.group(1)))
        else:
            structured[key] = float(m.group(1))
    return structured


# ---------- contradiction detection ----------
def contradiction_key(a: Dict[str, Any]) -> str:
    # crude but effective: concept + subject, ignore status
    return f"{normalize_ws(a.get('concept','') or '').lower()}|{a.get('subject','')}"


def apply_contradiction_flags(assertions: List[Dict[str, Any]]) -> None:
    """
    Flags contradictions where same concept appears both active and negated.
    Prefer higher evidence_rank; mark the weaker as contradicted=true.
    """
    bucket: Dict[str, List[Dict[str, Any]]] = {}
    for a in assertions:
        ck = contradiction_key(a)
        bucket.setdefault(ck, []).append(a)

    for ck, items in bucket.items():
        has_active = [x for x in items if x.get("status") == "active"]
        has_neg = [x for x in items if x.get("status") == "negated"]
        if not has_active or not has_neg:
            continue

        # pick strongest evidence as winner
        def score(x: Dict[str, Any]) -> Tuple[int, int]:
            # higher evidence_rank stronger? No: rank 1 strongest -> invert
            ev = x.get("evidence_rank", 3)
            ev_score = 4 - int(ev) if isinstance(ev, int) else 1
            # prefer assessment/diagnosis categories slightly
            cat = (x.get("category") or "").lower()
            cat_bonus = 1 if cat in {"assessment", "diagnosis", "plan", "lab_result", "lab_order"} else 0
            return (ev_score, cat_bonus)

        # winner among all items
        winner = max(items, key=score)
        for x in items:
            x["contradicted"] = (x is not winner)


def validate_and_enrich(assertions: List[Dict[str, Any]], pages_by_num: Dict[int, str]) -> List[Dict[str, Any]]:
    audited: List[Dict[str, Any]] = []
    for a in assertions:
        a = normalize_assertion(a)

        pn = a.get("page_number")
        q = a.get("exact_quote", "")

        if not isinstance(pn, int) or pn not in pages_by_num:
            continue

        off = find_quote_offset(pages_by_num[pn], q)
        if off is None:
            continue

        # deterministic admin quarantine (backup if model fails)
        txt = (a.get("text") or "").strip().lower()
        cq = (a.get("concept") or "").strip().lower()
        if txt.startswith("encounter for") or "encounter for" in txt or cq.startswith("encounter for"):
            a["category"] = "administrative_code"

        a["char_start"], a["char_end"] = off

        # attach deterministic structured vitals if this page has them
        a["structured_page_vitals"] = extract_structured_vitals_from_page(pages_by_num[pn])

        audited.append(a)

    # post-merge unique IDs
    for idx, a in enumerate(audited, start=1):
        pn = a.get("page_number", 0)
        a["assertion_id"] = f"p{pn:03d}_{idx:05d}"

    # contradiction flags
    apply_contradiction_flags(audited)

    return audited


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="Input PDF path")
    ap.add_argument("-o", "--out", default=None, help="Output JSON path")
    ap.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name")
    ap.add_argument("--chunk-chars", type=int, default=9000, help="Max characters per chunk")
    ap.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout seconds")
    args = ap.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set")

    pages = extract_pages(args.pdf)

    # Hard fail on scanned PDFs with no extractable text
    nonempty_pages = sum(1 for p in pages if p.text.strip())
    if nonempty_pages == 0:
        raise SystemExit("PDF text extraction returned empty for all pages. This is likely a scanned PDF. Add OCR if you need it.")

    ranges = chunk_pages_by_chars(pages, args.chunk_chars)
    client = OpenAI(api_key=api_key, timeout=args.timeout)

    chunk_results: List[Dict[str, Any]] = []
    t0 = time.time()

    for (i, j) in ranges:
        chunk_text = build_chunk_payload(pages, i, j)
        chunk_results.append(call_llm(client, args.model, chunk_text))

    merged = merge_results(chunk_results)
    merged = dedupe_assertions(merged)

    pages_by_num = {p.page_number: p.text for p in pages}
    audited = validate_and_enrich(merged, pages_by_num)

    out_path = args.out
    if out_path is None:
        base = os.path.splitext(os.path.basename(args.pdf))[0]
        out_path = f"{base}.atomic_assertions.json"

    out = {
        "meta": {
            "pdf": os.path.basename(args.pdf),
            "page_count": len(pages),
            "pages_with_text": nonempty_pages,
            "chunks": len(ranges),
            "model": args.model,
            "elapsed_sec": round(time.time() - t0, 2),
            "assertions_total_raw": len(merged),
            "assertions_total_audited": len(audited),
        },
        "assertions": audited,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote: {out_path}")
    print(json.dumps(out["meta"], indent=2))


if __name__ == "__main__":
    main()