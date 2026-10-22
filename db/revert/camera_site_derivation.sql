-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Revert sig:camera_site_derivation from pg
--
-- Restores the pre-v3 relation vocabulary and drops the census/demotion
-- tables. The revert REFUSES loudly when widened-vocabulary rows, census
-- rows, or demotion rows exist (P1–P3: recorded decisions are append-only
-- history — reverting them would falsify the record; such a revert is a
-- recorded operator action, not a clean rollback).

BEGIN;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM camera_site_match
     WHERE relation_type IN ('derived_from', 'possible_duplicate')
  ) THEN
    RAISE EXCEPTION
      'camera_site_derivation revert refused: v3 link rows exist '
      '(append-only history; reverting the CHECK would falsify them)';
  END IF;
END $$;

REVOKE SELECT ON camera_site_census, camera_site_demotion FROM sig_export;
REVOKE SELECT, INSERT ON camera_site_census, camera_site_demotion FROM sig_materialize;

DROP TABLE camera_site_demotion;
DROP TABLE camera_site_census;

ALTER TABLE camera_site_match DROP COLUMN site_id;

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
  CHECK (relation_type IN ('same_as', 'cannot_link'));

COMMIT;
