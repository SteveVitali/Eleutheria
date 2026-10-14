-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:intake_application_bridge on pg
--
-- Reworked under @r11-verify-membership (P34.46, D-P34.24b-1; ADR-196): the
-- reworked deploy installs the deployer membership, so this verify asserts
-- it. The bridge's functional probes stay in the tagged copy
-- verify/intake_application_bridge@r11-verify-membership.sql, which runs
-- unchanged for the tagged instance (now legal on a non-superuser deploy
-- login — the grant is what makes its SET ROLE work).

BEGIN;

SELECT 1 / (CASE WHEN pg_has_role(current_user, 'sig_intake_bridge', 'MEMBER')
                 THEN 1 ELSE 0 END);

ROLLBACK;
