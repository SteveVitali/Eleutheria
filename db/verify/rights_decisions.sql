-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:rights_decisions on pg

BEGIN;

-- The decision table exists with its key columns.
SELECT decision_id, source_id, rights_id, prior_rights_id, basis, reviewer,
       review_packet, terms_url, terms_capture_id, decided_at
  FROM rights_decision WHERE false;

-- decided_at defaults to the DB clock (not caller-supplied).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_name = 'rights_decision' AND column_name = 'decided_at'
       AND column_default LIKE '%clock_timestamp%'
  ) THEN 1 ELSE 0 END);

-- The latest-decision index exists.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'public' AND indexname = 'rights_decision_source_idx'
  ) THEN 1 ELSE 0 END);

-- The immutability trigger exists (UPDATE and DELETE both refuse).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid
     WHERE c.relname = 'rights_decision' AND t.tgname = 'rights_decision_immutable'
       AND NOT t.tgisinternal
  ) THEN 1 ELSE 0 END);

ROLLBACK;
