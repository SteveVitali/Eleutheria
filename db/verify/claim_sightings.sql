-- Verify eleutheria-claims:claim_sightings on pg

BEGIN;

-- The view exists with exactly the explicit columns policy.transparency's
-- allow-list names (P35.44 / J3 T-2 — no SELECT *; the closure test mirrors
-- this list against CLAIM_SIGHTING_VIEW_COLUMNS).
SELECT claim_id, subject_id, object_entity, predicate_id, sensitivity_tier,
       rights_id, sys_period, capture_id, role, binding_status, bound_at,
       artifact_id, source_id, run_id, retrieved_at
FROM v_claim_sightings WHERE FALSE;

-- The grant boundary (J3 §3.3 item 2): sig_export reads the view; the
-- public role does not reach it, and nobody else is added.
SELECT 1 AS ok FROM information_schema.role_table_grants
 WHERE table_name = 'v_claim_sightings'
   AND privilege_type = 'SELECT'
   AND grantee NOT IN ('sig_export', CURRENT_USER)
HAVING count(*) = 0;

SELECT 1 FROM information_schema.role_table_grants
 WHERE table_name = 'v_claim_sightings'
   AND grantee = 'sig_read_public'
HAVING count(*) = 0;

SELECT 1 FROM information_schema.role_table_grants
 WHERE table_name = 'v_claim_sightings'
   AND grantee = 'sig_export'
   AND privilege_type = 'SELECT'
HAVING count(*) = 1;

-- Behavioural probe (rolled back): one claim with an 'establishes' link
-- surfaces through the view carrying its sighting provenance; a
-- 'contradicts' link never appears in the edge list.
DO $$
DECLARE
    rid        uuid;
    run_a      uuid;
    run_b      uuid;
    subject    uuid;
    author     uuid;
    claim_a    uuid;
    artifact_a uuid;
    cap_a      uuid;
    cap_b      uuid;
BEGIN
    INSERT INTO vocab_resolution_strategy(strategy_id, definition)
    VALUES ('authoritative_source_wins', 'fixture') ON CONFLICT DO NOTHING;
    INSERT INTO vocab_predicate(predicate_id, vocab_version, value_datatype,
                                object_type, definition, volatility_class,
                                half_life_days, resolution_strategy)
    VALUES ('contracted_camera_count', '1.0.0', 'integer', 'quantity',
            'fixture', 'MODERATE', 365, 'authoritative_source_wins')
    ON CONFLICT DO NOTHING;

    INSERT INTO rights_record(spdx_expression, redistributable,
                              derivative_permitted, retrieval_date)
    VALUES ('Apache-2.0', 'yes', 'yes', date '2026-01-01')
    RETURNING rights_id INTO rid;

    INSERT INTO source_registry(source_id, name, source_kind,
        default_reliability, reliability_justification, rights_id,
        custody_posture, compact_status, robots_policy)
    VALUES ('src.sightings.verify', 'Sightings fixture', 'portal', 'R2',
            'fixture', rid, 'MIRROR', 'no_response', 'obey');

    INSERT INTO ingest_run(connector_name, connector_version, code_commit,
                           ruleset_version, vocab_version, parameters,
                           environment, input_digests)
    VALUES ('sig.test.sightings', '0.0.0', 'b10b', '1.0.0', '1.0.0',
            '{}', '{}', '{}')
    RETURNING run_id INTO run_a;
    INSERT INTO ingest_run(connector_name, connector_version, code_commit,
                           ruleset_version, vocab_version, parameters,
                           environment, input_digests)
    VALUES ('sig.test.sightings', '0.0.0', 'b10c', '1.0.0', '1.0.0',
            '{}', '{}', '{}')
    RETURNING run_id INTO run_b;

    INSERT INTO entity(entity_type) VALUES ('deployment') RETURNING entity_id INTO subject;
    INSERT INTO entity(entity_type) VALUES ('person') RETURNING entity_id INTO author;

    INSERT INTO claim(subject_id, predicate_id, object_type, value_kind,
                      value_text, value_num, unit, raw_value, observed_at,
                      source_reliability, claim_directness, artifact_integrity,
                      asserted_by, assertion_rationale, ingest_run_id,
                      rights_id, sensitivity_tier)
    VALUES (subject, 'contracted_camera_count', 'quantity', 'value', '25', 25,
            'cameras', '25', '2026-05-01', 'R1', 'D1', 'I1', author, 'fixture',
            run_a, rid, 0)
    RETURNING claim_id INTO claim_a;

    INSERT INTO evidence_artifact(source_id, url, stable_locator, artifact_type,
                                  acquisition_method, primary_or_secondary,
                                  rights_id, capture_status)
    VALUES ('src.sightings.verify', 'https://example.test/a',
            'stable://a', 'fixture', 'fixture', 'primary', rid, 'captured')
    RETURNING artifact_id INTO artifact_a;

    INSERT INTO evidence_capture(artifact_id, content_digest, byte_size,
                                 media_type, retrieved_at,
                                 retrieved_by_run_id, ocfl_object_id,
                                 ocfl_version, capture_method,
                                 capture_tool_version)
    VALUES (artifact_a, 'sha256:a', 10, 'application/json',
            '2026-05-01T00:00:00Z', run_a, 'obj', 'v1', 'fixture', '0')
    RETURNING capture_id INTO cap_a;
    INSERT INTO evidence_capture(artifact_id, content_digest, byte_size,
                                 media_type, retrieved_at,
                                 retrieved_by_run_id, ocfl_object_id,
                                 ocfl_version, capture_method,
                                 capture_tool_version)
    VALUES (artifact_a, 'sha256:b', 10, 'application/json',
            '2026-06-01T00:00:00Z', run_b, 'obj', 'v2', 'fixture', '0')
    RETURNING capture_id INTO cap_b;

    -- One establishing sighting + one re-sighting on a later run: two rows,
    -- the sighting's own run + retrieval instant on each.
    INSERT INTO claim_evidence(claim_id, capture_id, role)
    VALUES (claim_a, cap_a, 'establishes'), (claim_a, cap_b, 'establishes');

    IF (SELECT count(*) FROM v_claim_sightings WHERE claim_id = claim_a) <> 2 THEN
        RAISE EXCEPTION 'establishes bindings did not surface as sighting rows';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM v_claim_sightings
         WHERE claim_id = claim_a AND run_id = run_b
           AND retrieved_at = '2026-06-01T00:00:00Z'::timestamptz
           AND source_id = 'src.sightings.verify'
           AND binding_status = 'legacy_synthetic'
    ) THEN
        RAISE EXCEPTION 're-sighting row missing its run/retrieval/source columns';
    END IF;

    -- A non-establishes role is evidence AGAINST the claim — never a sighting.
    INSERT INTO claim_evidence(claim_id, capture_id, role)
    VALUES (claim_a, cap_b, 'contradicts');
    IF (SELECT count(*) FROM v_claim_sightings
         WHERE claim_id = claim_a AND role = 'contradicts') <> 0 THEN
        RAISE EXCEPTION 'a contradicts binding surfaced as a sighting';
    END IF;
END $$;

ROLLBACK;
