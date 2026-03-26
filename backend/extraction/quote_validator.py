"""Quote validation and matching for clinical assertion evidence.

Provides strict, whitespace-normalized, approximate, and token-rescue
matching strategies to verify LLM-produced quotes against page text.
"""

from __future__ import annotations

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _build_ws_normalized_index(text: str) -> Tuple[str, List[int]]:
    norm_chars: List[str] = []
    idx_map: List[int] = []
    in_ws = False
    DASHES = {'\u2010', '\u2011', '\u2012', '\u2013', '\u2014', '\u2015', '\u2212', '\uFE58', '\uFE63', '\uFF0D'}
    QUOTES = {'\u2018': '\'', '\u2019': '\'', '\u201C': '"', '\u201D': '"', '\u00B4': '\''}
    ZERO_WIDTH = {'\u200b', '\u200c', '\u200d', '\ufeff'}

    for i, ch in enumerate(text):
        if ch in ZERO_WIDTH:
            continue
        if ch in QUOTES:
            ch = QUOTES[ch]
        if ch in DASHES:
            ch = '-'
        if ch.isspace():
            if not in_ws:
                norm_chars.append(" ")
                idx_map.append(i)
                in_ws = True
        else:
            norm_chars.append(ch)
            idx_map.append(i)
            in_ws = False
    return "".join(norm_chars), idx_map


def _strict_or_ws_match(
    page_text: str, model_quote: str
) -> Optional[Tuple[int, int, str, bool, float, str]]:
    if not model_quote:
        return None
    idx = page_text.find(model_quote)
    if idx >= 0:
        return idx, idx + len(model_quote), model_quote, False, 1.0, "strict"
    norm_page, idx_map = _build_ws_normalized_index(page_text)
    norm_quote = normalize_ws(model_quote)
    if not norm_quote:
        return None
    idx2 = norm_page.find(norm_quote)
    if idx2 < 0:
        return None
    start_orig = idx_map[idx2]
    end_norm = idx2 + len(norm_quote) - 1
    end_orig = idx_map[end_norm] + 1
    while end_orig < len(page_text) and page_text[end_orig].isspace():
        end_orig += 1
    exact_verbatim = page_text[start_orig:end_orig]
    if normalize_ws(exact_verbatim) != norm_quote:
        return None
    return start_orig, end_orig, exact_verbatim, True, 0.98, "ws_normalized"


def _approximate_quote_match(
    page_text: str, model_quote: str, min_similarity: float = 0.92
) -> Optional[Tuple[int, int, str, float]]:
    mq = normalize_ws(model_quote)
    if not mq or len(mq) < 10 or not page_text:
        return None
    pt = page_text
    norm_page, idx_map = _build_ws_normalized_index(pt)
    best: Tuple[float, Optional[int], Optional[int]] = (0.0, None, None)
    qlen = len(mq)
    win_sizes = [max(20, int(qlen * 0.9)), qlen, int(qlen * 1.1)]
    stride = max(1, int(min(40, max(5, qlen * 0.15))))
    for w in win_sizes:
        if w <= 0:
            continue
        for s in range(0, max(1, len(norm_page) - w + 1), stride):
            cand = norm_page[s:s + w]
            sim = difflib.SequenceMatcher(None, mq, cand).ratio()
            if sim > best[0]:
                best = (sim, s, s + w)
    sim_val, ns, ne = best
    if ns is None or sim_val < min_similarity:
        return None
    start_orig = idx_map[ns]
    end_orig = idx_map[min(ne - 1, len(idx_map) - 1)] + 1
    expand = 60
    start_orig = max(0, start_orig - expand)
    end_orig = min(len(pt), end_orig + expand)
    region = pt[start_orig:end_orig]
    if len(normalize_ws(region)) < 10:
        return None
    if mq in normalize_ws(region):
        m = _strict_or_ws_match(region, model_quote)
        if m:
            rs, re_, verb, _, sim2, _ = m
            return start_orig + rs, start_orig + re_, verb, max(sim_val, sim2)
    lines = [ln for ln in region.splitlines() if ln.strip()]
    best2: Tuple[float, Optional[str]] = (0.0, None)
    for ln in lines:
        ln_n = normalize_ws(ln)
        if not ln_n:
            continue
        sim2 = difflib.SequenceMatcher(None, mq, ln_n).ratio()
        if sim2 > best2[0]:
            best2 = (sim2, ln)
    sim2_val, best_line = best2
    if best_line and sim2_val >= min_similarity:
        li = region.find(best_line)
        if li >= 0:
            return start_orig + li, start_orig + li + len(best_line), best_line, sim2_val
    return None


def _token_rescue_quote(
    page_text: str, model_quote: str, min_token_overlap: float = 0.85
) -> Optional[Tuple[int, int, str, float]]:
    """Token-based rescue for quotes that fail strict/ws/approx matching."""
    mq = normalize_ws(model_quote)
    if not mq or len(mq) > 120:
        return None

    tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", mq) if t]
    exp: List[str] = []
    for t in tokens:
        if t == "sob":
            exp += ["shortness", "breath"]
        if t == "n":
            exp += ["nausea"]
        if t == "v":
            exp += ["vomiting"]
    tokens += exp
    if len(tokens) < 2:
        return None

    if len(tokens) >= 8:
        req = 0.70
    elif len(tokens) >= 5:
        req = 0.78
    else:
        req = min_token_overlap

    lines = [ln for ln in page_text.splitlines() if ln.strip()]
    candidates: List[str] = []
    for i, ln in enumerate(lines):
        candidates.append(ln)
        if i + 1 < len(lines):
            candidates.append(ln + " " + lines[i + 1])

    best_score = 0.0
    best_chunk: Optional[str] = None
    for chunk in candidates:
        chunk_n = normalize_ws(chunk)
        chunk_tokens = set(t.lower() for t in re.findall(r"[A-Za-z0-9]+", chunk_n))
        if not chunk_tokens:
            continue
        hit = sum(1 for t in tokens if t in chunk_tokens)
        score = hit / max(1, len(tokens))
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if not best_chunk or best_score < req:
        return None

    idx = page_text.find(best_chunk if best_chunk in page_text else best_chunk.split(" ", 1)[0])
    if idx < 0:
        first = best_chunk.split(" ", 1)[0]
        idx = page_text.find(first)
        if idx < 0:
            return None

    if best_chunk in page_text:
        verb = best_chunk
        end = idx + len(best_chunk)
    else:
        verb = best_chunk.split(" ", 1)[0]
        end = idx + len(verb)

    return idx, end, verb, float(best_score)


def find_quote_offset(
    page_text: str, model_quote: str, min_similarity: float = 0.92
) -> Optional[Tuple[int, int, str, bool, float, str]]:
    """Find the quote in the page text using multiple matching strategies.

    Returns (char_start, char_end, verbatim_text, repaired, similarity, method) or None.
    """
    m = _strict_or_ws_match(page_text, model_quote)
    if m is not None:
        return m
    am = _approximate_quote_match(page_text, model_quote, min_similarity=min_similarity)
    if am is not None:
        s, e, verb, sim = am
        return s, e, verb, True, float(sim), "approximate"
    tr = _token_rescue_quote(page_text, model_quote)
    if tr is not None:
        s, e, verb, sim = tr
        return s, e, verb, True, float(sim), "token_rescue"
    return None
