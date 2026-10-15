-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:vocab_enforcement_count on pg

BEGIN;

-- The predicate is registered — the closed sink resolves it instead of
-- quarantining the ATE family's first live emit (P36.6 / P36.12 L0).
SELECT predicate_id FROM vocab_predicate WHERE predicate_id = 'enforcement_count';
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE predicate_id = 'enforcement_count';

-- The seeded row carries the full registry metadata (SIG-ONTO-066):
-- VOLATILE with a non-NULL half-life, the interval_union strategy, the
-- aggregate-only definition and the registry SKOS IRI — never a stub row.
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE predicate_id = 'enforcement_count'
   AND vocab_version = '1.0.0'
   AND value_datatype = 'integer'
   AND cardinality = 'multi'
   AND volatility_class = 'VOLATILE'
   AND half_life_days IS NOT NULL
   AND resolution_strategy = 'interval_union'
   AND definition IS NOT NULL
   AND skos_concept_iri = 'https://ontology.sig-project.org/vocab/predicate/1.0.0/enforcement_count';

-- The directness matrix covers the predicate — one row per registered
-- genre at ruleset_version 1.0.0 (20 rows, camera_registry=D2).
SELECT 1 / (CASE WHEN count(*) = 20 THEN 1 ELSE 0 END) FROM directness_matrix
 WHERE predicate_id = 'enforcement_count' AND ruleset_version = '1.0.0';
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM directness_matrix
 WHERE predicate_id = 'enforcement_count' AND artifact_type = 'camera_registry'
   AND directness = 'D2' AND ruleset_version = '1.0.0';

ROLLBACK;
