"""Pydantic schemas for configuration endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ConfigResponse(BaseModel):
    llm: Dict[str, Any]
    pipeline: Dict[str, Any]
    ml: Dict[str, Any]
    feature_flags: Dict[str, bool]


class FeatureFlagUpdate(BaseModel):
    flag: str
    enabled: bool


class PromptTemplateUpdate(BaseModel):
    content: str
