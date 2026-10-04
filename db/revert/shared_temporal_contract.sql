-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:shared_temporal_contract from pg
--
-- Reworked under @r11-sqitch-hygiene (P34.24a, ADR-196): the deploy above is a
-- no-op, so its revert is a no-op. Reverting further — past the tag — runs
-- shared_temporal_contract@r11-sqitch-hygiene.sql, which drops the P32.4
-- objects as before.

BEGIN;

SELECT 1;

COMMIT;
