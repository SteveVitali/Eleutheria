-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:resolution_supersede to pg
-- P31.7 / ADR-R9-RESIGHT (ADR-110 D6a, ADR-104 §4 revisit): claim re-sightings are now
-- recorded — every live execution that re-asserts a stored claim appends a
-- claim_evidence link to the execution's own capture. Capture-dating reads the LATEST
-- sighting (capture_retrieved_at_latest), so a re-sighting moves the resolver's
-- observed_at for an undated claim and changes its SIG-RECON-020 input_digest.
--
-- A changed input_digest must land as a SUPERSEDING decision: insert the new envelope
-- and close the prior live row's sys_period first (§16.4 / resolution_materialize:
-- "a genuinely CHANGED input yields a new digest and a superseding decision (close
-- the prior sys_period first) — never an in-place edit"). Without this step the
-- resolution_no_overlap exclusion constraint would reject the insert: two live rows
-- for one (subject, predicate) with overlapping valid_periods are forbidden in the
-- database, not by convention.
--
-- The closure is the ONE temporal mutation the model sanctions — the decision record
-- is not edited; its belief-time interval is closed and the row stays as history
-- (closed rows remain readable; readers filter upper_inf(sys_period) for the current
-- decision). It is packaged as a SECURITY DEFINER function so the caller NEVER needs
-- UPDATE on resolution: sig_materialize keeps its INSERT-only posture
-- (materialize_role), and the function — owned by the schema owner — performs only
-- this closure and nothing else.
--
-- Guarantees of the closure itself:
--   * only LIVE rows (upper_inf(sys_period)) are touched;
--   * only AUTO decisions (decided_by='auto') are closed — a human override is never
--     superseded by a batch recompute;
--   * a live row whose input_digest already equals the batch's digest is left live
--     (the materializer's ON CONFLICT dedupes it — unchanged input stays +0);
--   * rows whose live current decision is non-auto are REPORTED as 'blocked' so the
--     materializer skips them instead of crashing on the exclusion constraint.
--
-- The function takes three parallel arrays — (subject, predicate, keep_digest) per
-- pending envelope — so a whole flush batch pays ONE round trip.

BEGIN;

CREATE FUNCTION close_superseded_resolutions(
  p_subjects uuid[], p_predicates text[], p_digests text[])
RETURNS TABLE(subject_id uuid, predicate_id text, action text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $fn$
BEGIN
  RETURN QUERY
    WITH s AS (
      SELECT * FROM unnest(p_subjects, p_predicates, p_digests)
        AS s(subject_id, predicate_id, keep_digest)
    ), live AS (
      -- Live rows whose recorded input differs from what this batch computed.
      SELECT r.subject_id, r.predicate_id, r.input_digest, r.decided_by
        FROM s JOIN public.resolution r
          ON r.subject_id = s.subject_id AND r.predicate_id = s.predicate_id
       WHERE pg_catalog.upper_inf(r.sys_period)
         AND r.input_digest IS DISTINCT FROM s.keep_digest
    ), closed AS (
      UPDATE public.resolution r
         SET sys_period = pg_catalog.tstzrange(
               pg_catalog.lower(r.sys_period), pg_catalog.clock_timestamp(), '[)')
        FROM live l
       WHERE r.subject_id = l.subject_id AND r.predicate_id = l.predicate_id
         AND l.decided_by = 'auto'
         AND pg_catalog.upper_inf(r.sys_period)
     RETURNING r.subject_id, r.predicate_id
    )
    SELECT l.subject_id, l.predicate_id,
           CASE WHEN c.subject_id IS NULL THEN 'blocked' ELSE 'closed' END
      FROM live l LEFT JOIN closed c
        ON c.subject_id = l.subject_id AND c.predicate_id = l.predicate_id;
END;
$fn$;

-- Only the materializer calls it; every other role loses the default EXECUTE.
REVOKE ALL ON FUNCTION close_superseded_resolutions(uuid[], text[], text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION close_superseded_resolutions(uuid[], text[], text[])
  TO sig_materialize;

COMMIT;
