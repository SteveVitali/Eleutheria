-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:organization_cascade to pg
-- P37.46b (R11-CONF-13 13b, CP-10, ADR-L3-B §4, SIG-CONF-004, SIG-IDENT-020/025):
-- the organisation-identity cascade materialized as a production write path —
-- the organisation analogue of camera_site_resolution (ADR-105).
--
--   * `organization_match` — the append-only match-record log: one row per
--     recorded organisation pair per cascade run, carrying its §14.6 tier, its
--     machine-readable match_evidence and the establishing claims. Tiers 0–1
--     auto-LINK (relation_type 'same_as', disposition 'auto_link'): an exact
--     shared authoritative identifier (tier 0) or an established registry
--     crosswalk (tier 1 — an org_crosswalk_entry entity whose upstream row
--     carries identifiers both sides share). Tier 2 (normalized name + state +
--     class, minus the committed collision exclusion) records 'possibly_same'
--     under disposition 'surfaced' — a name-based match is published as
--     "possibly the same", never auto-linked (SIG-CONF-004 / ADR-L3-B §4: tier
--     2 auto-links only once a registry-generated collision list exists).
--     Idempotent: input_digest UNIQUE, INSERT ... ON CONFLICT DO NOTHING — a
--     re-run over an unchanged spine is +0. Never UPDATEd or DELETEd; a
--     changed spine or ruleset mints a NEW run_key with new rows.
--   * `organization_run` — the run record (SIG-RECON-001): ruleset/resolver
--     versions, the auto-link tiers, M (organisation records read), the
--     link/possibly-same counts and the run summary. Written LAST, so it is
--     also the completion marker.
--   * `organization_execution` — one append-only completion/result reference
--     per EXECUTION (ADR-123): organization_run is keyed by the full input
--     digest so an A→B→A reversion reuses the earlier run row; the execution
--     record is still appended, so readers follow the LATEST completed
--     execution, never the latest distinct run. execution_id is the
--     idempotency key.
--
-- Grants mirror the post-P34.25 posture: sig_materialize SELECTs + INSERTs
-- (INSERT-only — no UPDATE/DELETE anywhere); sig_export SELECTs so a later
-- export surface can publish the links. The tables stay off the public read
-- allowlist surface, like camera_site_*. Additive & back-compatible: new
-- tables + grants only; no existing object is altered.

BEGIN;

CREATE TABLE organization_run (
  run_key              text PRIMARY KEY,
  ruleset_version      text NOT NULL,
  resolver_version     text NOT NULL,
  auto_link_tiers      smallint[] NOT NULL,
  organization_count   integer NOT NULL CHECK (organization_count >= 0),   -- M
  link_count           integer NOT NULL CHECK (link_count >= 0),           -- same_as pairs
  possibly_same_count  integer NOT NULL CHECK (possibly_same_count >= 0),  -- tier-2 surfaced
  summary              jsonb NOT NULL,
  completed_at         timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE organization_run IS
  'P37.46b organisation cascade (R11-CONF-13 13b): one ER run over organisation '
  'entities — tiers 0-1 auto-link, tier 2 surfaced as possibly_same. Written '
  'last as the run-completion marker (SIG-RECON-001).';

CREATE TABLE organization_match (
  match_id           uuid PRIMARY KEY DEFAULT uuidv7(),
  run_key            text NOT NULL,
  left_entity        uuid NOT NULL REFERENCES entity(entity_id),
  right_entity       uuid NOT NULL REFERENCES entity(entity_id),
  relation_type      text NOT NULL CHECK (relation_type IN ('same_as', 'possibly_same')),
  match_tier         smallint NOT NULL CHECK (match_tier BETWEEN 0 AND 2),
  tier_label         text NOT NULL,
  disposition        text NOT NULL CHECK (disposition IN ('auto_link', 'surfaced')),
  disposition_reason text,
  match_evidence     jsonb NOT NULL,         -- SIG-IDENT-025: an unexplainable link is a violation
  evidence_claims    uuid[] NOT NULL,
  ruleset_version    text NOT NULL,
  resolver_version   text NOT NULL,
  input_digest       text NOT NULL,
  decided_by         text NOT NULL DEFAULT 'auto',
  decided_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (left_entity < right_entity)          -- one canonical row per unordered pair
);

COMMENT ON TABLE organization_match IS
  'P37.46b append-only organisation match records (SIG-IDENT-020/025, '
  'SIG-CONF-004): tiers 0-1 same_as auto-links plus the tier-2 possibly_same '
  'surface. INSERT-only — input_digest UNIQUE makes a digest-identical '
  're-run +0.';

CREATE UNIQUE INDEX organization_match_input_digest_key
  ON organization_match (input_digest);
CREATE INDEX organization_match_run_idx
  ON organization_match (run_key, disposition);

CREATE TABLE organization_execution (
  execution_id  uuid PRIMARY KEY,
  run_key       text NOT NULL REFERENCES organization_run(run_key),
  completed_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
  input_count   integer NOT NULL CHECK (input_count >= 0),   -- the execution's M
  summary       jsonb NOT NULL
);

COMMENT ON TABLE organization_execution IS
  'P37.46b / ADR-123: one append-only completion/result reference per cascade '
  'EXECUTION — readers select the run the LATEST COMPLETED EXECUTION produced '
  '(an A→B→A reversion shows a new completion naming A). execution_id is the '
  'idempotency key: retrying the same execution appends +0.';

CREATE INDEX organization_execution_completed_idx
  ON organization_execution (completed_at DESC);

GRANT SELECT ON organization_run, organization_match, organization_execution
  TO sig_export, sig_materialize;
GRANT INSERT ON organization_run, organization_match, organization_execution
  TO sig_materialize;

COMMIT;
