"""Coding Helper Service — BM25 + fuzzy ICD-10 code suggestion engine.

Provides AJAX-like ICD-10 code suggestions for abstractors/coders.
Indexes the V28 ICD-10 catalog and supports query-time BM25 ranking,
prefix matching, and code-based lookups.
"""
from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from config.settings import PROJECT_ROOT


# BM25 tuning
K1 = 1.5
B = 0.75
MAX_RESULTS = 20


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into tokens."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) >= 2]


class _ICDEntry:
    __slots__ = ("icd10_code", "description", "hcc_code", "hcc_label", "is_payment_hcc", "tokens")

    def __init__(self, icd10_code: str, description: str, hcc_code: str, hcc_label: str, is_payment: bool):
        self.icd10_code = icd10_code
        self.description = description
        self.hcc_code = hcc_code
        self.hcc_label = hcc_label
        self.is_payment_hcc = is_payment
        self.tokens = _tokenize(f"{description} {hcc_label}")


class CodingHelperService:
    """In-memory BM25 index over the V28 ICD-10 catalog for fast code suggestions."""

    _instance: Optional[CodingHelperService] = None
    _entries: list[_ICDEntry]
    _inverted: dict[str, list[int]]
    _doc_len: list[int]
    _avg_dl: float
    _df: dict[str, int]
    _loaded: bool

    def __new__(cls) -> CodingHelperService:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._entries = []
        self._inverted = defaultdict(list)
        self._doc_len = []
        self._df = defaultdict(int)

        # Load from CSV
        csv_path = PROJECT_ROOT / "decisioning" / "reference" / "v28_icd_hcc_mappings.csv"
        if csv_path.exists():
            self._load_csv(csv_path)
        else:
            # Fallback: try JSON catalog
            json_path = PROJECT_ROOT / "ml_engine" / "models" / "icd10_catalog.json"
            if json_path.exists():
                self._load_json(json_path)

        # Build index
        total_dl = 0
        for idx, entry in enumerate(self._entries):
            dl = len(entry.tokens)
            self._doc_len.append(dl)
            total_dl += dl
            seen: set[str] = set()
            for tok in entry.tokens:
                self._inverted[tok].append(idx)
                if tok not in seen:
                    self._df[tok] += 1
                    seen.add(tok)

        self._avg_dl = total_dl / max(len(self._entries), 1)
        self._loaded = True

    def _load_csv(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                icd = (row.get("icd10_code") or row.get("ICD-10-CM Code") or "").strip()
                desc = (row.get("cc_label") or row.get("ICD-10-CM Code Description") or "").strip()
                hcc = (row.get("hcc_code") or row.get("CMS-HCC Model Category V28") or "").strip()
                hcc_label = (row.get("cc_label") or "").strip()
                is_pay = str(row.get("is_payment_hcc", "1")).strip().lower() in {"1", "true", "yes"}
                if icd:
                    self._entries.append(_ICDEntry(icd, desc, hcc, hcc_label, is_pay))

    def _load_json(self, path: Path) -> None:
        import json
        with open(path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        if isinstance(catalog, dict):
            for code, info in catalog.items():
                desc = info.get("description", "") if isinstance(info, dict) else str(info)
                hcc = info.get("hcc", "") if isinstance(info, dict) else ""
                self._entries.append(_ICDEntry(code, desc, hcc, "", True))
        elif isinstance(catalog, list):
            for item in catalog:
                code = item.get("code", "")
                desc = item.get("description", "")
                hcc = item.get("hcc", "")
                self._entries.append(_ICDEntry(code, desc, hcc, "", True))

    def suggest(
        self, query: str, limit: int = MAX_RESULTS, payment_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Suggest ICD-10 codes for a text query using BM25 ranking.

        Args:
            query: Clinical text or description to search.
            limit: Max results to return.
            payment_only: Only return codes that map to payable HCCs.

        Returns:
            List of {icd10_code, description, hcc_code, hcc_label, score, is_payment_hcc}
        """
        self._ensure_loaded()

        # Direct code lookup (if query looks like an ICD code)
        code_upper = query.strip().upper().replace(" ", "")
        if re.match(r"^[A-Z]\d{2}", code_upper):
            return self._code_lookup(code_upper, limit, payment_only)

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        n = len(self._entries)
        scores: dict[int, float] = defaultdict(float)

        for qt in query_tokens:
            # Exact token match
            if qt in self._inverted:
                df = self._df.get(qt, 0)
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
                for idx in self._inverted[qt]:
                    tf = self._entries[idx].tokens.count(qt)
                    dl = self._doc_len[idx]
                    score = idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * dl / self._avg_dl))
                    scores[idx] += score
            else:
                # Prefix match fallback
                for token, postings in self._inverted.items():
                    if token.startswith(qt) or qt.startswith(token):
                        df = self._df.get(token, 0)
                        idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0) * 0.5  # discount
                        for idx in postings:
                            scores[idx] += idf * 0.3

        # Rank
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results: list[dict] = []
        for idx, score in ranked:
            entry = self._entries[idx]
            if payment_only and not entry.is_payment_hcc:
                continue
            results.append({
                "icd10_code": entry.icd10_code,
                "description": entry.description,
                "hcc_code": entry.hcc_code,
                "hcc_label": entry.hcc_label,
                "is_payment_hcc": entry.is_payment_hcc,
                "score": round(score, 4),
            })
            if len(results) >= limit:
                break

        return results

    def _code_lookup(self, code_prefix: str, limit: int, payment_only: bool) -> list[dict]:
        """Direct ICD code prefix lookup."""
        results: list[dict] = []
        code_no_dot = code_prefix.replace(".", "")
        for entry in self._entries:
            entry_no_dot = entry.icd10_code.replace(".", "").upper()
            if entry_no_dot.startswith(code_no_dot):
                if payment_only and not entry.is_payment_hcc:
                    continue
                # Exact match gets highest score
                score = 10.0 if entry_no_dot == code_no_dot else 5.0
                results.append({
                    "icd10_code": entry.icd10_code,
                    "description": entry.description,
                    "hcc_code": entry.hcc_code,
                    "hcc_label": entry.hcc_label,
                    "is_payment_hcc": entry.is_payment_hcc,
                    "score": score,
                })
                if len(results) >= limit:
                    break
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def get_entry_count(self) -> int:
        """Return the number of indexed ICD entries."""
        self._ensure_loaded()
        return len(self._entries)
