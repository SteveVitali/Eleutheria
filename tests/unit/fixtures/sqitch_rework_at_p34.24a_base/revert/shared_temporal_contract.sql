-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:shared_temporal_contract from pg
--
-- Drops the P32.4 objects: the triggers first, then the trigger function, the
-- watermark table, the execution table and the SQL function. camera_site_run
-- rows are untouched (append-only history is never rewritten).

BEGIN;

DO $$
DECLARE
  facet text;
BEGIN
  FOREACH facet IN ARRAY ARRAY[
    'claim','claim_evidence','claim_qualifier','evidence_capture',
    'evidence_artifact','evidence_blob','extraction','ingest_run',
    'ingest_run_capture','ingest_run_completion','rights_record','rights_decision',
    'source_registry','entity','entity_identifier','organization',
    'organization_relation','relationship','resolution','contradiction',
    'coverage_record','research_task','review_item','review_decision',
    'camera_site_run','camera_site_match','camera_site_execution']
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS spine_watermark_insert ON %I', facet);
    EXECUTE format('DROP TRIGGER IF EXISTS spine_watermark_update ON %I', facet);
    EXECUTE format('DROP TRIGGER IF EXISTS spine_watermark_truncate ON %I', facet);
  END LOOP;
END
$$;

DROP INDEX IF EXISTS camera_site_execution_completed_idx;
DROP INDEX IF EXISTS claim_evidence_establishing_idx;
DROP FUNCTION IF EXISTS spine_watermark_touch();
DROP TABLE IF EXISTS spine_watermark;
DROP TABLE IF EXISTS camera_site_execution;
DROP FUNCTION IF EXISTS eligible_occurrence(uuid, timestamptz);

COMMIT;
