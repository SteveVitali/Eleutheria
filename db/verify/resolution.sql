-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:resolution on pg
SELECT resolution_id FROM resolution WHERE false;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='resolution_no_overlap' AND contype='x') THEN
    RAISE EXCEPTION 'resolution non-overlap exclusion constraint missing'; END IF;
END $$;
