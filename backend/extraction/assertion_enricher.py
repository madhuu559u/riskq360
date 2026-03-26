"""Assertion normalization, cleaning, and enrichment.

Handles concept cleaning, text hygiene, medication normalization,
status corrections, admin quarantine, and more.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .quote_validator import normalize_ws


# --- Text cleaning regexes ---
_SNO_PREFIX_RE = re.compile(r"^\s*snomed\s*[:#]?\s*", re.I)
_BRACKET_JUNK_RE = re.compile(r"^\s*\d{4,}\s*\]\s*")
_TRAILING_BRACKET_GARBAGE_RE = re.compile(r"[\]\[]+$")
_LEADING_ENUM_RE = re.compile(r"^\s*\d+\s*[:\-\)]\s*")
_LEADING_BIGINT_RE = re.compile(r"^\s*\d{6,}\s*[\]\)]?\s*")
_LEADING_ICD_LIKE_RE = re.compile(r"^\s*[A-TV-Z][0-9]{2}(?:\.[0-9A-TV-Z]{1,4})?\s*,?\s*", re.I)
_LEADING_ICD_WORD_RE = re.compile(r"^\s*ICD\s*[:#-]?\s*", re.I)
_LEADING_LEGACY_CODE_RE = re.compile(r"^\s*\d{3}(?:\.\d{1,2})?\s*,?\s*")
_TRAILING_PUNCT_RE = re.compile(r"^[,;:\-\s]+|[,;:\-\s]+$")
_TRAILING_DASH9_RE = re.compile(r"(?:\s*,?\s*-\s*9\s*)+$", re.I)
_GARBAGE_CONCEPT_RE = re.compile(r"^(?:[\]\[,\s\-]+|[,\s\-]+)$")
_GARBAGE_CONCEPT_HAS_BRACKETS_RE = re.compile(r"[\[\]]")
_NO_LETTERS_RE = re.compile(r"^[^A-Za-z]*$")
_TOO_MANY_SYMBOLS_RE = re.compile(r"[\[\]\{\}\|]")
_BRACKET_SOUP_RE = re.compile(r"[\[\]].*[\[\]]")
_ICD9_FRAGMENT_RE = re.compile(r"\b-\s*9\b")
_ICD_TAG_RE = re.compile(r"(?:ICD[-\s]?10(?:-CM)?\s*[:#]?\s*)([A-TV-Z]\d{2,3}(?:\.\d{1,4})?)", re.I)

# --- Admin detection ---
_CPT2_RE = re.compile(r"\b(\d{4}F)\b")
_HCPCS_RE = re.compile(r"\b([A-Z]\d{4})\b")
_ADMIN_Z_CODE_RE = re.compile(
    r"\b(Z(?:00\.\d{2}|01\.\d{1,3}|02\.\d{1,3}|11\.\d{1,3}|13\.\d{1,3}|23|68\.\d{1,2}|91\.\d{1,2}))\b", re.I
)
_ADMIN_PHRASES = [
    "encounter for", "screening for", "documentation of",
    "medication reviewed", "patient screened for", "health maintenance",
]

# --- Status correction ---
_NEVER_SMOKER_RE = re.compile(r"\b(never smoker|never smoked|does not smoke|non[-\s]?smoker|non[-\s]?tobacco user|does not use tobacco)\b", re.I)
_NKDA_RE = re.compile(r"\b(NKDA|no known drug allergies|no known allergies)\b", re.I)
_PE_NORMAL_PATTERNS = [
    re.compile(r"\balert\s+and\s+oriented\b", re.I), re.compile(r"\baox\s*\d\b", re.I),
    re.compile(r"\bnormal\s+speech\b", re.I), re.compile(r"\bnormal\s+affect\b", re.I),
    re.compile(r"\bnormal\s+mood\b", re.I), re.compile(r"\bnormal\s+cognitive\b", re.I),
    re.compile(r"\bno\s+acute\s+distress\b", re.I),
]
_DX_SIGNAL = re.compile(r"\b(diagnos|assessment|impression|problem|hx of|history of|chronic|acute)\b", re.I)
_NEG_WORD_RE = re.compile(r"\b(no|denies|without|negative for)\b", re.I)
_PE_SPLIT_RE = re.compile(r"^(?P<pos>.*?)(?:(?:\bwith\b\s+)?\bno\b\s+(?P<neg>.+))$", re.I)

# --- Medication normalization ---
_BRAND_TO_GENERIC = {
    "norvasc": "amlodipine", "zoloft": "sertraline", "synthroid": "levothyroxine",
    "cozaar": "losartan", "hygroton": "chlorthalidone", "lipitor": "atorvastatin",
    "prinivil": "lisinopril", "zestril": "lisinopril",
}
_FORM_WORDS = {"tablet", "tab", "capsule", "cap", "solution", "suspension", "cream", "ointment", "drops", "drop", "spray", "injection", "patch"}
_ROUTE_WORDS = {"po": "oral", "oral": "oral", "by mouth": "oral", "topical": "topical", "subcutaneous": "subcutaneous", "sc": "subcutaneous", "iv": "intravenous", "intravenous": "intravenous", "ophthalmic": "ophthalmic"}
_STRENGTH_RX = re.compile(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|units)\b", re.I)
_FREQ_RX = re.compile(r"\b(qd|daily|bid|tid|qid|qhs|prn|every day|once daily|twice daily|three times daily|at bedtime)\b", re.I)
_ROUTE_RX = re.compile(r"\b(po|oral|by mouth|topical|sc|subcutaneous|iv|intravenous|ophthalmic)\b", re.I)

# --- Evidence rank floors ---
_CATEGORY_RANK_FLOOR = {
    "physical_exam": 2, "vital_sign": 2, "medication": 2, "allergy": 2,
    "social_history": 2, "family_history": 2, "history_present_illness": 2,
    "chief_complaint": 2, "symptom": 2, "screening": 2, "functional_status": 2,
    "review_of_systems": 3, "administrative_code": 3, "assessment": 1,
    "diagnosis": 1, "plan": 1, "lab_result": 1, "lab_order": 1, "referral": 1, "procedure": 1,
}

# --- Canonical concept ---
_CANON_SPACE = re.compile(r"\s+")
_STAGE_RX = re.compile(r"\bstage\s*(\d)\b", re.I)


def normalize_assertion(a: Dict[str, Any]) -> Dict[str, Any]:
    """Set default values for all assertion fields."""
    a = dict(a)
    a.setdefault("negation_trigger", None)
    a.setdefault("allergy_none", False)
    a.setdefault("evidence_rank", 3)
    a.setdefault("subject", "patient")
    a.setdefault("structured", {})
    a.setdefault("codes", [])
    a.setdefault("icd_codes", [])
    a.setdefault("icd9_codes", [])
    a.setdefault("cpt2_codes", [])
    a.setdefault("hcpcs_codes", [])
    a.setdefault("quote_repaired", False)
    a.setdefault("quote_similarity", None)
    a.setdefault("quote_match_method", "strict")
    a.setdefault("date_candidates", [])
    a.setdefault("inferred_date", None)
    a.setdefault("inferred_date_confidence", "low")
    a.setdefault("inferred_date_source", "none")
    a.setdefault("inferred_date_anchor_kind", None)
    a.setdefault("inferred_date_doc_match", False)
    a.setdefault("doc_best_guess_dos", None)
    a.setdefault("page_best_dos", None)
    a.setdefault("medication_normalized", None)
    a.setdefault("medication_dedupe_key", None)
    a.setdefault("is_hcc_candidate", False)
    a.setdefault("is_hedis_evidence", False)
    a.setdefault("icd_tags_near_quote", [])
    a.setdefault("icd_codes_near_quote", [])
    a.setdefault("clean_text", None)
    a.setdefault("effective_date", None)
    a.setdefault("effective_date_source", None)
    a.setdefault("is_hedis_evidence_effective", False)
    a.setdefault("condition_group_key", None)
    a.setdefault("condition_group_id", None)
    a.setdefault("is_condition_best_evidence", False)
    a.setdefault("is_payable_hcc_candidate", False)
    a.setdefault("payable_hcc_exclusion_reason", None)
    a.setdefault("page_best_dos_nn", None)
    a.setdefault("effective_date_used_nn", False)
    a.setdefault("is_payable_ra_candidate", False)
    a.setdefault("ra_candidate_exclusion_reason", None)
    a.setdefault("canonical_concept", None)
    a.setdefault("canonical_concept_method", None)
    a.setdefault("condition_group_key_v3", None)
    a.setdefault("condition_group_id_v3", None)
    a.setdefault("is_condition_best_evidence_v3", False)
    a.setdefault("condition_group_key_v2", None)
    a.setdefault("condition_group_id_v2", None)
    a.setdefault("is_condition_best_evidence_v2", False)
    return a


def clean_concept_text(s: str) -> str:
    s = normalize_ws(s)
    s = _SNO_PREFIX_RE.sub("", s)
    s = _BRACKET_JUNK_RE.sub("", s)
    s = _LEADING_ICD_WORD_RE.sub("", s)
    s = _LEADING_ENUM_RE.sub("", s)
    s = _LEADING_BIGINT_RE.sub("", s)
    s = _LEADING_ICD_LIKE_RE.sub("", s)
    s = _LEADING_LEGACY_CODE_RE.sub("", s)
    s = _TRAILING_PUNCT_RE.sub("", s)
    s = re.sub(r"^[\]\[,\s]+", "", s)
    s = re.sub(r"[\[\]]", " ", s)
    s = normalize_ws(s)
    s = _TRAILING_PUNCT_RE.sub("", s)
    s = _TRAILING_BRACKET_GARBAGE_RE.sub("", s).strip()
    s = re.sub(r"\bSNOMED\s*[:#]?\s*\d+\]?\s*", "", s, flags=re.I).strip()
    s = re.sub(r"^(diagnosis|assessment|problem list|problem|dx|impression)\s*[:\-]\s*", "", s, flags=re.I).strip()
    s = re.sub(r"^[\-•\*]+\s*", "", s).strip()
    s = s.rstrip(".;: ")
    s = normalize_ws(s)
    return s


def clean_statement_text(s: str) -> str:
    s = normalize_ws(s)
    s = _LEADING_ENUM_RE.sub("", s)
    s = _LEADING_BIGINT_RE.sub("", s)
    s = _LEADING_ICD_LIKE_RE.sub("", s)
    s = _LEADING_LEGACY_CODE_RE.sub("", s)
    s = _TRAILING_PUNCT_RE.sub("", s)
    s = re.sub(r"^[\]\[,\s]+", "", s)
    s = re.sub(r"[\[\]]", " ", s)
    s = normalize_ws(s)
    s = _TRAILING_PUNCT_RE.sub("", s)
    s = re.sub(r"\bSNOMED\s*[:#]?\s*\d+\]?\s*", "", s, flags=re.I)
    s = re.sub(r"^\s*\d{4,}\]\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonicalize_concept(concept: str, icd_codes: List[Dict[str, str]]) -> Tuple[str, str]:
    c = normalize_ws((concept or "")).lower()
    c = re.sub(r"[\[\]\(\)]", " ", c)
    c = _CANON_SPACE.sub(" ", c).strip()
    icds = {(x.get("code", "") or "").upper() for x in (icd_codes or []) if x.get("code")}
    if icds.intersection({"N18.30", "N18.31", "N18.32"}):
        return ("chronic kidney disease stage 3", "icd_ckd_stage3")
    if any(x.startswith("E11.4") for x in icds):
        return ("type 2 diabetes mellitus with diabetic neuropathy", "icd_t2dm_neuropathy")
    if any(x.startswith("E11.6") for x in icds):
        return ("type 2 diabetes mellitus with complication", "icd_t2dm_complication")
    if "I10" in icds:
        return ("essential hypertension", "icd_htn")
    if "E03.9" in icds:
        return ("hypothyroidism", "icd_hypothyroidism")
    if "E78.2" in icds:
        return ("mixed hyperlipidemia", "icd_mixed_hld")
    if "E78.5" in icds:
        return ("dyslipidemia", "icd_dyslipidemia")
    if "D64.9" in icds:
        return ("anemia", "icd_anemia")
    c = c.replace("type 2 dm", "type 2 diabetes mellitus")
    c = c.replace("t2dm", "type 2 diabetes mellitus")
    c = c.replace("dm2", "type 2 diabetes mellitus")
    if "chronic kidney disease" in c:
        m = _STAGE_RX.search(c)
        if m and m.group(1) == "3":
            return ("chronic kidney disease stage 3", "text_ckd_stage3")
    return (c if c else concept, "none")


def is_garbage_concept_str(s: Optional[str]) -> bool:
    if s is None:
        return True
    t = normalize_ws(str(s))
    if not t:
        return True
    if _NO_LETTERS_RE.match(t):
        return True
    if _GARBAGE_CONCEPT_RE.match(t):
        return True
    sym = len(re.sub(r"[A-Za-z0-9\s]", "", t))
    if sym / max(1, len(t)) > 0.45:
        return True
    if _TOO_MANY_SYMBOLS_RE.search(t) and sym / max(1, len(t)) > 0.25:
        return True
    if _BRACKET_SOUP_RE.search(t):
        return True
    if _ICD9_FRAGMENT_RE.search(t):
        return True
    return False


def is_garbage_clean_text(s: Optional[str]) -> bool:
    if s is None:
        return True
    t = normalize_ws(str(s))
    if not t:
        return True
    if any(x in t for x in ["[ICD", "ICD-9", "SNOMED", "]]", "], ["]):
        return True
    sym = len(re.sub(r"[A-Za-z0-9\s]", "", t))
    if sym / max(1, len(t)) > 0.40:
        return True
    return False


def is_text_soup(s: Optional[str]) -> bool:
    if s is None:
        return True
    t = normalize_ws(str(s))
    if not t:
        return True
    if re.match(r"^[^A-Za-z]*$", t):
        return True
    if _LEADING_ENUM_RE.match(t) or _LEADING_BIGINT_RE.match(t) or _LEADING_LEGACY_CODE_RE.match(t):
        return True
    if _LEADING_ICD_LIKE_RE.match(t):
        return True
    if re.search(r"\bICD-?\s*9\b|\bICD-?\s*10\b|\bSNOMED\b", t, flags=re.I):
        return True
    sym = len(re.sub(r"[A-Za-z0-9\s]", "", t))
    if sym / max(1, len(t)) > 0.40:
        return True
    return False


def extract_label_from_evidence(a: Dict[str, Any]) -> Optional[str]:
    q = a.get("exact_quote") or a.get("text") or ""
    if not q:
        return None
    s = normalize_ws(q)
    s = re.sub(r"\[[^\]]{0,80}\]", " ", s)
    s = re.sub(r"\b(ICD-?10|ICD|SNOMED)\b\s*[:#]?\s*", " ", s, flags=re.I)
    s = re.sub(r"\b[A-TV-Z][0-9]{2}(?:\.[0-9A-TV-Z]{1,4})?\b", " ", s, flags=re.I)
    s = re.sub(r"\b\d{3}(?:\.\d{1,2})?\b", " ", s)
    s = _LEADING_ENUM_RE.sub("", s)
    s = _LEADING_BIGINT_RE.sub("", s)
    s = normalize_ws(s)
    if re.search(r"\bdiagnosis\b\s*[:\-]", s, flags=re.I):
        s = re.split(r"\bdiagnosis\b\s*[:\-]", s, flags=re.I)[-1].strip()
    s = re.split(r"\b(CPT|HCPCS)\b", s, flags=re.I)[0].strip()
    if len(s) > 140:
        s = s[:140].rsplit(" ", 1)[0].strip()
    s = clean_concept_text(s)
    if not s:
        return None
    if _LEADING_ICD_LIKE_RE.match(s) or _LEADING_LEGACY_CODE_RE.match(s):
        return None
    return s


def sanitize_dx_concept(a: Dict[str, Any]) -> None:
    cat = (a.get("category") or "").lower()
    if cat not in {"diagnosis", "assessment"}:
        return
    concept = clean_concept_text(a.get("concept", ""))
    concept = normalize_ws(concept)
    if is_garbage_concept_str(concept) or _LEADING_ICD_LIKE_RE.match(concept) or _LEADING_LEGACY_CODE_RE.match(concept):
        rec = extract_label_from_evidence(a)
        if rec:
            concept = clean_concept_text(rec)
    if is_garbage_concept_str(concept):
        icds = [c.get("code", "").upper() for c in (a.get("icd_codes") or []) if c.get("code")]
        if icds:
            concept = f"diagnosis code {icds[0].upper()}"
        else:
            concept = "diagnosis"
    concept = _TRAILING_DASH9_RE.sub("", concept)
    concept = normalize_ws(concept)
    a["concept"] = concept.lower()
    can, method = canonicalize_concept(a.get("concept", ""), a.get("icd_codes") or [])
    if is_garbage_concept_str(can):
        can = a.get("concept", "")
        method = "fallback_to_concept"
    a["canonical_concept"] = normalize_ws(can).lower()
    a["canonical_concept_method"] = method
    a["clean_text"] = clean_statement_text(a.get("concept", "") + ".")
    a["text"] = a.get("clean_text")
    if is_garbage_clean_text(a.get("clean_text")):
        a["clean_text"] = clean_statement_text(concept + ".")
    if (is_text_soup(a.get("text"))
        or _LEADING_BIGINT_RE.match(normalize_ws(str(a.get("text") or "")))
        or _LEADING_LEGACY_CODE_RE.match(normalize_ws(str(a.get("text") or "")))
        or _LEADING_ICD_LIKE_RE.match(normalize_ws(str(a.get("text") or "")))) and not is_text_soup(a.get("clean_text")):
        a["text"] = a.get("clean_text")


def is_administrative(concept: str, text: str, quote: str) -> bool:
    combined = f"{concept} {text} {quote}".lower()
    if _CPT2_RE.search(combined) or _HCPCS_RE.search(combined):
        return True
    z = _ADMIN_Z_CODE_RE.search(combined.upper())
    if z and z.group(1).startswith("Z68"):
        return True
    for ph in _ADMIN_PHRASES:
        if ph in combined:
            return True
    return False


def force_admin_quarantine(a: Dict[str, Any]) -> None:
    blob = f"{a.get('concept', '')} {a.get('text', '')} {a.get('exact_quote', '')}".lower()
    if _CPT2_RE.search(blob) or _HCPCS_RE.search(blob):
        if "most recent systolic" in blob or "most recent diastolic" in blob:
            a["category"] = "administrative_code"
            return
        if "most recent" in blob or "documentation" in blob or "screen" in blob:
            a["category"] = "administrative_code"
            return


def apply_status_corrections(a: Dict[str, Any]) -> None:
    q = (a.get("exact_quote") or "").lower()
    if "phq" in q and "score" in q:
        a["status"] = "active"
        if a.get("category") in (None, "", "mental_health"):
            a["category"] = "screening"
        m = re.search(r"\bscore\s*=\s*(\d+)\b", q)
        if m:
            a.setdefault("structured", {})
            a["structured"]["score_name"] = "PHQ-9"
            a["structured"]["score_value"] = int(m.group(1))
    if "fall risk" in q and ("low risk" in q or "no fall risk" in q or "at low risk" in q):
        a["status"] = "active"
        if a.get("category") in (None, "", "screening"):
            a["category"] = "functional_status"
        a.setdefault("structured", {})
        a["structured"]["risk_level"] = "low"
    if "not present-" in q:
        a["status"] = "negated"
        a["category"] = "review_of_systems"
        a["evidence_rank"] = 3


def normalize_tobacco(a: Dict[str, Any]) -> None:
    q = a.get("exact_quote", "") or ""
    if _NEVER_SMOKER_RE.search(q):
        a["category"] = "social_history"
        a["concept"] = "tobacco use"
        a["status"] = "negated"
        a["subject"] = "patient"
        a["text"] = "Tobacco use denied (never smoker)."
        a["negation_trigger"] = "never"


def normalize_allergies(a: Dict[str, Any]) -> None:
    q = a.get("exact_quote", "") or ""
    if bool(a.get("allergy_none")) or _NKDA_RE.search(q):
        a["category"] = "allergy"
        a["concept"] = "drug allergy"
        a["status"] = "negated"
        a["subject"] = "patient"
        a["allergy_none"] = True
        a["text"] = "No known drug allergies (NKDA)."


def sanitize_diagnosis_category(a: Dict[str, Any]) -> None:
    cat = (a.get("category") or "")
    if cat not in {"diagnosis", "assessment"}:
        return
    blob = f"{a.get('text', '')} {a.get('exact_quote', '')}"
    if a.get("icd_codes"):
        return
    if _DX_SIGNAL.search(blob):
        return
    for rx in _PE_NORMAL_PATTERNS:
        if rx.search(blob):
            if any(k in blob.lower() for k in ["affect", "speech", "cognitive", "mood"]):
                a["category"] = "mental_health"
            else:
                a["category"] = "physical_exam"
            return


def enforce_evidence_rank(a: Dict[str, Any]) -> None:
    floor = _CATEGORY_RANK_FLOOR.get((a.get("category") or "").strip())
    if floor is None:
        return
    try:
        cur = int(a.get("evidence_rank", 3))
    except Exception:
        cur = 3
    a["evidence_rank"] = max(cur, int(floor))


def split_mixed_polarity_physical_exam(a: Dict[str, Any], page_text: str) -> List[Dict[str, Any]]:
    if (a.get("category") or "") != "physical_exam":
        return [a]
    quote = (a.get("exact_quote") or "").strip()
    if not quote or not _NEG_WORD_RE.search(quote):
        return [a]
    m = _PE_SPLIT_RE.match(quote)
    if not m:
        return [a]
    idx_no = quote.lower().find("no ")
    if idx_no < 0:
        return [a]
    pos_q = quote[:idx_no].strip().rstrip(",;: ")
    neg_q = quote[idx_no:].strip()
    if not pos_q or not neg_q:
        return [a]
    if page_text.find(pos_q) < 0 or page_text.find(neg_q) < 0:
        return [a]
    a_pos = dict(a)
    a_pos["status"] = "active"
    a_pos["exact_quote"] = pos_q
    a_pos["text"] = normalize_ws(pos_q)
    a_neg = dict(a)
    a_neg["status"] = "negated"
    a_neg["exact_quote"] = neg_q
    a_neg["negation_trigger"] = "no"
    a_neg["text"] = normalize_ws(neg_q)
    return [a_pos, a_neg]


def normalize_medication_string(s: str) -> Dict[str, Any]:
    raw = normalize_ws((s or "").lower())
    out: Dict[str, Any] = {"ingredient": None, "normalized_name": None, "brand_name": None, "route": None, "strength": None, "frequency": None}
    rm = _ROUTE_RX.search(raw)
    if rm:
        out["route"] = _ROUTE_WORDS.get(rm.group(1).lower(), rm.group(1).lower())
    sm = _STRENGTH_RX.search(raw)
    if sm:
        out["strength"] = f"{sm.group(1)} {sm.group(2).lower()}"
    fm = _FREQ_RX.search(raw)
    if fm:
        out["frequency"] = fm.group(1).lower()
    tokens = [t for t in re.split(r"[\s,;/()]+", raw) if t]
    tokens_wo = [t for t in tokens if t not in _FORM_WORDS and t not in _ROUTE_WORDS and t not in _ROUTE_WORDS.values()]
    brand = tokens_wo[0] if tokens_wo else None
    if brand and brand in _BRAND_TO_GENERIC:
        out["brand_name"] = brand
        out["ingredient"] = _BRAND_TO_GENERIC[brand]
        out["normalized_name"] = out["ingredient"]
        return out
    if tokens_wo:
        out["ingredient"] = tokens_wo[0]
        out["normalized_name"] = tokens_wo[0]
    return out


def attach_medication_normalization(a: Dict[str, Any]) -> None:
    if (a.get("category") or "") != "medication":
        return
    blob = " ".join([str(a.get("concept", "")), str(a.get("text", "")), str(a.get("exact_quote", ""))])
    nm = normalize_medication_string(blob)
    a["medication_normalized"] = nm
    ing = nm.get("ingredient") or a.get("concept") or ""
    a["medication_dedupe_key"] = normalize_ws(str(ing).lower())


def normalize_concept(a: Dict[str, Any]) -> None:
    concept = (a.get("concept") or "").strip() or (a.get("text") or "").strip()
    concept = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFE58\uFE63\uFF0D]", "-", concept)
    concept = clean_concept_text(concept)
    is_garbage = bool(_GARBAGE_CONCEPT_RE.match(concept)) or (
        bool(_GARBAGE_CONCEPT_HAS_BRACKETS_RE.search(concept)) and len(re.sub(r"[A-Za-z]", "", concept)) / max(1, len(concept)) > 0.6
    )
    if (not concept) or is_garbage or _LEADING_ICD_LIKE_RE.match(concept) or _LEADING_LEGACY_CODE_RE.match(concept):
        rec = extract_label_from_evidence(a)
        if rec:
            concept = rec
    a["concept"] = normalize_ws(concept).lower()


def attach_canonical_concept(a: Dict[str, Any]) -> None:
    can, method = canonicalize_concept(a.get("concept", ""), a.get("icd_codes") or [])
    a["canonical_concept"] = can
    a["canonical_concept_method"] = method
