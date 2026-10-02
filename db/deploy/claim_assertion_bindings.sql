-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:claim_assertion_bindings to pg
-- P32.2 (SIG-TRUST-001/002, FIELD_MAP docs/build/reports/p32.2-assertions/):
-- typed-assertion preservation + actual-capture binding persistence. Additive
-- only — every new column's default labels pre-P32.2 rows honestly instead of
-- rewriting them: claim_evidence.binding_status DEFAULT 'legacy_synthetic' marks
-- every existing link as the synthetic per-run provenance it is; new writes
-- classify themselves actual_capture|replayed|document_only. claim_qualifier
-- (defined in claim_evidence.sql, never written) gains the typed columns the
-- six mapped qualifier families need. assertion_quarantine is the append-only
-- fail-closed landing for unknown predicates/types and binding failures.

BEGIN;

-- 1. claim_evidence: populate the extraction + locator columns that existed but
--    were never written, and persist the extractor/config identity + binding
--    classification the link was missing (SIG-TRUST-002).
ALTER TABLE claim_evidence
  ADD COLUMN extraction_config_digest text,
  ADD COLUMN extractor_version        text,
  ADD COLUMN binding_status           text NOT NULL DEFAULT 'legacy_synthetic',
  ADD COLUMN bound_at                 timestamptz NOT NULL DEFAULT clock_timestamp();

ALTER TABLE claim_evidence
  ADD CONSTRAINT claim_evidence_binding_status_ck
  CHECK (binding_status IN
         ('actual_capture','replayed','document_only','legacy_synthetic'));

-- 2. claim: the named versioned default mapping + explicit basis a row's
--    defaults were derived under (SIG-TRUST-001: "a named versioned mapping
--    and an explicit basis"). NULL on pre-P32.2 rows = not recorded (honest).
ALTER TABLE claim
  ADD COLUMN assertion_map_id   text,
  ADD COLUMN assertion_map_basis text;

-- The append-only guard (claim_append_only.sql) covers every claim column
-- except sys_period, populated from the live schema at ITS deploy time — new
-- columns must be registered explicitly so the guard cannot silently widen
-- what is mutable (SIG-STORE-011).
INSERT INTO append_only_guard (table_name, column_name)
VALUES ('claim', 'assertion_map_id'), ('claim', 'assertion_map_basis')
ON CONFLICT (table_name, column_name) DO NOTHING;

-- 3. claim_qualifier: the typed qualifier surface. The table exists with only
--    (value_text, value_num, value_entity); add bool + the
--    unit/jurisdiction/valid-time/rank/extraction columns the six mapped
--    families need (FIELD_MAP §3). The uniqueness widens to cover the
--    numeric/entity/bool value columns so differently-typed qualifier values
--    cannot collide on the COALESCE('') bucket.
ALTER TABLE claim_qualifier
  ADD COLUMN value_bool    boolean,
  ADD COLUMN unit          text,
  ADD COLUMN jurisdiction  text,
  ADD COLUMN valid_from    date,
  ADD COLUMN valid_to      date,
  ADD COLUMN extraction_id uuid REFERENCES extraction(extraction_id),
  ADD COLUMN rank          text NOT NULL DEFAULT 'normal';

DROP INDEX claim_qualifier_pk;
CREATE UNIQUE INDEX claim_qualifier_pk ON claim_qualifier
  (claim_id, qualifier_id,
   COALESCE(value_text, ''), COALESCE(value_num::text, ''),
   COALESCE(value_entity::text, ''), COALESCE(value_bool::text, ''));

-- 4. evidence_capture: honest capture classification. 'legacy' is the column
--    default — the classes that are PROVABLE are backfilled, and whatever is
--    unverifiable stays 'legacy' rather than being guessed:
--      synthetic = the connector sink's per-(source,genre,run) placeholder
--                  (its artifact's stable_locator is sig:connector:*);
--      actual    = a byte-bearing capture with a real content digest.
ALTER TABLE evidence_capture
  ADD COLUMN capture_classification text NOT NULL DEFAULT 'legacy';
ALTER TABLE evidence_capture
  ADD CONSTRAINT evidence_capture_classification_ck
  CHECK (capture_classification IN ('actual','synthetic','legacy'));

UPDATE evidence_capture ec
   SET capture_classification = 'synthetic'
  FROM evidence_artifact ea
 WHERE ec.artifact_id = ea.artifact_id
   AND ea.stable_locator LIKE 'sig:connector:%'
   AND ec.capture_classification = 'legacy';

UPDATE evidence_capture
   SET capture_classification = 'actual'
 WHERE capture_classification = 'legacy'
   AND byte_size > 0 AND content_digest IS NOT NULL;

-- 4b. ingest_run_capture: the mark names the immutable OCFL occurrence its
--     capture bytes were committed under, so a resume or replay binds THAT
--     version rather than whatever a re-fetch moved head to (SIG-TRUST-002).
ALTER TABLE ingest_run_capture
  ADD COLUMN ocfl_object_id text,
  ADD COLUMN ocfl_version   text;

-- 5. assertion_quarantine: the append-only fail-closed landing for rejected
--    assertions (SIG-TRUST-001: unknown predicate/type combinations fail closed
--    or enter an explicit quarantine). Append-only + immutable: a review that
--    resolves a row lands as a NEW claim assertion, never a row rewrite.
CREATE TABLE assertion_quarantine (
  quarantine_id  uuid PRIMARY KEY DEFAULT uuidv7(),
  run_id         uuid NOT NULL REFERENCES ingest_run(run_id),
  received_at    timestamptz NOT NULL DEFAULT clock_timestamp(),
  reason         text NOT NULL,
  connector_name text NOT NULL,
  source_id      text,
  subject_ref    text,
  predicate_id   text,
  payload        jsonb NOT NULL,
  payload_digest text NOT NULL UNIQUE,
  CHECK (reason IN ('bad_digest','unknown_predicate','unknown_object_type',
                    'unknown_value_kind','missing_capture_binding',
                    'unsupported_locator','extractor_failure',
                    'version_mismatch','missing_required_field',
                    'unknown_qualifier'))
);

CREATE FUNCTION assertion_quarantine_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'assertion_quarantine rows are immutable (append-only, P1-P3); append a NEW row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER assertion_quarantine_immutable
  BEFORE UPDATE OR DELETE ON assertion_quarantine
  FOR EACH ROW EXECUTE FUNCTION assertion_quarantine_immutable();

-- 5b. The evidence/qualifier links are recorded facts too (P1-P3): re-sightings
--     append NEW rows, a correction never rewrites a link.
CREATE FUNCTION claim_evidence_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'claim_evidence/claim_qualifier rows are immutable (append-only, P1-P3); append a NEW row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER claim_evidence_immutable
  BEFORE UPDATE OR DELETE ON claim_evidence
  FOR EACH ROW EXECUTE FUNCTION claim_evidence_immutable();
CREATE TRIGGER claim_qualifier_immutable
  BEFORE UPDATE OR DELETE ON claim_qualifier
  FOR EACH ROW EXECUTE FUNCTION claim_evidence_immutable();

-- 6. Privileges. claim_evidence/claim_qualifier are written by the claim sink:
--    make the ingest role's INSERT right explicit (it owns every spine write).
--    Quarantine holds unreviewed rejected content: auditable by the internal
--    elevated roles, NEVER granted to the public read/export surfaces —
--    "auditable without exposing unreviewed content".
GRANT SELECT, INSERT ON claim_evidence, claim_qualifier TO sig_ingest;
GRANT INSERT ON assertion_quarantine TO sig_ingest;
GRANT SELECT ON assertion_quarantine TO sig_read_restricted, sig_read_sealed;
REVOKE DELETE ON claim_evidence, claim_qualifier, assertion_quarantine FROM PUBLIC;
REVOKE DELETE ON assertion_quarantine
  FROM sig_ingest, sig_read_public, sig_read_restricted, sig_read_sealed, sig_export;

COMMIT;
