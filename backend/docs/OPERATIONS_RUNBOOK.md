# Operations Runbook

## Environment
- Backend root: `medinsight360_codex`
- Frontend root: `../medinsight360-frontend_codex/ui-5-react-mantine`
- Database: PostgreSQL `medinsight360` on `localhost:5432`

## 1) Bootstrap Database
Use once on a fresh database:

```powershell
venv\Scripts\python.exe scripts\db\bootstrap_medinsight360.py
```

What it does:
- creates DB if missing,
- creates ORM tables,
- seeds ICD->HCC mappings,
- syncs HEDIS measure definitions and valuesets from files into DB,
- sets top-25 HEDIS profile in `system_config`.

## 2) Reset Chart-Derived Data (keep config/reference)
```powershell
venv\Scripts\python.exe scripts\db\reset_chart_data.py
```

Equivalent SQL:
- `scripts/db/reset_chart_data.sql`

## 3) Fresh Batch Processing (10 PDFs)
```powershell
$env:HEDIS_ASSUME_ENROLLED_IF_MISSING='1'
venv\Scripts\python.exe scripts\process_charts.py --input-dir input --max-files 10 --db-url postgres
```

## 4) API Start
```powershell
venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## 5) Frontend Start
```powershell
cd ..\medinsight360-frontend_codex\ui-5-react-mantine
npm install
npm run dev
```

## 6) Validation
Backend:
```powershell
venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_process_charts_hardening.py tests/test_hedis_fallback.py tests/test_assertion_service_labs.py hedis/hedis_engine/tests/test_adapter_enrollment.py -q
```

Frontend:
```powershell
npm run build
```

## 7) Docker
Compose stack (API on `8006`):
```powershell
docker compose up --build
```

Build images only:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\docker\build_images.ps1
```

## 8) Config Snapshot Query
Use `scripts/db/show_config_snapshot.sql` to verify:
- active HEDIS profile,
- measure/value set availability.

## 9) Known Runtime Constraints
- If external LLM/OCR network calls fail, deterministic fallback will populate core evidence but may have less rich encounter detail.
- `6_RET236976864.pdf` remains extraction-failed in current environment (no text extracted).
