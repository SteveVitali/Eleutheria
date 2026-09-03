-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:claim_enums on pg
SELECT 'value_kind'::regtype;
SELECT 'claim_rank'::regtype;
SELECT 'review_status'::regtype;
