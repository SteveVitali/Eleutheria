-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:claim_enums from pg
BEGIN;
DROP TYPE IF EXISTS review_status;
DROP TYPE IF EXISTS claim_rank;
DROP TYPE IF EXISTS value_kind;
COMMIT;
