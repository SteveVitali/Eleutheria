# Run ledger — SEED-17 (Round 11 Stage B, T5): LEDGER seed — OPERATING MODE — Round 11, CURRENT STATE, RETURN PASS re-key, GATE DECISIONS rows, PHASE LOG entries, leg-runner prompt, guards marker

- **Harness:** claude-code/claude-opus-5-5/subagent
- **Skills:** 8aeb6dc (`git -C ~/agent-skills rev-parse --short HEAD`; build-memory release 0.5.0 + the closed-run-ledger history rule)
- **Started:** 2026-10-01T16:38:30Z (the first `date -u` read by this unit; HEAD `7bd2028c`, SEED-13e)
- **Closed:** 2026-10-01T17:11:50Z
- **Unit:** SEED-17 = plan Appendix A **T5** (`PD/NEXT_PHASE_PLAN.md`; `PD` = `docs/build/planning/2026-09-30-next-phase/`),
  `PD/data/round11_plan.csv` row SEED-17 (C8), the T0c skill contract (`PD/stageB/T0c_sync_obligations.md`) and every
  `PD/stageB/CARRY.md` item routed to SEED-17 / T5 / OPERATING MODE. Brief: `PD/stageB/AGENT_BRIEF.md` (rule 8: no nested
  sub-agents — none used).
- **Worktree / branch:** `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed`. Read-only git only in the worktree; the
  planning orchestrator commits. Concurrent unit SEED-15 committed `f68a3c96` mid-run; none of its files was touched. A
  throwaway `git clone --shared` under the session scratch directory held the history-mode dry runs (its scratch commits
  never left it).
- **Read:** plan §3.3, §8.3, §8.5, §8.6, §12, Appendix A T5; `PD/feedback/RATIFICATION_LOG.md` rounds 1–27; `PD/META_PLAN.md`
  §7.1 (GATE-M) and §11 (the 14:24:47Z…15:08:54Z entries); T0c; CARRY; H2 §7; G2 §2; ADR-149; the build-memory layout
  (BM-LEDGER-02…08, BM-ORIENT-01, BM-GATE-05…09, BM-COMPAT-06); the vendored validator and `memory_guard.py`
  (living-archived, G4a gate-record and pause rules, R1/R2); run ledgers SEED-01-04-06-07, SEED-02a/b/c, SEED-03,
  SEED-05-10-16, SEED-08-09, SEED-11a–d, SEED-12a–c, SEED-13a–e, SEED-14a/b, SEED-15 (targeted reads); the 11A contracts'
  Gate status / OM-20 status / Production mutations headers; `docs/build/OPERATIONAL_READINESS.md` §(f3); the BUILD_INDEX
  rows of the nine landed tickets.

## What was done

### 1. CURRENT STATE (T5 bullet 1)
- Exactly the 20 layout keys in the T0c order (unchanged order; values only; 1,833 B; longest line 173 B). γ's values kept
  (`projectStatus: PAUSED`, `pauseRequested: true`, `harness: devin-desktop/swe-2-high/subagent`, `dispatchTarget:
  subagent`, `mergePolicy: OPERATOR`, `autonomy: checkpoint`, `chainTip: r11/seed`, …); `nextTicket: P34.1` comment no
  longer says the row is unwritten; `updatedAt` from `date -u` at the last LEDGER write.
- **`returnPass` re-keyed (orchestrator decision γ, CARRY):** `P21.5, P31.4, P32.18, P32.19, P32.20, P32.21, P32.22,
  P32.23a, P32.25` — the nine landed Round-10 tickets that owe a live leg. Derivation: `### RETURN PASS — current`'s nine
  obligations × OPERATIONAL_READINESS §(f3) packets × plan §8.6 ("row 183 → P35.61 · 188 → P35.62 · 191 → P35.63 · 179–182 →
  P37.16"): D-P21.5-1 → P21.5 (row 59, PR #61); D-P31.4-1 → P31.4 (row 145, #140); D-P32.18…21-1 → P32.18…P32.21 (rows
  179–182, #175–#178); D-R10-LIVE-1 → P32.22 (row 183, #179; packet `p32.22-bounded-recovery`); D-P32.23a-1 → P32.23a (row
  188, #180); D-R10-PUBLISH-1 → P32.25 (row 191, #182). Every id is in BUILD_INDEX, so the validators' lowest-unlanded rule
  cannot misfire on a key.

### 2. `### RETURN PASS — current` (exempt region, `history.policy`)
- Rewritten so each row is keyed by the landed ticket and its re-run line names the Round-11 row (P37.55 row 482, P34.39a
  row 247 (+ P34.39b 248), P37.16a/b rows 438/439 for the four dossier rows, P35.61 row 338, P35.62 row 339, P35.63 row
  341) with the landed row and PR; obligations, gates, operator actions, packets and the HG-05 `—` row unchanged; the
  membership comment and the labelled agent interpretation updated; a dated superseding note appended (the SEED-16 keying
  at `e2ab1897`, why it would misfire, the γ decision, P34.29 reproduces it).

### 3. OPERATING MODE — Round 11 (T5 bullet 2)
- **Head:** SEED-10's placeholder (LEDGER lines 6–8 at `7bd2028c`, 689 B) archived byte-for-byte to
  `docs/build/reports/memory-repair/LEDGER_head_placeholder_SEED-10.txt` (sha256
  `c3324b73a0ce70f55d396fffbe043ca4219a9d28be11bc880e5f11773f2ffe32`, equal to the source slice) with a pointer comment on
  line 3, and replaced by a 16-bullet one-line form: state, dispatch (round 25 + isolation check + round-27 fallback
  order), orient (O1–O6, ≤ 48 KiB, re-measure Loads + ≈ 17.5k skill text), clock (+ D-P31.4-1 guard), CI
  (`ci-boundary.sh` + `ci_boundary.py`, merge-base boundary record), records (`--staged`/`--range`, ADR-146, C-10, SEED-03
  closeout rules), harness/authorship (OM-01, A-21), pauses (A-15, A-2b), digest (`digest.sh` with spend vs $300 and agent
  usage), pre-authorisation (OM-20 rows, P34.40 nginx only, P34.6 drill clone only, B-9 renewal), gates (S5-2, no GATE while
  a leg is due, GATE-ANNOUNCE re-anchoring, OP-26 flips), live legs (OM-19, AR-1…AR-9, backstop prompt), live API (A-20),
  contact (P16 alias first / C-8, U-011, B-31/B-42), numbers (≥ ADR-191, copy batches, `later_register.py`), skills (B6 §5.3
  conditional). Head = **8,183 B** (under the 8 KiB warning level; budget 12 KiB).
- **Full text:** `docs/build/reports/OPERATING_MODE_R11.md` (33 KB; the validator does not allow new files at the
  `docs/build/` root, so it sits under `reports/`): §1 executor/dispatch/isolation/fallback/chain lock; §2 orient + sizing;
  §3 OM-01…OM-20 **copied byte-for-byte from plan §3.3 lines 328–372** (S4c wording, incl. OM-01's trailer grammar and the
  class-based never-list) + the 11A list in force; §4 the T0c skill rules (clock, CI, records, harness, digest, stop and
  ask); §5 pauses, gate markers, packets, GATE-ANNOUNCE re-anchoring, OP-26, the Class R standing go, gate-record rules;
  §6 H2 §7's PR-1/2 + CI-1…CI-9 adapted to the files that exist (`ci_required.txt`; P34.2 creates the flake allow-list);
  §7 G2 §2 AR-1…AR-9 + D-P31.4-1 + A-20; §8 contact, honesty, authorship, the COV-14 boundary record; §9 OM-19 legs + OP-24;
  §10 SEED-02a/SEED-03 record conventions, ADR numbering, copy batches, `later_register.py`, projection regeneration;
  §11 skill loading (no B6 §5.3 override in force). Operator words verbatim with round times; agent readings labelled
  (the chain-lock mechanism; the 30-day reading of B-9).

### 4. GATE DECISIONS (T5 bullet 4 + the task's list) — 32 rows appended after SEED-07's row in the `### Round 11` 7-column table
- GATE-M (2026-09-30T16:16Z, META_PLAN §7.1, `1703734a`); GATE-P go (05:03:05Z; the 03:34:09Z instruction verbatim;
  `de0b3591`); S5-1 decision (04:28:49Z); **13 `pre-authorization` rows** for the 11A OM-20 list (P34.3, P34.4, P34.5,
  P34.6 drill clone, P34.21a, P34.24b, P34.40 **L1 nginx roll only — the `/v1/*` step needs its own go**, P34.42a, P34.42b,
  P34.43, P34.49, P34.44b, **P34.45 ER re-run**), each with its contract's mutation, restore point, `expires: GATE-G4` and
  `voided-by:` (red probe, failed restore point, contradicting production read); the **B-9 Class R standing go** as a
  `pre-authorization` row with the adopted sentence verbatim (sha256 `e4e24975…` re-computed = S6's), `expires: GATE-G4 or
  2026-10-31, whichever is first`, `voided-by:` ratchet regression / Part VIII screen change / new source; C-2
  (confirmation), C-3 (correction; sentence sha256 `1461ae21…` = S6's), C-13 (decision); round 24 S6-F1/F2 (waivers WV-08/09)
  + S6-F3 (decision); round 25 dispatch (decision); round 26 S6R-01/S6R-03 (waivers WV-10/11), S6R-08 (decision) and the
  **S6R-02 record clarification** (correction); round 27 SB-1 (waiver WV-12), SB-2, SB-3 (decisions); the A-2b resume
  answer (14:25:28Z). Every date is the receipt time from the log (never invented); every row carries `retro: recorded by
  SEED-17 at T5 from <log @ commit>` because it is a late recording. Sentences of rounds 24–27 hashed here (labelled
  "computed by SEED-17").

### 5. PHASE LOG — Round 11 (T5 bullet "PHASE LOG"; one line each, ≤ 2 KiB, lead date `date -u +%F`)
- 13 entries appended after ROUND11's: `GATE-P gate` (the planning ratification pause), `SEED-01 round` (preflight +
  registers), `SEED-11 round`, `SEED-12 round`, `SEED-02 round`, `SEED-03 round`, `SEED-08 correction` and `SEED-09
  correction` (the run-ledger drafts verbatim, dated), `SEED-13 round`, `STAGEB pause` (the usage-limit event, the resume
  answer, the recovery audit and the system restart), `SEED-14 round`, `SEED-15 round` (after `f68a3c96` landed),
  `SEED-17 round`. Each cites its commits from `git log --oneline b051732c..HEAD`. No entry uses the word "done" (seed units
  have no BUILD_INDEX row). Largest entry 1,395 B. No PHASE LOG entry that contains the word "pause" names GATE-M (see
  issue 2).

### 6. Leg-runner backstop prompt (T5 bullet 3)
- `docs/build/planning/2026-09-30-next-phase/stageB/LEG_RUNNER_PROMPT.md`: the operator's OP-24 scheduling notes (Devin
  Desktop if it supports scheduled sessions, else Devin CLI headless with `swe-2-high`; harness string recorded; every 6 h
  + window edges) and the verbatim prompt: orient reads, chain lock (`mkdir docs/build/LEDGER.md.drive-lock`, the
  drive-build single-driver lock — agent design, labelled), what counts as a leg (a landed ticket's own live re-run — an
  undispatched chain row is not a leg), due + go-held tests (GATE DECISIONS rows, expiry, void conditions, AR-3 windows,
  AR-4 clock guard), per-leg steps (CI read, AR-2 restore point, `r11/<id>-live-<n>` branch, one PR, head-bound CI,
  run-ledger/probe-run/transition records, `--staged` check, harness trailer, chainTip + PHASE LOG), usage-limit stop, the
  alert path (P34.4's channel once landed; until then `digest.sh --trigger block --write` + final message — labelled) and
  the never-list.

### 7. Guards marker (T5 / T0c) — added last
- `<!-- build-memory-guards: 1 -->` alone on the line after `<!-- build-memory: v2 -->` in `docs/build/README.md`. The
  README's "rows 1-200 as of P33.8, 2026-09-28" line is still true (no chain row landed in the seed; P33.8 committed
  2026-09-28T22:45:44Z) — unchanged.

### 8. Stale tokens and paths (T5 bullet 5)
- Head scan for `.agents/scratch`, `gitignored`, `Do not resume until` (+ no repo `stale_tokens.txt`): **0**. Every repo path
  in the head exists (`docs/build/LEDGER.md`, `docs/build/reports/OPERATING_MODE_R11.md`,
  `docs/build/reports/current/CURRENT.md`, `docs/build/tools/ci_boundary.py`, `db/sqitch.plan`, both archive files,
  `date_corrections.csv`, the leg-runner prompt, the manifest, the spec); the only non-existent string is the template
  `docs/build/reports/copy-batches/batch-<NN>.md` (created by the first ticket that writes a copy batch; the validator skips
  `<…>` templates).

## Files written / changed
- `docs/build/LEDGER.md` — head (pointer line, OPERATING MODE replacing the archived placeholder, CURRENT STATE
  `nextTicket` comment / `returnPass` / `updatedAt`), `### RETURN PASS — current` (exempt; rewritten + note), GATE DECISIONS
  `### Round 11` (+32 rows at the table's end), PHASE LOG — Round 11 (+13 entries at EOF). No other line changed.
- `docs/build/reports/memory-repair/LEDGER_head_placeholder_SEED-10.txt` (new; the archive).
- `docs/build/reports/OPERATING_MODE_R11.md` (new).
- `docs/build/planning/2026-09-30-next-phase/stageB/LEG_RUNNER_PROMPT.md` (new).
- `docs/build/README.md` (+1 line: the guards marker).
- `docs/build/runs/SEED-17.md` (this ledger).
- Scratch only (not committed): the generator scripts and templates under the session scratch directory; the clone.

## Checks
| check | where | result |
|---|---|---|
| `bash scripts/docs/check-build-memory.sh .` | live tree, before this unit (no marker) | exit 0 — no violations, 44 warnings |
| same, after, **guards marker on** | live tree | **exit 0 — no violations, 44 warnings** (the same 44 legacy warnings; only line numbers moved). An intermediate run failed once: `layout: docs/build/OPERATING_MODE_R11.md is not an allowed build-memory root entry` → the file moved under `reports/` |
| `python3 docs/build/tools/memory_guard.py all --worktree` | live tree, marker on | **exit 0 — 0 violations**, 2 warnings: G4a-pause for the GATE-M row (expected; issue 2) and SEED-17.md's `Closed:` placeholder (cleared at close — re-run below) |
| the same two runs at close (after `Closed:` and `updatedAt` were stamped) | live tree, marker on | validator **exit 0, no violations, 44 warnings**; memory_guard **exit 0, 0 violations, 1 warning** (GATE-M G4a-pause, issue 2) |
| history mode on a scratch commit of exactly this unit's six files over `f68a3c96` | scratch clone | `memory_guard.py all --range HEAD~1..HEAD`: 0 violations except an R1 on a deliberately fake future `Closed:` stamp I put in the scratch copy (proves R1 bites; the real stamp is `date -u` before the commit); skill `check-history.sh --range HEAD~1..HEAD` (repo hook moved aside): same single artefact, 0 warnings; living-archived, pointer, append position, record dates all pass |
| `uv run pytest tests/unit -q -k "ledger or build_memory or memory or projection"` | live tree | **73 passed, 1 failed**: `test_build_memory_audit.py::test_real_tree_zero_errors_and_every_status_conflict_documented` — the audit's 26 pre-existing errors (20 `adr/dangling-reference` to ticket-authored ADR-156/160/161/174/177, 6 `tickets/forward-dependency` on `203_P35.38a`), identical before this unit; **0 `ledger/*` findings** (issue 4) |
| `python3 docs/build/tools/audit_current_state.py` | live tree | exit 1 — 26 errors, 9 conflicts, the same set as before this unit; no `ledger/*` finding (key order with `harness`, nextTicket, returnPass all clean) |
| `bash scripts/docs/check-repo-docs-freshness.sh .` / `check-agent-docs-freshness.sh .` | live tree | 430 docs, 0 broken refs, 0 stale / 8 docs, 0 issues |
| `python3 docs/build/tools/current_projection.py verify` | live tree | STALE (expected: the LEDGER and new inputs changed; T6 regenerates `reports/current/`) |
| writer self-checks | scripts | archive = source slice (sha256 equal); head 8,183 B ≤ 12 KiB (< 8 KiB warn); CURRENT STATE 1,833 B ≤ 3 KiB, every key line ≤ 256 B; no other line begins with a key name; the last `## ` heading is PHASE LOG — Round 11; 33 rows × 7 cells, no `\|` in a cell; each new entry ≤ 2 KiB; adopted-sentence hashes re-computed (B-9, C-3 equal S6's); no operator e-mail address in any added text |

No test was changed. No ADR, DEFERRALS row, contract or SEED-15 file was edited.

## Draft — the C10 `harness-switch` PHASE LOG entry (append at GATE-B, not now)

C10 appends it at the end of the file **before the first Devin dispatch**, with the lead date and the GATE-B time from
`date -u` (placeholders in `<…>`):

```
- <date -u +%F> — C10 harness-switch — claude-code/claude-opus-5-5/subagent → devin-desktop/swe-2-high/subagent · reason: A-15 (Devin Desktop with swe-2-high, 256k, executes chain rows 201–510) and round 25 (one orchestrator session hands each ticket to a fresh sub-agent; dispatchTarget: subagent) · operator: "We will drive most of the execution with Devin Desktop using their new SWE-2 High model (256k context window)" (2026-10-01T04:16:29Z, AskUserQuestion custom answer in the Claude Code planning session, A-15 round 6); "How about Devin for everything and Claude Code can do a deep review after the entire thing, similar to what we did here where Claude Code with high-powered Opus 5.5 xhigh discovered issues from Devin over a many-dozen-ticket build" (2026-10-01T04:21:56Z, A-15 round 7); "Orchestrator + sub-agents (Recommended)" (2026-10-01T06:14:06Z, AskUserQuestion, round 25) · recorded at GATE-B (GATE DECISIONS ### Round 11 row <date -u>) · P34.1 re-runs orient, the validators and the CI read before dispatch · chainTip → <seed PR head branch> · next → P34.1 · harness: <the harness writing this entry>
```

With it, C10 sets `projectStatus: IN_PROGRESS`, `pauseRequested: false`, `updatedAt` (and `buildWorktree`/`chainTip` if T6
changed them). **Also at C10:** record a PHASE LOG `gate` (or `pause`) entry naming **GATE-B** when its packet is presented,
dated no later than the GATE-B decision row; otherwise `memory_guard` warns G4a-pause on the GATE-B row (GATE-B is not a
`GATE-G<n>` marker, so it is a warning, not a failure).

## Issues for other units / the orchestrator
1. **ADR-149 should cite the B-9 pre-authorization row** (CARRY: "record it at T5 … and cite it from ADR-149 · SEED-17 (T5) +
   orchestrator"). The row exists (GATE DECISIONS `### Round 11`, 2026-10-01T04:35:53Z); the ADR edit — an appended
   clarification/status line on a seed ADR — is the orchestrator's (not this unit's file).
2. **GATE-M warning (expected, not fixable honestly):** the GATE-M decision (2026-09-30T16:16Z) answered a stop recorded in
   the planning ledger (META_PLAN §7.1), not in this PHASE LOG; a PHASE LOG pause entry naming GATE-M would be dated
   2026-10-01 and turn the warning into a G4a-pause **violation** (decision earlier than every pause). The row's consequence
   says so. GATE-P's rows are satisfied by the `GATE-P gate` entry (same date). Keep GATE-M out of any future PHASE LOG
   entry that contains the word "pause".
3. **Agent readings for the GATE-B packet:** (a) the chain-lock mechanism (`docs/build/LEDGER.md.drive-lock`, drive-build's
   lock) — the plan names a lock but not its mechanism; (b) B-9's 30 days counted from adoption (2026-10-01T04:35:53Z →
   expires GATE-G4 or 2026-10-31, whichever first); (c) the leg-runner's alert path before P34.4 lands (digest + final
   message). Also carry the existing packet questions (P34.40 `/v1/*` own go; P34.6 export/lifecycle coverage).
4. **Audit errors outside this unit** (`test_real_tree_zero_errors_and_every_status_conflict_documented` fails): 6
   `tickets/forward-dependency` errors — `203_P35.38a__crawler-ua-contact-and-explanation-page.md` (chain row 202) depends on
   P35.11, P36.12, P36.74, P36.76, P37.2, P37.54 (later rows) → T3/orchestrator (contract wording or a Plan-extensions
   note); 20 `adr/dangling-reference` errors to ticket-authored ADR-156/160/161/174/177 that do not exist yet (they resolve
   as those tickets land, or the test needs a documented expected list) → orchestrator/T6.
5. **T6:** regenerate `docs/build/reports/current/` (projection STALE); confirm `buildWorktree`; verify in Devin Desktop:
   skill loading from `~/.claude/skills` (else append the B6 §5.3 overrides as an `## Amendment` of
   `docs/build/reports/OPERATING_MODE_R11.md` and say so in the packet), the co-author trailer it writes, whether a headless
   Devin command exists for `drive-build.sh --agent-cmd`, and whether it runs scheduled sessions for OP-24 (record the
   leg-runner harness string in the HANDOFF).
6. **Optional:** a pointer line for the new archive file in `docs/build/reports/memory-repair/README.md` (SEED-15 appended
   to that README in `f68a3c96`; the LEDGER pointer comment is what the guard requires, so this is cosmetic).
7. `docs/build/planning/2026-09-30-next-phase/tools/test_extract_universe.py` shows as modified in the worktree; it is not
   this unit's file (left untouched).
8. CARRY item "SEED-13d · P34.49's capture-side OSM `user`/`uid` fix → DEFERRALS row" is already met by SEED-14a's
   `D-R11-OSMUID-1`; nothing owed by T5.
