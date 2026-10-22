-- Deploy eleutheria-claims:ingest_run_report to pg
-- requires: rights_sources_lineage
-- requires: ingest_run_completion
-- requires: ingest_run_capture

BEGIN;

-- ## P35.32 / J3 §3.3 item 1 + K10 §18 (SIG-TRANSP-036 as also-requirement; the
-- ## SIG stays routed to its owner P36.46 — this ticket delivers its engine
-- ## field, not the SIG's full verdict)
--
-- Append-only report layer for ingestion: one `ingest_run_report` row per
-- execution, in addition to the shared `ingest_run` bookkeeping. The run
-- stays the shared unit of ingest; the report records WHAT THE EXECUTION
-- SAW — fetches, robots per host, refusal classes, per-fetch scrub — every
-- value typed, nothing fabricated. Every report row carries `link_basis`
-- (how the row links to an `ingest_run`) + `clock_basis` (where its clock
-- came from) so history is unioned WITHOUT conflating shared-run values
-- with individual executions (K10 C-13: a shared pre-P31.2 run's values are
-- never presented as the execution's own — `not_recorded`-shaped where the
-- run row cannot evidence them; C-14: a row exists per execution including
-- executions with `run_id NULL` and the repo-pinned live-run records).
--
-- Columns mirror J3 §3.3 item 1 + K10 §18: fetches, robots per host,
-- refusal classes, per-fetch scrubbed shape (PKG-12: host+status+bytes;
-- full URLs only where the S-6 lane allows — the writers store hosts and
-- never secrets), document outcomes, quota/budget, `error_class` (the S-4
-- closed vocabulary, enforced in-code by `policy.transparency`), and
-- `recorded_at` (the append timestamp — `clock_basis` marks where the
-- execution's own clock came from).
--
-- `started_at` is the execution's own start clock and stays NULL whenever
-- the row cannot evidence one (`backfill:sole-candidate` rows whose run row
-- recorded no start, and any link that would borrow a shared run's clock —
-- K10 C-13: the shared run's started_at is NOT the execution's own).
--
-- The table is append-only: a BEFORE trigger refuses UPDATE and DELETE
-- outright; `recorded_at` is written by the DB on insert (clock_timestamp),
-- never by callers. The report feeds the scheduled transparency report and
-- public dashboards; quarantine contributes COUNT-BY-REASON only — the
-- private payload never enters this table.
--
-- `backfilled_from` mirrors `ingest_run_completion.backfilled_from`: the
-- WORM URI of the source record ('gs://…/runs/<source>/<date>/<ts>.json')
-- for run-row backfill rows, 'repo:<path>' for repo-pinned live-run
-- records (C-14), or NULL for live-written rows. The partial unique index
-- makes every backfill re-run a +0 no-op.

CREATE TABLE IF NOT EXISTS ingest_run_report (
    report_id          uuid PRIMARY KEY DEFAULT uuidv7(),
    -- nullable: unmatched executions and refused (non-executed) rows carry
    -- run_id NULL (C-14 — the row exists per execution regardless of link).
    run_id             uuid REFERENCES ingest_run(run_id),
    source_id          text,
    -- 'live' · 'repo_record' · 'backfill:claims-in-window' ·
    -- 'backfill:sole-candidate' · 'unmatched:<reason>' (P31.2 classes)
    link_basis         text NOT NULL,
    -- 'db' (an ingest_run own clock) · 'run_row' (WORM row own clock) ·
    -- 'git_only' (repo-pinned record)
    clock_basis        text NOT NULL,
    -- the execution's own start; NULL = not_recorded, never a borrowed
    -- shared-run clock (K10 C-13)
    started_at         timestamptz,
    fetches            integer,
    records_emitted    integer,
    duration_seconds   double precision,
    -- {host: {obeyed|disallowed|unavailable|disregarded: n}} — per-host
    -- robots verdicts folded to the K10/J3 closed vocabulary
    robots_outcomes    jsonb,
    -- {class: n} — refusal classes: connector FetchRecord refusals and
    -- politeness refusals, plus assertion_quarantine COUNT-BY-REASON (the
    -- quarantine payload never enters this table — K10 §18)
    refusal_classes    jsonb,
    rate_limit_events  integer,
    disappearances     integer,
    -- {outcome: n} — connector document outcomes
    document_outcomes  jsonb,
    quota_reached      boolean,
    budget_reached     boolean,
    -- the P35.31 S-4 closed vocabulary (policy.transparency): 'db_connection_lost',
    -- 'storage_error', 'read_timeout', 'constraint_violation',
    -- 'robots_unavailable', 'robots_disallow', 'politeness_refusal',
    -- 'quota_reached', 'content_drift', 'disappearance',
    -- 'unclassified_error', 'upstream_http_<code>'; NULL = not_recorded
    error_class        text,
    -- PKG-12 per-fetch rows: {host,status,bytes} (+ 'url' only where the S-6
    -- lane allows full URLs); hosts are S-4-scrubbed, secrets stripped
    per_fetch          jsonb,
    backfilled_from    text,
    -- DB-set append timestamp — the report row's own clock, distinct from
    -- the execution clock in started_at/clock_basis
    recorded_at        timestamptz NOT NULL DEFAULT clock_timestamp(),

    CHECK (link_basis IN ('live', 'repo_record', 'backfill:claims-in-window',
                          'backfill:sole-candidate')
           OR link_basis LIKE 'unmatched:%'),
    CHECK (clock_basis IN ('db', 'run_row', 'git_only')),
    CHECK (fetches IS NULL OR fetches >= 0),
    CHECK (records_emitted IS NULL OR records_emitted >= 0),
    CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CHECK (rate_limit_events IS NULL OR rate_limit_events >= 0),
    CHECK (disappearances IS NULL OR disappearances >= 0),
    CHECK (robots_outcomes IS NULL OR jsonb_typeof(robots_outcomes) = 'object'),
    CHECK (refusal_classes IS NULL OR jsonb_typeof(refusal_classes) = 'object'),
    CHECK (document_outcomes IS NULL OR jsonb_typeof(document_outcomes) = 'object'),
    CHECK (per_fetch IS NULL OR jsonb_typeof(per_fetch) = 'array'),
    CHECK (backfilled_from IS NULL
           OR backfilled_from LIKE 'gs://%' OR backfilled_from LIKE 'repo:%'),
    -- error_class: the S-4 closed vocabulary — NULL means "not evidenced",
    -- never an off-vocabulary string. Validated in code by
    -- policy.transparency.valid_error_class; mirrored here so the column
    -- contract is visible in the schema.
    CHECK (error_class IS NULL
           OR error_class IN ('db_connection_lost', 'storage_error',
                              'read_timeout', 'constraint_violation',
                              'robots_unavailable', 'robots_disallow',
                              'politeness_refusal', 'quota_reached',
                              'content_drift', 'disappearance',
                              'unclassified_error')
           OR error_class ~ '^upstream_http_[1-5][0-9][0-9]$')
);

-- Live rows: one report per ingest_run (NULL run_id rows — refusals and
-- unmatched executions — do not contend on this key).
CREATE UNIQUE INDEX IF NOT EXISTS ingest_run_report_live_key
    ON ingest_run_report (run_id)
    WHERE backfilled_from IS NULL AND run_id IS NOT NULL;

-- Backfilled rows: one report per source record URI; ON CONFLICT DO NOTHING
-- makes every re-run +0.
CREATE UNIQUE INDEX IF NOT EXISTS ingest_run_report_backfill_key
    ON ingest_run_report (backfilled_from)
    WHERE backfilled_from IS NOT NULL;

CREATE INDEX IF NOT EXISTS ingest_run_report_source_idx
    ON ingest_run_report (source_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS ingest_run_report_run_idx
    ON ingest_run_report (run_id)
    WHERE run_id IS NOT NULL;

-- Immutability: this table is audit history, append-only. No UPDATE, no
-- DELETE — a wrong row is corrected by a new superseding report row or left
-- as history, never rewritten.
CREATE OR REPLACE FUNCTION ingest_run_report_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'ingest_run_report is append-only: % not allowed', TG_OP;
END; $$;

DROP TRIGGER IF EXISTS ingest_run_report_immutable ON ingest_run_report;
CREATE TRIGGER ingest_run_report_immutable
    BEFORE UPDATE OR DELETE ON ingest_run_report
    FOR EACH ROW EXECUTE FUNCTION ingest_run_report_immutable();

-- Privileges mirror ingest_run_completion (P31.2) with one deliberate
-- narrowing: sig_read_public does NOT read this table. ingest_run_completion
-- is on the §37 public read surface; ingest_run_report is not — the
-- execution-keyed public history is P36.46's surface (row 389), published
-- through the v_transparency_* views of rows 311/313, never a raw table
-- grant ahead of them. Reads therefore run on the restricted/sealed/export
-- roles (the reconciliation + scheduled-transparency-report readers); writes
-- are append-only — sig_ingest inserts live rows, and the WORM/repo backfill
-- runs as the least-privilege sig_materialize role (ADR-103) with INSERT and
-- nothing else here — no UPDATE/DELETE/TRUNCATE. The schema-owner role always
-- retains full table privileges on its own objects — nothing revokes those —
-- but no *granted* role receives UPDATE/DELETE, and the trigger above blocks
-- those operations no matter the role.
REVOKE UPDATE, DELETE ON ingest_run_report FROM PUBLIC;
GRANT SELECT, INSERT ON ingest_run_report TO sig_ingest;
GRANT SELECT ON ingest_run_report
  TO sig_read_restricted, sig_read_sealed, sig_export;
GRANT INSERT ON ingest_run_report TO sig_materialize;

COMMIT;
