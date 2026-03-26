"""LLM provider configuration and client factory settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from config.settings import LLMProvider


@dataclass
class PromptTemplate:
    """A named prompt template with version tracking."""

    name: str
    system_prompt: str
    version: int = 1
    is_active: bool = True


@dataclass
class LLMCallConfig:
    """Per-call LLM configuration overrides."""

    provider: Optional[LLMProvider] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    response_format: Optional[Dict] = None  # e.g. {"type": "json_object"}


# Default model recommendations per task type
TASK_MODEL_DEFAULTS: Dict[str, str] = {
    "demographics_extraction": "gpt-4o",
    "sentence_categorization": "gpt-4o-mini",
    "risk_dx_extraction": "gpt-4o",
    "hedis_evidence": "gpt-4o-mini",
    "encounter_extraction": "gpt-4o-mini",
    "icd_meat_verification": "gpt-4o",
    "ocr_vision": "gpt-4o",
    "clinical_summary": "gpt-4o-mini",
}
