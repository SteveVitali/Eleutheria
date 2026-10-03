-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:disposition_decided_at_authority from pg
--
-- Restores the documented pre-change state: the `publication_dispositions`
-- change had already created `decided_at ... DEFAULT clock_timestamp()` — so
-- the default is re-pinned identically (never dropped; dropping it would
-- break every normal write under the P32.10a writer contract) and the
-- authority comment is removed. Rows are untouched (append-only; nothing is
-- rewritten).

BEGIN;

COMMENT ON COLUMN publication_disposition.decided_at IS NULL;
ALTER TABLE publication_disposition
  ALTER COLUMN decided_at SET DEFAULT clock_timestamp();

COMMIT;
