-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:accountability_link_materialize on pg

BEGIN;

-- The column exists.
SELECT input_digest FROM inference.derived_fact WHERE false;

-- The partial unique index exists (in the `inference` schema).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'inference' AND indexname = 'derived_fact_input_digest_key'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
