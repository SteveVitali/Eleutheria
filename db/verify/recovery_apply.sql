-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:recovery_apply on pg
--
-- Structure + the least-privilege grant shape (the negative paths — a failed
-- UPDATE on a non-sys_period claim column, a DELETE, writes under a role with
-- no grants — are asserted by tests/db/test_recovery_apply.py where a
-- must-fail statement is a first-class pytest.raises instead of an aborted
-- verify transaction).

BEGIN;

-- Table, indexes, trigger, role exist.
SELECT 1/(CASE WHEN to_regclass('recovery_application') IS NOT NULL
    THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('recovery_application_claim_idx') IS NOT NULL
  AND to_regclass('recovery_application_execution_idx') IS NOT NULL
    THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'recovery_application_immutable')
    THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'sig_recovery') THEN 1 ELSE 0 END);

-- action_digest uniqueness is the exactly-once barrier.
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
     WHERE n.nspname = 'public' AND t.relname = 'recovery_application'
       AND c.contype = 'u'
       AND (SELECT array_agg(a.attname) FROM unnest(c.conkey) k
              JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k)
           = '{action_digest}'::name[]) THEN 1 ELSE 0 END);

-- The applier role's least-privilege shape: narrow canonical writes only.
SELECT 1/(CASE WHEN
      has_table_privilege('sig_recovery','recovery_application','INSERT')
  AND has_table_privilege('sig_recovery','recovery_application','SELECT')
  AND has_table_privilege('sig_recovery','claim','INSERT')
  AND has_column_privilege('sig_recovery','claim','sys_period','UPDATE')
  AND NOT has_column_privilege('sig_recovery','claim','raw_value','UPDATE')
  AND NOT has_table_privilege('sig_recovery','claim','DELETE')
  AND has_table_privilege('sig_recovery','claim_evidence','INSERT')
  AND has_table_privilege('sig_recovery','entity','INSERT')
  AND has_table_privilege('sig_recovery','entity_identity_key','INSERT')
  AND has_table_privilege('sig_recovery','ingest_run','INSERT')
  AND has_table_privilege('sig_recovery','publication_disposition','INSERT')
  AND NOT has_table_privilege('sig_recovery','review_decision','INSERT')
  AND NOT has_table_privilege('sig_recovery','evidence_capture','INSERT')
  AND NOT has_table_privilege('sig_recovery','evidence_capture','UPDATE')
  AND NOT has_table_privilege('sig_recovery','evidence_blob','INSERT')
  AND NOT has_table_privilege('sig_recovery','evidence_blob','UPDATE')
  AND NOT has_table_privilege('sig_recovery','extraction','INSERT')
  AND NOT has_table_privilege('sig_recovery','claim_evidence','UPDATE')
  AND NOT has_table_privilege('sig_recovery','claim_evidence','DELETE')
  AND NOT has_table_privilege('sig_recovery','publication_disposition','UPDATE')
  AND NOT has_table_privilege('sig_materialize','recovery_application','INSERT')
  AND NOT has_table_privilege('sig_ingest','recovery_application','INSERT')
  THEN 1 ELSE 0 END);

-- The deployer login holds membership (can SET ROLE like materialize_role).
SELECT 1/(CASE WHEN pg_has_role(current_user, 'sig_recovery', 'USAGE')
    THEN 1 ELSE 0 END);

-- The sealed-reader membership is what admits the applier past claim RLS:
-- sig_visible_max_tier() must resolve 2 under the role.
SET ROLE sig_recovery;
SELECT 1/(CASE WHEN sig_visible_max_tier() = 2 THEN 1 ELSE 0 END);
RESET ROLE;

ROLLBACK;
