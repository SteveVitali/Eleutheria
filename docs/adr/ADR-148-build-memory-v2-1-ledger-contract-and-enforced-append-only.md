# ADR-148: Build memory v2.1: ledger contract and enforced append-only

- **Status:** Accepted
- **Date:** 2026-10-01T04:09:43Z (decided by the operator at GATE-P — line A-13, log round 5)
- **Phase:** Round 11 / Stage B seed (T1)
- **Ticket:** SEED-11 (unit SEED-11a)
- **Implemented by:** the seed units SEED-02…SEED-10, SEED-16, SEED-17 and the 11A rows P34.7, P34.8, P34.9, P34.29,
  P34.30 (P34.30 implements the D-R10-MEMORY-1 split and writes no ADR — plan `round11_plan.csv` row 235)
- **Decided by:** the operator at GATE-P (`PD/feedback/RATIFICATION_LOG.md`; `PD` = `docs/build/planning/2026-09-30-next-phase/`):
  - **A-13**, round 5 (2026-10-01T04:09:43Z): **"Full seed (Recommended)"** — answering Q-14 (a: the seed carries B3's
    C0–C10, the date-correction ADR, B4's guard core and the PKG-02 pin rewrites; M1–M6 as early tickets), Q-B4-1 (yes:
    the seed carries the guard core), **OD-05 (a: split D-R10-MEMORY-1 per B3 option C)**, OD-06 (yes: restore the 53
    GATE DECISIONS rows first) and Q-17 (yes: Round 11 = phases P34+, manifest rows 201+). The log's labelled
    interpretation: *"seed = restore-first + correction ADR + guard core + PKG-02 pins + D-R10-MEMORY-1 split (B3 option
    C); rows 201+, phases P34+."*
  - Context, not a line of this ADR: A-14, round 6 (2026-10-01T04:16:29Z), "All, staged (Recommended)" — the B6 skill
    changes that put the `harness` key and the gate-record rules into the build-memory layout contract (T0–T0c).
- **Requirement ids:** SIG-MEM-002 (evidence-backed obligation transitions that retain history); SIG-MEM-003
  (single-writer closeout; shadow until a verified operator-approved cutover) — verdict MET-ENGINEERED for Round 11
  (B3 §4); DRAFT-MEM-2 "append-only, proven per change" → **SIG-MEM-006**, DRAFT-MEM-6 "ledger contract" →
  **SIG-MEM-010**, DRAFT-ENG-1 "tests assert invariants" (the seed's six pin conversions) → **SIG-ENG-040**, and
  SIG-ENG-044 "guards precede the records they protect" (the seed guard core) — ids as in SEED-12's id map
  `PD/stageB/T1_id_map.csv`, read at writing; SEED-12 owns them; SIG-ENG-003.
- **Spec:** §55.7 (SIG-MEM-002, SIG-MEM-003); proposed Part XII §56 for DRAFT-MEM-2/6 and DRAFT-ENG-1 (SEED-12).
- **Supersedes:** ADR-126 and ADR-127 — **their cutover statements only** (plan §7, row 148): ADR-126 "Shadow
  boundary" ("P32.8 owns the enforced single-writer protocol and entry-point cutover") and its first revisit trigger
  ("P32.8 cutover … this ADR's shadow-mode statements get superseded by the cutover ADR"); ADR-127's "all shadow-mode
  until the recorded operator cutover" and "enforcement begins only at the recorded operator-approved cutover" on
  `D-R10-MEMORY-1`. The appended `Superseded by ADR-148` status lines are written by SEED-11d, not here; the rest of
  ADR-126/127 stands.
- **Amends / qualifies / extends:** extends ADR-073 (build memory v2) with the v2.1 ledger contract *(agent
  interpretation, labelled; §7 names no status line for ADR-073)*.
- **Sources:** plan §2.1 (build memory), §3.2–§3.3 (OM-01, OM-02, OM-13, OM-15), §5.2, §7 (row 148), §9.2
  (D-R10-MEMORY-1 → P34.30), Appendix A (T2 SEED-01…10, SEED-16; T5 SEED-17); `PD/design/B3-ledger-redesign.md` §1, §3.1–§3.5,
  §4, §5, §6; `PD/design/B4-verification.md` §0, G2, G5, §5, §6.1–§6.3; `PD/design/S2-round-structure.md` CF-01, CF-03,
  CF-04, CF-07; `PD/research/B2-append-only.md` §1; `PD/data/decision_catalog.csv` (Q-14, Q-B4-1, OD-05, OD-06, Q-17);
  `PD/data/round11_plan.csv` (SEED-02, SEED-17, P34.7–P34.9, P34.29, P34.30); landed ADR-126 and ADR-127 (re-read);
  `~/.claude/skills/build-memory/layout.md` BM-LEDGER-01/02/04/06 (the final skill contract per T0c).
- **Recorded:** 2026-10-01T07:42:36Z by Claude Code (Opus 5.5), harness `claude-code/claude-opus-5-5/subagent` — an
  agent-drafted record of the operator's decisions; the operator's words are quoted verbatim from the log.

## Context

Build memory v2 (ADR-073) made the LEDGER the control authority, and ADR-126/127 added obligation events, a current
projection and a single-writer closeout protocol in **shadow mode**, all awaiting an operator-approved cutover recorded on
`D-R10-MEMORY-1`. At chain tip `b051732c` the memory was not a safe resume point (B3 §1, measured):

- **Size and orient cost.** `LEDGER.md` is 679,109 B; CURRENT STATE alone is 122,978 B, 93.5 % of it `| PRIOR` chains
  (268 segments, 41 October dates). A fresh orient reads 126,875 B (≈ 32k tokens), meets a stale prompt ("gitignored,
  never commit", a `.agents/scratch` path, "Do not resume until Codex reports…") and resolves `nextTicket: HUMAN-H4`, a row
  the operator deferred.
- **Append-only broken.** B2 found 42 losses in 24 commits: the 53-row GATE DECISIONS deletion (`c2055d96`), three
  wholesale rewrites of `events.jsonl` (the last mutating 8 anchors in place, 0 transitions ever), erased DEFERRALS cell
  history, rewritten executed contracts and overwritten readouts. G2 would have failed 25 commits.
- **Validators pass on all of it** (F-27): the PHASE LOG→BUILD_INDEX check parses 0 of 139 "done" bullets; the
  projection's `activation-check` passes *because* history was rewritten to match the cells.
- **The shadow tools have no operating evidence**: the closeout journal was used for 2 of 35 Round-10 closeouts and is
  host-local (B3 §4).
- **Six tests pin living records** (next ticket, `IN-PROGRESS`), so the seed's own records would turn `make check` red
  (B4 NEW-3).

`D-R10-MEMORY-1` is operator-owned. B3 offered three options: cut over now, retire both, or split; the operator chose the
split as part of the full seed (A-13, OD-05 a).

## Decision

1. **Orient budget and a value-only CURRENT STATE.**
   - The LEDGER head (line 1 up to `## OPEN FINDINGS`) is ≤ 12 KiB (12,288 B; target 8 KiB). CURRENT STATE is ≤ 3 KiB,
     one value per key, each key line ≤ 256 B, no PRIOR chains; the value history lives in PHASE LOG entries and git.
   - CURRENT STATE has exactly the keys of the build-memory layout contract (BM-LEDGER-02, final skill contract per T0c):
     the 19 keys in order plus the optional **`harness:`** key in its slot between `round` and `updatedAt` (CF-04;
     S6R-06), and **no `model:` key**. Round 11 writes `dispatchTarget: subagent` and
     `harness: devin-desktop/swe-2-high/subagent` (ADR-149); the Stage-B seed's own records carry
     `claude-code/claude-opus-5-5/subagent`. `projectStatus` is `PAUSED` until GATE-B and moves to `IN_PROGRESS` with
     the GATE-B entry (SEED-17, C10).
   - The documented orient recipe (B3 §3.3, O1–O6) reads ≤ 48 KiB (≈ 12k tokens) and never opens LEDGER, DEFERRALS or
     BUILD_INDEX whole; workers still load their contract and scoped DEFERRALS rows.
2. **Living head archived, never lost.** LEDGER lines 1–54 at the seed base are archived byte-for-byte as
   `docs/build/reports/memory-repair/LEDGER_head_R01-R10.txt`, its sha256 recorded in the pointer comment, the
   `memory-repair/README.md` and the PHASE LOG entry; the stale prompt is superseded by the Round-11 OPERATING MODE with a
   one-line tombstone (SEED-10, SEED-17). The archive keeps its wrong dates and points to the date register (ADR-146).
3. **Everything else only gains lines.** In order: the 53-row GATE DECISIONS restoration first (SEED-06; ADR-147); DATE
   CORRECTION entries (SEED-07); BUILD_INDEX index repairs (SEED-09); a `PHASE LOG INDEX — Rounds 1–10` backed by a
   hash-anchored CSV and a new last section **`## PHASE LOG — Round 11`, the only append target** (SEED-05); a RETURN
   PASS superseding note and `### RETURN PASS — current` (SEED-16). GATE DECISIONS rows from Round 11 use the 7-column
   form with `kind` (ADR-147).
4. **Append-only is enforced, not described.** The guard core ships in the seed, before any seed memory record (A-13,
   Q-B4-1; SEED-02; CF-01 — the P34.0a records-only fallback is not used):
   - `docs/build/tools/memory_guard.py`: G1 `record-dates` (diff mode; ADR-146), G2 `append-only` core (region policy,
     append position, the `living-archived` mode — a removal from the living head is legal only when the removed bytes
     are added verbatim under `reports/memory-repair/` in the same commit — readouts, and a `prefix` mode for `*.jsonl`),
     G4a/G4b (ADR-147);
   - policies under `docs/build/tools/record_policy/`, including `ci_required.txt` naming the five `ci.yml` jobs
     (python, docs, composed, security, web); G1 scoped to build-memory records, never `docs/build/planning/**`;
   - `make docs-check-memory`, `-spec`, `-matrix`; a memory-guard step in the PR-triggered `docs` job; pytest collecting
     `docs/build/tools/test_*.py`;
   - `docs/build/tools/ci_boundary.py` (G3a) reading the head-bound check-runs of the current `r11/` PR and its `r11/`
     ancestors only (never #141–#190); the OM-01 trailer check (ADR-149); `runs-on: ubuntu-24.04` pinned in every job;
   - a three-way sync of the vendored `scripts/docs/check-build-memory.sh` (upstream at T0c, the repo's P32.8/ADR-127
     patches, Round 11's needs), incl. the GATE DECISIONS `kind` + pre-authorization check;
   - the six living-record pin conversions (SEED-03, PKG-02; OM-15).
   The full G2 modes, replay oracle and nightly replay follow in M1 (P34.7); the ledger-contract validator (B3 V1–V6, V8,
   V9, V11 plus V12 harness, V13 manifest rounds, V14 planning-ledger freshness) and G11 no-vacuous-pass in M2 (P34.9).
   Until M2, the planning-side `seed_verify.py` checks each seed commit (0 removed lines on protected paths, hashes,
   budgets).
5. **`D-R10-MEMORY-1` is split (B3 option C; OD-05 a):**
   - **Obligation events — repaired, then enforced in-repo.** `events.jsonl` is append-only in `prefix` mode; `migrate`
     refuses once the file exists; correction, transition and `date-correction` events are appended and the seed's
     queued `pending_transitions` are applied through the repaired tool (M3, P34.8; CF-03); CI fails a PR that changes a
     DEFERRALS leading token without a matching appended transition event (M6, P34.30). This half needs no skill edit,
     because CI enforces it at PR level.
   - **Projection — kept as an advisory, CI-verified orient view.** `current_projection.py verify` runs in the CI
     `docs` job, `known_inconsistencies` must be empty, `CURRENT.md` stays ≤ 20 KiB, and landings come from the recorded
     dispositions (M5, P34.29). The authority stays LEDGER + DEFERRALS (ADR-126).
   - **Closeout journal (`closeout-op/1`, ADR-127) — stays shadow in Round 11.** Code and tests are kept; it is not
     wired into entry points; the worktree-safe validator patch stays live. **Cut-over trigger:** parallel ticket
     dispatch, a multi-worktree build, or a second host or harness writing memory concurrently. Prerequisites at the
     trigger: the B6 entry-point patches applied by the operator, `--authoritative-root` set explicitly, and a dry-run
     in a scratch clone.
   - **Record of the legs:** the events leg → ticket (P34.8 + P34.30), DONE on enforcement evidence; the journal leg →
     later-phase with the trigger above; SIG-MEM-003's verdict → MET-ENGINEERED.
   This replaces the "one operator-approved entry-point cutover" that ADR-126 and ADR-127 anticipated: there is no
   wholesale cutover; the events half is enforced by CI now and the journal half waits for its trigger.

## Consequences

- A fresh session orients in ≤ 48 KiB and resolves the real next row (row 201) instead of a deferred human row; GATE-B's
  T6 dry-run proves it (≤ 12 KiB head, the five seed-PR checks green).
- Protected regions can no longer be deleted or rewritten silently: a removal fails CI unless it is an archived living
  replacement. Corrections and restorations are visible as appended, dated blocks.
- `LEDGER.md` stays large (≈ 600 KB after the seed); the budget applies to the orient region only. Rotating the whole
  LEDGER per round was considered and deferred (B3 §3.14).
- The `events.jsonl` history is repaired forward; the three rewrites stay visible through correction events, and
  `activation-check`'s result is recorded as-is rather than trusted.
- The single-writer protocol remains unenforced; a closeout repaired by the orchestrator is a PHASE LOG `repair` entry,
  and two in a round set `blockedOn` (OM-02).
- The seed is larger (≈ 700 lines of guard code in Stage B), and GATE-B needs it green.

## Alternatives considered

- **Cut over events and journal now (B3 A; OD-05 b):** rejected — enforcement would run on rewritten history, needs
  out-of-repo skill edits, and the journal has no operating evidence.
- **Retire both (B3 B; OD-05 c):** rejected — it restores "last token wins" over 15 reconciled conflicts, needs a
  SIG-MEM-002 waiver and loses the compact owed-work view.
- **Records-only seed, guard core as row 201 (Q-14 b; the P34.0a fallback):** not chosen — it leaves T1, T4 and T5's
  records unguarded in CI while they write exactly the record classes where F-21/F-22/F-29 happened.
- **Archive the head as a fenced `.md`, or add a `ledgerArchive:` key:** rejected (B3 §3.2) — the slice contains fences,
  and an extra key breaks the layout contract's key order.
- **Carry the harness inside `dispatchTarget`'s value (B4 G5's interim proposal):** superseded by the layout contract's
  optional `harness` key (CF-04, T0c).

## Revisit trigger

- The journal cut-over trigger fires: parallel ticket dispatch, a multi-worktree build, or a second host or harness
  writing build memory concurrently (including a leg-runner that writes without the chain lock).
- The orient region exceeds 12 KiB, or the orient recipe exceeds 48 KiB, in any committed LEDGER.
- G2 or the transition rule is weakened, bypassed or allow-listed to let a protected-region removal through; or a
  DEFERRALS leading token changes without an event.
- The build-memory layout contract changes CURRENT STATE's keys or the PHASE LOG shape (a new skill release).
- The round closes with `pending_transitions` non-empty (the 11A exit requires 0).
