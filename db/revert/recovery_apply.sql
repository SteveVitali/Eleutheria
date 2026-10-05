-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:recovery_apply from pg
--
-- P32.22 (SIG-TRUST-008, ADR-141): drop the applied-receipt table and the
-- applier role. Canonical writes the apply already committed (correction
-- claims, typed bindings, disposition rows, adjudicator entities, ingest_run
-- rows) are append-only history and are deliberately NOT touched — a revert
-- removes the applier's ability to write more, never the record that it did.

BEGIN;

DROP TABLE IF EXISTS recovery_application;
DROP FUNCTION IF EXISTS recovery_application_immutable();

-- DROP ROLE refuses while the role still holds privileges, so the narrow
-- grant set + the sealed-reader membership are revoked first.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM sig_recovery;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM sig_recovery;
REVOKE sig_read_sealed FROM sig_recovery;
DROP ROLE IF EXISTS sig_recovery;

COMMIT;
