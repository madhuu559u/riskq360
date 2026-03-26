"""TF-IDF + embedding ICD-10 retrieval system.

Adapted from ra-training-data-factory's retrieval modules.
Retrieves candidate ICD-10-CM codes by matching clinical text to ICD descriptions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog

from config.settings import MLSettings
from core.exceptions import ICDRetrievalError

logger = structlog.get_logger(__name__)

# Medical abbreviation expansions
MEDICAL_ABBREVIATIONS = {
    "dm": "diabetes mellitus",
    "htn": "hypertension",
    "chf": "congestive heart failure",
    "copd": "chronic obstructive pulmonary disease",
    "ckd": "chronic kidney disease",
    "cad": "coronary artery disease",
    "afib": "atrial fibrillation",
    "mi": "myocardial infarction",
    "cva": "cerebrovascular accident stroke",
    "dvt": "deep vein thrombosis",
    "pe": "pulmonary embolism",
    "esrd": "end stage renal disease",
    "ra": "rheumatoid arthritis",
    "sle": "systemic lupus erythematosus",
    "ms": "multiple sclerosis",
    "hf": "heart failure",
    "pvd": "peripheral vascular disease",
    "pad": "peripheral arterial disease",
    "bph": "benign prostatic hyperplasia",
    "gerd": "gastroesophageal reflux disease",
    "osa": "obstructive sleep apnea",
    "tia": "transient ischemic attack",
}


class ICDRetriever:
    """Retrieves candidate ICD-10-CM codes using TF-IDF similarity.

    Searches over 7,903 ICD-10-CM codes using cosine similarity
    between clinical text and ICD code descriptions.
    """

    def __init__(self, ml_settings: MLSettings) -> None:
        self.settings = ml_settings
        self._vectorizer = None
        self._tfidf_matrix = None
        self._icd_catalog: List[Dict[str, str]] = []
        self._hcc_to_icds: Dict[str, List[str]] = {}
        self._is_loaded = False

    def _load(self) -> None:
        """Lazy-load the TF-IDF vectorizer and ICD catalog."""
        if self._is_loaded:
            return

        try:
            import joblib

            # Load TF-IDF vectorizer
            vec_path = Path(self.settings.tfidf_vectorizer_path)
            if vec_path.exists():
                self._vectorizer = joblib.load(str(vec_path))
                logger.info("retrieval.vectorizer_loaded", path=str(vec_path))
            else:
                logger.warning("retrieval.vectorizer_not_found, building from catalog")
                self._build_vectorizer()

            # Load ICD catalog
            catalog_path = Path(self.settings.icd_catalog_path)
            if catalog_path.exists():
                with open(catalog_path, encoding="utf-8") as f:
                    self._icd_catalog = json.load(f)
                logger.info("retrieval.catalog_loaded", codes=len(self._icd_catalog))
            else:
                logger.warning("retrieval.catalog_not_found", path=str(catalog_path))
                self._icd_catalog = []

            # Build HCC → ICD reverse index
            for entry in self._icd_catalog:
                for hcc in entry.get("mapped_hccs", []):
                    self._hcc_to_icds.setdefault(hcc, []).append(entry["code"])

            # Build TF-IDF matrix from catalog descriptions
            if self._vectorizer and self._icd_catalog:
                descriptions = [
                    self._expand_abbreviations(e.get("description", "") + " " + " ".join(e.get("synonyms", [])))
                    for e in self._icd_catalog
                ]
                self._tfidf_matrix = self._vectorizer.transform(descriptions)

            self._is_loaded = True

        except Exception as e:
            raise ICDRetrievalError(f"Failed to load ICD retrieval system: {e}")

    def _build_vectorizer(self) -> None:
        """Build a TF-IDF vectorizer from scratch if pre-trained one not available."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            max_features=50000,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )

    def retrieve(
        self,
        text: str,
        predicted_hccs: List[str],
        llm_icds: List[str] | None = None,
        threshold: float = 0.35,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve candidate ICD-10 codes using dual-source approach.

        Path 1 (CMS Crosswalk): All ICDs that map to each predicted HCC.
        Path 2 (TF-IDF): ICDs similar to clinical text.

        Merges, deduplicates, and ranks by combined relevance score.
        """
        try:
            self._load()
        except ICDRetrievalError:
            logger.warning("retrieval.system_unavailable")
            return []

        candidates: Dict[str, Dict[str, Any]] = {}

        # Path 1: CMS crosswalk — ICDs for each predicted HCC
        for hcc in predicted_hccs:
            hcc_upper = hcc.upper()
            mapped_icds = self._hcc_to_icds.get(hcc_upper, [])
            for icd_code in mapped_icds:
                if icd_code not in candidates:
                    entry = self._find_catalog_entry(icd_code)
                    candidates[icd_code] = {
                        "icd10_code": icd_code,
                        "description": entry.get("description", "") if entry else "",
                        "source_hcc": hcc_upper,
                        "source": "cms_crosswalk",
                        "similarity_score": 0.0,
                        "relevance_score": 0.5,  # base score for crosswalk hits
                    }

        # Path 2: TF-IDF retrieval — match text to ICD descriptions
        if self._vectorizer and self._tfidf_matrix is not None:
            tfidf_candidates = self._tfidf_search(text, threshold, top_k * 3)
            for tc in tfidf_candidates:
                code = tc["icd10_code"]
                if code in candidates:
                    # Boost existing candidate
                    candidates[code]["similarity_score"] = tc["similarity_score"]
                    candidates[code]["relevance_score"] += tc["similarity_score"]
                    candidates[code]["source"] = "cms_crosswalk+tfidf"
                else:
                    candidates[code] = tc

        # Path 3: Include LLM-extracted ICDs
        if llm_icds:
            for icd_code in llm_icds:
                if icd_code and icd_code not in candidates:
                    entry = self._find_catalog_entry(icd_code)
                    candidates[icd_code] = {
                        "icd10_code": icd_code,
                        "description": entry.get("description", "") if entry else "",
                        "source_hcc": "",
                        "source": "llm",
                        "similarity_score": 0.0,
                        "relevance_score": 0.7,  # LLM extraction gets moderate base score
                    }

        # Sort by relevance and return top-k
        result = sorted(candidates.values(), key=lambda x: x["relevance_score"], reverse=True)
        return result[:top_k * len(predicted_hccs) if predicted_hccs else top_k]

    def _tfidf_search(self, text: str, threshold: float, top_k: int) -> List[Dict[str, Any]]:
        """Search ICD catalog using TF-IDF cosine similarity."""
        from sklearn.metrics.pairwise import cosine_similarity

        expanded = self._expand_abbreviations(text.lower())
        query_vec = self._vectorizer.transform([expanded])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Get top-k above threshold
        results = []
        top_indices = similarities.argsort()[::-1][:top_k]
        for idx in top_indices:
            score = float(similarities[idx])
            if score < threshold:
                break
            entry = self._icd_catalog[idx]
            results.append({
                "icd10_code": entry["code"],
                "description": entry.get("description", ""),
                "source_hcc": "",
                "source": "tfidf",
                "similarity_score": round(score, 4),
                "relevance_score": round(score, 4),
            })

        return results

    def _find_catalog_entry(self, code: str) -> Optional[Dict]:
        """Find an ICD catalog entry by code."""
        for entry in self._icd_catalog:
            if entry["code"] == code:
                return entry
        return None

    @staticmethod
    def _expand_abbreviations(text: str) -> str:
        """Expand medical abbreviations in text."""
        words = text.lower().split()
        expanded = []
        for w in words:
            clean = re.sub(r"[^\w]", "", w)
            if clean in MEDICAL_ABBREVIATIONS:
                expanded.append(MEDICAL_ABBREVIATIONS[clean])
            else:
                expanded.append(w)
        return " ".join(expanded)
