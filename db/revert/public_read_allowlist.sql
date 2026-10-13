-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:public_read_allowlist from pg
-- Restores the pre-P34.25 grant posture EXACTLY. A fresh `GRANT SELECT ON ALL
-- TABLES` would be WRONG here: it would also grant the post-blanket tables the
-- public role never had (assertion_quarantine, entity_identity_key,
-- ingest_run_capture, recovery_application, the human_eval relations). So the
-- revert enumerates the real pre-change set: every table that existed when
-- read_surface_grants deployed (its ALL TABLES scope) plus each explicit
-- public grant a later change made.

BEGIN;

-- Undo the direct read scope this change declared for sig_materialize.
REVOKE SELECT ON
  resolution, relationship,
  camera_site_run, camera_site_match, camera_site_execution,
  review_campaign, review_campaign_item,
  ingest_run, ingest_run_completion,
  vocab_resolution_strategy, vocab_rationale, vocab_confidence
FROM sig_materialize;
REVOKE SELECT ON inference.derived_fact FROM sig_materialize;
REVOKE USAGE  ON SCHEMA inference FROM sig_materialize;
REVOKE SELECT ON append_only_guard FROM sig_intake_bridge, sig_recovery;

-- The allow-list + column grant this change installed.
REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM sig_read_public;

-- The pre-P34.25 posture: read_surface_grants' ALL TABLES scope (every
-- public/inference table deployed at that point) …
GRANT SELECT ON
  vocab_entity_type, vocab_object_type, vocab_evidence_role, vocab_confidence,
  vocab_rationale, vocab_resolution_strategy, vocab_normalization,
  vocab_source_reliability, vocab_claim_directness, vocab_artifact_integrity,
  vocab_predicate, directness_matrix,
  entity, rights_record, source_registry, ingest_run,
  evidence_artifact, evidence_capture, extraction,
  evidence_blob, evidence_access_log,
  claim, append_only_guard, resolution, claim_evidence, claim_qualifier,
  jurisdiction, organization, entity_identifier, organization_relation,
  person, product, technology, capability, deployment, physical_asset,
  candidate_asset, data_system, contract, funding_instrument, policy,
  legal_instrument, configuration_state, accountability_event,
  legal_proceeding, records_request,
  relationship, entity_role,
  contradiction, coverage_record, research_task,
  review_item, review_decision
TO sig_read_public;
GRANT USAGE  ON SCHEMA inference TO sig_read_public;
GRANT SELECT ON inference.derived_fact, inference.derived_geometry TO sig_read_public;

-- … plus the explicit public grants the later changes made.
GRANT SELECT ON rights_decision TO sig_read_public;
GRANT SELECT ON camera_site_run, camera_site_match TO sig_read_public;
GRANT SELECT ON camera_site_execution TO sig_read_public;
GRANT SELECT ON ingest_run_completion TO sig_read_public;
GRANT SELECT ON review_campaign, review_campaign_item TO sig_read_public;
GRANT SELECT ON spine_watermark TO sig_read_public;
GRANT SELECT (disposition_id, disposition_seq, target_kind, target_id,
              disposition, reason_category, authority, decided_at,
              evidence_claim_id, supersedes, policy_version)
  ON publication_disposition TO sig_read_public;

COMMIT;
