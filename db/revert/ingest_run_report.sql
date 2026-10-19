-- Revert eleutheria-claims:ingest_run_report from pg

BEGIN;

DROP TRIGGER IF EXISTS ingest_run_report_immutable ON ingest_run_report;
DROP FUNCTION IF EXISTS ingest_run_report_immutable;
DROP TABLE IF EXISTS ingest_run_report;

COMMIT;
