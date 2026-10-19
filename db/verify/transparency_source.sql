-- Verify sig:transparency_source on pg

BEGIN;

-- v_transparency_source exists with exactly the explicit columns
-- policy.transparency.TRANSPARENCY_SOURCE_VIEW_COLUMNS names (J3 §3.3
-- item 3 — no SELECT *; the closure test mirrors this list).
SELECT source_id, name, source_kind, homepage_url, custody_posture,
       compact_status, ingestion_permitted, robots_policy, last_verified_at,
       spdx_expression, attribution_text, redistributable,
       derivative_permitted, terms_url, terms_reviewed, terms_reviewed_at,
       retrieval_date, rights_decision_basis, rights_decision_reviewer,
       rights_decided_at, lane, lane_evidence, lane_evidence_uri,
       lane_decision_authority, lane_review_needed, part_viii_class,
       packet_limited, sig_labelled_cc0, last_execution_at, last_capture_at
FROM v_transparency_source WHERE FALSE;

-- The grant boundary (J3 §3.3 items 2–3): sig_export reads the view; the
-- public role does not reach it, and nobody else is added.
SELECT 1 AS ok FROM information_schema.role_table_grants
 WHERE table_name = 'v_transparency_source'
   AND privilege_type = 'SELECT'
   AND grantee NOT IN ('sig_export', CURRENT_USER)
HAVING count(*) = 0;

SELECT 1 FROM information_schema.role_table_grants
 WHERE table_name = 'v_transparency_source'
   AND grantee = 'sig_read_public'
HAVING count(*) = 0;

-- The mirror is append-only: an UPDATE must refuse.
DO $$
DECLARE
    rid uuid;
BEGIN
    INSERT INTO rights_record(spdx_expression, redistributable,
                              derivative_permitted, retrieval_date)
    VALUES ('UNDETERMINED', 'UNDETERMINED', 'UNDETERMINED', date '2026-10-19')
    RETURNING rights_id INTO rid;

    INSERT INTO source_registry(source_id, name, source_kind,
        default_reliability, reliability_justification, rights_id,
        custody_posture, compact_status, robots_policy)
    VALUES ('src.transparency.verify', 'Fixture', 'portal', 'R2', 'fixture',
            rid, 'MIRROR', 'no_response', 'obey');

    -- Two declarations for the same source: the current view renders the
    -- latest recorded version, never an update of the first.
    INSERT INTO source_redistribution(source_id, registry_version, lane,
        part_viii_class, evidence, decision_authority)
    VALUES ('src.transparency.verify', 'v1', 'derived-only', 'none-known',
            'first declaration', 'D-J3-1 [B-19]'),
           ('src.transparency.verify', 'v2', 'link-only', 'P8-3',
            'second declaration', 'D-J3-1 [B-19]');

    IF (SELECT lane FROM source_redistribution_current
         WHERE source_id = 'src.transparency.verify') <> 'link-only' THEN
        RAISE EXCEPTION 'source_redistribution_current did not pick the latest row';
    END IF;

    -- The transparency view carries the recorded lane fields end-to-end.
    IF (SELECT lane FROM v_transparency_source
         WHERE source_id = 'src.transparency.verify') <> 'link-only' THEN
        RAISE EXCEPTION 'v_transparency_source did not join the recorded lane';
    END IF;
    IF (SELECT part_viii_class FROM v_transparency_source
         WHERE source_id = 'src.transparency.verify') <> 'P8-3' THEN
        RAISE EXCEPTION 'v_transparency_source did not join the Part VIII class';
    END IF;

    -- The lane vocabulary is closed: an invented lane cannot be written.
    BEGIN
        INSERT INTO source_redistribution(source_id, registry_version, lane)
        VALUES ('src.transparency.verify', 'v3', 'wide-open');
        RAISE EXCEPTION 'the lane CHECK accepted an off-vocabulary lane';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;

    -- Append-only: an UPDATE is never a path. The trigger's refusal is
    -- caught; the row state itself proves nothing moved (the trigger and
    -- a sentinel raise share the raise_exception SQLSTATE, so the assert
    -- reads the row, not the exception).
    BEGIN
        UPDATE source_redistribution SET lane = 'raw-ok'
         WHERE source_id = 'src.transparency.verify';
    EXCEPTION WHEN raise_exception THEN
        NULL;
    END;
    IF EXISTS (SELECT 1 FROM source_redistribution
                WHERE source_id = 'src.transparency.verify'
                  AND lane = 'raw-ok') THEN
        RAISE EXCEPTION 'source_redistribution allowed an UPDATE';
    END IF;
END $$;

ROLLBACK;
