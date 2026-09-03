-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:temporal_invariants from pg

BEGIN;

DROP FUNCTION IF EXISTS resolution_as_of(timestamptz, timestamptz);
DROP FUNCTION IF EXISTS claim_as_of(timestamptz, timestamptz);

DELETE FROM append_only_guard
 WHERE table_name = 'claim'
   AND column_name IN ('temporally_unanchored', 'temporally_unanchored_reason');

ALTER TABLE claim
  DROP CONSTRAINT IF EXISTS claim_unanchored_reasoned,
  DROP COLUMN IF EXISTS temporally_unanchored_reason,
  DROP COLUMN IF EXISTS temporally_unanchored;

COMMIT;
