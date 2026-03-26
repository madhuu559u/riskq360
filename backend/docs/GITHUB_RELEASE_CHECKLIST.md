# GitHub Release Checklist

Use this checklist when publishing this cleaned workspace.

## 1) Confirm Runtime Baseline
1. Verify DB/env target in `.env` points to intended environment.
2. Confirm active run artifact exists:
   - `run_outputs/batch10_worldclass_hedis_repaired_v4_20260307_133847`
3. Confirm docs are present:
   - `docs/PROJECT_MEMORY.md`
   - `docs/OPERATIONS_RUNBOOK.md`
   - `docs/CLEANUP_AND_HANDOFF_2026-03-07.md`

## 2) Validate Local Build/Test
1. Backend targeted tests:
```powershell
venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_process_charts_hardening.py tests/test_hedis_fallback.py tests/test_assertion_service_labs.py hedis/hedis_engine/tests/test_adapter_enrollment.py -q
```
2. Frontend build (in frontend repo):
```powershell
npm run build
```
3. Docker compose config sanity:
```powershell
docker compose config
```

## 3) Guardrails Before Push
1. Ensure no secrets are committed (`.env` must remain ignored).
2. Ensure generated artifacts are not staged (`run_outputs/`, `backups/`, `uploads/` ignored).
3. Confirm lock/temp folders are ignored:
   - `.pytest_cache/`
   - `run_outputs/pytest-of-madhu`
   - `run_outputs/pytest_tmp`

## 4) Initialize Git (if repo metadata is missing)
```powershell
git init
git add .
git commit -m "chore: cleanup workspace, add DB bootstrap/reset, docker, and handoff docs"
```

## 5) Connect Remote And Push
```powershell
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## 6) Post-Push Smoke
1. Fresh clone into a new folder.
2. Run DB bootstrap and API start from `docs/OPERATIONS_RUNBOOK.md`.
3. Run one upload/process flow from UI and verify:
   - chart appears,
   - clinical + HEDIS tabs render,
   - evidence links include page reference.
