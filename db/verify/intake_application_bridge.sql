-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:intake_application_bridge on pg
--
-- Structure + the least-privilege grant shape (the negative paths — reviewer
-- still refused applied/published, receiver still without canonical writes,
-- the full apply transaction — are asserted by
-- tests/db/test_intake_apply_pg.py, where a must-fail statement is a
-- first-class pytest.raises instead of an aborted verify transaction).

BEGIN;

-- Table, index, trigger, role exist.
SELECT 1/(CASE WHEN to_regclass('intake.application') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('intake.intake_application_report_idx') IS NOT NULL
    THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger WHERE tgname = 'intake_application_immutable')
    THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'sig_intake_bridge') THEN 1 ELSE 0 END);

-- operation_id uniqueness is the exactly-once barrier.
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
     WHERE n.nspname = 'intake' AND t.relname = 'application'
       AND c.contype = 'u'
       AND (SELECT array_agg(a.attname) FROM unnest(c.conkey) k
              JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k)
           = '{operation_id}'::name[]) THEN 1 ELSE 0 END);

-- The bridge role's least-privilege shape: narrow canonical writes, no
-- receiver/reviewer broadening, no review_decision/capture/payload write.
SELECT 1/(CASE WHEN
      has_table_privilege('sig_intake_bridge','intake.application','INSERT')
  AND has_table_privilege('sig_intake_bridge','intake.application','SELECT')
  AND has_table_privilege('sig_intake_bridge','intake.event','INSERT')
  AND has_table_privilege('sig_intake_bridge','intake.report','SELECT')
  AND has_table_privilege('sig_intake_bridge','claim','INSERT')
  AND has_column_privilege('sig_intake_bridge','claim','sys_period','UPDATE')
  AND NOT has_column_privilege('sig_intake_bridge','claim','raw_value','UPDATE')
  AND NOT has_table_privilege('sig_intake_bridge','claim','DELETE')
  AND has_table_privilege('sig_intake_bridge','claim_evidence','INSERT')
  AND has_table_privilege('sig_intake_bridge','entity','INSERT')
  AND has_table_privilege('sig_intake_bridge','entity_identity_key','INSERT')
  AND has_table_privilege('sig_intake_bridge','ingest_run','INSERT')
  AND has_table_privilege('sig_intake_bridge','publication_disposition','INSERT')
  AND NOT has_table_privilege('sig_intake_bridge','review_decision','INSERT')
  AND NOT has_table_privilege('sig_intake_bridge','intake.report','INSERT')
  AND NOT has_table_privilege('sig_intake_bridge','intake.report','UPDATE')
  AND NOT has_table_privilege('sig_intake_bridge','intake.reporter_contact','SELECT')
  AND NOT has_table_privilege('sig_intake_receiver','claim','INSERT')
  AND NOT has_table_privilege('sig_intake_receiver','intake.application','INSERT')
  AND NOT has_table_privilege('sig_intake_reviewer','intake.application','INSERT')
  AND NOT has_table_privilege('sig_intake_reviewer','claim','INSERT')
  THEN 1 ELSE 0 END);

-- The sealed-reader membership is what admits the bridge past claim RLS:
-- sig_visible_max_tier() must resolve 2 under the role.
SET ROLE sig_intake_bridge;
SELECT 1/(CASE WHEN sig_visible_max_tier() = 2 THEN 1 ELSE 0 END);
RESET ROLE;

-- The writer guard admits `applied` only under the bridge role now.
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'intake' AND p.proname = 'event_writer_guard'
       AND p.prosrc LIKE '%sig_intake_bridge%') THEN 1 ELSE 0 END);

ROLLBACK;
