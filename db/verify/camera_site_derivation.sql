-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:camera_site_derivation on pg
--
-- pg_get_constraintdef's rendering is version-dependent, so the checks match
-- on the VALUE SET each constraint must contain — never a byte-exact string.

BEGIN;

-- relation_type admits exactly the v3 link vocabulary.
SELECT 1 / (CASE WHEN EXISTS (
            SELECT 1 FROM pg_constraint
             WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%relation_type%'
               AND pg_get_constraintdef(oid) LIKE '%same_as%'
               AND pg_get_constraintdef(oid) LIKE '%cannot_link%'
               AND pg_get_constraintdef(oid) LIKE '%derived_from%'
               AND pg_get_constraintdef(oid) LIKE '%possible_duplicate%')
               THEN 1 ELSE 0 END);

-- the shared site-id column exists (nullable — only merged edges carry it).
SELECT 1 / (CASE WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'camera_site_match' AND column_name = 'site_id'
               AND is_nullable = 'YES')
               THEN 1 ELSE 0 END);

-- the census table is one row per run, FK'd to the completion marker.
SELECT 1 / (CASE WHEN to_regclass('public.camera_site_census') IS NOT NULL
                  AND EXISTS (
                    SELECT 1 FROM pg_constraint
                     WHERE conrelid = 'camera_site_census'::regclass AND contype = 'f')
                 THEN 1 ELSE 0 END);

-- the demotion log exists with its (run_key, token, tier) natural key.
SELECT 1 / (CASE WHEN to_regclass('public.camera_site_demotion') IS NOT NULL
                  AND EXISTS (
                    SELECT 1 FROM pg_constraint
                     WHERE conrelid = 'camera_site_demotion'::regclass AND contype = 'p')
                 THEN 1 ELSE 0 END);

-- sig_materialize writes census/demotions and reads the prior demotion set;
-- sig_export selects (the public surface stays closed — camera_site_* was
-- delisted by public_read_allowlist); no role holds UPDATE or DELETE.
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'camera_site_census', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'camera_site_demotion', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'camera_site_demotion', 'SELECT')
                  AND has_table_privilege('sig_export', 'camera_site_census', 'SELECT')
                  AND has_table_privilege('sig_export', 'camera_site_demotion', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'camera_site_census', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'camera_site_demotion', 'SELECT')
                  AND NOT has_table_privilege('sig_materialize', 'camera_site_census', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'camera_site_census', 'DELETE')
                  AND NOT has_table_privilege('sig_materialize', 'camera_site_demotion', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'camera_site_demotion', 'DELETE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
