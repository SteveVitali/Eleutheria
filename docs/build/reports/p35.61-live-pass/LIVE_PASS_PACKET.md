# P35.61 — live-pass return packet (prepared, not executed)

Ticket `338_P35.61__round10-live-pass-audit-apply-freeze.md` /
R11-ACT-14 — the owed production half of `D-R10-LIVE-1` and finding
F-522's owner row. **Status: `prepared_not_executed` — no hosted
audit ran, no plan exists yet, no production write was attempted and
no snapshot was created.** All three live legs are queued (L1, L3) or
reached-and-stopped (L2); the re-run prompt below re-dispatches the
pass when the preconditions hold.

Machine-readable twin: `LIVE_PASS_PACKET.json`
(`live-pass-return-pass/1`).

## Leg dispositions at 2026-10-24T18:20Z

- **L1 — hosted audit + plan (read-only): queued.** The never-mutate
  bands were not active at the run clock (Saturday ~18:20Z, outside
  the preferred weekday 14:00–20:00Z slot — a note, not a refusal,
  for a read-only leg), but the audit's hosted access is still
  absent — no exec host, no login, no mounted capture root:
  `live:P34.46` (the Round-10 schema deploy + roll
  carrying `audit_login`, `recovery_apply` and the `sig_recovery`
  role) is still queued, `live:P34.43` L1/L2 (exec host,
  `sig_audit`/`sig_recovery` logins) are still queued — read-only
  checks at this record found the `sig-quality-probe-rt` runtime SA
  and both login secrets absent (NOT_FOUND) — and the runtime
  environment (`SIG_GCP_PROJECT`, `SIG_EXEC_IMAGE`,
  `SIG_HOSTED_DSN`, the login passwords) is unset in this shell.
- **L2 — operator plan review (1–4 h): pause reached.** Nothing was
  reviewed because the queued L1 produced no plan yet; after L1 runs,
  the operator reviews the recorded plan and fixes the apply scope —
  the apply never starts on silence.
- **L3 — bounded apply + `+0` re-run + rematerialize + freeze:
  queued.** No verbatim in-ticket go has been given and none is ever
  pre-authorised for this row (GATE-G4 §4 never-list); the queued
  hosted write path (`sig_recovery`, `sig_recovery_login`) does not
  exist yet, no AR-2 restore point has been taken for this row, and
  the run clock is outside the preferred weekday slot.

## Re-run

**Re-run prompt (queued only — nothing in this row executed; no
probe-run/1 record exists):**
`implement-spec spec=docs/tickets/338_P35.61__round10-live-pass-audit-apply-freeze.md
live_verification=true` — queued, not executed.

Next valid slot: the next weekday 14:00–20:00Z once every
precondition holds — earliest Monday 2026-10-26T14:00Z, and only if
the queued live rows (`live:P34.46` + its 48 h soak, `live:P34.43`
L1+L2) have run by then.

## Ordered command sequence (G2 §4 step 2 verbatim)

1. Queued hosted read-only audit — `uv run sig-ops evidence-audit --dsn
   $SIG_HOSTED_DSN --capture-dir <mounted OCFL root> --seed
   <recorded> --sample <recorded> --out <audit-out>/`
2. Recovery plan — `uv run sig-ops recovery-plan --audit
   <audit-out>/audit_report.json --out <audit-out>/`
3. Operator review pause (1–4 h) — the operator reviews the plan and
   fixes the apply scope.
4. Bounded apply, pilot first — `uv run sig-ops recovery-apply --dsn
   $SIG_HOSTED_DSN --plan <audit-out>/recovery_plan.json --audit
   <audit-out>/audit_report.json --apply --execution-id <recorded>
   --authority <operator-auth-ref> --capture-dir <mounted OCFL root>
   --verify-rerun --rematerialize --out <apply-out>/` with
   `--max-actions` and a `--batches`/`--claims` selection inside the
   pilot ceiling.
5. Approved batches — the same command per approved batch.
6. Unpublished freeze — `uv run sig-ops recovery-freeze --dsn
   $SIG_HOSTED_DSN --apply-report <apply-out>/APPLY_REPORT.json
   --plan <audit-out>/recovery_plan.json --audit
   <audit-out>/audit_report.json --out <apply-out>/`
7. Close — `implement-spec
   spec=docs/tickets/183_P32.22__bounded-recovery-and-activation.md
   live_verification=true` (the OPERATIONAL_READINESS (f3) pass).

On the ACT-13 exec host steps 1–6 run as `sig-exec-{audit,recovery}
-<stamp>` one-off Cloud Run jobs rendered by `sig-ops exec-host run
--purpose {audit,recovery}` (`ops/exec_host.toml`) with a read-only
captures mount; the `--dsn` form above is the contract's command
surface.

## Ceilings (byte figures recorded — AR-9 absolute)

- Pilot batch: ≤ 500 claims and ≤ 50 MiB (52,428,800 B); a first
  failure after 50 writes pauses the pass.
- Approved batch: ≤ 10,000 assertions, ≤ 250 MiB distinct bytes
  (262,144,000 B), 1 worker.
- Storage headroom (fractions → bytes on the G1-recorded 15 GB =
  15,000,000,000 B allocation; autoresize is on with limit 0, so the
  leg re-reads `bytesUsed`/`bytesAllocated` at run time and
  recomputes the same fractions on the read allocation): warn at
  0.7 → 10,500,000,000 B used; a disposition is required at 0.85 →
  12,750,000,000 B; each batch keeps ≥ 0.2 free → ≥ 3,000,000,000 B
  free before it starts. A batch never starts below its free floor.
- The exec-host job itself: CPU 1, memory 512 Mi, timeout 1800 s,
  max-retries 0.

## Verify (what a green pass looks like)

The queued audit's hosted population digest reconciles with the plan's
before any write; applied actions are a digest-for-digest subset of
the plan; receipts are unique (exactly-once across restarts — a
restart mid-apply reconciles `already_applied`); the `+0` re-run
applies nothing; no fetch path is used (a missing byte can only
skip; nothing is reconstructed as old evidence); rematerialize is
dependency-ordered and a `+0` no-op on re-run; the snapshot records
`frozen_unpublished`; the disk before/after read is recorded at the
leg.

## Explicit reservations

- `D-R10-LIVE-1` stays OPEN; its production-recovery half stays owed
  until the packet executes — the post-evaluation candidate
  half stays owed through the human-evaluation path (P35.62).
- No source-rights flip, no publication, no HG gate tick, no human
  label; the snapshot is never published by this row.
- The bounded apply is never pre-authorised: it runs only under the
  operator's verbatim in-ticket go plus a recorded `--authority`
  scope.
- Credentials and secrets stay environment-only (HG-09); the project
  id and bucket names are never literal in any tracked file; the
  OCFL captures mount is read-only by IAM condition and mount flag
  (SIG-STORE-048).
- A defect found mid-pass pauses and records — machinery is never
  patched during the leg; the disk before/after read, the
  restore-point id and a `date -u` stamp are recorded in the run
  ledger.
- The candidate P35.61a/b split flag stays with C13 — nothing
  pre-splits.
