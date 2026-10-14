-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:intake_reporter_outcome on pg
--
-- P34.37 (DR-C4-12): the reporter projection carries the outcome + published
-- linkage columns and keeps its exact least-privilege grant shape. The
-- behavioural end-to-end (reporter sees outcome/response/link) is asserted by
-- tests/db/test_intake_pg.py over the role-scoped stores.

BEGIN;

-- The four additive columns exist on the view (order-appended).
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'intake' AND table_name = 'report_public'
       AND column_name IN ('outcome','correction_ref','publication_id','tombstone')
    HAVING count(*) = 4) THEN 1 ELSE 0 END);

-- The grant shape is unchanged: receiver + reviewer read it, nobody else.
SELECT 1/(CASE WHEN
      has_table_privilege('sig_intake_receiver','intake.report_public','SELECT')
  AND has_table_privilege('sig_intake_reviewer','intake.report_public','SELECT')
  AND NOT has_table_privilege('sig_read_public','intake.report_public','SELECT')
  AND NOT has_table_privilege('sig_intake_receiver','intake.report','SELECT')
  THEN 1 ELSE 0 END);

-- A guarded projection probe: seed a report under the receiver role, decide
-- + publish it under reviewer/bridge rows the verify transaction fabricates
-- directly, and the public row reports outcome + linkage — all rolled back.
SET LOCAL ROLE sig_intake_receiver;
INSERT INTO intake.report (report_id, receipt_id, idempotency_key, category, description)
VALUES ('00000000-0000-4000-8000-0000000000bb', 'rct-00000000000000000000000000face01',
        'verify-nonce-outcome-01', 'factual_error', 'verify row — rolled back');
RESET ROLE;

SET LOCAL ROLE sig_intake_reviewer;
INSERT INTO intake.event (report_id, event, actor, detail)
VALUES ('00000000-0000-4000-8000-0000000000bb','disposition_approved','verify-cur',
        '{"outcome":"suppress","reason":"verified","public_response":"Withheld.",
          "public_response_publish":true}'::jsonb);
RESET ROLE;
-- `published` is a bridge-only event — the writer guard admits it only under
-- the P32.16a role.
SET LOCAL ROLE sig_intake_bridge;
INSERT INTO intake.event (report_id, event, actor, detail)
VALUES ('00000000-0000-4000-8000-0000000000bb','published','sig-intake-bridge',
        '{"correction_ref":"dddddddd-0000-4000-8000-000000000000",
          "publication_id":"p-00000000000000000000000000000000000000000000000000000000000000ff"}'::jsonb);

SET LOCAL ROLE sig_intake_receiver;
SELECT 1/(CASE WHEN EXISTS (
    SELECT 1 FROM intake.report_public
     WHERE receipt_id = 'rct-00000000000000000000000000face01'
       AND state = 'resolved' AND outcome = 'suppress'
       AND public_response = 'Withheld.'
       AND correction_ref = 'dddddddd-0000-4000-8000-000000000000'
       AND publication_id LIKE 'p-%') THEN 1 ELSE 0 END);
RESET ROLE;

ROLLBACK;
