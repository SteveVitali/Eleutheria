-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:entity_typing_mobility_check from pg
--
-- P35.14b. DDL rollback only: the NOT VALID constraint changed no data, so
-- dropping it is the honest inverse. `entity_type_decision` rows that already
-- landed are append-only history — a wrong decision is corrected by a
-- superseding decision, and reverting the schema drops the log the same way a
-- fresh spine never had it (the ticket's rollback clause: corruption-only
-- fallback is the PITR-clone pattern, never an in-place restore).

BEGIN;

SET LOCAL lock_timeout = '5s';

-- The reason CHECK returns to its closed_vocabulary (P35.14a) shape.
ALTER TABLE assertion_quarantine DROP CONSTRAINT assertion_quarantine_reason_check;
ALTER TABLE assertion_quarantine ADD CONSTRAINT assertion_quarantine_reason_check
  CHECK (reason IN ('bad_digest','unknown_predicate','unknown_genre',
                    'unknown_object_type','unknown_value_kind',
                    'missing_capture_binding','unsupported_locator',
                    'extractor_failure','version_mismatch',
                    'missing_required_field','unknown_qualifier'));

ALTER TABLE physical_asset DROP CONSTRAINT physical_asset_mobility_vocab;

DELETE FROM spine_watermark WHERE facet = 'entity_type_decision';
DROP TRIGGER spine_watermark_truncate ON entity_type_decision;
DROP TRIGGER spine_watermark_update ON entity_type_decision;
DROP TRIGGER spine_watermark_insert ON entity_type_decision;
DROP VIEW entity_current_type;
DROP TRIGGER entity_type_decision_immutable ON entity_type_decision;
DROP FUNCTION entity_type_decision_immutable();
DROP TABLE entity_type_decision;

COMMIT;
