-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:claim_payload_version on pg

BEGIN;

-- The column exists and is nullable (additive; no default rewrites old rows).
SELECT payload_version FROM claim WHERE false;

-- Nullable with no default: existing rows must not gain a value on deploy.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'claim'
       AND column_name = 'payload_version'
       AND is_nullable = 'YES' AND column_default IS NULL
  ) THEN 1 ELSE 0 END);

-- The new column is in the append-only guard list.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM append_only_guard
     WHERE table_name = 'claim' AND column_name = 'payload_version'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
