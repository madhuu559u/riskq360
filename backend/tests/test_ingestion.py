"""Tests for the ingestion layer — PDF processing, quality scoring, text normalization."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.quality_scorer import QualityScorer
from ingestion.text_normalizer import normalize_text, segment_sections, split_into_encounter_chunks
from ingestion.page_extractor import extract_pages


# ── Quality Scorer Tests ─────────────────────────────────────────────────────

class TestQualityScorer:
    def setup_method(self) -> None:
        self.scorer = QualityScorer()

    def test_high_quality_text(self, sample_clinical_text: str) -> None:
        score = self.scorer.score(sample_clinical_text)
        assert 50 <= score <= 100, f"Clinical text should score well, got {score}"

    def test_empty_text(self) -> None:
        score = self.scorer.score("")
        assert score == 0

    def test_garbage_text(self) -> None:
        # Real gibberish: long consonant clusters that trigger penalty
        garbage = "xbcdfghjklmnp qrstvwxyz bcdfgh" * 20
        score = self.scorer.score(garbage)
        assert score < 95, f"Garbage text should score below max, got {score}"

    def test_very_short_text(self) -> None:
        score = self.scorer.score("Page 1")
        # Very short text still gets some line structure + density points
        assert score < 70

    def test_score_range(self) -> None:
        texts = [
            "",
            "Hello",
            "This is a medical note. The patient has diabetes.",
            "ASSESSMENT AND PLAN:\n1. Diabetes mellitus type 2 - continue metformin.\n"
            "2. Hypertension - increase lisinopril.\nFollow up in 3 months.\n" * 5,
        ]
        for text in texts:
            score = self.scorer.score(text)
            assert 0 <= score <= 100, f"Score {score} out of range for text len={len(text)}"

    def test_threshold_check(self, sample_clinical_text: str) -> None:
        score = self.scorer.score(sample_clinical_text)
        # Good clinical text should score above 60 (OCR threshold)
        assert score >= 60


# ── Text Normalizer Tests ────────────────────────────────────────────────────

class TestTextNormalizer:
    def test_section_detection(self, sample_clinical_text: str) -> None:
        sections = segment_sections(sample_clinical_text)
        assert len(sections) > 0
        section_names = [s["section"] for s in sections]
        # Should detect at least some standard sections
        assert any(
            name in section_names
            for name in [
                "CHIEF_COMPLAINT",
                "HPI",
                "ASSESSMENT_PLAN",
                "PHYSICAL_EXAM",
                "ROS",
                "LABS",
            ]
        ), f"Expected clinical sections, got: {section_names}"

    def test_encounter_chunking(self, sample_clinical_text: str) -> None:
        chunks = split_into_encounter_chunks(sample_clinical_text)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "text" in chunk
            assert len(chunk["text"]) > 0

    def test_empty_text(self) -> None:
        sections = segment_sections("")
        # Empty text returns single FULL_TEXT section
        assert len(sections) <= 1

    def test_whitespace_normalization(self) -> None:
        messy = "Hello   world\t\ttab   spaces\n\n\n\nmany newlines"
        normalized = normalize_text(messy)
        assert "\t" not in normalized
        # Multiple spaces should be collapsed
        assert "   " not in normalized


# ── Page Extractor Tests ─────────────────────────────────────────────────────

class TestPageExtractor:
    def test_extract_from_nonexistent_file(self) -> None:
        with pytest.raises(Exception):
            extract_pages(Path("/nonexistent/file.pdf"))

    def test_extract_from_real_pdf(self, uploads_dir: Path) -> None:
        pdfs = list(uploads_dir.glob("*.pdf"))
        if not pdfs:
            pytest.skip("No test PDFs available in uploads/")
        pages = extract_pages(pdfs[0])
        assert len(pages) > 0
        for page in pages:
            assert "page_number" in page
            assert "text" in page
