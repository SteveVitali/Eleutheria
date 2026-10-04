-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:read_surface_grants from pg
--
-- Reworked under @r11-read-allowlist (P34.25, ADR-196): the deploy above is a
-- no-op, so its revert is a no-op. Reverting further — past the tag — runs
-- read_surface_grants@r11-read-allowlist.sql, which revokes the P24.1 grants
-- as before.

BEGIN;

SELECT 1;

COMMIT;
