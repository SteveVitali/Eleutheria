-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:relationship_materialize to pg
-- P28.2 / ADR-099 (materialize-at-scale posture) + ADR-101 (the public surface then
-- reads these rows). The Appendix C.5 `relationship` table (the §12 edge catalog) has
-- existed since P02.1 but has never held a row — the launch posture computed sharing
-- edges on read (ADR-092, `exports.shaping.shape_sharing_edges`). P28.2 runs the
-- §29.3 sharing-edge reconciler (P08.2, `reconcile.sharing.reconcile_sharing`) over the
-- real spine and WRITES the reconciled directed access edges as durable `relationship`
-- rows, append-only (ADR-005): an edge is a stored, evidenced fact, never a
-- recompute-in-place and never an UPDATE/DELETE.
--
-- This change adds the idempotency contract the append-only edge materializer needs,
-- exactly as `resolution_materialize` (ADR-099) and `claim_content_digest` (ADR-059)
-- did for their write paths: a nullable `input_digest` (a sha256 over the reconciled
-- edge's reproducible content — endpoints + edge_type + access_kind + direction +
-- valid_from_kind + perspective + the sorted evidence-claim id set) plus a partial
-- UNIQUE index, so the materializer can `INSERT ... ON CONFLICT DO NOTHING` and a
-- re-run over unchanged claims inserts each edge exactly once (+0).
--
-- Additive & back-compatible (SIG-STORE-042): the column is nullable with no default,
-- so any pre-existing / hand-inserted relationship row (input_digest IS NULL) is
-- unaffected and excluded from the partial index. A genuinely CHANGED evidence set
-- yields a new digest and a superseding edge row — never an in-place edit.

BEGIN;

ALTER TABLE relationship
  ADD COLUMN input_digest text;

-- The idempotency key: one persisted relationship edge per reproducible reconciler
-- input. Partial so pre-existing / hand-inserted rows (digest NULL) never collide.
CREATE UNIQUE INDEX relationship_input_digest_key
  ON relationship (input_digest) WHERE input_digest IS NOT NULL;

COMMIT;
