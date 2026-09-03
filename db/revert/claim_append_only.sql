-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:claim_append_only from pg
BEGIN;
DROP TRIGGER IF EXISTS claim_append_only_trg ON claim;
DROP FUNCTION IF EXISTS claim_append_only();
DROP TABLE IF EXISTS append_only_guard;
COMMIT;
