# Cleanup And Handoff (2026-03-07)

## Objective
Prepare a clean, reproducible, handoff-ready workspace:
- keep code/config/runtime essentials,
- archive generated noise and stale reports,
- document exact operating baseline for future Codex/Claude sessions.

## Cleanup Performed
- Created archive root:
  - `backups/cleanup_20260307_140001/`
- Moved legacy generated artifacts from project root into backup:
  - `outputs/`, `logs/`, `batch10/`, `improve/`, `test_batch_10/`
- Archived legacy run-output history:
  - most prior `run_outputs/*` into `backups/.../run_outputs_archive/`
- Archived legacy root reports and old handoff files:
  - moved to `backups/.../legacy_root_reports/`
- Archived previous uploaded files:
  - moved to `backups/.../uploads_archive/`
- Kept only current baseline run in active workspace:
  - `run_outputs/batch10_worldclass_hedis_repaired_v4_20260307_133847`
- Left `uploads/` empty as blank-slate runtime input folder.

## Important Note On Locked Directories
Two local test temp folders remain under `run_outputs/` because of access locks:
- `run_outputs/pytest-of-madhu`
- `run_outputs/pytest_tmp`

They are ignored by `.gitignore`, with archived copies in backup.

## Repo Hygiene Updates
- `.gitignore` hardened for generated artifacts (`run_outputs`, `backups`, `uploads`, etc.).
- Added backend Docker assets:
  - `Dockerfile`
  - `.dockerignore`
  - `docker-compose.yml` (API exposed at host port `8006`)
- Added helper script:
  - `scripts/docker/build_images.ps1`
- Added frontend container assets in sibling frontend repo:
  - `../medinsight360-frontend_codex/ui-5-react-mantine/Dockerfile`
  - `../medinsight360-frontend_codex/ui-5-react-mantine/.dockerignore`

## Database Preparedness
Added scripts for clean bootstrap/reset and config visibility:
- `scripts/db/bootstrap_medinsight360.py`
- `scripts/db/reset_chart_data.py`
- `scripts/db/reset_chart_data.sql`
- `scripts/db/show_config_snapshot.sql`

Bootstrap script provisions:
- schema/tables,
- ICD->HCC map load,
- HEDIS measure definitions + valuesets sync,
- active top-25 HEDIS profile in `system_config`.

## Verification Completed
- Python syntax check:
  - `py_compile` passed for new DB scripts.
- Script argument checks:
  - `bootstrap_medinsight360.py --help` passed.
  - `reset_chart_data.py --help` passed.
- Docker compose validation:
  - `docker compose config` succeeds.

## Canonical Handoff Documents
- `docs/PROJECT_MEMORY.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/GITHUB_RELEASE_CHECKLIST.md`
- `CLAUDE_CURRENT_STATE.md`
