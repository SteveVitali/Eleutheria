-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:vocab_published_by on pg

BEGIN;

-- The predicate is registered — the closed sink resolves it instead of
-- quarantining the first publisher claim (P35.26 / SIG-TRUST-003).
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE predicate_id = 'published_by';

-- The seeded row carries the full registry metadata (SIG-ONTO-066): GLACIAL
-- with a 10y half-life, the max_support strategy, the provenance-only
-- definition and the registry SKOS IRI — never a stub row.
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE predicate_id = 'published_by'
   AND vocab_version = '1.0.0'
   AND value_datatype = 'string'
   AND cardinality = 'single'
   AND volatility_class = 'GLACIAL'
   AND half_life_days = 3652
   AND resolution_strategy = 'max_support'
   AND definition IS NOT NULL
   AND skos_concept_iri = 'https://ontology.sig-project.org/vocab/predicate/1.0.0/published_by';

-- The directness matrix covers the predicate — one row per registered
-- genre at ruleset_version 1.0.0 (20 rows: published-artifact genres D2,
-- connector_run D3, official_statement D3, the rest D6).
SELECT 1 / (CASE WHEN count(*) = 20 THEN 1 ELSE 0 END) FROM directness_matrix
 WHERE predicate_id = 'published_by' AND ruleset_version = '1.0.0';
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM directness_matrix
 WHERE predicate_id = 'published_by' AND artifact_type = 'osm_node_set'
   AND directness = 'D2' AND ruleset_version = '1.0.0';
SELECT 1 / (CASE WHEN count(*) = 1 THEN 1 ELSE 0 END) FROM directness_matrix
 WHERE predicate_id = 'published_by' AND artifact_type = 'connector_run'
   AND directness = 'D3' AND ruleset_version = '1.0.0';

ROLLBACK;
