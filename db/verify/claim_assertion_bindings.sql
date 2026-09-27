-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:claim_assertion_bindings on pg

BEGIN;

SELECT extraction_config_digest, extractor_version, binding_status, bound_at
  FROM claim_evidence WHERE false;
SELECT assertion_map_id, assertion_map_basis FROM claim WHERE false;
SELECT value_bool, unit, jurisdiction, valid_from, valid_to, extraction_id, rank
  FROM claim_qualifier WHERE false;
SELECT capture_classification FROM evidence_capture WHERE false;
SELECT quarantine_id, run_id, received_at, reason, connector_name, source_id,
       subject_ref, predicate_id, payload, payload_digest
  FROM assertion_quarantine WHERE false;
SELECT ocfl_object_id, ocfl_version FROM ingest_run_capture WHERE false;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'claim_evidence_binding_status_ck') THEN
    RAISE EXCEPTION 'claim_evidence binding_status CHECK missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'evidence_capture_classification_ck') THEN
    RAISE EXCEPTION 'evidence_capture classification CHECK missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'claim_qualifier_pk') THEN
    RAISE EXCEPTION 'claim_qualifier_pk missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'assertion_quarantine_immutable') THEN
    RAISE EXCEPTION 'assertion_quarantine immutability trigger missing';
  END IF;
END $$;

ROLLBACK;
