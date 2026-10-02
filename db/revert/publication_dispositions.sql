-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:publication_dispositions from pg
--
-- Drops the P32.5 objects: the spine_watermark triggers + facet row, the
-- immutability trigger + functions, and the registry table. Spine rows in
-- other tables are untouched (append-only history is never rewritten).

BEGIN;

DROP TRIGGER IF EXISTS spine_watermark_insert ON publication_disposition;
DROP TRIGGER IF EXISTS spine_watermark_update ON publication_disposition;
DROP TRIGGER IF EXISTS spine_watermark_truncate ON publication_disposition;
DELETE FROM spine_watermark WHERE facet = 'publication_disposition';

DROP TRIGGER IF EXISTS publication_disposition_immutable ON publication_disposition;
DROP FUNCTION IF EXISTS publication_disposition_immutable();
DROP FUNCTION IF EXISTS effective_disposition(text, text, timestamptz);
DROP TABLE IF EXISTS publication_disposition;

COMMIT;
