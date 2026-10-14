-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:seal_register on pg

BEGIN;

-- The register, its indexes, both functions and the writer role exist.
SELECT 1 / (CASE WHEN to_regclass('capture_seal') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('capture_seal_capture_idx') IS NOT NULL
                THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('capture_seal_digest_idx') IS NOT NULL
                THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'capture_currently_sealed'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'capture_seal_immutable'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'sig_seal_writer'
  ) THEN 1 ELSE 0 END);

-- The immutability trigger is armed.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'capture_seal_immutable'
  ) THEN 1 ELSE 0 END);

-- The spine_watermark facet exists with all three triggers.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM spine_watermark WHERE facet = 'capture_seal'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN (
    SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
     WHERE c.relname = 'capture_seal'
       AND t.tgname LIKE 'spine_watermark_%'
  ) = 3 THEN 1 ELSE 0 END);

-- Least privilege: sig_read_public holds column-grants (not a table grant)
-- and no INSERT/UPDATE/DELETE; sig_seal_writer holds INSERT but no
-- UPDATE/DELETE; sig_seal_writer is NOLOGIN.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.column_privileges
     WHERE table_name = 'capture_seal'
       AND grantee = 'sig_read_public' AND privilege_type = 'SELECT'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT EXISTS (
    SELECT 1 FROM information_schema.table_privileges
     WHERE table_name = 'capture_seal'
       AND grantee IN ('sig_read_public','sig_export','sig_materialize',
                       'sig_ingest','sig_seal_writer')
       AND privilege_type IN ('UPDATE','DELETE')
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.column_privileges
     WHERE table_name = 'capture_seal'
       AND grantee = 'sig_seal_writer' AND privilege_type = 'INSERT'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'sig_seal_writer' AND NOT rolcanlogin
  ) THEN 1 ELSE 0 END);

ROLLBACK;
