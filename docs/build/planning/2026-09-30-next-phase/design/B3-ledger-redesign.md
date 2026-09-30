# B3 — Control-ledger and index redesign

Row **B3** of `META_PLAN.md` (Stage P, stream B, Wave 3). Owner D. **This row is design only.** It edits no control
file (P10) and commits nothing. It writes two files: this note and `findings/incoming/B3.csv`. Scratch scripts and
raw outputs are in `/private/tmp/…/scratchpad/B3/` (session scratch, not committed; §9 lists the commands).

- **Authored:** 2026-09-30T17:21:20Z → 17:39:23Z (`date -u`) by Claude Code (Opus 5.5), in the planning worktree
  `/Users/stevenvitali/Eleutheria-next-phase` (`claude/next-phase-planning` @ `888930ff`).
- **Inputs are baseline-identical.** `git diff --quiet b051732c HEAD` is empty for `LEDGER.md`, `BUILD_INDEX.md`,
  `docs/tickets/`, `reports/current/` and `OPERATIONAL_READINESS.md`. The LEDGER sha256 is `d459173f…1a30` and the
  BUILD_INDEX sha256 is `7830dbc3…`, both as in A1.
- **P13 honoured.** The LEDGER (679,109 B) was never read whole. Scripts printed section boundaries, byte counts, key
  names, date tokens, blame commits and excerpts of at most 170 characters.
- **Evidence classes (P1):** `code` (file bytes, git history, blame); `live-read` (`gh pr list`, and the host-local
  closeout journal under `.git/sig-closeout/`); `recorded-execution` (validator replays). Token counts are
  **inference**, estimated at about 4 bytes per token.
- **Builds on:** B1 (date register; correction ADR §8; sqitch: never edit a deployed line), B2 (GATE DECISIONS
  restoration §4.1; `check-append-only` §7; events.jsonl §5.1), A3 NEW-2/NEW-3 (RETURN PASS disagreements), F-21…F-29,
  build-memory `layout.md` (BM-LAYOUT-01, BM-LEDGER-01…07, BM-INDEX-01), `orchestrate-build` §0 Orient, ADR-126/127,
  `CLOSEOUT_WRITER_PROTOCOL.md`, and `OPERATIONAL_READINESS.md` §(f3).

---

## 1. Summary

**Measured (LEDGER @ `b051732c`).**
- **Size.** 679,109 B in 463 lines. The PHASE LOG entries make up 490,036 B (72 %).
- **CURRENT STATE.** 122,978 B. Its 19 key lines hold 7,922 B of values and 114,735 B (93.5 %) of `| PRIOR` chains: 268
  PRIOR segments and 41 October dates.
- **Orient cost.** A fresh orient that reads through CURRENT STATE loads 126,875 B (≈32k tokens). The same session is
  handed a stale prompt: "gitignored, never commit", a `.agents/scratch` ledger path, "drives all 17 tickets", and
  "Do not resume until Codex reports…". It resolves `nextTicket: HUMAN-H4`, a row the operator deferred.
- **PHASE LOG.** 170 dated entries, split across **five regions**:
  - 54 entries (189 KB) sit under the `## CAPSTONE — step 2/3 closure` heading.
  - Round 10's 35 entries are split across three of the regions.
  - There are 12 date inversions.
  - The vendored validator's PHASE-LOG→BUILD_INDEX check parses **0 of the 139 "done" bullets**, because every entry
    bolds its ticket id.
- **BUILD_INDEX.**
  - Seq 170 is used twice (P32.10 and P32.10a).
  - The executed markers 190 (GATE-G3) and 195 (GATE-ACCEPT) have no rows.
  - **7** rows read "PR pending": 76–81 are PRs #76–#81 and 94 is PR #89.
  - **F-24 reconciled.** Depending on method, 7, 13, 16 or 36 tickets lack a PHASE LOG entry. The "17" does not
    reproduce under any method. The design uses 13 with no entry plus 3 with no "done" entry, **16 in all** (§2.6).

**Target.**
1. **Orient budget.** The LEDGER head, meaning everything before `## OPEN FINDINGS`, is capped at ≤ 12 KiB (target
   8 KiB). CURRENT STATE is ≤ 3 KiB, with values only: one line per key, at most 256 B each, and no PRIOR chains.
   A documented orient recipe reads ≤ 48 KiB in total (≈ 12k tokens).
2. **Head archive.** Lines 1–54 are archived **byte-for-byte** to `docs/build/reports/memory-repair/`, with a
   sha256-linked pointer.
3. **Superseded prompt.** A fresh Round-11 OPERATING MODE supersedes the old prompt. The old text is archived and a
   one-line tombstone stays in place.
4. **Appended sections.** Everything else is appended:
   - B2's 53-row GATE DECISIONS restoration;
   - B1 DATE CORRECTION entries;
   - a `RETURN PASS — current` table regenerated from §(f3) plus the S1 dispositions, with a mechanical sync rule;
   - a `PHASE LOG INDEX — Rounds 1–10` backed by a hash-anchored CSV;
   - a new last section, `PHASE LOG — Round 11`, as the only append target;
   - BUILD_INDEX index repairs.
5. **`nextTicket`.** It becomes the first dispatchable Round-11 row, and rows 184–187 carry a machine-readable
   deferred or superseded mark (option N1, §3.12).

**Shadow mode (§4). Split D-R10-MEMORY-1. Do not cut over wholesale, and do not retire wholesale.**
- **Obligation events: repair, then enforce in-repo.** The file becomes append-only, correction and transition events
  are appended, and CI checks that cell moves have events. No skill edit is needed.
- **Projection: keep it**, as a CI-verified, advisory orient view.
- **Closeout journal (`closeout-op/1`): stays shadow.** Its trigger is parallel dispatch or a multi-worktree build. The
  evidence: `events.jsonl` was rewritten 3× with 0 transitions; the journal was used for 2 of 35 Round-10 closeouts;
  `activation-check` passes only on rewritten history.

**Split (§5).** The **Stage-B seed** (T2/T5) is 10 ordered commits: C0 preflight, C1–C9 changes, and C10, which lands
after GATE-B. Every commit is append-only except C6, the archived living head. Each ends with a validator run and an
acceptance check. The code and test repairs are **early Round-11 tickets M1–M6**: the append-only guard, the
ledger-contract validator, the events repair, the remaining restorations, the RETURN PASS generator, and the
D-R10-MEMORY-1 disposition. §6 gives the validator and CI requirements for B4. §7 lists 8 new findings.

---

## 2. Measurements (current state)

### 2.1 LEDGER sections (`b051732c`, `python3` section scan)

| lines | bytes | heading | mode (layout / B2) | in orient read? |
|---|---:|---|---|---|
| 1–28 | 3,897 | H1 + provenance + `OPERATING MODE` (Round 1) + Round-10 amendment (L27, 1,263 B) | living (resume prompt) | **yes** |
| 29–54 | 122,978 | `## CURRENT STATE` | living | **yes** |
| 55–60 | 4,743 | `## OPEN FINDINGS` | append-only | no |
| 61–101 | 6,244 | `## LEGACY PLAN` | historical | no |
| 102–112 | 1,905 | `## GATE PROTOCOL` (Round-1 rules) | historical | no |
| 113–191 | 26,750 | `## GATE DECISIONS` | append-only | no |
| 192–222 | 4,836 | invariants · out of scope · SETUP / CAPSTONE checklists | historical | no |
| 223–242 | 11,385 | `## RETURN PASS` | row-annotate | no |
| 243–273 | 40,426 | `## PHASE LOG (append-only, newest last)` | append-only | no |
| 274–283 | 4,042 | OPEN FINDINGS additions · CAPSTONE step 1 | append-only / historical | no |
| 284–358 | 191,404 | `## CAPSTONE — step 2/3 closure …` — **contains 54 PHASE LOG entries (189,471 B)** | historical heading, de-facto PHASE LOG | no |
| 359–364 | 4,310 | `## PHASE LOG — CAPSTONE done` · `## PHASE LOG — Round 2` | append-only | no |
| 365–463 | 256,190 | `## PHASE LOG — Round 3 (go-live) + Round 4 (productionize)` — also holds P25–P26 and most of Round 10 | append-only | no |

BM-LEDGER-01 requires six sections in a fixed order. They are all present, in that relative order, but they are
interleaved with 9 historical sections. The validator checks only the CURRENT STATE key order (it passes today).

### 2.2 CURRENT STATE keys (L34–52)

| key | line bytes | value head (B) | `\| PRIOR` segments | October dates | never-fail reader returns (`drive-build.sh` `status_val`) |
|---|---:|---:|---:|---:|---|
| projectStatus | 25,922 | 727 | 39 | 17 | `IN-PROGRESS` — **off-enum** (layout `IN_PROGRESS`). drive-build tests only DONE/BLOCKED/PAUSED, so it loops on, and the validator never checks the enum |
| nextTicket | 12,043 | 370 | 60 | 5 | `HUMAN-H4` (row 184, deferred by the operator; the validator only checks that the row exists) |
| lastCompleted | 32,382 | 751 | 51 | 0 | `P33.8` |
| blockedOn | 169 | 169 | 0 | 0 | `(nothing)` (194/194 committed versions, F-36) |
| pauseRequested | 566 | 95 | 5 | 0 | `false` |
| returnPass | 3,871 | 3,871 | 0 | 0 | **a 2,054-char prose fragment**, cut at the first `#`; not the ids that BM-LEDGER-05 requires |
| canonicalSpec | 251 | 80 | 1 | 0 | ok |
| dispatchTarget | 139 | 139 | 0 | 0 | `subagent`, with the comment "Devin CLI isolated-subagent primitive" (harness-specific, stale) |
| buildBranchBase / pinnedBaseSha | 43 / 24 | — | 0 | 0 | `devin/p18-2-france-belgium` / `1baf05f` (Round-1 values) |
| chainTip | 8,973 | 207 | 53 | 0 | `devin/p33-8-agent-docs-refresh` |
| round | 1,361 | 43 | 4 | 0 | `10` |
| updatedAt | 36,129 | 619 | 55 | 19 | `2026-09-28 — P33.8 (row 200, the final manifest row) DONE: PR` (truncated at `#190`) |
| other 6 keys | 784 | 784 | 0 | 0 | ok |
| **total** | **122,657** | **7,922** | **268** | **41** | |

### 2.3 Stale text in the orient region (lines 1–28)

| line | text | why it is stale |
|---|---|---|
| 1 | `(orchestrate-build machine state; gitignored, never commit)` | Committed since P22.3 / ADR-073 (build-memory v2) |
| 5 | `Ticket contracts: docs/tickets/P19.1…P21.9` | The chain has 200 rows |
| 8 | `One orchestrator session drives all 17 tickets` | Same |
| 13 | `ledger=.agents/scratch/planning/sig-postbuild-build-ledger.md` | Path retired (AGENTS.md; ADR-073); the file does not exist |
| 14–18 | `pinned_base_sha=1baf05f`, "drive it to CAPSTONE", "ticket file named in PHASE PLAN" | Round-1 values; the PHASE PLAN became `## LEGACY PLAN` |
| 3–4 | `DECISION_MEMO.md` | Now `docs/build/reports/DECISION_MEMO.md` |
| 27 | "**Do not resume until Codex reports the checkout/PR handoff verified.**" | The condition was met in practice: Round 10 resumed 2026-09-27 (PHASE LOG L417/L419, PR #155 closeout), and nothing voids the text. A fresh session that obeys it stops |

Three of the seven paths named in lines 1–28 do not exist at HEAD: `.agents/scratch/planning/…`,
`docs/build/DECISION_MEMO.md` and `docs/tickets/P19.1`.

### 2.4 PHASE LOG

The scan matched `^- YYYY-MM-DD —` and ran `git blame --line-porcelain b051732c`.

- **170 dated entries, 490,036 B.** Sizes: median 2,703 B, p90 5,076 B, max 6,523 B. 111 entries exceed 2 KiB. BM-LEDGER-06
  asks for a "one-line summary".
- **Five regions.** New entries were appended to whichever section each writer found:

| region (heading) | entries | what is in it |
|---|---:|---|
| `## PHASE LOG (append-only, newest last)` L244–271 | 28 | Round 1 (SETUP, P19.1–P22.2), **plus P32.1 (L270, `ebd34ce1`) and P32.11 (L271, `30d401dc`)** |
| `## CAPSTONE — step 2/3 closure …` L289–357 | **54** | Round 5 (P27), 6 (P28), 7 (P29), 8 (P30), 9 (P31.x), **plus P32.10, the P32.10a insert and P32.10a (L353–357)** |
| `## PHASE LOG — CAPSTONE done` L360 | 1 | Round-1 capstone |
| `## PHASE LOG — Round 2` L363 | 1 | P22.3 |
| `## PHASE LOG — Round 3 … + Round 4` L366–462 | 86 | Rounds 3/4, P25–P26, Round-9 Wave-B seed, **Round 10 P32.2–P33.8** |

- **12 consecutive date inversions** in file order. F-24 counted 11. Examples: L342 P31.10 `10-02` → L343 P31.11 `09-25`;
  L386 P24.6 `09-14` → L387 P24.7 `09-13`; L454 P33.1 `10-21` → L455 P33.2 `09-28`.
- **Wrong dates against blame.**
  - 25 entries carry a recorded date later than their last-writing commit. They cover P31.10–P33.1, plus the HUMAN-H4
    pause, the S3 deferral and the GATE-G3 pause.
  - 15 entries carry a date more than 1 day before it: the Round-3 session, 09-10 recorded for 09-13 work.
  - This matches B1 correction rows #2 and #7–#35.
- **Validator blind spot (NEW-1).** `scripts/docs/check-build-memory.sh:372-376` extracts the id with
  `^-\s*[0-9-]+\s*—\s*(ID_RE)`, but entries write `— **P32.1 …**`. A replay found 139 bullets that contain `done` and
  0 ids checked. A bold-aware parser would check 138 and flag 4 historical pseudo-ids (`SETUP`, `OPERATOR`, `ROUND`,
  and `P24.9`, which has no runs/pr file). M2 must allow-list these.

### 2.5 GATE DECISIONS, RETURN PASS

- **GATE DECISIONS** (26,750 B) holds 23 dated bullets and no table. BM-LEDGER-04 requires a table.
  - It runs in **two orders**. From `307161ee` (2026-09-23T02:14Z) on, new decisions were **inserted at the top**:
    L115 was written by `4127dbf3` 09-28T18:47Z, above L116 `95c8a73f` 09-28T03:49Z, above L117 `a33cd6ec`, and so on.
  - The older bullets (L156/166 GL-GATE-07/08, L174/181 P27.2) were appended.
  - There are 6 inversions and 2 future-dated bullets (L116/L117 `2026-10-19`).
  - Inserting at the top removes no line, so a removal-only guard would not catch it (NEW-3).
  - The 53 rows deleted by `c2055d96` are absent (F-22 / B2 §4).
- **RETURN PASS** (11,385 B) holds 16 table rows. The `returnPass:` key holds 18 ids. The two disagree with each other
  and with DEFERRALS (A3 NEW-2):
  - P24.3, P24.6 and P24.7 are only in the key; P31.4 is only in the table;
  - the P21.1, P21.4, P23.6 and P31.16 rows list owed items that are DONE or WONTFIX;
  - P23.1 (HG-05) has no deferral row (A3 NEW-3).
  - The accurate list is `OPERATIONAL_READINESS.md` §(f3), 36 owed rows (F-25).

### 2.6 BUILD_INDEX (295,436 B, 268 lines, 193 numbered rows, seq 1–200)

| defect | detail | evidence |
|---|---|---|
| duplicate seq | `170` at L242 (P32.10, #165) and L243 (P32.10a, #166). The manifest says `170a` | row scan |
| missing rows for executed markers | **190 GATE-G3** (signed `95c8a73f`, 2026-09-28T03:49Z) and **195 GATE-ACCEPT** (ACCEPT-R10, signed `4127dbf3`, 2026-09-28T18:47Z). Precedent for a marker row: row 87 `P24.9 \| gate (marker, retro-indexed)` | readouts/GATE-G3.md, ACCEPT-R10.md |
| correctly absent | 158/159 (unused, manifest :343) · 184–187 (deferred, manifest :5) | — |
| "PR pending" (7, not 6) | rows 76–81 = **PRs #76–#81**, created 2026-09-13T21:11Z…09-14T02:31Z and merged into `main` 2026-09-24T22:16–22:17Z (the PR base is `main`, not the stacked base in the row); row **94 P25.7 = PR #89**, created 2026-09-16T05:14Z | `gh pr list --head <branch>` (NEW-7) |
| off-vocabulary kind | row 157 P31.16, kind cell `ticket — **done (HG-11 granted …)**`, written at close by `4cc7e13c`, so not a later rewrite | row scan |
| date drift | B1's list: rows 67–80, 88, 90, 151, 155, 156, 162–170, 175–180, 188, 189, 191, 192 | B1 §5.1 |

**F-24 count reconciled (132 `ticket`-kind rows, seq ≥ 47):**

| method | missing | tickets |
|---|---:|---|
| id appears in **no** dated entry anywhere | 7 | P25.8, P25.9, P26.1, P26.5, P26.7, P26.8, P26.10 |
| no entry **led by** the id; also no entry whose first bold span names it (two parsers agree; = A2's 13) | **13** | P25.2, P25.4, P25.6, P25.8, P25.9, P25.10, P26.1, P26.5, P26.7, P26.8, P26.9, P26.10, P26.11 |
| no **"done"** entry led by the id | **16** | the 13, plus P25.1, P25.3, P25.5, whose only entries read "partial" / "landed" (L393, L396, L400; branch `devin/deploy-gcp-live`) |
| no mention inside a **PHASE-LOG-headed** section | 36 | an artefact of the 54 entries under the CAPSTONE heading |

Appendix A's "17" does not reproduce under any of these methods. **The design uses 16**: 13 index-only rows ("no PHASE LOG
entry; the BUILD_INDEX row is the record") and 3 marked "no done entry".

### 2.7 The memory tools in practice (for §4)

- **`events.jsonl`:** 97 `migration` events and 0 transitions. It was rewritten wholesale 3× (B2 §5.1, F-26). All 97
  carry `recorded_at 2026-10-21` (B1 #35).
- **Closeout journal (`<git-common-dir>/sig-closeout/operations/`, live-read):** **2 operations**, P32.8 and P32.9, both
  `acknowledged` at 2026-09-27T09:13:53Z and 09:53:05Z.
  - The other 33 of the 35 Round-10 ticket closeouts did not use it.
  - Its clock stamps contradict the BUILD_INDEX "landed" dates for those two rows (2026-10-15 and 10-16). The only
    clock-stamped memory surface was correct (NEW-4).
- **Projection (`reports/current/`):** regenerated in 15 commits. `current.json` is 436,782 B and `manifest.json`
  89,104 B.
  - `verify` reports "fresh" while carrying future dates and stale landings (F-27, F-28).
  - Its header still reads "single-writer protocol is `D-R10-MEMORY-1` → P32.8", although P32.8 has landed.
- **`closeout_protocol.authoritative_root`** (`closeout_protocol.py:239-249`) defaults to the **main worktree** of the
  common dir. That contradicts BM-ROOT-02 whenever the build runs in a sibling worktree (NEW-5).

---

## 3. Target design

### 3.1 Principles

- The **budget applies to the orient region, not to the file.** Append-only history stays in `LEDGER.md` and is
  navigated by index and anchors. The file will still be ≈ 600 KB after the seed (§3.14).
- **Living regions** are the H1, provenance, OPERATING MODE and CURRENT STATE. They may be replaced only when the
  removed bytes are archived **verbatim**, hash-linked, in the same commit (new guard mode `living-archived`, §6 V7).
- **Every other region** changes only by appending (B2 §6). Corrections name what they correct.
- **Values, not narrative, in CURRENT STATE.** The history of values is already carried by each PHASE LOG entry's
  `chainTip → … · next → …` fields (BM-LEDGER-06) and by git.
- **One append target.** Every new PHASE LOG entry goes at EOF, in `## PHASE LOG — Round 11`.

### 3.2 Target shape

```
docs/build/LEDGER.md                                   (≈ 600 KB; orient region ≤ 12 KiB)
  # SIG — build ledger (orchestrate-build machine state; committed build memory v2, ADR-073)   ┐
  provenance (2 lines) + archive pointer (HTML comment, sha256)                                  │ living head
  > OPERATING MODE — Round 11 (binding) + one-line tombstone for the superseded prompt           │ ≤ 12 KiB
  ## CURRENT STATE   (19 keys, values only, ≤ 3 KiB)                                             ┘
  ## OPEN FINDINGS   (history unchanged; Round-11 findings appended as "### Round 11")
  ## LEGACY PLAN · ## GATE PROTOCOL                    (historical, unchanged; declared non-binding)
  ## GATE DECISIONS  (history unchanged)
     + RESTORED from c2055d96^ block (53 rows, B2 §4.1)
     + ### Round 11+ (BM-LEDGER-04 table, newest last)  ← DATE CORRECTION row, GATE-M, GATE-P, GATE-B …
  ## CROSS-CUTTING … ## CAPSTONE checklist             (historical, unchanged)
  ## RETURN PASS     (history unchanged) + superseding note + ### RETURN PASS — current (Round 11)
  ## PHASE LOG …  (the five historical regions, unchanged)
  ## PHASE LOG INDEX — Rounds 1–10 (appended; compact, points at the CSV)
  ## PHASE LOG — Round 11 (append-only, newest last)   ← the only place new entries go (EOF)

docs/build/reports/memory-repair/                      (new; reports/ is an allowed root entry, BM-LAYOUT-01)
  README.md                         provenance, sha256 of every file, verify commands, pointer back to LEDGER lines
  LEDGER_head_R01-R10.txt           byte-identical slice LEDGER.md L1–54 @ <PRE> (126,875 B)
  phase_log_index_r01-r10.csv       one row per PHASE LOG entry / index-only row (§3.10)
  date_corrections.csv              promoted from planning data/date_drift.csv (B1 register; "B3 decides the location")
  append_only_register.csv          promoted from planning data/append_only_violations.csv (B2)

docs/build/BUILD_INDEX.md  + appended "## Index repairs — Round 11 seed (append-only)"
```

Two rejected alternatives:
- Archiving the head as a fenced `.md`: the slice itself contains fences, and a raw `.txt` hashes identically to the
  source slice.
- A new `ledgerArchive:` CURRENT STATE key: BM-LEDGER-02 fixes exactly 19 keys, and the validator's key-order check
  would fail.

### 3.3 Orient budget and how `orchestrate-build` reads it

| read | command (written into the OPERATING MODE) | budget | today |
|---|---|---:|---:|
| O1 LEDGER head | `sed -n '1,/^## OPEN FINDINGS/p' docs/build/LEDGER.md` | ≤ 12,288 B (target 8,192) | 126,875 B |
| O2 (inside O1) CURRENT STATE | — | ≤ 3,072 B; each key line ≤ 256 B | 122,978 B; max line 36,129 B |
| O3 RETURN PASS current | `awk '/^### RETURN PASS — current/{f=1;print;next} f&&/^##/{exit} f' docs/build/LEDGER.md` | ≤ 8,192 B | n/a (table stale) |
| O4 owed obligations | `python3 docs/build/tools/current_projection.py verify` then read `reports/current/CURRENT.md` | ≤ 20,480 B (ADR-126 cap) | 14,203 B |
| O5 latest events | `tail -n 3 docs/build/LEDGER.md` | ≤ 6,144 B (3 × 2 KiB entry cap) | 10,111 B |
| O6 next row | `grep -n "<nextTicket>" docs/tickets/00_MANIFEST.md` + the contract's header | ≤ 2,048 B | — |
| **total** | | **≤ 48 KiB ≈ 12k tokens** | ≥ 127 KB (≈ 32k tokens) for O1 alone |

- `drive-build.sh` already reads keys with `grep -m1 '^key:'`, so it is unaffected. The first match is in CURRENT
  STATE, and no other line in the LEDGER may begin with a CURRENT STATE key name. M2 adds that check.
- Workers still perform their mandatory loads (SIG-MEM-004): the ticket contract and their scoped DEFERRALS rows.
  The orient view never replaces those.
- B6 should propose the same recipe for `orchestrate-build` §0, which today says only "Read CURRENT STATE".

### 3.4 CURRENT STATE target (T5 fills the `<…>` values)

```
projectStatus:   PAUSED             # NOT_STARTED|IN_PROGRESS|BLOCKED|PAUSED|DONE — PAUSED until GATE-B is recorded
nextTicket:      <row-201 id>       # first Round-11 row; rows 184–187 <F4: deferred(D-R10-HUMAN-1)|superseded-by(…)>
lastCompleted:   P33.8              # row 200, Round-10 final row
blockedOn:       (nothing)          # real blocks only (BM-LEDGER-03)
pauseRequested:  true               # flips false with the GATE-B entry (C10)
returnPass:      <ids of RETURN PASS — current, comma-separated, ids only>
manifest:        docs/tickets/00_MANIFEST.md
canonicalSpec:   docs/2_canonical_design_spec.md
memoryRoot:      docs/build
dispatchTarget:  <Q-16 / T3 sizing target>
buildWorktree:   <H2 / Q-16>
buildBranchBase: devin/p33-8-agent-docs-refresh   # Round 11 stacks on the chain tip, PR #190 (§7.1 Q-11)
pinnedBaseSha:   b051732c
chainTip:        <Stage-B seed branch>
benchmarkSet:    N/A
autonomy:        <Q-15>
mergePolicy:     NONE               # the operator merges later (§7.1)
round:           11
updatedAt:       <date -u, ISO-8601 Z>   # <writer> — <≤ 80 chars>
<!-- Rounds 1–10 CURRENT STATE, OPERATING MODE and header: docs/build/reports/memory-repair/LEDGER_head_R01-R10.txt
     sha256 <H>, = git show <PRE>:docs/build/LEDGER.md | sed -n '1,54p'. Dates inside are uncorrected: see date_corrections.csv. -->
```

- The pointer comment sits outside the fenced block but inside the section. No line in it may begin with `word:`,
  because the validator's awk would read it as a key.
- About 2 KB in total.

### 3.5 Archive + hash-linked pointer

1. `LEDGER_head_R01-R10.txt` is exactly `git show <PRE>:docs/build/LEDGER.md | sed -n '1,54p'`. Its sha256 is recorded in
   three places: the LEDGER pointer comment, `memory-repair/README.md` (with `<PRE>`, the line range and 126,875 B), and
   the C6 PHASE LOG entry.
2. **Verify:** `shasum -a 256 docs/build/reports/memory-repair/LEDGER_head_R01-R10.txt` must equal the recorded value,
   and so must `git show <PRE>:docs/build/LEDGER.md | sed -n '1,54p' | shasum -a 256`.
3. The PRIOR chains carry 41 October dates. They are **not** corrected in the archive, which is byte-identical. The README
   points to `date_corrections.csv` (B1 §5.1: "archived PRIOR chains go into the archive with a pointer to the correction
   register").

### 3.6 OPERATING MODE — Round 11 skeleton (T5 fills `{…}` from B5 / Q-15 / Q-16 / H2)

```
> **OPERATING MODE — Round 11 (binding; recorded <date -u> by <T5 author>; operator approval: GATE-B, GATE DECISIONS <date>).**
> Supersedes the Round-1 OPERATING MODE (2026-09-08) and the Round-10 import amendment (2026-09-27), archived
> verbatim in reports/memory-repair/LEDGER_head_R01-R10.txt (sha256 <H>). Their "gitignored", ".agents/scratch",
> "17 tickets" and "Do not resume until Codex reports…" clauses no longer bind.
>
> **Resume prompt (paste verbatim in a fresh session; cwd {buildWorktree}):**
> ```
> Invoke the orchestrate-build skill with ledger=docs/build/LEDGER.md dispatch={Q-16 tier}
> autonomy={Q-15} build_worktree={buildWorktree}. ORIENT CHEAPLY: never read LEDGER.md, DEFERRALS.md or
> BUILD_INDEX.md whole. Run exactly O1–O6 from the LEDGER's OPERATING MODE (≤ 48 KiB), then act on CURRENT STATE.
> R1 Clock: every date or time you write comes from `date -u` at that moment. Never infer, extrapolate or use
>    "previous entry + 1 day". A date later than now is a bug. PHASE LOG lead date = UTC date; add the ISO time inside.
> R2 CI truth: at every ticket boundary run `gh pr checks <PR>`. Green = every required check passes on GitHub;
>    local-only = "locally-green". {B5 rule for a red PR}.
> R3 Append-only: never remove or rewrite a line in GATE DECISIONS, PHASE LOG, OPEN FINDINGS, RETURN PASS,
>    DEFERRALS, readouts, BUILD_INDEX rows, executed contracts, ADR bodies or events.jsonl. Corrections are new dated
>    entries naming what they correct. New PHASE LOG entries go only at EOF ("PHASE LOG — Round 11"), in the shape
>    `- YYYY-MM-DD — <ID> <kind> — …` (no markup before the kind; ≤ 2 KiB; details belong in runs/<ID>.md).
> R4 CURRENT STATE holds values only: one line per key, ≤ 256 B, no PRIOR chains.
> R5 Gates: never sign, tick or pre-answer a gate. An agent-drafted readout is labelled agent-drafted and the operator
>    confirms the exact text. Record the operator's words verbatim (GATE DECISIONS table). {B5 rules on blanket or
>    pre-authorised approvals}. A pending gate is a pause (PAUSED + RETURN PASS), never a guess.
> R6 Production: {B5 rule: live stages only inside the ticket that owns them, with recorded scope}. Never merge, tag or
>    push main (mergePolicy NONE).
> R7 Harness: {Q-16 harness + dispatch-tier binding; subagent sizing warning}.
> R8 {remaining B5 operating rules, each citing its incident}.
> Resume from CURRENT STATE.
> ```
> Binding: this block, CURRENT STATE, GATE DECISIONS, "RETURN PASS — current", "PHASE LOG — Round 11".
> Historical only (do not obey): LEGACY PLAN, GATE PROTOCOL, CROSS-CUTTING INVARIANTS, OUT OF SCOPE,
> SETUP/CAPSTONE checklists and results, every earlier PHASE LOG section, the RETURN PASS table above "current".
```

About 4.5 KB. The B5 rules must fit in the remaining ≈ 3 KB; longer rationale goes in the Round-11 ADR, not the ledger.

### 3.7 Superseding notes for stale amendments

Every note is appended or inserted, and none edits an existing line.

- **LEDGER head.** Archived (§3.5). The tombstone is the first sentence of the new OPERATING MODE. The C6 PHASE LOG
  entry quotes each voided clause and its reason (§2.3):
  - For "Do not resume until Codex reports…", the reason is: *condition met in practice at the Round-10 resume on
    2026-09-27 (PHASE LOG L417/L419, PR #155); voided here*.
- **Manifest head** (for T3; B2 NEW-9 applies).
  - Insert one Round-11 dispatch amendment above the two existing blockquotes.
  - Under each old blockquote, insert the line: `> *Superseded <date -u> by the Round-11 dispatch amendment above;
    the "2026-10-19" date is corrected in reports/memory-repair/date_corrections.csv (true ≤ 2026-09-28T01:27Z).*`
- **GATE PROTOCOL / OUT OF SCOPE / SETUP / CAPSTONE sections.** They get no in-place notes. They are declared
  non-binding once, in the OPERATING MODE.
- **`OPERATIONAL_READINESS.md` §(f3) footer.** "SIG-MEM-004 — owner P33.8 … when the chain reaches it" is stale. The
  Round-11 REC tail appends a dated note; it is not seed work.
- **`CURRENT.md` header.** "→ P32.8" is fixed by the projection template (M5), not by hand.

### 3.8 GATE DECISIONS — restoration placement and the form question (B2 open question 1)

1. **C3** appends B2 §4.1's block verbatim at the **end** of the section, after L188–190, before
   `## CROSS-CUTTING INVARIANTS`. That means the caption plus the 6-column header and 53 rows, sha256 `baec891d…82bd8`.
2. **Form decision.** The restored table and the historical bullets both stay as they are; the section is never
   reordered or re-headed. New entries from Round 11 go in `### Round 11+ (BM-LEDGER-04 table; newest last; date -u)`
   at the end of the section:
   `| date (ISO Z) | ticket | gate | item | answer — operator's words verbatim, or "provided: yes/no" | consequence |`.
   - Rationale: a worker finds its answers with `grep '| <ticket> |'` (BM-GATE-01). Order and date checks become
     mechanical (V8). The F-29 lesson (verbatim words, no agent signature) has a fixed column.
3. **Ordering note.** A one-line appended note records that entries from 2026-09-23 on were inserted at the top (NEW-3),
   and that the true order is recoverable with `git blame`.
4. GL-GATE-06 citations resolve again after C3: 58 `sources.toml` lines, 21 rights packets, and the P26.2 contract.

### 3.9 B1 date-correction entries (in the seed; the full register is `date_corrections.csv`)

- **GATE DECISIONS** (Round 11+ table): one `DATE CORRECTION (ADR-<corr>)` row. It covers L116 GATE-G3 and L117 S3
  deferral: recorded `2026-10-19`, true ≤ 2026-09-28T03:49Z (`95c8a73f`) and ≤ 2026-09-28T01:27Z (`a33cd6ec`), with the
  operator confirmation pending (Q-B1-2). It also points at the register rows for the other GATE DECISIONS dates.
- **PHASE LOG — Round 11:** one `ROUND11 correction` entry covering:
  - the 25 entries dated after their writing commit;
  - the 15 Round-3 entries recorded as 09-10;
  - the 12 order inversions.

  Per-line recorded → true values are in `phase_log_index_r01-r10.csv` (`date_status`, `correction_ref`), and
  nothing is edited.
- **BUILD_INDEX:** the `Row corrections` table in §3.11 carries B1's landed-date rows.
- **CURRENT STATE PRIOR chains:** archived verbatim, with a pointer to the register (§3.5).
- **Not in the seed:**
  - `events.jsonl` date-correction events, which need the fixed tool (M3);
  - ADR footers, which belong with the correction ADR in T1;
  - code, fixtures and sqitch comment lines, which are B1 tickets. Sqitch plan lines are **never** edited (B1 §5.7).

### 3.10 PHASE LOG INDEX (appended; history not moved)

- **Machine form:** `reports/memory-repair/phase_log_index_r01-r10.csv`, generated by the seed script.
  - Columns: `idx, order_key(introduced_utc, line), recorded_date, introduced_by (git log -S<entry prefix> --reverse,
    fallback blame), last_written_by, line@PRE, section, lead_id, kind(done|partial|gate|pause|round|inserted|resume|
    other), entry_sha256_12, build_index_seq, date_status(ok|future|past), correction_ref`.
  - It has 170 entry rows plus 16 index-only rows (`kind=missing-entry` / `no-done-entry`, §2.6).
  - `entry_sha256_12` anchors each row to its entry independently of line shifts. The head replacement moves every
    line number.
- **LEDGER form:** `## PHASE LOG INDEX — Rounds 1–10`, about 3 KB. It has one row per round or era:
  `| era | tickets | true dates (git) | recorded dates | where (heading → lines @PRE) | entries |`, plus the CSV sha256
  and the rule "find an entry: `grep -n -F '<first 40 chars>' LEDGER.md`". Its rows:
  - R1: 21 entries, L247–363;
  - R3: 12, L369–380;
  - R3/4: 11, L381–391;
  - P25–26: 16, L393–414;
  - R5: 10, L290–300;
  - R6: 6, L302–307;
  - R7: 3, L308–310;
  - R8: 6, L314–324;
  - R9: 18, L328–351;
  - R10: 35, split across L270–271, L353–357 and L415–462;
  - 32 orchestrator and round events.
- **`## PHASE LOG — Round 11`** is created in the same commit and stays the last heading in the file (V4). **No
  retro "done" entries are fabricated** for the 16 tickets; the index names them.

### 3.11 BUILD_INDEX repairs (appended section `## Index repairs — Round 11 seed (append-only; <date -u>)`)

1. **Late marker rows** in the BM-INDEX-01 11-column shape, `kind = gate (marker, retro-indexed <date>)`, following the
   row-87 precedent:
   - `190 | GATE-G3 | … | — (no PR; marker) | … | ≤2026-09-28T03:49Z | … | evidence readouts/GATE-G3.md`;
   - `195 | GATE-ACCEPT | … | ≤2026-09-28T18:47Z | … | readouts/ACCEPT-R10.md`.

   Both landed dates cite B1 corrections; the recorded readout dates are wrong for G3.
2. **Row corrections table:** `| seq | ticket | field | recorded | corrected | evidence | source | recorded_at |`:
   - PR fills: 76–81 → #76–#81 (+ `PR base = main; merged 2026-09-24`); 94 → #89;
   - `170 (L243, P32.10a)` → manifest row `170a`;
   - row 157 kind → `ticket` (note only);
   - B1's landed-date rows.
3. **Not-landed note:** 158/159 unused and 184–187 deferred have no rows by design. It points to the manifest and to
   F4's outcome.

### 3.12 `nextTicket` with rows 184–187 deferred and new rows 201+ (options for F4 and S2)

| option | CURRENT STATE | manifest | consequence |
|---|---|---|---|
| **N1 — skip-with-record (recommended default)** | `nextTicket: <row 201>` | rows 184–187 annotated `deferred(D-R10-HUMAN-1)`, or `superseded-by(<rows>)` if F4 re-scopes them. Files kept; a Round-11 Plan-extensions line | Monotone, machine-checkable. Validator rule (V2): `nextTicket` = the lowest chain row that is not landed and not `deferred` / `superseded` / `unused`. Rows 184–187 stay owed through DEFERRALS and RETURN PASS |
| N2 — re-enter the spine first | `nextTicket: HUMAN-H4` | unchanged | Only if the operator (Q-8/Q-24) puts human evaluation first. The Round-10 contracts are bound to the superseded fixture candidate `p-17b713` (B1 §5.8), so in practice N2 becomes "N1 with re-scoped rows placed first" |
| N3 — Round-11 kickoff marker | `nextTicket: GATE-G4` (row 201, marker) | a marker row whose readout cites GATE-P, GATE-B and the seed verification | Adds a recorded operator touchpoint inside the loop and gives BUILD_INDEX a row. Redundant with GATE-B unless the operator wants it |
| N4 — leave `HUMAN-H4` (status quo) | — | — | **Rejected.** It resolves to a deferred row: the orchestrator either pauses at a marker the operator deferred, or dispatches a stale contract |

Whatever F4 decides maps onto N1 or N2. The seed writes the value that F4 and S2 choose. T6 asserts it (§5.3).

### 3.13 RETURN PASS regenerated from §(f3), and how it stays in sync

1. **Seed (C7, after S1/T4 dispositions).**
   - Append a note under the old table. It says: "historical as of P31.16 (2026-09-27); stale rows per A3 NEW-2: P21.1,
     P21.4, P23.6, P31.16; key-only P24.3/P24.6/P24.7; table-only P31.4; P23.1 has no deferral (NEW-3 A3 → T4 adds a
     D-row or S1 dispositions HG-05); superseded, not edited, by the table below."
   - Then append `### RETURN PASS — current (Round 11; generated <date -u> from OPERATIONAL_READINESS §(f3) @ <sha> +
     S1 dispositions)`, with columns `| ticket | obligations | gates / blocking domain | what the operator must do |
     re-run line |`.
2. **Membership rule.** An owed obligation (events head OPEN/PARTIAL) whose S1 disposition is
   `live-return-pass(<ticket>)` gets a row keyed by that ticket. §(f3) supplies the re-run line: for example
   `179_P32.18 … live_verification=true` for D-P32.18-1, or `P21.3_…` for D-P21.3-2.
   - Obligations whose return path has no ticket (scheduled crons, pure operator decisions) are listed with ticket `—`
     and **excluded from `returnPass:`**.
   - Obligations that become Round-11 rows are **not** RETURN PASS rows.
3. **`returnPass:`** is the sorted, comma-separated id list of the table's tickets.
4. **Staying in sync (M5).**
   - `docs/build/tools/return_pass.py generate` renders the table and the key from `events.jsonl` heads and a small
     committed `return_pass.toml` (obligation → ticket + re-run line, seeded from §(f3)).
   - `check` enforces three things: the key equals the table tickets; the table equals the generated output; and every
     owed obligation sits in exactly one home: a RETURN PASS row, a manifest row, or a later-phase/wontfix disposition.
   - Regeneration triggers: an `implement-spec` close that opens or closes a live-leg deferral, an orchestrator gate
     skip, and the round's REC tail.

### 3.14 Considered and deferred: rotate the whole LEDGER per round

The alternative: archive `LEDGER.md` whole to `reports/…/LEDGER_R01-R10.md` and start an empty Round-11 file. It is
rejected for Round 11 for four reasons:
- it removes append-only sections, which conflicts with P7 and B2's guard;
- the P21.x contracts and GL-GATE-06 citations point at "LEDGER GATE DECISIONS";
- the validator couples the PHASE LOG with BUILD_INDEX in one file;
- the META_PLAN says "index instead of moving history".

Size after the seed (inference):
- 679,109 − 126,875 (old head) + ≈ 10,000 (new head) + 25,500 (restored GD) + ≈ 3,000 (corrections) + ≈ 6,000
  (RETURN PASS current) + ≈ 3,000 (index) + ≈ 3,000 (Round-11 GD/PL seed entries) ≈ **603 KB**.
- Growth per round with the 2 KiB entry cap: ≈ 40 rows × ≤ 2 KiB ≈ 80 KB.

**Revisit trigger:** the LEDGER exceeds 1 MiB, or the build-memory skill gains a round-archive key (B6).

---

## 4. Shadow mode: D-R10-MEMORY-1 cutover vs retiring the projection

**Evidence against B2, §2.7 and the spec text.**

| surface | what the record shows | implication |
|---|---|---|
| `events.jsonl` (ADR-126) | 4 versions, 3 wholesale rewrites; `seq=0` only; **0 transitions**; 8 e0 anchors mutated OPEN/PARTIAL→DONE in place by P33.1; `recorded_at 2026-10-21` on all 97 | The "event chain" has never worked as an append-only log. Its cell-divergence check (`activation-check`) passes **because** history was rewritten to match the cells |
| closeout journal (ADR-127) | 2 of 35 Round-10 closeouts (P32.8, P32.9); abandoned after P32.9; host-local; authority defaults to the main worktree (NEW-5) | No operating evidence. Enforcing it means applying `contract/patch/1..3` to user-global skills (B6, after GATE-P; Q-13: never from this repo) |
| projection (ADR-126) | deterministic; `verify` green; CURRENT.md 14 KB is the cheapest owed-work view (vs DEFERRALS 339 KB) | It is only as true as its inputs (F-27/F-28). Its value to orient is real |
| spec | SIG-MEM-002: transitions must be evidence-backed and retain history. SIG-MEM-003: "workflow activation stays shadow-only until a verified operator-approved cutover" | Leaving the journal in shadow is spec-compliant with no waiver. Retiring the events would need a waiver ADR |

**Options.**
- **(A) Cut over now.** Enforce events and the journal at the first Round-11 boundary. *Rejected.* Enforcement would
  run on rewritten history. The skill edits are out of repo, and the journal has no operating evidence.
- **(B) Retire both.** Freeze the events and the projection as historical, with the DEFERRALS cells as the sole
  authority. *Rejected.* It restores "last token wins": 15 reconciled conflicts become implicit again. SIG-MEM-002 needs
  a waiver, and orient loses its compact owed view.
- **(C) Split D-R10-MEMORY-1 (recommended; operator decides at S5 because D-R10-MEMORY-1 is operator-owned).**
  1. **Obligation events: repair, then enforce in-repo (M3 + M1 + M6).**
     - Treat `events.jsonl` as `prefix` append-only; `migrate` refuses once the file exists.
     - Append the correction and e1 transition events of B2 §5.1 and the date corrections of B1 §5.6.
     - CI checks that a DEFERRALS leading-token change in a PR comes with a matching appended transition (B2 §7
       `row-annotate` (a)).

     This is the "event half" of the cutover. It needs no skill edit, because CI enforces it at PR level.
  2. **Projection: keep, as an advisory, CI-verified orient view.** `verify` runs in the CI `docs` job and
     `known_inconsistencies` must be empty. The landings come from S1 dispositions, and the header text is fixed (M5).
     The authority stays LEDGER + DEFERRALS (ADR-126).
  3. **Closeout journal: stays shadow in Round 11.** Keep the code and tests; do not wire it into entry points. The
     worktree-safe validator patch (contract/patch/3) is already live and stays.
     - **Trigger to cut over:** parallel ticket dispatch, a multi-worktree build, or a second host/harness writing
       memory concurrently.
     - At the trigger, the prerequisites are: B6 patches applied by the operator; `--authoritative-root` set
       explicitly (NEW-5); and a dry-run in a scratch clone.
  4. **Record.** A new ADR (from ADR-146) supersedes ADR-126/127's cutover statements. The D-R10-MEMORY-1 legs go to S1
     as follows:
     - events leg → `ticket(M3/M6)`, DONE on enforcement evidence;
     - journal leg → `later-phase(trigger above)`;
     - SIG-MEM-003 verdict → `MET-ENGINEERED` (§8.3).

---

## 5. Migration procedure

`<PRE>` is the seed base, the chain tip (`b051732c`) or its H2 successor. `PD` is the planning directory. For every
commit:
- `bash scripts/docs/check-build-memory.sh . --json docs/build/logs/b3-<Cn>.json` exits 0;
- `python3 PD/tools/seed_verify.py <Cn> --pre <PRE>` passes. This is a planning-side script written in Stage B, like
  `extract_universe.py`, and is not product code. It checks **0 removed lines on protected paths**, with C6 excepted
  for L1–54, and the step's hashes and budgets;
- a `date -u` stamp goes into the commit body.

`current_projection.py verify` is **expected STALE from C1 until C9 regenerates it**; this is documented, not a failure.
`obligation_events.py check`, `check_backlog.py` and `check_coverage_matrix.py` are unaffected until T4. They are run at
C7 and C9.

### 5.1 (a) Stage-B seed — must be true before any orchestrator resumes (T2 → T5)

| # | commit (one purpose each) | acceptance |
|---|---|---|
| C0 | preflight, no commit: operator go for control-ledger edits recorded (P10, B2 §4.1); A1 delta run; `<PRE>` pinned | delta shows no unexplained `mem.*` change |
| C1 | add `reports/memory-repair/{README.md, date_corrections.csv, append_only_register.csv}` | sha256 of each CSV = the planning `data/` file (or a documented added column); layout check green |
| C2 | generate `phase_log_index_r01-r10.csv`; append `## PHASE LOG INDEX — Rounds 1–10` and `## PHASE LOG — Round 11` with the first entry `- <date> — ROUND11 round — …` | 186 CSV rows; each `entry_sha256_12` matches a LEDGER line @PRE; last `## ` heading = Round 11; 0 removed lines |
| C3 | GATE DECISIONS restoration (B2 §4.1) + ordering note + `### Round 11+` table header; PHASE LOG `ROUND11 restored` entry | 53-line slice sha256 `baec891d…`; each source line occurs once; 0 removed lines; `grep -c GL-GATE-06` inside GATE DECISIONS ≥ 1 |
| C4 | B1 corrections: GATE DECISIONS DATE CORRECTION row; PHASE LOG `ROUND11 correction` entry; BUILD_INDEX `Row corrections` (date rows) | every `date_corrections.csv` row for LEDGER/BUILD_INDEX is referenced by exactly one correction; 0 removed lines |
| C5 | BUILD_INDEX index repairs: rows 190/195, PR fills (#76–#81, #89), 170a, not-landed note; PHASE LOG entry | every manifest chain row is either indexed or listed as unused/deferred; 0 removed lines |
| C6 | **living head**: write `LEDGER_head_R01-R10.txt` (L1–54 @PRE) and replace L1–54 with the new head (Round-10 values kept, slimmed; `projectStatus: PAUSED`, `pauseRequested: true`; interim OPERATING MODE = "Round-11 seed in progress — not a resume point; see PD/HANDOFF.md"); PHASE LOG `ROUND11 round` entry quoting the voided clauses | archive sha256 = `sed -n 1,54p` @PRE sha256; removed lines ⊆ old L1–54; head ≤ 12 KiB; 19 keys in order; `status_val` returns a single token for each key; enum valid |
| C7 | RETURN PASS superseding note + `### RETURN PASS — current` (needs S1/T4 dispositions) + `returnPass:` ids | key == table tickets; every owed obligation in exactly one home (script); each A3 NEW-2 disagreement resolved by a row or the note |
| C8 | Round-11 CURRENT STATE values + OPERATING MODE (§3.6, B5 rules filled) + GATE DECISIONS rows for GATE-M and GATE-P (verbatim, §7.1) + manifest Round-11 dispatch amendment is T3's | stale-token scan of the head = 0 hits; every path named in the head exists; `nextTicket` = the value F4/S2 chose (rule V2); `updatedAt` from `date -u`; head ≤ 12 KiB |
| C9 | `current_projection.py generate` | `verify` exit 0; CURRENT.md shows round 11, the chosen `nextTicket`, 0 known inconsistencies, ≤ 20 KiB; `make docs-check` green; `make check` green |
| C10 | after GATE-B: `projectStatus: IN_PROGRESS`, `pauseRequested: false`, GATE DECISIONS GATE-B row (verbatim), PHASE LOG `ROUND11 gate` entry | reader returns `IN_PROGRESS`/`false`; 0 removed lines outside the key lines |

- **Entry-word hazard.** The current validator requires a BUILD_INDEX row for any PHASE LOG bullet that contains the
  bare word `done` **and** is parseable, and with the no-bold shape the seed entries are parseable. So seed entries
  (`ROUND11 round/restored/correction`) must not contain the word "done".
- **Dates.** Entries keep a date-only lead so that the current parser works. The ISO time goes inside the entry.

### 5.2 (b) Early Round-11 tickets (code + tests; T3 numbers them in the first memory-repair wave)

| id | scope | acceptance |
|---|---|---|
| M1 | `check-append-only` (B2 §7) + `APPEND_ONLY.toml` + new mode `living-archived` (the LEDGER head: a removal is allowed only if the removed bytes equal a file added under `reports/memory-repair/` in the same commit) + CI `docs` job + pre-commit | backtest flags exactly B2's 42 `loss` + 4 `transition-unjustified` rows and each misdated stamp; passes the 405 benign rows; passes seed commits C1–C10 |
| M2 | ledger-contract validator (V1–V6, V8, V10 in §6), including the bold-aware PHASE LOG parser with a pseudo-id allow-list (`SETUP`, `OPERATOR`, `ROUND*`) and marker evidence = readout; tests assert invariants, never current values | on the LEDGER @PRE: fails V1/V2/V3 (proves it catches F-23); on the seeded LEDGER: passes; replaying the history finds exactly the 4 known pseudo-id cases, all allow-listed |
| M3 | `obligation_events.py` repair (no regenerate; `--recorded-at` defaults to `date -u`; reject future dates and `recorded_at` < previous event; `correction` kind) + data: correction events for the 3 rewrites, e1 transitions for the 8 mutated anchors, B1 date corrections | `events.jsonl` @PRE is a byte prefix of the new file; ≥ 8 transitions; `check` green; `activation-check` result recorded as-is |
| M4 | remaining B2 restorations (DEFERRALS cell history + 5 unjustified transitions via e1 events; readout addenda confirmed by the operator; `> Amended` contract blocks; manifest Plan-extension corrections; run-ledger superseded records; P26.16 PHASE LOG corrections), run under M1 | each B2 `loss` / `transition-unjustified` row maps to one restored block; guard green |
| M5 | `return_pass.py` generator + check; projection fixes (landings from dispositions, F-28; header text; `verify` in the CI `docs` job; RETURN PASS in CURRENT.md) | regenerating reproduces the C7 table byte-for-byte; CI runs `verify` |
| M6 | D-R10-MEMORY-1 disposition per §4 (C): ADR, CI rule "DEFERRALS lead-token change ⇒ matching transition", journal trigger recorded | ADR landed; a fixture PR that flips a cell without an event fails CI |

B1's own tickets (constants, fixtures, the sqitch `planned_at ≤ commit` guard, candidate supersession) are outside B3.

### 5.3 T6 orient dry-run (GATE-B evidence)

A fresh subagent receives **only** the §3.6 resume prompt, in a read-only checkout of the seed PR head. Pass criteria:
1. it executes O1–O6 and reports the bytes it read: **≤ 48 KiB**, and the head alone ≤ 12 KiB;
2. it resolves `projectStatus = PAUSED` (before GATE-B), `nextTicket = <F4/S2 value>`, `returnPass = <C7 ids>`, and
   `blockedOn = (nothing)`;
3. it names the manifest row and contract for `nextTicket` and states that its dependency has landed;
4. it never opens LEDGER, DEFERRALS or BUILD_INDEX whole;
5. `gh pr checks <seed PR>` shows all 5 checks green (P11).

---

## 6. Validator and CI requirements (input to B4)

| id | requirement | catches |
|---|---|---|
| V1 | LEDGER head (line 1 → before `## OPEN FINDINGS`) ≤ 12,288 B (fail), warn > 8,192 | F-23 size |
| V2 | CURRENT STATE: 19 keys in order (exists); each line ≤ 256 B (fail > 512); no `PRIOR`; `projectStatus` ∈ {NOT_STARTED, IN_PROGRESS, BLOCKED, PAUSED, DONE}; `pauseRequested` ∈ {true, false}; `mergePolicy` ∈ {NONE, OPERATOR, AUTO-BOTTOM-UP}; `autonomy` ∈ {auto, checkpoint, manual}; `round` an integer; `updatedAt` ISO-8601 Z and ≤ commit time; `returnPass` ids only (BM id grammar); `nextTicket` = the lowest not-landed, not-deferred/superseded/unused row, or DONE; no other LEDGER line starts with a key name | F-23 enum, NEW-6, N4 |
| V3 | stale-path/stale-token check on the head: every repo path named exists; deny-list (`.agents/scratch`, `gitignored`, `never commit`, `PHASE PLAN`, `Do not resume until`); a "N tickets" claim matches the manifest; harness names only inside R7 | F-23 stale prompt |
| V4 | PHASE LOG: bold-aware parser; new entries only at EOF, in the last section `## PHASE LOG — Round N`; kind ∈ {done, blocked, inserted, split, gate, pause, round, correction, restored}; entry ≤ 2,048 B; lead date ≤ commit date; done ⇒ BUILD_INDEX row + runs/pr (fix the vacuous check); reverse: a BUILD_INDEX row added in a PR ⇒ a done entry in the same PR | F-24, NEW-1, NEW-2, NEW-8 |
| V5 | BUILD_INDEX: unique seq (`170a` form allowed); no `PR pending` / `#TBD` left after the ticket's stamps commit; every executed marker (signed / PASSED / SKIPPED readout) has a row; kind ∈ vocabulary | F-24, NEW-7 |
| V6 | RETURN PASS: `returnPass:` == tickets in `### RETURN PASS — current`; each owed obligation in exactly one home; the table equals `return_pass.py generate` output (M5) | F-25, A3 NEW-2 |
| V7 | `check-append-only` (B2 §7) + `living-archived` mode + `prefix` mode for `*.jsonl`; first-parent merge diffs | F-22, F-26, B2 classes |
| V8 | GATE DECISIONS: Round-11 entries in table form, appended at the section end (newest last); date ≤ commit; the answer column non-empty and quoted | NEW-3, F-29 |
| V9 | `current_projection.py verify` in the CI `docs` job; `known_inconsistencies` empty; CURRENT.md ≤ 20 KiB; landings name an existing chain row or BL id | F-27, F-28 |
| V10 | global date rule (B1/B2): an added date token > commit UTC date fails unless it carries a `scheduled:` / allow-list marker | F-21 |
| V11 | orient probe in CI: runs O1–O6 against the tree, asserts ≤ 48 KiB and that `nextTicket` resolves under the V2 rule | the T6 criteria, kept true after the seed |

B6 should carry V2's enum and V4's kinds (`correction`, `restored`) upstream into `layout.md` BM-LEDGER-02/06. B6 should
also carry the orient recipe into `orchestrate-build` §0, and a 2 KiB entry cap into `implement-spec`'s close step.

---

## 7. New findings (`findings/incoming/B3.csv`)

| id | title (short) | sev | relation |
|---|---|---|---|
| NEW-1 | The validator's PHASE-LOG-done→BUILD_INDEX check is vacuous: 0 of the 139 "done" bullets are parsed (bold ids) | S2 | extends F-27 |
| NEW-2 | PHASE LOG split across 5 regions; 54 entries under a CAPSTONE heading; Round 10 in 3 places | S2 | refines F-24 |
| NEW-3 | GATE DECISIONS written newest-first since 2026-09-23 but oldest-first before; top-insertion evades removal-only guards; bullets not the BM-LEDGER-04 table | S2 | new; feeds B2 guard |
| NEW-4 | Closeout journal used for 2/35 Round-10 closeouts; `activation-check` passes only because P33.1 rewrote the anchors; its clock stamps contradict BUILD_INDEX dates | S2 | links F-26, F-21, D-R10-MEMORY-1 |
| NEW-5 | `closeout_protocol` authority defaults to the main worktree (contrary to BM-ROOT-02) | S3 | new |
| NEW-6 | CURRENT STATE values are not machine-readable (returnPass prose cut at `#`, updatedAt truncated, Round-1 base/sha, harness-specific dispatch comment) | S3 | extends F-23/F-25 |
| NEW-7 | BUILD_INDEX has 7 "PR pending" rows, all with real PRs (#76–#81, #89); row 157 kind off-vocabulary | S3 | refines F-24 |
| NEW-8 | PHASE LOG entries are median 2.7 KB (111/170 > 2 KiB; 72 % of LEDGER bytes) versus BM-LEDGER-06's "one-line summary" — the growth driver | S3 | new; feeds V4 |

---

## 8. Open questions (recorded, not answered)

1. **Operator (S5): the D-R10-MEMORY-1 split.** Recommendation (C) needs the operator to accept the journal leg as
   `later-phase(trigger)` rather than a cutover.
2. **F4 / S2:** the `nextTicket` option (N1 recommended; N3 if the operator wants a kickoff marker inside the loop).
3. **B5:** the operating rules that fill R2/R5–R8. They must fit about 3 KB. Anything longer goes to the Round-11 ADR.
4. **Operator (P10, B2 Q3):** confirm that C3 (GATE DECISIONS restoration) lands in the seed before the head
   restructure, as ordered here: "restore first, so B3 migrates a complete record".
5. **T4 / S1:** HG-05 / P23.1 has no deferral row (A3 NEW-3). Should it get a D-row, or a disposition as operator-owned
   integration (§7.1: the operator merges later)?
6. **B6:** upstream the V2 enum and V4 kinds, and decide whether `layout.md` should allow a Round-archive key. That
   choice decides §3.14's revisit.

## 9. Reproduction (read-only; scratch not committed)

- Section and key scan: a `python3` loop over `LEDGER.md` lines, printing `##` boundaries, byte sums, the `| PRIOR`
  split counts and `2026-10-\d\d` counts per CURRENT STATE line.
- PHASE LOG and BUILD_INDEX: `scratchpad/B3/analyze.py`. It covers dated-entry regex, section attribution, lead-id
  parsing, inversions, BUILD_INDEX seq/duplicate/missing/"PR pending", and the four F-24 methods. It also used
  `git blame --line-porcelain b051732c -- docs/build/LEDGER.md` for write times.
- Validator replay: `ID_RE` from `scripts/docs/check-build-memory.sh:146` and the loop at :372-376, run over
  `grep -E '^-[[:space:]]' docs/build/LEDGER.md`. Result: 139 bullets contain "done", 0 ids checked.
- Reader emulation: `status_val` from `~/agent-skills/skills/orchestrate-build/scripts/drive-build.sh` (`grep -m1` + sed
  strip at `#`), run for each key.
- PRs: `gh pr list --state all --head <branch> --json number,state,createdAt,baseRefName,mergedAt` for the 7 "PR pending"
  branches.
- Journal: `ls "$(git rev-parse --git-common-dir)"/sig-closeout/operations`, 2 files, reading only `ticket_id`, `state`,
  `created_at` and `updated_at`.
