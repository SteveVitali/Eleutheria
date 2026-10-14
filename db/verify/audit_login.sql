-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:audit_login on pg
--
-- P34.43: the logins' least-privilege shape (posture flags, connection
-- limits, session defaults, memberships, the exact read surface, and the
-- writes they must NOT hold). Refused-write probes under SET ROLE live in
-- tests/db/test_audit_login.py — a must-fail statement is a first-class
-- pytest.raises, not an aborted verify transaction.

BEGIN;

SET LOCAL lock_timeout = '5s';

-- sig_audit exists as LOGIN with the least-privilege flags + a 4-connection cap.
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles
     WHERE rolname = 'sig_audit' AND rolcanlogin
       AND NOT rolsuper AND NOT rolcreaterole AND NOT rolcreatedb
       AND NOT rolbypassrls AND rolconnlimit = 4)
    THEN 1 ELSE 0 END);

-- Its session defaults: read-only + a 60s statement timeout.
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles
     WHERE rolname = 'sig_audit'
       AND rolconfig @> ARRAY['default_transaction_read_only=on']
       AND rolconfig @> ARRAY['statement_timeout=60s'])
    THEN 1 ELSE 0 END);

-- READ: the §37 surface via membership in sig_read_public.
SELECT 1/(CASE WHEN pg_has_role('sig_audit', 'sig_read_public', 'USAGE')
    THEN 1 ELSE 0 END);

-- The NEW-16 capture-store grants, exactly (SELECT — no write).
SELECT 1/(CASE WHEN
      has_table_privilege('sig_audit','ingest_run_capture','SELECT')
  AND has_table_privilege('sig_audit','entity_identity_key','SELECT')
  AND NOT has_table_privilege('sig_audit','ingest_run_capture','INSERT')
  AND NOT has_table_privilege('sig_audit','ingest_run_capture','UPDATE')
  AND NOT has_table_privilege('sig_audit','ingest_run_capture','DELETE')
  AND NOT has_table_privilege('sig_audit','entity_identity_key','INSERT')
  AND NOT has_table_privilege('sig_audit','entity_identity_key','UPDATE')
  AND NOT has_table_privilege('sig_audit','entity_identity_key','DELETE')
  AND NOT has_table_privilege('sig_audit','claim','INSERT')
  AND NOT has_table_privilege('sig_audit','claim','UPDATE')
  AND NOT has_table_privilege('sig_audit','claim','DELETE')
  AND NOT has_table_privilege('sig_audit','evidence_capture','INSERT')
  AND NOT has_table_privilege('sig_audit','publication_disposition','INSERT')
  AND NOT has_table_privilege('sig_audit','recovery_application','INSERT')
    THEN 1 ELSE 0 END);

-- The audit login is not a member of any write-bearing role.
SELECT 1/(CASE WHEN
      NOT pg_has_role('sig_audit', 'sig_recovery', 'USAGE')
  AND NOT pg_has_role('sig_audit', 'sig_materialize', 'USAGE')
  AND NOT pg_has_role('sig_audit', 'sig_intake_bridge', 'USAGE')
    THEN 1 ELSE 0 END);

-- sig_recovery_login exists as LOGIN with the cap, a member of the group
-- role — and nothing else (its surface is sig_recovery's, never duplicated).
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles
     WHERE rolname = 'sig_recovery_login' AND rolcanlogin
       AND NOT rolsuper AND NOT rolcreaterole AND NOT rolcreatedb
       AND NOT rolbypassrls AND rolconnlimit = 2)
    THEN 1 ELSE 0 END);
-- Its DIRECT memberships are exactly {sig_recovery}: the read surface it
-- reaches transitively is the group's own L52 scope, never duplicated here.
SELECT 1/(CASE WHEN
      pg_has_role('sig_recovery_login', 'sig_recovery', 'USAGE')
  AND NOT EXISTS (
    SELECT 1 FROM pg_auth_members m
     JOIN pg_roles member ON m.member = member.oid
     JOIN pg_roles grp    ON m.roleid = grp.oid
     WHERE member.rolname = 'sig_recovery_login'
       AND grp.rolname <> 'sig_recovery')
    THEN 1 ELSE 0 END);

ROLLBACK;
