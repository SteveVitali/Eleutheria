-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:publication_dispositions on pg

BEGIN;

-- The registry, index and both functions exist.
SELECT 1 / (CASE WHEN to_regclass('publication_disposition') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('publication_disposition_target_idx') IS NOT NULL
                THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'effective_disposition'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'publication_disposition_immutable'
  ) THEN 1 ELSE 0 END);

-- The immutability trigger is armed.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'publication_disposition_immutable'
  ) THEN 1 ELSE 0 END);

-- The spine_watermark facet exists with all three triggers.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM spine_watermark WHERE facet = 'publication_disposition'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN (
    SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
     WHERE c.relname = 'publication_disposition'
       AND t.tgname LIKE 'spine_watermark_%'
  ) = 3 THEN 1 ELSE 0 END);

-- Least privilege: sig_read_public holds column-grants (not a table grant) and
-- no INSERT/UPDATE/DELETE; sig_materialize holds INSERT but no UPDATE/DELETE.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.column_privileges
     WHERE table_name = 'publication_disposition'
       AND grantee = 'sig_read_public' AND privilege_type = 'SELECT'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT EXISTS (
    SELECT 1 FROM information_schema.table_privileges
     WHERE table_name = 'publication_disposition'
       AND grantee IN ('sig_read_public','sig_export','sig_materialize','sig_ingest')
       AND privilege_type IN ('UPDATE','DELETE')
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.table_privileges
     WHERE table_name = 'publication_disposition'
       AND grantee = 'sig_materialize' AND privilege_type = 'INSERT'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
