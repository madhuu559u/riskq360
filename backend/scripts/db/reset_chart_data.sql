-- Reset chart-derived data while preserving reference/config tables.
-- Intended for medinsight360 PostgreSQL database.

BEGIN;

UPDATE patients
SET run_id = NULL, chart_id = NULL
WHERE chart_id IS NOT NULL;

DELETE FROM charts;

COMMIT;
