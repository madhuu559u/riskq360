"""Per-page text quality scoring — adapted from medinsights smartpdf.py.

Scores each page 0-100 based on text characteristics to decide if OCR is needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class QualityBreakdown:
    text_length_score: float = 0.0
    char_ratio_score: float = 0.0
    word_length_score: float = 0.0
    line_structure_score: float = 0.0
    text_density_score: float = 0.0
    total: float = 0.0


class QualityScorer:
    """Deterministic text quality scorer for PDF pages."""

    def score(self, text: str, image_area_ratio: float = 0.0) -> float:
        """Score page text quality from 0 to 100."""
        if not text or not text.strip():
            return 0.0

        breakdown = QualityBreakdown()
        text = text.strip()

        # 1. Text length score (0-25)
        length = len(text)
        if length >= 500:
            breakdown.text_length_score = 25.0
        elif length >= 200:
            breakdown.text_length_score = 20.0
        elif length >= 50:
            breakdown.text_length_score = 10.0
        else:
            breakdown.text_length_score = length / 50 * 5

        # 2. Character ratio score (0-25) — proportion of alphanumeric chars
        if length > 0:
            alnum_count = sum(1 for c in text if c.isalnum())
            ratio = alnum_count / length
            breakdown.char_ratio_score = min(ratio * 35, 25.0)

        # 3. Word length score (0-20) — average word length should be 3-10
        words = text.split()
        if words:
            avg_word_len = sum(len(w) for w in words) / len(words)
            if 3 <= avg_word_len <= 10:
                breakdown.word_length_score = 20.0
            elif 2 <= avg_word_len <= 15:
                breakdown.word_length_score = 12.0
            else:
                breakdown.word_length_score = 5.0

        # 4. Line structure score (0-15) — presence of normal line breaks
        lines = text.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]
        if len(non_empty_lines) >= 3:
            breakdown.line_structure_score = 15.0
        elif len(non_empty_lines) >= 1:
            breakdown.line_structure_score = 8.0

        # 5. Text density vs image ratio (0-15)
        if image_area_ratio < 0.3:
            breakdown.text_density_score = 15.0
        elif image_area_ratio < 0.6:
            breakdown.text_density_score = 10.0
        elif image_area_ratio < 0.8:
            breakdown.text_density_score = 5.0
        else:
            breakdown.text_density_score = 2.0

        # Penalize gibberish (long consonant clusters)
        gibberish_penalty = 0.0
        consonant_clusters = re.findall(r"[bcdfghjklmnpqrstvwxyz]{5,}", text.lower())
        if consonant_clusters:
            gibberish_penalty = min(len(consonant_clusters) * 3, 20)

        breakdown.total = max(0.0, min(100.0,
            breakdown.text_length_score
            + breakdown.char_ratio_score
            + breakdown.word_length_score
            + breakdown.line_structure_score
            + breakdown.text_density_score
            - gibberish_penalty
        ))

        return round(breakdown.total, 1)
