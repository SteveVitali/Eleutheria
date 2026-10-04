-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:read_surface_grants to pg
--
-- Reworked under @r11-read-allowlist (P34.25, ADR-196): the grants themselves
-- are unchanged at deploy time — the repair is the *verify* script, whose
-- inference-USAGE assertion stops being true once public_read_allowlist
-- narrows sig_read_public to the published §37 surface. The real GRANTs live
-- in read_surface_grants@r11-read-allowlist.sql, which a fresh database still
-- runs for the tagged instance; this deploy is a deliberate no-op so an
-- already-deployed database only gains the new change record.

BEGIN;

SELECT 1;

COMMIT;
