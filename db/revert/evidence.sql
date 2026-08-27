-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:evidence from pg
BEGIN;
DROP TABLE IF EXISTS extraction;
ALTER TABLE rights_record DROP CONSTRAINT IF EXISTS rights_terms_capture_fk;
DROP TABLE IF EXISTS evidence_capture;
DROP TABLE IF EXISTS evidence_artifact;
COMMIT;
