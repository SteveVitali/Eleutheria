-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:research_task_predicates on pg

BEGIN;

-- Both additive columns exist.
SELECT predicate_ids, disposition_reason FROM research_task WHERE false;

-- The column-scoped UPDATE grant to sig_materialize exists.
SELECT 1
  FROM information_schema.role_table_grants
 WHERE grantee = 'sig_materialize'
   AND table_name = 'research_task'
   AND privilege_type = 'UPDATE'
 LIMIT 1;

ROLLBACK;
