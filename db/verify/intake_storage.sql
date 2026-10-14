-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:intake_storage on pg
--
-- Reworked under @r11-verify-membership (P34.46, D-P34.24b-1; ADR-196 — a
-- verify asserts what holds of its own change in the final posture): the
-- reworked deploy installs the deployer memberships, so this verify asserts
-- them. The intake-schema functional probes stay in the tagged copy
-- verify/intake_storage@r11-verify-membership.sql, which runs unchanged for
-- the tagged instance (and now passes on a non-superuser deploy login —
-- the grant is what makes its SET ROLE legal).

BEGIN;

SELECT 1 / (CASE WHEN pg_has_role(current_user, 'sig_intake_receiver', 'MEMBER')
                 THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN pg_has_role(current_user, 'sig_intake_reviewer', 'MEMBER')
                 THEN 1 ELSE 0 END);

ROLLBACK;
