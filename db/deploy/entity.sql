-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:entity to pg
-- §16.1 / SIG-STORE-008: the L2 identity table. Entities hold identity ONLY —
-- entity_id, entity_type, lifecycle bookkeeping, and cached resolver output
-- (merged_into). Every attribute of every entity is a claim, never a column.

BEGIN;

CREATE TABLE entity (
  entity_id    uuid PRIMARY KEY DEFAULT uuidv7(),
  entity_type  text NOT NULL REFERENCES vocab_entity_type(entity_type),
  created_at   timestamptz NOT NULL DEFAULT clock_timestamp(),
  merged_into  uuid REFERENCES entity(entity_id),   -- cached resolver output; the merge is itself a claim
  CHECK (merged_into IS NULL OR merged_into <> entity_id)
);

COMMIT;
