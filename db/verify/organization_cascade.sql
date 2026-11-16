-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:organization_cascade on pg

BEGIN;

SELECT run_key, auto_link_tiers, organization_count, link_count,
       possibly_same_count, summary
  FROM organization_run WHERE false;
SELECT left_entity, right_entity, relation_type, match_tier, disposition,
       match_evidence, input_digest
  FROM organization_match WHERE false;
SELECT execution_id, run_key, input_count, summary
  FROM organization_execution WHERE false;

SELECT 1 / (CASE WHEN EXISTS (
    SELECT 1 FROM pg_indexes
     WHERE schemaname = 'public' AND indexname = 'organization_match_input_digest_key'
  ) THEN 1 ELSE 0 END);

-- The materializer may INSERT + SELECT, never UPDATE/DELETE; the export role
-- reads; the public read role does not (the post-P34.25 allowlist posture).
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'organization_match', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'organization_run', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'organization_execution', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'organization_match', 'SELECT')
                  AND has_table_privilege('sig_export', 'organization_match', 'SELECT')
                  AND NOT has_table_privilege('sig_materialize', 'organization_match', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'organization_match', 'DELETE')
                  AND NOT has_table_privilege('sig_materialize', 'organization_run', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'organization_run', 'DELETE')
                  AND NOT has_table_privilege('sig_materialize', 'organization_execution', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'organization_execution', 'DELETE')
                  AND NOT has_table_privilege('sig_read_public', 'organization_match', 'SELECT')
                 THEN 1 ELSE 0 END);

ROLLBACK;
