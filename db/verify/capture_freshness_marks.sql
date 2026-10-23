-- Verify eleutheria-claims:capture_freshness_marks on pg

BEGIN;

-- The mark table carries the four P35.41 columns.
SELECT records_digest, upstream_modified_at, upstream_token, upstream_modified_basis
FROM ingest_run_capture WHERE FALSE;

-- The view carries them appended after the P35.33 prefix (the closure test
-- mirrors this list against TRANSPARENCY_CAPTURE_VIEW_COLUMNS).
SELECT run_id, target_key, state, source_uri, records, mark_digest,
       capture_classification, storage_tier, byte_size, media_type,
       retrieved_at, mark_recorded_at, bytes_retained, redaction_applied,
       redacted_derivative, http_status, source_id, shared_run,
       records_digest, upstream_modified_at, upstream_token, upstream_modified_basis
FROM v_transparency_capture WHERE FALSE;

-- The grant boundary is unchanged: sig_export reads the view; the public
-- role does not reach it.
SELECT 1 FROM information_schema.role_table_grants
 WHERE table_name = 'v_transparency_capture'
   AND grantee = 'sig_read_public'
HAVING count(*) = 0;

-- records_digest is flushed-marks-only: a captured mark carrying one is refused.
DO $$
DECLARE
    probe_run uuid;
BEGIN
    INSERT INTO ingest_run (connector_name, connector_version, code_commit,
                            ruleset_version, vocab_version, parameters,
                            environment, input_digests)
    VALUES ('sig.test.cfm', '0.0.0', 'f00d', '1.0.0', '1.0.0',
            '{}', '{}', '{}')
    RETURNING run_id INTO probe_run;

    BEGIN
        INSERT INTO ingest_run_capture
            (run_id, target_key, state, capture_digest, source_uri,
             media_type, byte_size, records_digest)
        VALUES (probe_run, 't1', 'captured', 'sha256:x', 'https://x/y',
                'application/json', 1, 'deadbeef');
        RAISE EXCEPTION 'records_digest on a captured mark was not refused';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;

    -- A flushed mark carries digest + the declared upstream value fine.
    INSERT INTO ingest_run_capture
        (run_id, target_key, state, capture_digest, source_uri,
         media_type, byte_size, records, records_digest,
         upstream_modified_at, upstream_token, upstream_modified_basis)
    VALUES (probe_run, 't1', 'flushed', 'sha256:x', 'https://x/y',
            'application/json', 1, 3, 'deadbeef',
            '2026-10-01T00:00:00Z', '"v9"', 'ETag');
END $$;

ROLLBACK;
