"""Text normalization and section segmentation for clinical documents."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


# Clinical section header patterns
SECTION_PATTERNS = [
    (r"(?i)\b(HISTORY OF PRESENT(?:ING)? ILLNESS|HPI)\b", "HPI"),
    (r"(?i)\b(CHIEF COMPLAINT|CC|REASON FOR VISIT)\b", "CHIEF_COMPLAINT"),
    (r"(?i)\b(REVIEW OF SYSTEMS|ROS)\b", "ROS"),
    (r"(?i)\b(PHYSICAL EXAM(?:INATION)?|PE)\b", "PHYSICAL_EXAM"),
    (r"(?i)\b(ASSESSMENT(?:\s*(?:AND|&)\s*PLAN)?|A/?P)\b", "ASSESSMENT_PLAN"),
    (r"(?i)\b(PLAN)\b", "PLAN"),
    (r"(?i)\b(MEDICATIONS?|CURRENT MEDICATIONS?|MED(?:ICATION)? LIST)\b", "MEDICATIONS"),
    (r"(?i)\b(LAB(?:ORATORY)? RESULTS?|LABS?)\b", "LABS"),
    (r"(?i)\b(VITAL SIGNS?|VITALS?)\b", "VITALS"),
    (r"(?i)\b(PAST MEDICAL HISTORY|PMH|PMHx)\b", "PMH"),
    (r"(?i)\b(PAST SURGICAL HISTORY|PSH|PSHx)\b", "PSH"),
    (r"(?i)\b(FAMILY HISTORY|FH|FHx)\b", "FAMILY_HISTORY"),
    (r"(?i)\b(SOCIAL HISTORY|SH|SHx)\b", "SOCIAL_HISTORY"),
    (r"(?i)\b(ALLERGIES|ALLERGY)\b", "ALLERGIES"),
    (r"(?i)\b(PROBLEM LIST)\b", "PROBLEM_LIST"),
    (r"(?i)\b(DISCHARGE DIAGNOS[EI]S|DISCHARGE SUMMARY)\b", "DISCHARGE"),
    (r"(?i)\b(IMPRESSION)\b", "IMPRESSION"),
    (r"(?i)\b(PROCEDURES?|OPERATIVE NOTES?)\b", "PROCEDURES"),
    (r"(?i)\b(IMAGING|RADIOLOGY|X-?RAY|CT|MRI)\b", "IMAGING"),
    (r"(?i)\b(IMMUNIZATIONS?|VACCINES?)\b", "IMMUNIZATIONS"),
]


def normalize_text(text: str) -> str:
    """Clean and normalize extracted text."""
    # Collapse multiple whitespace
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def segment_sections(text: str) -> List[Dict[str, str]]:
    """Split clinical text into labeled sections.

    Returns list of {section: str, text: str, start: int, end: int}.
    """
    # Find all section header positions
    matches: List[Tuple[int, str]] = []
    for pattern, label in SECTION_PATTERNS:
        for m in re.finditer(pattern, text):
            matches.append((m.start(), label))

    if not matches:
        return [{"section": "FULL_TEXT", "text": text, "start": 0, "end": len(text)}]

    # Sort by position
    matches.sort(key=lambda x: x[0])

    sections = []
    for i, (pos, label) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        section_text = text[pos:end].strip()
        sections.append({
            "section": label,
            "text": section_text,
            "start": pos,
            "end": end,
        })

    return sections


def split_into_encounter_chunks(text: str) -> List[Dict[str, str]]:
    """Split text into encounter-delimited chunks based on date patterns."""
    date_pattern = r"(?:Date(?:\s+of\s+(?:Service|Visit))?|DOS|Visit)\s*[:]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    matches = list(re.finditer(date_pattern, text, re.IGNORECASE))

    if not matches:
        return [{"encounter_marker": None, "text": text, "start": 0, "end": len(text)}]

    chunks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks.append({
            "encounter_marker": m.group(1),
            "text": text[start:end].strip(),
            "start": start,
            "end": end,
        })

    return chunks
