-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:subject_rekey from pg
-- P35.24 / ADR-212: drop the pin mirror, the decision log and the helper index.
-- Reverting NEVER removes recorded decisions' claims — those rows are
-- append-only corrections and stand regardless (P1-P3); this only removes
-- the metadata tables + index the change added.

BEGIN;

DROP INDEX IF EXISTS claim_evidence_claim_idx;
DROP TABLE IF EXISTS subject_rekey_decision;
DROP TABLE IF EXISTS subject_key_pin;
DROP FUNCTION IF EXISTS subject_rekey_decision_immutable;
DROP FUNCTION IF EXISTS subject_key_pin_immutable;

COMMIT;
