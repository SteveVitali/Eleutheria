-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:declared_lineage from pg
-- P35.25 (SIG-CONF-014): drop the lineage mirror, the per-claim lineage record,
-- the current-declaration view, the indexes and the immutability triggers.
-- Reverting NEVER removes claim rows or recorded decisions — append-only
-- stands regardless (P1-P3); this only removes the metadata this change added.

BEGIN;

DROP VIEW IF EXISTS source_lineage_current;
DROP TABLE IF EXISTS claim_lineage;
DROP TABLE IF EXISTS source_lineage;
DROP FUNCTION IF EXISTS claim_lineage_immutable;
DROP FUNCTION IF EXISTS source_lineage_immutable;

-- Restore the pre-change quarantine-reason vocabulary.
ALTER TABLE assertion_quarantine
  DROP CONSTRAINT IF EXISTS assertion_quarantine_reason_check;
ALTER TABLE assertion_quarantine
  ADD CONSTRAINT assertion_quarantine_reason_check
  CHECK (reason IN ('bad_digest','unknown_predicate','unknown_genre',
                    'unknown_subject_scheme','unknown_object_type',
                    'unknown_value_kind','missing_capture_binding',
                    'unsupported_locator','extractor_failure',
                    'version_mismatch','missing_required_field',
                    'unknown_qualifier'));

COMMIT;
