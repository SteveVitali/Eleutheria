-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:vocab_registries to pg
-- Appendix C.1: the controlled-vocabulary reference tables the claim spine's
-- foreign keys resolve against, plus the predicate registry (SIG-ONTO-066) and
-- the (genre x predicate) directness matrix (SIG-EPIS-017). Row *values* are
-- owned by the ontology (§20.1); this change owns the physical shape.

BEGIN;

CREATE TABLE vocab_entity_type          (entity_type text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_object_type          (object_type text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_evidence_role        (role text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_confidence           (confidence text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_rationale            (rationale_code text PRIMARY KEY, template text NOT NULL);
CREATE TABLE vocab_resolution_strategy  (strategy_id text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_normalization        (normalization_id text PRIMARY KEY, definition text NOT NULL);
CREATE TABLE vocab_source_reliability   (code text PRIMARY KEY, definition text NOT NULL);  -- R1..R6
CREATE TABLE vocab_claim_directness     (code text PRIMARY KEY, definition text NOT NULL);  -- D1..D6
CREATE TABLE vocab_artifact_integrity   (code text PRIMARY KEY, definition text NOT NULL);  -- I1..I3

-- The predicate registry. SIG-ONTO-066: a predicate without all of these is unresolvable.
CREATE TABLE vocab_predicate (
  predicate_id        text PRIMARY KEY,
  vocab_version       text NOT NULL,
  value_datatype      text NOT NULL,
  object_type         text NOT NULL REFERENCES vocab_object_type(object_type),
  cardinality         text NOT NULL DEFAULT 'single',
  definition          text NOT NULL,
  skos_concept_iri    text,
  volatility_class    text NOT NULL,            -- IMMUTABLE|GLACIAL|SLOW|MODERATE|FAST|VOLATILE
  half_life_days      integer,                  -- NULL only when IMMUTABLE
  is_windowed         boolean NOT NULL DEFAULT false,   -- SIG-RECON-011
  resolution_strategy text NOT NULL REFERENCES vocab_resolution_strategy(strategy_id),
  max_relative_spread numeric,                  -- numeric predicates: the U4 tolerance
  deprecated_at       timestamptz,
  superseded_by       text REFERENCES vocab_predicate(predicate_id),
  CHECK (volatility_class = 'IMMUTABLE' OR half_life_days IS NOT NULL)
);

-- The (genre x predicate) directness matrix. SIG-EPIS-017: published, versioned, not illustrative.
CREATE TABLE directness_matrix (
  artifact_type   text NOT NULL,
  predicate_id    text NOT NULL REFERENCES vocab_predicate(predicate_id),
  directness      text NOT NULL REFERENCES vocab_claim_directness(code),
  ruleset_version text NOT NULL,
  note            text,
  PRIMARY KEY (artifact_type, predicate_id, ruleset_version)
);

COMMIT;
