-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:resolution_materialize to pg
-- P28.1 / ADR-099: materialize entity resolution at scale. The §16.4 resolution
-- table (a stored DECISION record, SIG-STORE-014) has existed since P02.1 but has
-- never held a row — the launch posture computed the resolution envelope on read
-- (ADR-092). P28.1 runs the §28 resolver over the real spine and WRITES the
-- envelopes as durable rows, append-only (ADR-005): a resolution is a stored
-- decision, never a recompute-in-place and never an UPDATE/DELETE.
--
-- This change adds the idempotency contract the append-only materializer needs,
-- exactly as `claim_content_digest` (ADR-059) did for the connector write path: a
-- nullable `input_digest` (the resolver's SIG-RECON-020 reproducibility digest over
-- (claims + ruleset_version + resolver_version + as_of pair)) plus a partial UNIQUE
-- index, so the materializer can `INSERT ... ON CONFLICT DO NOTHING` and a re-run
-- over unchanged inputs inserts each envelope exactly once (+0).
--
-- Additive & back-compatible (SIG-STORE-042): the column is nullable with no
-- default, so any pre-existing resolution row (input_digest IS NULL) is unaffected
-- and excluded from the partial index. A genuinely CHANGED input yields a new
-- digest and a superseding decision (close the prior sys_period first, §16.4) —
-- never an in-place edit.

BEGIN;

ALTER TABLE resolution
  ADD COLUMN input_digest text;

-- The idempotency key: one persisted resolution per reproducible resolver input.
-- Partial so pre-existing / hand-inserted rows (digest NULL) never collide.
CREATE UNIQUE INDEX resolution_input_digest_key
  ON resolution (input_digest) WHERE input_digest IS NOT NULL;

COMMIT;
