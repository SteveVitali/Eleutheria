-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:evidence to pg
-- Appendix C.3: the L0 evidence tables. This change owns their PHYSICAL SHAPE so
-- the claim spine (extraction_id, claim_evidence.capture_id) has defined FK
-- targets. The OCFL object store and the capture pipeline are P02.2; here the
-- ocfl_* columns are recorded but nothing writes bytes.

BEGIN;

CREATE TABLE evidence_artifact (
  artifact_id        uuid PRIMARY KEY DEFAULT uuidv7(),
  source_id          text NOT NULL REFERENCES source_registry(source_id),
  url                text,
  stable_locator     text NOT NULL,
  artifact_type      text NOT NULL,
  title              text,
  publisher_org_id   uuid REFERENCES entity(entity_id),
  published_at_edtf  text,                       -- T3, EDTF (often imprecise)
  document_date_edtf text,
  acquisition_method text NOT NULL,
  records_request_id uuid,
  page_count         integer,
  primary_or_secondary text NOT NULL,
  default_reliability  text REFERENCES vocab_source_reliability(code),
  rights_id          uuid NOT NULL REFERENCES rights_record(rights_id),
  sensitivity_tier   smallint NOT NULL DEFAULT 0,
  capture_status     text NOT NULL,              -- captured|access_restricted|paywalled|
                                                 -- link_rotted|not_attempted|refused_by_policy
  disappeared_observed_at timestamptz,           -- §17.6: an EVENT, never a delete
  supersedes_artifact_id  uuid REFERENCES evidence_artifact(artifact_id),
  UNIQUE (source_id, stable_locator)
);

CREATE TABLE evidence_capture (
  capture_id         uuid PRIMARY KEY DEFAULT uuidv7(),
  artifact_id        uuid NOT NULL REFERENCES evidence_artifact(artifact_id),
  content_digest     text NOT NULL,              -- multihash, base32 (SIG-EVID-002)
  digest_blake3      text,
  byte_size          bigint NOT NULL,
  media_type         text NOT NULL,
  retrieved_at       timestamptz NOT NULL,       -- T4
  retrieved_by_run_id uuid NOT NULL REFERENCES ingest_run(run_id),
  http_status        integer,
  ocfl_object_id     text NOT NULL,
  ocfl_version       text NOT NULL,
  storage_tier       text NOT NULL DEFAULT 'public',   -- public|restricted|sealed
  capture_method     text NOT NULL,
  capture_tool_version text NOT NULL,
  request_fingerprint jsonb,
  redaction_applied  boolean NOT NULL DEFAULT false,
  redaction_method   text,
  parent_capture_id  uuid REFERENCES evidence_capture(capture_id),   -- redacted derivative
  UNIQUE (content_digest, artifact_id),
  CHECK (storage_tier IN ('public','restricted','sealed')),
  CHECK (NOT redaction_applied OR redaction_method IS NOT NULL)
);

ALTER TABLE rights_record
  ADD CONSTRAINT rights_terms_capture_fk
  FOREIGN KEY (terms_capture_id) REFERENCES evidence_capture(capture_id);

CREATE TABLE extraction (
  extraction_id      uuid PRIMARY KEY DEFAULT uuidv7(),
  capture_id         uuid NOT NULL REFERENCES evidence_capture(capture_id),
  method             text NOT NULL,
  extractor_name     text NOT NULL,
  extractor_version  text NOT NULL,
  normalizer_version text NOT NULL,
  model_id           text,                       -- REQUIRED when method='llm_assisted'
  prompt_version     text,
  parameters         jsonb NOT NULL,
  extracted_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
  run_id             uuid NOT NULL REFERENCES ingest_run(run_id),
  review_status      text NOT NULL DEFAULT 'unreviewed',
  superseded_by_extraction_id uuid REFERENCES extraction(extraction_id),
  CHECK (method <> 'llm_assisted' OR (model_id IS NOT NULL AND prompt_version IS NOT NULL))
);

COMMIT;
