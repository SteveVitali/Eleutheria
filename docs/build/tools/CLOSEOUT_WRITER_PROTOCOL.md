<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42. -->

# CLOSEOUT_WRITER_PROTOCOL.md — `closeout-op/1`

P32.8 (SIG-MEM-003, ADR-127). The single-writer closeout protocol for
implement-spec closeouts and orchestrator repair paths. **`LEDGER.md` CURRENT
STATE stays the control authority** — this document governs the operational
journal (`docs/build/tools/closeout_protocol.py`) that makes an interrupted
closeout resume to exactly one closeout across worktrees, never a duplicated
index row, a second PR, or invented closure.

**Mode: SHADOW / AVAILABLE — not yet enforced on entry points.** The protocol
tool is landed, tested, and documented; the actual worker/orchestrator skill
entry points (which live in user-global `~/.claude/skills/` and `~/.codex/skills/`
and are never edited from this repo) adopt it only at the operator-approved
ticket-boundary cutover recorded on **D-R10-MEMORY-1** (stays OPEN). Until then
`activation-check` reports whether the legacy/event state would permit cutover.

## Where the state lives

Everything goes under `<git-common-dir>/sig-closeout/` — the git common
directory every worktree of one clone shares (`git rev-parse
--git-common-dir`), so all worktrees see one journal:

```
<common-dir>/sig-closeout/
├── locks/<lock-…>/info.json      # mkdir-atomic scoped advisory lock
├── operations/co-….json          # one closeout-op/1 record per operation
└── recoveries.jsonl              # stale-lock recoveries, append-only
```

The journal is host-local operational state, not committed build memory — the
committed control files remain `LEDGER.md`, `BUILD_INDEX.md`, `DEFERRALS.md`,
`runs/<ID>.md`, `pr/<ID>.md`.

## The operation id (defined before PR creation)

`prepare` computes `co-<sha256[16]>` over
`{schema, ticket_id, attempt, implementation, base}` — a stable identity defined
**before** any remote PR creation, so a crash+retry anywhere in the flow maps
to the same operation instead of inventing a second identity. The remote PR
number attaches afterward (`external-known`). Same identity re-presented at any
boundary is an idempotent resume, never a second record.

## Expected-state preconditions (the four input values)

`prepare` compares caller belief against the **authoritative chain ref** — the
main worktree's checkout (the checkout that shares this common dir), never
merely the caller's own stale files:

| precondition | source of truth | stale signal |
|---|---|---|
| `expected_next_ticket` | authoritative `LEDGER.md` `nextTicket` | exit 2 |
| `expected_last_completed` | authoritative `LEDGER.md` `lastCompleted` | exit 2 |
| `expected_control_digest` | sha256 over authoritative LEDGER + BUILD_INDEX + DEFERRALS | exit 2 (also CAS'd again at memory-commit) |
| `expected_chain_head` | `git rev-parse HEAD` on the authoritative root | exit 2 |

Any mismatch exits non-zero naming the deltas and writes **nothing** — stale
expected-state fails without partial advancement. Callers may pass the values
explicitly or let the tool read their own files as the belief being checked.

## The scoped advisory lock

- **Scope:** `lock-<sha256[16](chain_id | common_dir | ledger_rel)>` where
  `chain_id` is the ledger's `manifest` field (stable for the chain's life) —
  one lock per build chain per clone, shared by every worktree.
- **Mechanism:** `mkdir` (atomic) + `info.json` recording
  `{pid, host, worktree, operation_id, acquired_at}`.
- **Held only during critical sections** (prepare's read-modify-write of the
  journal; manual `lock acquire` for repair sections).
- **Single-host assumption (documented):** multi-host orchestration is out of
  scope (S6 research). PID liveness is meaningful only on the recorded host — a
  lock recorded on another host is *never* reclaimed here.
- **Stale-lock recovery:** a lock left by a crashed writer is surfaced with
  recovery instructions, and reclaimed only by an explicit `--recover-stale`
  after the recorded PID is confirmed dead **on the recorded host** — never
  removed merely because a timeout elapsed. Every recovery appends to
  `recoveries.jsonl` (auditable, never silent).

## The closeout-op/1 state machine

```
prepared ──▶ external-known ──▶ memory-committed ──▶ acknowledged
   │                                               ▲
   └── abort / superseded (terminal)               │
```

1. **prepare** — identity + preconditions under the scoped lock. Refuses: a
   different implementation/attempt identity for a ticket that already has an
   in-flight or acknowledged operation (exit 3, unless `--attempt N --reason`
   records a new attempt — which also supersedes the in-flight predecessor);
   another ticket's unacknowledged operation (next dispatch is prohibited
   before acknowledgment); stale expected-state (exit 2).
2. **external-known** — attach `{number, url, head, base}`. A second PR number
   for the same op is the duplicate-creation failure mode — refused. With
   `--uncertain` the tool reconciles ambiguous creation by exact head/base
   (`gh pr list --head --base`, or `--lookup-json` in tests): a found PR is
   adopted (never re-created); an absent one is reported so the caller may
   create exactly one.
3. **memory-committed** — the validated git commit IS the memory transaction.
   The commit must (a) exist, (b) descend from `expected_chain_head`, (c) have
   a parent whose control digest equals the recorded expected digest —
   compare-and-swap proof the transition applied onto the expected state,
   (d) touch `LEDGER.md` + `BUILD_INDEX.md`, (e) pass the validator
   (default `check-build-memory.sh`). Ordinary uncommitted file replacement is
   not atomic and is never accepted as a transition.
4. **acknowledge** — confirms the authoritative chain ref actually advanced
   (`lastCompleted` = this ticket, `nextTicket` moved on). Only an acknowledged
   closeout permits the next dispatch.

Terminal side-states: `aborted` (operator/worker abort) and `superseded`
(replaced by a recorded later attempt) — both preserve full history, never
silently dropped.

## Invocation recipes

Implement-spec closeout (worker), after the implementation commit `I` on branch
`B` with base `X`:

```
python3 docs/build/tools/closeout_protocol.py prepare \
    --ticket P32.8 --implementation $(git rev-parse HEAD) --base <X>
# → prints the operation id co-…; on stale-state exit 2 re-sync and re-run
#   (re-run is idempotent — same identity resumes, never duplicates)

# … push, create PR, or reconcile an uncertain creation …
python3 docs/build/tools/closeout_protocol.py external-known \
    --operation co-… --pr 165
# or, when `gh pr create` outcome was uncertain:
python3 docs/build/tools/closeout_protocol.py external-known \
    --operation co-… --uncertain --head B --base <base-branch>

# … write run ledger, BUILD_INDEX row, DEFERRALS annotation, LEDGER advance …
python3 docs/build/tools/closeout_protocol.py memory-committed \
    --operation co-… --commit $(git rev-parse HEAD)

python3 docs/build/tools/closeout_protocol.py acknowledge --operation co-…
```

Orchestrator repair paths use the identical calls — every writer compares
against the same authoritative chain head, the same scoped lock, and the same
identity rules.

`status` lists recorded operations; `lock inspect|acquire|release
[--recover-stale]` manages the advisory lock manually; `abort` records a dead
operation honestly.

## activation-check — the cutover gate

`activation-check` refuses enforcement (exit 6) while ANY legacy/event
divergence exists: a DEFERRALS row with no migration anchor (legacy-only), an
event for an unknown obligation (event-only), a compatibility cell that
disagrees with its event-chain head. READY (exit 0) reports the chain is clean
— and still notes enforcement begins only at the operator-approved
entry-point cutover (D-R10-MEMORY-1).

## Skill-entry-point patch contract (reviewed, applied at cutover)

External skill entry points are never edited from this repository. The
reviewed contract below is the integration surface; the operator applies it at
the D-R10-MEMORY-1 boundary (both `~/.claude/skills/` and `~/.codex/skills/` are
references for reviewers only).

### contract/patch/1 — implement-spec closeout boundary

Where the skill currently writes memory files directly and pushes:

1. Insert `prepare` (above) before any remote PR creation; carry the printed
   operation id.
2. Replace "create PR; on failure retry create" with `external-known --pr N`,
   or `external-known --uncertain` reconciliation when the remote outcome is
   ambiguous.
3. Require `memory-committed --commit <closeout-commit>` to exit 0 — the
   validator-green commit carrying the control-state diff is the memory
   transaction; uncommitted edits are never a transition.
4. Require `acknowledge` exit 0 before reporting closeout DONE / before the
   next dispatch.
5. On non-zero exits: 2 = re-sync to authoritative head and re-prepare;
   3 = record a new attempt (`--attempt`, `--reason`) — never retry blindly;
   4 = stale-lock recovery per the printed instructions.

### contract/patch/2 — orchestrate-build repair + worker invocation

1. The orchestrator's dispatch of a closeout worker passes
   `--implementation <worker-tip>` and `--base <ticket-base>` so the operation
   identity is reproducible.
2. Before declaring a ticket closed (verify succeeded, index row exists) the
   orchestrator runs `acknowledge --operation <id>` — no acknowledgment, no
   next dispatch.
3. The orchestrator's own repair path (broken branch, missing index row,
   interrupted closeout) uses `prepare … --attempt N --reason …` for every
   remediation write — the same authoritative-chain check as workers.
4. On any stale-state exit the orchestrator re-syncs the worktree and
   re-invokes; it never edits memory files outside the protocol.

### contract/patch/3 — upstream validator patch (truthful provenance)

`scripts/docs/check-build-memory.sh` is a vendored copy of the upstream
build-memory skill's `check-build-memory.sh` — and is **NO LONGER
byte-identical** (LOCAL PATCH banner in-file). The delta, reviewable upstream:

1. JSON report → caller-selected `--json PATH` or a unique per-run temp file
   (`mktemp`); the shared `/tmp/build-memory-check.json` destination (a
   write-collision between concurrent worktrees) is removed; the exact path is
   printed on the last stdout line.
2. The report (`build-memory-check/2`) records checked-input identity —
   `{repo, commit, dirty, input_digest}` where `input_digest` chains the
   sha256 of every file the checker read; a report is valid only for the exact
   input revision it names.
3. Diagnostics carry `{check, severity, file, obligation, evidence, message}`
   and `summary.exit` records the process exit code — report severity and exit
   status agree by construction.
4. Detection logic (layout allowlist, ticket grammar, manifest↔files,
   DEFERRALS ids, ADR index↔files, LEDGER keys, secret/size scans, exit
   severities) is unchanged — the patch touches output/reporting only.

> **Note appended 2026-10-01T14:34:10Z (SEED-02b, Round-11 Stage B; `date -u`).** The text above
> describes the P32.8 fork as landed and is kept as written. Since SEED-02c
> (2026-10-01) `scripts/docs/check-build-memory.sh` is no longer that fork: it is
> the upstream build-memory **0.5.0** validator (skill commit `8aeb6dc`) behind a
> provenance banner, and upstream now carries items 1–3 of this patch (the
> `build-memory-check/2` report at `--json PATH` or a unique `mktemp` file named on
> the last stdout line, the `{repo, commit, dirty, input_digest}` identity, the
> uniform diagnostic records and `summary.exit`). Item 4 no longer holds: the
> detection logic is 0.5.0's (duplicate ticket ids keyed on the id, tolerant
> DEFERRALS status parsing, region-aware PHASE LOG parsing, the guards marker,
> ledger budgets and the `harness` slot, history mode handed to
> `scripts/docs/check-history.sh` → `docs/build/tools/memory_guard.py`). Three
> SIG-local hunks remain, tagged `SIG-LOCAL` in the file: L1 `dirty` also covers
> the canonical spec, L2 an unwritable report exits 2, L3 diagnostic fields are
> split on `\037`. The banner at the top of the script and
> `docs/build/runs/SEED-02c.md` are the current description; this contract's
> reporting guarantees (items 1–3) still hold.

## Prior art the protocol consumes (never forks)

- `audit_current_state.py` (P32.1): input digests, expected-revision
  comparison, the `{check,severity,…}` record shape.
- `obligation_events.py` (P32.7): the event chain + compatibility-cell
  divergence checks powering `activation-check`.
- `current_projection.py` (P32.7): deterministic current view (unaffected —
  this ticket governs writes, not reads).
- `check-build-memory.sh` (BM-VALID-01): the memory-commit validator.

## Exit codes

`0` ok · `1` state/validation failure · `2` stale expected-state or control
divergence · `3` implementation/PR identity conflict · `4` lock contention or
stale lock · `5` usage error · `6` activation-check BLOCKED.
