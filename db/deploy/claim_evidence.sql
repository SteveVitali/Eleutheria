-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim_evidence to pg
-- §16.5: a claim has an evidence SET (not a single source), each row carrying a
-- role — including `contradicts`, which records a document as evidence AGAINST a
-- claim without inventing a negative claim (SIG-EPIS-011). claim_qualifier carries
-- the per-claim qualifier statements.

BEGIN;

CREATE TABLE claim_evidence (
  claim_id      uuid NOT NULL REFERENCES claim(claim_id),
  capture_id    uuid NOT NULL REFERENCES evidence_capture(capture_id),
  extraction_id uuid REFERENCES extraction(extraction_id),
  role          text NOT NULL REFERENCES vocab_evidence_role(role),
  locator       jsonb,
  excerpt       text,
  weight_note   text,
  PRIMARY KEY (claim_id, capture_id, role)
);

-- §16.5 specifies PRIMARY KEY (claim_id, qualifier_id, COALESCE(value_text, '')).
-- Postgres forbids an expression in a PRIMARY KEY, so the same uniqueness is
-- enforced by a unique index on the expression (a faithful, enforceable
-- equivalent). No table FKs claim_qualifier, so nothing depends on a named PK.
CREATE TABLE claim_qualifier (
  claim_id     uuid NOT NULL REFERENCES claim(claim_id),
  qualifier_id text NOT NULL REFERENCES vocab_predicate(predicate_id),
  value_text   text,
  value_num    numeric,
  value_entity uuid REFERENCES entity(entity_id)
);

CREATE UNIQUE INDEX claim_qualifier_pk
  ON claim_qualifier (claim_id, qualifier_id, COALESCE(value_text, ''));

COMMIT;
