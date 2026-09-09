-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:review_queue on pg

BEGIN;

-- Both tables exist with their key columns.
SELECT item_id, kind, summary, confidence, overall_weight, model_id, prompt_version, payload, created_at
  FROM review_item WHERE false;
SELECT decision_id, item_id, decision, reviewer, model_id, prompt_version, rationale, decided_at
  FROM review_decision WHERE false;

-- decided_at defaults to the DB clock (not caller-supplied).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_name = 'review_decision' AND column_name = 'decided_at'
       AND column_default LIKE '%clock_timestamp%'
  ) THEN 1 ELSE 0 END);

-- the decision-history index exists.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'public' AND indexname = 'review_decision_item_idx'
  ) THEN 1 ELSE 0 END);

ROLLBACK;
