-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:vocab_geometry_defect on pg

BEGIN;

-- The predicate is registered — the closed sink resolves it instead of
-- quarantining the first defect marking (P35.16 / F-322).
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE predicate_id = 'geometry_defect';

-- The seeded row carries the full registry metadata (SIG-ONTO-066):
-- IMMUTABLE with a NULL half-life, the never_resolve strategy, the
-- defect-marking definition and the registry SKOS IRI — never a stub row.
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE predicate_id = 'geometry_defect'
   AND vocab_version = '1.0.0'
   AND value_datatype = 'string'
   AND cardinality = 'multi'
   AND volatility_class = 'IMMUTABLE'
   AND half_life_days IS NULL
   AND resolution_strategy = 'never_resolve'
   AND definition IS NOT NULL
   AND skos_concept_iri = 'https://ontology.sig-project.org/vocab/predicate/1.0.0/geometry_defect';

-- The directness matrix covers the predicate — one row per registered
-- genre at ruleset_version 1.0.0 (20 rows, camera_registry=D4,
-- connector_run=D3).
SELECT 1 / (CASE WHEN count(*) = 20 THEN 1 ELSE 0 END) FROM directness_matrix
 WHERE predicate_id = 'geometry_defect' AND ruleset_version = '1.0.0';
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM directness_matrix
 WHERE predicate_id = 'geometry_defect' AND artifact_type = 'camera_registry'
   AND directness = 'D4' AND ruleset_version = '1.0.0';

ROLLBACK;
