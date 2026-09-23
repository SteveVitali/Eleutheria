-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:contradiction_materialize to pg
-- P28.3 / ADR-099 (materialize-at-scale posture). The Appendix C.6 `contradiction`
-- table (the first-class, VISIBLE §31 contradiction object — the point of retiring
-- Risk 3) has existed since P02.1 but has never held a row — the launch posture
-- computed contradictions on read (ADR-092, `api.store_pg._compute_on_read`). P28.3
-- runs §29 reconciliation + the §28 resolver over the real (resolved) spine and WRITES
-- each detected contradiction as a durable `contradiction` row, append-only (ADR-005):
-- a contradiction is a stored, addressable finding, kept VISIBLE and never resolved
-- away (§3.1). Resolution is a NEW lifecycle state row (SIG-RECON-021/055), never an
-- UPDATE/DELETE.
--
-- This change adds the idempotency contract the append-only contradiction materializer
-- needs, exactly as `resolution_materialize` / `relationship_materialize` (ADR-099) and
-- `claim_content_digest` (ADR-059) did for their write paths: a nullable `input_digest`
-- (a sha256 over the contradiction's reproducible content — subject + predicate +
-- contradiction_type + the sorted disagreeing claim-id set + lifecycle status +
-- severity) plus a partial UNIQUE index, so the materializer can `INSERT ... ON CONFLICT
-- DO NOTHING` and a re-run over an unchanged spine inserts each contradiction state
-- exactly once (+0). A lifecycle transition (an open finding no longer detected because
-- later evidence resolved it) changes the status component of the digest, so it lands as
-- a NEW superseding row — never an edit of the open one.
--
-- Additive & back-compatible (SIG-STORE-042): the column is nullable with no default, so
-- any pre-existing / hand-inserted contradiction row (input_digest IS NULL) is unaffected
-- and excluded from the partial index.

BEGIN;

ALTER TABLE contradiction
  ADD COLUMN input_digest text;

-- The idempotency key: one persisted contradiction row per reproducible detected state
-- (identity + lifecycle status). Partial so pre-existing / hand-inserted rows (digest
-- NULL) never collide.
CREATE UNIQUE INDEX contradiction_input_digest_key
  ON contradiction (input_digest) WHERE input_digest IS NOT NULL;

COMMIT;
