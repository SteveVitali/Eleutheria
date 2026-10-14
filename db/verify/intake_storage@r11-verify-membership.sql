-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:intake_storage on pg
--
-- Structure + one guarded end-to-end write (the negative paths — reserved
-- bridge events, cross-role writes, immutable identity fields — are asserted by
-- tests/db/test_intake_pg.py, where a must-fail statement is a first-class
-- pytest.raises instead of an aborted verify transaction).

BEGIN;

-- Schema, tables, view, index, guards and functions exist.
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_namespace WHERE nspname = 'intake') THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('intake.report') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('intake.reporter_contact') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('intake.receipt') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('intake.event') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('intake.report_public') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN to_regclass('intake.intake_event_report_idx') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'intake' AND p.proname IN (
       'event_writer_guard','append_only_guard','report_mutation_guard',
       'contact_mutation_guard','redact_report','expunge_report','public_state')) THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN (
    SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'intake' AND p.proname IN (
       'event_writer_guard','append_only_guard','report_mutation_guard',
       'contact_mutation_guard','redact_report','expunge_report','public_state')) = 7
    THEN 1 ELSE 0 END);

-- The writer/mutation guards are armed.
SELECT 1/(CASE WHEN (
    SELECT count(*) FROM pg_trigger
     WHERE tgname IN ('intake_event_writer_guard','intake_receipt_immutable',
                      'intake_event_immutable','intake_report_mutation_guard',
                      'intake_contact_mutation_guard')) = 5
    THEN 1 ELSE 0 END);

-- Both roles exist.
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'sig_intake_receiver') THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'sig_intake_reviewer') THEN 1 ELSE 0 END);

-- Least-privilege shape: receiver inserts payloads + reads the projection and
-- the digest columns only; reviewer reads payloads + appends events; PUBLIC
-- cannot execute the maintenance functions; no existing role touches intake.
SELECT 1/(CASE WHEN
      has_table_privilege('sig_intake_receiver','intake.report','INSERT')
  AND has_table_privilege('sig_intake_receiver','intake.reporter_contact','INSERT')
  AND has_table_privilege('sig_intake_receiver','intake.receipt','INSERT')
  AND has_table_privilege('sig_intake_receiver','intake.event','INSERT')
  AND has_table_privilege('sig_intake_receiver','intake.report_public','SELECT')
  AND has_column_privilege('sig_intake_receiver','intake.receipt','token_digest','SELECT')
  AND NOT has_table_privilege('sig_intake_receiver','intake.report','SELECT')
  AND NOT has_table_privilege('sig_intake_receiver','intake.report','UPDATE')
  AND NOT has_table_privilege('sig_intake_receiver','claim','INSERT')
  AND NOT has_table_privilege('sig_intake_receiver','review_decision','INSERT')
  AND NOT has_table_privilege('sig_intake_receiver','publication_disposition','INSERT')
  AND has_table_privilege('sig_intake_reviewer','intake.report','SELECT')
  AND has_table_privilege('sig_intake_reviewer','intake.reporter_contact','SELECT')
  AND has_table_privilege('sig_intake_reviewer','intake.event','INSERT')
  AND NOT has_table_privilege('sig_intake_reviewer','intake.report','UPDATE')
  AND NOT has_table_privilege('sig_intake_reviewer','claim','INSERT')
  AND NOT has_table_privilege('sig_read_public','intake.report','SELECT')
  AND NOT has_table_privilege('sig_export','intake.report','SELECT')
  AND NOT has_table_privilege('sig_ingest','intake.report','SELECT')
  AND NOT has_table_privilege('sig_materialize','intake.report','SELECT')
  AND has_function_privilege('sig_intake_reviewer','intake.expunge_report(uuid)','EXECUTE')
  AND has_function_privilege('sig_intake_reviewer','intake.redact_report(uuid,text[],text)','EXECUTE')
  AND NOT has_function_privilege('public','intake.expunge_report(uuid)','EXECUTE')
  THEN 1 ELSE 0 END);

-- One guarded end-to-end write: receiver appends report+receipt+received,
-- reviewer appends triaged + expunges, and the coarse projection shows
-- under_review with the payload blanked — all inside this transaction.
SET LOCAL ROLE sig_intake_receiver;
INSERT INTO intake.report (report_id, receipt_id, idempotency_key, category, description)
VALUES ('00000000-0000-4000-8000-0000000000aa', 'rct-00000000000000000000000000beef01',
        'verify-nonce-00000000', 'factual_error', 'verify row — expunged below');
INSERT INTO intake.receipt (report_id, token_digest)
VALUES ('00000000-0000-4000-8000-0000000000aa',
        decode('00000000000000000000000000000000000000000000000000000000000000aa','hex'));
INSERT INTO intake.event (report_id, event, actor)
VALUES ('00000000-0000-4000-8000-0000000000aa', 'received', 'sig-intake-receiver');
RESET ROLE;

SET LOCAL ROLE sig_intake_reviewer;
INSERT INTO intake.event (report_id, event, actor, detail)
VALUES ('00000000-0000-4000-8000-0000000000aa', 'triaged', 'verify-reviewer', '{}'::jsonb);
SELECT intake.expunge_report('00000000-0000-4000-8000-0000000000aa');
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM intake.report_public
     WHERE receipt_id = 'rct-00000000000000000000000000beef01'
       AND state = 'under_review' AND expunged_at IS NOT NULL
       AND lifecycle_event = 'triaged') THEN 1 ELSE 0 END);
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM intake.report
     WHERE receipt_id = 'rct-00000000000000000000000000beef01'
       AND description = '[expunged]' AND publication_id IS NULL) THEN 1 ELSE 0 END);
RESET ROLE;

ROLLBACK;
