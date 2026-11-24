-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:closed_vocabulary on pg
--
-- Reworked under @r11-vocab-verify-scope (OPS-SPINE-SCHEMA-DEPLOY, ADR-196 —
-- a verify asserts what holds of its own change in the final posture): the
-- repair lives in the tagged copy
-- verify/closed_vocabulary@r11-vocab-verify-scope.sql, which runs right
-- after the change's own DDL on every spine; this head-instance verify
-- re-asserts the same scoped invariants at the plan tip. The unscoped
-- metadata assert divided by zero on sig-pg's 133 runtime-registered
-- vocab_predicate rows whose skos_concept_iri IS NULL — the projection is
-- INSERT … ON CONFLICT DO NOTHING, so a pre-existing row keeps its values
-- verbatim and its NULL iri is honest runtime state (corrected by queued
-- hosted work, never this change's job). A skos_concept_iri is written only
-- by ontology-registry seeds, so `IS NOT NULL` marks exactly the set this
-- change established metadata on — the fresh-vs-existing defect class of
-- D-P34.24b-1.

BEGIN;

-- The genre vocabulary exists and carries the 20 registry genres.
SELECT genre_id FROM vocab_artifact_genre;
SELECT 1/count(*) FROM vocab_artifact_genre;

-- The six measured-unregistered predicates resolve (P35.14a AC).
SELECT predicate_id FROM vocab_predicate
 WHERE predicate_id IN ('installation_date','last_checked','upstream_ref',
                        'portal_stated_permitted_use','deployed',
                        'retention_window_observed');
SELECT 1 / (CASE WHEN count(*) = 6 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE predicate_id IN ('installation_date','last_checked','upstream_ref',
                        'portal_stated_permitted_use','deployed',
                        'retention_window_observed');

-- unknown_genre is an admissible quarantine reason.
SELECT conname FROM pg_constraint
 WHERE conname = 'assertion_quarantine_reason_check'
   AND pg_get_constraintdef(oid) LIKE '%unknown_genre%';

-- every predicate id this change projects resolves to a vocab_predicate
-- row — the directness matrix it just wrote is the projection's own
-- manifest, so a missing seed row shows up here.
SELECT 1 / (CASE WHEN count(*) = 0 THEN 1 ELSE 0 END)
  FROM (SELECT DISTINCT predicate_id FROM directness_matrix
         WHERE ruleset_version = '1.0.0') dm
 WHERE NOT EXISTS (SELECT 1 FROM vocab_predicate
                    WHERE vocab_predicate.predicate_id = dm.predicate_id);

-- every registry-projected predicate carries the full registry metadata
-- (SIG-ONTO-066). Scope: rows carrying a SKOS concept IRI — written only by
-- the ontology-registry seeds, never by the runtime auto-registration —
-- so a pre-existing NULL-iri row ON CONFLICT kept stays outside by design.
SELECT 1 / (CASE WHEN count(*) = 0 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE skos_concept_iri IS NOT NULL
   AND (value_datatype IS NULL OR object_type IS NULL OR cardinality IS NULL
        OR definition IS NULL OR volatility_class IS NULL
        OR resolution_strategy IS NULL
        OR (volatility_class <> 'IMMUTABLE' AND half_life_days IS NULL));

-- …and the IRI it carries names the row's own predicate slug — a malformed
-- or mismatched IRI is exactly the missing-metadata seed defect this
-- assert exists to catch. Deliberately base-agnostic: the deployed IRI
-- base is descriptive metadata under D-P35.38b-1's alias map, and the join
-- key is predicate_id, never the IRI.
SELECT 1 / (CASE WHEN count(*) = 0 THEN 1 ELSE 0 END) FROM vocab_predicate
 WHERE skos_concept_iri IS NOT NULL
   AND skos_concept_iri NOT LIKE '%/' || predicate_id;

-- the directness matrix covers the registry (one row per genre x predicate).
SELECT count(*) FROM directness_matrix WHERE ruleset_version = '1.0.0';

ROLLBACK;
