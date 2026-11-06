-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify eleutheria-claims:disappearance_event_grant on pg

BEGIN;

-- The two event columns are writable by sig_ingest.
SELECT 1 WHERE has_column_privilege(
    'sig_ingest', 'public.evidence_artifact', 'capture_status', 'UPDATE');
SELECT 1 WHERE has_column_privilege(
    'sig_ingest', 'public.evidence_artifact', 'disappeared_observed_at', 'UPDATE');

-- Nothing else on the artifact widened: no other-column UPDATE, no DELETE.
SELECT 1 WHERE NOT has_column_privilege(
    'sig_ingest', 'public.evidence_artifact', 'stable_locator', 'UPDATE');
SELECT 1 WHERE NOT has_table_privilege(
    'sig_ingest', 'public.evidence_artifact', 'DELETE');

COMMIT;
