-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:claim_assertion_bindings from pg
-- P32.2: drop the typed-binding columns, the widened qualifier columns, the
-- capture classification, the quarantine surface, and restore the original
-- claim_qualifier uniqueness.

BEGIN;

REVOKE INSERT ON assertion_quarantine FROM sig_ingest;
REVOKE SELECT ON assertion_quarantine FROM sig_read_restricted, sig_read_sealed;
REVOKE SELECT, INSERT ON claim_evidence, claim_qualifier FROM sig_ingest;

DROP TRIGGER IF EXISTS assertion_quarantine_immutable ON assertion_quarantine;
DROP FUNCTION IF EXISTS assertion_quarantine_immutable();
DROP TRIGGER IF EXISTS claim_evidence_immutable ON claim_evidence;
DROP TRIGGER IF EXISTS claim_qualifier_immutable ON claim_qualifier;
DROP FUNCTION IF EXISTS claim_evidence_immutable();
DROP TABLE IF EXISTS assertion_quarantine;

DELETE FROM append_only_guard
 WHERE table_name = 'claim'
   AND column_name IN ('assertion_map_id', 'assertion_map_basis');

ALTER TABLE evidence_capture
  DROP CONSTRAINT IF EXISTS evidence_capture_classification_ck,
  DROP COLUMN IF EXISTS capture_classification;

DROP INDEX IF EXISTS claim_qualifier_pk;
CREATE UNIQUE INDEX claim_qualifier_pk
  ON claim_qualifier (claim_id, qualifier_id, COALESCE(value_text, ''));

ALTER TABLE claim_qualifier
  DROP COLUMN IF EXISTS value_bool,
  DROP COLUMN IF EXISTS unit,
  DROP COLUMN IF EXISTS jurisdiction,
  DROP COLUMN IF EXISTS valid_from,
  DROP COLUMN IF EXISTS valid_to,
  DROP COLUMN IF EXISTS extraction_id,
  DROP COLUMN IF EXISTS rank;

ALTER TABLE claim
  DROP COLUMN IF EXISTS assertion_map_id,
  DROP COLUMN IF EXISTS assertion_map_basis;

ALTER TABLE claim_evidence
  DROP CONSTRAINT IF EXISTS claim_evidence_binding_status_ck,
  DROP COLUMN IF EXISTS extraction_config_digest,
  DROP COLUMN IF EXISTS extractor_version,
  DROP COLUMN IF EXISTS binding_status,
  DROP COLUMN IF EXISTS bound_at;

ALTER TABLE ingest_run_capture
  DROP COLUMN IF EXISTS ocfl_object_id,
  DROP COLUMN IF EXISTS ocfl_version;

COMMIT;
