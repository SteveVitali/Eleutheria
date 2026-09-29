-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:research_task_trigger on pg

BEGIN;

-- Both trigger-citation columns exist.
SELECT trigger_kind, trigger_ref FROM research_task WHERE false;

ROLLBACK;
