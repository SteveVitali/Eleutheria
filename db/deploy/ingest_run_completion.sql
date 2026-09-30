-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:ingest_run_completion to pg
-- P31.2 / ADR-109: how an ingest execution FINISHED, recorded append-only.
--
-- `ingest_run` (rights_sources_lineage) carries a nullable `finished_at` and a
-- `status` defaulting to 'running', but nothing in the repo ever closes a run —
-- and closing it would be an UPDATE, which the spine forbids. Completion is
-- therefore a NEW row in this table, appended once when an execution ends
-- (success, quota stop, or a failure the process survives). `ingest_run` itself is
-- never updated; a SIGKILLed execution appends nothing and honestly stays
-- "no completion".
--
-- Two writers:
--   * the live pipeline (`connectors.pipeline.run` -> `PgClaimSink.record_completion`):
--     `backfilled_from` NULL, `finished_at` set by the DB clock, counts exact,
--     `run_record_uri` = the WORM `gs://…/ops/runs/…` object the scheduled
--     wrapper writes for the same execution. At most ONE live completion per run.
--   * the one-shot WORM backfill (`sig-ops backfill-run-completions`):
--     `backfilled_from` = the gs:// run row it read (unique, so a re-run is +0),
--     `finished_at` = that row's recorded started_at + duration_seconds — never a
--     guessed time; `claims_inserted` counted from the spine inside that window.
--
-- `recorded_at` is when the row was appended (DB clock) — for a backfilled row that
-- is later than `finished_at`, which is the point: a belief-pinned read (§9.4)
-- does not see a completion before it was recorded.

BEGIN;

CREATE TABLE ingest_run_completion (
  completion_id      uuid PRIMARY KEY DEFAULT uuidv7(),
  run_id             uuid NOT NULL REFERENCES ingest_run(run_id),
  source_id          text,            -- the source the execution ran (freshness is per source)
  status             text NOT NULL,
  finished_at        timestamptz NOT NULL DEFAULT clock_timestamp(),
  claims_considered  integer,         -- NULL when not recorded (backfill)
  claims_inserted    integer NOT NULL,
  claims_duplicate   integer,         -- NULL when not recorded (backfill)
  run_record_uri     text,            -- the WORM run row for this execution, when one exists
  backfilled_from    text,            -- the WORM run row a backfilled completion was read from
  detail             text,            -- short, secret-free (an exception CLASS, never its message)
  recorded_at        timestamptz NOT NULL DEFAULT clock_timestamp(),
  CHECK (status IN ('ok', 'partial', 'quota_reached', 'failed')),
  CHECK (claims_inserted >= 0),
  CHECK (claims_considered IS NULL OR claims_considered >= 0),
  CHECK (claims_duplicate IS NULL OR claims_duplicate >= 0),
  CHECK (backfilled_from IS NULL OR backfilled_from LIKE 'gs://%')
);

-- One live completion per execution; one backfilled completion per WORM run row
-- (the backfill's +0 re-run key). A legacy run that folded many executions
-- together (the pre-P31.2 reuse-by-key) may carry several backfilled rows.
CREATE UNIQUE INDEX ingest_run_completion_live_key
  ON ingest_run_completion (run_id) WHERE backfilled_from IS NULL;
CREATE UNIQUE INDEX ingest_run_completion_backfill_key
  ON ingest_run_completion (backfilled_from) WHERE backfilled_from IS NOT NULL;
-- The per-source freshness read (latest completion per source).
CREATE INDEX ingest_run_completion_source_idx
  ON ingest_run_completion (source_id, finished_at DESC);

-- Append-only enforcement: a completion is a recorded fact; it is never edited or
-- deleted (P1–P3). A different outcome would be a different execution's row.
CREATE FUNCTION ingest_run_completion_immutable() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION
    'ingest_run_completion rows are immutable (append-only, P1-P3); append a NEW row instead';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ingest_run_completion_immutable
  BEFORE UPDATE OR DELETE ON ingest_run_completion
  FOR EACH ROW EXECUTE FUNCTION ingest_run_completion_immutable();

GRANT SELECT, INSERT ON ingest_run_completion TO sig_ingest;
GRANT SELECT ON ingest_run_completion
  TO sig_read_public, sig_read_restricted, sig_read_sealed, sig_export;
-- The WORM backfill runs as the least-privilege materialize role (ADR-103): it may
-- append completions and nothing else here — no UPDATE/DELETE/TRUNCATE.
GRANT INSERT ON ingest_run_completion TO sig_materialize;

COMMIT;
