# ADR-234 — Manual-acquisition registry + the disappearance event-column writer (P37.5b)

- Date: 2026-11-06
- Status: accepted
- Ticket: P37.5b (Round 11 / P37, row 425 — R11-DEBT-03; serves SIG-INGEST-008,
  SIG-INGEST-009, SIG-INGEST-010; F2a-verdicts.md §5 group 10,
  F5-eng-debt.md PKG-12)
- Base: `r11/P37.5a-ingestion-hardening-unwired-function-scan`
- Related: SIG-EVID-013/014 (§17.6 — the event columns this row writes),
  ADR-233 (the split-a half), SIG-TASK-007 (the dedup contract the task write
  shares with P29.2)

## Context

P37.5b carries the F2a group-10 remainder — the manual-acquisition
record/runbook (SIG-INGEST-008) and "disappearances persisted as append-only
events and research tasks" (SIG-INGEST-009/010, the catalog's
`disappeared_observed_at has a writer` shape) — plus the P37.5a unwired-scan's
`capability-half` flock_portal change-detection findings routed here. Three
decisions needed recording:

1. *How a manual dependency is modelled.* SIG-INGEST-008 requires manual
   dependencies be "modelled as such, with a documented human procedure
   recording DOI, version, and checksum" and that "the build MUST NOT assume
   they are automatically fetchable". The model could have been a sources.toml
   flag or a dedicated record.
2. *What the writer writes.* The artifact event lives on two columns
   (`capture_status`, `disappeared_observed_at`) designed for exactly this
   UPDATE (C.3: "an EVENT, never a delete") — but `sig_ingest` held no UPDATE
   grant at all, so the writer had no permission surface; and whether a
   re-observation may overwrite the first recorded disappearance needed a
   stated semantics.
3. *Where the portal change feed lives.* `detect_portal_changes` /
   `diff_portal_snapshots` / `portal_capture` / `is_poll_due` are pure halves
   needing a driver and a persisted feed.

## Decision

1. **`sig.manual-acquisitions/1` is a dedicated registry**
   (`connectors/data/manual_acquisitions.toml`) + `connectors.manual_acquisition`
   — not a sources.toml flag. A source's `access_method` free text declares
   the posture; the registry row models the dependency: `identifier`/`doi`,
   `version`, `sha256`, `acquired_at`, `status` (`pending`|`acquired`), the
   human `access` path and the `runbook`
   (`docs/ops/manual-acquisition.md`, the documented procedure). Both
   directions bind in `sig-connectors validate`: every manual-declared source
   has a record and every record names a manual-declared source; an
   `acquired` row missing DOI/identifier, version or checksum fails closed,
   and a `pending` row carrying acquisition provenance fails as a fabricated
   record. `sig-connectors run` refuses a registered manual dependency in
   **every** mode (exit 3 naming the runbook) — there is no fetch stage for
   the driver to run, which is what "MUST NOT assume fetchable" means
   mechanically.
2. **`tasks.disappearance_pg` is the `disappeared_observed_at` writer**, and
   the sqitch `disappearance_event_grant` change grants
   `UPDATE (capture_status, disappeared_observed_at)` on `evidence_artifact`
   to `sig_ingest` — **column-scoped**, so the append-only posture holds
   inside the grant itself (every other column and DELETE stay un-granted;
   `tests/db/test_disappearance_persist.py` proves the boundary on a real
   engine). `capture_status` tracks the latest failing status;
   `disappeared_observed_at` is **first-observation-wins** (`COALESCE`) — an
   observation, once recorded, is never erased. The research task is
   append-only + idempotent: entity-resolved subjects dedup on
   `UNIQUE (task_type, subject_id)`; unresolved subjects land subjectless
   with `trigger_kind='artifact_disappearance'` + `trigger_ref` citing the
   artifact, deduped SELECT-first. An artifact not in this spine is an honest
   `artifact_found: False`, never a crash. `disappeared_artifacts` is the
   SIG-INGEST-010 queryable read; `sig-tasks disappearances` exposes it.
3. **`connectors.portal_changes` is the change-feed driver**, and
   `sig-tasks portal-changes` is its operable surface (tasks depends on
   connectors — the driver cannot live in the downstream package).
   `portal_change_feed(previous, current, …)` emits the
   `sig.portal-changes/1` report: poll-due keyed on the upstream's declared
   snapshot (SIG-INGEST-030c), the appearance/disappearance `portal_exists`
   claims + research tasks, and the per-field `FieldChangeEvent` stream on
   shared portals. With `--dsn` the verb persists the task rows through the
   same writer; the claim rows are emitted for the claim path (a run asserts
   them — the verb never fabricates an ingest). A portal with no parseable
   snapshot date yields no field events — honestly undated data, never a
   crash or a guessed date.

## Consequences

- `sig-connectors run --source leaic_crosswalk` refuses exit 3 in all modes;
  `sig-connectors validate` fails closed on registry/source mismatches.
- `disappeared_observed_at` has a writer for the first time
  (`persist_disappearance`); the catalog AC's "replay test green" half was
  P37.5a's.
- The four routed `capability-half` findings are wired and left the
  adjudicated baseline (94 rows); `portal_slugs` joined them (the driver
  consumes it for the slug sets).
- `detect_portal_changes` / `portal_appeared_task` signatures widened to
  `date | None` — additive/back-compat — so an undated snapshot emits
  `observed_at`-absent claims, never a wall-clock claim value
  (SIG-INGEST-018).

## Alternatives

- *A sources.toml `manual = true` flag:* rejected — the flag duplicates a
  fact already declared in `access_method` and provides nowhere for the
  acquisition provenance (DOI/version/checksum) the MUST requires.
- *Task rows keyed `subject_id`-only (drop unresolved):* rejected — a
  disappearance whose subject has not resolved is exactly the case the
  research queue exists for; the trigger-pair dedup keeps it idempotent.
- *Emit-only `portal-changes` verb with no `--dsn`:* rejected — the routed
  finding says "wires it into the persisted event feed", and a feed that can
  never persist is the capability-half again.

## Revisit trigger

Revisit if a second manual-acquisition dependency shows the registry's
per-row shape too narrow (e.g. multi-artifact acquisitions needing a nested
file list), or if disappearance history needs per-event rows rather than
first-observation columns (a `disappearance_event` table would supersede the
COALESCE semantics), or if the portal feed's claim rows need a direct sink
path of their own instead of riding the next run.
