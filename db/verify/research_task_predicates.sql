-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:research_task_predicates on pg

BEGIN;

-- Both additive columns exist.
SELECT predicate_ids, disposition_reason FROM research_task WHERE false;

-- The three event columns are writable by sig_materialize.
SELECT 1 WHERE has_column_privilege(
    'sig_materialize', 'public.research_task', 'status', 'UPDATE');
SELECT 1 WHERE has_column_privilege(
    'sig_materialize', 'public.research_task', 'disposition', 'UPDATE');
SELECT 1 WHERE has_column_privilege(
    'sig_materialize', 'public.research_task', 'disposition_reason', 'UPDATE');

-- Nothing else widened: no other-column UPDATE, no DELETE.
SELECT 1 WHERE NOT has_column_privilege(
    'sig_materialize', 'public.research_task', 'closing_condition', 'UPDATE');
SELECT 1 WHERE NOT has_table_privilege(
    'sig_materialize', 'public.research_task', 'DELETE');

COMMIT;
