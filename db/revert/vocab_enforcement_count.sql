-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:vocab_enforcement_count from pg
-- Removes the seeded directness rows and the predicate row only where no
-- live row references it — a row claims already resolve through is recorded
-- registry history (append-only, P1–P3) and stays, exactly the
-- `closed_vocabulary` revert convention.

BEGIN;

DELETE FROM directness_matrix
 WHERE predicate_id = 'enforcement_count' AND ruleset_version = '1.0.0';

DELETE FROM vocab_predicate
 WHERE predicate_id = 'enforcement_count'
   AND NOT EXISTS (SELECT 1 FROM claim WHERE claim.predicate_id = vocab_predicate.predicate_id)
   AND NOT EXISTS (SELECT 1 FROM claim_qualifier WHERE claim_qualifier.qualifier_id = vocab_predicate.predicate_id)
   AND NOT EXISTS (SELECT 1 FROM contradiction WHERE contradiction.predicate_id = vocab_predicate.predicate_id)
   AND NOT EXISTS (SELECT 1 FROM coverage_record WHERE coverage_record.predicate_id = vocab_predicate.predicate_id)
   AND NOT EXISTS (SELECT 1 FROM resolution WHERE resolution.predicate_id = vocab_predicate.predicate_id);

COMMIT;
