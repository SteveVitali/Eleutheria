-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:coverage_exclusion_disclosure on pg

BEGIN;

-- The disclosure column exists.
SELECT exclusions FROM coverage_record WHERE false;

-- The sum CHECK exists (numerator + excluded = denominator, pinned at the DB).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'coverage_ratio_exclusions_sum'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
