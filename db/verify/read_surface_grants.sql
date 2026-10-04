-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:read_surface_grants on pg
--
-- Reworked under @r11-read-allowlist (P34.25, ADR-196 — a verify asserts what
-- holds of its own change in the FINAL posture): the original script also
-- asserted `sig_read_public` USAGE on the inference schema — true when this
-- change landed under the P24.1 blanket grant, deliberately false after
-- public_read_allowlist narrowed the public role to the §37 surface (the L4
-- schema is off it). The assertion that survives is the grant this change
-- exists to prove — the hosted API's missing-grant fix: the public read role
-- can SELECT entity_identifier (it is on the P34.25 allow-list).

BEGIN;

SELECT 1 / (CASE WHEN has_table_privilege('sig_read_public', 'entity_identifier', 'SELECT')
                 THEN 1 ELSE 0 END);

ROLLBACK;
