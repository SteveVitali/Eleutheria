# ADR-109 — One `ingest_run` per execution; completion is an appended row

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.2 (`docs/tickets/P31.2__ingest-run-completion-and-freshness.md`) — Round 9 `HARDEN.2`. This is the design's placeholder `ADR-R9-RUNLIFE`, and it lands with that ticket.
- **Date:** 2026-09-24
- **Related:** §16 (the append-only claim spine; SIG-STORE-011/012), §32.4 (SIG-METRIC-006/007: the public freshness page), §3.1 (never assert what the evidence does not support), ADR-059 (`PgClaimSink`, content-digest idempotency), ADR-103 (the least-privilege `sig_materialize` role; heavy DB work runs next to the DB), ADR-106 (the launch surface publishes `not-recorded`), ADR-R9-RESUME (P31.4: restart = resume); deferral **D-P30.3-1**; backlog home **BL-056**.

## Context

The public `/data-freshness/` page shows `not-recorded` for every source and `degraded` status. Measured on the
hosted spine on 2026-09-24:

- all 20 `ingest_run` rows are `status = 'running'`, `finished_at` NULL;
- no code anywhere sets either column. `rights_sources_lineage.sql` defines them as nullable, with a default of
  `running`;
- `PgClaimSink._ensure_run` **reused** one row per `(connector_name, connector_version, code_commit, is_replay)`.
  Every hosted run records `code_commit = 'unknown'`, so there is one row per connector: `dot_511` holds
  2,058,714 claims written by more than 250 executions across seven days.

Closing a run would mean an `UPDATE ingest_run`. The spine has no update path (root `AGENTS.md` §5, `db/AGENTS.md`).
The executions did finish, though. Each scheduled one left a write-once run row in
`gs://<project>-sig-restricted/ops/runs/<source>/<date>/<ts>.json` (324 rows, 315 with outcome `ok`).

## Decision

1. **One `ingest_run` per execution.** Each `PgClaimSink` is one execution. It carries an `execution_id`
   (generated when the caller does not pass one) and records it in `ingest_run.parameters`, together with the
   WORM run-row URI when known. Its `environment` records `TZ`, `LC_ALL` and the Cloud Run job, execution,
   task-index and attempt variables, and only the ones that are set (SIG-EVID-018). The sink no longer looks up
   an earlier run by key. A caller that passes an explicit `execution_id` is resuming that execution and reuses
   its run. That is the hook ADR-R9-RESUME (P31.4) uses. Replays keep `is_replay`. Shadow runs assert nothing,
   so they write nothing.
2. **Completion is appended to a new table, never written onto `ingest_run`.** A new sqitch change,
   `ingest_run_completion`, adds one row per finished execution with these columns:
   - `run_id`, and `source_id` (freshness is per source, and a +0 re-run leaves no claim to join through);
   - `status`, one of:
     - `ok`: ran to the end and every target yielded;
     - `partial`: ran to the end, but some targets were recorded as disappearances, refusals or drift, or the
       request budget deferred a tail;
     - `quota_reached`: stopped at a 429 wall;
     - `failed`;
   - `finished_at`, the DB clock by default;
   - the counts (`claims_considered`, `claims_inserted`, `claims_duplicate`), `run_record_uri`,
     `backfilled_from`, a secret-free `detail`, and `recorded_at`.

   An immutability trigger refuses UPDATE and DELETE. Partial unique indexes allow **one live completion per
   run** and **one backfilled completion per WORM object**, so every write is
   `INSERT … ON CONFLICT DO NOTHING` and a repeat is +0. `ingest_run.status` and `ingest_run.finished_at` stay
   as they were inserted. They are legacy columns that nothing writes.
3. **Every live execution the process survives records its completion.** `connectors.pipeline.run` records it
   after the gate:
   - on success, the status from `completion_status(report)`;
   - on an exception, `failed` plus the exception **class** only, never its message, which can carry a URL
     with a key.

   It records through the sink's `record_completion`, the `CompletionRecorder` protocol; the in-memory sink
   records nothing. A gate refusal is not an execution and records nothing. Replay and shadow runs record
   nothing. A completion that cannot be written, for example because the connection is already dead, is logged
   and dropped: it never masks the run's outcome or exception. A SIGKILLed execution records nothing and
   honestly has no completion.
4. **The WORM run row and the completion name each other.** `scheduled-ingest` computes the run row's object
   name before the run: `run_object_uri`, a pure function of the prefix, the source and `started_at`. It passes
   that URI to the sink, and the completion's `run_record_uri` names the object that `store_run_row` then
   writes. The run row gains an additive `ingest_run_id` field.
5. **A one-shot, idempotent WORM backfill for history.** `sig-ops backfill-run-completions` runs as a
   `materialize.sh run run-completions` Cloud Run execution under `sig_materialize`, whose only new privilege is
   INSERT on this table. It reads the run rows and appends a completion labelled `backfilled_from = <gs URI>`
   only where the row proves one. `finished_at` = the row's own `started_at + duration_seconds`. The matching
   rules are deterministic:
   - connector = `fetch_record.connector`, else the registry map;
   - candidates = that connector's non-replay runs that had started by the row's finish;
   - `claims_inserted` = the claims that run established for that source inside the window
     `[started_at, finish + 1 s]`, counted in one set-based statement;
   - the row is matched when exactly one candidate holds claims in the window. When no claim is in the window, a
     normally-ended `scheduled-ingest` that handed claims to the sink is matched only if it has exactly one
     candidate: under the old reuse-by-key that run is the one it wrote through.

   Every other row is reported **unmatched with its reason**, never guessed. That covers:
   - refusals;
   - a connector whose first run started after the row;
   - a failure with no claim in its window;
   - a non-scheduled sweep with no claim in its window;
   - two overlapping windows of one source.

   A row already completed live is skipped. A re-run is +0.
6. **Freshness reads completions.** The shaper adds a per-source completion read:
   - `last_successful_run` is the latest `finished_at` among `ok`, `partial` and `quota_reached`;
   - `last_content_change` is the latest `finished_at` of a completion that **inserted > 0 claims**, so a +0
     re-run moves the success date but not the content date;
   - `status` is the latest completion's status (`ok` → ok, `failed` → failing, `partial`/`quota_reached` →
     degraded).

   The legacy `ingest_run` columns and the claims' `max(observed_at)` stay the fallback, so a pre-P31.2 spine
   and the fixture harness read as before. `not-recorded` stays the token wherever nothing is recorded. A
   belief-pinned read also hides completions recorded after the pin.

## Consequences

- The hosted spine gains real completion dates for every source whose scheduled execution the WORM record
  proves. Sources with no provable completion keep `not-recorded` and say why, in the backfill report.
- The public page shows those dates only after the next public export and republish. Operator decision Q3
  (2026-09-24): no standalone republish; the single republish is P31.16. Until then the public display
  honestly stays `not-recorded`, and D-P30.3-1's surface half is owed to P31.16.
- New completions only happen once the scheduled jobs run this code. Rolling every ingest job by pinned digest
  is owned by **P31.4**. Until that roll, hosted freshness advances only through the backfill: it can be
  re-run, +0 on rows already appended.
- Each execution now writes its own synthetic evidence capture and extraction per `(source, genre)`, because
  the capture is keyed by the run that retrieved it. That adds a few rows per source per execution instead of
  reusing one per connector. Claims are unchanged: they still de-duplicate on the content digest.
- `sig_materialize` gains INSERT on `ingest_run_completion`. It still holds no UPDATE, DELETE or TRUNCATE
  anywhere and no write on the claim spine.

## Alternatives considered

- **An `UPDATE ingest_run SET status, finished_at` at the end of each run.** This is the narrowest code
  change. Rejected: it adds the first update path to `db/`, against the append-only invariant. Recording the
  lifecycle as data (a new row) keeps every past state readable.
- **Close runs through a new "run-closed" claim on the spine.** A run is operational metadata, not a claim
  about the world. It would pollute the L1 claim set and the exports. Rejected.
- **Keep reuse-by-key and append one completion per execution to the folded run.** Freshness could work, but a
  run would still not identify an execution: its claims, captures and completion could not be told apart.
  Rejected for per-execution identity, which the ticket requires.
- **Backfill by source and date alone, without spine evidence.** Matching every `ok` row to "the connector's
  run" regardless of proof would date sources whose executions never wrote. Rejected: rows are matched only
  on claims in the window, or on the sole-candidate rule with a positive `claims_added`.
- **Use the GCS object's creation time as `finished_at`.** It is when the row was *written*, not when the run
  ended. Rejected for the row's own recorded `started_at + duration_seconds`.

## Revisit trigger

Revisit if any of these happens:

- P31.4 changes restart semantics (resume under one logical run) in a way that needs more than one live
  completion per run, or a completion per chunk;
- a scheduled execution is observed with no completion although its WORM row says it finished (the pipeline
  hook is not firing, or the connection dies before the record);
- the freshness page needs a status the four-value vocabulary cannot express (for example a
  `retired` source);
- `ingest_run.status`/`finished_at` gain any writer (they must stay legacy), or the evidence rows added per
  execution grow material (a source run far more often than weekly).
