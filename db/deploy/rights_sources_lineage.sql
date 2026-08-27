-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:rights_sources_lineage to pg
-- Appendix C.2: the cross-cutting RIGHTS and LINEAGE registries. Every claim
-- carries rights_id (SIG-LIC) and ingest_run_id (SIG-INGEST-015); every evidence
-- artifact names a registered source. rights_record.terms_capture_id gains its
-- FK to evidence_capture in the later `evidence` change (circular dependency).

BEGIN;

CREATE TABLE rights_record (
  rights_id            uuid PRIMARY KEY DEFAULT uuidv7(),
  spdx_expression      text NOT NULL,            -- LicenseRef-SIG-<slug> for bespoke terms
  attribution_text     text,
  redistributable      text NOT NULL,            -- yes|no|review_required|UNDETERMINED
  derivative_permitted text NOT NULL,
  terms_url            text,
  terms_capture_id     uuid,                     -- the ARCHIVED terms (SIG-LIC-002); FK added in `evidence`
  reviewed_by          text,
  reviewed_at          timestamptz,
  retrieval_date       date NOT NULL,
  CHECK (redistributable IN ('yes','no','review_required','UNDETERMINED'))
);

CREATE TABLE source_registry (
  source_id            text PRIMARY KEY,
  name                 text NOT NULL,
  source_kind          text NOT NULL,
  homepage_url         text,
  operator_org_id      uuid REFERENCES entity(entity_id),
  default_reliability  text NOT NULL REFERENCES vocab_source_reliability(code),
  reliability_provisional boolean NOT NULL DEFAULT false,
  reliability_justification text NOT NULL,       -- SIG-EPIS-014: written, reviewed on a schedule
  rights_id            uuid NOT NULL REFERENCES rights_record(rights_id),
  custody_posture      text NOT NULL,            -- MIRROR|DERIVE|REFERENCE|LINK
  compact_status       text NOT NULL,            -- SIG-INGEST-027, incl. 'no_response'
  ingestion_permitted  boolean NOT NULL DEFAULT false,   -- HARD GATE, default deny
  robots_policy        text NOT NULL,
  crawl_budget         jsonb,
  contact_channel      text,
  last_verified_at     timestamptz,
  CHECK (custody_posture IN ('MIRROR','DERIVE','REFERENCE','LINK'))
);

CREATE TABLE ingest_run (
  run_id             uuid PRIMARY KEY DEFAULT uuidv7(),
  connector_name     text NOT NULL,
  connector_version  text NOT NULL,
  code_commit        text NOT NULL,
  ruleset_version    text NOT NULL,
  vocab_version      text NOT NULL,
  parameters         jsonb NOT NULL,
  environment        jsonb NOT NULL,             -- must record LC_ALL=C, TZ=UTC (SIG-EVID-018)
  input_digests      text[] NOT NULL,
  started_at         timestamptz NOT NULL DEFAULT clock_timestamp(),
  finished_at        timestamptz,
  status             text NOT NULL DEFAULT 'running',
  is_replay          boolean NOT NULL DEFAULT false,
  shadow_mode        boolean NOT NULL DEFAULT false   -- SIG-INGEST-019
);

COMMIT;
