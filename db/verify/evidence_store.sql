-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:evidence_store on pg
SELECT blob_digest, source_uri, ocfl_object_id FROM evidence_blob WHERE false;
SELECT access_id, requester, purpose, retention_expires_at FROM evidence_access_log WHERE false;
SELECT source_uri, blob_digest, redaction_version FROM evidence_capture WHERE false;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint
             WHERE conname = 'evidence_capture_content_digest_artifact_id_key') THEN
    RAISE EXCEPTION 'dedup-blocking (content_digest, artifact_id) unique still present (SIG-EVID-004)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'evidence_capture_blob_fk') THEN
    RAISE EXCEPTION 'evidence_capture_blob_fk missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'evidence_blob_pkey') THEN
    RAISE EXCEPTION 'evidence_blob (blob_digest, source_uri) primary key missing (SIG-EVID-004)';
  END IF;
END $$;
