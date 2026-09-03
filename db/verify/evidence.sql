-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify sig:evidence on pg
SELECT artifact_id FROM evidence_artifact WHERE false;
SELECT capture_id FROM evidence_capture WHERE false;
SELECT extraction_id FROM extraction WHERE false;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='rights_terms_capture_fk') THEN
    RAISE EXCEPTION 'rights_terms_capture_fk missing'; END IF;
END $$;
