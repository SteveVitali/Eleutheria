-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:entity_identifier_value_trgm to pg
-- P31.1 / ADR-108: bound GET /v1/search (D-P30.4-2). The read API matches
-- `entity_identifier.value ILIKE '%term%'`; the only index on the table is the
-- (entity_id, scheme, value) primary key, so every search was a sequential scan.
-- A pg_trgm GIN index serves an unanchored ILIKE for any term of 3 or more
-- characters, which is exactly the minimum query length the API enforces.
--
-- NON-TRANSACTIONAL on purpose (no BEGIN/COMMIT): CREATE INDEX CONCURRENTLY cannot
-- run inside a transaction block, and it is what keeps the build from blocking the
-- scheduled ingest's INSERTs into entity_identifier (design §5 lesson 11). If a
-- concurrent build is interrupted it leaves an INVALID index; the verify script
-- fails on that (indisvalid), and the operator drops it and re-deploys.
--
-- Measured on the hosted spine before the build (2026-09-24): entity_identifier is
-- 247,065 rows / 32 MB heap (68 MB with the PK), ~16 MB of value text; the whole
-- database is 4.37 GB of the 15 GB disk. A trigram GIN over ~16 MB of text is tens
-- of MB, well inside the headroom.
--
-- pg_trgm ships with PostgreSQL contrib, is a trusted extension (PG13+), and is on
-- the Cloud SQL supported-extension list (pg_available_extensions on sig-pg lists
-- pg_trgm 1.6). Additive and back-compatible: no table, column, or row changes.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX CONCURRENTLY IF NOT EXISTS entity_identifier_value_trgm_idx
  ON entity_identifier USING gin (value gin_trgm_ops);

-- IF NOT EXISTS also skips an INVALID leftover of an interrupted concurrent build.
-- Fail the deploy loudly in that case rather than record a success over a dead index.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
     WHERE c.relname = 'entity_identifier_value_trgm_idx' AND i.indisvalid
  ) THEN
    RAISE EXCEPTION 'entity_identifier_value_trgm_idx is missing or INVALID (drop it CONCURRENTLY, then redeploy)';
  END IF;
END
$$;
