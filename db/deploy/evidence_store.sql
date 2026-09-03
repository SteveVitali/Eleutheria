-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:evidence_store to pg
-- §17 (P02.2, ADR-023): the byte-level evidence-store contract on top of the L0
-- evidence tables P02.1 shaped. Adds the deduplicated blob registry (SIG-EVID-004),
-- the (content_digest, source_uri) uniqueness the spec mandates, the redaction
-- version guard (SIG-EVID-011), and the audited access log with its own retention
-- (SIG-EVID-012). The OCFL bytes themselves live in object storage (evidence.ocfl).

BEGIN;

-- SIG-EVID-004: content-addressed, deduplicated blob registry. The unique
-- (blob_digest, source_uri) is the dedup key — a portal page fetched daily that
-- has not changed is ONE stored blob, referenced by N capture rows.
CREATE TABLE evidence_blob (
  blob_digest    text NOT NULL,             -- multihash, base32 (SIG-EVID-002)
  source_uri     text NOT NULL,
  byte_size      bigint NOT NULL,
  digest_blake3  text,                       -- fixity, hex BLAKE3 (SIG-EVID-003)
  ocfl_object_id text NOT NULL,              -- the source-stream OCFL object
  ocfl_version   text NOT NULL,              -- the OCFL version that first stored it
  first_seen_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (blob_digest, source_uri)      -- SIG-EVID-004 uniqueness
);

-- The byte-level columns P02.2 owns on the capture row.
ALTER TABLE evidence_capture ADD COLUMN source_uri        text;
ALTER TABLE evidence_capture ADD COLUMN blob_digest       text;
ALTER TABLE evidence_capture ADD COLUMN redaction_version text;

-- SIG-EVID-004: a re-fetch of unchanged bytes is ONE blob but N capture rows, so
-- (content_digest, artifact_id) must NOT be unique. Dedup lives on evidence_blob.
ALTER TABLE evidence_capture
  DROP CONSTRAINT IF EXISTS evidence_capture_content_digest_artifact_id_key;

-- Each capture points at its deduplicated blob (nullable: additive; a capture
-- with no bytes recorded yet simply has no blob reference).
ALTER TABLE evidence_capture
  ADD CONSTRAINT evidence_capture_blob_fk
  FOREIGN KEY (blob_digest, source_uri) REFERENCES evidence_blob (blob_digest, source_uri);

-- SIG-EVID-011: a redaction records its method AND version, so a mis-redaction is
-- identifiable and re-doable.
ALTER TABLE evidence_capture
  ADD CONSTRAINT evidence_capture_redaction_versioned
  CHECK (NOT redaction_applied OR redaction_version IS NOT NULL);

-- SIG-EVID-012: audited access to restricted/sealed bytes, with its OWN retention
-- so it never becomes a surveillance record of SIG's own researchers (§44.5).
CREATE TABLE evidence_access_log (
  access_id            uuid PRIMARY KEY DEFAULT uuidv7(),
  capture_id           uuid NOT NULL REFERENCES evidence_capture (capture_id),
  requester            text NOT NULL,
  purpose              text NOT NULL,
  storage_tier         text NOT NULL,
  accessed_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
  retention_expires_at timestamptz NOT NULL,          -- SIG-EVID-012 retention limit
  CHECK (storage_tier IN ('restricted','sealed'))     -- public access is not audited
);
COMMENT ON TABLE evidence_access_log IS
  'SIG-EVID-012: requester/purpose/timestamp for restricted+sealed byte access; '
  'retained then purged so it is not a surveillance record of SIG staff (§44.5).';

-- Grants. Readers of restricted/sealed bytes WRITE the audit trail; the retention
-- sweep reads and purges expired rows (the access log is not append-only — it is
-- meant to be purged, unlike the evidence tables).
GRANT SELECT, INSERT ON evidence_blob TO sig_ingest;
GRANT SELECT ON evidence_blob TO sig_read_public, sig_read_restricted, sig_read_sealed, sig_export;
GRANT INSERT ON evidence_access_log TO sig_ingest, sig_read_restricted, sig_read_sealed;
GRANT SELECT, DELETE ON evidence_access_log TO sig_export;

COMMIT;
