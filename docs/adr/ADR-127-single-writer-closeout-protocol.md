# ADR-127 — The single-writer closeout protocol `closeout-op/1` and the worktree-safe validator (P32.8)

- Date: 2026-10-15
- Status: accepted (engineering; shadow mode — entry-point enforcement deferred to the operator-approved cutover on `D-R10-MEMORY-1`)
- Ticket: P32.8 (Round 10 / S6, row 168; requirement SIG-MEM-003; annotates `D-R10-MEMORY-1`)
- Base: `778a5e2` (the P32.7 closeout tip `devin/p32-7-memory-events-and-current-projection`, PR #162)

## Context

SIG-MEM-003 (§55.7) requires build-memory validation and closeout to survive
concurrent worktrees and interrupted runs. P32.1's audit demonstrated the
defects concretely:

1. **Shared-`/tmp` report collision.** The vendored validator wrote every JSON
   report to one fixed path (`/tmp/build-memory-check.json`), so two
   worktrees validating concurrently silently overwrote each other's report —
   and neither report named the input revision it checked, so a stale report
   could masquerade as fresh.
2. **Interrupted closeout could resume to a second closeout.** The closeout
   flow (implementation commit → PR → run ledger → index row → deferral
   annotation → ledger advance) is a multi-commit sequence; a crash between
   any two boundaries left no recorded operation to resume, so a retry could
   create a second PR, a second index row, or an invented closure.
3. **Stale worktrees could compare against their own files.** Expected-state
   assertions read from the caller's checkout — a stale worktree would
   "confirm" its own stale belief and close out on top of a moved chain.
4. **External skill entry points are outside the repo.** The actual worker/
   orchestrator entry points live in user-global skill directories that a
   repository change must never edit — yet closeout correctness depends on
   them adopting one protocol.

## Decision

**One operational journal under the shared git common dir, one operation
record per closeout, one validated git commit as the memory transaction —
all shadow-mode until the recorded operator cutover.**

### The `closeout-op/1` protocol (`docs/build/tools/closeout_protocol.py`)

Journal + lock live in `<git-common-dir>/sig-closeout/` — host-local
operational state every worktree of one clone shares; the committed control
files (`LEDGER.md`, `BUILD_INDEX.md`, `DEFERRALS.md`, `runs/`, `pr/`) stay
the memory.

- **Operation id first.** `prepare` defines `co-<sha256[16]>` over
  `(schema, ticket_id, attempt, implementation, base)` *before* any remote PR
  creation; the remote identity attaches afterward at `external-known`. A
  crash+retry anywhere maps to the same operation — idempotent resume, never a
  second record.
- **Expected-state preconditions.** `prepare` compares caller belief
  (`expected_next_ticket`, `expected_last_completed`, `expected_control_digest`
  over LEDGER+INDEX+DEFERRALS, `expected_chain_head`) against the
  **authoritative chain ref** — the main worktree of the shared common dir,
  never the caller's own stale files. Mismatch exits 2 naming the deltas and
  writes nothing: stale expected-state fails *without partial advancement*.
- **Scoped advisory lock.** `mkdir`-atomic under `locks/`, keyed to the stable
  build-chain id (the ledger's `manifest` field) + common dir +
  repo-relative ledger path — one lock per build chain per clone.
  **Single-host assumption:** PID liveness is only meaningful on the recorded
  host; a lock recorded elsewhere is never reclaimed here. A stale lock is
  surfaced with recovery instructions and reclaimed only by an explicit
  `--recover-stale` with a confirmed-dead recorded PID — never removed merely
  because a timeout elapsed; every recovery appends to `recoveries.jsonl`.
- **State machine:** `prepared → external-known → memory-committed →
  acknowledged`, with `aborted`/`superseded` as terminal side-states that
  preserve full history. A different implementation/attempt identity for a
  ticket that already has an in-flight or acknowledged operation is refused —
  the only accepted path is a new *recorded* attempt (`--attempt N --reason`),
  which also marks the predecessor superseded. Another ticket's
  unacknowledged operation blocks `prepare`: next dispatch is prohibited
  before acknowledgment.
- **Ambiguous remote PR creation reconciled before retry.** `external-known
  --uncertain` looks up the remote by exact head/base and adopts the found PR
  (never re-creates); attaching a second PR number to one operation is the
  duplicate-creation failure mode and is refused.
- **The validated git commit is the memory transaction.** `memory-committed`
  requires the commit to exist, to descend from `expected_chain_head`, to have
  a parent whose control digest equals the recorded expected digest
  (compare-and-swap), to touch LEDGER + BUILD_INDEX, and to pass the
  validator. Ordinary uncommitted file replacement is not atomic and is never
  a transition.
- **acknowledge** confirms the authoritative ref actually advanced
  (`lastCompleted` = this ticket, `nextTicket` moved on) before the next
  dispatch is permitted.
- **activation-check** refuses cutover (exit 6) while any legacy/event
  divergence exists — a DEFERRALS row with no anchor, an event for an unknown
  obligation, or a cell disagreeing with its event-chain head (consumed from
  `obligation_events.py`, never forked).

### The validator local patch (truthful upstream provenance)

`scripts/docs/check-build-memory.sh` is a vendored copy now marked **NO
LONGER byte-identical** (LOCAL PATCH banner in-file): the JSON report goes to
a caller-selected `--json PATH` or a unique per-run temp file; the report
(`build-memory-check/2`) records checked-input identity (`repo`, `commit`,
`dirty`, `input_digest` chaining the sha256 of every file the checker read);
diagnostics carry `{check, severity, file, obligation, evidence, message}`;
`summary.exit` records the process exit code so report severity and exit
status agree by construction. Detection logic is unchanged — output/reporting
only. The reviewed upstream-patch contract lives in
`docs/build/tools/CLOSEOUT_WRITER_PROTOCOL.md` (contract/patch/3).

### Shadow mode — enforcement deferred, not claimed

The protocol is landed, tested, and documented; the actual worker/orchestrator
entry points adopt it only at the operator-approved ticket-boundary cutover
recorded on `D-R10-MEMORY-1` (stays OPEN). The reviewed entry-point patch
contract (`contract/patch/1..3` in the protocol doc) is the integration
surface; user-global skill files are never edited from this repository.
Multi-host orchestration is explicitly out of scope: the supported runtime is
a single host where the shared common dir and PID liveness are meaningful.

## Consequences

- An interrupted closeout resumes to exactly one closeout at every boundary —
  code, PR, run-ledger, index, deferral, ledger — demonstrated by
  failure-injection tests with real git repos.
- Two concurrent validations produce two reports, each naming its input
  revision; stale expected-state and foreign-host locks fail loudly with
  recovery instructions.
- `D-R10-MEMORY-1` stays `OPEN`: enforcement begins only at the recorded
  operator-approved cutover — `activation-check` reports readiness without
  asserting it.
- The journal is host-local (not committed): `status`/`recoveries.jsonl`
  provide local audit; the committed memory remains the ledger family.
- Worker and orchestrator repair paths share one identity model: the same
  authoritative-chain check, the same lock, the same new-attempt rule.

## Alternatives considered

- **Edit the skill entry points in place.** Rejected: user-global skills are
  outside repository authority; the reviewed patch contract is the honest
  boundary.
- **Long-lived lock held across the whole closeout.** Rejected: it would make
  every normal resume collide with the previous attempt's lock; short critical
  sections + the journal's ordering rule (no unacknowledged predecessor)
  provide the same exclusion without the friction.
- **Authoritative ref = the ledger's `chainTip` field value.** Rejected:
  `chainTip` is a recorded branch name whose validity depends on the same
  files being checked; the main worktree of the shared common dir is the
  ground truth every writer's objects already share.
- **Commit the journal to build memory.** Rejected: the journal is
  operational state (PIDs, hosts, lock scope); committed memory stays the
  append-only ledger family — mixing operational locks into it would pollute
  the control state the lock protects.

## Revisit trigger

Revisit when: the operator approves the D-R10-MEMORY-1 entry-point cutover
(apply `contract/patch/1..3` and flip enforcement); a second host ever
participates in the build chain (the single-host PID-liveness assumption must
then be replaced — e.g. by a shared-store lock with fencing tokens); or the
memory root gains control files beyond LEDGER/BUILD_INDEX/DEFERRALS (extend
`CONTROL_FILES` and the digest recipe in the same PR).

## Status updates

- **Status:** Superseded by ADR-148 (2026-10-01) — the D-R10-MEMORY-1 cutover statements only
- **Status note (2026-10-01, Round-11 T1, unit SEED-11d):** Per plan §7 row 148, ADR-148 (build memory v2.1)
  splits D-R10-MEMORY-1 (B3 option C) and supersedes this ADR's cutover statements; the closeout journal stays
  in shadow mode (LATER-13), and the protocol design stands. The body above is unchanged (SIG-ENG-003).
