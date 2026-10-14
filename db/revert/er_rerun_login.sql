-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:er_rerun_login from pg
--
-- P34.45: remove the write-capable re-run login. The membership is revoked
-- first (DROP ROLE refuses a member); `sig_materialize` itself is Round-6's
-- role and is untouched. Re-running the leg's credential teardown stays the
-- leg's job — this revert removes the catalog row, not a Secret Manager
-- version.

BEGIN;

SET LOCAL lock_timeout = '5s';

REVOKE sig_materialize FROM sig_materialize_login;
DROP ROLE IF EXISTS sig_materialize_login;

COMMIT;
