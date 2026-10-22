-- Verify eleutheria-claims:transparency_views on pg

BEGIN;

-- Both views exist with exactly the explicit columns policy.transparency's
-- allow-lists name (J3 §3.3 items 1–2 — no SELECT *, the closure test
-- mirrors this list against TRANSPARENCY_*_VIEW_COLUMNS).
SELECT report_id, run_id, source_id, link_basis, clock_basis, shared_run,
       started_at, finished_at, duration_seconds, completion_status,
       claims_considered, claims_inserted, claims_duplicate,
       fetches, records_emitted, robots_outcomes, refusal_classes,
       rate_limit_events, disappearances, document_outcomes,
       quota_reached, budget_reached, error_class, per_fetch,
       connector_name, connector_version, code_commit, recorded_at
FROM v_transparency_run WHERE FALSE;

SELECT run_id, target_key, state, source_uri, records, mark_digest,
       capture_classification, storage_tier, byte_size, media_type,
       retrieved_at, mark_recorded_at, bytes_retained, redaction_applied,
       redacted_derivative, http_status, source_id, shared_run
FROM v_transparency_capture WHERE FALSE;

-- The grant boundary (J3 §3.3 item 2): sig_export reads the views; the
-- public role does not reach them, and nobody else is added.
SELECT 1 AS ok FROM information_schema.role_table_grants
 WHERE table_name IN ('v_transparency_run', 'v_transparency_capture')
   AND privilege_type = 'SELECT'
   AND grantee NOT IN ('sig_export', CURRENT_USER)
HAVING count(*) = 0;

SELECT 1 FROM information_schema.role_table_grants
 WHERE table_name = 'v_transparency_run'
   AND grantee = 'sig_read_public'
HAVING count(*) = 0;
SELECT 1 FROM information_schema.role_table_grants
 WHERE table_name = 'v_transparency_capture'
   AND grantee = 'sig_read_public'
HAVING count(*) = 0;

-- The C-13 shared-run rule, functionally: two executions recorded on one
-- run render NULL for the run-owned values rather than presenting the
-- shared run's code identity and completion counts as each execution's;
-- the unshared execution keeps them. (Report rows are immutable, so the
-- unshared case uses its own fresh run.)
DO $$
DECLARE
    shared_run_id uuid;
    sole_run_id   uuid;
BEGIN
    INSERT INTO ingest_run (connector_name, connector_version, code_commit,
                            ruleset_version, vocab_version, parameters,
                            environment, input_digests)
    VALUES ('sig.test.transparency', '0.0.0', 'deadbeef', '1.0.0', '1.0.0',
            '{}', '{}', '{}')
    RETURNING run_id INTO shared_run_id;

    INSERT INTO ingest_run_completion (run_id, source_id, status, claims_inserted)
    VALUES (shared_run_id, 'src.shared.demo', 'ok', 7);

    -- A shared run = one live report plus a backfilled report (the live key
    -- refuses a second live row; the backfill key needs its source URI).
    INSERT INTO ingest_run_report (run_id, source_id, link_basis, clock_basis,
                                   fetches, records_emitted, backfilled_from)
    VALUES (shared_run_id, 'src.shared.demo', 'live', 'db', 3, 7, NULL),
           (shared_run_id, 'src.shared.demo', 'backfill:sole-candidate',
            'run_row', 3, 7,
            'gs://sig-test/ops/runs/src.shared.demo/1.json');

    IF (SELECT count(*) FROM v_transparency_run
         WHERE run_id = shared_run_id AND shared_run
           AND code_commit IS NULL AND claims_inserted IS NULL
           AND finished_at IS NULL AND completion_status IS NULL) <> 2 THEN
        RAISE EXCEPTION 'C-13 shared-run suppression did not fire';
    END IF;

    INSERT INTO ingest_run (connector_name, connector_version, code_commit,
                            ruleset_version, vocab_version, parameters,
                            environment, input_digests)
    VALUES ('sig.test.transparency', '0.0.0', 'cafef00d', '1.0.0', '1.0.0',
            '{}', '{}', '{}')
    RETURNING run_id INTO sole_run_id;

    INSERT INTO ingest_run_completion (run_id, source_id, status, claims_inserted)
    VALUES (sole_run_id, 'src.sole.demo', 'ok', 11);

    INSERT INTO ingest_run_report (run_id, source_id, link_basis, clock_basis,
                                   fetches, records_emitted)
    VALUES (sole_run_id, 'src.sole.demo', 'live', 'db', 1, 11);

    IF NOT EXISTS (SELECT 1 FROM v_transparency_run
                    WHERE run_id = sole_run_id AND NOT shared_run
                      AND code_commit = 'cafef00d' AND claims_inserted = 11
                      AND completion_status = 'ok') THEN
        RAISE EXCEPTION 'sole-execution run-owned values missing from view';
    END IF;
END $$;

ROLLBACK;
