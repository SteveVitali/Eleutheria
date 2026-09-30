-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:entity_identifier_scheme_value to pg
-- P31.3 / ADR-110: a btree index on entity_identifier (scheme, value).
--
-- The only indexes on entity_identifier were the (entity_id, scheme, value) primary
-- key and P31.1's trigram GIN on value. So "which entity carries this identifier?"
-- could only be answered by a scan. The identity guard asks that question once per
-- chunk, for the subjects that are not keyed yet (it adopts a legacy identifier
-- instead of minting a duplicate). Measured on a 1M-identifier table with 10k unkeyed
-- values, that lookup took 0.7-1.7 s under a custom plan but 19-169 s under a generic
-- (prepared) plan. psycopg prepares a statement after its fifth execution, so a long
-- land would eventually hit the generic plan. With this index both plans are index
-- probes (measured in docs/build/runs/P31.3.md).
--
-- NON-TRANSACTIONAL on purpose (no BEGIN/COMMIT): CREATE INDEX CONCURRENTLY cannot
-- run inside a transaction block, and it keeps the build from blocking ingest INSERTs
-- (design §5 lesson 11). An interrupted concurrent build leaves an INVALID index.
-- The check below and the verify script fail on it; the operator then drops the
-- index CONCURRENTLY and redeploys. Additive: no table, column or row changes.

CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_identifier_scheme_value_idx
  ON entity_identifier (scheme, value);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
     WHERE c.relname = 'entity_identifier_scheme_value_idx' AND i.indisvalid
  ) THEN
    RAISE EXCEPTION 'entity_identifier_scheme_value_idx is missing or INVALID (drop it CONCURRENTLY, then redeploy)';
  END IF;
END
$$;
