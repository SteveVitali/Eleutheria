-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:ingest_run_report_upstream_recon to pg

BEGIN;

ALTER TABLE ingest_run_report
    DROP CONSTRAINT IF EXISTS ingest_run_report_upstream_recon_object;

ALTER TABLE ingest_run_report
    DROP COLUMN IF EXISTS upstream_reconciliation;

COMMIT;
