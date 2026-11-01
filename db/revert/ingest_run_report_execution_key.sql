-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert eleutheria-claims:ingest_run_report_execution_key from pg
--
-- Restore the P35.33 v_transparency_run shape (the added columns make
-- CREATE OR REPLACE refuse, so the view is dropped and recreated at its
-- prior definition), then drop the report's mode/kind columns.

BEGIN;

DROP VIEW IF EXISTS v_transparency_run;

CREATE VIEW v_transparency_run AS
WITH run_executions AS (
    SELECT run_id, count(*) AS n
      FROM ingest_run_report
     WHERE run_id IS NOT NULL
     GROUP BY run_id
),
run_completions AS (
    SELECT run_id, count(*) AS n
      FROM ingest_run_completion
     GROUP BY run_id
)
SELECT
    rr.report_id,
    rr.run_id,
    rr.source_id,
    rr.link_basis,
    rr.clock_basis,
    COALESCE(GREATEST(re.n, rc.n) > 1, false) AS shared_run,
    rr.started_at,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.finished_at END AS finished_at,
    rr.duration_seconds,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.status END AS completion_status,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.claims_considered END AS claims_considered,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.claims_inserted END AS claims_inserted,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.claims_duplicate END AS claims_duplicate,
    rr.fetches,
    rr.records_emitted,
    rr.robots_outcomes,
    rr.refusal_classes,
    rr.rate_limit_events,
    rr.disappearances,
    rr.document_outcomes,
    rr.quota_reached,
    rr.budget_reached,
    rr.error_class,
    rr.per_fetch,
    CASE WHEN COALESCE(re.n, 0) = 1 AND COALESCE(rc.n, 0) <= 1
         THEN ir.connector_name END AS connector_name,
    CASE WHEN COALESCE(re.n, 0) = 1 AND COALESCE(rc.n, 0) <= 1
         THEN ir.connector_version END AS connector_version,
    CASE WHEN COALESCE(re.n, 0) = 1 AND COALESCE(rc.n, 0) <= 1
         THEN ir.code_commit END AS code_commit,
    rr.recorded_at
FROM ingest_run_report rr
LEFT JOIN run_executions re ON re.run_id = rr.run_id
LEFT JOIN run_completions rc ON rc.run_id = rr.run_id
LEFT JOIN ingest_run_completion c
       ON c.run_id = rr.run_id
      AND COALESCE(re.n, 1) = 1
      AND COALESCE(rc.n, 0) = 1
LEFT JOIN ingest_run ir
       ON ir.run_id = rr.run_id
      AND COALESCE(re.n, 0) = 1
      AND COALESCE(rc.n, 0) <= 1;

GRANT SELECT ON v_transparency_run TO sig_export;

ALTER TABLE ingest_run_report
  DROP CONSTRAINT IF EXISTS ingest_run_report_mode_vocab;

ALTER TABLE ingest_run_report
  DROP COLUMN IF EXISTS mode,
  DROP COLUMN IF EXISTS kind;

COMMIT;
