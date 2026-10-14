-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:intake_storage from pg
--
-- Reworked under @r11-verify-membership (P34.46, D-P34.24b-1): the reworked
-- deploy only grants the deploying login membership in the two intake
-- roles, so its revert revokes exactly that (guarded — reverting past the
-- tagged instance drops the roles entirely, and REVOKE of a missing role's
-- membership must not be attempted). Reverting further — past the tag —
-- runs intake_storage@r11-verify-membership.sql's revert, which drops the
-- schema and both roles as before.

BEGIN;

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sig_intake_receiver') THEN
    EXECUTE format('REVOKE sig_intake_receiver FROM %I', current_user);
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sig_intake_reviewer') THEN
    EXECUTE format('REVOKE sig_intake_reviewer FROM %I', current_user);
  END IF;
END $$;

COMMIT;
