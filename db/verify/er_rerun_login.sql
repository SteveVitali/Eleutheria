-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:er_rerun_login on pg
--
-- P34.45: the write-capable re-run login's least-privilege shape — posture
-- flags, the 2-connection cap, exactly one membership (sig_materialize), the
-- append-only camera-site surface (INSERT+SELECT, no UPDATE/DELETE/TRUNCATE),
-- and no claim-spine write. Refused-write probes under SET ROLE live in
-- tests/db/test_er_rerun_login.py — a must-fail statement is a first-class
-- pytest.raises, not an aborted verify transaction.

BEGIN;

SET LOCAL lock_timeout = '5s';

-- sig_materialize_login exists as LOGIN with the least-privilege flags + a
-- 2-connection cap, and NO read-only session default (it is the one
-- write-capable login — INSERT grants bound it, not a session flag).
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles
     WHERE rolname = 'sig_materialize_login' AND rolcanlogin
       AND NOT rolsuper AND NOT rolcreaterole AND NOT rolcreatedb
       AND NOT rolbypassrls AND rolconnlimit = 2
       AND NOT (coalesce(rolconfig, '{}'::text[]) @> ARRAY['default_transaction_read_only=on']))
    THEN 1 ELSE 0 END);

-- Its DIRECT memberships are exactly {sig_materialize}.
SELECT 1/(CASE WHEN
      pg_has_role('sig_materialize_login', 'sig_materialize', 'USAGE')
  AND NOT EXISTS (
    SELECT 1 FROM pg_auth_members m
     JOIN pg_roles member ON m.member = member.oid
     JOIN pg_roles grp    ON m.roleid = grp.oid
     WHERE member.rolname = 'sig_materialize_login'
       AND grp.rolname <> 'sig_materialize')
    THEN 1 ELSE 0 END);

-- The ER surface, inherited through the group: INSERT + SELECT on the
-- append-only camera-site tables, and INSERT into the review queue.
SELECT 1/(CASE WHEN
      has_table_privilege('sig_materialize_login','camera_site_match','INSERT')
  AND has_table_privilege('sig_materialize_login','camera_site_run','INSERT')
  AND has_table_privilege('sig_materialize_login','camera_site_execution','INSERT')
  AND has_table_privilege('sig_materialize_login','review_item','INSERT')
  AND has_table_privilege('sig_materialize_login','camera_site_match','SELECT')
  AND has_table_privilege('sig_materialize_login','camera_site_execution','SELECT')
  AND has_table_privilege('sig_materialize_login','review_decision','SELECT')
    THEN 1 ELSE 0 END);

-- Nothing mutates: no UPDATE/DELETE/TRUNCATE on the camera-site tables, and
-- no claim-spine write of any kind (the claim spine is insert-only through
-- sig_ingest — this login is not it).
SELECT 1/(CASE WHEN
      NOT has_table_privilege('sig_materialize_login','camera_site_match','UPDATE')
  AND NOT has_table_privilege('sig_materialize_login','camera_site_match','DELETE')
  AND NOT has_table_privilege('sig_materialize_login','camera_site_match','TRUNCATE')
  AND NOT has_table_privilege('sig_materialize_login','camera_site_run','UPDATE')
  AND NOT has_table_privilege('sig_materialize_login','camera_site_run','DELETE')
  AND NOT has_table_privilege('sig_materialize_login','camera_site_execution','UPDATE')
  AND NOT has_table_privilege('sig_materialize_login','camera_site_execution','DELETE')
  AND NOT has_table_privilege('sig_materialize_login','claim','INSERT')
  AND NOT has_table_privilege('sig_materialize_login','claim','UPDATE')
  AND NOT has_table_privilege('sig_materialize_login','claim','DELETE')
  AND NOT has_table_privilege('sig_materialize_login','evidence_capture','INSERT')
  AND NOT has_table_privilege('sig_materialize_login','publication_disposition','UPDATE')
    THEN 1 ELSE 0 END);

ROLLBACK;
