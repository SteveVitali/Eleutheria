-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert eleutheria-claims:capture_freshness_marks from pg
--
-- Restore the P35.33 v_transparency_capture shape (the new columns make
-- CREATE OR REPLACE refuse, so the view is dropped and recreated at its
-- prior definition), then drop the mark columns.

BEGIN;

DROP VIEW IF EXISTS v_transparency_capture;

CREATE VIEW v_transparency_capture AS
WITH run_executions AS (
    SELECT run_id, count(*) AS n
      FROM ingest_run_report
     WHERE run_id IS NOT NULL
     GROUP BY run_id
),
run_completions AS (
    SELECT run_id, count(*) AS n
      FROM ingest_run_completion
     GROUP BY run_id
)
SELECT
    irc.run_id,
    irc.target_key,
    irc.state,
    irc.source_uri,
    irc.records,
    irc.capture_digest AS mark_digest,
    ec.capture_classification,
    ec.storage_tier,
    COALESCE(ec.byte_size, irc.byte_size) AS byte_size,
    COALESCE(ec.media_type, irc.media_type) AS media_type,
    COALESCE(ec.retrieved_at, irc.retrieved_at) AS retrieved_at,
    irc.recorded_at AS mark_recorded_at,
    (ec.blob_digest IS NOT NULL) AS bytes_retained,
    COALESCE(ec.redaction_applied, false) AS redaction_applied,
    (ec.parent_capture_id IS NOT NULL) AS redacted_derivative,
    ec.http_status,
    COALESCE(ea.source_id, rr_own.source_id) AS source_id,
    COALESCE(GREATEST(re.n, rc.n) > 1, false) AS shared_run
FROM ingest_run_capture irc
LEFT JOIN run_executions re ON re.run_id = irc.run_id
LEFT JOIN run_completions rc ON rc.run_id = irc.run_id
LEFT JOIN LATERAL (
    SELECT ec.*
      FROM evidence_capture ec
      LEFT JOIN evidence_blob eb ON eb.blob_digest = ec.blob_digest
     WHERE ec.retrieved_by_run_id = irc.run_id
       AND (ec.content_digest = irc.capture_digest
            OR ec.blob_digest = irc.capture_digest
            OR eb.source_uri = irc.source_uri)
     ORDER BY (ec.content_digest = irc.capture_digest) DESC,
              (ec.blob_digest = irc.capture_digest) DESC,
              ec.retrieved_at DESC
     LIMIT 1
) ec ON true
LEFT JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
LEFT JOIN ingest_run_report rr_own
       ON rr_own.run_id = irc.run_id
      AND GREATEST(COALESCE(re.n, 0), COALESCE(rc.n, 0)) = 1;

GRANT SELECT ON v_transparency_capture TO sig_export;

ALTER TABLE ingest_run_capture
  DROP CONSTRAINT IF EXISTS ingest_run_capture_records_digest_flushed,
  DROP COLUMN IF EXISTS records_digest,
  DROP COLUMN IF EXISTS upstream_modified_at,
  DROP COLUMN IF EXISTS upstream_token,
  DROP COLUMN IF EXISTS upstream_modified_basis;

COMMIT;
