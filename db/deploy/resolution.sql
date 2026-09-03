-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:resolution to pg
-- §16.4: the L3 resolution table — a stored, attributable, diffable DECISION
-- record (SIG-STORE-014), not a view. At most one resolved value per
-- (subject, predicate) may be current for any instant of valid time, enforced by
-- a GiST exclusion constraint IN THE DATABASE, never by application code
-- (SIG-STORE-016). unresolved_conflict is a first-class publishable outcome
-- (SIG-STORE-015). resolver_version and ruleset_version version independently
-- (SIG-STORE-017); human overrides are first-class (SIG-STORE-019).

BEGIN;

CREATE TABLE resolution (
  resolution_id       uuid PRIMARY KEY DEFAULT uuidv7(),
  subject_id          uuid NOT NULL REFERENCES entity(entity_id),
  predicate_id        text NOT NULL REFERENCES vocab_predicate(predicate_id),

  value_kind          value_kind NOT NULL,
  value_text          text,
  value_num           numeric,
  value_geom          geometry(Geometry, 4326),
  value_json          jsonb,
  object_entity       uuid REFERENCES entity(entity_id),

  valid_period        tstzrange NOT NULL,
  sys_period          tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),

  -- WHY: what makes this a decision record rather than a cache
  winning_claim       uuid REFERENCES claim(claim_id),
  considered_claims   uuid[] NOT NULL,
  dissenting_claims   uuid[] NOT NULL DEFAULT '{}',
  contradiction_state text NOT NULL,   -- uncontested|resolved_conflict|unresolved_conflict|insufficient
  strategy_id         text NOT NULL REFERENCES vocab_resolution_strategy(strategy_id),
  rationale_code      text NOT NULL REFERENCES vocab_rationale(rationale_code),
  rationale_text      text NOT NULL,   -- a quotable sentence
  confidence          text NOT NULL REFERENCES vocab_confidence(confidence),
  evidence_counts     jsonb NOT NULL,  -- machine-readable support/dissent counts by tier (§10.6)
  resolver_version    text NOT NULL,
  ruleset_version     text NOT NULL,
  decided_by          text NOT NULL DEFAULT 'auto',
  decided_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
  override_rationale  text,

  CONSTRAINT resolution_no_overlap
    EXCLUDE USING gist (subject_id WITH =, predicate_id WITH =, valid_period WITH &&)
    WHERE (upper_inf(sys_period)),
  CONSTRAINT resolution_override_reasoned CHECK (
    decided_by = 'auto' OR override_rationale IS NOT NULL
  )
);

CREATE INDEX resolution_subject_pred_idx ON resolution (subject_id, predicate_id);

COMMIT;
