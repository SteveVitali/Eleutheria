-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:seed_vocab from pg
BEGIN;
DELETE FROM vocab_entity_type;
DELETE FROM vocab_evidence_role;
DELETE FROM vocab_object_type;
DELETE FROM vocab_artifact_integrity;
DELETE FROM vocab_claim_directness;
DELETE FROM vocab_source_reliability;
COMMIT;
