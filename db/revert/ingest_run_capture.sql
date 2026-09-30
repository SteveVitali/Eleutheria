-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:ingest_run_capture from pg

BEGIN;

DROP TRIGGER IF EXISTS ingest_run_capture_immutable ON ingest_run_capture;
DROP FUNCTION IF EXISTS ingest_run_capture_immutable();
DROP TABLE IF EXISTS ingest_run_capture;

COMMIT;
