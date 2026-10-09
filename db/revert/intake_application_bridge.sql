-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:intake_application_bridge from pg
--
-- Reworked under @r11-verify-membership (P34.46, D-P34.24b-1): the reworked
-- deploy only grants the deploying login membership in sig_intake_bridge,
-- so its revert revokes exactly that (guarded, as in intake_storage).
-- Reverting further — past the tag — runs the tagged revert, which revokes
-- the bridge's narrow grants and drops the role as before.

BEGIN;

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sig_intake_bridge') THEN
    EXECUTE format('REVOKE sig_intake_bridge FROM %I', current_user);
  END IF;
END $$;

COMMIT;
