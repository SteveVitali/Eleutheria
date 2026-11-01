-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Verify eleutheria-claims:ingest_run_report_execution_key on pg

BEGIN;

-- The report gains the run-row execution metadata (NULL-tolerant).
SELECT mode, kind FROM ingest_run_report WHERE FALSE;

-- mode is the closed run-mode vocabulary (live|replay|shadow); an
-- off-vocabulary value refuses. kind is recorded verbatim (open).
DO $$
BEGIN
    BEGIN
        INSERT INTO ingest_run_report (link_basis, clock_basis, mode)
        VALUES ('live', 'db', 'synthetic');
        RAISE EXCEPTION 'mode CHECK did not fire';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;
END $$;

-- The view carries the full allow-listed column set (the appended
-- execution surface columns included).
SELECT report_id, run_id, source_id, link_basis, clock_basis, shared_run,
       started_at, finished_at, duration_seconds, completion_status,
       claims_considered, claims_inserted, claims_duplicate,
       fetches, records_emitted, robots_outcomes, refusal_classes,
       rate_limit_events, disappearances, document_outcomes,
       quota_reached, budget_reached, error_class, per_fetch,
       connector_name, connector_version, code_commit, recorded_at,
       execution_key, mode, kind
FROM v_transparency_run WHERE FALSE;

-- sig_export keeps its read grant on the redefined view.
SELECT 1 WHERE has_table_privilege('sig_export', 'v_transparency_run', 'SELECT');

COMMIT;
