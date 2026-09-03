-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:evidence_store from pg
BEGIN;
DROP TABLE IF EXISTS evidence_access_log;
ALTER TABLE evidence_capture DROP CONSTRAINT IF EXISTS evidence_capture_blob_fk;
ALTER TABLE evidence_capture DROP CONSTRAINT IF EXISTS evidence_capture_redaction_versioned;
ALTER TABLE evidence_capture DROP COLUMN IF EXISTS redaction_version;
ALTER TABLE evidence_capture DROP COLUMN IF EXISTS blob_digest;
ALTER TABLE evidence_capture DROP COLUMN IF EXISTS source_uri;
-- Restore the original P02.1 uniqueness.
ALTER TABLE evidence_capture
  ADD CONSTRAINT evidence_capture_content_digest_artifact_id_key UNIQUE (content_digest, artifact_id);
DROP TABLE IF EXISTS evidence_blob;
COMMIT;
