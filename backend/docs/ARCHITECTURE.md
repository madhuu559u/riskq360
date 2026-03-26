# MedInsight 360 — Architecture Document

## Overview

MedInsight 360 is a unified Risk Adjustment + Quality Intelligence platform. It processes medical chart PDFs through a single-pass LLM extraction pipeline, maps clinical assertions to HCC codes and HEDIS quality measures, computes RAF scores, and persists all results to a relational database exposed through a REST API.

**Scale**: 135 Python files, ~21,800 lines of code, 22 database tables, 43 API endpoints, 7 services, 8 repositories.

---

## System Architecture

```
PDF Input
    |
    v
+---------------------------+
|  Extraction Layer          |
|  (MiniMax Single-Pass LLM) |
|  12 modules                |
+---------------------------+
    |
    v  (assertions JSON)
+---------------------------+
|  Core Orchestrator         |
|  HCC Bridge + HEDIS Bridge |
+---------------------------+
    |               |
    v               v
+----------+  +-----------+
| Decisioning|  | HEDIS     |
| HCC Mapper |  | Engine    |
| RAF Calc   |  | 122 YAML  |
+----------+  +-----------+
    |               |
    v               v
+---------------------------+
|  Persistence Layer         |
|  22 SQLAlchemy ORM Tables  |
|  Sync (batch) + Async (API)|
+---------------------------+
    |
    v
+---------------------------+
|  Service Layer             |
|  7 Business Logic Services |
+---------------------------+
    |
    v
+---------------------------+
|  API Layer                 |
|  FastAPI, 43 endpoints     |
|  10 routers                |
+---------------------------+
    |
    v
+---------------------------+
|  Dashboard                 |
|  HTML + Tailwind + Alpine  |
+---------------------------+
```

---

## Directory Structure

```
medinsight360/
|-- api/                      # REST API (FastAPI)
|   |-- main.py               # App factory, lifespan, CORS, router mounts
|   |-- middleware.py          # Request logging, error handling
|   |-- routers/              # 10 route modules (43 endpoints total)
|   |   |-- charts.py         # 5 endpoints: upload, list, get, pages, delete
|   |   |-- clinical.py       # 8 endpoints: assertions, diagnoses, meds, vitals, labs, encounters, categories, ra-candidates
|   |   |-- risk_adjustment.py# 3 endpoints: hcc-pack, raf-summary, hierarchy
|   |   |-- hedis.py          # 4 endpoints: measures, gaps, evidence, summary
|   |   |-- audit.py          # 4 endpoints: logs, reviews, review-assertion, pending
|   |   |-- config.py         # 8 endpoints: config CRUD, feature-flags, prompts, model-versions, llm-configs
|   |   |-- pipeline.py       # 4 endpoints: list-runs, get-run, runs-by-chart, stats
|   |   |-- dashboard.py      # 5 endpoints: stats, db-stats, processing-metrics, recent-activity, top-raf
|   |   |-- patients.py       # 1 endpoint: patient demographics from assertions
|   |   |-- encounters.py     # 1 endpoint: encounter timeline from assertions
|   |-- schemas/              # Pydantic request/response models
|
|-- services/                 # Business logic layer (7 services)
|   |-- chart_service.py      # ChartService: create, list, get_summary, delete
|   |-- assertion_service.py  # AssertionService: clinical data queries + review
|   |-- risk_service.py       # RiskService: HCC pack, RAF, hierarchy
|   |-- hedis_service.py      # HEDISService: measures, gaps, met, summary
|   |-- pipeline_service.py   # PipelineService: runs, logs, stats
|   |-- audit_service.py      # AuditService: audit logs, review actions
|   |-- config_service.py     # ConfigService: config, LLM, prompts, models
|
|-- database/                 # Persistence layer
|   |-- models.py             # 22 SQLAlchemy ORM models (assertion-centric)
|   |-- session.py            # Async session factory (SQLite/PostgreSQL)
|   |-- persist.py            # Sync persistence for batch scripts
|   |-- connection.py         # PostgreSQL connection config
|   |-- repositories/         # 8 async repository classes
|       |-- assertion_repo.py # Assertions + ConditionGroups (central)
|       |-- chart_repo.py     # Charts + ChartPages + PipelineRuns
|       |-- hcc_repo.py       # PayableHCC + SuppressedHCC
|       |-- hedis_repo.py     # HEDISResult + HEDISSummary
|       |-- raf_repo.py       # RAFSummary + HCCHierarchyLog
|       |-- pipeline_repo.py  # PipelineRun/Log, ProcessingStats, APICallLog
|       |-- audit_repo.py     # AuditLog + ReviewAction
|       |-- config_repo.py    # SystemConfig, LLMConfig, PromptTemplate, ModelVersion
|
|-- extraction/               # MiniMax single-pass LLM extraction (12 modules)
|   |-- assertion_extractor.py  # Main orchestrator class
|   |-- page_handler.py         # PDF page extraction + chunking
|   |-- llm_caller.py           # LLM API calls with system prompt
|   |-- post_processor.py       # Validate, enrich, deduplicate
|   |-- quote_validator.py      # 4-strategy quote matching
|   |-- date_engine.py          # Date extraction + inference
|   |-- code_classifier.py      # ICD/CPT/HCPCS classification
|   |-- vital_extractor.py      # Deterministic vitals parsing
|   |-- dx_harvester.py         # ICD code harvesting from text
|   |-- assertion_enricher.py   # Concept normalization
|   |-- condition_grouper.py    # Condition grouping + contradiction
|   |-- hcc_hedis_flags.py      # HCC/HEDIS candidacy flags
|
|-- core/                     # Pipeline orchestration
|   |-- orchestrator.py       # PDF -> extraction -> HCC -> HEDIS -> output
|   |-- hcc_bridge.py         # Assertions -> payable ICDs -> HCC mapping -> RAF
|   |-- hedis_bridge.py       # Assertions -> HEDIS adapter -> engine -> results
|   |-- exceptions.py         # Custom exception hierarchy
|   |-- feature_registry.py   # Feature flag registry
|
|-- hedis/                    # HEDIS quality engine
|   |-- hedis_engine/
|       |-- engine.py         # Rule-based measure evaluation
|       |-- measure_def.py    # YAML measure definition loader
|       |-- primitives.py     # Evaluation primitives (diagnosis, med, lab, etc.)
|       |-- types.py          # Data types (MemberEventStore, etc.)
|       |-- adapters/
|       |   |-- assertion_adapter.py  # Converts assertions to events
|       |-- catalog/          # 122 YAML measure definitions
|       |-- valuesets/        # Value set loaders
|
|-- decisioning/              # HCC mapping + RAF calculation
|   |-- hcc_mapper.py         # V28 ICD->HCC mapping + hierarchy suppression
|   |-- raf_calculator.py     # RAF score computation
|   |-- hedis_evaluator.py    # HEDIS evaluation wrapper
|   |-- icd_verifier.py       # ICD verification logic
|   |-- audit_scorer.py       # Audit risk scoring
|   |-- reference/            # CMS reference data
|       |-- v28_icd_hcc_mappings.csv   # 7,903 ICD->HCC mappings
|       |-- v28_coefficients.csv       # 115 RAF coefficients
|       |-- v28_hierarchy_rules.json   # 21 hierarchy groups
|
|-- ingestion/                # PDF intake and text processing
|   |-- pdf_processor.py      # PDF file handling
|   |-- quality_scorer.py     # Per-page quality scoring
|   |-- ocr_engine.py         # GPT-4o Vision OCR fallback
|   |-- text_normalizer.py    # Section segmentation
|   |-- page_extractor.py     # Raw text extraction
|
|-- ml_engine/                # ML prediction modules
|   |-- hcc_predictor.py      # BioClinicalBERT HCC predictor
|   |-- icd_retriever.py      # TF-IDF ICD-10 retrieval
|   |-- negation_detector.py  # ConText/NegEx negation detection
|   |-- span_proposer.py      # Evidence span extraction
|
|-- config/                   # Configuration
|   |-- settings.py           # Pydantic BaseSettings (central config)
|   |-- feature_flags.py      # Dynamic feature toggles
|   |-- llm_config.py         # LLM provider settings
|   |-- model_config.py       # ML model paths/thresholds
|   |-- pipeline_config.py    # Pipeline parallelism, chunk sizes
|   |-- prompts/              # 7 LLM prompt templates (.txt)
|
|-- scripts/                  # CLI tools
|   |-- run_chart.py          # Process single chart
|   |-- run_batch.py          # Batch process charts
|   |-- process_minimax_outputs.py  # Process pre-extracted MiniMax JSONs + DB persist
|   |-- validate_outputs.py   # Validate output structure
|   |-- init_db.py            # Initialize database
|   |-- seed_reference_data.py # Load V28 mappings
|   |-- export_results.py     # Export to CSV/JSON
|
|-- tests/                    # Test suite
|-- dashboard/                # Web UI (HTML + Tailwind + Alpine.js)
|-- outputs/                  # Generated output files + SQLite DB
```

---

## Database Schema (22 Tables)

### Core Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `charts` | Chart metadata | id, filename, file_path, page_count, status, quality_score_avg |
| `chart_pages` | Per-page text and quality | chart_id, page_number, text_content, quality_score, extraction_method |
| `pipeline_runs` | Pipeline execution records | chart_id, status, mode, model, duration_seconds, assertions_raw |
| `pipeline_logs` | Step-level log entries | run_id, step, message, duration_seconds |

### Clinical Tables (Assertion-Centric)
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `assertions` | **Central table** - every clinical fact | chart_id, category, concept, status, page_number, exact_quote, icd_codes, effective_date, is_hcc_candidate, is_hedis_evidence, review_status |
| `condition_groups` | Aggregated condition groupings | chart_id, group_id, group_key, canonical_concept, assertion_count |

### Risk Adjustment Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `payable_hccs` | Final payable HCC list | chart_id, hcc_code, hcc_description, raf_weight, supported_icds (JSON) |
| `suppressed_hccs` | Hierarchy-suppressed HCCs | chart_id, hcc_code, suppressed_by, hierarchy_group |
| `raf_summaries` | RAF score breakdown | chart_id, total_raf_score, hcc_raf, payable_hcc_count |
| `hcc_hierarchy_log` | Hierarchy suppression audit | chart_id, suppressed_hcc, suppressed_by, group_name |
| `icd_hcc_mappings` | V28 reference table | icd10_code, hcc_category, raf_weight |

### HEDIS Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `hedis_results` | Per-measure evaluation result | chart_id, measure_id, status (met/gap), evidence_used (JSON) |
| `hedis_summaries` | Aggregate per-chart summary | chart_id, total_measures, met_count, gap_count |

### Audit & Review Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `audit_logs` | System action log | action, entity_type, entity_id, user_name |
| `review_actions` | Coder accept/reject actions | chart_id, entity_type, action, reviewer |

### Configuration Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `system_config` | Key-value config store | config_key, config_value (JSON) |
| `llm_configs` | LLM provider settings | provider, model_name, temperature, is_active |
| `prompt_templates` | LLM prompt versions | pipeline_name, version, system_prompt, is_active |
| `model_versions` | ML model tracking | model_name, version, f1_score, is_active |

### Analytics Tables
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `processing_stats` | Per-chart processing metrics | chart_id, total_processing_seconds, pages_processed, model_used |
| `api_call_logs` | LLM API call tracking | run_id, provider, model_name, total_tokens, latency_ms |

---

## Repository Layer (8 Classes)

Each repository wraps a domain-model group with async CRUD operations:

| Repository | Models | Key Methods |
|------------|--------|-------------|
| `AssertionRepository` | Assertion, ConditionGroup | get_by_chart, get_diagnoses, get_medications, get_vitals, get_labs, get_hedis_evidence, get_ra_candidates, get_pending_review, update_review, count_by_category |
| `ChartRepository` | Chart, ChartPage, PipelineRun | create, get_by_id (eager load pages+runs), list_all, update_status, delete, create_pages_bulk, get_pipeline_runs_by_chart |
| `HCCRepository` | PayableHCC, SuppressedHCC | create_payable, get_payable_by_chart, count_payable, create_suppressed, get_suppressed_by_chart |
| `HEDISRepository` | HEDISResult, HEDISSummary | get_results_by_chart (with status filter), get_gaps, get_met, get_result_by_measure, count_by_status |
| `RAFRepository` | RAFSummary, HCCHierarchyLog | create_summary, get_summary_by_chart, get_hierarchy_by_chart |
| `PipelineRepository` | PipelineRun, PipelineLog, ProcessingStats, APICallLog | list_runs, complete_run, get_stats_by_chart, get_avg_processing_time, get_token_usage |
| `AuditRepository` | AuditLog, ReviewAction | create_log, get_logs (with entity filter), create_review, get_reviews_by_chart |
| `ConfigRepository` | SystemConfig, LLMConfig, PromptTemplate, ModelVersion | get/set_config, get_active_llm, get/create_prompt, get_all_model_versions |

---

## Service Layer (7 Classes)

Services encapsulate business logic, compose multiple repositories, and serialize ORM objects for API responses:

| Service | Repos Used | Key Methods |
|---------|-----------|-------------|
| `ChartService` | Chart, Assertion, HCC, HEDIS, RAF | create_chart, list_charts, get_chart_summary (joins assertion/RAF/HEDIS counts), delete_chart |
| `AssertionService` | Assertion | get_all (with category/status filters), get_diagnoses, get_medications, get_vitals, get_labs, get_encounters (derived from dates), get_ra_candidates, get_pending_reviews, update_review |
| `RiskService` | HCC, RAF | get_hcc_pack (payable + suppressed + RAF + hierarchy), get_raf_summary, get_hierarchy |
| `HEDISService` | HEDIS | get_measures (with status filter + summary), get_gaps, get_met, get_measure_detail, get_summary |
| `PipelineService` | Pipeline | list_runs, get_run (with logs), get_runs_by_chart, get_stats, get_avg_processing_time |
| `AuditService` | Audit | log_action, get_logs, create_review, get_reviews_by_chart |
| `ConfigService` | Config | get/set_config, get_active_llm, get_all_llm_configs, get/create_prompt, get_model_versions |

---

## API Endpoints (43 Total)

### Charts (/api/charts) - 5 endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /upload | Upload PDF chart |
| GET | / | List charts with pagination |
| GET | /{chart_id} | Chart summary with assertion/RAF/HEDIS counts |
| GET | /{chart_id}/pages | Page-level data |
| DELETE | /{chart_id} | Delete chart and all related data |

### Clinical (/api/clinical) - 8 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /{chart_id}/assertions | All assertions with category/status filters |
| GET | /{chart_id}/diagnoses | Diagnoses with ICD codes |
| GET | /{chart_id}/medications | Medications |
| GET | /{chart_id}/vitals | Vital signs (BP, BMI, etc.) |
| GET | /{chart_id}/labs | Lab results |
| GET | /{chart_id}/encounters | Encounter timeline (derived from dates) |
| GET | /{chart_id}/categories | Assertion counts by category |
| GET | /{chart_id}/ra-candidates | Payable RA candidate assertions |

### Risk Adjustment (/api/risk) - 3 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /{chart_id}/hcc-pack | Complete Payable HCC Pack |
| GET | /{chart_id}/raf-summary | RAF score breakdown |
| GET | /{chart_id}/hierarchy | HCC hierarchy suppression details |

### HEDIS (/api/hedis) - 4 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /{chart_id}/measures | Measures with status filter |
| GET | /{chart_id}/gaps | Care gaps |
| GET | /{chart_id}/evidence | Met measures with evidence |
| GET | /{chart_id}/summary | Aggregate HEDIS summary |

### Audit (/api/audit) - 4 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /logs | Audit logs with entity filter |
| GET | /{chart_id}/reviews | Review actions for chart |
| PUT | /review/assertion/{id} | Accept/reject assertion |
| GET | /pending | Pending review items |

### Configuration (/api/config) - 8 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | / | All configuration (env + DB) |
| PUT | / | Update config value |
| GET | /feature-flags | Feature flags |
| PUT | /feature-flags | Toggle feature flag |
| GET | /prompts | Prompt templates (DB + files) |
| PUT | /prompts | Create prompt template version |
| GET | /model-versions | ML model versions |
| GET | /llm-configs | LLM provider configs |

### Pipeline (/api/pipeline) - 4 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /runs | List pipeline runs |
| GET | /runs/{run_id} | Run details with logs |
| GET | /runs/chart/{chart_id} | Runs by chart |
| GET | /stats/{chart_id} | Processing stats |

### Dashboard (/api/dashboard) - 5 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /stats | System-wide statistics |
| GET | /db-stats | Database table row counts |
| GET | /processing-metrics | Avg processing time + recent runs |
| GET | /recent-activity | Recent chart activity |
| GET | /top-raf | Top charts by RAF score |

### Legacy Compatibility - 2 endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/patients/{chart_id} | Patient demographics from assertions |
| GET | /api/encounters/{chart_id} | Encounters from assertions |

---

## Data Flow

### Pipeline Flow (PDF -> DB)

```
1. PDF Input
   |
2. page_handler.py: Extract pages (PyMuPDF), chunk text
   |
3. llm_caller.py: Send chunks to MiniMax LLM with system prompt
   |
4. post_processor.py: Parse JSON, validate, enrich assertions
   |  |-- quote_validator.py: Match quotes to source text
   |  |-- date_engine.py: Resolve dates, compute effective_date
   |  |-- code_classifier.py: Extract ICD/CPT/HCPCS codes
   |  |-- vital_extractor.py: Parse vitals from text
   |  |-- dx_harvester.py: Harvest ICD codes
   |  |-- assertion_enricher.py: Clean concepts, fix statuses
   |  |-- condition_grouper.py: Group related conditions
   |  |-- hcc_hedis_flags.py: Set HCC/HEDIS candidacy flags
   |
5. hcc_bridge.py: Filter payable RA candidates -> map ICDs to HCCs
   |  |-- hcc_mapper.py: V28 ICD->HCC + hierarchy suppression
   |  |-- raf_calculator.py: Compute RAF from coefficients
   |
6. hedis_bridge.py: Convert assertions to events -> evaluate measures
   |  |-- assertion_adapter.py: Assertion -> MemberEventStore
   |  |-- engine.py: Evaluate 122 YAML measures
   |
7. Output: 7 sub-JSON files per chart
   |
8. persist.py: Bulk-insert to database
   |-- Chart + PipelineRun
   |-- Assertions (bulk)
   |-- PayableHCC + SuppressedHCC + RAFSummary
   |-- HEDISResult + HEDISSummary
   |-- ProcessingStats
```

### API Request Flow

```
HTTP Request -> FastAPI Router -> Depends(get_db) -> Service -> Repository -> SQLAlchemy -> DB
```

Every API route:
1. Receives request with `db: AsyncSession = Depends(get_db)`
2. Instantiates the appropriate service: `svc = ChartService(db)`
3. Service calls repository methods
4. Repository executes SQLAlchemy queries
5. Service serializes ORM objects to dicts
6. Router returns JSON response

---

## Database Configuration

### SQLite (Default / Development)
- File: `outputs/medinsight360.db`
- Async: `sqlite+aiosqlite://` (via `database/session.py`)
- Sync: `sqlite:///` (via `database/persist.py`)
- Zero configuration required

### PostgreSQL (Production)
Set these environment variables:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=medinsight360
POSTGRES_USER=medinsight
POSTGRES_PASSWORD=<password>
```
- Async: `postgresql+asyncpg://` (auto-detected by session.py)
- Sync: `postgresql://` (via `database/connection.py`)

---

## Key Design Decisions

1. **Assertion-centric schema**: Single `assertions` table replaces separate Patient, Diagnosis, Encounter, Vital, Lab, Medication tables. Every clinical fact is one assertion row with a `category` column discriminator.

2. **Dual session factories**: Sync sessions for batch scripts (`persist.py`), async sessions for API (`session.py`). Both create tables from the same `models.py`.

3. **MiniMax single-pass extraction**: One LLM call per chunk extracts ALL clinical assertions simultaneously. Replaces the old 5-pipeline parallel extraction approach.

4. **Repository pattern**: Thin async CRUD wrappers isolate SQLAlchemy queries from business logic. Each repo serves 1-4 related ORM models.

5. **Service layer**: Business logic sits between repos and API. Services compose multiple repos, handle serialization, and enforce business rules.

6. **Evidence chain**: Every assertion carries page_number, exact_quote, char_start/char_end. This provenance flows through to HCC evidence and HEDIS evidence.

7. **Cascading deletes**: Chart deletion cascades to all child tables via `ondelete="CASCADE"` foreign keys.

---

## Reference Data

| File | Contents | Size |
|------|----------|------|
| `decisioning/reference/v28_icd_hcc_mappings.csv` | 7,903 ICD-10 to HCC mappings | V28 model |
| `decisioning/reference/v28_coefficients.csv` | 115 RAF coefficient weights per HCC | V28 model |
| `decisioning/reference/v28_hierarchy_rules.json` | 21 hierarchy suppression groups | V28 model |
| `hedis/hedis_engine/catalog/*.yaml` | 122 HEDIS measure definitions | MY2025 |
| `ml_engine/models/icd10_catalog.json` | 7,903 ICD-10-CM code descriptions | Full catalog |

---

## Testing

Test suite in `tests/`:
- `test_ingestion.py` — PDF processing, quality scoring
- `test_extraction.py` — MiniMax extraction pipeline
- `test_ml_engine.py` — HCC predictor, ICD retriever, negation detector
- `test_decisioning.py` — HCC mapper, RAF calculator
- `test_api.py` — FastAPI endpoint tests
- `test_e2e_integration.py` — End-to-end pipeline test

HEDIS engine tests in `hedis/hedis_engine/tests/`:
- `test_adapter.py`, `test_engine.py`, `test_primitives.py`, `test_types.py`
- `test_expanded_measures.py`, `test_new_measures.py`

---

## Scripts

| Script | Purpose | Key Options |
|--------|---------|-------------|
| `run_chart.py` | Process single PDF | --chart-path, --mode (full/risk_only/hedis_only) |
| `run_batch.py` | Batch process PDFs | --input-dir, --output-dir |
| `process_minimax_outputs.py` | Process pre-extracted JSONs + persist to DB | --persist-db, --db-url |
| `validate_outputs.py` | Validate output JSON structure | --output-dir |
| `init_db.py` | Initialize database tables | --db-url |
| `seed_reference_data.py` | Load V28 mappings into DB | -- |
| `export_results.py` | Export results to CSV/JSON | --chart-id, --format |
