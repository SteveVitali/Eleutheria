-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:disposition_decided_at_authority on pg

BEGIN;

-- decided_at defaults to the DB clock — the single clock authority the
-- eligibility fragments evaluate against.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_name = 'publication_disposition' AND column_name = 'decided_at'
       AND column_default LIKE '%clock_timestamp%'
  ) THEN 1 ELSE 0 END);

-- The authority contract is recorded on the column.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_description d
      JOIN pg_class c ON c.oid = d.objoid
      JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.objsubid
     WHERE c.relname = 'publication_disposition' AND a.attname = 'decided_at'
       AND d.description LIKE '%single clock authority%'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
