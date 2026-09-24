-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:camera_site_resolution on pg

BEGIN;

SELECT run_key, auto_write_tiers, observation_count, cluster_count, summary
  FROM camera_site_run WHERE false;
SELECT left_entity, right_entity, match_tier, disposition, match_evidence, input_digest
  FROM camera_site_match WHERE false;

SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'public' AND indexname = 'camera_site_match_input_digest_key'
  ) THEN 1 ELSE 0 END);

-- The materializer may INSERT, never UPDATE/DELETE.
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'camera_site_match', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'camera_site_run', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'review_item', 'INSERT')
                  AND NOT has_table_privilege('sig_materialize', 'camera_site_match', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'camera_site_match', 'DELETE')
                  AND NOT has_table_privilege('sig_materialize', 'review_item', 'UPDATE')
                 THEN 1 ELSE 0 END);

ROLLBACK;
