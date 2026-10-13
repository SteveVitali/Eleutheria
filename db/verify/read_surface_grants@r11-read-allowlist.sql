-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:read_surface_grants on pg

BEGIN;

-- The read role can now SELECT the table whose missing grant 500'd the hosted API.
SELECT 1 / (CASE WHEN has_table_privilege('sig_read_public', 'entity_identifier', 'SELECT')
                 THEN 1 ELSE 0 END);

-- … and the L4 inference schema is readable by the read role.
SELECT 1 / (CASE WHEN has_schema_privilege('sig_read_public', 'inference', 'USAGE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
