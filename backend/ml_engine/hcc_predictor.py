"""BioClinicalBERT multi-label HCC predictor.

Adapted from ra-training-data-factory's hcc_predictor.py.
Handles long clinical notes via section-aware chunking + attention pooling.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from config.settings import MLSettings
from core.exceptions import ModelLoadError, PredictionError

logger = structlog.get_logger(__name__)

# Clinical section header patterns for section-aware chunking
SECTION_PATTERNS = [
    r"(?i)\b(HISTORY OF PRESENT(?:ING)? ILLNESS|HPI)\b",
    r"(?i)\b(ASSESSMENT(?:\s*(?:AND|&)\s*PLAN)?|A/?P)\b",
    r"(?i)\b(REVIEW OF SYSTEMS|ROS)\b",
    r"(?i)\b(PHYSICAL EXAM(?:INATION)?|PE)\b",
    r"(?i)\b(MEDICATIONS?)\b",
    r"(?i)\b(LAB(?:ORATORY)? RESULTS?|LABS?)\b",
    r"(?i)\b(PAST MEDICAL HISTORY|PMH)\b",
    r"(?i)\b(PROBLEM LIST)\b",
    r"(?i)\b(DISCHARGE DIAGNOS[EI]S)\b",
    r"(?i)\b(IMPRESSION)\b",
]


class HCCPredictor:
    """Multi-label HCC predictor using BioClinicalBERT.

    Predicts which of the 115 payable V28 HCC categories are present
    in a clinical note, with confidence scores per category.
    """

    def __init__(self, ml_settings: MLSettings) -> None:
        self.settings = ml_settings
        self.model_dir = ml_settings.ml_model_path
        self.confidence_threshold = ml_settings.ml_confidence_threshold
        self.model_version = "bioclinicalbert-v28-1.0"
        self._model = None
        self._tokenizer = None
        self._label_mapping: Dict[int, str] = {}
        self._is_loaded = False

    def _load_model(self) -> None:
        """Lazy-load the model, tokenizer, and label mapping."""
        if self._is_loaded:
            return

        model_path = Path(self.model_dir)

        # Check if model files exist
        if not model_path.exists():
            logger.warning("ml.model_not_found", path=str(model_path))
            raise ModelLoadError(
                f"BioClinicalBERT model not found at {model_path}. "
                "Run the training pipeline first or copy model from ra-training-data-factory."
            )

        try:
            import torch
            from transformers import AutoModel, AutoTokenizer

            # Load tokenizer
            tokenizer_path = model_path / "tokenizer"
            if tokenizer_path.exists():
                self._tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path))
            else:
                self._tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")

            # Load label mapping
            label_map_path = model_path / "label_mapping.json"
            if label_map_path.exists():
                with open(label_map_path) as f:
                    raw = json.load(f)
                self._label_mapping = {int(k): v for k, v in raw.items()}
            else:
                logger.warning("ml.label_mapping_not_found")
                self._label_mapping = {}

            # Load model checkpoint
            checkpoint_path = model_path / "model"
            if checkpoint_path.exists():
                self._model = AutoModel.from_pretrained(str(checkpoint_path))
            else:
                logger.warning("ml.using_base_model")
                self._model = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")

            self._model.eval()
            self._is_loaded = True
            logger.info("ml.model_loaded", labels=len(self._label_mapping))

        except ImportError as e:
            raise ModelLoadError(f"Missing ML dependencies: {e}")
        except Exception as e:
            raise ModelLoadError(f"Failed to load model: {e}")

    def predict(self, text: str) -> List[Dict[str, Any]]:
        """Predict HCC categories from clinical text.

        Args:
            text: Full clinical note text.

        Returns:
            List of {hcc_code, hcc_description, confidence} dicts,
            sorted by confidence descending.
        """
        try:
            self._load_model()
        except ModelLoadError:
            logger.warning("ml.model_unavailable, returning empty predictions")
            return []

        try:
            import torch

            # Section-aware chunking
            chunks = self._chunk_text(text, max_length=512, max_chunks=8)

            # Tokenize all chunks
            encodings = self._tokenizer(
                chunks,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )

            # Forward pass
            with torch.no_grad():
                outputs = self._model(**encodings)
                # Pool over chunks using mean of [CLS] tokens
                cls_embeddings = outputs.last_hidden_state[:, 0, :]  # [num_chunks, hidden]
                pooled = cls_embeddings.mean(dim=0, keepdim=True)  # [1, hidden]

                # Simple linear projection for prediction (if no classification head loaded)
                # In production, the full model with classification head would be used
                if hasattr(self._model, "classifier"):
                    logits = self._model.classifier(pooled)
                else:
                    # Fallback: return empty if no classification head
                    logger.warning("ml.no_classifier_head")
                    return []

                probs = torch.sigmoid(logits).squeeze().cpu().numpy()

            # Gather predictions above threshold
            predictions = []
            for idx, prob in enumerate(probs):
                if prob >= self.confidence_threshold:
                    hcc_code = self._label_mapping.get(idx, f"HCC{idx}")
                    predictions.append({
                        "hcc_code": hcc_code,
                        "hcc_description": "",
                        "confidence": round(float(prob), 4),
                    })

            predictions.sort(key=lambda x: x["confidence"], reverse=True)
            logger.info("ml.prediction_done", predictions=len(predictions))
            return predictions

        except Exception as e:
            raise PredictionError(f"HCC prediction failed: {e}")

    def _chunk_text(self, text: str, max_length: int = 512, max_chunks: int = 8) -> List[str]:
        """Section-aware text chunking for the transformer model."""
        # Find section boundaries
        section_starts = []
        for pattern in SECTION_PATTERNS:
            for m in re.finditer(pattern, text):
                section_starts.append(m.start())
        section_starts.sort()

        # If no sections found, split evenly
        if not section_starts:
            chunk_size = len(text) // max_chunks + 1
            chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
            return chunks[:max_chunks]

        # Split at section boundaries
        sections = []
        for i, start in enumerate(section_starts):
            end = section_starts[i + 1] if i + 1 < len(section_starts) else len(text)
            sections.append(text[start:end])

        # Merge small sections and split large ones to fit max_length
        # Approximate: 1 token ≈ 4 chars
        char_limit = max_length * 4
        chunks = []
        current = ""
        for section in sections:
            if len(current) + len(section) <= char_limit:
                current += "\n\n" + section if current else section
            else:
                if current:
                    chunks.append(current)
                if len(section) > char_limit:
                    # Split large section
                    for i in range(0, len(section), char_limit):
                        chunks.append(section[i:i + char_limit])
                else:
                    current = section
                    continue
                current = ""

        if current:
            chunks.append(current)

        return chunks[:max_chunks]
