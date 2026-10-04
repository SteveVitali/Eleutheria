-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:public_read_allowlist on pg

BEGIN;

-- The published §37 surface IS readable by the public role.
SELECT 1 / (CASE WHEN has_table_privilege('sig_read_public', 'claim', 'SELECT')
                  AND has_table_privilege('sig_read_public', 'entity_identifier', 'SELECT')
                  AND has_table_privilege('sig_read_public', 'spine_watermark', 'SELECT')
                  AND has_table_privilege('sig_read_public', 'coverage_record', 'SELECT')
                 THEN 1 ELSE 0 END);

-- … and every table OFF the published surface is NOT — spot-checks across the
-- formerly blanket-granted categories: domain projections, graph internals,
-- operational/ingest tables, byte stores, review + camera-site machinery,
-- vocab registries, and the L4 inference schema.
SELECT 1 / (CASE WHEN NOT has_table_privilege('sig_read_public', 'person', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'contract', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'resolution', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'extraction', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'ingest_run', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'evidence_blob', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'review_item', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'camera_site_run', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'vocab_predicate', 'SELECT')
                  AND NOT has_table_privilege('sig_read_public', 'inference.derived_fact', 'SELECT')
                  AND NOT has_schema_privilege('sig_read_public', 'inference', 'USAGE')
                 THEN 1 ELSE 0 END);

-- publication_disposition keeps the column-limited posture: the tombstone-safe
-- columns are readable, the privileged columns are not, and there is no
-- table-level SELECT.
SELECT 1 / (CASE WHEN has_column_privilege('sig_read_public', 'publication_disposition',
                                          'disposition', 'SELECT')
                  AND NOT has_column_privilege('sig_read_public', 'publication_disposition',
                                               'rationale', 'SELECT')
                  AND NOT has_column_privilege('sig_read_public', 'publication_disposition',
                                               'decided_by', 'SELECT')
                 THEN 1 ELSE 0 END);

-- sig_materialize keeps the read scope it actually uses (was: inheritance).
SELECT 1 / (CASE WHEN has_table_privilege('sig_materialize', 'resolution', 'SELECT')
                  AND has_table_privilege('sig_materialize', 'ingest_run_completion', 'SELECT')
                  AND has_table_privilege('sig_materialize', 'inference.derived_fact', 'SELECT')
                  AND has_table_privilege('sig_materialize', 'camera_site_match', 'SELECT')
                 THEN 1 ELSE 0 END);

ROLLBACK;
