# Project Memory (Authoritative Handoff)

Last updated: 2026-03-07

## 1) What This Project Is
MedInsight 360 processes chart PDFs into auditable clinical outputs:
- diagnoses / ICD evidence,
- HCC candidate lifecycle,
- HEDIS measure results with evidence,
- clinical entities (vitals, labs, meds, encounters),
- API + reviewer UI delivery.

## 2) Source of Truth
- Code behavior: `scripts/process_charts.py`, `services/`, `database/`, `hedis/hedis_engine/`.
- Latest validated run artifacts:
  - `run_outputs/batch10_worldclass_hedis_repaired_v4_20260307_133847`
- Database (active): PostgreSQL `medinsight360`.

## 3) Current Processing Reality
- Run scope: 10 PDFs from `input/`.
- Success: `9/10`.
- Failure: `6_RET236976864.pdf` (`No text extracted` in current OCR/vision runtime constraints).
- HEDIS focus: top 25 three-letter profile active by default via DB/system config.
- Enrollment behavior: when missing explicit enrollment evidence, assume enrolled for measurement year (`HEDIS_ASSUME_ENROLLED_IF_MISSING=1`).

## 4) Key Recent Hardening (Completed)
- BP quality hardening:
  - implausible BP filtering,
  - DOB/date bleed prevention,
  - sanitized HEDIS BP ingestion.
- Evidence traceability improvements:
  - page + quote propagation for vitals/labs/meds/encounters.
- Encounter fallback hardening:
  - deterministic encounter extraction from chart text when LLM encounter pipeline is empty/error.
- Lab detail quality:
  - structured output (`test_name`, `value`, `unit`),
  - A1c/eGFR parsing guardrails to avoid wrong number capture.
- Frontend clinical evidence click-through:
  - meds/labs/encounters evidence wired with page hints and quote targeting.

## 5) Core Execution Flow
1. PDF extraction (`extraction/smart_pdf.py`) with OCR/vision fallback when needed.
2. 5 parallel extraction pipelines:
   - demographics, sentences, risk diagnoses, HEDIS evidence, encounters.
3. Deterministic fallback patching (`extraction/hedis_fallback.py`) when sparse/error.
4. HCC mapping + trace generation.
5. HEDIS engine evaluation with active measure profile.
6. Persist assertions + normalized entities + measure results + trace.
7. Serve via API + frontend.

## 6) Critical Config Tables
- `system_config`:
  - `hedis.measure_profile`
  - `hedis.assume_enrolled_if_missing`
- `hedis_measure_definitions`
- `hedis_valuesets`

## 7) Important Scripts
- Batch processing: `scripts/process_charts.py`
- DB bootstrap: `scripts/db/bootstrap_medinsight360.py`
- Chart-data reset: `scripts/db/reset_chart_data.py`
- Docker image build helper: `scripts/docker/build_images.ps1`

## 8) Validation Commands
- Backend tests:
  - `venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_process_charts_hardening.py tests/test_hedis_fallback.py tests/test_assertion_service_labs.py hedis/hedis_engine/tests/test_adapter_enrollment.py -q`
- Frontend build:
  - run in frontend repo: `npm run build`

## 9) Known Gaps / Next Work
- OCR hardening for `6_RET236976864.pdf` to achieve 10/10 batch completion.
- Encounter fallback still conservative and may return generic `type=documented` for sparse pages.
- Some charts still produce sparse structured encounter metadata when source text is weakly formatted.

## 10) Archive + Cleanup
- Legacy generated artifacts moved to:
  - `backups/cleanup_20260307_140001/`
- Active workspace intentionally trimmed to reduce noise for future sessions.
