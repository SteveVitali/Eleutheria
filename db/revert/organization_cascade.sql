-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:organization_cascade from pg

BEGIN;

REVOKE INSERT ON organization_run, organization_match, organization_execution
  FROM sig_materialize;
REVOKE SELECT ON organization_run, organization_match, organization_execution
  FROM sig_export, sig_materialize;
DROP TABLE IF EXISTS organization_execution;
DROP TABLE IF EXISTS organization_match;
DROP TABLE IF EXISTS organization_run;

COMMIT;
