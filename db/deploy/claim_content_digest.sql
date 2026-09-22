-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim_content_digest to pg
-- P19.4 / ADR-059: the append-only claim spine's idempotency contract for the
-- connector write path (`PgClaimSink`). A connector replay is byte-reproducible
-- modulo the two non-deterministic columns the reproducibility fingerprint
-- excludes (`claim_id`, `sys_period`, SIG-INGEST-003); persisting the same run
-- twice must therefore insert each claim exactly once. This change adds a
-- nullable `content_digest` (the sha256 over the reproducible claim payload) and
-- a partial UNIQUE index so the sink can `INSERT ... ON CONFLICT DO NOTHING` —
-- append-only preserved (no UPDATE/DELETE), corrections still land as new rows.
--
-- Additive & back-compatible (SIG-STORE-042): the column is nullable with no
-- default, so every existing claim row (content_digest IS NULL) is unaffected and
-- excluded from the partial index. The column joins the append-only guard list so
-- it is immutable like every other claim column (§16.3, SIG-STORE-011).

BEGIN;

ALTER TABLE claim
  ADD COLUMN content_digest text;

-- The idempotency key: one persisted claim per reproducible payload. Partial so
-- pre-existing / hand-inserted claims (digest NULL) never collide.
CREATE UNIQUE INDEX claim_content_digest_key
  ON claim (content_digest) WHERE content_digest IS NOT NULL;

-- Keep the append-only guard list complete (SIG-STORE-011, §16.3).
INSERT INTO append_only_guard (table_name, column_name)
VALUES ('claim', 'content_digest');

COMMIT;
