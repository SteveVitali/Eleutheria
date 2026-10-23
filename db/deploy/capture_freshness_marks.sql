-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:capture_freshness_marks to pg
-- P35.41 / SIG-TRANSP-031 + K9 §5.4: the capture mark's freshness columns —
--
--   * records_digest          — the order-independent fingerprint of the record
--     set the capture's post-capture stages emitted (volatile-field-free under
--     the registry's obs/ref classes). The mark where a target's records_digest
--     differs from its prior flushed mark IS the SIG-record-change date —
--     byte-only and volatile-field-only differences never move it.
--   * upstream_modified_at    — the upstream's own declared change instant
--     (editingInfo.lastEditDate, rowsUpdatedAt, metadata_modified,
--     data_last_updated, Last-Modified). Never SIG's retrieval clock — a
--     transport that declares no date carries NULL and the release surface
--     renders not_detectable.
--   * upstream_token          — an opaque upstream version marker (ETag) where
--     the publisher declares a version but no date.
--   * upstream_modified_basis — the declared field the value came from (closed
--     basis vocabulary at the writer; the column itself stores the label).
--
-- All four are NULL-tolerant for every mark written before this change — no
-- backfill invents a declared value an acquisition never read. records_digest
-- is flushed-marks-only by CHECK. v_transparency_capture gains the columns on
-- its existing explicit-column list (the sig_export surface; the artifact's
-- own scrub stays the publication boundary). Append-only: no UPDATE/DELETE on
-- any living row.

BEGIN;

ALTER TABLE ingest_run_capture
  ADD COLUMN records_digest text,
  ADD COLUMN upstream_modified_at timestamptz,
  ADD COLUMN upstream_token text,
  ADD COLUMN upstream_modified_basis text;

ALTER TABLE ingest_run_capture
  ADD CONSTRAINT ingest_run_capture_records_digest_flushed
  CHECK (records_digest IS NULL OR state = 'flushed');

CREATE OR REPLACE VIEW v_transparency_capture AS
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
    COALESCE(GREATEST(re.n, rc.n) > 1, false) AS shared_run,
    -- P35.41: appended columns — CREATE OR REPLACE requires the original
    -- column prefix unchanged; the allow-list order in
    -- policy.transparency.TRANSPARENCY_CAPTURE_VIEW_COLUMNS mirrors this.
    irc.records_digest,
    irc.upstream_modified_at,
    irc.upstream_token,
    irc.upstream_modified_basis
FROM ingest_run_capture irc
LEFT JOIN run_executions re ON re.run_id = irc.run_id
LEFT JOIN run_completions rc ON rc.run_id = irc.run_id
-- The mark binds its capture row by the run that fetched it and the best
-- available address: the recorded content digest, then the blob digest
-- (evidence_blob.blob_digest shares the mark's multihash scheme), then the
-- fetched URI as it resolves through evidence_blob. LATERAL … LIMIT 1 keeps
-- the join 1:1 — a mark row never fans out across several captures.
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
-- A mark on an unshared run takes its source from that execution's report;
-- a shared-run mark carries NULL source_id rather than guessing which
-- execution fetched it (C-13).
LEFT JOIN ingest_run_report rr_own
       ON rr_own.run_id = irc.run_id
      AND GREATEST(COALESCE(re.n, 0), COALESCE(rc.n, 0)) = 1;

GRANT SELECT ON v_transparency_capture TO sig_export;

COMMIT;
