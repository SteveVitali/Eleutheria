-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:review_campaign on pg

BEGIN;

SELECT campaign_id, purpose, design, created_by, created_at
  FROM review_campaign WHERE false;
SELECT campaign_id, item_id, stratum, created_at
  FROM review_campaign_item WHERE false;

-- The materializer may draw campaigns and append decisions, never mutate them.
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'review_campaign', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'review_campaign', 'SELECT')
                  AND has_table_privilege('sig_materialize', 'review_campaign_item', 'INSERT')
                  AND has_table_privilege('sig_materialize', 'review_campaign_item', 'SELECT')
                  AND has_table_privilege('sig_materialize', 'review_decision', 'INSERT')
                  AND NOT has_table_privilege('sig_materialize', 'review_campaign', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'review_campaign', 'DELETE')
                  AND NOT has_table_privilege('sig_materialize', 'review_campaign_item', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'review_campaign_item', 'DELETE')
                  AND NOT has_table_privilege('sig_materialize', 'review_decision', 'UPDATE')
                  AND NOT has_table_privilege('sig_materialize', 'review_decision', 'DELETE')
                 THEN 1 ELSE 0 END);

-- The read roles may inspect campaigns (SELECT only).
SELECT 1 / (CASE WHEN has_table_privilege('sig_read_public', 'review_campaign', 'SELECT')
                  AND has_table_privilege('sig_read_public', 'review_campaign_item', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'review_campaign', 'INSERT')
                 THEN 1 ELSE 0 END);

ROLLBACK;
