-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:materialize_role from pg
-- Removes the P30.2 read/materialize role and every privilege it holds. Rows the role
-- already materialized stay (append-only history is never deleted by a revert).

BEGIN;

REVOKE INSERT ON resolution, relationship, contradiction, coverage_record, research_task
  FROM sig_materialize;
REVOKE INSERT ON inference.derived_fact FROM sig_materialize;
REVOKE INSERT ON vocab_resolution_strategy, vocab_rationale, vocab_confidence
  FROM sig_materialize;
REVOKE sig_read_public FROM sig_materialize;
DROP OWNED BY sig_materialize;
DROP ROLE IF EXISTS sig_materialize;

COMMIT;
