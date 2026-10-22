-- SPDX-License-Identifier: Apache-2.0
-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
-- carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
-- Deploy sig:ingest_run_report_upstream_recon to pg
-- requires: ingest_run_report

BEGIN;

-- ## P35.34 / SIG-CONF-009 — the upstream-count reconciliation the check reads
--
-- `upstream_reconciliation` carries the `sig.upstream-reconciliation/1` object:
-- `{"schema", "pairs": [{target, upstream_count, count_basis, subjects_held,
-- subjects_basis, difference_pct, classification, reason, skipped}]}` — one
-- pair per fetch-evidenced comparison plus a run-level pair. Values are typed
-- honesty tokens, never guesses: `upstream_count` is an int or the recorded
-- token "not_exposed"; `subjects_held` an int or "not_recorded";
-- `classification` is `in_range` | `explained` | `unexplained` |
-- `not_evaluable`; `reason` is drawn from the closed vocabulary
-- (filtered|withheld_rows|pagination_cap|upstream_misreport|other:<class>).
-- The >1 % unexplained fail rule binds where the P34.44a/b check machinery
-- (GQ-19) reads it — this column is the recording surface, not the
-- enforcement.
--
-- NULL means not_recorded (pre-P35.34 rows and runs that never executed
-- fetches) — a missing value is never zero-shaped.
--
-- The column inherits the table's append-only trigger and grants
-- (table-level SELECT/INSERT covers new columns); it is deliberately NOT on
-- the v_transparency_run explicit-column list — it is check machinery input,
-- not a public field.

ALTER TABLE ingest_run_report
    ADD COLUMN upstream_reconciliation jsonb;

ALTER TABLE ingest_run_report
    ADD CONSTRAINT ingest_run_report_upstream_recon_object
    CHECK (upstream_reconciliation IS NULL
           OR jsonb_typeof(upstream_reconciliation) = 'object');

COMMIT;
