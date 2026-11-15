-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:research_task_predicates from pg

BEGIN;

REVOKE UPDATE (status, disposition, disposition_reason)
  ON research_task FROM sig_materialize;

ALTER TABLE research_task
  DROP COLUMN IF EXISTS predicate_ids,
  DROP COLUMN IF EXISTS disposition_reason;

COMMIT;
