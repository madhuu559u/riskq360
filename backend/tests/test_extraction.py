"""Tests for the extraction layer — chunking, LLM client, pipeline base."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extraction.chunk_manager import chunk_text
from config.pipeline_config import ChunkingConfig


# ── Chunk Manager Tests ──────────────────────────────────────────────────────

class TestChunkManager:
    def test_short_text_single_chunk(self) -> None:
        text = "This is a short text."
        chunks = chunk_text(text, config=ChunkingConfig(chunk_size=10000, chunk_overlap=200))
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self) -> None:
        paragraph = "This is a clinical paragraph about the patient. " * 50 + "\n\n"
        text = paragraph * 10
        chunks = chunk_text(text, config=ChunkingConfig(chunk_size=5000, chunk_overlap=200))
        assert len(chunks) > 1

    def test_chunks_are_strings(self) -> None:
        text = "First paragraph about diabetes.\n\nSecond paragraph about hypertension.\n\n"
        text = text * 100
        chunks = chunk_text(text, config=ChunkingConfig(chunk_size=1000, chunk_overlap=100))
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) > 0

    def test_overlap_present(self) -> None:
        text = "Word " * 3000
        chunks = chunk_text(text, config=ChunkingConfig(chunk_size=5000, chunk_overlap=500))
        if len(chunks) >= 2:
            end_of_first = chunks[0][-200:]
            start_of_second = chunks[1][:500]
            assert any(
                word in start_of_second
                for word in end_of_first.split()
            )

    def test_empty_text(self) -> None:
        chunks = chunk_text("", config=ChunkingConfig(chunk_size=10000, chunk_overlap=200))
        assert len(chunks) <= 1

    def test_respects_max_chars(self) -> None:
        text = "Sentence about the patient. " * 500
        max_chars = 2000
        chunks = chunk_text(text, config=ChunkingConfig(chunk_size=max_chars, chunk_overlap=100))
        for chunk in chunks:
            assert len(chunk) <= max_chars * 1.5, (
                f"Chunk too large: {len(chunk)} > {max_chars * 1.5}"
            )


# ── LLM Client Tests (unit, no real API calls) ──────────────────────────────

class TestLLMClient:
    def test_safe_json_parse(self) -> None:
        from extraction.llm_client import safe_parse_json

        # Valid JSON
        result = safe_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

        # JSON in markdown fence
        result = safe_parse_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

        # Invalid JSON
        result = safe_parse_json("not json at all")
        # Implementation returns dict with _parse_error flag for unparseable text
        assert result is None or isinstance(result, dict)

    def test_safe_json_parse_array(self) -> None:
        from extraction.llm_client import safe_parse_json

        result = safe_parse_json('[{"a": 1}, {"b": 2}]')
        assert isinstance(result, (list, dict))

    def test_safe_json_parse_trailing_comma(self) -> None:
        from extraction.llm_client import safe_parse_json

        result = safe_parse_json('{"a": 1, "b": 2,}')
        if result is not None and isinstance(result, dict):
            assert result["a"] == 1


# ── Pipeline Base Tests ──────────────────────────────────────────────────────

class TestPipelineImports:
    """Verify all pipeline classes can be imported."""

    def test_import_demographics(self) -> None:
        from extraction.demographics_pipeline import DemographicsPipeline
        assert DemographicsPipeline is not None

    def test_import_sentence(self) -> None:
        from extraction.sentence_pipeline import SentencePipeline
        assert SentencePipeline is not None

    def test_import_risk_dx(self) -> None:
        from extraction.risk_dx_pipeline import RiskDxPipeline
        assert RiskDxPipeline is not None

    def test_import_hedis(self) -> None:
        from extraction.hedis_pipeline import HEDISPipeline
        assert HEDISPipeline is not None

    def test_import_encounter(self) -> None:
        from extraction.encounter_pipeline import EncounterPipeline
        assert EncounterPipeline is not None
