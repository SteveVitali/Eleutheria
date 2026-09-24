-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:camera_site_resolution to pg
-- P30.2b / ADR-105: geospatial camera-site ENTITY resolution. A resolved site is a
-- cluster of observation-level camera records (one source's row each) judged to be the
-- SAME PHYSICAL DEVICE; M = records, N = clusters, dedup ratio = 1 - N/M. §28 value
-- resolution (the `resolution` table) decides which of ONE record's claims stands; this
-- change records which RECORDS are one device — a different decision, kept separate.
--
--   * `camera_site_match` — the append-only same_as decision log (SIG-IDENT-020/025,
--     SIG-RECON-002): one row per recorded candidate pair per ER run, carrying its §14.6
--     tier, its machine-readable match_evidence and the establishing claims. Disposition
--     `auto_write` rows form the resolved-site clusters; `proposed` rows are PROPOSED
--     merges enqueued for human review (review_item) and never cluster until accepted.
--     Idempotent: input_digest UNIQUE, INSERT ... ON CONFLICT DO NOTHING (a re-run over an
--     unchanged spine is +0). Never UPDATEd or DELETEd; a changed spine or ruleset is a
--     NEW run_key with new rows (the prior clustering stays as history).
--   * `camera_site_run` — the run record (SIG-RECON-001): rules/resolver/gold versions,
--     the measured auto-write tiers and the eval summary (kappa, per-tier holdout
--     precision, demotions, cluster-shape alerts, M, N). Written LAST, so it is also the
--     completion marker: readers take the latest COMPLETED run, never a partial one.
--
-- The least-privilege `sig_materialize` role (ADR-103) gains INSERT on both tables and on
-- `review_item` (the proposals it enqueues) — nothing else, and no UPDATE/DELETE anywhere.
-- Additive & back-compatible: new tables + grants only; no existing object is altered.

BEGIN;

CREATE TABLE camera_site_run (
  run_key           text PRIMARY KEY,
  ruleset_version   text NOT NULL,
  resolver_version  text NOT NULL,
  gold_set_version  text,
  auto_write_tiers  smallint[] NOT NULL,
  observation_count integer NOT NULL CHECK (observation_count >= 0),   -- M
  cluster_count     integer NOT NULL CHECK (cluster_count >= 0),       -- N
  summary           jsonb NOT NULL,
  completed_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (cluster_count <= observation_count)                            -- N <= M, always
);

CREATE TABLE camera_site_match (
  match_id         uuid PRIMARY KEY DEFAULT uuidv7(),
  run_key          text NOT NULL,          -- the run (its camera_site_run row lands last)
  left_entity      uuid NOT NULL REFERENCES entity(entity_id),
  right_entity     uuid NOT NULL REFERENCES entity(entity_id),
  relation_type    text NOT NULL DEFAULT 'same_as' CHECK (relation_type = 'same_as'),
  match_tier       smallint NOT NULL CHECK (match_tier BETWEEN 0 AND 5),
  tier_label       text NOT NULL,
  disposition      text NOT NULL CHECK (disposition IN ('auto_write', 'proposed')),
  disposition_reason text,
  match_evidence   jsonb NOT NULL,         -- SIG-IDENT-025: an unexplainable merge is a violation
  evidence_claims  uuid[] NOT NULL,
  ruleset_version  text NOT NULL,
  resolver_version text NOT NULL,
  input_digest     text NOT NULL,
  decided_by       text NOT NULL DEFAULT 'auto',
  decided_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (left_entity < right_entity)       -- one canonical row per unordered pair
);

CREATE UNIQUE INDEX camera_site_match_input_digest_key ON camera_site_match (input_digest);
CREATE INDEX camera_site_match_run_idx ON camera_site_match (run_key, disposition);

-- Read surface (the export + API read the resolved-site clusters; tier-0 ceiling unaffected:
-- these tables hold decisions over tier-0 subjects and no claim values).
GRANT SELECT ON camera_site_run, camera_site_match TO sig_read_public, sig_export;

-- The materializer writes decisions, the run record, and the proposals it enqueues.
GRANT INSERT ON camera_site_run, camera_site_match, review_item TO sig_materialize;
GRANT SELECT ON review_item TO sig_materialize;

COMMIT;
