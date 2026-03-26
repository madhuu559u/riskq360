"""Central configuration using Pydantic BaseSettings.

All settings are loaded from environment variables / .env file.
Nested config objects group related settings for clarity.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Project root (directory containing this file's parent)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    GEMINI = "gemini"


class PipelineMode(str, Enum):
    FULL = "full"
    RISK_ONLY = "risk_only"
    HEDIS_ONLY = "hedis_only"
    HCC_PACK = "hcc_pack"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Database Settings
# ---------------------------------------------------------------------------
class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = 5432
    db: str = "medinsight360"
    user: str = "medinsight"
    password: str = "change_me_in_production"
    pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    @property
    def async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )

    @property
    def sync_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


# ---------------------------------------------------------------------------
# LLM Provider Settings
# ---------------------------------------------------------------------------
class OpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENAI_", extra="ignore")

    api_key: str = ""
    base_url: str = ""
    org_id: str = ""


class AzureOpenAISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AZURE_OPENAI_", extra="ignore")

    endpoint: str = ""
    key: str = ""
    deployment: str = "gpt-4o"
    api_version: str = "2024-08-06"


class GeminiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_", extra="ignore")

    gemini_key: str = ""


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    active_llm_provider: LLMProvider = LLMProvider.OPENAI
    active_llm_model: str = "gpt-4o"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 16384
    llm_timeout: int = 120

    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    azure: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)


# ---------------------------------------------------------------------------
# ML Model Settings
# ---------------------------------------------------------------------------
class MLSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    ml_model_path: Path = PROJECT_ROOT / "ml_engine" / "models" / "bioclinicalbert"
    tfidf_vectorizer_path: Path = PROJECT_ROOT / "ml_engine" / "models" / "tfidf_vectorizer.pkl"
    icd_catalog_path: Path = PROJECT_ROOT / "ml_engine" / "models" / "icd10_catalog.json"
    label_encoder_path: Path = PROJECT_ROOT / "ml_engine" / "models" / "label_encoder.pkl"
    ml_confidence_threshold: float = 0.3
    tfidf_similarity_threshold: float = 0.35


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------
class FeatureFlags(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENABLE_", extra="ignore")

    risk_adjustment: bool = True
    hedis: bool = True
    ml_predictions: bool = True
    llm_verification: bool = True
    ocr_fallback: bool = True
    parallel_pipelines: bool = True
    audit_logging: bool = True
    dashboard: bool = True


# ---------------------------------------------------------------------------
# Pipeline Settings
# ---------------------------------------------------------------------------
class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    max_concurrent_charts: int = 3
    max_concurrent_pipelines: int = 5
    chunk_size: int = 10000
    chunk_overlap: int = 500
    quality_threshold: int = 60
    llm_verification_threshold: float = 0.5
    measurement_year: int = 2026


# ---------------------------------------------------------------------------
# Server Settings
# ---------------------------------------------------------------------------
class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


# ---------------------------------------------------------------------------
# Path Settings
# ---------------------------------------------------------------------------
class PathSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    output_dir: Path = PROJECT_ROOT / "outputs"
    log_dir: Path = PROJECT_ROOT / "logs"
    chart_upload_dir: Path = PROJECT_ROOT / "uploads"
    reference_data_dir: Path = PROJECT_ROOT / "decisioning" / "reference"
    prompts_dir: Path = PROJECT_ROOT / "config" / "prompts"

    def ensure_dirs(self) -> None:
        """Create all required directories if they don't exist."""
        for d in [self.output_dir, self.log_dir, self.chart_upload_dir]:
            d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Root Settings (aggregates everything)
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Root settings object that aggregates all config sections."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Sub-configs
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    paths: PathSettings = Field(default_factory=PathSettings)

    # Top-level settings
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "json"
    secret_key: str = "change_me_to_a_random_secret_key"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    enable_auth: bool = False
    # DB backend selector: auto (legacy), postgres, sqlite
    db_backend: str = "auto"

    @field_validator("db_backend")
    @classmethod
    def validate_db_backend(cls, v: str) -> str:
        allowed = {"auto", "postgres", "sqlite"}
        value = (v or "auto").strip().lower()
        if value not in allowed:
            raise ValueError(f"db_backend must be one of {sorted(allowed)}")
        return value

    def init(self) -> None:
        """Run once at startup — create directories, validate paths."""
        self.paths.ensure_dirs()


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    settings = Settings()
    settings.init()
    return settings
