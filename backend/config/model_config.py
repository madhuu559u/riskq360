"""ML model configuration — paths, thresholds, and version tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from config.settings import PROJECT_ROOT


@dataclass
class BioClinicalBERTConfig:
    """Configuration for the HCC multi-label predictor."""

    model_dir: Path = PROJECT_ROOT / "ml_engine" / "models" / "bioclinicalbert"
    max_length: int = 512
    batch_size: int = 16
    confidence_threshold: float = 0.3
    num_labels: int = 115  # V28 payable HCC categories
    model_version: str = "bioclinicalbert-v28-1.0"


@dataclass
class TFIDFConfig:
    """Configuration for the ICD-10 TF-IDF retrieval system."""

    vectorizer_path: Path = PROJECT_ROOT / "ml_engine" / "models" / "tfidf_vectorizer.pkl"
    icd_catalog_path: Path = PROJECT_ROOT / "ml_engine" / "models" / "icd10_catalog.json"
    similarity_threshold: float = 0.35
    top_k: int = 10  # max candidate ICDs per HCC prediction
    total_icd_codes: int = 7903


@dataclass
class NegationConfig:
    """Configuration for ConText/NegEx negation detection."""

    window_size: int = 6  # tokens to look around trigger
    max_scope: int = 15  # max token distance for negation scope


@dataclass
class SpanProposerConfig:
    """Configuration for evidence span extraction."""

    min_span_length: int = 20
    max_span_length: int = 500
    context_window: int = 100  # chars of context around matched span


@dataclass
class ModelRegistry:
    """Central registry for all ML model configs."""

    bioclinicalbert: BioClinicalBERTConfig = field(default_factory=BioClinicalBERTConfig)
    tfidf: TFIDFConfig = field(default_factory=TFIDFConfig)
    negation: NegationConfig = field(default_factory=NegationConfig)
    span_proposer: SpanProposerConfig = field(default_factory=SpanProposerConfig)

    def get_model_versions(self) -> Dict[str, str]:
        return {
            "bioclinicalbert": self.bioclinicalbert.model_version,
            "tfidf_icd_codes": str(self.tfidf.total_icd_codes),
        }


_registry: Optional[ModelRegistry] = None


def get_model_config() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
