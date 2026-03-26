"""Custom exception classes for MedInsight 360."""

from __future__ import annotations


class MedInsightError(Exception):
    """Base exception for MedInsight 360."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


# -- Ingestion Errors -------------------------------------------------------

class PDFProcessingError(MedInsightError):
    """Failed to process a PDF file."""


class OCRError(MedInsightError):
    """OCR (Vision API) failed for a page."""


class QualityScoringError(MedInsightError):
    """Text quality scoring failed."""


# -- Extraction Errors ------------------------------------------------------

class ExtractionError(MedInsightError):
    """Base class for LLM extraction pipeline errors."""


class LLMCallError(ExtractionError):
    """An LLM API call failed after retries."""

    def __init__(
        self,
        message: str,
        provider: str = "",
        model: str = "",
        status_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details)
        self.provider = provider
        self.model = model
        self.status_code = status_code


class JSONParsingError(ExtractionError):
    """LLM returned invalid / unparseable JSON."""


class ChunkingError(ExtractionError):
    """Text chunking failed."""


# -- ML Engine Errors -------------------------------------------------------

class MLEngineError(MedInsightError):
    """Base class for ML engine errors."""


class ModelLoadError(MLEngineError):
    """Failed to load an ML model (weights, tokenizer, etc.)."""


class PredictionError(MLEngineError):
    """Model inference failed."""


class ICDRetrievalError(MLEngineError):
    """TF-IDF ICD retrieval failed."""


# -- Decisioning Errors -----------------------------------------------------

class DecisioningError(MedInsightError):
    """Base class for decisioning layer errors."""


class HCCMappingError(DecisioningError):
    """ICD-to-HCC mapping failed."""


class RAFCalculationError(DecisioningError):
    """RAF score calculation failed."""


class HierarchyError(DecisioningError):
    """Hierarchy suppression logic failed."""


class VerificationError(DecisioningError):
    """LLM verification of ICD codes failed."""


# -- Database Errors --------------------------------------------------------

class DatabaseError(MedInsightError):
    """Database operation failed."""


class ConnectionError(DatabaseError):
    """Cannot connect to the database."""


class MigrationError(DatabaseError):
    """Database migration failed."""


# -- Pipeline Errors --------------------------------------------------------

class PipelineError(MedInsightError):
    """Pipeline orchestration error."""


class PipelineTimeoutError(PipelineError):
    """A pipeline step exceeded its timeout."""


class FeatureFlagError(MedInsightError):
    """Invalid or missing feature flag."""


# -- Configuration Errors ---------------------------------------------------

class ConfigurationError(MedInsightError):
    """Invalid or missing configuration."""


class ReferenceDataError(MedInsightError):
    """Reference data (V28 tables, HEDIS specs) is missing or corrupt."""
