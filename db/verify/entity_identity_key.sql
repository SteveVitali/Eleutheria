-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:entity_identity_key on pg

BEGIN;

SELECT scheme, value, entity_id, keyed_at, backfilled FROM entity_identity_key WHERE false;

-- (scheme, value) is the primary key: the uniqueness the guard relies on.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'entity_identity_key'::regclass AND contype = 'p'
       AND pg_get_constraintdef(oid) = 'PRIMARY KEY (scheme, value)'
  ) THEN 1 ELSE 0 END);

-- The entity FK is deferred (the key is claimed before its entity row is inserted).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'entity_identity_key'::regclass AND contype = 'f'
       AND condeferrable AND condeferred
  ) THEN 1 ELSE 0 END);

-- The immutability trigger exists.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid
     WHERE c.relname = 'entity_identity_key' AND t.tgname = 'entity_identity_key_immutable'
       AND NOT t.tgisinternal
  ) THEN 1 ELSE 0 END);

ROLLBACK;
