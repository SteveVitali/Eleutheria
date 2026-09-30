-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:ingest_run_capture to pg
-- P31.4 / ADR-111: per-target capture marks, so a restarted execution RESUMES.
--
-- Since P31.4 the live pipeline commits each capture's claims as soon as the capture
-- is processed (one `assert_claims` call per capture; each call is a commit boundary,
-- ADR-110). This table records, append-only, what an execution had durably done for
-- each fetch target:
--
--   * state 'captured' — the target's bytes were fetched and stored in the capture
--     store (content multihash `capture_digest`). A resumed execution re-processes
--     them FROM THE STORED CAPTURE (no re-fetch) when the store still holds them.
--   * state 'flushed'  — every claim the capture yielded has committed to the spine.
--     A resumed execution skips the target entirely, but still counts it as seen:
--     its capture digest and its record count go into the resumed execution's report,
--     so disappearance detection and the run's digests equal an uninterrupted run's.
--
-- A mark belongs to one execution (`run_id`, P31.2's per-execution run identity,
-- ADR-109). Executions of the same LOGICAL run share `ingest_run.parameters ->>
-- 'logical_run'` (source + cadence window); a restarted execution reads the marks of
-- the executions of its logical run that started after the last one that completed.
-- A fresh cadence window is a new logical run and never skips anything.
--
-- `records` is the number of records the capture's post-capture stages emitted
-- (claims and non-claim records alike), so a resumed run reports the same emitted
-- count as an uninterrupted one without re-walking a skipped page.

BEGIN;

CREATE TABLE ingest_run_capture (
  run_id          uuid NOT NULL REFERENCES ingest_run(run_id),
  target_key      text NOT NULL,           -- the fetch target (its URL; else its id)
  state           text NOT NULL,
  capture_digest  text NOT NULL,           -- the connectors' content multihash
  source_uri      text NOT NULL,
  media_type      text NOT NULL,
  byte_size       bigint NOT NULL,
  retrieved_at    timestamptz,
  records         integer,                 -- emitted records (flushed marks only)
  recorded_at     timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (run_id, target_key, state),
  CHECK (state IN ('captured', 'flushed')),
  CHECK (byte_size >= 0),
  CHECK (records IS NULL OR records >= 0),
  CHECK ((state = 'flushed') = (records IS NOT NULL))
);

-- Append-only enforcement: a mark is a recorded fact (P1-P3).
CREATE FUNCTION ingest_run_capture_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'ingest_run_capture rows are immutable (append-only, P1-P3); append a NEW row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ingest_run_capture_immutable
  BEFORE UPDATE OR DELETE ON ingest_run_capture
  FOR EACH ROW EXECUTE FUNCTION ingest_run_capture_immutable();

GRANT SELECT, INSERT ON ingest_run_capture TO sig_ingest;
GRANT SELECT ON ingest_run_capture TO sig_read_restricted, sig_read_sealed, sig_export;

COMMIT;
