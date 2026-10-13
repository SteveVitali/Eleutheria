-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:shared_temporal_contract to pg
--
-- Reworked under @r11-sqitch-hygiene (P34.24a, ADR-196): the schema is
-- unchanged — the repair is the *verify* script (D-P32.10a-1). The real DDL
-- lives in shared_temporal_contract@r11-sqitch-hygiene.sql, which a fresh
-- database still runs for the tagged instance; this deploy is a deliberate
-- no-op so an already-deployed database only gains the new change record.

BEGIN;

SELECT 1;

COMMIT;
