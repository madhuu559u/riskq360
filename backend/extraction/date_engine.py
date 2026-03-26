"""Date extraction, inference, and effective-date computation for clinical assertions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as dateparser

from .quote_validator import normalize_ws


@dataclass
class DateSpan:
    raw: str
    iso: str
    start: int
    end: int
    kind: str


@dataclass
class DateAnchor:
    kind: str
    start: int
    end: int
    text: str


_DATE_REGEXES = [
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b", re.I),
]
_DOB_RX = re.compile(r"\b(dob|d\.o\.b\.|date of birth|born)\b", re.I)
_AGE_RX = re.compile(r"\b(age|yrs?|years? old)\b", re.I)

_CTX = {
    "dos": re.compile(r"\b(date of service|dos|service date|encounter date|visit date|date of visit)\b", re.I),
    "performed": re.compile(r"\b(performed on|procedure date)\b", re.I),
    "collection": re.compile(r"\b(collection date|collected|specimen collected)\b", re.I),
    "result": re.compile(r"\b(result date|results date|resulted|resulted on)\b", re.I),
    "reported": re.compile(r"\b(reported|reported on|final report)\b", re.I),
    "created": re.compile(r"\b(created|generated|printed|print date|signed|signed on)\b", re.I),
}
_KIND_PRIORITY = {"dos": 0, "performed": 1, "collection": 1, "result": 2, "reported": 2, "created": 3, "generic": 5, "dob": 9}

_ANCHOR_PATTERNS = [
    ("dos", re.compile(r"\b(date of service|dos|service date|visit date|encounter date|date of visit)\b\s*[:\-]?", re.I)),
    ("order", re.compile(r"\b(order date|ordered)\b\s*[:\-]?", re.I)),
    ("collection", re.compile(r"\b(collection date|collected|specimen collected)\b\s*[:\-]?", re.I)),
    ("result", re.compile(r"\b(result date|results date|resulted|resulted on)\b\s*[:\-]?", re.I)),
    ("reported", re.compile(r"\b(reported|reported on)\b\s*[:\-]?", re.I)),
    ("performed", re.compile(r"\b(performed on|procedure date)\b\s*[:\-]?", re.I)),
    ("created", re.compile(r"\b(created|generated|printed|print date|signed|signed on)\b\s*[:\-]?", re.I)),
    ("dob", re.compile(r"\b(dob|d\.o\.b\.|date of birth|born)\b\s*[:\-]?", re.I)),
    ("date", re.compile(r"(?m)^\s*date\s*[:\-]\s*", re.I)),
]


def _safe_parse_date(raw: str) -> Optional[date]:
    try:
        dt = dateparser.parse(raw, dayfirst=False, yearfirst=False, fuzzy=True)
        if not dt:
            return None
        today = datetime.utcnow().date()
        if dt.date() > today.replace(year=today.year + 1):
            return None
        if dt.year < 1900:
            return None
        return dt.date()
    except Exception:
        return None


def _classify_date_kind(left_context: str, right_context: str) -> str:
    if _DOB_RX.search(left_context) or _DOB_RX.search(right_context):
        return "dob"
    for k, rx in _CTX.items():
        if rx.search(left_context) or rx.search(right_context):
            return k
    return "generic"


def extract_dates_from_page(page_text: str) -> List[DateSpan]:
    spans: List[DateSpan] = []
    if not page_text:
        return spans
    for rx in _DATE_REGEXES:
        for m in rx.finditer(page_text):
            raw = m.group(1)
            d = _safe_parse_date(raw)
            if not d:
                continue
            left = page_text[max(0, m.start() - 80):m.start()]
            right = page_text[m.end():min(len(page_text), m.end() + 60)]
            kind = _classify_date_kind(left, right)
            spans.append(DateSpan(raw=raw, iso=d.isoformat(), start=m.start(), end=m.end(), kind=kind))
    uniq: Dict[Tuple[str, int, int, str], DateSpan] = {}
    for s in spans:
        uniq[(s.iso, s.start, s.end, s.kind)] = s
    spans = list(uniq.values())
    spans.sort(key=lambda x: x.start)
    return spans


def extract_date_anchors(page_text: str) -> List[DateAnchor]:
    anchors: List[DateAnchor] = []
    if not page_text:
        return anchors
    for kind, rx in _ANCHOR_PATTERNS:
        for m in rx.finditer(page_text):
            anchors.append(DateAnchor(kind=kind, start=m.start(), end=m.end(), text=m.group(0)))
    anchors.sort(key=lambda x: x.start)
    return anchors


def page_best_dos(page_dates: List[DateSpan]) -> Optional[str]:
    eligible = [d for d in page_dates if d.kind != "dob"]
    if not eligible:
        return None
    dos = [d for d in eligible if d.kind == "dos"]
    if dos:
        dos.sort(key=lambda x: x.start)
        return dos[0].iso
    strong = [d for d in eligible if d.kind in {"performed", "collection", "result", "reported"}]
    if strong:
        strong.sort(key=lambda x: x.start)
        return strong[0].iso
    eligible.sort(key=lambda x: x.start)
    return eligible[0].iso


def fill_page_best_dos_nearest(
    page_best_dos_map: Dict[int, Optional[str]], page_count: int
) -> Dict[int, Optional[str]]:
    """Nearest-neighbor fallback for pages without a date of service."""
    out = dict(page_best_dos_map)
    pages = list(range(1, page_count + 1))
    has = {pn: out.get(pn) for pn in pages}
    known_pages = [pn for pn in pages if has.get(pn)]
    if not known_pages:
        return out
    for pn in pages:
        if out.get(pn):
            continue
        prev = [k for k in known_pages if k < pn]
        nxt = [k for k in known_pages if k > pn]
        prev_p = prev[-1] if prev else None
        next_p = nxt[0] if nxt else None
        if prev_p is None and next_p is None:
            continue
        if prev_p is None:
            out[pn] = out.get(next_p)
        elif next_p is None:
            out[pn] = out.get(prev_p)
        else:
            if (pn - prev_p) <= (next_p - pn):
                out[pn] = out.get(prev_p)
            else:
                out[pn] = out.get(next_p)
    return out


def best_guess_doc_dos(all_page_dates: Dict[int, List[DateSpan]]) -> Optional[str]:
    dos_counts: Dict[str, int] = {}
    strong_counts: Dict[str, int] = {}
    all_counts: Dict[str, int] = {}
    for spans in all_page_dates.values():
        for s in spans:
            if s.kind == "dob":
                continue
            all_counts[s.iso] = all_counts.get(s.iso, 0) + 1
            if s.kind == "dos":
                dos_counts[s.iso] = dos_counts.get(s.iso, 0) + 1
            if s.kind in {"performed", "collection", "result", "reported"}:
                strong_counts[s.iso] = strong_counts.get(s.iso, 0) + 1
    if dos_counts:
        return max(dos_counts.items(), key=lambda x: x[1])[0]
    if strong_counts:
        return max(strong_counts.items(), key=lambda x: x[1])[0]
    if all_counts:
        return max(all_counts.items(), key=lambda x: x[1])[0]
    return None


def _nearest_anchor(anchors: List[DateAnchor], pos: int, max_dist: int = 250) -> Optional[DateAnchor]:
    best = None
    best_d = 10 ** 9
    for a in anchors:
        d = min(abs(a.start - pos), abs(a.end - pos))
        if d < best_d:
            best = a
            best_d = d
    if best and best_d <= max_dist:
        return best
    return None


def attach_dates_to_assertion(
    a: Dict[str, Any],
    page_text: str,
    page_dates: List[DateSpan],
    anchors: List[DateAnchor],
    doc_dos: Optional[str],
    page_dos_val: Optional[str],
) -> None:
    a["doc_best_guess_dos"] = doc_dos
    a["page_best_dos"] = page_dos_val
    if not page_dates:
        a["date_candidates"] = []
        a["inferred_date"] = None
        a["inferred_date_confidence"] = "low"
        a["inferred_date_source"] = "none"
        a["inferred_date_anchor_kind"] = None
        a["inferred_date_doc_match"] = False
        return
    start = int(a.get("char_start", 0))
    cands: List[Dict[str, Any]] = []
    for d in page_dates:
        dist = min(abs(d.start - start), abs(d.end - start))
        cands.append({"iso": d.iso, "raw": d.raw, "kind": d.kind, "distance": dist,
                       "position": "before" if d.end <= start else "after"})
    cands.sort(key=lambda x: (x["distance"], _KIND_PRIORITY.get(x["kind"], 7)))
    a["date_candidates"] = cands[:10]
    blob = f"{a.get('text', '')} {a.get('exact_quote', '')}".lower()
    if _DOB_RX.search(blob) or _AGE_RX.search(blob):
        a["inferred_date"] = None
        a["inferred_date_confidence"] = "low"
        a["inferred_date_source"] = "none"
        a["inferred_date_anchor_kind"] = None
        a["inferred_date_doc_match"] = False
        return
    eligible = [x for x in cands if x["kind"] != "dob"]
    if not eligible:
        a["inferred_date"] = None
        a["inferred_date_confidence"] = "low"
        a["inferred_date_source"] = "none"
        a["inferred_date_anchor_kind"] = None
        a["inferred_date_doc_match"] = False
        return
    anchor = _nearest_anchor(anchors, start, max_dist=300)
    if anchor and anchor.kind != "dob":
        if anchor.kind == "date":
            if any((abs(a2.start - anchor.start) <= 80 and a2.kind == "dob") for a2 in anchors):
                anchor = None
    if anchor and anchor.kind not in {"dob"}:
        anchor_pos = anchor.end
        best_cand = None
        best_score = 10 ** 9
        for x in eligible:
            kind_pen = _KIND_PRIORITY.get(x["kind"], 7) * 25
            score = abs(anchor_pos - start) + x["distance"] + kind_pen
            if score < best_score:
                best_cand = x
                best_score = score
        if best_cand:
            a["inferred_date"] = best_cand["iso"]
            if anchor.kind in {"dos"}:
                a["inferred_date_confidence"] = "high"
            else:
                a["inferred_date_confidence"] = "medium"
            a["inferred_date_source"] = "anchor"
            a["inferred_date_anchor_kind"] = anchor.kind
            a["inferred_date_doc_match"] = bool(doc_dos and best_cand["iso"] == doc_dos)
            if a["inferred_date_doc_match"] and a["inferred_date_confidence"] == "low":
                a["inferred_date_confidence"] = "medium"
            return
    best_cand = eligible[0]
    a["inferred_date"] = best_cand["iso"]
    a["inferred_date_source"] = "proximity"
    a["inferred_date_anchor_kind"] = None
    a["inferred_date_doc_match"] = bool(doc_dos and best_cand["iso"] == doc_dos)
    d_val = int(best_cand["distance"])
    kind = best_cand["kind"]
    if kind in {"dos"} and d_val <= 120:
        conf = "high"
    elif kind in {"performed", "collection", "result", "reported"} and d_val <= 120:
        conf = "medium"
    elif d_val <= 60:
        conf = "medium"
    else:
        conf = "low"
    if a["inferred_date_doc_match"] and conf == "low":
        conf = "medium"
    if page_dos_val and a.get("inferred_date") == page_dos_val and conf == "low":
        conf = "medium"
    a["inferred_date_confidence"] = conf


def is_likely_dob(date_str: str) -> bool:
    if not date_str:
        return False
    try:
        year = int(date_str[:4])
        return year < 2015
    except Exception:
        return False


def compute_effective_date(a: Dict[str, Any], dob_dates: Optional[List[str]] = None) -> None:
    if dob_dates is None:
        dob_dates = []
    plausible_dob_dates = [d for d in dob_dates if is_likely_dob(d)]

    if a.get("inferred_date"):
        eff = a.get("inferred_date")
        if eff and eff in plausible_dob_dates:
            pbd = a.get("page_best_dos")
            if pbd and pbd not in plausible_dob_dates:
                eff = pbd
                a["effective_date_source"] = "page_best_dos"
            else:
                dbd = a.get("doc_best_guess_dos")
                if dbd and dbd not in plausible_dob_dates:
                    eff = dbd
                    a["effective_date_source"] = "doc_best_guess_dos"
                else:
                    a["effective_date_source"] = "inferred_date"
        else:
            a["effective_date_source"] = "inferred_date"
        a["effective_date"] = eff
        return
    if a.get("page_best_dos"):
        a["effective_date"] = a.get("page_best_dos")
        a["effective_date_source"] = "page_best_dos"
        return
    if a.get("doc_best_guess_dos"):
        a["effective_date"] = a.get("doc_best_guess_dos")
        a["effective_date_source"] = "doc_best_guess_dos"
        return
    a["effective_date"] = None
    a["effective_date_source"] = "none"
