-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:temporal_invariants on pg

BEGIN;

-- TI-8 columns + reasoned-flag constraint exist.
SELECT temporally_unanchored, temporally_unanchored_reason
  FROM claim WHERE false;
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'claim_unanchored_reasoned'
  ) THEN 1 ELSE 0 END);

-- The new columns are in the append-only guard list.
SELECT 1 / (CASE WHEN (
    SELECT count(*) FROM append_only_guard
     WHERE table_name = 'claim'
       AND column_name IN ('temporally_unanchored', 'temporally_unanchored_reason')
  ) = 2 THEN 1 ELSE 0 END);

-- The as-of query functions exist with the two-axis signature.
SELECT 1 / (CASE WHEN (
    SELECT count(*) FROM pg_proc
     WHERE proname IN ('claim_as_of', 'resolution_as_of')
  ) = 2 THEN 1 ELSE 0 END);

ROLLBACK;
