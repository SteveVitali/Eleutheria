-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:audit_login from pg
--
-- P34.43: remove the two least-privilege logins. Memberships and the NEW-16
-- SELECT grants are revoked first (DROP ROLE refuses a privileged role);
-- `sig_recovery` itself is L52's role and is untouched. Re-running the
-- P34.43 leg's credential teardown stays the leg's job — this revert
-- removes the catalog rows, not a Secret Manager version.

BEGIN;

SET LOCAL lock_timeout = '5s';

REVOKE SELECT ON ingest_run_capture FROM sig_audit;
REVOKE SELECT ON entity_identity_key FROM sig_audit;
REVOKE sig_read_public FROM sig_audit;
DROP ROLE IF EXISTS sig_audit;

REVOKE sig_recovery FROM sig_recovery_login;
DROP ROLE IF EXISTS sig_recovery_login;

COMMIT;
