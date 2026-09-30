-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:materialize_role on pg

BEGIN;

-- The role exists, cannot log in, cannot bypass RLS, is not a superuser.
SELECT 1 / (CASE WHEN EXISTS (
  SELECT 1 FROM pg_roles WHERE rolname = 'sig_materialize'
     AND NOT rolcanlogin AND NOT rolbypassrls AND NOT rolsuper) THEN 1 ELSE 0 END);

-- READ via the public read role (tier-0 RLS ceiling binds).
SELECT 1 / (CASE WHEN pg_has_role('sig_materialize', 'sig_read_public', 'USAGE')
                 THEN 1 ELSE 0 END);

-- WRITE = INSERT on a materialized table …
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'resolution', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'inference.derived_fact', 'INSERT')
                 THEN 1 ELSE 0 END);

-- … and never UPDATE/DELETE, never a write on the claim spine.
SELECT 1 / (CASE WHEN NOT has_table_privilege('sig_materialize', 'resolution', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'resolution', 'DELETE')
                  AND NOT has_table_privilege('sig_materialize', 'claim', 'INSERT')
                  AND NOT has_table_privilege('sig_materialize', 'claim', 'UPDATE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
