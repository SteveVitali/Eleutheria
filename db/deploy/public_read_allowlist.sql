-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:public_read_allowlist to pg
-- P34.25 (S0 RI-02): the public read role must read ONLY the published §37
-- read surface. P24.1's read_surface_grants gave sig_read_public SELECT ON ALL
-- TABLES in public + inference — so until this change the "public" role could
-- also read person, the domain projections (contract/funding_instrument/
-- legal_proceeding/records_request/…), resolution/relationship internals,
-- extraction, ingest_run, the review queue, the camera-site machinery,
-- append_only_guard, evidence_blob, evidence_access_log, every vocab registry
-- and both inference tables. None of those reach the public API: PgReadStore's
-- entire read set is the allow-list re-granted below (plus the P32.5
-- column-limited publication_disposition tombstone).
--
-- The elevated/internal roles are unaffected except where they INHERITED the
-- widened set through sig_read_public: sig_materialize (ADR-103 reads through
-- public membership) gets the read scope it actually uses granted directly,
-- so narrowing public changes nothing a materializer or the curation queue
-- runs on. sig_export keeps its deploy posture (export reads are a separate
-- surface, out of scope here). RLS is untouched — the tier ceilings still
-- bind on top of every grant below.

BEGIN;

-- 1. Strip every SELECT the blanket (and later per-change) grants left on the
--    public read role — table- and column-level alike.
REVOKE SELECT ON ALL TABLES IN SCHEMA public    FROM sig_read_public;
REVOKE SELECT ON ALL TABLES IN SCHEMA inference FROM sig_read_public;
REVOKE USAGE  ON SCHEMA inference FROM sig_read_public;

-- 2. Re-grant exactly the published §37 read surface — the relations
--    PgReadStore queries and nothing else.
GRANT SELECT ON
  claim, claim_evidence, claim_qualifier,
  entity, entity_identifier, organization,
  evidence_artifact, evidence_capture,
  source_registry, rights_record, rights_decision,
  contradiction, coverage_record, research_task,
  spine_watermark
TO sig_read_public;

-- publication_disposition stays COLUMN-LIMITED (P32.5/SIG-TRUST-006): the
-- tombstone-safe columns only — rationale and decided_by remain elevated.
GRANT SELECT (disposition_id, disposition_seq, target_kind, target_id,
              disposition, reason_category, authority, decided_at,
              evidence_claim_id, supersedes, policy_version)
  ON publication_disposition TO sig_read_public;

-- 3. sig_materialize read the wider set through public membership. Declare the
--    read scope its materializers + the curation review queue actually use:
GRANT SELECT ON
  resolution, relationship,
  camera_site_run, camera_site_match, camera_site_execution,
  review_campaign, review_campaign_item,
  ingest_run, ingest_run_completion,
  vocab_resolution_strategy, vocab_rationale, vocab_confidence
TO sig_materialize;
GRANT USAGE  ON SCHEMA inference TO sig_materialize;
GRANT SELECT ON inference.derived_fact TO sig_materialize;

-- The claim_immutable trigger SELECTs append_only_guard on EVERY claim UPDATE
-- (the guarded-column list is data). The two roles that close a prior belief —
-- UPDATE(sys_period) on claim — carried that read through the revoked
-- inheritance; keep it directly or their belief-close write breaks.
GRANT SELECT ON append_only_guard TO sig_intake_bridge, sig_recovery;

COMMIT;
