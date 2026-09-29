-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:coverage_materialize from pg

BEGIN;

DROP INDEX IF EXISTS coverage_record_input_digest_key;

ALTER TABLE coverage_record
  DROP CONSTRAINT IF EXISTS coverage_metric_numerator_le_denominator;

ALTER TABLE coverage_record
  DROP CONSTRAINT IF EXISTS coverage_metric_named_denominator;

ALTER TABLE coverage_record
  DROP COLUMN IF EXISTS metric_value,
  DROP COLUMN IF EXISTS named_denominator,
  DROP COLUMN IF EXISTS not_evaluable,
  DROP COLUMN IF EXISTS denominator,
  DROP COLUMN IF EXISTS numerator,
  DROP COLUMN IF EXISTS metric_label,
  DROP COLUMN IF EXISTS metric_method,
  DROP COLUMN IF EXISTS input_digest;

COMMIT;
