# ADR-141 — The bounded recovery apply: exactly-once receipts, the sig_recovery role, and ordered rematerialization (P32.22)

- Date: 2026-09-27
- Status: accepted (engineering; `live_verification=false` — fixture/test-PG only; the production execution is the operator-gated live pass under `D-R10-LIVE-1`, still OPEN)
- Ticket: P32.22 (Round 10 / S1, row 183; requirement SIG-TRUST-008; annotates `D-R10-LIVE-1`)
- Base: `devin/p32-21-acquisition-pilot` tip (PR chain of P32.21 / ADR-140)

## Context

P32.6 (ADR-125) shipped `evidence-audit/1` + `recovery-plan/1`: a read-only audit and a
**dry-run-only** planner that emits append-only action proposals keyed by deterministic
`action_digest`s. P32.22 owns the second half the ticket chain demanded — *executing* a
bounded selected scope of those proposals, rematerializing the read surface in dependency
order, and freezing an unpublished repaired-input snapshot + audit preview for
**HUMAN-H4** (the final post-evaluation release candidate is P32.23a's, not this stage's).

The design had to answer four questions without weakening any of the spine's invariants:

1. **Exactly-once across interruption.** A bounded apply can die mid-batch; a restart
   must continue — never duplicate a repair, a disposition, or a binding.
2. **Honesty about conflicts.** `bind_verified_capture` proposals name
   `(claim_id, capture_id, establishes)` triples the append-only PK may already hold
   (the audit only verifies already-bound establishing captures) — the apply must not
   fabricate a row nor `UPDATE` the immutable link.
3. **Least privilege.** The applier needs the narrowest possible write surface: the
   §16.6 correction pair (claim INSERT + the single permitted `sys_period` close),
   typed `claim_evidence` bindings, disposition rows, the apply's own `ingest_run`,
   the marker table, and the adjudicator-entity mint — and nothing else (no capture/
   extraction/blob/source writes, no `UPDATE`/`DELETE` anywhere).
4. **No refetch path.** Missing bytes must never cause a network fetch — the privilege
   surface and the code must both make it impossible, not merely unused.

## Decision

### `recovery_application` — the applied-receipt barrier

The sqitch change `recovery_apply` adds `recovery_application`: one **append-only**
row per executed action, `UNIQUE(action_digest)` as the exactly-once barrier — the same
shape `intake.application.operation_id` gives the P32.16a bridge. Each action executes
in **one transaction**: a per-action `pg_advisory_xact_lock` serializes concurrent
appliers, the marker check runs, the canonical write lands, and the receipt commits
atomically. A crash before commit leaves nothing; a crash after commit reconciles to
the committed receipt (`already_applied`). Feeding recorded digests back into
`recovery-plan --applied` yields a **+0** re-plan — resume is a property of the data,
not of a checkpoint file the process could lose.

`outcome` is honest about +0 cases: `applied` (new canonical rows) or
`conflict_existing` (claim_evidence's `(claim_id, capture_id, role)` PK deduplicated an
already-bound capture — recorded with the existing row's typedness in `detail`,
never fabricated, never retried into an `UPDATE`).

### `sig_recovery` — least-privilege applier role

`sig_recovery` (NOLOGIN NOBYPASSRLS) receives: INSERT on `claim`, `claim_evidence`,
`recovery_application`, `publication_disposition`, `ingest_run`, and the guarded entity
tables (`entity`/`entity_identifier`/`entity_identity_key` for the §11.3 adjudicator
mint); `UPDATE (sys_period)` on `claim` — the *only* update the append-only trigger
permits and the sole one the §16.6 correction pair needs; sequence usage for the
disposition identity; and membership in `sig_read_sealed` so claim RLS (FORCED) admits
repairs at any tier the audit cited. Membership is granted to the deploying login only
(operator grants extend it deliberately).

### `recovery-apply/1` — the DB write path (`db.recovery_apply`)

`PgRecoveryApplier.apply_action` wraps one action in one transaction and dispatches on
kind:

- `record_disposition` → `db.dispositions.record_disposition` under the shared
  `policy.eligibility.new_disposition` validator. The plan's placeholder authority is
  **replaced** by the operator authorization the apply was invoked under; the audit's
  basis survives in `rationale`.
- `bind_verified_capture` → `INSERT … ON CONFLICT DO NOTHING`, gated on the capture row
  existing (a dangling capture refuses `capture_missing` — no row is ever invented).
- `repair_claim` → the §16.6 correction pair, mirroring `intake_apply`: close the old
  claim's open `sys_period` (a concurrent close makes it a no-row update → `stale_record`,
  never a double close), INSERT the corrected claim (`revises_claim` +
  `correction_reason` + adjudicator `asserted_by` minted via `resolve_identities`), and
  re-bind the SAME captures to the new assertion. `revised_fields` is a fail-closed
  allowlist (`value_geom` deliberately out of scope) and every revised string passes the
  Part VIII refusal screen before persistence.

### `recovery-apply-report/1` — the ops orchestration (`ops.recovery_apply`)

- **Fail-closed scope reconciliation**: plan must be `recovery-plan/1` over the SAME
  population digest as the cited audit, `exceeds_ceiling` false, and every selected
  action `proposed` — else `ApplyScopeError` before a single write.
- **Bounded selection**: operator filters (batch/kind/claim) + `max_actions` abort
  threshold, deterministic digest order, one worker.
- **Bind re-verification**: a bind action executes only after the probe re-reads the
  pinned occurrence and the recorded digest verifies — `None`/`False` is an explicit
  `skipped` result. There is no fetch or transport code in either module; missing bytes
  cannot trigger a refetch *because no path exists to one*.
- **Recorded accounting**: before/after inventories scoped to the selected claims,
  per-kind `result_writes`, wall-clock, batch-bounds re-check, and a `verify_rerun`
  pass that re-executes the selection and asserts `already_applied` + zero delta.
- **Rematerialization** runs the shared temporal/publication materializers in the
  recorded dependency order (resolution → camera-sites → edges → contradictions →
  coverage → accountability), each in its own transaction, every step's counts and
  timing recorded.

### `sig.repaired-snapshot/1` — the frozen HUMAN-H4 frame

`freeze_snapshot` re-loads the SAME claim population from the repaired spine, re-runs
the audit under the recorded parameters, and freezes a snapshot that is explicitly
`frozen_unpublished` + `provisional_preview` + `not_a_release_candidate`. It pins the
code/schema/semantic-rules identities and the applied-write digests, records the
actual source identities, and embeds the post-apply audit digest + findings — the frame
HUMAN-H4 evaluates, not a release artifact.

`PROVISIONAL_VS_SHADOW` records that the eval-confidence evaluator remains `shadow`
(`applied: []`) while the explicitly PROVISIONAL production rules stay active — the
ticket's "provisional rules vs new shadow eligibility" report; `recovery-apply-return-pass/1`
keeps `D-R10-LIVE-1` OPEN as a prepared, unexecuted operator contract.

## Consequences

- The applier can do exactly what the plan allows and nothing else — at the privilege
  layer, the code layer, and the check layer.
- A restart is a reconcile, not a re-write: receipt + plan digests make idempotence
  provable rather than assumed.
- The frozen snapshot gives HUMAN-H4 a byte-stable frame; nothing public, gated, or
  human can be confused into thinking a release candidate exists — it does not.
- The production execution inherits the identical contract (same commands in
  `LIVE_RETURN_PASS.json`); only the DSN/probe/authority change.

## Alternatives considered

- **Checkpoint-file resume** (write a cursor file between actions): rejected — a file
  outside the database can be lost, diverges from the write state, and duplicates the
  bookkeeping the receipt already is; `UNIQUE(action_digest)` makes the database itself
  the checkpoint.
- **In-place binding "upgrade"** (`UPDATE claim_evidence` to a typed status): rejected —
  claim_evidence is append-only-immutable; a new typed binding is an INSERT (or an
  honest `conflict_existing` when the PK already holds the triple).
- **Batch-scoped transactions** (commit per batch): rejected — a mid-batch crash would
  leave a half-applied batch whose digest-level state is ambiguous; per-action receipts
  make the resume unit the action.
- **Auto-fetch missing bytes**: rejected categorically — a new fetch is never the old
  capture (ADR-125); absence must remain a finding.

## Revisit trigger

- The live return pass (the production execution of `LIVE_RETURN_PASS.json`) exercises a
  scope or failure class the fixture cannot express — e.g. a receipt collision under two
  operator appliers, batch-boundary aborts over >10 000 actions, or a rematerializer that
  must run as `sig_materialize` under hosted grants.
- `claim_evidence`/`claim` schema additions that change the repair's allowed
  `revised_fields` or the binding conflict surface.
- HUMAN-H4 / P32.22a surfacing a snapshot-content requirement the `sig.repaired-snapshot/1`
  frame does not carry.
