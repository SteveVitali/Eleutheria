-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:claim_payload_version from pg

BEGIN;

DELETE FROM append_only_guard
 WHERE table_name = 'claim'
   AND column_name = 'payload_version';

ALTER TABLE claim
  DROP COLUMN IF EXISTS payload_version;

COMMIT;
