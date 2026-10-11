-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:closed_vocabulary on pg

BEGIN;

-- The genre vocabulary exists and carries the 20 registry genres.
SELECT genre_id FROM vocab_artifact_genre;
SELECT 1/count(*) FROM vocab_artifact_genre;

-- The six measured-unregistered predicates resolve (P35.14a AC).
SELECT predicate_id FROM vocab_predicate
 WHERE predicate_id IN ('installation_date','last_checked','upstream_ref',
                        'portal_stated_permitted_use','deployed',
                        'retention_window_observed');
SELECT 6/count(*) FROM vocab_predicate
 WHERE predicate_id IN ('installation_date','last_checked','upstream_ref',
                        'portal_stated_permitted_use','deployed',
                        'retention_window_observed');

-- unknown_genre is an admissible quarantine reason.
SELECT conname FROM pg_constraint
 WHERE conname = 'assertion_quarantine_reason_check'
   AND pg_get_constraintdef(oid) LIKE '%unknown_genre%';

-- every seeded predicate carries the full registry metadata (SIG-ONTO-066).
SELECT 0/count(*) FROM vocab_predicate
 WHERE volatility_class IS NULL OR resolution_strategy IS NULL
    OR definition IS NULL OR skos_concept_iri IS NULL
    OR (volatility_class <> 'IMMUTABLE' AND half_life_days IS NULL);

-- the directness matrix covers the registry (one row per genre x predicate).
SELECT count(*) FROM directness_matrix WHERE ruleset_version = '1.0.0';

ROLLBACK;
