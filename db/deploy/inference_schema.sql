-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:inference_schema to pg
-- Appendix C.6 (L4): a SEPARATE schema, so an inference can never be mistaken for
-- an observation (§8.1, SIG-ONTO-002). Every derived row carries its rule,
-- version, and input_claim_ids — "every inference says it is an inference".

BEGIN;

CREATE SCHEMA inference;

CREATE TABLE inference.derived_fact (
  derived_id     uuid PRIMARY KEY DEFAULT uuidv7(),
  subject_id     uuid NOT NULL,
  predicate_id   text NOT NULL,
  value_json     jsonb NOT NULL,
  derivation_rule text NOT NULL,
  rule_version   text NOT NULL,
  input_claim_ids uuid[] NOT NULL,
  confidence     text NOT NULL,
  derived_at     timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE inference.derived_geometry (       -- SIG-GEO-006
  derived_id     uuid PRIMARY KEY DEFAULT uuidv7(),
  asset_id       uuid NOT NULL REFERENCES entity(entity_id),
  geometry       geometry(Geometry, 4326) NOT NULL,
  geometry_kind  text NOT NULL,                 -- fov_cone|coverage_estimate|road_snap
  model_version  text NOT NULL,
  assumptions    jsonb NOT NULL,
  input_claim_ids uuid[] NOT NULL,
  derived_at     timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMIT;
