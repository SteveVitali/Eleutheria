-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:accountability_link_materialize from pg

BEGIN;

DROP INDEX IF EXISTS inference.derived_fact_input_digest_key;

ALTER TABLE inference.derived_fact
  DROP COLUMN IF EXISTS input_digest;

COMMIT;
