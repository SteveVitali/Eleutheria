-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim_payload_version to pg
-- P35.22 / F-504 (ADR-059's digest mechanism, extended; ADR-211): claim identity moves to
-- the shared `evidence.claim_identity` normalisation — volatile acquisition
-- fields (row position, page/capture URL, capture digest, fetch time, upstream
-- version counters) leave `digest_base`, `value_json` is canonicalised, and the
-- predicate registry's `obs`/`ref` class governs whether the temporal qualifier
-- is in identity. The scheme is sealed by `payload_version` so a future
-- normalisation change is a declared new shape — it mints distinct digests by
-- construction, never silent drift.
--
-- Additive & back-compatible (SIG-STORE-042): the column is nullable with no
-- default — every existing claim keeps its id and carries
-- `payload_version IS NULL` (pre-versioning, honest). The migration NEVER
-- recomputes a stored `content_digest` (CP-1's no-mass-re-mint invariant): only
-- rows minted after this change carry the version marker. The column joins the
-- append-only guard list so it is immutable like every other claim column
-- (§16.3, SIG-STORE-011). No index on the digest base is needed — the existing
-- `claim_content_digest_key` partial unique index is unchanged: the dedup key
-- is still `content_digest`; `payload_version` records which normalisation
-- produced it.

BEGIN;

ALTER TABLE claim
  ADD COLUMN payload_version text;

-- The append-only guard (claim_append_only.sql) covers every claim column
-- except sys_period, populated from the live schema at ITS deploy time — new
-- columns must be registered explicitly so the guard cannot silently widen
-- what is mutable (SIG-STORE-011).
INSERT INTO append_only_guard (table_name, column_name)
VALUES ('claim', 'payload_version')
ON CONFLICT (table_name, column_name) DO NOTHING;

COMMIT;
