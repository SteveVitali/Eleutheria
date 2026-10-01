-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:camera_site_human_decisions from pg
--
-- Restores the P30.2b CHECK vocabulary. The revert REFUSES loudly if any row
-- uses a widened value (a human-decision row can never be silently re-labelled
-- — P1–P3): such a state means the wiring has already produced decisions and
-- reverting is a recorded operator action, not a clean rollback.

BEGIN;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM camera_site_match
     WHERE disposition IN ('human_accept', 'human_reject', 'refused')
        OR relation_type = 'cannot_link'
  ) THEN
    RAISE EXCEPTION
      'camera_site_human_decisions revert refused: human-decision rows exist '
      '(append-only history; reverting the CHECK would falsify them)';
  END IF;
END $$;

REVOKE SELECT ON review_decision FROM sig_materialize;

DO $$
DECLARE
  con_name text;
BEGIN
  SELECT conname INTO con_name FROM pg_constraint
   WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
     AND pg_get_constraintdef(oid) LIKE '%disposition = ANY%';
  IF con_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE camera_site_match DROP CONSTRAINT %I', con_name);
  END IF;
END $$;
ALTER TABLE camera_site_match
  ADD CONSTRAINT camera_site_match_disposition_check
  CHECK (disposition IN ('auto_write', 'proposed'));

DO $$
DECLARE
  con_name text;
BEGIN
  SELECT conname INTO con_name FROM pg_constraint
   WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
     AND pg_get_constraintdef(oid) LIKE '%relation_type%';
  IF con_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE camera_site_match DROP CONSTRAINT %I', con_name);
  END IF;
END $$;
ALTER TABLE camera_site_match
  ADD CONSTRAINT camera_site_match_relation_type_check
  CHECK (relation_type = 'same_as');

COMMIT;
