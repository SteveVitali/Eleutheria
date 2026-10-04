-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:shared_temporal_contract on pg

BEGIN;

-- All four objects exist.
SELECT 1 / (CASE WHEN to_regclass('camera_site_execution') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('spine_watermark') IS NOT NULL THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'eligible_occurrence'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'spine_watermark_touch'
  ) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('claim_evidence_establishing_idx') IS NOT NULL
                THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN to_regclass('camera_site_execution_completed_idx') IS NOT NULL
                THEN 1 ELSE 0 END);

-- Every existing run has exactly one backfilled execution reference.
SELECT 1 / (CASE WHEN NOT EXISTS (
    SELECT 1 FROM camera_site_run r
     WHERE NOT EXISTS (SELECT 1 FROM camera_site_execution x
                        WHERE x.run_key = r.run_key)
  ) THEN 1 ELSE 0 END);

-- One watermark row per watched facet; counts agree with the real tables.
SELECT 1 / (CASE WHEN (SELECT count(*) FROM spine_watermark) = 27 THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN (SELECT row_count FROM spine_watermark WHERE facet = 'claim')
                    = (SELECT count(*) FROM claim) THEN 1 ELSE 0 END);
SELECT 1 / (CASE WHEN (SELECT closed_count FROM spine_watermark WHERE facet = 'claim')
                    = (SELECT count(*) FROM claim WHERE upper(sys_period) IS NOT NULL)
             THEN 1 ELSE 0 END);

-- The row-change trigger fires: inserting an entity bumps the entity facet
-- (the whole verify rolls back, so this fixture row never lands).
INSERT INTO entity(entity_type) VALUES ('deployment');
SELECT 1 / (CASE WHEN (SELECT bump FROM spine_watermark WHERE facet = 'entity') > 0
             THEN 1 ELSE 0 END);

ROLLBACK;
