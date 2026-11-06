-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:operator_purge on pg

BEGIN;

-- The function, both tables, both immutability triggers and the role exist.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc
     WHERE proname = 'sig_purge_claims'
       AND prosecdef IS TRUE          -- SECURITY DEFINER, per ADR-189
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('purge_tombstone') IS NOT NULL
                  THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('purge_audit') IS NOT NULL
                  THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
     WHERE c.relname = 'purge_tombstone'
       AND t.tgname = 'purge_tombstone_immutable'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
     WHERE c.relname = 'purge_audit'
       AND t.tgname = 'purge_audit_immutable'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles
     WHERE rolname = 'sig_purge_operator' AND NOT rolcanlogin
  ) THEN 1 ELSE 0 END);

-- EXECUTE is held by sig_purge_operator only (the owner's implicit rights
-- aside): no other named role may execute.
SELECT 1 / (CASE WHEN NOT has_function_privilege(
    'sig_ingest', 'sig_purge_claims(uuid[],text,text,text)', 'EXECUTE'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT has_function_privilege(
    'sig_materialize', 'sig_purge_claims(uuid[],text,text,text)', 'EXECUTE'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT has_function_privilege(
    'sig_read_public', 'sig_purge_claims(uuid[],text,text,text)', 'EXECUTE'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT has_function_privilege(
    'sig_export', 'sig_purge_claims(uuid[],text,text,text)', 'EXECUTE'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN has_function_privilege(
    'sig_purge_operator', 'sig_purge_claims(uuid[],text,text,text)', 'EXECUTE'
  ) THEN 1 ELSE 0 END);

-- The append-only trigger is still armed on claim.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'claim_append_only_trg'
  ) THEN 1 ELSE 0 END);

-- Grants posture: the tombstone is public-safe; the audit record is
-- restricted-only; no role holds UPDATE/DELETE on either.
SELECT 1 / (CASE WHEN has_table_privilege(
    'sig_read_public', 'purge_tombstone', 'SELECT'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN has_table_privilege(
    'sig_export', 'purge_tombstone', 'SELECT'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN has_table_privilege(
    'sig_read_sealed', 'purge_audit', 'SELECT'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT has_table_privilege(
    'sig_read_public', 'purge_audit', 'SELECT'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT EXISTS (
    SELECT 1 FROM information_schema.table_privileges
     WHERE table_name IN ('purge_tombstone', 'purge_audit')
       AND grantee IN ('sig_read_public','sig_export','sig_materialize',
                       'sig_ingest','sig_read_restricted','sig_read_sealed',
                       'sig_purge_operator')
       AND privilege_type IN ('INSERT','UPDATE','DELETE')
  ) THEN 1 ELSE 0 END);

-- The spine_watermark facet + its three triggers exist.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM spine_watermark WHERE facet = 'purge_tombstone'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN (
    SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
     WHERE c.relname = 'purge_tombstone'
       AND t.tgname LIKE 'spine_watermark_%'
  ) = 3 THEN 1 ELSE 0 END);

ROLLBACK;
