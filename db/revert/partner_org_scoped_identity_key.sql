-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:partner_org_scoped_identity_key from pg
-- Nothing to drop: the change only backfilled keys, and entity_identity_key rows are
-- immutable recorded identity decisions (its trigger refuses DELETE, append-only
-- P1-P3). Reverting the code (db.identity_guard.PARTNER_NAME_SCOPED_SCHEME) stops new
-- scoped-name keys; the keys already claimed stay, pointing at their organisations.

BEGIN;

SELECT 1;

COMMIT;
