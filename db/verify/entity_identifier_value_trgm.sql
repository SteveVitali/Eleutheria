-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:entity_identifier_value_trgm on pg

BEGIN;

-- The extension is installed.
SELECT 1 / (CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')
                 THEN 1 ELSE 0 END);

-- The trigram index exists, is a GIN index on entity_identifier, and is VALID (an
-- interrupted CREATE INDEX CONCURRENTLY leaves indisvalid = false).
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1
      FROM pg_index i
      JOIN pg_class ic ON ic.oid = i.indexrelid
      JOIN pg_class t  ON t.oid  = i.indrelid
      JOIN pg_am am    ON am.oid = ic.relam
     WHERE ic.relname = 'entity_identifier_value_trgm_idx'
       AND t.relname  = 'entity_identifier'
       AND am.amname  = 'gin'
       AND i.indisvalid
  ) THEN 1 ELSE 0 END);

ROLLBACK;
