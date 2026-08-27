-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:claim on pg
SELECT claim_id, subject_id, predicate_id, sys_period, sensitivity_tier, revises_claim FROM claim WHERE false;
