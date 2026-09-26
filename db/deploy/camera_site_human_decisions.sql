-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:camera_site_human_decisions to pg
-- P31.11 (DEEPEN.7, ADR-R9-HUMANER): the camera-site run now CONSUMES the
-- append-only `review_decision` rows for `er_match:camera_site*` items. The
-- decision vocabulary widens, all still append-only (INSERT ... ON CONFLICT
-- DO NOTHING; no UPDATE/DELETE anywhere):
--
--   * disposition 'human_accept' — a human `accept` applied as a same-device
--     edge (decided_by = the curator); clusters alongside `auto_write` edges.
--   * disposition 'human_reject' + relation_type 'cannot_link' — a human
--     `reject`, recorded as a hard cannot-link; the pair never clusters.
--   * disposition 'refused' — a human accept that would violate a hard
--     constraint (same-source without duplicate-target evidence, an
--     incompatible device class, the span/size bounds): RECORDED and refused,
--     never silently applied (disposition_reason names the constraint).
--   * 'proposed' is unchanged (now also `human_conflict` — two curators in
--     disagreement stay proposed and are routed back for adjudication).
--
-- `sig_materialize` gains SELECT on review_decision so the materializer can
-- read the human verdicts (it already had INSERT from `review_campaign`).

BEGIN;

DO $$
DECLARE
  con_name text;
BEGIN
  -- PG renders the column CHECK as `disposition = ANY (ARRAY[...])`.
  SELECT conname INTO con_name FROM pg_constraint
   WHERE conrelid = 'camera_site_match'::regclass AND contype = 'c'
     AND pg_get_constraintdef(oid) LIKE '%disposition = ANY%';
  IF con_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE camera_site_match DROP CONSTRAINT %I', con_name);
  END IF;
END $$;
ALTER TABLE camera_site_match
  ADD CONSTRAINT camera_site_match_disposition_check
  CHECK (disposition IN ('auto_write', 'proposed', 'human_accept', 'human_reject', 'refused'));

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

GRANT SELECT ON review_decision TO sig_materialize;

COMMIT;
