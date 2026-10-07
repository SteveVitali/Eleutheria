-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:intake_reporter_outcome to pg
--
-- P34.37 (C4 NEW-17 / DR-C4-12, SIG-FIND-008): the reporter-facing projection
-- `intake.report_public` gains the disposition outcome, the published
-- corrections-log/release linkage and the safe tombstone — the facts a
-- reporter needs to see how their report ended. Still the ONLY intake
-- relation `sig_intake_receiver` may SELECT; the columns are additive
-- (CREATE OR REPLACE appends them at the end), the grants are unchanged,
-- and nothing restricted — raw narrative, contact, evidence URLs, claim
-- ids, reviewer rationale, network identifiers — is reachable through it.
-- Every projected value is already public-safe: the outcome is a vocabulary
-- id, the linkage values are screened at write time by
-- policy.intake.validate_publish_linkage, and public_response only appears
-- when the approver explicitly set public_response_publish.

BEGIN;

CREATE OR REPLACE VIEW intake.report_public WITH (security_invoker = off) AS
SELECT r.report_id,
       r.receipt_id,
       r.idempotency_key,
       r.category,
       r.received_at,
       r.expunged_at,
       COALESCE(le.event, 'received') AS lifecycle_event,
       intake.public_state(COALESCE(le.event, 'received')) AS state,
       pr.response AS public_response,
       oc.outcome AS outcome,
       pub.detail->>'correction_ref' AS correction_ref,
       pub.detail->>'publication_id' AS publication_id,
       pub.detail->>'tombstone' AS tombstone
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
  ) pr ON true
  -- P34.37: the decided outcome (refuse is a real, reportable outcome —
  -- SIG-GOV-004), taken from the latest deciding lifecycle event.
  LEFT JOIN LATERAL (
    SELECT e.detail->>'outcome' AS outcome
      FROM intake.event e
     WHERE e.report_id = r.report_id
       AND e.event IN ('disposition_approved','applied')
     ORDER BY e.event_seq DESC
     LIMIT 1
  ) oc ON true
  -- P34.37: the post-publication linkage (DR-C4-12) — the immutable release
  -- namespace and/or the corrections-log pointer the bridge recorded, or the
  -- screened tombstone when neither is linkable. Absent until `published`.
  LEFT JOIN LATERAL (
    SELECT e.detail
      FROM intake.event e
     WHERE e.report_id = r.report_id
       AND e.event = 'published'
     ORDER BY e.event_seq DESC
     LIMIT 1
  ) pub ON true;

COMMENT ON VIEW intake.report_public IS
  'P32.16/ADR-135 + P34.37: the receiver-role projection — report_id/'
  'receipt_id, idempotency_key (dedupe), category, received_at, coarse '
  'state, the decided outcome, the reviewer-approved public_response, and '
  'the published correction/release linkage (correction_ref, '
  'publication_id, tombstone). Raw narrative, contact, URLs, claim ids and '
  'network identifiers are unreachable from it by construction.';

COMMIT;
