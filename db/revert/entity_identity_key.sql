-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:entity_identity_key from pg
-- Drops the guard side table only. entity / entity_identifier rows written through the
-- guard stay (they are ordinary identity rows); the writers fall back to
-- check-then-insert only if the code is reverted too.

BEGIN;

DROP TRIGGER IF EXISTS entity_identity_key_immutable ON entity_identity_key;
DROP FUNCTION IF EXISTS entity_identity_key_immutable();
DROP TABLE IF EXISTS entity_identity_key;

COMMIT;
