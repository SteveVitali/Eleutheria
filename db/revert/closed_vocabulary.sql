-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:closed_vocabulary from pg
--
-- Reworked under @r11-vocab-verify-scope (OPS-SPINE-SCHEMA-DEPLOY, ADR-196):
-- the repair is the *verify* script only — this head-instance revert is a
-- deliberate no-op; the real revert (restore the reason CHECK, drop the
-- genre table, delete unreferenced registry rows) lives in
-- closed_vocabulary@r11-vocab-verify-scope.sql and runs for the tagged
-- instance.

BEGIN;

SELECT 1;

COMMIT;
