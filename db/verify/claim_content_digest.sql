-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:claim_content_digest on pg

BEGIN;

-- The column exists.
SELECT content_digest FROM claim WHERE false;

-- The partial unique index exists.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'public' AND indexname = 'claim_content_digest_key'
  ) THEN 1 ELSE 0 END);

-- The new column is in the append-only guard list.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM append_only_guard
     WHERE table_name = 'claim' AND column_name = 'content_digest'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
