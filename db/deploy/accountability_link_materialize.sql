-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:accountability_link_materialize to pg
-- P28.6 / ADR-099 (materialize-at-scale posture) + ADR-101 (the public surface then
-- reads these rows). The Appendix C.6 L4 `inference.derived_fact` table (a SEPARATE
-- schema so an inference can NEVER be mistaken for an observation, §8.1/SIG-ONTO-002)
-- has existed since P02.1 but has never held a row. P28.6 connects the accountability
-- layer — the P13.x contract/funding/policy/oversight entities (§11.11-11.18) — to the
-- RESOLVED deployments/orgs (P28.1) and WRITES each discovered
-- deployment→vendor→contract→funding→policy→oversight link as a durable, append-only
-- L4 `derived_fact` row (`inference.accountability`), honoring every invariant §3.1
-- demands:
--
-- * **Labelled inference, never an observation (SIG-ONTO-002 / SIG-RECON-047).** The
--   link lands in the L4 `inference.*` namespace, carrying its `derivation_rule`,
--   `rule_version`, `input_claim_ids`, and `confidence`. This IS the procured≠deployed
--   two-layer guard at the storage layer: a contract/procurement claim yields a
--   derived accountability link, never a deployment observation.
-- * **Every link cites its establishing claims (§3.1).** `input_claim_ids` is NOT NULL
--   on `derived_fact` by construction — a link always resolves to real backing claims.
-- * **Append-only + idempotent (ADR-005 / ADR-099).** Exactly as
--   `resolution_materialize`/`relationship_materialize`/`contradiction_materialize`/
--   `coverage_materialize` (ADR-099) and `claim_content_digest` (ADR-059): a nullable
--   `input_digest` (a sha256 over the link's reproducible content) plus a partial
--   UNIQUE index so the materializer can `INSERT ... ON CONFLICT DO NOTHING` and a
--   re-run over an unchanged spine inserts each link exactly once (+0).
--
-- Additive & back-compatible (SIG-STORE-042): the column is nullable with no default,
-- so any pre-existing / hand-inserted derived_fact row (input_digest IS NULL) is
-- unaffected and excluded from the partial index. A genuinely CHANGED establishing-claim
-- set yields a new digest and a superseding link row — never an in-place edit.

BEGIN;

ALTER TABLE inference.derived_fact
  ADD COLUMN input_digest text;

-- The idempotency key: one persisted derived link per reproducible content. Partial so
-- pre-existing / hand-inserted rows (digest NULL) never collide.
CREATE UNIQUE INDEX derived_fact_input_digest_key
  ON inference.derived_fact (input_digest) WHERE input_digest IS NOT NULL;

COMMIT;
