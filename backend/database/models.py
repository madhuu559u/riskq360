"""SQLAlchemy ORM models for MedInsight 360 — assertion-centric schema.

This schema is built around the MiniMax single-pass extractor output.
The `assertions` table is the central entity, containing all clinical facts
with provenance (exact_quote, page_number, char offsets) and enrichment
(codes, dates, flags) stored as both indexed columns and JSONB.

Tables:
  Core:        charts, chart_pages, pipeline_runs, pipeline_logs
  Clinical:    assertions (central), condition_groups
  Risk Adj:    payable_hccs, raf_summaries, hcc_hierarchy_log
  HEDIS:       hedis_results, hedis_gaps
  Audit:       audit_logs, review_actions
  Config:      system_config, llm_configs, prompt_templates
  Reference:   icd_hcc_mappings
  Analytics:   processing_stats
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# =============================================================================
# CORE TABLES
# =============================================================================

class Chart(Base):
    __tablename__ = "charts"

    id = Column(Integer, Sequence("charts_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size_bytes = Column(Integer)
    page_count = Column(Integer)
    pages_with_text = Column(Integer)
    total_chars = Column(Integer)
    upload_source = Column(String(20), default="cli")  # cli | api | batch
    status = Column(String(30), default="uploaded")  # uploaded | processing | completed | failed
    quality_score_avg = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    patient = relationship("Patient", back_populates="charts", foreign_keys=[patient_id])
    pages = relationship("ChartPage", back_populates="chart", cascade="all, delete-orphan")
    pipeline_runs = relationship("PipelineRun", back_populates="chart", cascade="all, delete-orphan")
    assertions = relationship("Assertion", back_populates="chart", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_charts_status", "status"),
        Index("ix_charts_created", "created_at"),
        Index("ix_charts_patient", "patient_id"),
    )


class ChartPage(Base):
    __tablename__ = "chart_pages"

    id = Column(Integer, Sequence("chart_pages_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    page_number = Column(Integer, nullable=False)
    text_content = Column(Text)
    text_length = Column(Integer)
    quality_score = Column(Float)
    extraction_method = Column(String(20), default="text")  # text | ocr | vision
    page_best_dos = Column(String(20))  # ISO date string
    dates_found = Column(JSON, default=list)  # [{iso, kind, raw}]

    chart = relationship("Chart", back_populates="pages")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, Sequence("pipeline_runs_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_number = Column(Integer, default=1)
    status = Column(String(30), default="running")  # running | completed | failed
    mode = Column(String(30), default="full")  # full | risk_only | hedis_only | hcc_pack
    model = Column(String(100))  # LLM model used
    chunk_count = Column(Integer)
    config_snapshot = Column(JSON)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    error_message = Column(Text)
    assertions_raw = Column(Integer, default=0)
    assertions_audited = Column(Integer, default=0)
    drops_total = Column(Integer, default=0)

    chart = relationship("Chart", back_populates="pipeline_runs")
    logs = relationship("PipelineLog", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_pipeline_runs_status", "status"),
        Index("ix_pipeline_runs_chart", "chart_id"),
    )


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id = Column(Integer, Sequence("pipeline_logs_id_seq"), primary_key=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    log_level = Column(String(10), default="INFO")
    step = Column(String(100))
    message = Column(Text)
    details = Column(JSON)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    run = relationship("PipelineRun", back_populates="logs")


# =============================================================================
# CLINICAL ASSERTIONS — THE CENTRAL TABLE
# =============================================================================

class Assertion(Base):
    """Central table — every clinical fact extracted from a chart.

    Each row is one atomic assertion (one diagnosis, one vital, one medication, etc.)
    with full provenance and enrichment.
    """
    __tablename__ = "assertions"

    id = Column(Integer, Sequence("assertions_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    assertion_id = Column(String(30))  # e.g. "p003_000012"

    # Core fields
    category = Column(String(50), nullable=False)  # diagnosis | medication | vital_sign | ...
    concept = Column(Text)
    canonical_concept = Column(Text)
    text = Column(Text)
    clean_text = Column(Text)
    status = Column(String(20), default="active")  # active | negated | historical | resolved | uncertain | family_history
    subject = Column(String(30), default="patient")  # patient | family_member | provider_plan | generic_education
    evidence_rank = Column(Integer, default=3)  # 1 = strong, 2 = moderate, 3 = weak

    # Provenance
    page_number = Column(Integer)
    exact_quote = Column(Text)
    char_start = Column(Integer)
    char_end = Column(Integer)
    quote_repaired = Column(Boolean, default=False)
    quote_similarity = Column(Float)
    quote_match_method = Column(String(20))  # strict | ws_normalized | approximate | token_rescue

    # Codes (indexed for fast queries)
    icd_codes = Column(JSON, default=list)  # [{code, description}]
    icd_codes_primary = Column(JSON)  # [{code, description}] for run-on lists
    icd9_codes = Column(JSON, default=list)
    cpt2_codes = Column(JSON, default=list)
    hcpcs_codes = Column(JSON, default=list)
    codes = Column(JSON, default=list)  # all typed codes [{system, code, description}]

    # Dates
    effective_date = Column(String(20))  # ISO date
    effective_date_source = Column(String(30))
    inferred_date = Column(String(20))
    inferred_date_confidence = Column(String(10))  # low | medium | high
    inferred_date_source = Column(String(30))
    page_best_dos = Column(String(20))
    doc_best_guess_dos = Column(String(20))

    # Negation
    negation_trigger = Column(String(100))
    allergy_none = Column(Boolean, default=False)

    # Structured data (vitals, scores)
    structured = Column(JSON, default=dict)  # {bp_systolic, score_name, score_value, ...}
    structured_page_vitals = Column(JSON, default=dict)
    medication_normalized = Column(JSON)  # {ingredient, strength, frequency, route}

    # Condition grouping
    condition_group_id_v3 = Column(String(20))
    condition_group_key_v3 = Column(Text)
    is_condition_best_evidence_v3 = Column(Boolean, default=False)

    # HCC / RA flags
    is_hcc_candidate = Column(Boolean, default=False)
    is_payable_hcc_candidate = Column(Boolean, default=False)
    is_payable_ra_candidate = Column(Boolean, default=False)
    payable_hcc_exclusion_reason = Column(String(50))

    # HEDIS flags
    is_hedis_evidence = Column(Boolean, default=False)
    is_hedis_evidence_effective = Column(Boolean, default=False)

    # Review
    review_status = Column(String(20), default="pending")  # pending | approved | rejected
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    # Metadata
    contradicted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    chart = relationship("Chart", back_populates="assertions")

    __table_args__ = (
        Index("ix_assertions_chart", "chart_id"),
        Index("ix_assertions_category", "category"),
        Index("ix_assertions_status", "status"),
        Index("ix_assertions_page", "page_number"),
        Index("ix_assertions_hcc_candidate", "is_hcc_candidate"),
        Index("ix_assertions_payable_ra", "is_payable_ra_candidate"),
        Index("ix_assertions_hedis", "is_hedis_evidence"),
        Index("ix_assertions_condition_group", "condition_group_id_v3"),
        Index("ix_assertions_review", "review_status"),
        Index("ix_assertions_effective_date", "effective_date"),
    )


class ConditionGroup(Base):
    """Aggregated condition groups from assertion grouping."""
    __tablename__ = "condition_groups"

    id = Column(Integer, Sequence("condition_groups_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    group_id = Column(String(20), nullable=False)  # e.g. "g0001"
    group_key = Column(Text)  # ICD:E11.65 or CAN:essential hypertension
    canonical_concept = Column(Text)
    best_evidence_assertion_id = Column(String(30))
    assertion_count = Column(Integer, default=0)
    icd_codes = Column(JSON, default=list)
    status = Column(String(20))  # active | resolved | etc.

    __table_args__ = (
        Index("ix_condition_groups_chart", "chart_id"),
        UniqueConstraint("chart_id", "group_id", name="uq_chart_group"),
    )


# =============================================================================
# RISK ADJUSTMENT / HCC TABLES
# =============================================================================

class PayableHCC(Base):
    __tablename__ = "payable_hccs"

    id = Column(Integer, Sequence("payable_hccs_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    hcc_code = Column(String(20), nullable=False)
    hcc_description = Column(String(255))
    raf_weight = Column(Numeric(6, 4))
    confidence = Column(Numeric(6, 4))  # Ensemble confidence (0-1)
    source = Column(String(20))  # llm | tfidf | trained_bert | ensemble
    llm_verified = Column(Boolean, nullable=True)  # LLM verification passed
    llm_confidence = Column(Numeric(6, 4), nullable=True)  # LLM verification confidence
    hierarchy_applied = Column(Boolean, default=False)
    supported_icds = Column(JSON, default=list)  # [{icd10_code, concept, page, quote}]
    icd_count = Column(Integer, default=0)
    measurement_year = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_payable_hccs_chart", "chart_id"),
        Index("ix_payable_hccs_hcc", "hcc_code"),
    )


class SuppressedHCC(Base):
    __tablename__ = "suppressed_hccs"

    id = Column(Integer, Sequence("suppressed_hccs_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    hcc_code = Column(String(20), nullable=False)
    hcc_description = Column(String(255))
    suppressed_by = Column(String(20))
    hierarchy_group = Column(String(100))
    supported_icds = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())


class RAFSummary(Base):
    __tablename__ = "raf_summaries"

    id = Column(Integer, Sequence("raf_summaries_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    total_raf_score = Column(Numeric(8, 4), default=0)
    demographic_raf = Column(Numeric(8, 4), default=0)
    hcc_raf = Column(Numeric(8, 4), default=0)
    hcc_count = Column(Integer, default=0)
    payable_hcc_count = Column(Integer, default=0)
    suppressed_hcc_count = Column(Integer, default=0)
    unmapped_icd_count = Column(Integer, default=0)
    total_payable_icds = Column(Integer, default=0)
    ensemble_version = Column(String(20))  # v4 | llm_only
    ensemble_metadata = Column(JSON, nullable=True)  # Full ensemble tracking
    measurement_year = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_raf_summaries_chart", "chart_id"),
    )


# =============================================================================
# HEDIS TABLES
# =============================================================================

class HEDISResult(Base):
    """Per-measure result from HEDIS evaluation."""
    __tablename__ = "hedis_results"

    id = Column(Integer, Sequence("hedis_results_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    measure_id = Column(String(50), nullable=False)
    measure_name = Column(String(255))
    status = Column(String(20))  # met | gap | not_applicable | excluded
    applicable = Column(Boolean, default=False)
    compliant = Column(Boolean, default=False)
    evidence_used = Column(JSON, default=list)
    gaps = Column(JSON, default=list)
    trace = Column(JSON, default=list)
    measurement_year = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_hedis_results_chart", "chart_id"),
        Index("ix_hedis_results_measure", "measure_id"),
        Index("ix_hedis_results_status", "status"),
    )


class HEDISSummary(Base):
    """Aggregate HEDIS summary per chart."""
    __tablename__ = "hedis_summaries"

    id = Column(Integer, Sequence("hedis_summaries_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    total_measures = Column(Integer, default=0)
    applicable_count = Column(Integer, default=0)
    met_count = Column(Integer, default=0)
    gap_count = Column(Integer, default=0)
    excluded_count = Column(Integer, default=0)
    indeterminate_count = Column(Integer, default=0)
    not_applicable_count = Column(Integer, default=0)
    measurement_year = Column(Integer)
    engine_version = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())


# =============================================================================
# AUDIT & REVIEW TABLES
# =============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, Sequence("audit_logs_id_seq"), primary_key=True)
    user_name = Column(String(100))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50))  # assertion | hcc | hedis | config
    entity_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created", "created_at"),
    )


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id = Column(Integer, Sequence("review_actions_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    entity_type = Column(String(30))  # assertion | hcc | hedis
    entity_id = Column(Integer)
    action = Column(String(20))  # approved | rejected | modified
    previous_value = Column(JSON)
    new_value = Column(JSON)
    reviewer = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# =============================================================================
# CONFIGURATION TABLES
# =============================================================================

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, Sequence("system_config_id_seq"), primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON)
    description = Column(Text)
    updated_by = Column(String(100))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id = Column(Integer, Sequence("llm_configs_id_seq"), primary_key=True)
    provider = Column(String(30), nullable=False)
    model_name = Column(String(100))
    temperature = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=4096)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, Sequence("prompt_templates_id_seq"), primary_key=True)
    pipeline_name = Column(String(50), nullable=False)  # "minimax_extraction" | etc.
    version = Column(Integer, default=1)
    system_prompt = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("pipeline_name", "version", name="uq_prompt_version"),
    )


class HEDISMeasureDefinition(Base):
    """DB-backed measure catalog entries (JSON form of YAML definitions)."""
    __tablename__ = "hedis_measure_definitions"

    id = Column(Integer, Sequence("hedis_measure_definitions_id_seq"), primary_key=True)
    measure_id = Column(String(50), nullable=False, unique=True)
    version = Column(String(40), default="2025")
    definition_json = Column(JSON, nullable=False)
    source = Column(String(20), default="file")  # file | db | imported
    checksum = Column(String(64))
    is_active = Column(Boolean, default=True)
    updated_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_hedis_measure_defs_measure_id", "measure_id"),
        Index("ix_hedis_measure_defs_active", "is_active"),
    )


class HEDISValueSet(Base):
    """DB-backed HEDIS valuesets with codes and metadata."""
    __tablename__ = "hedis_valuesets"

    id = Column(Integer, Sequence("hedis_valuesets_id_seq"), primary_key=True)
    valueset_id = Column(String(120), nullable=False, unique=True)
    code_system = Column(String(40))
    payload_json = Column(JSON, nullable=False)
    source = Column(String(20), default="file")  # file | db | imported
    checksum = Column(String(64))
    is_active = Column(Boolean, default=True)
    updated_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_hedis_valuesets_valueset_id", "valueset_id"),
        Index("ix_hedis_valuesets_active", "is_active"),
    )


# =============================================================================
# REFERENCE DATA TABLES
# =============================================================================

class ICDHCCMapping(Base):
    """V28 ICD-10 to HCC mapping reference table."""
    __tablename__ = "icd_hcc_mappings"

    id = Column(Integer, Sequence("icd_hcc_mappings_id_seq"), primary_key=True)
    icd10_code = Column(String(20), nullable=False)
    hcc_category = Column(String(20))
    hcc_description = Column(String(255))
    raf_weight = Column(Numeric(6, 4))
    is_payment_hcc = Column(Boolean, default=True)
    model_year = Column(String(20), default="V28")

    __table_args__ = (
        Index("ix_icd_hcc_icd10", "icd10_code"),
        Index("ix_icd_hcc_hcc", "hcc_category"),
    )


# =============================================================================
# ANALYTICS TABLES
# =============================================================================

class ProcessingStats(Base):
    __tablename__ = "processing_stats"

    id = Column(Integer, Sequence("processing_stats_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    total_processing_seconds = Column(Float)
    extraction_seconds = Column(Float)
    hcc_mapping_seconds = Column(Float)
    hedis_evaluation_seconds = Column(Float)
    pages_processed = Column(Integer)
    ocr_pages = Column(Integer, default=0)
    assertions_raw = Column(Integer)
    assertions_audited = Column(Integer)
    chunks_processed = Column(Integer)
    model_used = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())


class HCCHierarchyLog(Base):
    """Records which HCCs were suppressed and why."""
    __tablename__ = "hcc_hierarchy_log"

    id = Column(Integer, Sequence("hcc_hierarchy_log_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    suppressed_hcc = Column(String(20), nullable=False)
    suppressed_by = Column(String(20), nullable=False)
    group_name = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_hcc_hierarchy_chart", "chart_id"),
    )


class APICallLog(Base):
    """Track LLM API calls for cost and latency monitoring."""
    __tablename__ = "api_call_logs"

    id = Column(Integer, Sequence("api_call_logs_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    pipeline_name = Column(String(50))
    provider = Column(String(30))
    model_name = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Float)
    status = Column(String(20), default="success")  # success | error
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_api_call_logs_run", "run_id"),
    )


class ModelVersion(Base):
    """Track ML model versions and performance metrics."""
    __tablename__ = "model_versions"

    id = Column(Integer, Sequence("model_versions_id_seq"), primary_key=True)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    model_type = Column(String(50))  # hcc_predictor | icd_retriever | negation
    file_path = Column(Text)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_version"),
    )


# =============================================================================
# PATIENT & DEMOGRAPHICS TABLES (normalized from 5-pipeline extraction)
# =============================================================================

class Patient(Base):
    """Master patient entity — one row per unique member.

    Multiple charts can link to the same patient via Chart.patient_id.
    Patient matching is by (name + DOB) or member_id.
    Demographics are updated/merged when new charts arrive.
    """
    __tablename__ = "patients"

    id = Column(Integer, Sequence("patients_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    patient_name = Column(String(255))
    alternate_names = Column(JSON)
    date_of_birth = Column(String(20))
    gender = Column(String(20))
    age = Column(Integer)
    language = Column(String(50))
    race_ethnicity = Column(String(100))
    insurance = Column(String(255))
    allergies = Column(JSON)
    advance_directives = Column(Text)

    # Address
    address_street = Column(String(255))
    address_city = Column(String(100))
    address_state = Column(String(10))
    address_zip = Column(String(20))
    address_full = Column(Text)

    # Social history
    social_smoking = Column(String(255))
    social_alcohol = Column(String(255))
    social_drugs = Column(String(255))
    social_marital = Column(String(50))
    social_employment = Column(String(100))
    social_living = Column(String(255))

    # Mental health
    mental_phq9 = Column(String(50))
    mental_phq2 = Column(String(50))
    mental_mmse = Column(String(50))
    mental_depression = Column(String(100))
    mental_anxiety = Column(String(100))

    # Tracking
    chart_count = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    charts = relationship("Chart", back_populates="patient", foreign_keys="[Chart.patient_id]")
    vitals = relationship("PatientVital", back_populates="patient", cascade="all, delete-orphan")
    providers = relationship("PatientProvider", back_populates="patient", cascade="all, delete-orphan")
    family_history = relationship("PatientFamilyHistory", back_populates="patient", cascade="all, delete-orphan")
    member_ids = relationship("PatientMemberID", back_populates="patient", cascade="all, delete-orphan")
    phones = relationship("PatientPhone", back_populates="patient", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_patients_chart", "chart_id"),
        Index("ix_patients_name", "patient_name"),
        Index("ix_patients_dob", "date_of_birth"),
    )


class PatientVital(Base):
    __tablename__ = "patient_vitals"

    id = Column(Integer, Sequence("patient_vitals_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="SET NULL"), nullable=True)
    measurement_date = Column(String(20))
    bp_systolic = Column(String(20))
    bp_diastolic = Column(String(20))
    weight = Column(String(50))
    height = Column(String(50))
    bmi = Column(String(20))
    pulse = Column(String(20))
    temperature = Column(String(20))
    oxygen_saturation = Column(String(20))

    patient = relationship("Patient", back_populates="vitals")


class PatientProvider(Base):
    __tablename__ = "patient_providers"

    id = Column(Integer, Sequence("patient_providers_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255))
    specialty = Column(String(100))
    facility = Column(String(255))
    address = Column(Text)
    phone = Column(String(50))
    role = Column(String(50))

    patient = relationship("Patient", back_populates="providers")


class PatientFamilyHistory(Base):
    __tablename__ = "patient_family_history"

    id = Column(Integer, Sequence("patient_fh_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    condition = Column(String(255))
    relation = Column(String(100))

    patient = relationship("Patient", back_populates="family_history")


class PatientMemberID(Base):
    __tablename__ = "patient_member_ids"

    id = Column(Integer, Sequence("patient_mid_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String(100))
    source_system = Column(String(100))

    patient = relationship("Patient", back_populates="member_ids")


class PatientPhone(Base):
    __tablename__ = "patient_phones"

    id = Column(Integer, Sequence("patient_phones_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    number = Column(String(50))
    phone_type = Column(String(20))

    patient = relationship("Patient", back_populates="phones")


# =============================================================================
# DIAGNOSES TABLE (normalized from risk extraction pipeline)
# =============================================================================

class Diagnosis(Base):
    """Dedicated diagnosis table with full ICD codes and review workflow."""
    __tablename__ = "diagnoses"

    id = Column(Integer, Sequence("diagnoses_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    icd10_code = Column(String(20))
    icd9_code = Column(String(20))
    snomed_code = Column(String(20))
    description = Column(Text)
    negation_status = Column(String(20), nullable=False, default="active")
    negation_trigger = Column(String(100))
    supporting_text = Column(Text)
    source_section = Column(String(50))
    date_of_service = Column(String(20))
    provider = Column(String(255))

    review_status = Column(String(20), default="pending")
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    hcc_mappings = relationship("DiagnosisHCCMapping", back_populates="diagnosis", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_diagnoses_chart", "chart_id"),
        Index("ix_diagnoses_icd10", "icd10_code"),
        Index("ix_diagnoses_status", "negation_status"),
        Index("ix_diagnoses_review", "review_status"),
    )


class DiagnosisHCCMapping(Base):
    """Per-diagnosis HCC mapping with individual review status."""
    __tablename__ = "diagnosis_hcc_mappings"

    id = Column(Integer, Sequence("dx_hcc_map_id_seq"), primary_key=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    hcc_category = Column(Integer)
    hcc_description = Column(String(255))
    raf_weight = Column(Numeric(6, 4))
    counts_for_raf = Column(Boolean, default=True)
    exclusion_reason = Column(String(100))

    review_status = Column(String(20), default="pending")
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())

    diagnosis = relationship("Diagnosis", back_populates="hcc_mappings")


# =============================================================================
# ENCOUNTER TABLES (normalized from encounters extraction pipeline)
# =============================================================================

class Encounter(Base):
    """Dedicated encounter/visit table — one row per visit date."""
    __tablename__ = "encounters"

    id = Column(Integer, Sequence("encounters_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    encounter_date = Column(String(20))
    encounter_ext_id = Column(String(50))
    provider = Column(String(255))
    facility = Column(String(255))
    encounter_type = Column(String(50))  # office | telehealth | ER | inpatient
    chief_complaint = Column(Text)

    telehealth_platform = Column(String(100))
    telehealth_type = Column(String(20))
    telehealth_prearranged = Column(Boolean)

    counseling_topics = Column(JSON)
    time_spent = Column(String(50))
    signed_by = Column(String(255))

    review_status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    medications = relationship("EncounterMedication", back_populates="encounter", cascade="all, delete-orphan")
    lab_orders = relationship("EncounterLabOrder", back_populates="encounter", cascade="all, delete-orphan")
    procedures = relationship("EncounterProcedure", back_populates="encounter", cascade="all, delete-orphan")
    referrals = relationship("EncounterReferral", back_populates="encounter", cascade="all, delete-orphan")
    diagnoses_list = relationship("EncounterDiagnosis", back_populates="encounter", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_encounters_chart", "chart_id"),
        Index("ix_encounters_date", "encounter_date"),
    )


class EncounterMedication(Base):
    __tablename__ = "encounter_medications"

    id = Column(Integer, Sequence("enc_med_id_seq"), primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255))
    dose_form = Column(String(50))
    instructions = Column(Text)
    indication = Column(String(255))
    action = Column(String(30))  # continue | start | stop | increase | decrease

    encounter = relationship("Encounter", back_populates="medications")


class EncounterLabOrder(Base):
    __tablename__ = "encounter_lab_orders"

    id = Column(Integer, Sequence("enc_lab_id_seq"), primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String(255))
    status = Column(String(30))
    result = Column(Text)
    date_ordered = Column(String(20))
    date_resulted = Column(String(20))

    encounter = relationship("Encounter", back_populates="lab_orders")


class EncounterProcedure(Base):
    __tablename__ = "encounter_procedures"

    id = Column(Integer, Sequence("enc_proc_id_seq"), primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255))
    cpt_code = Column(String(20))
    status = Column(String(30))
    result = Column(Text)

    encounter = relationship("Encounter", back_populates="procedures")


class EncounterReferral(Base):
    __tablename__ = "encounter_referrals"

    id = Column(Integer, Sequence("enc_ref_id_seq"), primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    to_provider = Column(String(255))
    reason = Column(Text)
    status = Column(String(30))
    urgency = Column(String(20))

    encounter = relationship("Encounter", back_populates="referrals")


class EncounterDiagnosis(Base):
    __tablename__ = "encounter_diagnoses"

    id = Column(Integer, Sequence("enc_dx_id_seq"), primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    icd10_code = Column(String(20))
    description = Column(Text)

    encounter = relationship("Encounter", back_populates="diagnoses_list")


# =============================================================================
# CLINICAL SENTENCES TABLE (from sentences extraction pipeline)
# =============================================================================

class ClinicalSentence(Base):
    """Dedicated clinical sentence table with negation detection."""
    __tablename__ = "clinical_sentences"

    id = Column(Integer, Sequence("clin_sent_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    sentence_text = Column(Text, nullable=False)
    category = Column(String(50))
    is_negated = Column(Boolean, default=False)
    negation_trigger = Column(String(100))
    negated_item = Column(String(255))

    review_status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_clin_sent_chart", "chart_id"),
        Index("ix_clin_sent_category", "category"),
        Index("ix_clin_sent_negated", "is_negated"),
    )


# =============================================================================
# HEDIS EVIDENCE TABLES (normalized from HEDIS extraction pipeline)
# =============================================================================

class HEDISBPReading(Base):
    """Blood pressure readings for CBP measure."""
    __tablename__ = "hedis_bp_readings"

    id = Column(Integer, Sequence("hedis_bp_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    reading_date = Column(String(20))
    systolic = Column(Integer)
    diastolic = Column(Integer)
    location = Column(String(30))
    within_target = Column(Boolean)
    target_note = Column(String(100))

    review_status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_hedis_bp_chart", "chart_id"),)


class HEDISLabResult(Base):
    """Lab results for HEDIS measures (A1C, LDL, etc.)."""
    __tablename__ = "hedis_lab_results"

    id = Column(Integer, Sequence("hedis_lab_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    test_name = Column(String(100))
    result_value = Column(String(50))
    result_date = Column(String(20))
    reference_range = Column(String(50))
    hedis_measure = Column(String(20))
    within_target = Column(Boolean)

    review_status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_hedis_lab_chart", "chart_id"),)


class HEDISScreening(Base):
    """Screenings for HEDIS measures (mammogram, colonoscopy, pap, etc.)."""
    __tablename__ = "hedis_screenings"

    id = Column(Integer, Sequence("hedis_scr_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    screening_type = Column(String(50))
    screening_date = Column(String(20))
    result = Column(Text)
    hedis_measure = Column(String(20))
    status = Column(String(30))

    review_status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_hedis_scr_chart", "chart_id"),)


class HEDISDepressionScreening(Base):
    """Depression screening details for DSF measure."""
    __tablename__ = "hedis_depression_screenings"

    id = Column(Integer, Sequence("hedis_dep_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    phq2_score = Column(String(20))
    phq2_date = Column(String(20))
    phq9_score = Column(String(20))
    phq9_date = Column(String(20))
    positive_screen = Column(Boolean, default=False)
    follow_up_plan = Column(Text)

    review_status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())


class HEDISFallsRisk(Base):
    """Falls risk assessment for older adult measures."""
    __tablename__ = "hedis_falls_risk"

    id = Column(Integer, Sequence("hedis_falls_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    assessed = Column(Boolean, default=False)
    risk_level = Column(String(20))
    interventions = Column(JSON)
    assessment_date = Column(String(20))

    created_at = Column(DateTime, server_default=func.now())


class HEDISEligibility(Base):
    """HEDIS eligibility conditions (diabetes, hypertension, etc.)."""
    __tablename__ = "hedis_eligibility"

    id = Column(Integer, Sequence("hedis_elig_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    condition = Column(String(100))
    is_present = Column(Boolean)
    evidence = Column(Text)

    created_at = Column(DateTime, server_default=func.now())


class HEDISMedication(Base):
    """HEDIS-relevant medications."""
    __tablename__ = "hedis_medications"

    id = Column(Integer, Sequence("hedis_med_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)

    medication = Column(String(255))
    indication = Column(String(255))
    hedis_relevance = Column(String(100))

    created_at = Column(DateTime, server_default=func.now())


# =============================================================================
# RAW EXTRACTION RESULTS (for debugging / reprocessing)
# =============================================================================

class ExtractionResult(Base):
    """Raw pipeline JSON output per pipeline per run — for debugging/reprocessing."""
    __tablename__ = "extraction_results"

    id = Column(Integer, Sequence("extraction_results_id_seq"), primary_key=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    pipeline_name = Column(String(50), nullable=False)  # demographics | sentences | risk | hedis | encounters
    raw_json = Column(JSON, nullable=False)
    chunk_count = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_extraction_results_run", "run_id"),
    )


# =============================================================================
# CODEX AUDIT / HARDENING TABLES
# =============================================================================

class DiagnosisCandidate(Base):
    """Lifecycle-tracked diagnosis candidates for auditability."""
    __tablename__ = "diagnosis_candidates"

    id = Column(Integer, Sequence("diagnosis_candidates_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)

    assertion_id = Column(Integer, ForeignKey("assertions.id", ondelete="SET NULL"), nullable=True)
    candidate_key = Column(String(150), nullable=False)
    icd10_code = Column(String(20), nullable=True)
    hcc_code = Column(String(20), nullable=True)
    source_type = Column(String(50), nullable=False, default="assertion")
    lifecycle_state = Column(String(40), nullable=False)
    reason_code = Column(String(80), nullable=True)
    reason_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    effective_date = Column(Date, nullable=True)
    provider_name = Column(String(255), nullable=True)
    page_number = Column(Integer, nullable=True)
    exact_quote = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    review_status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("chart_id", "candidate_key", name="uq_diag_candidate_key"),
        Index("ix_diag_candidates_chart", "chart_id"),
        Index("ix_diag_candidates_patient", "patient_id"),
        Index("ix_diag_candidates_state", "lifecycle_state"),
        Index("ix_diag_candidates_icd", "icd10_code"),
        Index("ix_diag_candidates_hcc", "hcc_code"),
        Index("ix_diag_candidates_review", "review_status"),
        Index("ix_diag_candidates_effective_date", "effective_date"),
    )


class DiagnosisCandidateEvidence(Base):
    """Grounding spans for each diagnosis candidate."""
    __tablename__ = "diagnosis_candidate_evidence"

    id = Column(Integer, Sequence("diag_candidate_ev_id_seq"), primary_key=True)
    candidate_id = Column(Integer, ForeignKey("diagnosis_candidates.id", ondelete="CASCADE"), nullable=False)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=True)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    exact_quote = Column(Text, nullable=True)
    section_name = Column(String(100), nullable=True)
    is_primary = Column(Boolean, default=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_diag_candidate_ev_candidate", "candidate_id"),
        Index("ix_diag_candidate_ev_chart", "chart_id"),
        Index("ix_diag_candidate_ev_page", "page_number"),
    )


class DecisionTraceEvent(Base):
    """Deterministic rule path for HCC and HEDIS decisions."""
    __tablename__ = "decision_trace_events"

    id = Column(Integer, Sequence("decision_trace_events_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True)

    entity_type = Column(String(50), nullable=False)
    entity_key = Column(String(150), nullable=False)
    lifecycle_state = Column(String(40), nullable=False)
    reason_code = Column(String(80), nullable=True)
    reason_text = Column(Text, nullable=True)
    measure_id = Column(String(50), nullable=True)
    icd10_code = Column(String(20), nullable=True)
    hcc_code = Column(String(20), nullable=True)
    event_date = Column(Date, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_trace_events_chart", "chart_id"),
        Index("ix_trace_events_patient", "patient_id"),
        Index("ix_trace_events_entity", "entity_type", "entity_key"),
        Index("ix_trace_events_measure", "measure_id"),
        Index("ix_trace_events_icd", "icd10_code"),
        Index("ix_trace_events_hcc", "hcc_code"),
        Index("ix_trace_events_date", "event_date"),
    )


class EvaluationRun(Base):
    """Reproducible evaluation runs for before/after comparisons."""
    __tablename__ = "evaluation_runs"

    id = Column(Integer, Sequence("evaluation_runs_id_seq"), primary_key=True)
    run_label = Column(String(120), nullable=False)
    dataset_name = Column(String(120), nullable=False)
    scope = Column(String(40), nullable=False)
    git_ref = Column(String(80), nullable=True)
    metrics = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("run_label", "dataset_name", name="uq_eval_run_label_dataset"),
        Index("ix_eval_runs_dataset", "dataset_name"),
        Index("ix_eval_runs_scope", "scope"),
    )


class BenchmarkDataset(Base):
    """Registered benchmark datasets and provenance."""
    __tablename__ = "benchmark_datasets"

    id = Column(Integer, Sequence("benchmark_datasets_id_seq"), primary_key=True)
    dataset_name = Column(String(120), nullable=False, unique=True)
    dataset_type = Column(String(40), nullable=False)
    version = Column(String(40), nullable=True)
    source_path = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class GoldenLabel(Base):
    """Golden labels for chart-level benchmarking and review."""
    __tablename__ = "golden_labels"

    id = Column(Integer, Sequence("golden_labels_id_seq"), primary_key=True)
    dataset_id = Column(Integer, ForeignKey("benchmark_datasets.id", ondelete="CASCADE"), nullable=False)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)

    entity_type = Column(String(50), nullable=False)
    entity_key = Column(String(150), nullable=False)
    label_value = Column(String(120), nullable=False)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_golden_labels_dataset", "dataset_id"),
        Index("ix_golden_labels_chart", "chart_id"),
        Index("ix_golden_labels_patient", "patient_id"),
        Index("ix_golden_labels_entity", "entity_type", "entity_key"),
    )


class ReviewerDisagreement(Base):
    """Tracks human reviewer disagreements for targeted QA."""
    __tablename__ = "reviewer_disagreements"

    id = Column(Integer, Sequence("reviewer_disagreements_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    entity_type = Column(String(50), nullable=False)
    entity_key = Column(String(150), nullable=False)
    reviewer_a = Column(String(80), nullable=False)
    reviewer_b = Column(String(80), nullable=False)
    label_a = Column(String(120), nullable=False)
    label_b = Column(String(120), nullable=False)
    resolution = Column(String(120), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_reviewer_disagree_chart", "chart_id"),
        Index("ix_reviewer_disagree_patient", "patient_id"),
        Index("ix_reviewer_disagree_entity", "entity_type", "entity_key"),
    )


# =============================================================================
# MEMBER / ENROLLMENT TABLES (CLAUDE.md spec)
# =============================================================================

class MemberYear(Base):
    """Member-year records for RAF aggregation."""
    __tablename__ = "member_years"

    id = Column(Integer, Sequence("member_years_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    measurement_year = Column(Integer, nullable=False)
    plan_id = Column(String(50), nullable=True)
    lob = Column(String(50), nullable=True)  # line of business
    total_raf_score = Column(Float, nullable=True)
    demographic_raf = Column(Float, nullable=True)
    hcc_raf = Column(Float, nullable=True)
    hcc_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("patient_id", "measurement_year", name="uq_member_year"),
        Index("ix_member_years_patient", "patient_id"),
        Index("ix_member_years_year", "measurement_year"),
    )


class EnrollmentPeriod(Base):
    """Continuous enrollment tracking per member."""
    __tablename__ = "enrollment_periods"

    id = Column(Integer, Sequence("enrollment_periods_id_seq"), primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String(50), nullable=True)
    lob = Column(String(50), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_enrollment_patient", "patient_id"),
        Index("ix_enrollment_dates", "start_date", "end_date"),
    )


# =============================================================================
# ANALYTICS / DASHBOARD TABLES (CLAUDE.md spec)
# =============================================================================

class ModelPerformance(Base):
    """ML model performance metrics over time."""
    __tablename__ = "model_performance"

    id = Column(Integer, Sequence("model_performance_id_seq"), primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    hcc_code = Column(String(20), nullable=True)
    precision_score = Column(Float, nullable=True)
    recall_score = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    support = Column(Integer, nullable=True)
    evaluation_date = Column(DateTime, server_default=func.now())
    dataset = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_model_perf_model", "model_name", "model_version"),
        Index("ix_model_perf_hcc", "hcc_code"),
        Index("ix_model_perf_date", "evaluation_date"),
    )


class UserSession(Base):
    """Dashboard user session tracking."""
    __tablename__ = "user_sessions"

    id = Column(Integer, Sequence("user_sessions_id_seq"), primary_key=True)
    username = Column(String(100), nullable=False)
    session_token = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    last_active_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_user_sessions_user", "username"),
        Index("ix_user_sessions_active", "last_active_at"),
    )


class ScheduledJob(Base):
    """Batch processing job definitions."""
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, Sequence("scheduled_jobs_id_seq"), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    cron_expression = Column(String(50), nullable=True)
    job_type = Column(String(50), nullable=False, default="batch_process")
    config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_status = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_scheduled_jobs_active", "is_active"),
        Index("ix_scheduled_jobs_next", "next_run_at"),
    )


# =============================================================================
# AUDIT RISK SCORES (CLAUDE.md spec)
# =============================================================================

class AuditRiskScore(Base):
    """Per-chart and per-diagnosis audit risk levels."""
    __tablename__ = "audit_risk_scores"

    id = Column(Integer, Sequence("audit_risk_scores_id_seq"), primary_key=True)
    chart_id = Column(Integer, ForeignKey("charts.id", ondelete="CASCADE"), nullable=False)
    assertion_id = Column(Integer, ForeignKey("assertions.id", ondelete="CASCADE"), nullable=True)
    hcc_code = Column(String(20), nullable=True)
    icd_code = Column(String(20), nullable=True)
    risk_level = Column(String(20), nullable=False, default="low")  # low, medium, high
    risk_score = Column(Float, nullable=True)
    risk_factors = Column(JSON, nullable=True)  # {reason: ..., flags: [...]}
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_audit_risk_chart", "chart_id"),
        Index("ix_audit_risk_level", "risk_level"),
    )
