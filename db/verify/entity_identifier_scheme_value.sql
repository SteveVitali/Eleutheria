-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:entity_identifier_scheme_value on pg

BEGIN;

-- The btree exists on entity_identifier (scheme, value) and is VALID.
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1
      FROM pg_index i
      JOIN pg_class ic ON ic.oid = i.indexrelid
      JOIN pg_class t  ON t.oid  = i.indrelid
      JOIN pg_am am    ON am.oid = ic.relam
     WHERE ic.relname = 'entity_identifier_scheme_value_idx'
       AND t.relname  = 'entity_identifier'
       AND am.amname  = 'btree'
       AND i.indisvalid
  ) THEN 1 ELSE 0 END);

ROLLBACK;
