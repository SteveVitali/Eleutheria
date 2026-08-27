-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:access_control from pg
BEGIN;
DROP POLICY IF EXISTS evidence_capture_tier_ceiling ON evidence_capture;
DROP POLICY IF EXISTS evidence_capture_base ON evidence_capture;
ALTER TABLE evidence_capture NO FORCE ROW LEVEL SECURITY;
ALTER TABLE evidence_capture DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS evidence_artifact_tier_ceiling ON evidence_artifact;
DROP POLICY IF EXISTS evidence_artifact_base ON evidence_artifact;
ALTER TABLE evidence_artifact NO FORCE ROW LEVEL SECURITY;
ALTER TABLE evidence_artifact DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS claim_tier_ceiling ON claim;
DROP POLICY IF EXISTS claim_base ON claim;
ALTER TABLE claim NO FORCE ROW LEVEL SECURITY;
ALTER TABLE claim DISABLE ROW LEVEL SECURITY;
DROP FUNCTION IF EXISTS sig_visible_max_tier();
DROP OWNED BY sig_read_public, sig_read_restricted, sig_read_sealed, sig_export, sig_ingest;
DROP ROLE IF EXISTS sig_ingest;
DROP ROLE IF EXISTS sig_export;
DROP ROLE IF EXISTS sig_read_sealed;
DROP ROLE IF EXISTS sig_read_restricted;
DROP ROLE IF EXISTS sig_read_public;
COMMIT;
