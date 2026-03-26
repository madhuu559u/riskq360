# MedInsight 360 - Current State (Authoritative)

Last updated: 2026-03-07

This file replaces older status notes that overclaimed or referenced stale runs.

## Read Order For Any New Session
1. `docs/PROJECT_MEMORY.md`
2. `docs/OPERATIONS_RUNBOOK.md`
3. `docs/CLEANUP_AND_HANDOFF_2026-03-07.md`

## Current Baseline
- Backend root: `medinsight360_codex`
- Frontend root: `../medinsight360-frontend_codex/ui-5-react-mantine`
- Active database target: PostgreSQL `medinsight360` (`localhost:5432`)
- Latest validated batch run kept in workspace:
  - `run_outputs/batch10_worldclass_hedis_repaired_v4_20260307_133847`

## What Is Intentionally Archived
- Legacy generated outputs/logs and stale reports were moved to:
  - `backups/cleanup_20260307_140001/`
- `uploads/` is intentionally empty as a clean runtime baseline.

## Known Locked Paths
These directories may be locked by local processes on Windows:
- `run_outputs/pytest-of-madhu`
- `run_outputs/pytest_tmp`

They are ignored by `.gitignore` and do not affect runtime behavior.

## Key Bootstrap/Reset Commands
```powershell
venv\Scripts\python.exe scripts\db\bootstrap_medinsight360.py
venv\Scripts\python.exe scripts\db\reset_chart_data.py
```

## Do Not Use As Truth
- old root HTML review reports in backups
- old "fully built" claims from pre-cleanup notes
- stale summaries not tied to current run artifacts
