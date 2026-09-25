-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:camera_site_human_decisions on pg
--
-- pg_get_constraintdef's rendering is version-dependent (extra parens, ::text
-- casts), so the checks match on the VALUE SET the constraint must contain —
-- never a byte-exact definition string.

BEGIN;

-- disposition admits exactly the widened vocabulary (all five literals present
-- in ONE check constraint on the column).
SELECT 1 / (CASE WHEN EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%disposition%'
               AND pg_get_constraintdef(oid) LIKE '%auto_write%'
               AND pg_get_constraintdef(oid) LIKE '%proposed%'
               AND pg_get_constraintdef(oid) LIKE '%human_accept%'
               AND pg_get_constraintdef(oid) LIKE '%human_reject%'
               AND pg_get_constraintdef(oid) LIKE '%refused%')
               THEN 1 ELSE 0 END);

-- relation_type admits cannot_link.
SELECT 1 / (CASE WHEN EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%relation_type%'
               AND pg_get_constraintdef(oid) LIKE '%same_as%'
               AND pg_get_constraintdef(oid) LIKE '%cannot_link%')
               THEN 1 ELSE 0 END);

-- sig_materialize reads the human decision history, keeps INSERT, and holds
-- no UPDATE/DELETE anywhere on the decision log.
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'review_decision', 'SELECT')
                  AND has_table_privilege('sig_materialize', 'review_decision', 'INSERT')
                  AND NOT has_table_privilege('sig_materialize', 'review_decision', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'review_decision', 'DELETE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
