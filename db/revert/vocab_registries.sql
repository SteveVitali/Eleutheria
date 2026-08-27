-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:vocab_registries from pg
BEGIN;
DROP TABLE IF EXISTS directness_matrix;
DROP TABLE IF EXISTS vocab_predicate;
DROP TABLE IF EXISTS vocab_artifact_integrity;
DROP TABLE IF EXISTS vocab_claim_directness;
DROP TABLE IF EXISTS vocab_source_reliability;
DROP TABLE IF EXISTS vocab_normalization;
DROP TABLE IF EXISTS vocab_resolution_strategy;
DROP TABLE IF EXISTS vocab_rationale;
DROP TABLE IF EXISTS vocab_confidence;
DROP TABLE IF EXISTS vocab_evidence_role;
DROP TABLE IF EXISTS vocab_object_type;
DROP TABLE IF EXISTS vocab_entity_type;
COMMIT;
