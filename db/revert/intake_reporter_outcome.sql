-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:intake_reporter_outcome from pg
--
-- P34.37: restore the P32.16 `intake.report_public` shape (without the
-- outcome/linkage columns). CREATE OR REPLACE cannot drop view columns, so
-- the view is rebuilt and its two SELECT grants re-stated — no data is
-- touched (the projection derives from the append-only event log).

BEGIN;

DROP VIEW intake.report_public;
CREATE VIEW intake.report_public WITH (security_invoker = off) AS
SELECT r.report_id,
       r.receipt_id,
       r.idempotency_key,
       r.category,
       r.received_at,
       r.expunged_at,
       COALESCE(le.event, 'received') AS lifecycle_event,
       intake.public_state(COALESCE(le.event, 'received')) AS state,
       pr.response AS public_response
  FROM intake.report r
  LEFT JOIN LATERAL (
    SELECT e.event, e.detail
      FROM intake.event e
     WHERE e.report_id = r.report_id
       AND e.event IN ('received','triaged','assigned','review_requested',
                       'disposition_proposed','disposition_approved',
                       'applied','published','closed')
     ORDER BY e.event_seq DESC
     LIMIT 1
  ) le ON true
  LEFT JOIN LATERAL (
    SELECT e.detail->>'public_response' AS response
      FROM intake.event e
     WHERE e.report_id = r.report_id
       AND e.event IN ('disposition_approved','published','closed')
       AND COALESCE((e.detail->>'public_response_publish')::boolean, false)
     ORDER BY e.event_seq DESC
     LIMIT 1
  ) pr ON true;

COMMENT ON VIEW intake.report_public IS
  'P32.16/ADR-135: the receiver-role projection — report_id/receipt_id, '
  'idempotency_key (dedupe), category, received_at, coarse state and the '
  'reviewer-approved public_response only. Raw narrative, contact, URLs and '
  'network identifiers are unreachable from it by construction.';

GRANT SELECT ON intake.report_public TO sig_intake_receiver, sig_intake_reviewer;

COMMIT;
