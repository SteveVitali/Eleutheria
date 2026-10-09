-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:intake_application_bridge to pg
--
-- Reworked under @r11-verify-membership (P34.46, D-P34.24b-1; ADR-196): this
-- change's own verify SET ROLEs sig_intake_bridge — refused for a deploy
-- login holding no membership (the same class the P34.24b rehearsal
-- measured on intake_storage). The tagged copy
-- intake_application_bridge@r11-verify-membership.sql carries the full
-- original DDL plus this same grant; for a spine that already deployed the
-- tagged instance, this reworked deploy grants it now. Idempotent.

BEGIN;

DO $$ BEGIN
  EXECUTE format('GRANT sig_intake_bridge TO %I', current_user);
END $$;

COMMIT;
