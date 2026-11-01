-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:ingest_run_report_execution_key to pg
-- P36.46 / K10 §9 + §16.1 (SIG-TRANSP-036): the execution-keyed history
-- surface fields.
--
--   * ingest_run_report gains ``mode`` / ``kind`` — the run-row's own
--     recorded execution metadata (K10 §9's mode column: ``mode`` is the
--     run-row's live/replay, ``kind`` its job kind — scheduled-ingest,
--     p265-tenant-sweep, replay-ingest, …). Both are NULL-tolerant: rows
--     written before this change, and records that never carried the
--     values, stay NULL (not_recorded) — no backfill invents one.
--   * ``v_transparency_run`` gains, appended at the end of its explicit
--     column list (CREATE OR REPLACE requires the original prefix):
--       - ``execution_key`` — the C-14 merge key the public
--         ``sig.execution-record/1`` carries: ``completion:<completion_id>``
--         when a 1:1 completion links the execution, else the WORM
--         ``run-row:<object name>`` (object name only — the gs:// bucket
--         locator itself never leaves the view), else ``repo:<path>`` for
--         the repo-pinned live-run records, else ``report:<report_id>``
--         for a live row whose execution left no completion and no
--         backfilled record (the report row's own key — honest, never a
--         fabricated link).
--       - ``mode`` / ``kind`` — the report row's recorded values.
--
-- The change is additive only: nullable columns, an appended-column view,
-- no UPDATE/DELETE on any living row.

BEGIN;

ALTER TABLE ingest_run_report
  ADD COLUMN mode text,
  ADD COLUMN kind text;

ALTER TABLE ingest_run_report
  ADD CONSTRAINT ingest_run_report_mode_vocab
  CHECK (mode IS NULL OR mode IN ('live', 'replay', 'shadow'));

CREATE OR REPLACE VIEW v_transparency_run AS
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
    rr.recorded_at,
    -- P36.46: appended columns — CREATE OR REPLACE requires the original
    -- column prefix unchanged; the allow-list order in
    -- policy.transparency.TRANSPARENCY_RUN_VIEW_COLUMNS mirrors this.
    CASE
        WHEN c.completion_id IS NOT NULL THEN 'completion:' || c.completion_id::text
        WHEN rr.backfilled_from LIKE 'gs://%'
            THEN 'run-row:' || substring(rr.backfilled_from from '^gs://[^/]+/(.+)$')
        WHEN rr.backfilled_from LIKE 'repo:%'
            THEN 'repo:' || substring(rr.backfilled_from from 6)
        ELSE 'report:' || rr.report_id::text
    END AS execution_key,
    rr.mode,
    rr.kind
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

COMMIT;
