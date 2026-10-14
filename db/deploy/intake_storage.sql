-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:intake_storage to pg
--
-- Reworked under @r11-verify-membership (P34.46, D-P34.24b-1; ADR-196): this
-- change's own verify — and the later intake verifies — SET ROLE into the
-- NOLOGIN intake roles, which the Cloud SQL `sig` deploy login may not do:
-- it is not a superuser and held no membership, so the P34.24b production-
-- shaped clone rehearsal died at `SET LOCAL ROLE sig_intake_receiver`
-- (verify/intake_storage.sql:80). The tagged copy
-- intake_storage@r11-verify-membership.sql carries the full original DDL
-- plus this same grant, so a fresh deploy has the memberships before its
-- verify runs; for a spine that already deployed the tagged instance, this
-- reworked deploy grants them now. The materialize_role pattern
-- (GRANT <role> TO the deploying login), idempotent: GRANT of a held
-- membership is a no-op.

BEGIN;

DO $$ BEGIN
  EXECUTE format('GRANT sig_intake_receiver TO %I', current_user);
  EXECUTE format('GRANT sig_intake_reviewer TO %I', current_user);
END $$;

COMMIT;
