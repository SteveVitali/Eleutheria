-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:resolution_materialize from pg

BEGIN;

DROP INDEX IF EXISTS resolution_input_digest_key;

ALTER TABLE resolution
  DROP COLUMN IF EXISTS input_digest;

COMMIT;
