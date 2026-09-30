-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:ingest_run_capture on pg

BEGIN;

SELECT run_id, target_key, state, capture_digest, source_uri, media_type, byte_size,
       retrieved_at, records, recorded_at
  FROM ingest_run_capture WHERE false;

-- The immutability trigger exists (UPDATE and DELETE both refuse).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid
     WHERE c.relname = 'ingest_run_capture' AND t.tgname = 'ingest_run_capture_immutable'
       AND NOT t.tgisinternal
  ) THEN 1 ELSE 0 END);

-- The ingest role may INSERT, never UPDATE/DELETE.
SELECT 1 / (CASE WHEN has_table_privilege('sig_ingest', 'ingest_run_capture', 'INSERT')
                  AND NOT has_table_privilege('sig_ingest', 'ingest_run_capture', 'UPDATE')
                  AND NOT has_table_privilege('sig_ingest', 'ingest_run_capture', 'DELETE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
