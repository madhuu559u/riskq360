"""Pipeline-level configuration — parallelism, chunking, timeouts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ChunkingConfig:
    """Text chunking settings for LLM extraction."""

    chunk_size: int = 10_000  # characters
    chunk_overlap: int = 500
    split_on_paragraphs: bool = True
    min_chunk_size: int = 200


@dataclass
class ParallelismConfig:
    """Concurrency limits for pipeline execution."""

    max_concurrent_charts: int = 3
    max_concurrent_pipelines: int = 5
    max_chunk_workers: int = 4


@dataclass
class QualityConfig:
    """Page quality scoring thresholds."""

    quality_threshold: int = 60  # pages below this get OCR
    vision_dpi: int = 200
    min_text_length: int = 50
    max_image_area_ratio: float = 0.8


@dataclass
class ThresholdConfig:
    """Confidence and similarity thresholds."""

    tfidf_similarity: float = 0.35
    ml_confidence: float = 0.3
    llm_verification: float = 0.5
    negation_scope_window: int = 6
    max_negation_scope: int = 15


@dataclass
class PipelineRunConfig:
    """Complete config snapshot for a single pipeline run.

    This gets serialized and stored with each run for reproducibility.
    """

    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    parallelism: ParallelismConfig = field(default_factory=ParallelismConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    measurement_year: int = 2026
    v28_model_version: str = "CMS-HCC-V28-PY2026"

    # Which pipelines to run (set by feature flags / mode)
    run_demographics: bool = True
    run_sentences: bool = True
    run_risk_dx: bool = True
    run_hedis: bool = True
    run_encounters: bool = True
    run_ml_hcc: bool = True
    run_icd_retrieval: bool = True
    run_negation: bool = True
    run_llm_verification: bool = True
    run_raf_calculation: bool = True
