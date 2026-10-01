-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:resolution_supersede on pg

BEGIN;

-- The function exists (3 args, SECURITY DEFINER — the privilege checks below pin
-- the exact signature): it runs as its OWNER, so the caller never needs UPDATE
-- on resolution.
SELECT 1 / (CASE WHEN EXISTS (
  SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
   WHERE n.nspname = 'public' AND p.proname = 'close_superseded_resolutions'
     AND p.prosecdef AND p.pronargs = 3
  ) THEN 1 ELSE 0 END);

-- sig_materialize may EXECUTE it; PUBLIC may not (the default grant was revoked).
SELECT 1 / (CASE WHEN has_function_privilege(
    'sig_materialize',
    'close_superseded_resolutions(uuid[], text[], text[])', 'EXECUTE')
                 THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN NOT has_function_privilege(
    'public',
    'close_superseded_resolutions(uuid[], text[], text[])', 'EXECUTE')
                 THEN 1 ELSE 0 END);

-- The least-privilege posture still holds: sig_materialize has no UPDATE on the
-- decision table itself — the closure goes through the definer function only.
SELECT 1 / (CASE WHEN NOT has_table_privilege('sig_materialize', 'resolution', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'resolution', 'DELETE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
