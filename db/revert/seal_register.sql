-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:seal_register from pg
--
-- Drops the P34.49 objects: the spine_watermark triggers + facet row, the
-- immutability trigger + function, the currently-sealed helper, the
-- sig_seal_writer role, and the capture_seal register. Spine rows in other
-- tables are untouched (append-only history is never rewritten).

BEGIN;

DROP TRIGGER IF EXISTS spine_watermark_insert ON capture_seal;
DROP TRIGGER IF EXISTS spine_watermark_update ON capture_seal;
DROP TRIGGER IF EXISTS spine_watermark_truncate ON capture_seal;
DELETE FROM spine_watermark WHERE facet = 'capture_seal';

DROP TRIGGER IF EXISTS capture_seal_immutable ON capture_seal;
DROP FUNCTION IF EXISTS capture_seal_immutable();
DROP FUNCTION IF EXISTS capture_currently_sealed(uuid);
DROP TABLE IF EXISTS capture_seal;
DROP ROLE IF EXISTS sig_seal_writer;

COMMIT;
