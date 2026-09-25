-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:review_campaign to pg
-- P31.10 (camera-site review surface): the stratified review CAMPAIGN tag.
--
-- A campaign is a seeded, reproducible sample of pending review_item proposals
-- drawn for human review (the Round-10 camera-site campaign per design §6 Q11).
-- `review_item.payload` is immutable (insert-only), so campaign membership is
-- recorded in its own append-only relation — the same materialize posture as
-- every other artifact (deterministic ids, ON CONFLICT DO NOTHING, +0 re-run):
--
--   * `review_campaign`      — one row per drawn campaign: the label, the
--     purpose (e.g. "prepared for Round 10"), the full design (strata spec,
--     seed, n, per-stratum universe counts), and the tool/engineering actor —
--     never a person. `campaign_id` is caller-chosen; a conflicting design under
--     an existing id is refused by the caller (the row is never overwritten).
--   * `review_campaign_item` — the (campaign, item) membership, one row each,
--     carrying the stratum that drew the item. PRIMARY KEY (campaign_id,
--     item_id) + INSERT ... ON CONFLICT DO NOTHING makes a re-draw idempotent.
--
-- Grants mirror the existing least-privilege split: the materialize role may
-- SELECT + INSERT campaign rows (and now INSERT review_decision, so the
-- authenticated curation path can run under the same limited role); the public
-- read roles may SELECT both campaign tables (a campaign's membership is
-- public-class metadata — the items themselves are already SELECTable).
-- No UPDATE/DELETE anywhere; append-only only.

BEGIN;

CREATE TABLE review_campaign (
  campaign_id   text PRIMARY KEY,             -- caller-chosen label, e.g. 'camsite-round10-a'
  purpose       text NOT NULL,                -- e.g. 'prepared for Round 10 (P31.18); not a Round-9 campaign'
  design        jsonb NOT NULL DEFAULT '{}',  -- strata spec, seed, n, per-stratum universe + drawn counts
  created_by    text NOT NULL,                -- the tool/engineering actor, never a person
  created_at    timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE review_campaign_item (
  campaign_id   text NOT NULL REFERENCES review_campaign(campaign_id),
  item_id       text NOT NULL REFERENCES review_item(item_id),
  stratum       text NOT NULL,                -- the stratum that drew it (1g/3g/4g/5g/soft-conflict/disputed)
  created_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (campaign_id, item_id)
);

-- Read path: the public read roles may inspect campaign membership; the
-- materialize role draws campaigns and — new here — may append the human
-- review_decision rows the authenticated curation surface writes.
GRANT SELECT ON review_campaign, review_campaign_item TO sig_read_public, sig_export;
GRANT SELECT, INSERT ON review_campaign, review_campaign_item TO sig_materialize;
GRANT INSERT ON review_decision TO sig_materialize;

COMMIT;
