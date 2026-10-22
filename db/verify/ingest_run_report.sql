-- Verify eleutheria-claims:ingest_run_report on pg

BEGIN;

-- Table exists with the J3 §3.3 item 1 + K10 §18 shape (every field typed;
-- missing evidence stays NULL, never a fabricated 0 — the NOT NULLs are only
-- the row's own identity: link_basis, clock_basis, recorded_at).
SELECT report_id, run_id, source_id, link_basis, clock_basis, started_at,
       fetches, records_emitted, duration_seconds,
       robots_outcomes, refusal_classes, rate_limit_events, disappearances,
       document_outcomes, quota_reached, budget_reached,
       error_class, per_fetch, backfilled_from, recorded_at
FROM ingest_run_report WHERE FALSE;

-- link_basis: the closed C-14 vocabulary — 'live', the two backfill bases,
-- 'unmatched:<reason>', 'repo_record'. Off-vocabulary rows must not land.
-- clock_basis: db / run_row / git_only only.
DO $$
BEGIN
    BEGIN
        INSERT INTO ingest_run_report (link_basis, clock_basis)
        VALUES ('guessed', 'run_row');
        RAISE EXCEPTION 'link_basis CHECK did not fire';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;
    BEGIN
        INSERT INTO ingest_run_report (link_basis, clock_basis)
        VALUES ('live', 'wallclock');
        RAISE EXCEPTION 'clock_basis CHECK did not fire';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;
END $$;

-- error_class: the S-4 closed vocabulary only (validated in code too, via
-- policy.transparency.valid_error_class — mirrored here so the column
-- contract is visible in schema).
DO $$
BEGIN
    BEGIN
        INSERT INTO ingest_run_report (link_basis, clock_basis, error_class)
        VALUES ('live', 'db', 'made_up_error');
        RAISE EXCEPTION 'error_class CHECK did not fire';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;
END $$;

-- Unmatched rows carry a reason suffix and may have run_id NULL (C-14);
-- a repo record row carries link_basis 'repo_record' + clock_basis 'git_only'.
INSERT INTO ingest_run_report (link_basis, clock_basis)
VALUES ('unmatched:no_candidate_run', 'run_row');
INSERT INTO ingest_run_report (link_basis, clock_basis, backfilled_from)
VALUES ('repo_record', 'git_only', 'repo:docs/build/reports/live_runs/x.json');

-- The two partial unique keys exist (live row per run; one row per
-- backfilled source URI — the +0 guarantee).
SELECT 1 FROM pg_indexes
 WHERE tablename = 'ingest_run_report'
   AND indexname = 'ingest_run_report_live_key'
   AND indexdef LIKE '%WHERE%backfilled_from IS NULL%';
SELECT 1 FROM pg_indexes
 WHERE tablename = 'ingest_run_report'
   AND indexname = 'ingest_run_report_backfill_key'
   AND indexdef LIKE '%WHERE%backfilled_from IS NOT NULL%';

-- The immutability trigger is attached.
SELECT 1 FROM pg_trigger
 WHERE tgname = 'ingest_run_report_immutable'
   AND tgrelid = 'ingest_run_report'::regclass;

-- No granted role holds UPDATE/DELETE on the table.
SELECT 1
FROM information_schema.role_table_grants
WHERE table_name = 'ingest_run_report'
  AND grantee <> CURRENT_USER
  AND privilege_type IN ('UPDATE', 'DELETE')
HAVING COUNT(*) = 0;

ROLLBACK;
