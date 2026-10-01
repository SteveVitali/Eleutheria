-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:resolution_supersede from pg
-- Drops the supersession function. Resolutions it already closed keep their closed
-- sys_period (decision history is never rewritten by a revert).

BEGIN;

REVOKE EXECUTE ON FUNCTION close_superseded_resolutions(uuid[], text[], text[])
  FROM sig_materialize;
DROP FUNCTION close_superseded_resolutions(uuid[], text[], text[]);

COMMIT;
