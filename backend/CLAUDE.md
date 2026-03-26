# MedInsight 360 — Unified Project Build Prompt

> **Copy this entire prompt and give it to Claude in your new project folder at `C:\Next-Era\ClaudeProjects\medinsight360`**
> **Attach BOTH HTML documentation files along with this prompt.**

---

## THE PROMPT (START COPYING FROM HERE)

---

You are building **MedInsight 360** — a unified Risk Adjustment + Quality Intelligence platform that combines two existing production projects into one cohesive, configurable, world-class product.

## SOURCE PROJECTS TO READ AND INTEGRATE

**CRITICAL FIRST STEP**: Before writing ANY code, you MUST thoroughly read and analyze BOTH existing projects:

FIRST STEP — Read these in order:

1. Read ./docs/RA_ENGINE_UNIFIED_DOCUMENTATION.html
2. Read ./docs/MedInsights_Platform_Documentation.html
   (These 2 files contain complete documentation of both projects)

3. Then read the actual source code from:
   - C:\Next-Era\ClaudeProjects\medinsights_platform  (all .py files)
   - C:\Next-Era\ClaudeProjects\MLDataPrep\ra-training-data-factory  (all .py, .json, .csv files)
   
   Focus on: Python files, config files, prompt templates, 
   model files, reference data (V28 mappings, ICD catalogs)


### Project 1 — MedInsights Platform
**Location**: `C:\Next-Era\ClaudeProjects\medinsights_platform`

Read ALL files in this project. Key things to extract and reuse:
- `smartpdf.py` — PDF intake, per-page quality scoring, GPT-4o Vision OCR fallback
- `langextract.py` / extraction pipeline files — The 5 LLM pipelines (Demographics, Sentences, Risk Dx, HEDIS Evidence, Encounters)
- All LLM prompt templates (prompts 1–5 for each pipeline)
- `config.py` or any configuration files — API keys, model settings, DB connection strings
- Database schema / models — The 38 PostgreSQL tables (patients, diagnoses, hcc_mappings, raf_summaries, hedis tables, encounters, audit_logs, configs, etc.)
- FastAPI endpoints — All 22 REST API endpoints
- JSON output file structures (files 0–7)
- The review_status workflow (pending/approved/rejected)
- The parallelism architecture (3 PDFs × 5 pipelines × 4 chunks)
- Medical chart samples in the project for testing
- Any utility functions, helpers, validators
- The negation model (6 statuses: active, negated, resolved, historical, family_history, uncertain)
- HCC mapping logic and RAF scoring post-processing
- All requirements.txt / dependencies

### Project 2 — RA Training Data Factory
**Location**: `C:\Next-Era\ClaudeProjects\MLDataPrep\ra-training-data-factory`

Read ALL files in this project. Key things to extract and reuse:
- **BioClinicalBERT model** — The multi-label HCC predictor, training scripts, model weights/checkpoints, tokenizer configs
- **CMS-HCC V28 reference data** — The complete ICD-10-CM to HCC mapping tables, hierarchy rules, coefficient tables, 115 payable HCC categories
- **TF-IDF ICD retrieval system** — The TF-IDF vectorizer over 7,903 ICD-10-CM codes, the span proposer logic, similarity thresholds
- **ConText/NegEx implementation** — The deterministic negation detection rules and context gating logic
- **GPT-4o verification pipeline** — The structured JSON verification prompts for ICD + MEAT validation
- **6-layer JSON output schema** — ICD Layer, HCC Layer, Mapping Layer, RAF Layer, HEDIS Layer, Audit Pack
- **Evaluation framework** — Note-level + member-year metrics, RAF-weighted precision/recall, per-HCC confusion
- **Training data assets** — MIMIC/Synthea datasets, any preprocessed training examples
- **Reference mappings** — V28 ICD→HCC crosswalks, hierarchy suppression rules, demographic coefficient tables
- **Any embedding models** — If sentence embeddings or clinical embeddings are used alongside TF-IDF

### Attached Documentation
I am attaching two HTML documentation files that describe both projects in exhaustive detail:
1. `RA_ENGINE_UNIFIED_DOCUMENTATION.html` — Complete documentation of the RA Engine
2. `MedInsights_Platform_Documentation.html` — Complete documentation of the MedInsights Platform

**Read these documents THOROUGHLY.** They contain every schema definition, every pipeline description, every prompt template, every table structure, and every configuration option. These are your source of truth.

---

## TARGET PROJECT

**New Project Location**: `C:\Next-Era\ClaudeProjects\medinsight360`

Build the unified project HERE. Copy/adapt code from both source projects. Do NOT modify the source projects.

---

## WHAT TO BUILD — DETAILED SPECIFICATION

### A. PROJECT STRUCTURE

Create this exact folder structure:

```
medinsight360/
├── README.md                          # Project overview and setup guide
├── requirements.txt                   # All Python dependencies
├── setup.py                           # Package setup
├── .env.example                       # Environment variable template
├── .env                               # Actual env file (API keys, DB, etc.)
├── alembic.ini                        # Database migration config
├── alembic/                           # DB migration scripts
│   └── versions/
│
├── config/
│   ├── __init__.py
│   ├── settings.py                    # Central configuration (Pydantic BaseSettings)
│   ├── feature_flags.py               # Feature toggles (enable/disable RA, HEDIS, etc.)
│   ├── model_config.py                # ML model paths, thresholds, versions
│   ├── llm_config.py                  # LLM provider settings (OpenAI, Azure, Gemini)
│   ├── pipeline_config.py             # Pipeline parallelism, chunk sizes, timeouts
│   └── prompts/                       # All LLM prompt templates as .txt or .jinja2
│       ├── demographics_extraction.txt
│       ├── sentence_categorization.txt
│       ├── risk_dx_extraction.txt
│       ├── hedis_evidence.txt
│       ├── encounter_extraction.txt
│       ├── icd_meat_verification.txt
│       └── clinical_summary.txt
│
├── core/
│   ├── __init__.py
│   ├── orchestrator.py                # Main pipeline orchestrator
│   ├── feature_registry.py            # Feature flag registry + dynamic enable/disable
│   └── exceptions.py                  # Custom exception classes
│
├── ingestion/                         # Layer A — Ingestion & Normalization
│   ├── __init__.py
│   ├── pdf_processor.py               # PDF intake from medinsights smartpdf.py
│   ├── quality_scorer.py              # Per-page text quality scoring
│   ├── ocr_engine.py                  # GPT-4o Vision OCR fallback
│   ├── text_normalizer.py             # Section segmentation, encounter-delimited chunks
│   └── page_extractor.py              # Raw text extraction with page boundaries
│
├── extraction/                        # Layer B — LLM Extraction Pipelines
│   ├── __init__.py
│   ├── base_pipeline.py               # Abstract base for all extraction pipelines
│   ├── demographics_pipeline.py       # Pipeline 1: Demographics
│   ├── sentence_pipeline.py           # Pipeline 2: Clinical sentences + negation
│   ├── risk_dx_pipeline.py            # Pipeline 3: Risk adjustment diagnoses
│   ├── hedis_pipeline.py              # Pipeline 4: HEDIS evidence
│   ├── encounter_pipeline.py          # Pipeline 5: Encounters
│   ├── llm_client.py                  # Unified LLM client (OpenAI/Azure/Gemini)
│   └── chunk_manager.py               # Text chunking with overlap for LLM context
│
├── ml_engine/                         # Layer C — ML Prediction (from RA Engine)
│   ├── __init__.py
│   ├── hcc_predictor.py               # BioClinicalBERT multi-label HCC predictor
│   ├── icd_retriever.py               # TF-IDF + embedding ICD-10 retrieval
│   ├── negation_detector.py           # ConText/NegEx deterministic gating
│   ├── span_proposer.py               # Evidence span extraction and linking
│   └── models/                        # Model weights, tokenizers, vectorizers
│       ├── bioclinicalbert/           # Copy model checkpoint from ra-training-data-factory
│       ├── tfidf_vectorizer.pkl       # Copy TF-IDF vectorizer
│       ├── icd10_catalog.json         # Full ICD-10-CM code catalog (7,903 codes)
│       └── label_encoder.pkl          # HCC label encoder
│
├── decisioning/                       # Layer C — Verification & Decisioning
│   ├── __init__.py
│   ├── icd_verifier.py                # GPT-4o structured ICD + MEAT verification
│   ├── hcc_mapper.py                  # ICD→HCC V28 mapping with hierarchy suppression
│   ├── raf_calculator.py              # RAF score computation (encounter + member-year)
│   ├── hedis_evaluator.py             # HEDIS measure eligibility + numerator/gap logic
│   ├── audit_scorer.py                # Audit risk scoring per diagnosis
│   └── reference/                     # CMS reference data
│       ├── v28_icd_hcc_mappings.csv   # Copy from RA Engine
│       ├── v28_coefficients.csv       # RAF coefficients by demographic segment
│       ├── v28_hierarchy_rules.json   # Hierarchy suppression rules
│       └── hedis_measure_specs.json   # Measure specifications (age, gender, lookback)
│
├── database/                          # Layer D — Persistence
│   ├── __init__.py
│   ├── connection.py                  # PostgreSQL connection pool (asyncpg or psycopg2)
│   ├── models.py                      # SQLAlchemy ORM models for ALL tables
│   ├── repositories/                  # Data access layer
│   │   ├── __init__.py
│   │   ├── patient_repo.py
│   │   ├── chart_repo.py
│   │   ├── diagnosis_repo.py
│   │   ├── hcc_repo.py
│   │   ├── raf_repo.py
│   │   ├── hedis_repo.py
│   │   ├── encounter_repo.py
│   │   ├── audit_repo.py
│   │   ├── config_repo.py
│   │   └── pipeline_repo.py
│   └── migrations/                    # Alembic migration scripts
│
├── api/                               # Layer E — REST API
│   ├── __init__.py
│   ├── main.py                        # FastAPI app initialization
│   ├── middleware.py                   # Auth, CORS, logging, error handling
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── charts.py                  # Chart upload, processing, status
│   │   ├── patients.py                # Patient demographics, member info
│   │   ├── clinical.py                # Diagnoses, sentences, vitals, labs
│   │   ├── risk_adjustment.py         # HCC, RAF, payable codes
│   │   ├── hedis.py                   # HEDIS measures, gaps, evidence
│   │   ├── encounters.py              # Encounter timeline
│   │   ├── audit.py                   # Audit logs, review actions
│   │   ├── config.py                  # Runtime configuration management
│   │   ├── pipeline.py                # Pipeline status, logs, re-run
│   │   └── dashboard.py              # Dashboard data endpoints
│   └── schemas/                       # Pydantic request/response models
│       ├── __init__.py
│       ├── chart_schemas.py
│       ├── clinical_schemas.py
│       ├── risk_schemas.py
│       ├── hedis_schemas.py
│       └── config_schemas.py
│
├── dashboard/                         # Dashboard UI (React or HTML+JS)
│   ├── index.html                     # Main dashboard SPA
│   ├── assets/
│   │   ├── styles.css
│   │   └── app.js
│   └── components/                    # If using component-based approach
│
├── outputs/                           # Generated output files per chart run
│   └── .gitkeep
│
├── logs/                              # Application logs
│   └── .gitkeep
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_ingestion.py
│   ├── test_extraction.py
│   ├── test_ml_engine.py
│   ├── test_decisioning.py
│   └── test_api.py
│
└── scripts/
    ├── init_db.py                     # Create all database tables
    ├── seed_reference_data.py         # Load V28 mappings, HCC codes, HEDIS specs
    ├── run_chart.py                   # CLI: process a single chart
    ├── run_batch.py                   # CLI: batch process multiple charts
    └── export_results.py             # Export results to CSV/JSON
```

### B. CORE PIPELINE — THE HCC PAYABLE PACK FLOW

This is the PRIMARY flow. When given a medical chart PDF path, the system must:

#### Step 1: PDF Ingestion (from MedInsights `smartpdf.py`)
- Accept PDF file path as input
- Extract text per page with page boundaries preserved
- Score each page for text quality (0-100)
- For pages below quality threshold → invoke GPT-4o Vision OCR
- Output: normalized text segments with page numbers, quality scores, OCR flags

#### Step 2: LLM Extraction (from MedInsights pipelines)
Run these 5 LLM pipelines IN PARALLEL on the extracted text:

**Pipeline 1 — Demographics**: Extract patient name, DOB, gender, MBI, insurance, race/ethnicity, address, phone
**Pipeline 2 — Clinical Sentences**: Categorize every clinical sentence into 22 categories with 6-status negation (active/negated/resolved/historical/family_history/uncertain). Preserve source page + character offsets
**Pipeline 3 — Risk Adjustment Diagnoses**: Extract all mentioned diagnoses with ICD-10 codes, supporting text, negation status, date of service, provider, source section
**Pipeline 4 — HEDIS Evidence**: Extract evidence for quality measures — BP readings, A1C values, eye exams, colonoscopies, mammograms, medications, screenings, immunizations
**Pipeline 5 — Encounters**: Extract all encounters with date of service, provider, facility, visit type, CPT codes

Each pipeline:
- Uses configurable LLM prompts (from `config/prompts/`)
- Chunks text into configurable-size segments (default 10K chars with overlap)
- Calls LLM with structured JSON output format
- Merges chunk results with deduplication
- Outputs structured JSON

#### Step 3: ML HCC Prediction (from RA Engine)
- Feed extracted clinical text to **BioClinicalBERT multi-label HCC predictor**
- Model outputs candidate HCC categories with confidence scores
- This runs on the FULL text, not just LLM-extracted diagnoses
- The ML model catches patterns the LLM may miss in long documents
- Output: list of predicted HCC codes with confidence scores

#### Step 4: ICD-10 Retrieval (from RA Engine)
- For each ML-predicted HCC, use **TF-IDF retrieval** over the 7,903 ICD-10-CM catalog to find matching ICD codes
- Also use the text spans identified by the span proposer to match clinical language to ICD descriptions
- Score each candidate ICD by similarity to the clinical text
- Apply the V28 ICD→HCC mapping table to verify the ICD actually maps to the predicted HCC
- Output: candidate ICD-10 codes with similarity scores and text spans

#### Step 5: Negation & Context Gating (from RA Engine)
- Apply **ConText/NegEx deterministic rules** to every candidate ICD
- Filter out: negated mentions, family history (unless the ICD is family-history-specific), hypothetical/conditional mentions
- Assign polarity status: active / negated / resolved / historical / family_history / uncertain
- This is a DETERMINISTIC gate — no ML guessing. Pure clinical logic
- Output: filtered candidate list with polarity assignments

#### Step 6: LLM Verification + MEAT Validation (from RA Engine)
- For each surviving candidate ICD, call **GPT-4o** with structured verification prompt
- The LLM must verify:
  - Is this diagnosis supported by the clinical text? (yes/no + evidence quote)
  - MEAT check: Is there evidence of Monitoring, Evaluation, Assessment, or Treatment?
  - What is the date of service?
  - What is the provider context?
  - Confidence score (0.0–1.0)
- Output: verified ICD codes with MEAT breakdown, evidence spans, confidence

#### Step 7: HCC Mapping + Hierarchy + RAF (from RA Engine)
- Map verified ICD-10 codes to HCC categories using V28 mapping table
- Apply **hierarchy suppression** (e.g., HCC 18 suppresses HCC 19 if both present)
- Apply **constraining rules** (V28's same-coefficient grouping)
- Compute **RAF score** per encounter and aggregated per member-year
- Use demographic coefficients (age, gender, dual-eligible, institutional, etc.)
- Output: Payable HCC list, RAF breakdown, hierarchy explanations

#### Step 8: Output Generation
Generate these output files per chart run:

```
outputs/{chart_id}/
├── 0_demographics.json
├── 1_clinical_sentences.json
├── 2_risk_diagnoses.json        # LLM-extracted diagnoses (intermediate)
├── 3_hedis_evidence.json
├── 4_encounters.json
├── 5_ml_hcc_predictions.json    # BioClinicalBERT predictions
├── 6_icd_retrieval.json         # TF-IDF retrieved ICDs
├── 7_verified_icds.json         # Post-verification with MEAT
├── 8_payable_hcc_pack.json      # FINAL: Payable HCCs + RAF + evidence
├── 9_hedis_quality_pack.json    # HEDIS measures + gaps
├── 10_audit_pack.json           # Audit trail + risk scores
├── pipeline_log.json            # Processing log with timings
└── summary.json                 # Human-readable summary
```

#### The Payable HCC Pack JSON (file 8) must contain:

```json
{
  "chart_id": "...",
  "patient": { "name": "...", "dob": "...", "gender": "...", "mbi": "..." },
  "measurement_year": 2026,
  "processing_timestamp": "...",
  "payable_hccs": [
    {
      "hcc_code": "HCC 18",
      "hcc_description": "Diabetes with Chronic Complications",
      "raf_weight": 0.302,
      "hierarchy_applied": true,
      "suppresses": ["HCC 19"],
      "supported_icds": [
        {
          "icd10_code": "E11.65",
          "icd10_description": "Type 2 diabetes mellitus with hyperglycemia",
          "confidence": 0.92,
          "ml_confidence": 0.87,
          "llm_confidence": 0.95,
          "polarity": "active",
          "negation_method": "context_negex",
          "meat_evidence": {
            "monitored": true,
            "evaluated": true,
            "assessed": true,
            "treated": true,
            "monitoring_text": "A1C checked quarterly, last value 8.2%",
            "treatment_text": "Continue metformin 1000mg BID, added glipizide 5mg"
          },
          "evidence_spans": [
            {
              "text": "Patient has type 2 diabetes with chronic complications including hyperglycemia...",
              "page": 3,
              "section": "Assessment/Plan",
              "char_start": 1245,
              "char_end": 1340
            }
          ],
          "date_of_service": "2025-08-15",
          "provider": "Dr. Smith"
        }
      ],
      "audit_risk": "low"
    }
  ],
  "unsupported_candidates": [
    {
      "icd10_code": "...",
      "reason": "Negated — 'no evidence of...'",
      "polarity": "negated",
      "source_text": "..."
    }
  ],
  "raf_summary": {
    "total_raf_score": 1.847,
    "demographic_raf": 0.523,
    "hcc_raf": 1.324,
    "hcc_count": 5,
    "payable_hcc_count": 4,
    "suppressed_hcc_count": 1
  },
  "pipeline_metadata": {
    "ml_model_version": "bioclinicalbert-v28-1.0",
    "llm_model": "gpt-4o-2024-08-06",
    "tfidf_threshold": 0.35,
    "processing_time_seconds": 45.2,
    "pages_processed": 28,
    "ocr_pages": 3
  }
}
```

### C. DATABASE — COMPLETE SCHEMA

Create ALL tables in PostgreSQL. Use SQLAlchemy models. Include proper sequences, indexes, foreign keys, constraints.

**Required tables (minimum — add more as needed from both source projects):**

**Core Tables:**
- `patients` — Patient demographics, MBI, insurance, gender, DOB, race/ethnicity
- `charts` — Chart metadata, file path, page count, quality score, status, created/updated
- `chart_pages` — Per-page text content, quality score, OCR flag, page number
- `pipeline_runs` — Pipeline execution records, status, start/end time, config snapshot
- `pipeline_logs` — Detailed log entries per pipeline step with timing

**Clinical Extraction Tables:**
- `clinical_sentences` — Extracted sentences with category (22 types), negation status (6 types), page, offsets
- `demographics` — Extracted patient info per chart
- `encounters` — DOS, provider, facility, visit type, CPT codes
- `vitals` — BP readings, weight, height, BMI with dates
- `lab_results` — A1C, LDL, creatinine, etc. with values, dates, units
- `medications` — Drug name, dose, frequency, start/end dates, prescriber
- `procedures` — CPT/HCPCS codes, dates, providers
- `screenings` — Colonoscopy, mammogram, eye exam, etc. with dates and results

**Risk Adjustment Tables:**
- `diagnoses` — All extracted diagnoses: ICD-10 code, description, negation status, supporting text, source section, page, DOS, provider, confidence, source_method (llm/ml/rule), review_status
- `ml_hcc_predictions` — BioClinicalBERT predictions: HCC code, confidence, text spans
- `icd_retrievals` — TF-IDF retrieved ICDs: ICD code, similarity score, matched text
- `verified_icds` — Post-LLM-verification: ICD code, MEAT evidence, confidence, polarity
- `diagnosis_hcc_mappings` — ICD→HCC mappings with hierarchy info, suppression flags, V28 version
- `payable_hccs` — Final payable HCC list per chart/member-year with RAF weights
- `raf_summaries` — Total RAF scores per chart, encounter, member-year with breakdown
- `hcc_hierarchy_log` — Which HCCs were suppressed and why

**HEDIS Tables:**
- `hedis_eligibility` — Member eligibility per measure per measurement year
- `hedis_measures` — Measure definitions (code, description, age range, gender, lookback)
- `hedis_evidence` — Evidence items linked to measures with dates, values, status
- `hedis_gaps` — Identified gaps with missing evidence details and next actions
- `bp_readings` — Blood pressure specifics for CBP/BPC-E
- `diabetes_indicators` — A1C, eye exam, kidney for CDC measures
- `cancer_screenings` — Colonoscopy, mammogram, cervical for COL/BCS/CCS

**Member/Enrollment Tables:**
- `members` — Member enrollment records, plan, LOB, effective dates
- `member_years` — Member-year records for RAF aggregation
- `enrollment_periods` — Continuous enrollment tracking per member

**Audit & Review Tables:**
- `audit_logs` — Every action logged: who, what, when, before/after values
- `review_actions` — Coder accept/reject/edit actions on diagnoses, HCCs, HEDIS
- `audit_risk_scores` — Per-chart and per-diagnosis audit risk levels
- `meat_evidence` — MEAT breakdown per diagnosis with supporting text references

**Configuration Tables:**
- `system_config` — Key-value configuration store (managed via dashboard)
- `llm_configs` — LLM provider settings, model names, temperatures, max tokens
- `pipeline_configs` — Feature flags, pipeline settings, thresholds
- `prompt_templates` — LLM prompt templates stored in DB (editable via dashboard)
- `model_versions` — ML model version tracking with performance metrics
- `api_keys` — API key management (encrypted storage)

**Dashboard/Analytics Tables:**
- `processing_stats` — Per-chart processing metrics (time, tokens, pages)
- `model_performance` — F1, precision, recall tracking per model version per HCC
- `user_sessions` — Dashboard user tracking
- `scheduled_jobs` — Batch processing job definitions

### D. CONFIGURATION SYSTEM

The project must be **highly configurable** without code changes:

#### 1. Environment Variables (.env file)
```
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=medinsight360
POSTGRES_USER=medinsight
POSTGRES_PASSWORD=<password>

# LLM Providers
OPENAI_API_KEY=<key>
AZURE_OPENAI_ENDPOINT=<endpoint>
AZURE_OPENAI_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
GOOGLE_GEMINI_KEY=<key>

# Active LLM Provider: openai | azure | gemini
ACTIVE_LLM_PROVIDER=openai
ACTIVE_LLM_MODEL=gpt-4o

# ML Models
ML_MODEL_PATH=./ml_engine/models/bioclinicalbert
TFIDF_VECTORIZER_PATH=./ml_engine/models/tfidf_vectorizer.pkl
ICD_CATALOG_PATH=./ml_engine/models/icd10_catalog.json

# Feature Flags
ENABLE_RISK_ADJUSTMENT=true
ENABLE_HEDIS=true
ENABLE_ML_PREDICTIONS=true
ENABLE_LLM_VERIFICATION=true
ENABLE_OCR_FALLBACK=true
ENABLE_PARALLEL_PIPELINES=true

# Pipeline Settings
MAX_CONCURRENT_CHARTS=3
MAX_CONCURRENT_PIPELINES=5
CHUNK_SIZE=10000
CHUNK_OVERLAP=500
QUALITY_THRESHOLD=60
TFIDF_SIMILARITY_THRESHOLD=0.35
ML_CONFIDENCE_THRESHOLD=0.3
LLM_VERIFICATION_THRESHOLD=0.5

# Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

#### 2. Feature Flags (Dynamic)
Users must be able to tell the system what features to enable for a chart run:
- "I only need Risk Adjustment" → disable HEDIS pipelines
- "I only need HEDIS" → disable RA pipelines
- "Skip ML, use LLM only" → disable BioClinicalBERT
- "Skip OCR" → disable Vision fallback
- These can be set globally (in config) or per-chart (in API request)

#### 3. Pipeline Configuration
All these must be configurable via dashboard or config:
- Which LLM provider and model to use
- Prompt templates (editable via dashboard)
- Chunk size and overlap
- Confidence thresholds for ML and LLM
- TF-IDF similarity threshold
- Parallelism settings
- V28 model version and reference data version
- HEDIS measurement year

### E. CLI INTERFACE

Create `scripts/run_chart.py` that works like:

```bash
# Full pipeline (Risk + HEDIS + everything)
python scripts/run_chart.py --chart-path "/path/to/medical_chart.pdf"

# Risk Adjustment only
python scripts/run_chart.py --chart-path "/path/to/chart.pdf" --mode risk_only

# HEDIS only
python scripts/run_chart.py --chart-path "/path/to/chart.pdf" --mode hedis_only

# HCC Pack only (skip HEDIS, focus on payable)
python scripts/run_chart.py --chart-path "/path/to/chart.pdf" --mode hcc_pack

# Custom config overrides
python scripts/run_chart.py --chart-path "/path/to/chart.pdf" \
  --llm-provider azure \
  --enable-ml true \
  --tfidf-threshold 0.4 \
  --measurement-year 2026
```

### F. REST API ENDPOINTS

Implement these FastAPI endpoints:

```
# Chart Management
POST   /api/charts/upload              # Upload and process a chart
POST   /api/charts/process/{chart_id}  # Re-process a chart
GET    /api/charts/{chart_id}          # Get chart status and metadata
GET    /api/charts/{chart_id}/pages    # Get page-level text and quality
GET    /api/charts                     # List all charts with filters
DELETE /api/charts/{chart_id}          # Delete chart and all related data

# Clinical Data
GET    /api/clinical/{chart_id}/diagnoses     # All diagnoses with evidence
GET    /api/clinical/{chart_id}/sentences     # Clinical sentences with categories
GET    /api/clinical/{chart_id}/vitals        # Vital signs
GET    /api/clinical/{chart_id}/labs          # Lab results
GET    /api/clinical/{chart_id}/medications   # Medications
GET    /api/clinical/{chart_id}/encounters    # Encounter timeline

# Risk Adjustment
GET    /api/risk/{chart_id}/hcc-pack          # Complete Payable HCC Pack
GET    /api/risk/{chart_id}/raf-summary       # RAF score breakdown
GET    /api/risk/{chart_id}/ml-predictions    # Raw ML predictions
GET    /api/risk/{chart_id}/icd-retrievals    # TF-IDF retrieved ICDs
GET    /api/risk/{chart_id}/verified-icds     # Post-verification ICDs
GET    /api/risk/{chart_id}/hierarchy         # HCC hierarchy details

# HEDIS Quality
GET    /api/hedis/{chart_id}/measures         # Measure eligibility + evidence
GET    /api/hedis/{chart_id}/gaps             # Identified gaps
GET    /api/hedis/{chart_id}/evidence         # All HEDIS evidence items

# Audit
GET    /api/audit/{chart_id}/pack             # Complete audit pack
GET    /api/audit/{chart_id}/risk-scores      # Per-diagnosis risk scores
GET    /api/audit/logs                        # System audit logs

# Review Workflow
PUT    /api/review/diagnosis/{id}             # Accept/reject/edit diagnosis
PUT    /api/review/hcc/{id}                   # Accept/reject HCC
GET    /api/review/pending                    # All pending review items

# Configuration (Dashboard)
GET    /api/config                            # All configuration
PUT    /api/config                            # Update configuration
GET    /api/config/prompts                    # Get all prompt templates
PUT    /api/config/prompts/{name}             # Update a prompt template
GET    /api/config/feature-flags              # Get feature flags
PUT    /api/config/feature-flags              # Update feature flags
GET    /api/config/model-versions             # ML model versions

# Pipeline Management
GET    /api/pipeline/runs                     # Pipeline run history
GET    /api/pipeline/runs/{run_id}/logs       # Logs for a specific run
POST   /api/pipeline/runs/{run_id}/rerun      # Re-run a pipeline

# Dashboard Data
GET    /api/dashboard/stats                   # Overall system stats
GET    /api/dashboard/db-stats                # Database table counts and sizes
GET    /api/dashboard/processing-metrics      # Processing time, success rates
GET    /api/dashboard/model-performance       # ML model metrics over time
GET    /api/dashboard/recent-activity         # Recent chart processing activity
```

### G. DASHBOARD

After the core project is built and working, build a **management dashboard** as a single-page HTML application that calls the API endpoints above. The dashboard must include:

**Pages/Sections:**

1. **Overview** — System health, total charts processed, average processing time, success rate, recent activity feed

2. **Chart Manager** — Upload new charts, view all charts with status, click to see full results, filter by status/date/patient

3. **HCC Pack Viewer** — For any chart: show payable HCCs, supported ICDs, MEAT evidence, RAF breakdown, hierarchy visualization, evidence text with page references

4. **HEDIS Viewer** — Measure eligibility matrix, gap identification, evidence items per measure

5. **Configuration Panel** — Edit ALL settings from the dashboard:
   - API keys (masked input)
   - LLM provider selection (dropdown: OpenAI / Azure / Gemini)
   - Model selection
   - Feature flags (toggle switches)
   - Pipeline thresholds (sliders or number inputs)
   - Prompt template editor (code editor with syntax highlighting)
   - Measurement year settings

6. **Database Manager** — Table stats (row counts, sizes), recent records preview, data quality indicators

7. **Pipeline Monitor** — Running/completed/failed pipelines, processing logs with timestamps, token usage tracking, re-run capabilities

8. **Model Performance** — ML model metrics (F1, precision, recall per HCC), confusion matrices, trend over time

9. **Audit Trail** — Complete action log, review history, coder activity

**Dashboard Tech:**
- Single HTML file with embedded CSS + JS
- Use Tailwind CSS from CDN for styling
- Use Alpine.js or vanilla JS for interactivity
- Calls the FastAPI endpoints above
- Dark theme, professional design
- Responsive layout

### H. CRITICAL IMPLEMENTATION DETAILS

#### ICD Retrieval Strategy — The Dual Approach
This is where the competitive edge comes from. Do NOT rely on ICD codes alone from LLM extraction:

1. **LLM Route** (Pipeline 3): LLM reads clinical text and suggests ICD-10 codes directly. Good for obvious diagnoses but can hallucinate codes or miss subtle ones.

2. **ML + Retrieval Route** (RA Engine approach):
   - BioClinicalBERT predicts HCC CATEGORIES (not ICDs) from raw text
   - For each predicted HCC category, TF-IDF retrieves the most similar ICD-10 codes from the V28-mapped subset
   - This finds ICDs by matching clinical LANGUAGE to ICD DESCRIPTIONS, not by asking the LLM to guess codes
   - The V28 mapping table constrains which ICDs are even considered

3. **Merge + Deduplicate**: Combine candidates from both routes, deduplicate, then run through NegEx gating and LLM verification

4. **Why this wins**: The ML model captures HCC patterns the LLM misses in 40-page charts. The TF-IDF retrieval finds the correct ICD-10 specificity that LLMs often get wrong (e.g., E11.65 vs E11.9). The combination catches more legitimate diagnoses with higher code specificity.

#### Negation — The 6-Status Model
Do not simplify to binary (negated/not). Use all 6 statuses everywhere:
- **active** — Currently present, being managed
- **negated** — Explicitly denied ("no evidence of", "ruled out")
- **resolved** — Was present but no longer ("diabetes resolved after transplant")
- **historical** — Past occurrence, unclear if still active ("history of stroke in 2018")
- **family_history** — Family member condition ("mother had breast cancer")
- **uncertain** — Possible, suspected, differential ("possible CHF", "r/o PE")

Only `active` diagnoses should be payable. `historical` may be payable if recaptured with current-year encounter evidence showing ongoing management.

#### MEAT Validation — Per Diagnosis
Every payable ICD must have at least one MEAT element documented:
- **M**onitored: Labs ordered, vital signs tracked, follow-up scheduled
- **E**valuated: Symptoms assessed, exam findings documented
- **A**ssessed: Diagnosis acknowledged in assessment/plan, clinical reasoning documented
- **T**reated: Medications prescribed, procedures performed, therapy ordered

The LLM verification step must extract specific text evidence for each MEAT element found.

### I. WHAT TO COPY FROM SOURCE PROJECTS

**From medinsights_platform, copy and adapt:**
- PDF processing logic (smartpdf.py)
- LLM prompt templates (all 5 pipeline prompts)
- Database schema (all table definitions)
- FastAPI endpoint patterns
- JSON output structure (files 0–7)
- Configuration management
- Review workflow logic
- Medical chart samples for testing

**From ra-training-data-factory, copy and adapt:**
- BioClinicalBERT model weights and training config
- TF-IDF vectorizer (fitted on ICD-10 catalog)
- ICD-10-CM catalog (7,903 codes)
- V28 mapping tables (ICD→HCC, coefficients, hierarchy)
- ConText/NegEx rules and implementation
- GPT-4o verification prompts
- 6-layer JSON output schema
- Evaluation framework code
- Any pre-trained embeddings

### J. BUILD ORDER

Execute in this exact order:

1. **Read both projects completely** — understand every file, every function, every table
2. **Create project structure** — folders, __init__.py files, requirements.txt
3. **Set up configuration** — .env, settings.py, feature_flags.py
4. **Build database layer** — models.py with ALL tables, connection.py, init_db.py
5. **Build ingestion layer** — PDF processor, quality scorer, OCR engine, text normalizer
6. **Build extraction layer** — All 5 LLM pipelines with prompt templates
7. **Build ML engine** — Copy BioClinicalBERT, TF-IDF, NegEx. Wire them up
8. **Build decisioning layer** — ICD verifier, HCC mapper, RAF calculator, audit scorer
9. **Build orchestrator** — Wire all layers together with feature flag support
10. **Build CLI** — run_chart.py that processes a chart end-to-end
11. **Build API** — All FastAPI endpoints
12. **Test with sample charts** — Use charts from medinsights_platform
13. **Build dashboard** — Management UI calling the API
14. **Seed reference data** — Load V28 tables, HEDIS specs, initial configs

### K. QUALITY REQUIREMENTS

- All Python code must have type hints
- Use async/await for IO-bound operations (DB, LLM calls)
- Proper error handling with custom exceptions
- Structured logging (JSON format) to both console and file
- Every database operation must be atomic with proper transactions
- Every LLM call must be logged with prompt, response, tokens used, time elapsed
- Every ML prediction must be logged with input hash, output, confidence, time
- Configuration changes must be audit-logged
- API responses must follow consistent schema with proper HTTP status codes

---

## START BUILDING

Begin by reading both source projects thoroughly. Then create the project structure and start building layer by layer following the build order above. After each layer, verify it works before moving to the next.

The medical charts from medinsights_platform should be copied to this project for testing. After building the core pipeline, process a chart end-to-end and verify the Payable HCC Pack output is correct and complete.

Then build the dashboard as the management interface on top.

**This is a production-grade product, not a prototype. Build it accordingly.**

---

## END OF PROMPT
