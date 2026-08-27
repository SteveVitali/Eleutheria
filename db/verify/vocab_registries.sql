-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:vocab_registries on pg
SELECT entity_type FROM vocab_entity_type WHERE false;
SELECT object_type FROM vocab_object_type WHERE false;
SELECT code FROM vocab_source_reliability WHERE false;
SELECT code FROM vocab_claim_directness WHERE false;
SELECT code FROM vocab_artifact_integrity WHERE false;
SELECT predicate_id FROM vocab_predicate WHERE false;
SELECT predicate_id FROM directness_matrix WHERE false;
