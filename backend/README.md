# MedInsight 360 (Codex Workspace)

MedInsight 360 is a chart-processing platform for:
- clinical fact extraction from PDF charts,
- ICD/HCC risk adjustment review,
- HEDIS measure evaluation with evidence traceability,
- API + frontend chart reviewer workflows.

## Current Runtime Baseline (March 7, 2026)
- Database backend: PostgreSQL (`medinsight360`)
- Latest validated fresh run: `run_outputs/batch10_worldclass_hedis_repaired_v4_20260307_133847`
- Batch status on 10 input PDFs: `9/10` successful, `1` failed (`6_RET236976864.pdf` no extractable text in current OCR environment)
- HEDIS enrollment fallback enabled when explicit enrollment is missing: `HEDIS_ASSUME_ENROLLED_IF_MISSING=1`

## Project Structure
- `api/` FastAPI routes and app wiring.
- `services/` orchestration and response shaping.
- `extraction/` PDF/text extraction and deterministic fallback extractors.
- `hedis/hedis_engine/` measure definitions, rules engine, valuesets.
- `decisioning/` ICD->HCC mapping and hierarchy resources.
- `database/` ORM models, repositories, persistence helpers.
- `scripts/` processing, DB/bootstrap, utility scripts.
- `docs/` architecture/runbooks/handoff memory.
- `input/` canonical test PDFs.
- `uploads/` runtime upload folder (kept empty in clean baseline).

## Quick Start (Local)
1. Create/activate virtual env and install deps.
2. Configure `.env` from `.env.example`.
3. Bootstrap DB:
   - `venv\Scripts\python.exe scripts\db\bootstrap_medinsight360.py`
4. Process batch:
   - `venv\Scripts\python.exe scripts\process_charts.py --input-dir input --max-files 10 --db-url postgres`
5. Run API:
   - `venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000`

## Docker
- Backend Dockerfile: `Dockerfile`
- Compose stack (Postgres + API on host port `8006`): `docker-compose.yml`
- Build helper script: `scripts/docker/build_images.ps1`
- Frontend Dockerfile (sibling frontend repo):
  - `../medinsight360-frontend_codex/ui-5-react-mantine/Dockerfile`

## DB Operations
- Bootstrap schema + references + HEDIS registry/profile:
  - `scripts/db/bootstrap_medinsight360.py`
- Reset chart-derived data only:
  - `scripts/db/reset_chart_data.py`
  - SQL equivalent: `scripts/db/reset_chart_data.sql`
- Config snapshot SQL:
  - `scripts/db/show_config_snapshot.sql`

## Tests / Validation
- Backend targeted suite:
  - `venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_process_charts_hardening.py tests/test_hedis_fallback.py tests/test_assertion_service_labs.py hedis/hedis_engine/tests/test_adapter_enrollment.py -q`
- Frontend build:
  - `npm run build` (in frontend repo)

## Cleanup / Archive Policy
- Old generated artifacts were moved to:
  - `backups/cleanup_20260307_140001/`
- Active baseline artifacts were kept minimal for handoff continuity.

See:
- `docs/PROJECT_MEMORY.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/CLEANUP_AND_HANDOFF_2026-03-07.md`
- `docs/GITHUB_RELEASE_CHECKLIST.md`
