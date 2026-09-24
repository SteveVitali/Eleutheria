-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:ingest_run_completion on pg

BEGIN;

SELECT completion_id, run_id, source_id, status, finished_at, claims_considered,
       claims_inserted, claims_duplicate, run_record_uri, backfilled_from, detail, recorded_at
  FROM ingest_run_completion WHERE false;

-- The two uniqueness keys (one live completion per run; one backfilled row per WORM object).
SELECT 1 / (CASE WHEN (
    SELECT count(*) FROM pg_indexes
     WHERE schemaname = 'public'
       AND indexname IN ('ingest_run_completion_live_key', 'ingest_run_completion_backfill_key')
  ) = 2 THEN 1 ELSE 0 END);

-- The immutability trigger exists (UPDATE and DELETE both refuse).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid
     WHERE c.relname = 'ingest_run_completion' AND t.tgname = 'ingest_run_completion_immutable'
       AND NOT t.tgisinternal
  ) THEN 1 ELSE 0 END);

-- The backfill role may INSERT, never UPDATE/DELETE.
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'ingest_run_completion', 'INSERT')
                  AND NOT has_table_privilege('sig_materialize', 'ingest_run_completion', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'ingest_run_completion', 'DELETE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
