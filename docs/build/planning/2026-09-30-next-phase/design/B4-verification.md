# B4 — Verification and validator gap design

Row **B4** of `META_PLAN.md` (Stage P, stream B, Wave 4). Owner D. **This row is design only.** It adds no guard,
edits no control file (P10) and commits nothing. It writes two files: this note and `findings/incoming/B4.csv`.
Scratch is the session scratchpad (`…/scratchpad/B4/`, one validator JSON report; not committed).

- **Authored:** 2026-09-30T17:40:03Z → 18:02:50Z (`date -u`) by Claude Code (Opus 5.5), in the planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (`claude/next-phase-planning` @
  `41ab9521`).
- **Builds on:** B1 (date register, correction ADR, regression-test sketch §5.4), B2 (`check-append-only` §7 and the
  violation register), B3 (validator requirements V1–V11 §6, seed C0–C10, tickets M1–M6), B5 (operating rules
  OM-01…OM-18), F2b (verdict vocabulary and matrix cross-checks §2.4), H1 (CI facts), plus F3 §5/§7 (ADR triggers,
  register hygiene), G1 §4 (SIG-OPS drafts) and C3 §5/§6 (DR-C3 drafts) for coordination only.
- **Evidence classes (P1):** `code` (file reads, git history, blame); `recorded-execution` (validator runs, B4
  replays over git history); `live-read` (`gh run list`, `gh pr list`, read-only); `inference`, marked **(I)**.
  Numbers marked *(replay)* were computed by B4 from git or from the committed B1/B2 registers (§10).
- **Validators run read-only (17:41:14Z):** `check-build-memory.sh` exit 0 "no violations (0 warnings)";
  `check_spec_src.py` OK (722,981 B, 144 ADRs, 715 ids); `check_coverage_matrix.py` "715 rows OK";
  `check_backlog.py` "deferral homes: 36/36". All green on a tree that holds F-21…F-29 (F-27 reconfirmed).

---

## 0. Summary

**The eleven guards.**

| id | guard | catches (main) | runs | first placement |
|---|---|---|---|---|
| **G1** | `record-dates`: recorded event dates ≤ commit time and ≤ CI clock; acts not back-dated; expiring future-date allow-list | F-21, B1 NEW-1…7, C4 NEW-32, **B4 NEW-1** | CI `docs` job (PR + push), `make docs-check`, pre-commit, boundary | **Stage B, before C1** (diff mode) |
| **G2** | `append-only`: B2's region policy + append-position + `living-archived` + sqitch plan + id registry | F-22, F-26, B2 NEW-1…9, B3 NEW-3 | same as G1 | **Stage B, before C1** (core) · M1 (full) |
| **G3** | `ci-boundary`: read `gh pr checks` at every boundary, red → `blockedOn`; verify recorded CI; external-state delta; branch protection; toolchain pin | F-17, F-18, F-19, F-20, B5 NEW-2/4, H1 NEW-2/4 | orchestrator boundary, CI `docs` job, operator settings | script + rule **Stage B** · verifier early ticket · protection = operator |
| **G4** | `gate-record` + `readout-authorship`: verbatim table rows, answer after pause, hedge/delegation lint; permanent guard sentence; agent-drafted blocks + confirmation marker; signing only appends | F-29, F-36 (part), B2 NEW-6, E1 NEW-9, B5 NEW-3 | CI `docs` job, boundary | table form **Stage B** · readout rules before the first Round-11 gate |
| **G5** | `ledger-contract`: B3 V1–V6, V8, V9, V11 + V12 harness, V13 manifest rounds, V14 planning-ledger freshness | F-23, F-24, F-25, F-28 (part), B3 NEW-1/2/6/7/8, **B4 NEW-2** | CI `docs` job, `make docs-check`, boundary | seed-side `seed_verify.py` · product M2 |
| **G6** | `living-record-tests`: tests assert invariants, never the current value of a living record | F-19, B5 NEW-8, **B4 NEW-3** | `make check` (pytest AST lint) | pin conversion **Stage B** · lint early ticket |
| **G7** | `spec-and-verdicts`: `check_spec_src`, `check_coverage_matrix`, `check_backlog`, projection `verify` in CI; verdict grammar + cross-checks (verdict × DEFERRALS × `accepted_scope`) | F-32, F2b NEW-1/4, A3 NEW-1, F-16 shape, B5 NEW-6, **B4 NEW-4** | `make docs-check`, CI `docs` job | wiring **Stage B, before C1** · cross-checks **with T4** |
| **G8** | `adr-index-and-triggers`: index completeness (title, owning phase, status), supersession status, fired-revisit-trigger register | F-32, F3 NEW-3/4, **B4 NEW-6** | `make docs-check`, CI, round tail | new-ADR rule **with T1** · generator + register check early |
| **G9** | `round-close-records`: SIG-ENG-031 **amended** (matrix = traceability; risk register per round; round ↔ spec part) | F-32, F3 hygiene 1/3/5 | round tail (REC), CI | spec text T1 · check early |
| **G10** | `production-truth placement`: where G1-ops/C3 probes run (PR, candidate, publish, schedule, tail) + fixture-sentinel scan + live-claim binding | F-10, B5 NEW-5, C3 §5 causes 1–7, C4 NEW-11/27/32, F3 NEW-6 | CI, candidate gate, scheduler, tail | Round-11 wave 1 (safety and honesty) |
| **G11** | `no-vacuous-pass`: every check reports items evaluated; 0 evaluated of a non-empty candidate set fails | F-27, B3 NEW-1, G1 NEW-3 / J1 NEW-13 | every validator, scheduled workflows | M2 + the observability fix |

**Coverage (details §2).** Of the 17 in-scope Appendix-A findings (F-17…F-29, F-32, F-36, F-37, F-38), **13 are
caught** by at least one guard, **3 are caught in part** (F-28 semantic mis-status, F-36 gate substance, F-37
self-reported harness) and **1 is detect-after only** (F-38, via G1-ops SIG-OPS-005 drift detection). Of the 40
NEW items from B1/B2/B3/B5/F2b, **28 are caught**, **7 in part**, and **5 are not verification-layer targets**
(a code defect with its own unit test, a process cost, three product or governance gaps routed elsewhere). The C3
systemic causes are all catchable by C3's own draft checks; G10 only places them. What no repository check can
prove is listed in §2.3. The most important one: **the authenticity of an operator's words**, because agent
sessions act with the operator's git identity and `gh` token.

**Replays against this repository's history** (every guard has one; §4):
- G1 would have failed **70 chain commits** (502 future-dated records) from `305f94d5` (2026-09-09) through
  `b051732c`, including `062306e7` (the start of the ratchet), `a33cd6ec`, `95c8a73f`, `9bf11201` and `7a2ff9fa`. It
  would also have failed **17 commits of this planning round's own ledger today** (B4 NEW-1).
- G2 would have failed **25 commits** (B2's 42 losses + 4 unjustified transitions), plus **20 commits** that inserted
  inside GATE DECISIONS instead of at its end (18 of them top-insertions from `307161ee`).
- G3 would have **stopped the chain at 4 boundaries**: P31.6 (after run 36092963615 failed at 2026-09-25T04:09:25Z),
  P32.10a, P32.23a and P33.4. No red head would have had a successor stacked on it while red.
- G4 fails the three signing commits `0a715fcc`, `95c8a73f`, `4127dbf3`, and the GATE-G1 rewording `3259ca81`.
- G5 fails 121 of 194 LEDGER versions on V1 (from `2a5d01e0`), 128 on the enum (from `0ea9be15`), and every version
  since `4d5a5d27` on the stale `.agents/scratch` path.
- G6 fails `a3653d76` (P32.1), `e8bc0179` (P33.3), `6e93b098` (P33.7) and `c77bd45e` (P33.8).

**Placement (§6).**
- **Stage B, before any new memory record (pre-C1):** a small stdlib guard core, i.e. G1 in diff mode on record
  positions, G2-core, the G4 table and guard-sentence rules, G7 wiring, and the G3 boundary script with its
  OPERATING-MODE rule. This commit also converts the six living-record pins that the seed itself would turn red
  (B4 NEW-3). The reason: the seed writes date corrections, restorations, a new head, ADRs and GATE DECISIONS rows,
  which are exactly where F-21/F-22/F-29 happened, and this round's own ledger drifted under prose rules today.
- **With T1 / T4:** the new-ADR header rule; the verdict grammar and cross-checks; the trigger-register file.
- **Early Round-11 tickets:** M1 (G2 full), M2 (G5 + G11), M3, B1's code/sqitch/fixture guards, G3 verifier and
  external delta, full G4 readout rules, the G6 lint, the G8 generator and checker, and G9.
- **Later waves:** G10, placed with G1-ops and C3's own tickets.
- **B6 (user-global skills):** seven interface points (§6.3). Their contents are not designed here.

**New findings (§8, `findings/incoming/B4.csv`), ten in all.** Headline: **this planning round's own ledger
repeats F-21 today**. The META_PLAN change log records 24 entries 5–152 min *after* the commits that wrote them,
a growing forward ratchet, plus an operator decision stamped "18:2xZ" in a commit made at 17:10:49Z. The workers'
stamps are correct; only the single-writer orchestrator drifts (NEW-1, S1). Its CURRENT STATE is also stale
(NEW-2). And the seed would go red on six test pins, including one that pins the off-enum `IN-PROGRESS` (NEW-3).

---

## 1. Why every validator passed: what exists and what it cannot see

| tool | runs in (today) | checks | cannot see | evidence |
|---|---|---|---|---|
| `scripts/docs/check-build-memory.sh` (vendored, local patch) | `make docs-check` → CI `docs` job, **PRs only** (`ci.yml:28`) | layout allowlist; ticket grammar; manifest ↔ files; backward deps; DEFERRALS ids + status vocabulary; ADR index == regeneration + `## Revisit trigger`; CURRENT STATE key **order**; `nextTicket` names a row (warn); PHASE LOG done → BUILD_INDEX (**vacuous: 0/139 parsed**, B3 NEW-1); size and secrets | history (deletions, rewrites, insert position); dates; CURRENT STATE **values** (`IN-PROGRESS` passes); head size; stale paths; index **content** (a "—" row passes because the generator wrote it) | `check-build-memory.sh:44-61,348-385` |
| `scripts/docs/adr-index.sh` | inside the above | regenerates the index | parses only `# ADR-NNN:` titles and `**Ticket:**` → **79/144 titles, 142/144 tickets, 25/144 statuses are "—"** (B4 NEW-6) | `adr-index.sh` `field()`, title `grep` |
| `docs/build/tools/check_spec_src.py` | **no gate** (0 hits in `Makefile`, `.github`, `tests/`) | BUILD.sh byte identity; App F == ADR files; 668 + N ids; reference closure | not run; its own test `docs/build/tools/test_check_spec_src.py` is outside pytest `testpaths = ["tests"]` (`pyproject.toml:101-104`) → never collected (B4 NEW-4) | F-32 |
| `docs/build/tools/check_coverage_matrix.py` | **no gate** (F2b NEW-4) | 715 rows (**pinned constant**, `:32`), enums, routing present for non-MET, evidence non-blank | truth: MET citing OPEN D-rows, MET-DIFFERENTLY without ADR, routing to landed tickets, dead evidence paths, domains | F2b §2.4 |
| `docs/build/tools/check_backlog.py` | partly, via `tests/unit/test_backlog_housekeeping.py:187-193` (`deferral_homes` on the real DEFERRALS) | every owed row cites a BL id; triggers homed | whether the home is **open** (D-SOURCES.2-2 → closed BL-032 passes; 23 triggers on closed rows count as homed) | F3 NEW-1/NEW-3 |
| `audit_current_state.py` | `make check`, via a real-tree test (`test_build_memory_audit.py:323`) | parser-level conflicts | used as a **living-state pin** (§4 G6) | H1 §2b |
| `obligation_events.py` | **no gate** on the real tree (tests are fixture-only) | event chain | `migrate --recorded-at` is required and regex-only (`:1186`, "YYYY-MM-DD fixed input") | B1 §6.3 |
| `current_projection.py verify` | **no gate** on the real tree | input digests fresh | whether the inputs are true (F-28) | B3 V9 |
| CI `docs` job | `pull_request` only; `fetch-depth: 0` | runs the two above | pushes to `main`, i.e. merge commits, where `c2055d96` arrived (as `e2175c93`) | `ci.yml:28-42` |

**Diagnosis.** The validators check the **shape of the current tree**. None of them reads **history**, the
**clock** or **GitHub**, and none reports **how many items it evaluated**. Every failure in F-21…F-29 lives in one
of those four blind spots. Three of the six tools run in no gate at all.

---

## 2. Finding → guard map

### 2.1 Appendix-A memory/process findings (A2-verified)

| finding | guard(s) and rule | would have failed (replay) | verdict |
|---|---|---|---|
| **F-17** operator merges unrecorded | G3c external-state delta, recorded at every boundary; an off-stack merge → stop (OM-03) | first boundary after #148 (`devin/deploy-gcp-live`, merged 2026-09-26T03:07Z, off-stack, B5 NEW-4); the 09-29 and 09-30 sittings (#191, #112–#140); `d4522d82` on `main` not in the chain (F-40) | caught (recorded) |
| **F-18** #141–#154 red on `npm ci` | G3a (red → `blockedOn`); G3e toolchain pin prevents recurrence (H1 NEW-2) | P31.6 dispatch: run 36092963615 on `fa0d67a8` failed 2026-09-25T04:09:25Z; #142 was created 07:27:56Z | caught |
| **F-19** #165/#179/#185 red on living pins | G6 lint at the commits that added the pins; G3a at the next boundary; G5 V5 row well-formedness (the #179 cause is an unescaped `\|` in BUILD_INDEX row 183, H1 NEW-6) | G6: `a3653d76`, `e8bc0179`; G3a: P32.10a (red 10:31:38Z, #166 created 10:50:25Z), P32.23a (red 2026-09-27T20:13:09Z, #180 at 09-28T02:11:11Z), P33.4 (`4127dbf3` red from 18:47Z, #186 at 19:36:22Z); V5: `a97aaca2` | caught |
| **F-20** CI never consulted | G3a at every boundary; G3b verifies every recorded `ci:` claim against the GitHub API | every Round-9/10 boundary (0 of 183 run ledgers cite a check) | caught |
| **F-21** future-dated records | G1 R1 (record date ≤ commit time and ≤ CI clock) | 70 commits / 502 rows (B1 register), first `305f94d5` (2026-09-09, ADR-065 +1 day); ratchet from `062306e7` (sqitch L41, 2026-10-02 at 2026-09-25T08:09Z); `a33cd6ec`, `95c8a73f`, `9bf11201` (42 rows, candidate as-of), `6bade66e`, `7a2ff9fa` (97 events at 10-21); propagation `71e8bc83`, `e8bc0179`, `4127dbf3`, `c77bd45e` | caught |
| (F-21, backward) Round-3 "chain date" 09-10 recorded on 09-13 | G1 R2 (acts not back-dated beyond 48 h), act positions only | 22 commits / 87 rows (B1), e.g. `eb72be5f`…`759fcbac`; `e1cedcad` (21 `sources.toml` rights fields, B1 NEW-5) | caught (act positions); non-act back-dating is not |
| **F-22** `c2055d96` deleted 53 GATE DECISIONS rows | G2 `append-only` on the PR diff + first-parent diff on push | `c2055d96` (PR #108) and merge `e2175c93` | caught |
| **F-23** LEDGER 679 KB, stale prompt, off-enum | G5 V1 (head ≤ 12 KiB), V2 (enum), V3 (stale tokens and paths) | V1: 121/194 versions, first `2a5d01e0` (2026-09-13T21:20Z, 14,182 B); V2: 128 versions from `0ea9be15` (09-22, `IN-PROGRESS`); V3: `.agents/scratch` in every version since `4d5a5d27` (the v2 migration itself), "Do not resume until Codex" since `d6c562e5` | caught |
| **F-24** PHASE LOG order and gaps; BUILD_INDEX gaps | G5 V4 (bold-aware; append only at EOF; ≤ 2 KiB), V5 (unique seq; no `PR pending` after stamps; marker rows) | V5: duplicate seq 170 at `42bb286a`/`b132bbbb`; `PR pending` rows 76–81 from 2026-09-14; markers 190/195 absent after `95c8a73f`/`4127dbf3` | caught |
| **F-25** `returnPass` stale | G5 V6 (key == generated RETURN PASS table) | every LEDGER version from the Round-10 seed `d6c562e5` (no D-R10 ids) | caught once M5's generator exists |
| **F-26** `events.jsonl` rewritten 3× | G2 `prefix` mode (head bytes start with base bytes) | `b132bbbb`, `30d401dc`, `7a2ff9fa` | caught |
| **F-27** validators pass on false records | G11 (vacuous PHASE-LOG check) + G1/G2/G5 | G11 fails the check-build-memory PHASE-LOG loop (0 of 139 evaluated) on every version with bolded ids; `7a2ff9fa` (the "independent" P33.1) fails G1 and G2 | caught |
| **F-28** stale landings, mis-status, triple cadence | G5 V9 landing liveness (a landing must name an existing, non-dropped chain row) | projection landings on P31.18 (dropped/moved) | **partial**: D-SOURCES.12-1's "nothing actionable remains" while PARTIAL, and the pre-GL-GATE-08 blocker, are textual semantics → REC-tail re-verification (F1 method) |
| **F-29** readouts agent-written; guard line deleted | G4b (readouts append-only except `Status:`; permanent guard sentence; decision == verbatim GATE DECISIONS answer; agent text only inside confirmed agent-drafted blocks); G1 on `Date:` | `0a715fcc`, `95c8a73f` (also `Date: 2026-10-19` after a 2026-09-28T03:49Z commit; decision paragraph ≠ "I sign/accept. Please proceed"), `4127dbf3` ("oik looks good, proceed"), `3259ca81` | caught (form); authenticity not catchable (§2.3) |
| **F-32** process requirements unmet while MET | G7 (wire `check_spec_src`, collect its test), G8 (index completeness), G9 (SIG-ENG-031 amended; round ↔ spec part) | today: 79/142/25 "—" index rows; `check_spec_src` in no gate; `traceability.md`/`risk_register.md` untouched since 09-13/09-14 across 16 later phases | caught |
| **F-36** gates pre-answered/blanket; `blockedOn` never set | G4a (answer dated after the gate's pause entry, or typed `pre-authorization` with item ids + expiry; hedge and delegation lint), G3a/G3b (`blockedOn` on red is mechanical and audited), OM-11 defer-count rule on obligation events (M3/M6) | GL-GATE-01…05 "delegated … to Devin's judgement" (no item ids/expiry), GL-GATE-08 "I also wonder if…" (hedge), ACCEPT-R8 "please sign … for me or whatever" (`0a715fcc`, delegation); 194/194 ledger versions with `blockedOn: (nothing)` across 4 red boundaries | **partial**: shape is checkable; whether a blanket rule was wise is not |
| **F-37** harness switches untracked | G5 V12 (run-ledger `Harness:`/`Model:` header; commit trailers in Round-11 PRs) | 116/116 untrailered commits 2026-09-26…09-28 | **partial**: trailers are self-reported |
| **F-38** out-of-ticket production changes | not catchable by repository guards; G1-ops **SIG-OPS-005** live-config reconciler flags undeclared drift (min-instances, tier) after the fact; OM-14 is a rule, not a check | — | **detect-after only** |

### 2.2 NEW items from B1, B2, B3, B5, F2b (and cross-cutting C3/C4/H1)

| item | guard | verdict |
|---|---|---|
| B1 NEW-1 chain-date convention; hand-typed tool dates | G1 + M3 tool change (`--recorded-at` defaults to the clock; future and non-monotone refused) | caught |
| B1 NEW-2 candidate id/as-of carry 2026-10-19 | G1 R1 on `9bf11201` (added as-of); B1's whole-tree code-literal test | caught |
| B1 NEW-3 stand-in "retrieved 2026-10-01/02" | G1 R1 (added constants) + R4 (fixture captures carry `capture_kind: stand-in`, no retrieval date) | caught |
| B1 NEW-4 memory makes the 10-10 replay look overdue | G1 R5: the scheduled-date allow entry **expires** at the fire time, forcing a clock- and scheduler-based record; the D-P31.4-1 verify preflight (`date -u` ≥ fire time **and** scheduler `lastAttemptTime`) | caught |
| B1 NEW-5 `sources.toml` rights fields past-dated | G1 R2 (a rights date is an act when the same diff flips `ingestion_permitted`) | caught (`e1cedcad`) |
| B1 NEW-6 sqitch lines can never be corrected; no guard | G2 (`db/sqitch.plan` append-only at EOF) + G1 R1 (`planned_at ≤ commit`) | caught (`062306e7` first; the 6 same-day lines hours ahead also fail) |
| B1 NEW-7 events anchored at 10-21 | G1 R1 on `7a2ff9fa`; M3 monotone `recorded_at` except `correction` events | caught |
| B2 NEW-1, NEW-8 GATE DECISIONS / DEFERRALS history erased | G2 `append-only`, `row-annotate` | caught |
| B2 NEW-2 events mutated in place | G2 `prefix` | caught |
| B2 NEW-3 unjustified transitions | G2 `row-annotate` (lead-token change ⇒ appended transition event + date ≤ commit) | caught |
| B2 NEW-4 dated snapshot edited later | G2 `frozen-snapshot` | caught |
| B2 NEW-5 executed contracts rewritten | G2 `frozen-after-execution` (`> Amended <date -u>` blocks only) | caught |
| B2 NEW-6 ACCEPT-R8 guard text deleted | G4b | caught |
| B2 NEW-7 closed records overwritten | G2 `frozen-after-close` | caught |
| B2 NEW-9 Plan-extension edits; ids P23.1–P23.7 reused | G2 `append-only` + id registry (an id once in the chain table never re-binds to another slug) | caught (`32bea406`) |
| B3 NEW-1 vacuous PHASE-LOG check | G5 V4 + G11 | caught |
| B3 NEW-2 PHASE LOG in five regions | G5 V4 (single EOF append target) | caught |
| B3 NEW-3 top-insertion evades removal-only guards | G2 append-position | caught (20 commits) |
| B3 NEW-4 closeout journal abandoned | M6's CI rule (cell move ⇒ transition); the journal stays shadow | partial |
| B3 NEW-5 `closeout_protocol` authority defaults to main worktree | a unit test with a sibling-worktree fixture in the code fix (F5), not a verification-layer guard | not a guard target |
| B3 NEW-6 CURRENT STATE not machine-readable | G5 V2 | caught |
| B3 NEW-7 7 `PR pending` rows; kind off-vocabulary | G5 V5 | caught |
| B3 NEW-8 PHASE LOG entries are essays | G5 V4 (≤ 2,048 B per entry) | caught |
| B5 NEW-1 harness never recorded | G5 V12 | partial (self-reported) |
| B5 NEW-2 CI read only in CI tickets; protection never applied | G3a/G3b + G3d | caught |
| B5 NEW-3 gate census | G4a | partial |
| B5 NEW-4 rows without a round; off-stack PR #148 | G5 V13 + G3c | caught |
| B5 NEW-5 tail certified the repo against itself | G10 tail sweep + live-claim binding | partial (checks citation, not truth) |
| B5 NEW-6 acceptance hid the layer reached | G7 capstone two-sum check + layer tags | caught (headline) |
| B5 NEW-7 bookkeeping load | process cost (OM-02) | not a guard target |
| B5 NEW-8 failing pins relaxed | G6 | caught |
| F2b NEW-1 75 boilerplate MET-DIFFERENTLY | G7 (MET-DIFFERENTLY must name an ADR or RISK row that names the id) | caught (B4 replay: 74 of 77 cite no ADR anywhere) |
| F2b NEW-4 matrix checker in no gate, structure only | G7 | caught |
| F2b NEW-6 owed legs with no D-row | G7 requires `owed_legs` for MET-ENGINEERED; it cannot discover a leg nobody recorded | partial |
| F2b NEW-7 keepalive never run | G10 monitoring liveness (first-fire watch) | partial (detects after the due time) |
| F2b NEW-3 eval MET contradicted by the operated path | G10 claim-marker rule (DR-C3-03: "human-verified" needs a human-completion marker) | partial |
| F2b NEW-2, NEW-5, NEW-8 (false-corroboration guard inert; contributor-safety claims; leverage measures) | product/governance defects, routed to F2a/E2/C6 | not verification-layer |
| C3 §5 causes 1–7 | DR-C3-01/02/05/07/09/10/12/15, placed by G10 (§4 G10) | catchable by C3's checks |
| C4 NEW-11/27/32 fixture candidate, unmarked fixture builds, future dates | G10 sentinel scan + G1 | caught |
| C4 NEW-10 `rsync --delete` would wipe the release tree | G1-ops SIG-OPS-004 (single publish path) | caught (G1-ops) |
| H1 NEW-2/4/5 unpinned toolchain, cancelled `main` runs, unbounded merge loop | G3e, G3d (`cancel-in-progress` for PRs only), H2's bounded loop | caught (H2 decides) |
| E1 NEW-9 decisive meaning supplied by the recorder | G4a hedge lint + OM-09 confirming row | partial |

### 2.3 What no repository check can catch, and why

1. **Authenticity of the operator's words and signatures.** Agent sessions commit as the operator (`Steve Vitali`)
   and run `gh` with the operator's token. So any in-repo marker, PR comment or approval can be produced by an agent.
   G4 proves **consistency** (readout == ledger row verbatim, dated from the clock, agent text labelled and
   confirmed), not **origin**.
   - The only mechanical control is an operator-held signing key that agent sessions never load, for example a
     passphrase- or hardware-backed SSH key, used only for gate-signature commits. CI would verify it with
     `git verify-commit` against a committed `allowed_signers` file.
   - This is an operator decision (Q-B4-2). The cost is a few extra signing steps per round.
2. **Semantic truth of a status or disposition** (F-28 D-SOURCES.12-1; F1 NEW-2/3, "DONE" rows whose own verify
   rule fails live). A check can require evidence and a probe citation; it cannot read meaning. The mitigation is
   REC-tail re-verification with evidence, the F1 method.
3. **Whether a blanket or pre-authorized rule was wise** (GL-GATE-07's breadth), or the quality of a counsel
   determination. G4a checks only the shape: item ids, expiry, verbatim words.
4. **Independence of reviews** (P6). This is a dispatch property, not a file property.
5. **Back-dating outside act positions.** A prose note dated in the past has no anchor to compare against.
6. **Production mutations at the moment they happen** (F-38). The repository sees them only as drift afterwards
   (SIG-OPS-005).
7. **Which harness actually ran.** Trailers and headers are self-reported (F-37).
8. **Whether a prose claim about production is true.** G10 checks that it cites a probe run, not that the probe
   measured the right thing.

---

## 3. Common machinery (shared by G1, G2, G4, G5)

- **One stdlib tool:** `docs/build/tools/memory_guard.py`, with the subcommands `dates`, `append-only`, `readouts`,
  `ledger`, `all` and `replay`. It needs no uv, so it runs in the CI `docs` job next to the bash detectors, and it
  follows the SIG-MEM-003 report conventions: a caller-selected path and a recorded input identity.
- **Policy files** live under `docs/build/tools/record_policy/`. B2's proposed `docs/build/APPEND_ONLY.toml` would
  itself violate BM-LAYOUT-01: `check-build-memory.sh:161` has no such root entry (B4 NEW-5).
  - `append_only.toml`: B2 §7 regions and modes;
  - `dates.toml`: record positions and the future-date allow-list;
  - `readouts.toml`: the guard sentence, the Status vocabulary and the block markers;
  - `living_records.toml`: the paths G6 treats as living;
  - `ci_required.toml`: the required check names for G3.
- **Inputs by mode:**
  - `--range BASE...HEAD` (PR: `github.event.pull_request.base.sha…head.sha`; locally: the LEDGER `chainTip`);
  - `--first-parent SHA` (push to `main`, including merge commits);
  - `--staged` (pre-commit; commit time = now);
  - `replay FROM..TO` (read-only backtest over `git rev-list --first-parent`).

  Each added line carries its own commit's committer time (`git log -p --format=%H%x09%cI BASE..HEAD`). `CI_NOW` is
  the runner's `date -u`.
- **Report:** `memory-guard/1`, shaped
  `{input:{repo, base, head, ci_now, policy_sha256}, checks:[{check, candidates, evaluated, violations:[{path, line,
  commit, rule, message}]}], exit}`.
  - Exit codes: 0 clean, 1 violations, 2 usage or not a build-memory repo, **3 vacuous** (G11).
- **Where it runs.**
  - **`make docs-check`** gains:
    - `docs-check-memory` (`memory_guard.py all`);
    - `docs-check-spec` (`check_spec_src.py`);
    - `docs-check-matrix` (`check_coverage_matrix.py` + `check_backlog.py`);
    - `docs-check-projection` (`current_projection.py verify`, from seed C9 on).
  - **CI `docs` job:**
    - runs on `pull_request` **and** on `push` to `main` (today: PRs only, `ci.yml:28`);
    - already has `fetch-depth: 0`, which the history-aware guards need; the `python` job's shallow checkout
      cannot host them.
  - **Nightly:** `memory_guard.py replay` over the whole history against the committed oracle (below). This makes
    the guard's own behaviour a regression-tested invariant.
  - **Pre-commit (opt-in):** `scripts/hooks/pre-commit` runs `memory_guard.py dates append-only --staged` (< 1 s). The
    OPERATING MODE SETUP step runs `git config core.hooksPath scripts/hooks` in the build worktree. There is no
    pre-commit framework in the repo today (no `.pre-commit-config.yaml`).
  - **Orchestrator boundary:** at confirm-the-close (orchestrate-build §2.3), `make docs-check` and then
    `ci_boundary.py` (G3). It is binding through the OPERATING MODE rule in-repo, and is wired into the skill by B6.
- **Main-branch concurrency.** `cancel-in-progress: true` for every ref (`ci.yml:18`) cancelled 28 of 30 `main` push
  runs in the last two sittings (H1 NEW-4). Recommendation to H2:
  `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`, so every merge commit is memory-checked.
- **Replay oracle.** B3 plans to promote `data/date_drift.csv` and `data/append_only_violations.csv` under
  `docs/build/reports/memory-repair/`. `tests/unit/fixtures/memory_guard/replay_expected.csv` is derived from them
  plus this note's position and planning replays, one row per `(commit, path, rule)`. The replay must flag every
  oracle row and must pass B2's 405 benign rows. Tolerance: B1's classification is heuristic, so a disagreement is
  reviewed by hand before the oracle changes, never silently re-baselined.
- **Unit fixtures.** `tests/unit/test_memory_guard_*.py` build a throw-away git repo per case in `tmp_path`, commit
  with `GIT_COMMITTER_DATE`, and run the guard. This is deterministic and needs no network. Every rule has one passing
  and one failing case, each drawn from a real commit named in §4.

---

## 4. Guard specifications

### G1 — `record-dates` (item a)

**Record positions** (`dates.toml`, per path glob; the date is the capture group). The strict rules apply only
here. Dates elsewhere in prose are a warning in `docs/build/**`, so evidence notes such as this one can quote wrong
dates.

| path | position | class |
|---|---|---|
| `docs/build/LEDGER.md` | PHASE LOG bullet lead `^- (\d{4}-\d\d-\d\d)`; Round-11 GATE DECISIONS column 1; `updatedAt:` | act |
| `docs/build/BUILD_INDEX.md` | the `landed` column, located by header name | act |
| `docs/build/runs/*.md`, `pr/*.md` | header stamps `^(Date\|Closed\|Landed\|Recorded):` | act |
| `docs/build/readouts/*.md` | `Date:` in Authority/Signature lines; confirmation stamps | act |
| `docs/tickets/DEFERRALS.md` | a status lead `(OPEN\|PARTIAL\|DONE\|WONTFIX) (\d{4}-…)` in an added or changed cell | act |
| `docs/tickets/00_MANIFEST.md` | `## Plan extensions` bullets | act |
| `docs/adr/ADR-*.md` (added files) | `**Date:**` | act |
| `docs/research/_meta/spec_src/**` | dated landed-status parentheses and App F/G rows in added lines | event |
| `docs/build/reports/obligations/*.jsonl` | `recorded_at` (act); `observed_at`, `assessed_at` (event) | — |
| `db/sqitch.plan` | a new line's `planned_at` | act |
| `connectors/src/connectors/data/sources.toml` | `rights_reviewed_on`, `last_verified`, `retrieval_date` when the same diff adds the row or changes `ingestion_permitted` | act |
| `docs/build/planning/*/META_PLAN.md` | change-log bullets `^- (\d{4}-\d\d-\d\dT\d\d:\d\dZ)`; CURRENT STATE `updatedAt:`; verbatim-decision stamps `\((\d{4}-…Z)\)` | act |
| `ops/src/**`, `exports/src/**`, `web/src/**`, `connectors/src/**` | ISO-date string literals in added lines | event |

**Rules.**
- **R1 not-after (all positions).**
  - A timestamp *d* must satisfy *d* ≤ min(commit_time + 5 min, CI_NOW + 5 min).
  - A date-only *d* must satisfy *d* ≤ max(commit UTC date, committer-local date), the B1 convention.
  - An unparseable stamp in a record position (e.g. `18:2xZ`) takes its lowest reading and is also reported as
    malformed.
- **R2 not-back-dated (act positions).** *d* ≥ commit_time − 48 h, unless the line carries `≤`, `retro: <evidence>`
  or `as-of <sha|#PR|url>`. Legitimate late recordings then say so.
- **R3 correction context.** A date that fails R1 is accepted only if both of these hold:
  - the line is a correction (`DATE CORRECTION`, `recorded … → true …`, `corrected from`);
  - the line also holds a date that passes R1/R2, i.e. the true date.

  The `recorded_value` column of `reports/memory-repair/date_corrections.csv` is exempt.
- **R4 fixture captures** (tree check, early ticket). In fixture or stand-in packets, `retrieved_at`, `observed_at`
  and `searched_at` must be ≤ the fixture's own commit time. A hand-authored document carries `capture_kind: stand-in`
  and no retrieval date (B1 §5.4, OM-06).
- **R5 future-ok.** Either an inline `future-ok: <scheduled|real-world|synthetic|illustrative>: <reason>` (`#` in
  code/TOML, `<!-- -->` in Markdown), or a JSON/TOML field on the allow-list (`valid_from`, `valid_to`,
  `expiry_date`, `end_date`, `effective_date`, `due_date`, `next_run`, `schedule_time`, `deadline`), or a
  `dates.toml [[allow]]` entry `{path, pattern, class, reason, expires}`.
  - **An expired allow entry fails.** For example, the D-P31.4-1 replay entry expires at 2026-10-10T03:35Z + 1 h.
    The record must then be updated from the scheduler's `lastAttemptTime`, so the clock, not the latest memory
    date, decides what is overdue (B1 NEW-4).
  - Test code marks synthetic future timestamps with the `SYNTHETIC_` name prefix or `# future-ok: synthetic`, as B1
    §4 asked.
- **R6 commit-clock sanity.** commit_time ≤ CI_NOW + 5 min.

**Failure message.**
`record-dates R1: docs/build/LEDGER.md:463 (added in 7a2ff9fa, committed 2026-09-28T05:13:58Z): record date
2026-10-21 is 22 d after its commit. Write the time from \`date -u\` at recording; if the date is scheduled or
real-world, mark it \`future-ok: <class>: <reason>\` (docs/build/tools/record_policy/dates.toml).`

**Fixtures.** Each is a pass/fail pair:
- a PHASE LOG entry on the commit day (pass) vs +1 day (fail, the ADR-065 `305f94d5` shape);
- `2026-10-19` at 2026-09-28T03:49Z (fail, `95c8a73f`);
- 09-10 at 09-13 in an act position (fail, R2, Round 3);
- a planning change-log bullet +145 min (fail, `1b9b57b2`);
- a correction line quoting 10-19 with `≤ 2026-09-28T03:49Z` (pass, R3);
- the 2026-10-10 replay with `future-ok: scheduled` (pass) vs the same after expiry (fail);
- a sqitch line planned 2026-10-02T12:00 committed at 2026-09-25T08:09Z (fail) vs planned one minute before the
  commit (pass);
- a jsonl `recorded_at` of 10-21 at 09-28 (fail);
- an `ops/src` literal `"2026-10-19 operator choice"` (fail) vs `valid_from = "2027-06-30"` (pass).

**Replay (B1 register + B4 blame).**
- **70 chain commits** add 502 future-dated records:
  - memory 261, release-identity 75, fixture 53, code 49, ADR 31, spec 15, sqitch 12, jsonl 6;
  - the first is `305f94d5` and the last is `b051732c`.
- **22 commits** add 87 back-dated rows (R2 catches the act positions among them).
- **This planning round:** 17 commits of `META_PLAN.md` (`6266f393` … `41ab9521`) and the "18:2xZ" decision stamp in
  `e5725b7b` (B4 NEW-1).

**Placement.** R1, R3, R5 and R6 in diff mode land **in Stage B before C1**. The reasons:
- C4 writes DATE CORRECTION entries, which exercise R3;
- T1 writes ADR `Date:` headers;
- T5 writes GATE DECISIONS rows.

R2, R4 and B1's whole-tree code-literal test come with B1's constant-fix tickets, since the tree check fails until
`release_candidate.py` and its siblings are fixed.

**Requirement:** DRAFT-MEM-1.

### G2 — `append-only` (item b; B2 §7 plus four amendments)

**Modes.** As in B2 §7: `append-only`, `placeholder-fill`, `row-annotate`, `frozen-snapshot`,
`frozen-after-execution`, `frozen-after-close`, `frozen-after-landing` (only a `Superseded by ADR-NNN` status line may
be appended, and ADR-NNN must exist), and `prefix` for `*.jsonl`. B3 adds `living-archived`: the LEDGER head may be
replaced only if the removed bytes equal a file added under `reports/memory-repair/` in the same commit. The four
B4 amendments:
1. **Append position.** In an `append-only` region an addition is legal only as one contiguous block after the
   region's last non-blank line (after the last row, for tables). Additions elsewhere, including extra text inside an
   existing row, fail. Replay: **20 commits**, 18 of them top-insertions into GATE DECISIONS (`307161ee`, `ddf3ad29`,
   … `a33cd6ec`, `95c8a73f`, `4127dbf3`) plus the in-row cross-references `32bea406` and `b1250f62`. B2 classed the
   last two benign; under Round-11 policy they become appended notes. B3 NEW-3 shows that removal-only guards cannot
   see this.
2. **Policy location** under `docs/build/tools/record_policy/` (B4 NEW-5).
3. **`db/sqitch.plan`** is `append-only` for the whole file (no line removed or changed; new lines at EOF). Together
   with G1 R1 this is B1's missing guard.
4. **Chain-id registry.** An id that ever appeared in the manifest chain table never re-binds to a different file slug
   (B2 NEW-9: P23.1–P23.7 reused at `32bea406`). The check scans `git log -p` of the chain table; the output is cached
   in the report.

The planning ledger's §11 change log and §7.1 decision records are `append-only`; its CURRENT STATE block is living.

**Rule text (core).** Removed lines in a protected region must be 0, apart from whitespace- or escaping-equivalent
pairs and verbatim moves within the region. Added lines must satisfy the region's mode.
- **Push to `main`:** the merge commit is diffed against its first parent.
- **Stacked PR:** diffed against its base branch.

**Failure message.**
`append-only [append-only]: docs/build/LEDGER.md §GATE DECISIONS: 56 lines removed in c2055d96 (2026-09-18T20:14Z).
Protected regions change only by appending at the region end; restore with an appended "RESTORED from <sha>^"
block (record_policy/append_only.toml).`

**Fixtures.** B2 §7 already lists one passing and one failing diff per mode, drawn from `c2055d96`, `7a2ff9fa`,
`b542f236`, `4e0dd070`, `b87c279c`, `0a715fcc`, `7671b511` and `d8bcd3ab`. Add three more:
- `307161ee` (fails on position);
- B3's C6 (passes as `living-archived`);
- a fabricated C6 whose archive file differs by one byte (fails).

**Replay:** exactly B2's 42 `loss` + 4 `transition-unjustified` rows (**25 commits**, `c180c748` …
`4127dbf3`), plus the 20 position commits. The 405 benign rows pass.

**Placement.**
- **Core in Stage B, before C1:** `append-only` with position, `living-archived`, readouts (append-only except
  `Status:`) and a `prefix` byte check. It replaces the "0 removed lines on protected paths" half of B3's planning-side
  `seed_verify.py` with product code, so the seed PR's own CI proves it.
- **The remaining modes** (`row-annotate` with event coupling, `frozen-*`, `placeholder-fill`, jsonl schema and
  chaining) come with **M1/M6**.

**Requirement:** DRAFT-MEM-2 (the SIG-MEM-00x that B2 §7 asked for).

### G3 — `ci-boundary` (item c)

**G3a — boundary gate** (`docs/build/tools/ci_boundary.py`; binding through OPERATING MODE R2 / OM-05; skill wiring
via B6).
- **Inputs:**
  - the PR number (BUILD_INDEX row, or `gh pr list --head <branch>`);
  - `gh pr view <n> --json headRefOid,baseRefName,state`;
  - `gh pr checks <n> --json name,state,bucket,completedAt,link`, plus `--required` once protection exists;
  - `ci_required.toml`: `python`, `docs`, `composed`, `security`, `web`;
  - the stack: every open Round-11 PR from the first Round-11 PR (base `devin/p33-8-agent-docs-refresh`, #190, 5/5
    green) up to *n*.
- **Rule.** The PR head equals the local `chainTip` commit. Every required check is present with `bucket = pass` on
  that head, and so is every open ancestor in the stack; an inherited red still blocks (OM-05) unless GATE DECISIONS
  holds a verbatim operator waiver naming the PR and the check. The outcomes:
  - **pending:** bounded wait (poll 60 s, ≤ 45 min), then **exit 4**;
  - **fail, cancel, a skipped required check or a missing check:** **exit 3**;
  - **`gh` unavailable:** **exit 5**. This is never treated as green.
- **Output.** A `ci-boundary/1` JSON record in the run ledger, plus one PHASE LOG field:
  `ci: pass #192@3f2a1c0 (python 3612…; docs …; composed …; security …; web …)`.
  - On exit 3/4/5 the orchestrator writes
    `blockedOn: CI <fail|pending|unknown> on #<n> (<job>): <first failing line>`, leaves `nextTicket` unchanged and
    stops (OM-12/OM-18).
  - A local-only result is written `locally-green`, never green (P11).

**G3b — recorded-CI verifier** (CI `docs` job; early ticket). For every Round-11 PHASE LOG `done` entry and run-ledger
`ci:` line added by the PR (all of them, nightly), `gh api repos/{owner}/{repo}/actions/runs/{id}` must return a run
whose `head_sha` equals the recorded sha and whose conclusion equals the recorded state. A `done` entry with no `ci:`
field fails. This makes "green" auditable after the fact and catches fabricated or stale claims.
- The closeout commit re-triggers CI on PR *N*. The chain of truth is: G3a at *N+1*'s dispatch reads *N*'s final head.

**G3c — external-state delta** (inside G3a). At each boundary, record:
- `origin/main`'s sha;
- `git merge-base --is-ancestor origin/main <chainTip>`;
- PRs merged since the last boundary (`gh pr list --state merged --search "merged:>=<last boundary>"`);
- open PRs whose head is no chain row.

An off-stack merge, or a chain PR retargeted or rebased by anyone other than the operator's documented procedure,
sets `blockedOn` (OM-03). Otherwise the facts go into the boundary line and the operator digest (OM-17). Replay:
#148 (off-stack, merged 2026-09-26T03:07Z); the #191/#112–#130 and #131–#140 sittings; `d4522d82`.

**G3d — branch protection and required checks** (operator action; H2 decides the policy). Recommendation:
- make the `main` ruleset active (today `enforcement: disabled`, `protected:false`, H1 §1.1);
- require a PR, with required checks {python, docs, composed, security, web};
- block force-push and deletion; keep merge commits, which is the operator's method.
- **Timing:** turn it on **after** the #141–#190 integration, or grant admin bypass for that sitting. #165, #179 and
  #185 are red on their own heads (H1 §2b), so protection would block the bottom-up merge H1 recommends.
- The stacked chain never merges into its bases, so required checks do not protect it. G3a does.

**G3e — toolchain pin** (H1 NEW-2; early ticket). `web/.nvmrc` + `engines` + `actions/setup-node` with
`node-version-file` + `npm ci --engine-strict`. A unit test asserts that CI's node major equals `.nvmrc` and that
the devDependency `engines` ranges are satisfiable (license-checker-rseidelsohn@5.0.1 needs node ≥ 24 / npm ≥ 11; CI
runs 22 / 10.9.8).

**Replay (live-read, `gh run list`).**

| red head | failed run (completed) | next dispatch | G3a result |
|---|---|---|---|
| #141 `fa0d67a8` (P31.5 pause) | 36092963615, 2026-09-25T04:09:25Z (`npm ci`) | P31.6, #142 created 07:27:56Z | `blockedOn`; #142–#154 never stacked red |
| #165 `42bb286a` (insert P32.10a) | 36312594389, 2026-09-27T10:31:38Z | P32.10a, #166 10:50:25Z | `blockedOn` until the 170.5 cell is fixed |
| #179 `c4aafa20` (pause; malformed row from `a97aaca2`) | 36346856782, 2026-09-27T20:13:09Z | P32.23a, #180 2026-09-28T02:11:11Z | `blockedOn` at the resume |
| #185 `4127dbf3` (post-close signature) | 36467709050, attempt 1 created 18:47:44Z | P33.4, #186 19:36:22Z | `blockedOn`; the pin is removed explicitly (OM-15) instead of relaxed inside P33.4 |

**Placement.**
- **Stage B:** `ci_boundary.py` and the R2 rule. T5 cites the rule; T6 runs the script on the seed PR ("5 checks
  green"), and the first Round-11 boundary uses it.
- **Early ticket:** G3b, G3c and G3e.
- **Operator:** G3d.
- **B6:** the skill hook.

**Requirement:** DRAFT-MEM-3, plus the SIG-ENG-031 amendment (DRAFT-ENG-5).

### G4 — `gate-record` and `readout-authorship` (item d)

**G4a — GATE DECISIONS shape** (B3 V8 extended). Round-11 rows use
`| date (ISO Z) | ticket | gate | item | answer — operator's words verbatim | consequence | kind |`, where
kind ∈ {`decision`, `pre-authorization`, `confirmation`, `waiver`, `date-correction`}. Checks:
1. The date passes G1 R1/R2.
2. The answer is a quoted verbatim string or `provided: yes/no` (P14).
3. **Answer after pause.** A `decision` row for a gate marker is dated at or after that gate's PHASE LOG `pause`
   entry in the same round. An earlier answer must be typed `pre-authorization` and list explicit item ids and an
   `expires:` (ticket or date) (OM-10).
4. **Hedge lint.** An answer containing `?`, "I wonder", "perhaps", "maybe", "should just", "I think … but" needs a
   later `confirmation` row for the same gate/item with a plain yes/no before any consequence is acted on (OM-09).
5. **Delegation lint.** "for me", "on my behalf", "sign … for me", "your judgement", "delegate" in a signature or
   attestation context is an error: an agent never signs (OM-08).

**G4b — readouts** (`readouts.toml`).
1. **Guard sentence.** Every readout created or modified after the policy commit contains exactly: *"An operator or
   authorized human record supplies the decision; an agent must not sign or assume silence is approval."*
   - Existing readouts are grandfathered until M4 appends their `## Readout history (restored from <sha>^)`.
   - **Today 0 of 11 readouts contain it.** The build-memory `GATE.md`/`HUMAN.md` templates do not carry it either
     (B4 NEW-8).
2. **Append-only.** Readouts are append-only except the single `Status:` line, which may move from `PENDING…` to
   exactly one of {SIGNED, PASSED, SKIPPED-BY-OPERATOR, NOT-PASSABLE}. Checkbox ticks are forbidden in a signing
   diff; the signature block states what the operator declares met, by quoting.
3. **Signature block, appended.**
   ```
   ## Signature
   Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
   GATE DECISIONS row: <date> | <gate>
   <!-- agent-drafted:begin sha256=<64 hex> -->
   …agent-written summary, if any…
   <!-- agent-drafted:end -->
   Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:<first 12>
   Signed by: repository operator. Recorded by <agent/harness>, which does not sign.
   ```
   Checks:
   - the quote equals the GATE DECISIONS answer after whitespace normalisation;
   - each agent-drafted block's sha256 matches its bytes and has a confirmation line whose words also appear
     verbatim in a `confirmation` row;
   - any added prose outside a quote or an agent-drafted block fails;
   - dates pass G1.
4. **Optional G4c** (operator decision, §2.3): the signature commit is signed with an operator-only key and verified
   in CI.

**Failure messages.**
- `readout G4b-2: docs/build/readouts/GATE-G3.md: signing diff 95c8a73f removes 6 lines incl. the guard sentence;
  signing may only change the Status line and append a Signature block.`
- `readout G4b-3: decision text does not equal the GATE DECISIONS answer "I sign/accept. Please proceed" and
  about 3 KB of unlabelled text was added outside an agent-drafted block.`

**Fixtures.**
- the pending→signed pair from `95c8a73f^`/`95c8a73f` (fail) vs a correct appended signature (pass);
- an agent-drafted block with a mismatched sha (fail);
- the `0a715fcc` delegation phrase (fail);
- the GL-GATE-08 hedge with no confirming row (fail) vs with one (pass);
- a pre-authorization without `expires:` (fail).

**Replay:** `0a715fcc`, `95c8a73f`, `4127dbf3`, `3259ca81` (G4b); `c2055d96` (GL-GATE-08 hedge; GL-GATE-01…05
delegation with no item ids or expiry) (G4a).

**Placement.**
- **Stage B:** G4a table form, the verbatim answer, G1 dates, and the guard sentence for **new** readouts. T5 writes
  the GATE-M and GATE-P rows, and GATE-B's row is written at C10.
- **Before the first Round-11 gate readout is signed:** the full G4b.
- **B6:** the templates.

**Requirements:** DRAFT-MEM-4 and DRAFT-MEM-5.

### G5 — `ledger-contract` (item e; B3 V1–V11 adopted, plus V12–V14)

B3 §6 V1–V6, V8, V9 and V11 are adopted as written. V7 is G2 and V10 is G1. Additions:
- **V5+ row well-formedness.** Every BUILD_INDEX row parses to the header's column count. An unescaped `|` in an
  evidence cell (`a97aaca2`, the #179 red) fails.
- **V12 harness.** Round-11 run ledgers start with `Harness:` and `Model:` lines, and every commit in a Round-11 PR
  carries a harness trailer (OM-01).
  - **Conflict to resolve at S1 (B4 NEW-10):** B5 OM-01 puts `harness:` in CURRENT STATE, while B3 fixes CURRENT
    STATE at the 19 BM-LEDGER-02 keys, so an added key fails the existing key-order check.
  - Proposal: carry the harness in `dispatchTarget`'s value and in run-ledger headers until B6 adds a key upstream.
- **V13 manifest rounds.** Every chain row sits under a round banner (B5 NEW-4: rows 88–116 had none). Ids are
  never reused (G2 registry).
- **V14 planning-ledger freshness** (for `docs/build/planning/*/META_PLAN.md`):
  - CURRENT STATE `updatedAt` ≥ the newest change-log entry;
  - `lastCompleted` names the newest unit marked done in the change log;
  - `nextUnit` is not a done unit.

  Replay: every META_PLAN commit from `6266f393` (E3 done, 16:52:52Z) onward, 17 commits (B4 NEW-2).

**Replay for V1–V3 (B4, over 194 LEDGER versions at `b051732c`).**
- V1: head > 12,288 B in **121** versions, first `2a5d01e0` (14,182 B).
- V2: `projectStatus` off-enum in **128** versions, first `0ea9be15` (`IN-PROGRESS`).
- V3: `.agents/scratch` in the head of every version since `4d5a5d27`; "Do not resume until Codex reports" since
  `d6c562e5`.
- V4/V5: per B3 §2.4/§2.6.

**Placement.** B3 applies: `seed_verify.py` (planning-side) accepts C1–C10, and the product validator is **M2**,
which must be among the first Round-11 rows. V14 can be used at once by the planning orchestrator, which owns its
own ledger. **Requirement:** DRAFT-MEM-6.

### G6 — `living-record-tests` (item f)

**Rule** (AST lint, `tests/unit/test_no_living_record_pins.py`, runs in `make check`). A test that reads a path
listed in `living_records.toml` from `REPO_ROOT` (not `tmp_path`) must not contain:
1. a string literal matching a CURRENT STATE `key: value` (`nextTicket: HUMAN-H4`);
2. an assertion that a **named** obligation, requirement or readout has a specific status;
3. `len(<derived from a living record>) == <int literal>`;
4. a literal row range or date (`"rows 1-200"`).

Allowed: vocabulary membership against the policy's constant, uniqueness, generated == source, path/reference
resolution, append-only properties, and assertions over **frozen** artifacts (dated reports, `PLAN.json` of a closed
round), which are listed as `frozen` in the policy. The escape hatch is
`@pytest.mark.living_record_invariant("<why this holds at every commit>")`, listed in the policy with its reason
(grep-able, reviewed). **A failing pin is converted or deleted, never relaxed in place** (OM-15).

**Backtest.** Run the real-tree tests from commit *C* against the tree at the next commit *C′* that legitimately
changed a record (read-only, nightly). A pin fails exactly at the #165/#179/#185 transitions.

**Inventory and required actions** (living paths only; fixture-based tests are unaffected).

| test (file:line) | asserts | class | action and when |
|---|---|---|---|
| `test_agent_docs_current_state.py:83-89` | `lastCompleted: P33.8`, `nextTicket: HUMAN-H4`, `projectStatus: IN-PROGRESS` | living pin, **and it pins the off-enum value F-23 flags** | **delete in Stage B**: C6/C8 turn it red. G5 V2 replaces it |
| `…:77-80` | README `rows 1-200` | living pin | **convert in Stage B**: README range == max BUILD_INDEX seq |
| `…:59-63` | SIG-MEM-004 verdict `== "MET"` | living pin (T4 may re-verdict) | **convert in Stage B**: verdict ∈ vocabulary and MET ⇒ evidence (G7) |
| `…:66-74` | BUILD_INDEX contains P33.8 + runs/pr files | history fact (append-only) | keep; mark invariant |
| `test_capstone_closure_round10.py:143-157` | exactly 18 P33.3 annotations, all leading OPEN/PARTIAL | living pin (any legitimate closure flips one) | **convert in Stage B**: a lead change requires an event (G2 `row-annotate`) |
| `…:120-127` | every **current** OPEN deferral appears in the dated §(f5) register | living ↔ frozen coupling; T4's new D-rows turn it red | **convert in Stage B**: restrict to ids that existed at the packet's commit |
| `…:160-196` | readout ∈ {PENDING, SIGNED} + provenance (the #186 rewrite) | invariant-shaped | keep; move under the G4 policy |
| `…:52` | `len(ids) == 38` over the 2026-09-25 `PLAN.json` | frozen artifact | keep; mark frozen |
| `test_build_memory_audit.py:323-347` | real tree: zero errors **and** conflict set `== {"D-P21.5-1"}` | mixed | **Stage B**: keep zero-errors, delete the set equality |
| `…:350-367` | D-P31.4-1, D-R10-* stay OPEN/PARTIAL | living pin; **the 2026-10-10 replay can legitimately close D-P31.4-1 and turn CI red** | **delete in Stage B**; G2 `row-annotate` covers the real risk |
| `test_repo_docs_current_state.py` (8 tests, P33.7) | README/CHANGELOG wording | living doc pins | early ticket: move to the docs-freshness detector or delete |
| `test_round10_integration_plan.py` | a dated report + constant PR list | frozen artifact | keep; mark frozen |
| validators: `check_coverage_matrix.py:32` `EXPECTED_ROWS = 715`; `check_spec_src.py:41-42` `BASELINE_IDS`/`FOLD_BACK_IDS` | pinned counts | a validator pinning living state (B4 NEW-7) | **with T1/T4**: derive the count from spec definitions; keep the fold-back list as an explicit registry checked against App G |

**Replay (commits that added the pins):** `a3653d76` (P32.1), `e8bc0179` (P33.3), `6e93b098` (P33.7),
`c77bd45e` (P33.8).

**Placement.** The conversions marked "Stage B" go in the pre-C1 guard commit; without them C9's "make check green"
cannot hold (B4 NEW-3). The lint itself is an early ticket.

**Requirement:** DRAFT-ENG-1.

### G7 — `spec-and-verdicts` (item g)

1. **Wiring.** `check_spec_src.py`, `check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv` and
   `check_backlog.py` go into `make docs-check` → CI `docs` job; `current_projection.py verify` joins from C9.
   Collect `docs/build/tools/test_*.py`: add it to `testpaths`, or move the test under `tests/unit/`.
2. **Derived counts.** The expected row count equals the number of ids defined in the spec. This removes the
   715-constant edit that T1/T4 would otherwise make inside the validator they are validated by.
3. **Verdict grammar** (F2b §2.2, with T4). The enum gains `MET-ENGINEERED(D-id…)` and `WAIVED(ADR-nnn)`, and the
   columns `required_domain`, `achieved_domain`, `owed_legs`, `accepted_scope`.
   - `MET-DIFFERENTLY` must name an existing ADR, or a RISK row, that names the id.
   - `WAIVED` must name an accepted ADR containing the id and `## Revisit trigger`.
   - `MET-ENGINEERED` must have non-empty `owed_legs`.
4. **Cross-checks** against `events.jsonl` heads (F2b §2.4-3):
   - MET citing an OPEN/PARTIAL D-id → error;
   - MET-ENGINEERED whose D-rows are all DONE → error (stale; promote after verifying);
   - MET-ENGINEERED citing a WONTFIX D-row with no WAIVED ADR → error;
   - WAIVED with an OPEN D-row → error;
   - `accepted_scope` set ⇒ verdict ≤ MET-ENGINEERED (a scoped signature never raises a verdict);
   - routing to a ticket that has a BUILD_INDEX row → error;
   - every cited evidence path exists;
   - `achieved_domain ≥ required_domain` for MET.
5. **Capstone two-sum.** A closure packet's headline must equal *engineering closed* = MET + MET-DIFFERENTLY +
   MET-ENGINEERED and *requirement satisfied* = MET + MET-DIFFERENTLY, recomputed from the matrix. MET-ENGINEERED is
   never added into MET (B5 NEW-6; "34 MET").

**Replay on today's matrix** (B4 quick parser, approximate; T4's tool is authoritative):
- 74 of 77 MET-DIFFERENTLY rows cite no ADR anywhere (F2b: 75 boilerplate);
- ≥ 10 MET rows cite an OPEN/PARTIAL D-row (A3 NEW-1 / F2b: 17);
- 21 non-MET rows are routed to landed tickets (F-30: 19);
- 13 of 1,786 cited paths are dead.

The historical replay point: SIG-ENG-039 was marked MET from P20.2 while its checker ran in no gate. Item 1 would
have made that MET true; no check can judge an "evidence" cell's adequacy in general.

**Placement.**
- **Stage B, before C1:** item 1, so T1's `BUILD.sh` output and T4's registers are validated in CI for GATE-B.
- **With T4:** items 2–4, in the same commits that apply the vocabulary, because an unchecked vocabulary change is
  the F-16 failure again.
- **The REC tail:** item 5.

**Requirements:** DRAFT-ENG-2, DRAFT-ENG-3, and the SIG-ENG-039 amendment (DRAFT-ENG-4).

### G8 — `adr-index-and-triggers` (item h)

1. **Index completeness** (SIG-ENG-039 already requires "number, title, and owning phase"). Landed ADR bodies are
   frozen (SIG-ENG-003), so legacy gaps are fixed **in the generator**, not in the ADRs.
   - `adr-index.sh` also parses `# ADR-NNN — <title>` and takes the owning phase from `**Ticket:**`, then
     `**Phase:**`, then `**Phase / ticket:**`.
   - This is a local patch to the vendored copy plus the upstream proposal (B6).
   - The check: every index row has a title, an owning ticket/phase and a status. Today it fails on 79/142/25 rows
     (B4 NEW-6).
   - New ADRs (ADR-146+, written by T1) must use `# ADR-NNN: <title>` and `- **Ticket:**` / `- **Status:**` fields.
     This is a hard failure from T1 on.
2. **Supersession.** An ADR named in any `**Supersedes:**` field carries an appended
   `- **Status:** Superseded by ADR-NNN (<date -u>)` line (the only legal body change, G2 `frozen-after-landing`).
   Today 5 fail (F3 NEW-4: ADR-015, 058 §3, 075, 092, 096 §1).
3. **Revisit-trigger register** (`docs/build/reports/adr_triggers/ADR_TRIGGERS.csv`; F3's ADR-TRIGGER-REGISTER;
   created in T4). Columns:
   - `adr`;
   - `trigger_sha256`, the sha256 of the `## Revisit trigger` section text;
   - `state` ∈ {quiet, fired-unanswered, fired-answered(ref), superseded(ref), dormant(reason)};
   - `evidence`, `probe_id` (optional), `home` (BL id) and `last_evaluated` (`date -u`).

   Checks:
   - exactly one row per ADR;
   - the hash matches the current section, so a changed trigger is visible;
   - an `answered` or `superseded` ref resolves to an ADR file or a chain row;
   - `home` is an **open** BL row unless the state is quiet or superseded (F3 NEW-3: 23 triggers on closed rows);
   - at the round tail, every row's `last_evaluated` falls within the round, and no `fired-unanswered` row lacks an S1
     disposition.
   - A trigger with a `probe_id` flips automatically when its G10 probe fires, e.g. ADR-111 (digest pinning) and
     ADR-098 (cost against the Q-10 ceiling).

**Replay.** At the Round-10 tail the register check would have failed 42 fired-unanswered triggers and 23 closed
homes (F3 §5).

**Placement.**
- **With T1:** the new-ADR rule, as T1's acceptance.
- **In T4:** the register file.
- **Early ticket:** the generator patch and the checkers.
- **B6:** upstream `adr-index.sh`.

**Requirement:** DRAFT-ENG-4 and DRAFT-ENG-6.

### G9 — `round-close-records` (item i): keep or amend SIG-ENG-031? **Amend.**

- **Evidence.**
  - `docs/traceability.md` (320 KB, per-ticket tables) was last written at `f77803df` (2026-09-13).
  - `docs/risk_register.md` was last written at `9866efae` (2026-09-14).
  - Neither was touched across Rounds 3–10, yet SIG-ENG-031 is MET (F-32).
  - The machine-checkable traceability is already `COVERAGE_MATRIX.csv`: `owning_tickets`, tests, and after T4 the
    `coverage-assessment/1` events.
  - Keeping the per-phase clause verbatim guarantees another silent violation.
- **Amendment** (draft text DRAFT-ENG-5, §5).
  - "The traceability matrix" means the coverage matrix, updated through assessment events in the phase's own PRs
    and green under G7.
  - `traceability.md` and `TICKET_VS_SPEC.md` are frozen as historical Phase-0…P18 views, each with an appended
    pointer.
  - The risk register gains one dated, append-only `## Round N review` section at each round close, listing
    new/changed/closed/re-routed risks; at phase level, a phase adds rows only when it creates or retires a risk.
  - "CI green" is defined by DRAFT-MEM-3.
- **Checks at the round tail (REC).**
  - The register gained a section dated within the round.
  - RISK ids are unique (today `RISK-P5-04` ×2 and `RISK-P20-01` ×2 fail; F3 §7.1).
  - Every deferred RISK row has an open BL home (RISK-P21-03 unrouted; F3 §7.2).
  - **Round ↔ spec:** each manifest round banner cites an existing spec section. Round 11 needs its own part (T1),
    and Rounds 2–9 are not retrofitted (F-32 §52).
- **Placement:** amendment text in T1; checks with the REC-tail tooling (early-to-mid Round 11).
- **Requirement:** DRAFT-ENG-5.

### G10 — production-truth probe placement (item j; coordinates G1-ops and C3, adds no duplicate requirement)

G1 owns SIG-OPS-003/004/005/006/008 and C3 owns DR-C3-01…15. B4 fixes **when** each runs, **what evidence** it
leaves, and **three cross-cutting additions**.

| probe (owner) | PR (fixture) | candidate gate | post-publish | scheduled | round tail |
|---|---|---|---|---|---|
| public-route allow-list and absence (SIG-OPS-003) | build-output test | ✓ | every origin, incl. the `sig-web` bucket | 6-hourly | ✓ |
| release record and id on pages (SIG-OPS-004, DR-C3-14) | — | ✓ | ✓ | daily | ✓ |
| attribution sanity (DR-C3-09; J1 NEW-2/3, E1 NEW-4): every row with `rights_attribution_required=1` has holder + terms URL; holder from the source registry, never de-duplicated by licence | fixture export | ✓ bulk files | API sample | weekly | ✓ |
| jurisdiction–coordinate consistency (DR-C3-05/11, F-44): points in the claimed boundary; no (0,0) or swapped axes; one code scheme per dossier slug | fixture export | ✓ | — | — | ✓ |
| API-vs-release parity (DR-C3-12, C3 NEW-1/10): `/v1/dossier/{scope}` == release JSON or 404; `complete:false` when evaluated = 0 | contract test | — | ✓ | daily | ✓ |
| number truth (DR-C3-15) | — | ✓ recompute | — | — | ✓ |
| monitoring liveness (SIG-OPS-006): probe heartbeat ≤ 2 intervals old; alert path delivered; first-fire watch for never-run schedules (G1-08, F2b NEW-7) | — | — | — | ✓ | ✓ |
| live-config drift (SIG-OPS-005) | — | — | — | daily | ✓ |
| **fixture-sentinel scan (B4)** | build output | ✓ | ✓ | daily API sample | ✓ |
| **claim markers (B4, from DR-C3-03)**: "human-verified", "Reviewed", "independent review" need a recorded human-completion marker | build output | ✓ | — | — | ✓ |

**The three additions.**
1. **Fixture-sentinel scan.** It looks for `example.test`, `sig.example`, `_FIXTURE`, `demo_`, `Reviewer A/B`,
   loopback URLs (`127.0.0.1`), `capture_kind: stand-in` without disclosure, and unregistered contact domains
   (`sig-project.org`, E1 NEW-2). A hit outside a declared fixture compartment fails. Replay: it catches:
   - the G3-accepted candidate (C4 NEW-11);
   - `sig.example` IRIs in the live API (F3 NEW-6);
   - the fixture editorial review (E1 NEW-1);
   - `/task/new/` demo pages (G1 NEW-7);
   - the `/curate/` form posting to `127.0.0.1` (F-02).
2. **Live-claim binding.** A Round-11 build-memory, readiness or README statement that asserts production state
   ("deployed", "renders on", "live", "publicly", "0 stale") must cite a `probe-run/1` record (id, `date -u`, result,
   sha256 of the output) no older than 24 h at its commit. G5 checks the citation form and that the record exists
   under `docs/build/reports/probes/` or at a cited GCS path with a digest. Replay: `REPUBLISH_LIVE_2026-09-27.md:77`
   claimed `has_vendor` links render (live: 0; F-10); the P33.4–P33.8 tail's 0 live reads (B5 NEW-5); F1 NEW-2/3.
   This checks citation, not truth (§2.3-8).
3. **No vacuous probes** (G11 applied): a scheduled job that measured nothing fails. Today `observability.yml`
   reports success while skipping the probe (G1 NEW-3, J1 NEW-13).

**Placement:** Round-11 wave 1, "production safety and honesty" (§7.1). The sentinel scan and claim markers ride
with C3/C4's fix tickets; the tail sweep is part of the REC tail contract. **Requirements:** DRAFT-OPS-1 (placement
and evidence), DRAFT-OPS-2 (sentinels), DRAFT-MEM-7 (live-claim binding).

### G11 — `no-vacuous-pass` (cross-cutting)

- **Rule.** Every validator and scheduled check reports `candidates` (items its input offers) and `evaluated` (items
  it actually checked). It exits non-zero when `candidates > 0` and `evaluated = 0`, or when its parse rate falls
  below a declared floor (e.g. PHASE LOG bullets that contain "done" but yield no id).
- **Replay.**
  - The check-build-memory PHASE-LOG loop: 139 candidates, 0 evaluated → fails on every LEDGER version with bolded
    ids (B3 NEW-1).
  - `observability.yml`: 0 measurements → fails (G1 NEW-3).
- **Placement:** M2, for check-build-memory's parser (local patch plus B6 upstream), and the observability fix
  ticket. **Requirement:** DRAFT-ENG-3.

---

## 5. Draft requirement text (drafts; numbering and final wording are T1's)

| draft id | level | guard | text |
|---|---|---|---|
| **DRAFT-MEM-1** | MUST | G1 | **Clock-true records.** Every date or time recorded as an event in build memory, ADR headers, spec landed-status text, obligation events, `db/sqitch.plan`, release identities and product constants MUST come from the system clock at the moment of recording, or from the git or GitHub time of the event with its source named. It MUST NOT be later than the commit that records it. A future date is allowed only for a scheduled, real-world, synthetic or illustrative value that carries an explicit `future-ok` class and reason, or an allow-list entry that expires. CI MUST fail a change that adds a violating record. |
| **DRAFT-MEM-2** | MUST | G2 | **Append-only, proven per change.** Protected build-memory regions, declared in a committed policy, MUST change only in these ways: by appending at the region's end; by filling a declared placeholder; by an annotation that preserves the prior text; or, for a living region, by replacement whose removed bytes are archived verbatim and hash-linked in the same commit. CI MUST check every pull request against its base and every push to `main` against its first parent. |
| **DRAFT-MEM-3** | MUST | G3 | **CI truth at every boundary.** Before closing a ticket and before dispatching the next, the orchestrator MUST read the GitHub checks of the ticket's PR at its current head and of every unmerged ancestor in the stack. A failing, cancelled, missing or unknown required check MUST set `blockedOn` and stop until it is fixed or waived verbatim by the operator. The recorded result (check names, conclusions, run ids, head sha) MUST be verifiable by CI against GitHub. Local-only results are recorded as `locally-green`. Each boundary MUST also record `main`'s head, whether the chain descends from it, and merges since the previous boundary. |
| **DRAFT-MEM-4** | MUST | G4a | **Gate records.** Each gate decision MUST be recorded as a table row giving the `date -u` of receipt, the gate, the item, the operator's words verbatim (or `provided: yes/no`) and the consequence. A decision MUST be dated at or after the gate's pause, unless it is a pre-authorization that lists explicit item ids and an expiry. Words that are interrogative, conditional or hedged MUST be followed by a recorded plain yes/no before any consequence is acted on. No record may delegate a signature or attestation to an agent. |
| **DRAFT-MEM-5** | MUST | G4b | **Readout authorship.** Every gate or human readout MUST contain, from creation and permanently, the sentence "An operator or authorized human record supplies the decision; an agent must not sign or assume silence is approval." A signed readout's decision MUST be the operator's verbatim words, identical to its gate record. Agent-written text MUST sit in labelled agent-drafted blocks whose hash the operator confirmed in words recorded verbatim. Signing MUST only change the status line and append a signature block. |
| **DRAFT-MEM-6** | MUST | G5 | **Ledger contract.** The control ledger's orient region MUST stay within a declared byte budget. CURRENT STATE MUST hold single values from declared vocabularies. Every path named in the orient region MUST exist, and no deny-listed stale token may appear. PHASE LOG entries MUST be appended only at the end of the current round's section, in the fixed shape and size. BUILD_INDEX rows MUST be well-formed and uniquely sequenced, with no placeholders after close. RETURN PASS MUST equal its generated form. Run ledgers MUST name the harness and model. A CI probe MUST show that the documented orient recipe resolves the next unit within budget. Planning ledgers MUST keep CURRENT STATE consistent with their change logs. |
| **DRAFT-MEM-7** | MUST | G10 | **Live claims cite probes.** A build-memory, readiness or README statement that asserts production state MUST cite a probe-run record (id, time, result, output digest) no older than 24 h at its commit. |
| **DRAFT-ENG-1** | MUST | G6 | **Tests assert invariants.** A test MUST NOT assert the current value of a living record: next unit, project status, a named obligation's or readout's status, or counts, row ranges or dates of living registers. Tests over living records assert only properties that hold at every commit. A failing pin is converted or deleted, never relaxed in place. A lint in `make check` enforces this. |
| **DRAFT-ENG-2** | MUST | G7 | **Verdict integrity.** The coverage matrix checker MUST enforce the verdict grammar and parameters. It MUST also cross-check each verdict against the obligation register and `accepted_scope`: no MET with an owed leg; MET-ENGINEERED only with open owed legs; WAIVED only with an accepted ADR and no open leg; a scoped acceptance never raises a verdict. Routing MUST be live, cited evidence MUST exist, and expected counts MUST be derived from the spec rather than pinned. |
| **DRAFT-ENG-3** | MUST | G7, G11 | **Validator gates.** Every build-memory and spec validator MUST run in `make docs-check` and in the CI documentation job on every pull request and every push to `main`. Each MUST report how many items it evaluated, and MUST fail when it evaluated none of a non-empty candidate set. A scheduled job that measured nothing MUST NOT report success. |
| **DRAFT-ENG-4** | amend SIG-ENG-039 | G7, G8 | …the index MUST show, for every ADR, its number, title, owning ticket or phase, and status (the generator derives them from the header forms in use). An ADR named as superseded MUST carry an appended `Superseded by` status. `check_spec_src.py` and its tests MUST run in `make docs-check` and CI. New ADRs MUST use the template header fields. |
| **DRAFT-ENG-5** | amend SIG-ENG-031 | G3, G9 | No phase is complete until every acceptance criterion passes; its PR's required GitHub checks are green per DRAFT-MEM-3, including data-quality checks; new requirements have automated tests; ADRs record every deviation; and the coverage matrix (the traceability matrix) reflects the phase through assessment events. At each round close, the risk register MUST gain a dated round-review section, and the ADR revisit-trigger register MUST be re-evaluated. |
| **DRAFT-ENG-6** | MUST | G8 | **Revisit triggers are monitored.** Every ADR revisit trigger MUST have one register row with a state, evidence, an open home and a last-evaluated date. Fired triggers MUST have a recorded answer (new ADR, ticket or waiver) before the round closes. |
| **DRAFT-OPS-1** | MUST | G10 | **Probe placement and evidence.** Each production-truth probe (SIG-OPS-003/004/005/006/008; DR-C3-05/09/12/15) MUST declare its trigger points (pull request, release candidate, publish, schedule, round tail) and write a probe-run record. The round tail MUST include a full probe sweep. |
| **DRAFT-OPS-2** | MUST | G10 | **Fixture sentinels.** Release candidates, the public web build and sampled live API responses MUST be scanned for fixture and placeholder sentinels (test domains, placeholder IRIs, fixture and demo markers, loopback URLs, undisclosed stand-ins, unregistered contact domains). A hit outside a declared fixture compartment fails the gate. |

---

## 6. Sequencing

### 6.1 Stage B, before seed commit C1: the "guard core" commit (proposed C0.5; answers Q-14 for guards)

**Why before any record is written.**
1. C1–C10, T1, T4 and T5 write exactly the artifact classes where F-21/F-22/F-29 occurred: DATE CORRECTION entries
   that quote wrong dates, restorations, a replaced head, ADR `Date:` headers, and verbatim GATE DECISIONS rows.
2. **This round's own ledger drifted today under the prose rule P2** (B4 NEW-1). That refutes the hope that rules
   alone suffice, and it happened under a different harness from the one B1 associates with the Round-10 drift.
3. GATE-B requires "all validators green + CI green on the seed PR". Only guards that exist in the seed can be part
   of that proof.

| item | size (I) | notes |
|---|---|---|
| `memory_guard.py` core: G1 R1/R3/R5/R6 (diff mode, record positions); G2 `append-only` + position, `living-archived`, readouts, `prefix` bytes; G4a table/verbatim/date checks; G4b guard-sentence presence for new readouts | ~400 LOC stdlib + ~20 fixture tests | supersedes the removed-line half of `seed_verify.py`; the budget and hash checks stay planning-side |
| `record_policy/*.toml` | small | the seed's own allow entries: the 2026-10-10 replay (expires), and correction-context files |
| `Makefile` `docs-check-memory`, `-spec`, `-matrix`; CI `docs` job on push + a memory-guard step | ~30 lines | G7 item 1; `-projection` joins at C9 |
| pytest collects `docs/build/tools/test_*.py` | 1 line | B4 NEW-4 |
| G6 conversions (six pins, §4 G6) | ~80 lines | otherwise C6/C8/T4 turn `make check` red (B4 NEW-3) |
| `ci_boundary.py` (G3a) | ~150 LOC | used at T6 on the seed PR and at the first Round-11 boundary |

If the operator holds Q-14 strictly ("no code in the seed"), the fallback is:
- the same checks run planning-side inside `seed_verify.py`;
- the guard core becomes **row 201**, dispatched before anything else;
- the OPERATING MODE requires a manual G3a-equivalent `gh pr checks` read until it lands.

The fallback leaves T1/T4/T5 unguarded in CI, so B4 recommends the core commit.

### 6.2 Stage B alongside T1 / T4

- **T1:** new ADRs use the indexed header form (G8-1). Draft requirement text from §5 goes into spec_src.
  `check_spec_src` is green in CI.
- **T4:** the verdict grammar, cross-checks and derived counts (G7 items 2–4), in the same commits as the matrix
  deltas. `ADR_TRIGGERS.csv` is created (G8-3). DEFERRALS annotations stay G2-clean. The capstone two-sum rule is
  documented.

### 6.3 Round-11 first wave (memory repair; T3 numbers them with B3's M1–M6)

| ticket | guards | depends |
|---|---|---|
| M1 | G2 full modes + replay oracle + nightly replay | core |
| M2 | G5 V1–V6, V8, V9, V11–V14; G11 in check-build-memory (bold-aware parser) | core |
| M3 | obligation-event tool clock defaults (G1 at the source) | — |
| M6 | G2 `row-annotate` ⇔ transition events in CI | M1, M3 |
| B1-code | G1 R2/R4 + whole-tree code-literal test; sqitch comment corrections; fixture capture markers | core |
| CI-truth | G3b verifier, G3c delta, G3e toolchain pin | core |
| readouts | G4b full + template-conformant restored readouts (with M4) | before the first Round-11 gate |
| pins-lint | G6 AST lint + nightly advance backtest | core conversions |
| adr-index | G8-1 generator patch (local) + G8-2 + G8-3 checker | T4 register |
| rec-tail | G9 checks + G7 item 5 + G10 tail sweep contract | — |

**Later waves:** G10 probes land with G1-ops (R11-OPS) and C3/C4 fix tickets (R11-TRUTH), in the "production safety
and honesty" wave.

### 6.4 Interfaces for B6 (user-global skills; interface only, not designed here)

1. **orchestrate-build §2.3/§2.5:** after confirming a close, call the repo hook
   `docs/build/tools/ci_boundary.py --pr <n> --json <path>` when present.
   - Exit 0 → continue; 3/4/5 → write `blockedOn` from the JSON `summary` field and stop.
   - Remove "no CI polling" from the non-goals (`SKILL.md:313`).
   - `drive-build.sh` must treat a `blockedOn` set this way like any other block.
2. **implement-spec Phase 6.5 close:** run `make docs-check` (which includes the memory guards) before pushing the
   closeout. Take every date from `date -u`. Record the `ci:` field from `ci_boundary.py` after pushing, or
   `locally-green`. Remove "No CI polling" (`:410`, `:490`).
3. **build-memory templates:** `GATE.md`/`HUMAN.md` carry the guard sentence and the Signature-block skeleton (G4b).
   `layout.md` gets the BM-LEDGER-02 enum, the BM-LEDGER-06 kinds (`correction`, `restored`), the 2 KiB entry cap,
   the harness key decision (B4 NEW-10), and the `tools/record_policy/` location. `adr-index.sh` gets the header
   parsing (G8-1). `check-build-memory.sh` gets the bold-aware parser and evaluated counts (G11).
4. **decompose-spec:** the ticket template carries B5's OM clause block plus the AC "no test asserts the current state
   of a living record".
5. **reconcile-build (REC tail):** the probe sweep (G10), trigger-register sweep (G8-3), risk-register round section
   (G9) and capstone two-sum (G7-5).
6. **synthesize-spec** (planning ledgers): V14 freshness and G1 on change-log bullets. B4 NEW-1/NEW-2 show the planning
   harness needs the same guards.
7. **All skills:** the exit-code contract of `memory_guard.py` / `ci_boundary.py`
   (0 / 1 / 2 / 3 vacuous / 4 pending / 5 unknown).

---

## 7. B5 operating rules → guard

| rule | mechanical guard | residue that stays a rule |
|---|---|---|
| OM-01 harness | G5 V12 | truth of self-reported trailers |
| OM-02 close | G5 V4/V5 (a `done` entry ⇒ row + run + `ci:`); G3b | who closed it |
| OM-03 planning | G5 V13; G3c off-stack detection | whether the plan was reviewed |
| OM-04 clock | G1 (+ M3) | — |
| OM-05 CI gate | G3a/G3b | — |
| OM-06 status layers | G7 domains + two-sum; G1 R4 | wording in prose |
| OM-07 gate record | G4a/G4b | authenticity (§2.3-1) |
| OM-08 no proxy signatures | G4a delegation lint; optional G4c | agent holding operator credentials |
| OM-09 tentative ≠ decision | G4a hedge lint | judging hedges the lint misses |
| OM-10 no unbounded pre-answers | G4a pre-authorization fields + answer-after-pause | whether scope is sensible |
| OM-11 human work | obligation-event defer count (M3/M6) | scheduling realism |
| OM-12 blocks | G3a writes `blockedOn`; G3b audits | blocks for non-CI causes |
| OM-13 append-only | G2 | — |
| OM-14 production | SIG-OPS-005 drift detection (after the fact) | prevention |
| OM-15 tests | G6 | — |
| OM-16 size and tail | — (a diff-size warning is possible; not designed) | sizing judgement |
| OM-17 reporting | G3c digest facts; G10 live-claim binding | digest quality |
| OM-18 stop and ask | G3a/G4a/G1 turn most triggers into exits | the rest |

---

## 8. New findings (`findings/incoming/B4.csv`)

| id | title (short) | sev | relation |
|---|---|---|---|
| NEW-1 | The planning ledger repeats F-21 today: 24 META_PLAN change-log entries stamped 5–152 min after their writing commits (17 commits, a growing ratchet), and an operator decision stamped "18:2xZ" in a 17:10:49Z commit; worker stamps are correct | S1 | extends F-21; P2 |
| NEW-2 | The planning ledger's CURRENT STATE is stale (`nextUnit: WAVE-2`, `lastCompleted: A1`, `updatedAt 16:05Z`) while 20+ rows are done and Wave 4 has been dispatched | S2 | mirrors F-23/F-25 |
| NEW-3 | Six real-tree test pins will turn the Stage-B seed and T4 red, incl. one pinning the off-enum `IN-PROGRESS`; the 2026-10-10 replay can turn CI red by closing D-P31.4-1 | S2 | extends F-19; blocks B3 C9 |
| NEW-4 | `docs/build/tools/test_check_spec_src.py` is never collected (`testpaths = ["tests"]`) | S2 | extends F-32 |
| NEW-5 | B2's `docs/build/APPEND_ONLY.toml` would violate BM-LAYOUT-01 | S3 | amends B2 §7 |
| NEW-6 | The "79 rows with —" is reproducible: 79/144 index titles are "—" (em-dash H1s) besides 142 tickets and 25 statuses; the generator parses only one header form | S3 | amends F-32's A2 amendment |
| NEW-7 | Validators pin living counts (`EXPECTED_ROWS = 715`, `BASELINE_IDS`/`FOLD_BACK_IDS`), so T1/T4 must edit the validator in the PR it validates | S3 | G6 applied to tools |
| NEW-8 | No readout contains the "agent must not sign" sentence (0 of 11), and the GATE/HUMAN templates lack it, so HUMAN-H4/H5 were created without it | S2 | extends F-29, B2 NEW-6 |
| NEW-9 | Memory checks never run on pushes to `main` (the `docs` job is PR-only), where `c2055d96` arrived as merge `e2175c93` | S3 | with H1 NEW-4 |
| NEW-10 | B3 (19 fixed CURRENT STATE keys) and B5 OM-01 (`harness:` in CURRENT STATE) conflict; the existing key-order check would fail the added key | S3 | S1/T5/B6 reconciliation |

---

## 9. Open questions (recorded, not answered)

- **Q-B4-1 (operator, with Q-14).** May the Stage-B seed carry the ~700-line guard core (§6.1), or must every code
  change wait for row 201? Recommended: the core in the seed.
- **Q-B4-2 (operator).** Adopt G4c, an operator-only signing key for gate-signature commits, verified in CI? It is
  the only mechanical answer to "an agent must not sign" while agents act with the operator's credentials.
- **Q-B4-3 (operator / H2).** When should `main` branch protection be turned on: after the #141–#190 integration
  (recommended), or now with admin bypass for that sitting?
- **Q-B4-4 (S1).** Where does the harness identity live (B4 NEW-10)?
- **Q-B4-5 (planning orchestrator).** NEW-1 and NEW-2 need an appended, dated correction entry in META_PLAN §11 and a
  CURRENT STATE refresh, by the single writer. Should V14 and G1's change-log rule be run by hand at each wave
  boundary until Stage B?

---

## 10. Reproduction (read-only)

- **Validators:**
  `bash scripts/docs/check-build-memory.sh . --json <scratch>/bm.json; python3 docs/build/tools/check_spec_src.py;
  python3 docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv;
  python3 docs/build/tools/check_backlog.py` (17:41:14Z).
- **Gate wiring:** `grep -rn 'check_backlog\|current_projection\|obligation_events\|check_spec_src' Makefile .github/`
  → 0 hits; `pyproject.toml:101-104`.
- **Planning-ledger drift (NEW-1):** `git blame --line-porcelain HEAD -- docs/build/planning/2026-09-30-next-phase/META_PLAN.md`,
  then compare every `2026-09-30THH:MMZ` token with its line's committer time. 24 tokens are more than 5 min later,
  in 17 commits. `git blame -L 708,708` → `e5725b7b` (13:10:49-04:00).
- **Append-position replay:** for each first-parent commit touching `LEDGER.md`, `git diff -U0 <c>^ <c>`. A hunk that
  adds lines inside `## GATE DECISIONS` before its last non-blank line counts → 20 commits.
- **LEDGER V1/V2/V3 replay:** for each of the 194 `git log b051732c -- docs/build/LEDGER.md` versions, measure the
  bytes before `\n## OPEN FINDINGS`, the `projectStatus` token, and whether `.agents/scratch` is in the head.
- **G1 replay counts:** `data/date_drift.csv`, class `b*`, comparing `recorded_value[:10]` with
  `commit_date_utc[:10]` → future 502 rows / 70 commits; past 87 / 22.
- **G2 replay counts:** `data/append_only_violations.csv`, classification ∈ {loss, transition-unjustified} → 25
  commits.
- **CI replay:** `gh run list --branch <b> --workflow ci.yml --json databaseId,headSha,conclusion,createdAt,updatedAt,attempt`
  for the four branches in §4 G3; `gh pr list --state open --json number,headRefName,createdAt`.
- **Readouts:** `grep -c 'must not sign' docs/build/readouts/*.md` → 0 × 11; `git show 95c8a73f^:docs/build/readouts/GATE-G3.md`.
- **ADR index:** `awk -F'|' '/^\| \[ADR/{…$3,$4,$5 == "—"…}' docs/adr/README.md` → titles 79, tickets 142,
  statuses 25.
- **Matrix quick replay:** a stdlib script over `COVERAGE_MATRIX.csv` + DEFERRALS lead tokens + BUILD_INDEX ids
  (approximate; §4 G7).
- **Timestamps:** start 17:40:03Z; findings CSV written 18:02:47Z; closing 18:02:50Z (all `date -u`).
