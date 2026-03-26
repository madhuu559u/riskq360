"""Evidence span extraction and linking.

Deterministic span proposer that finds clinical evidence in text
before LLM verification — constrains hallucinations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from ingestion.text_normalizer import SECTION_PATTERNS


@dataclass
class EvidenceSpan:
    """A text span supporting a clinical finding."""

    text: str
    start: int
    end: int
    section: str
    relevance_score: float = 0.0


# Section relevance boosts for RA coding
SECTION_BOOSTS: Dict[str, float] = {
    "ASSESSMENT_PLAN": 1.50,
    "IMPRESSION": 1.40,
    "PROBLEM_LIST": 1.40,
    "DISCHARGE": 1.35,
    "HPI": 1.20,
    "CHIEF_COMPLAINT": 1.10,
    "MEDICATIONS": 1.00,
    "LABS": 0.80,
    "VITALS": 0.80,
    "FAMILY_HISTORY": 0.70,
    "SOCIAL_HISTORY": 0.70,
    "FULL_TEXT": 1.00,
}

# Condition-specific regex patterns for common HCC diagnoses
CONDITION_PATTERNS: Dict[str, List[str]] = {
    "diabetes": [
        r"(?i)(?:type\s*[12]\s*)?diabet(?:es|ic)",
        r"(?i)(?:DM|DM2|DMII|T2DM|T1DM)",
        r"(?i)A1[cC]\s*(?:of\s*)?\d+\.?\d*",
        r"(?i)hyperglycemia",
        r"(?i)insulin\s+(?:dependent|resistance)",
    ],
    "heart_failure": [
        r"(?i)(?:congestive\s+)?heart\s+failure",
        r"(?i)(?:CHF|HF|HFrEF|HFpEF)",
        r"(?i)(?:systolic|diastolic)\s+(?:dysfunction|failure)",
        r"(?i)ejection\s+fraction\s*(?:of\s*)?\d+",
        r"(?i)(?:left|right)\s+ventricular\s+(?:dysfunction|failure)",
    ],
    "ckd": [
        r"(?i)chronic\s+kidney\s+disease",
        r"(?i)CKD\s*(?:stage\s*)?[1-5]",
        r"(?i)(?:renal|kidney)\s+(?:failure|insufficiency|disease)",
        r"(?i)eGFR\s*(?:of\s*)?\d+",
        r"(?i)end\s+stage\s+renal",
    ],
    "copd": [
        r"(?i)chronic\s+obstructive\s+pulmonary",
        r"(?i)COPD",
        r"(?i)emphysema",
        r"(?i)chronic\s+bronchitis",
    ],
    "cancer": [
        r"(?i)(?:malignant\s+)?(?:neoplasm|tumor|carcinoma|lymphoma|leukemia|melanoma|sarcoma)",
        r"(?i)(?:breast|lung|colon|prostate|liver|pancreatic|ovarian)\s+cancer",
        r"(?i)metastas[ie]s",
        r"(?i)oncology",
    ],
}


class SpanProposer:
    """Proposes evidence spans by matching clinical patterns in text."""

    def propose_spans(
        self,
        text: str,
        icd_description: str,
        context_window: int = 100,
    ) -> List[EvidenceSpan]:
        """Find evidence spans supporting an ICD diagnosis.

        Args:
            text: Full clinical note text.
            icd_description: Description of the ICD code to find evidence for.
            context_window: Extra characters of context around matches.

        Returns:
            List of EvidenceSpan objects, sorted by relevance.
        """
        spans: List[EvidenceSpan] = []

        # 1. Direct description matching
        desc_spans = self._match_description(text, icd_description, context_window)
        spans.extend(desc_spans)

        # 2. Condition-family pattern matching
        for condition, patterns in CONDITION_PATTERNS.items():
            if self._description_matches_condition(icd_description, condition):
                for pattern in patterns:
                    pattern_spans = self._match_pattern(text, pattern, condition, context_window)
                    spans.extend(pattern_spans)

        # Deduplicate overlapping spans
        spans = self._deduplicate(spans)

        # Apply section boosts
        for span in spans:
            boost = SECTION_BOOSTS.get(span.section, 1.0)
            span.relevance_score *= boost

        spans.sort(key=lambda s: s.relevance_score, reverse=True)
        return spans[:10]  # Top 10 spans

    def _match_description(self, text: str, description: str, context: int) -> List[EvidenceSpan]:
        """Fuzzy match ICD description against text."""
        spans = []
        # Use key words from description
        words = [w for w in description.lower().split() if len(w) > 3]
        if not words:
            return spans

        # Build regex from description keywords
        pattern = r"(?i)" + r"[\s\S]{0,30}".join(re.escape(w) for w in words[:4])
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - context)
            end = min(len(text), m.end() + context)
            section = self._detect_section(text, m.start())
            spans.append(EvidenceSpan(
                text=text[start:end].strip(),
                start=m.start(),
                end=m.end(),
                section=section,
                relevance_score=0.8,
            ))

        return spans

    def _match_pattern(self, text: str, pattern: str, condition: str, context: int) -> List[EvidenceSpan]:
        """Match a regex pattern in text."""
        spans = []
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - context)
            end = min(len(text), m.end() + context)
            section = self._detect_section(text, m.start())
            spans.append(EvidenceSpan(
                text=text[start:end].strip(),
                start=m.start(),
                end=m.end(),
                section=section,
                relevance_score=0.6,
            ))
        return spans

    def _detect_section(self, text: str, position: int) -> str:
        """Detect which clinical section a position falls in."""
        best_section = "FULL_TEXT"
        best_pos = -1

        for pattern, label in SECTION_PATTERNS:
            for m in re.finditer(pattern, text):
                if m.start() <= position and m.start() > best_pos:
                    best_section = label
                    best_pos = m.start()

        return best_section

    @staticmethod
    def _description_matches_condition(description: str, condition: str) -> bool:
        """Check if an ICD description relates to a condition family."""
        desc_lower = description.lower()
        keyword_map = {
            "diabetes": ["diabet", "dm", "hyperglycemia", "insulin"],
            "heart_failure": ["heart failure", "chf", "cardiomyopathy", "ventricular"],
            "ckd": ["kidney", "renal", "ckd", "nephro"],
            "copd": ["copd", "obstructive pulmonary", "emphysema", "bronchitis"],
            "cancer": ["cancer", "neoplasm", "carcinoma", "lymphoma", "leukemia", "malignant"],
        }
        return any(kw in desc_lower for kw in keyword_map.get(condition, []))

    @staticmethod
    def _deduplicate(spans: List[EvidenceSpan]) -> List[EvidenceSpan]:
        """Remove overlapping spans, keeping the one with higher relevance."""
        if not spans:
            return spans

        spans.sort(key=lambda s: s.start)
        result = [spans[0]]

        for span in spans[1:]:
            prev = result[-1]
            if span.start < prev.end:
                # Overlapping — keep the one with higher relevance
                if span.relevance_score > prev.relevance_score:
                    result[-1] = span
            else:
                result.append(span)

        return result
