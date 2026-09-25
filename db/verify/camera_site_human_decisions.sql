-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:camera_site_human_decisions on pg

BEGIN;

-- The widened vocabularies exist and carry exactly the new value sets.
SELECT 1 / (CASE WHEN EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
               AND pg_get_constraintdef(oid) =
                   'CHECK (disposition = ANY (ARRAY[''auto_write''::text, ''proposed''::text, ''human_accept''::text, ''human_reject''::text, ''refused''::text]))')
               THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
               AND pg_get_constraintdef(oid) =
                   'CHECK (relation_type = ANY (ARRAY[''same_as''::text, ''cannot_link''::text]))')
               THEN 1 ELSE 0 END);

-- sig_materialize reads the human decision history (and keeps INSERT, never
-- UPDATE/DELETE).
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'review_decision', 'SELECT')
                  AND has_table_privilege('sig_materialize', 'review_decision', 'INSERT')
                  AND NOT has_table_privilege('sig_materialize', 'review_decision', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'review_decision', 'DELETE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
