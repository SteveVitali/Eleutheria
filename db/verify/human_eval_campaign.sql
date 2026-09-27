-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:human_eval_campaign on pg

BEGIN;

-- Tables exist with the expected shape (empty selects exercise columns).
SELECT campaign_id, purpose, protocol_digest, frame_snapshot, ruleset_digest,
       seed, design, created_by, created_at
  FROM human_eval_campaign WHERE false;
SELECT campaign_id, manifest_digest, membership_digest, sample_count,
       denominators, created_by, created_at
  FROM human_eval_manifest WHERE false;
SELECT campaign_id, sample_id, pair_id, left_ref, right_ref, packet_digest,
       partition, estimand, stratum_id, dependency_group_id,
       source_lineage_ids, selection_probability, weight, draw_order,
       reference_basis, created_at
  FROM human_eval_sample WHERE false;
SELECT campaign_id, sample_id, packet_digest, payload, created_at
  FROM human_eval_packet WHERE false;
SELECT campaign_id, sample_id, reviewer_id, pass_no, assigned_by, created_at
  FROM human_eval_assignment WHERE false;
SELECT attestation_id, campaign_id, reviewer_id, kind, detail, recorded_by,
       recorded_at
  FROM human_eval_attestation WHERE false;
SELECT label_id, label_seq, campaign_id, sample_id, reviewer_id, label_round,
       label, reason_codes, evidence_refs, rubric_version, packet_digest,
       attestation_id, supersedes_label_id, label_digest, recorded_at
  FROM human_eval_label WHERE false;
SELECT adjudication_id, adjudication_seq, campaign_id, sample_id,
       adjudicator_id, phase, label, reason, evidence_refs,
       supersedes_adjudication_id, recorded_at
  FROM human_eval_adjudication WHERE false;
SELECT release_id, campaign_id, scope, authorized_by, detail, authorized_at
  FROM human_eval_release WHERE false;
SELECT * FROM human_eval_label_released WHERE false;
SELECT * FROM human_eval_adjudication_released WHERE false;
SELECT * FROM human_eval_label_operational WHERE false;
SELECT * FROM human_eval_adjudication_operational WHERE false;

-- RLS is enabled and forced on every eval table.
SELECT 1 / (CASE WHEN count(*) = 9 THEN 1 ELSE 0 END)
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public'
   AND c.relname IN ('human_eval_campaign','human_eval_manifest',
                     'human_eval_sample','human_eval_packet',
                     'human_eval_assignment','human_eval_attestation',
                     'human_eval_label','human_eval_adjudication',
                     'human_eval_release')
   AND c.relrowsecurity AND c.relforcerowsecurity;

-- sig_eval_admin: prep tables SELECT+INSERT, released views SELECT, and NO
-- access to the base label/adjudication/release tables (sealed).
SELECT 1 / (CASE WHEN has_table_privilege('sig_eval_admin','human_eval_campaign','INSERT')
                  AND has_table_privilege('sig_eval_admin','human_eval_campaign','SELECT')
                  AND has_table_privilege('sig_eval_admin','human_eval_sample','INSERT')
                  AND has_table_privilege('sig_eval_admin','human_eval_sample','SELECT')
                  AND has_table_privilege('sig_eval_admin','human_eval_packet','INSERT')
                  AND has_table_privilege('sig_eval_admin','human_eval_packet','SELECT')
                  AND has_table_privilege('sig_eval_admin','human_eval_assignment','INSERT')
                  AND has_table_privilege('sig_eval_admin','human_eval_assignment','SELECT')
                  AND has_table_privilege('sig_eval_admin','human_eval_attestation','INSERT')
                  AND has_table_privilege('sig_eval_admin','human_eval_attestation','SELECT')
                  AND has_table_privilege('sig_eval_admin','human_eval_manifest','INSERT')
                  AND has_table_privilege('sig_eval_admin','human_eval_manifest','SELECT')
                  AND has_table_privilege('sig_eval_admin','human_eval_label_released','SELECT')
                  AND has_table_privilege('sig_eval_admin','human_eval_adjudication_released','SELECT')
                  AND NOT has_table_privilege('sig_eval_admin','human_eval_label','SELECT')
                  AND NOT has_table_privilege('sig_eval_admin','human_eval_adjudication','SELECT')
                  AND NOT has_table_privilege('sig_eval_admin','human_eval_release','SELECT')
                  AND NOT has_table_privilege('sig_eval_admin','human_eval_sample','UPDATE')
                  AND NOT has_table_privilege('sig_eval_admin','human_eval_label','INSERT')
                 THEN 1 ELSE 0 END);

-- sig_eval_reviewer: scoped label/attestation writes + the blinded read
-- surface; NO sample internals, adjudications, releases or campaign design.
SELECT 1 / (CASE WHEN has_table_privilege('sig_eval_reviewer','human_eval_label','INSERT')
                  AND has_table_privilege('sig_eval_reviewer','human_eval_label','SELECT')
                  AND has_table_privilege('sig_eval_reviewer','human_eval_attestation','INSERT')
                  AND has_table_privilege('sig_eval_reviewer','human_eval_attestation','SELECT')
                  AND has_table_privilege('sig_eval_reviewer','human_eval_assignment','SELECT')
                  AND has_table_privilege('sig_eval_reviewer','human_eval_packet','SELECT')
                  AND NOT has_table_privilege('sig_eval_reviewer','human_eval_sample','SELECT')
                  AND NOT has_table_privilege('sig_eval_reviewer','human_eval_adjudication','SELECT')
                  AND NOT has_table_privilege('sig_eval_reviewer','human_eval_release','SELECT')
                  AND NOT has_table_privilege('sig_eval_reviewer','human_eval_campaign','SELECT')
                  AND NOT has_table_privilege('sig_eval_reviewer','human_eval_label','UPDATE')
                  AND NOT has_table_privilege('sig_eval_reviewer','human_eval_label','DELETE')
                 THEN 1 ELSE 0 END);

-- sig_eval_custodian: reads all, writes the sealing decisions; cannot mint a
-- human label.
SELECT 1 / (CASE WHEN has_table_privilege('sig_eval_custodian','human_eval_label','SELECT')
                  AND has_table_privilege('sig_eval_custodian','human_eval_adjudication','INSERT')
                  AND has_table_privilege('sig_eval_custodian','human_eval_release','INSERT')
                  AND has_table_privilege('sig_eval_custodian','human_eval_sample','SELECT')
                  AND has_table_privilege('sig_eval_custodian','human_eval_campaign','SELECT')
                  AND NOT has_table_privilege('sig_eval_custodian','human_eval_label','INSERT')
                  AND NOT has_table_privilege('sig_eval_custodian','human_eval_label','UPDATE')
                 THEN 1 ELSE 0 END);

-- sig_materialize + read/export/ingest roles: NO base-table access; only the
-- operational released views (empty until an authorized operational release).
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize','human_eval_label_operational','SELECT')
                  AND has_table_privilege('sig_materialize','human_eval_adjudication_operational','SELECT')
                  AND NOT has_table_privilege('sig_materialize','human_eval_label','SELECT')
                  AND NOT has_table_privilege('sig_materialize','human_eval_label','INSERT')
                  AND NOT has_table_privilege('sig_materialize','human_eval_sample','SELECT')
                  AND NOT has_table_privilege('sig_materialize','human_eval_packet','SELECT')
                  AND NOT has_table_privilege('sig_materialize','human_eval_adjudication','SELECT')
                  AND NOT has_table_privilege('sig_materialize','human_eval_release','SELECT')
                  AND NOT has_table_privilege('sig_materialize','human_eval_campaign','SELECT')
                  AND NOT has_table_privilege('sig_read_public','human_eval_label','SELECT')
                  AND NOT has_table_privilege('sig_read_restricted','human_eval_label','SELECT')
                  AND NOT has_table_privilege('sig_read_sealed','human_eval_label','SELECT')
                  AND NOT has_table_privilege('sig_export','human_eval_label','SELECT')
                  AND NOT has_table_privilege('sig_ingest','human_eval_label','INSERT')
                  AND NOT has_table_privilege('sig_read_public','human_eval_label_operational','SELECT')
                 THEN 1 ELSE 0 END);

ROLLBACK;
