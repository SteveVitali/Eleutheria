-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:coverage_materialize on pg

BEGIN;

-- The idempotency + metric columns exist.
SELECT input_digest, metric_method, metric_label, numerator, denominator,
       not_evaluable, named_denominator, metric_value
  FROM coverage_record WHERE false;

-- The partial unique index exists.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'public' AND indexname = 'coverage_record_input_digest_key'
  ) THEN 1 ELSE 0 END);

-- The no-total CHECK exists (the SIG-METRIC-009/010 invariant, pinned at the DB).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'coverage_metric_named_denominator'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
