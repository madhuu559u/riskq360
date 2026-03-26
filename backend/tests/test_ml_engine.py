"""Tests for the ML engine layer — negation detection, ICD retrieval, span proposer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml_engine.negation_detector import NegationDetector


# ── Negation Detector Tests ──────────────────────────────────────────────────

class TestNegationDetector:
    def setup_method(self) -> None:
        self.detector = NegationDetector()

    def test_active_diagnosis(self) -> None:
        result = self.detector.detect(
            "type 2 diabetes mellitus",
            "Patient has type 2 diabetes mellitus.",
        )
        assert result.polarity == "active"

    def test_negated_diagnosis(self) -> None:
        result = self.detector.detect(
            "peripheral neuropathy",
            "No evidence of peripheral neuropathy.",
        )
        assert result.polarity == "negated"

    def test_denied_diagnosis(self) -> None:
        result = self.detector.detect(
            "chest pain",
            "Patient denies chest pain or shortness of breath.",
        )
        assert result.polarity == "negated"

    def test_historical_diagnosis(self) -> None:
        result = self.detector.detect(
            "stroke",
            "History of stroke in 2018.",
        )
        assert result.polarity == "historical"

    def test_family_history(self) -> None:
        result = self.detector.detect(
            "breast cancer",
            "Mother had breast cancer at age 62.",
        )
        assert result.polarity == "family_history"

    def test_uncertain_diagnosis(self) -> None:
        result = self.detector.detect(
            "congestive heart failure",
            "Possible congestive heart failure.",
        )
        assert result.polarity == "uncertain"

    def test_resolved_diagnosis(self) -> None:
        result = self.detector.detect(
            "diabetes",
            "Diabetes resolved after pancreas transplant.",
        )
        assert result.polarity == "resolved"

    def test_ruled_out(self) -> None:
        result = self.detector.detect(
            "pulmonary embolism",
            "Pulmonary embolism was ruled out by CT angiography.",
        )
        assert result.polarity == "negated"

    def test_result_fields(self) -> None:
        result = self.detector.detect(
            "hypertension",
            "Patient has hypertension.",
        )
        assert hasattr(result, "polarity")
        assert hasattr(result, "triggers")
        assert result.polarity == "active"

    def test_batch_detect(self) -> None:
        cases = [
            ("diabetes", "Patient has diabetes."),
            ("cancer", "No evidence of cancer."),
            ("MI", "History of MI in 2020."),
        ]
        results = [
            self.detector.detect(term, sent)
            for term, sent in cases
        ]
        assert results[0].polarity == "active"
        assert results[1].polarity == "negated"
        assert results[2].polarity == "historical"


# ── ICD Retriever Tests ──────────────────────────────────────────────────────

class TestICDRetriever:
    def test_import(self) -> None:
        from ml_engine.icd_retriever import ICDRetriever
        assert ICDRetriever is not None

    def test_instantiate(self) -> None:
        from ml_engine.icd_retriever import ICDRetriever
        from config.settings import get_settings
        settings = get_settings()
        retriever = ICDRetriever(settings.ml)
        assert retriever is not None

    def test_retrieve_by_description(self) -> None:
        from ml_engine.icd_retriever import ICDRetriever
        from config.settings import get_settings
        settings = get_settings()

        retriever = ICDRetriever(settings.ml)
        try:
            retriever._load()
        except Exception:
            pytest.skip("ICD retriever data not available for loading")

        if not retriever._is_loaded:
            pytest.skip("ICD retriever could not load reference data")

        results = retriever.retrieve(
            text="type 2 diabetes mellitus with hyperglycemia",
            predicted_hccs=["HCC37"],
            top_k=5,
        )
        assert isinstance(results, list)
        if len(results) > 0:
            assert "icd10_code" in results[0]
            assert "similarity_score" in results[0] or "relevance_score" in results[0]


# ── Span Proposer Tests ──────────────────────────────────────────────────────

class TestSpanProposer:
    def test_import(self) -> None:
        from ml_engine.span_proposer import SpanProposer
        assert SpanProposer is not None

    def test_propose_spans(self) -> None:
        from ml_engine.span_proposer import SpanProposer

        proposer = SpanProposer()
        text = (
            "ASSESSMENT AND PLAN:\n"
            "1. Type 2 diabetes mellitus with hyperglycemia (E11.65).\n"
            "   Continue metformin 1000mg BID.\n"
            "2. Essential hypertension (I10) - not at goal.\n"
        )
        spans = proposer.propose_spans(
            text=text,
            icd_description="diabetes mellitus",
        )
        assert isinstance(spans, list)
        if len(spans) > 0:
            span = spans[0]
            assert hasattr(span, "text")


# ── HCC Predictor Tests (mock/import only) ──────────────────────────────────

class TestHCCPredictor:
    def test_import(self) -> None:
        from ml_engine.hcc_predictor import HCCPredictor
        assert HCCPredictor is not None

    def test_instantiate(self) -> None:
        from ml_engine.hcc_predictor import HCCPredictor
        from config.settings import get_settings
        settings = get_settings()
        predictor = HCCPredictor(settings.ml)
        assert predictor is not None
