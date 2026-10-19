-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:ingest_run_report_upstream_recon on pg

BEGIN;

-- The column exists and is typed jsonb.
SELECT upstream_reconciliation FROM ingest_run_report WHERE false;
SELECT 1 / (CASE WHEN (
    SELECT data_type FROM information_schema.columns
     WHERE table_name = 'ingest_run_report'
       AND column_name = 'upstream_reconciliation'
  ) = 'jsonb' THEN 1 ELSE 0 END);

-- The object-shape constraint exists.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'ingest_run_report_upstream_recon_object'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
