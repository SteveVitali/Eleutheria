-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:transparency_views to pg
-- P35.33 (J3 §3.1 + §3.3 items 1–2, K10 §18 C-13/C-14): the explicit-column
-- transparency views the export's runs.jsonl / captures.jsonl / issues.jsonl
-- read. S-12: views only, never SELECT *; GRANT SELECT TO sig_export only —
-- the public never reaches the raw report/capture rows. Every emitted column
-- is named in policy.transparency's allow-list (TRANSPARENCY_*_VIEW_COLUMNS)
-- and passes the S-1…S-14 scrub at emission.
--
-- K10 C-13 — execution-keyed rows: one row per ingest_run_report execution.
-- A pre-P31.2 shared ingest_run may serve several executions (several
-- reports and/or several completions keyed to it); its run-level values
-- (ingest_run.code_commit / connector identity, and the completion's
-- finished_at / status / claims_* counts) belong to the RUN, not to each
-- execution, so they are emitted NULL wherever a run serves more than one
-- recorded execution — the export renders "not_recorded (shared run)".
-- The report row's own fields (started_at, duration_seconds, fetches,
-- records_emitted, the outcome classes) are the execution's own and always
-- pass through.
--
-- Never-exported fields stay out of both views (J3 §3.5 + S-2…S-4):
-- ingest_run.parameters / environment, ingest_run_completion.detail /
-- run_record_uri / backfilled_from, report backfilled_from and the gs://
-- WORM locators (internal locations), extraction.parameters, and any
-- quarantine payload (counts by reason ride the report's refusal_classes).

BEGIN;

CREATE VIEW v_transparency_run AS
WITH run_executions AS (
    -- How many recorded executions a run row serves (the C-13 shared-run
    -- test): reports and completions are each execution-keyed, so the run
    -- is shared when EITHER grain records more than one execution on it.
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
    rr.report_id,
    rr.run_id,
    rr.source_id,
    rr.link_basis,
    rr.clock_basis,
    COALESCE(GREATEST(re.n, rc.n) > 1, false) AS shared_run,
    rr.started_at,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.finished_at END AS finished_at,
    rr.duration_seconds,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.status END AS completion_status,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.claims_considered END AS claims_considered,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.claims_inserted END AS claims_inserted,
    CASE WHEN GREATEST(COALESCE(re.n, 1), COALESCE(rc.n, 0)) = 1
         THEN c.claims_duplicate END AS claims_duplicate,
    rr.fetches,
    rr.records_emitted,
    rr.robots_outcomes,
    rr.refusal_classes,
    rr.rate_limit_events,
    rr.disappearances,
    rr.document_outcomes,
    rr.quota_reached,
    rr.budget_reached,
    rr.error_class,
    rr.per_fetch,
    CASE WHEN COALESCE(re.n, 0) = 1 AND COALESCE(rc.n, 0) <= 1
         THEN ir.connector_name END AS connector_name,
    CASE WHEN COALESCE(re.n, 0) = 1 AND COALESCE(rc.n, 0) <= 1
         THEN ir.connector_version END AS connector_version,
    CASE WHEN COALESCE(re.n, 0) = 1 AND COALESCE(rc.n, 0) <= 1
         THEN ir.code_commit END AS code_commit,
    rr.recorded_at
FROM ingest_run_report rr
LEFT JOIN run_executions re ON re.run_id = rr.run_id
LEFT JOIN run_completions rc ON rc.run_id = rr.run_id
-- A completion row attributes run-level counts to the execution only when
-- the run serves exactly one recorded execution of each grain (1:1). A
-- second completion on the same run (a backfilled WORM row beside the live
-- one) makes attribution ambiguous and the fields stay NULL.
LEFT JOIN ingest_run_completion c
       ON c.run_id = rr.run_id
      AND COALESCE(re.n, 1) = 1
      AND COALESCE(rc.n, 0) = 1
-- The run row's code identity only when the execution owns its run —
-- re.n = 1 and no competing completions (C-13); NULL renders
-- "not_recorded (shared run)".
LEFT JOIN ingest_run ir
       ON ir.run_id = rr.run_id
      AND COALESCE(re.n, 0) = 1
      AND COALESCE(rc.n, 0) <= 1;

GRANT SELECT ON v_transparency_run TO sig_export;

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
