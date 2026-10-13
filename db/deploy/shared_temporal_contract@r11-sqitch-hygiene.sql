-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:shared_temporal_contract to pg
--
-- P32.4 / ADR-123 (SIG-TRUST-005): the shared bitemporal occurrence-selection
-- contract, one rule every reader shares (db.occurrences is the pure twin):
--
--   1. eligible_occurrence(claim_id, belief) — the SQL twin of
--      db.occurrences.select_occurrence: the LATEST *eligible* establishing
--      occurrence of a claim — role='establishes' only (a corroborating or
--      contradicting link never re-dates the claim), bound_at <= belief (a
--      later capture/replay/correction can never reach backward into a frozen
--      belief read), ordered by the real temporal field retrieved_at DESC with
--      capture_id as the deterministic last-resort tie (an id is never a clock).
--
--   2. camera_site_execution — the per-EXECUTION completion/result reference.
--      camera_site_run is keyed by the full input digest, so a re-run over an
--      unchanged spine reuses the existing run row (+0, by design) — which left
--      no record that a new execution completed, and a later A→B→A reversion
--      left readers unable to say "the LATEST EXECUTION ended on result A".
--      Every execution appends one execution row (execution_id idempotent), so
--      the latest completed execution governs current selection. Deploy
--      backfills one execution per existing run (honest completed_at).
--
--   3. spine_watermark — the trigger-maintained materialized watermark closing
--      D-P31.1-1. The API's annotation/shaping watermark used to COUNT six
--      spine tables under the annotation lock per request (~10 s measured on
--      the hosted spine). Now each watched relation carries a statement-level
--      trigger that bumps its facet row (count, closed count, latest instant,
--      monotone bump) in the SAME transaction — an O(facets) read that is
--      snapshot-consistent by construction and never stale. The watched set is
--      deliberately a superset of everything the cached compute-on-read paths
--      read (claims, the evidence chain, qualifiers, rights, run/completion
--      state, entities, persisted annotations) plus every completed-
--      materialization relation: an unnecessary facet bump costs one recompute;
--      a missed relation is a stale serve.
--
-- Additive and append-only throughout: new tables/function/triggers; no
-- table/column/existing-row changes. The trigger function is SECURITY DEFINER
-- for the same reason close_superseded_resolutions is: it only bumps its own
-- bookkeeping row, and the INSERT-only writer roles must not need UPDATE.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. The shared eligible-occurrence function (SQL twin of the pure contract).
-- ---------------------------------------------------------------------------

CREATE FUNCTION eligible_occurrence(p_claim_id uuid, p_belief timestamptz)
RETURNS TABLE (
  capture_id    uuid,
  source_id     text,
  artifact_type text,
  retrieved_at  timestamptz,
  bound_at      timestamptz
) AS $$
  SELECT ce.capture_id, ea.source_id, ea.artifact_type, ec.retrieved_at, ce.bound_at
    FROM claim_evidence ce
    JOIN evidence_capture ec ON ec.capture_id = ce.capture_id
    JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
   WHERE ce.claim_id = p_claim_id
     AND ce.role = 'establishes'
     -- p_belief NULL = "current knowledge" (all bindings recorded so far).
     AND ce.bound_at <= COALESCE(p_belief, clock_timestamp())
   ORDER BY ec.retrieved_at DESC NULLS LAST, ce.capture_id ASC
   LIMIT 1
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION eligible_occurrence(uuid, timestamptz) IS
  'P32.4/ADR-123 temporal-read/1: the latest ELIGIBLE establishing occurrence '
  'of a claim — role=establishes, bound_at <= belief (NULL belief = current '
  'knowledge), retrieved_at DESC (capture_id deterministic tie only, never a '
  'timestamp). The pure twin is db.occurrences.select_occurrence; fixture/PG '
  'parity is tested.';

-- The index/query-plan budget for the shared read: every consumer's lateral /
-- CTE selects per-claim *establishing* bindings with a bound_at predicate — a
-- partial index makes the eligible-occurrence lookup bounded on representative
-- data instead of scanning a claim's whole evidence edge set.
CREATE INDEX claim_evidence_establishing_idx
  ON claim_evidence (claim_id, bound_at) WHERE role = 'establishes';

-- ---------------------------------------------------------------------------
-- 2. camera_site_execution: one append-only completion ref per EXECUTION.
-- ---------------------------------------------------------------------------

CREATE TABLE camera_site_execution (
  execution_id  uuid PRIMARY KEY,
  run_key       text NOT NULL REFERENCES camera_site_run(run_key),
  completed_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
  input_count   integer NOT NULL CHECK (input_count >= 0),  -- the execution's M
  summary       jsonb NOT NULL
);

COMMENT ON TABLE camera_site_execution IS
  'P32.4/ADR-123: one append-only completion/result reference per camera-site '
  'EXECUTION. camera_site_run is keyed by input digest so a re-run over an '
  'unchanged spine reuses the row (+0); this table still records that the '
  'execution completed, so readers select the run the LATEST COMPLETED '
  'EXECUTION produced (an A→B→A reversion shows a new completion naming A). '
  'execution_id is the idempotency key: retrying the same execution appends +0.';

-- One honest backfilled execution per existing run: the run's own completion.
INSERT INTO camera_site_execution (execution_id, run_key, completed_at, input_count, summary)
SELECT gen_random_uuid(), run_key, completed_at, observation_count, summary
  FROM camera_site_run;

GRANT SELECT ON camera_site_execution TO sig_read_public, sig_export;
GRANT INSERT ON camera_site_execution TO sig_materialize;

-- The latest-execution probe (read_resolved_site_runs LIMIT 1 by completed_at).
CREATE INDEX camera_site_execution_completed_idx
  ON camera_site_execution (completed_at DESC);

-- ---------------------------------------------------------------------------
-- 3. spine_watermark: the bounded, trigger-maintained freshness marker.
-- ---------------------------------------------------------------------------

CREATE TABLE spine_watermark (
  facet          text PRIMARY KEY,
  row_count      bigint NOT NULL,
  closed_count   bigint NOT NULL,
  latest_instant timestamptz,
  bump           bigint NOT NULL DEFAULT 0,
  bumped_at      timestamptz NOT NULL DEFAULT clock_timestamp()
);

COMMENT ON TABLE spine_watermark IS
  'P32.4/ADR-123 (D-P31.1-1): trigger-maintained spine freshness. One row per '
  'watched relation facet, bumped by statement-level triggers on '
  'INSERT/UPDATE/TRUNCATE. Readers get an O(facets), snapshot-consistent, '
  'never-stale watermark instead of counting the claim spine per request.';

-- Seed from the deployed state so the first read is exactly consistent.
INSERT INTO spine_watermark (facet, row_count, closed_count, latest_instant) VALUES
  ('claim',                 (SELECT count(*) FROM claim),
                            (SELECT count(*) FROM claim WHERE upper(sys_period) IS NOT NULL),
                            (SELECT max(lower(sys_period)) FROM claim)),
  ('claim_evidence',        (SELECT count(*) FROM claim_evidence), 0,
                            (SELECT max(bound_at) FROM claim_evidence)),
  ('claim_qualifier',       (SELECT count(*) FROM claim_qualifier), 0, NULL),
  ('evidence_capture',      (SELECT count(*) FROM evidence_capture), 0,
                            (SELECT max(retrieved_at) FROM evidence_capture)),
  ('evidence_artifact',     (SELECT count(*) FROM evidence_artifact), 0, NULL),
  ('evidence_blob',         (SELECT count(*) FROM evidence_blob), 0, NULL),
  ('extraction',            (SELECT count(*) FROM extraction), 0, NULL),
  ('ingest_run',            (SELECT count(*) FROM ingest_run), 0,
                            (SELECT max(COALESCE(finished_at, started_at)) FROM ingest_run)),
  ('ingest_run_capture',    (SELECT count(*) FROM ingest_run_capture), 0,
                            (SELECT max(recorded_at) FROM ingest_run_capture)),
  ('ingest_run_completion', (SELECT count(*) FROM ingest_run_completion), 0,
                            (SELECT max(recorded_at) FROM ingest_run_completion)),
  ('rights_record',         (SELECT count(*) FROM rights_record), 0,
                            (SELECT max(reviewed_at) FROM rights_record)),
  ('rights_decision',       (SELECT count(*) FROM rights_decision), 0,
                            (SELECT max(decided_at) FROM rights_decision)),
  ('source_registry',       (SELECT count(*) FROM source_registry), 0,
                            (SELECT max(last_verified_at) FROM source_registry)),
  ('entity',                (SELECT count(*) FROM entity), 0,
                            (SELECT max(created_at) FROM entity)),
  ('entity_identifier',     (SELECT count(*) FROM entity_identifier), 0, NULL),
  ('organization',          (SELECT count(*) FROM organization), 0, NULL),
  ('organization_relation', (SELECT count(*) FROM organization_relation),
                            (SELECT count(*) FROM organization_relation
                              WHERE upper(sys_period) IS NOT NULL),
                            (SELECT max(lower(sys_period)) FROM organization_relation)),
  ('relationship',          (SELECT count(*) FROM relationship), 0, NULL),
  ('resolution',            (SELECT count(*) FROM resolution),
                            (SELECT count(*) FROM resolution WHERE upper(sys_period) IS NOT NULL),
                            (SELECT max(lower(sys_period)) FROM resolution)),
  ('contradiction',         (SELECT count(*) FROM contradiction), 0,
                            (SELECT max(resolved_at) FROM contradiction)),
  ('coverage_record',       (SELECT count(*) FROM coverage_record), 0,
                            (SELECT max(searched_at) FROM coverage_record)),
  ('research_task',         (SELECT count(*) FROM research_task), 0,
                            (SELECT max(generated_at) FROM research_task)),
  ('review_item',           (SELECT count(*) FROM review_item), 0,
                            (SELECT max(created_at) FROM review_item)),
  ('review_decision',       (SELECT count(*) FROM review_decision), 0,
                            (SELECT max(decided_at) FROM review_decision)),
  ('camera_site_run',       (SELECT count(*) FROM camera_site_run), 0,
                            (SELECT max(completed_at) FROM camera_site_run)),
  ('camera_site_match',     (SELECT count(*) FROM camera_site_match), 0, NULL),
  ('camera_site_execution', (SELECT count(*) FROM camera_site_execution), 0,
                            (SELECT max(completed_at) FROM camera_site_execution));

-- The generic statement-level bump. TG_ARGV[0] = the per-facet "latest instant"
-- expression evaluated over new_rows (or 'NULL'); TG_ARGV[1] = the "closed"
-- predicate (default false). SECURITY DEFINER so INSERT-only writer roles bump
-- the facet without UPDATE privilege on the bookkeeping table (same pattern as
-- close_superseded_resolutions). Column names come from this deploy script —
-- never caller input.
CREATE FUNCTION spine_watermark_touch() RETURNS trigger AS $$
DECLARE
  v_inst   text := TG_ARGV[0];
  v_closed text := TG_ARGV[1];
BEGIN
  IF TG_OP = 'TRUNCATE' THEN
    UPDATE spine_watermark
       SET row_count = 0, closed_count = 0, latest_instant = NULL,
           bump = bump + 1, bumped_at = clock_timestamp()
     WHERE facet = TG_TABLE_NAME;
    RETURN NULL;
  END IF;
  IF TG_OP = 'UPDATE' THEN
    -- The ONLY permitted mutation is closing a sys_period's upper bound (the
    -- append-only guard); an UPDATE adds no row, so row_count is untouched and
    -- closed_count takes the (new closed - old closed) delta.
    EXECUTE format($f$
      UPDATE spine_watermark w
         SET closed_count = w.closed_count + n.closed,
             bump = w.bump + 1,
             bumped_at = clock_timestamp()
        FROM (SELECT (SELECT count(*) FROM new_rows WHERE COALESCE(%s, false))
                   - (SELECT count(*) FROM old_rows WHERE COALESCE(%s, false)) AS closed) n
       WHERE w.facet = %L
      $f$, v_closed, v_closed, TG_TABLE_NAME);
    RETURN NULL;
  END IF;
  -- INSERT: add the new rows and their closed share (normally 0 on insert).
  EXECUTE format($f$
    UPDATE spine_watermark w
       SET row_count = w.row_count + n.cnt,
           closed_count = w.closed_count + n.closed,
           latest_instant = GREATEST(w.latest_instant, n.mx),
           bump = w.bump + 1,
           bumped_at = clock_timestamp()
      FROM (SELECT (SELECT count(*) FROM new_rows) AS cnt,
                   (SELECT count(*) FROM new_rows WHERE COALESCE(%s, false)) AS closed,
                   (SELECT max((%s)::timestamptz) FROM new_rows) AS mx) n
     WHERE w.facet = %L
    $f$, v_closed, v_inst, TG_TABLE_NAME);
  RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public;

-- Three statement-level triggers per watched relation (INSERT / UPDATE /
-- TRUNCATE): transition tables cannot be declared on a multi-event trigger,
-- and the row-count and closed-count deltas differ per event anyway.
-- Statement level: a 10k-row chunk insert pays one UPDATE, not 10k.
DO $$
DECLARE
  facet record;
BEGIN
  FOR facet IN
    SELECT * FROM (VALUES
      ('claim',                 'lower(sys_period)', 'upper(sys_period) IS NOT NULL'),
      ('claim_evidence',        'bound_at',          'false'),
      ('claim_qualifier',       'NULL',              'false'),
      ('evidence_capture',      'retrieved_at',      'false'),
      ('evidence_artifact',     'NULL',              'false'),
      ('evidence_blob',         'NULL',              'false'),
      ('extraction',            'NULL',              'false'),
      ('ingest_run',            'COALESCE(finished_at, started_at)', 'false'),
      ('ingest_run_capture',    'recorded_at',       'false'),
      ('ingest_run_completion', 'recorded_at',       'false'),
      ('rights_record',         'reviewed_at',       'false'),
      ('rights_decision',       'decided_at',        'false'),
      ('source_registry',       'last_verified_at',  'false'),
      ('entity',                'created_at',        'false'),
      ('entity_identifier',     'NULL',              'false'),
      ('organization',          'NULL',              'false'),
      ('organization_relation', 'lower(sys_period)', 'upper(sys_period) IS NOT NULL'),
      ('relationship',          'NULL',              'false'),
      ('resolution',            'lower(sys_period)', 'upper(sys_period) IS NOT NULL'),
      ('contradiction',         'resolved_at',       'false'),
      ('coverage_record',       'searched_at',       'false'),
      ('research_task',         'generated_at',      'false'),
      ('review_item',           'created_at',        'false'),
      ('review_decision',       'decided_at',        'false'),
      ('camera_site_run',       'completed_at',      'false'),
      ('camera_site_match',     'NULL',              'false'),
      ('camera_site_execution', 'completed_at',      'false')
    ) AS t(name, inst, closed)
  LOOP
    EXECUTE format(
      'CREATE TRIGGER spine_watermark_insert
         AFTER INSERT ON %I
         REFERENCING NEW TABLE AS new_rows
         FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch(%L, %L)',
      facet.name, facet.inst, facet.closed);
    EXECUTE format(
      'CREATE TRIGGER spine_watermark_update
         AFTER UPDATE ON %I
         REFERENCING NEW TABLE AS new_rows OLD TABLE AS old_rows
         FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch(%L, %L)',
      facet.name, facet.inst, facet.closed);
    EXECUTE format(
      'CREATE TRIGGER spine_watermark_truncate
         AFTER TRUNCATE ON %I
         FOR EACH STATEMENT EXECUTE FUNCTION spine_watermark_touch(''NULL'', ''false'')',
      facet.name);
  END LOOP;
END
$$;

GRANT SELECT ON spine_watermark TO sig_read_public, sig_export;
-- No INSERT/UPDATE/DELETE grants: only the SECURITY DEFINER trigger writes it.

COMMIT;
