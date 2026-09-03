-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:relationships to pg
-- Appendix C.5: the edge tables. Every edge has a closed-catalog type (§12) and
-- is evidenced (no unevidenced edges). `integrates_with` is forbidden by CHECK
-- (SIG-ONTO-045). entity_role carries the fourteen roles of §12.4.

BEGIN;

CREATE TABLE relationship (
  relationship_id uuid PRIMARY KEY DEFAULT uuidv7(),
  from_entity    uuid NOT NULL REFERENCES entity(entity_id),
  to_entity      uuid NOT NULL REFERENCES entity(entity_id),
  edge_type      text NOT NULL,                 -- the CLOSED catalog of §12; no 'integrates_with'
  -- Access-edge attributes (§12.5)
  access_kind    text,                          -- configured_access|observed_use|declared_policy
  scope          text,
  direction      text NOT NULL,
  automaticity   text,
  -- Integration-edge attributes (§12.3)
  initiator      text,
  transport      text,
  granularity    text,
  data_comes_to_rest boolean,
  consent_gate   text,
  mechanism      text,
  terminable_by  text,
  termination_reason text,
  applies_to_cohort text DEFAULT 'all',         -- SIG-ONTO-046.2
  -- Universal (SIG-ONTO-041)
  asserted_by    uuid REFERENCES entity(entity_id),   -- perspective; enables asymmetry detection
  valid_period   tstzrange NOT NULL,
  valid_from_kind text NOT NULL DEFAULT 'unknown',
  valid_to_kind   text NOT NULL DEFAULT 'unknown',
  observed_at    timestamptz,
  sys_period     tstzrange NOT NULL DEFAULT tstzrange(clock_timestamp(), NULL, '[)'),
  evidence_claim uuid NOT NULL REFERENCES claim(claim_id),   -- no unevidenced edges
  CHECK (edge_type <> 'integrates_with')        -- SIG-ONTO-045, enforced
);
CREATE INDEX relationship_from_idx ON relationship (from_entity, edge_type);
CREATE INDEX relationship_to_idx   ON relationship (to_entity, edge_type);
CREATE INDEX relationship_valid_idx ON relationship USING gist (valid_period);

CREATE TABLE entity_role (                      -- the FOURTEEN roles of §12.4
  entity_id      uuid NOT NULL REFERENCES entity(entity_id),   -- the asset/deployment/system
  actor_id       uuid NOT NULL REFERENCES entity(entity_id),   -- the organization
  role           text NOT NULL,
  valid_period   tstzrange NOT NULL,
  evidence_claim uuid NOT NULL REFERENCES claim(claim_id),
  PRIMARY KEY (entity_id, actor_id, role, valid_period)
);

COMMIT;
