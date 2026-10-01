# B2 — Append-only integrity scan and restoration design

Row **B2** of `META_PLAN.md` (Stage P, stream B). **This row is read-only and design-only.** It restores
nothing and edits no control file (P10). It writes three things: this note, `data/append_only_violations.csv`
(one row per commit × file × section that removed a line from a protected artifact) and
`findings/incoming/B2.csv`. Scratch scripts and raw outputs are in `docs/build/logs/next-phase/B2/` (gitignored).

- **Scanned history:** every commit reachable from the planning branch: 501 commits, of which 485 are chain
  history up to `b051732c`. No protected file changed after `b051732c` (`git diff --stat b051732c HEAD` is
  empty for the scanned paths).
- **Observed:** 2026-09-30T17:10Z (`date -u`). Every date below comes from git: the committer date in UTC unless
  it is labelled local.
- **Evidence class:** `code` (git history), unless a claim is marked *inference*.

---

## 1. Result in one screen

| artifact (mode) | benign | transition-justified | transition-unjustified | loss |
|---|---|---|---|---|
| `LEDGER.md` GATE DECISIONS / PHASE LOG / OPEN FINDINGS / RETURN PASS (append-only) | 21 | 9 | 0 | **6** (the c2055d96 GATE DECISIONS deletion, counted twice because merge `e2175c93` carried it, + 4 PHASE LOG rewrites) |
| `DEFERRALS.md` (append-only) | 132 | 52 | **4** | **14** |
| `BUILD_INDEX.md` (historical) | 38 | 6 | 0 | **3** |
| `runs/*.md` (historical after close) | 69 | 0 | 0 | **5** |
| ticket contracts, executed ones frozen (BM-TICKET-04) | 80 | 19 | 0 | **6** |
| `00_MANIFEST.md` Plan extensions / Spec amendments applied (append-only) | 10 | 2 | 0 | 0 (2 in-place Plan-extension edits classed benign, restoration still proposed) |
| `readouts/*.md` (append-only) | 1 | 0 | 0 | **5** |
| `adr/ADR-*.md` bodies after landing (frozen) | 3 | 0 | 0 | 0 |
| `obligations/events.jsonl` (append-only) | 0 | 0 | 0 | **3** |
| `obligations/coverage_assessments.jsonl` | 1 | 0 | 0 | 0 |
| `adr/README.md` (generated) | 11 | 0 | 0 | 0 |
| Round-9 drafts moved into `docs/tickets/` | 39 | 0 | 0 | 0 |
| `spec_src/99c_appG_corrections.md`; manifest `## Spec amendments applied` | 0 | 0 | 0 | 0 (no line ever removed) |
| **Total CSV rows (539; 208 distinct commits)** | **405** | **88** | **4** | **42 (24 commits)** |

`LEDGER.md` `CURRENT STATE` is living state. It had 523 removed lines in 134 commits, every one a `key: value`
state line (`nextTicket`, `updatedAt`, `chainTip`, …). These are excluded from the CSV.

**Most serious, in order:**
1. **S1.** `c2055d96` deleted the entire 53-row GATE DECISIONS table (§4). None of the 53 rows survives
   verbatim. GL-GATE-06, which HEAD still cites as the authority for 58 `sources.toml` rights lines and 21 rights
   packets, is orphaned. Six rows were the only record of their gate answers.
2. **S2.** `events.jsonl` was regenerated three times. The last regeneration (`7a2ff9fa`, P33.1) changed the
   status of 8 existing events in place instead of appending transitions (§5.1).
3. **S2.** In DEFERRALS, `b542f236` erased the dated history of 6 cells. The dated snapshot "P30.4 sweep
   (2026-09-24)" was edited after its date. 5 status transitions have no valid justification (§5.2).
4. **S2.** Executed contracts were rewritten in place: P25.4 and P25.5 scope and ACs, and P29.3 ACs. No contract
   in the repo has ever carried a `> Amended` note (§5.3).
5. **S2/S3.** The readout signatures overwrote their pending state, and the "no agent signs" guard text went with
   it (§5.4). Closed PHASE LOG, BUILD_INDEX and run-ledger records were overwritten as hosted work progressed (§5.5).

**Restoration** is always an appended, dated `RESTORED from <sha>^` block that quotes the removed text verbatim
and records its sha256. Nothing is re-inserted in place (§7). **The proposed guard** is a history-aware CI check,
`check-append-only`, that diffs each PR against its base, and each merge against its first parent, under a
per-region mode policy. It would have failed every loss and unjustified-transition class found here. It would
pass every benign class (§8).

---

## 2. Method

1. **Scan** (`scan.py`). For every commit in `git rev-list HEAD`, run `git diff -M -U0 <first-parent> <commit>`
   over the protected paths: `docs/build/LEDGER.md`, `docs/tickets/**`, `docs/build/readouts/**`, `docs/adr/**`,
   `spec_src/99c_appG_corrections.md`, `docs/build/BUILD_INDEX.md`, `docs/build/runs/**`,
   `reports/obligations/events.jsonl` and the pre-seed `reports/round9-drafts/**`. Each hunk is attributed to the
   `##`/`###` heading in effect at its old line number in `<parent>:<path>`. Merge commits are diffed against their
   first parent, which is how `c2055d96` shows up a second time as `e2175c93`. The scan produced 2,171 hunks.
2. **Classify each removed line** (`analyze.py`, `reclass.py`). A changed line counts as one removal plus one
   addition. The classes are:
   - `blank`, `moved`, `whitespace`, `escaping`, `rewrap`;
   - `superset`: the old text is preserved inside the new text, i.e. an appended annotation;
   - `placeholder`: a `pending` / `TBD` / `PENDING-COMMIT-SHA` value filled in;
   - `typo`: at most 3 non-numeric, non-status words changed;
   - `status-transition`: for DEFERRALS rows matched by id, the leading status token of the status cell changed;
   - `altered` or `deleted`: content removed or rewritten.

   Table rows are compared by row id with a full-row word diff, so a pure insertion counts as `superset`.
3. **Classify each group** (`build_csv.py`). Every group that contained `altered`, `deleted` or
   `status-transition` lines was reviewed by hand against its word diff. The rules:
   - A run ledger edited by its own ticket before close is **benign**.
   - A contract edited before its ticket's first implementation commit is **benign**. So is a Gate-status block
     filled by the executing ticket (the manifest recipe sanctions it); those are recorded as
     transition-justified.
   - A DEFERRALS transition is **justified** if the new cell carries a dated note on or before the commit's UTC
     date, or an earlier valid dated note. An obligation event would also justify it, but none exists. Otherwise
     the transition is **unjustified**.
   - A same-ticket ADR edit before landing is **benign**.
   - Anything else that removes a decision, date, status, evidence or signature is **loss**. Losses are graded
     S1–S3 in the summary.
4. **Survival check for the 53 GATE DECISIONS rows.** The check looks for each row verbatim, then for
   40-character windows of the answer over every HEAD file under `docs/`, then does a manual semantic mapping
   (ticket Gate-status blocks, readouts, DEFERRALS cells, ADRs).

**Provenance.** sha256 prefixes of the scratch files: `scan.py` 5a5e17cadfb8115e, `analyze.py` cc8daa58d852bfad,
`reclass.py` ec22c188b85da462, `build_csv.py` d62158a66e7c5a44, `hunks.jsonl` aa8ef122628bed9d. The scripts are
deterministic over a fixed history. B4 can port `scan.py` + `reclass.py` as the backtest harness for the guard.

**Limitations.**
- Heading attribution uses the hunk's first line. A hunk that crosses a heading is attributed to the earlier
  section. None of the reviewed losses crosses one.
- `typo` and `superset` are heuristics. Every group containing a non-benign line was read by hand, but the
  benign-only groups (405) were sampled, not all read.
- History before 2026-09-09 lived in the gitignored `.agents/scratch/`. `LEDGER.md` first entered git at
  `4d5a5d27` (the v2 migration). Anything deleted before migration cannot be detected.

---

## 3. Benign rewrites — listed and justified

All 405 benign rows are in the CSV, each with its justification. By category:

| category | rows | why it is benign |
|---|---|---|
| DEFERRALS appended annotation | 129 | The old cell text is preserved inside the new cell; the leading status token is unchanged. |
| Run ledger edited by its own ticket before close | 68 | `runs/<ID>.md` is living until its ticket closes (PR/sha stamps, evidence fill, in-run corrections). |
| Path / formatting | 59 | Paths moved to `docs/build/reports/` by the v2 migration (a583df05, 4d5a5d27); the spec was homed into the repo (d8bcd3ab); table-pipe escaping (9bf11201). *a583df05 and d8bcd3ab touch executed contracts, so BM-TICKET-04's form is still owed (§5.3).* |
| PR-number / placeholder stamps | 56 | Closeout protocol: `PR pending` / `#TBD` / `<pending>` → `#NNN` in the ticket's own PHASE LOG entry and BUILD_INDEX row. |
| Round-9 drafts → seeded contracts | 39 | 34406ffc moved drafts from `reports/round9-drafts/` into `docs/tickets/` before execution. |
| Contract edited before execution | 28 | Amendments and renumbering before the ticket's first implementation commit: 901405c2 (P26.2), 4f8c748d (P27.6/P27.8), 83cd6668 (P30.3), 5f4772d8 (P33.7), 32bea406, b1250f62. |
| Generated `docs/adr/README.md` | 11 | Regenerated by `build-memory adr-index`, explicitly allowed. |
| ADR bodies | 3 | All same-ticket and before landing: ADR-033 7 min after `cacbfeba` (P07.1); ADR-117 4 min after `be7bab69`; ADR-131 2 min after `f73a997e`, where its future `Date: 2026-10-15` was corrected to 2026-09-27. **No ADR body was edited after landing, and no ADR Status line was rewritten.** |
| Redactions (D3) | 3 | b1250f62 replaced the literal GCP project id with `$SIG_GCP_PROJECT` in GL-GATE-04, D-ACCT.1-1 and the manifest, each with an in-place dated note ("decision unchanged"). |
| Other | 9 | 32bea406 added cross-references to 4 GL-GATE rows (additive); 28e46800 updated living chain-scope counts; b132bbbb changed the 170.5 → 170a label; c77bd45e reworded the BUILD_INDEX title; the `coverage_assessments.jsonl` a2 `PENDING-COMMIT-SHA` stamp; 8ec2bcfb corrected a future date on D-R10-SOURCES-1. |

**Transition-justified (88 rows).**
- **DEFERRALS (52).** Leading-token changes with a dated note in the cell. The primary-row totals are in §5.2.
- **Contracts (19).** Executing tickets copied gate answers into their Gate-status blocks: P20.2, P21.1, P21.4,
  P21.5, P21.8, P27.8, P27.10, P28.5, P29.1 and the P29.3 gate block. **Several of these cite GATE DECISIONS rows
  that `c2055d96` later deleted.** This group also includes the Round-2 tail contracts removed by cbe5fd48.
- **LEDGER (9).** RETURN PASS rows closed with strike-through, a DONE date and a matching PHASE LOG entry
  (e1cedcad, 773ae598, 5c9e76e6, 4c58f407, f6641b06); the PHASE LOG state updates 7671b511, 755dbd3f, 5c9e76e6
  and f6641b06.
- **BUILD_INDEX (6).** Rows 82, 91, 92, 113, 114 and 157 moved from pending to done with dated evidence. The
  change is justified in substance, but the row is "written at close, never reconstructed" (BM-INDEX-01), so a
  correction line is still proposed.
- **MANIFEST (2).** cbe5fd48 removed the Round-2 tail; it is recorded as Plan extension "2026-09-09 — REMOVE
  (P23.x tail)". 03450cb8 changed P25.1's row scope.

---

## 4. The known case — `c2055d96` (F-22), fully characterised

| fact | value |
|---|---|
| commit | `c2055d96`, 2026-09-18T20:14:45Z, author Steve Vitali, trailer `Co-Authored-By: Devin`; message "record GL-GATE-07 (257-dataset blanket approval) + GL-GATE-08 (robots non-gating)" |
| branch path | Off first-parent: `c2055d96` is on `devin/p26-15-eu-tenders`. It entered the chain through merge `e2175c93` (2026-09-19T00:03:05Z) into `devin/p26-16-rights-batch`, whose first-parent diff shows the same +20/−56. |
| parent (restore source) | `c2055d96^` = `eb9a23d0e…` (`git rev-parse c2055d96^` = `eb9a23d0bc6676c99caa86e4176b3016dc7cd480`) |
| removed | 56 lines at `eb9a23d0:docs/build/LEDGER.md` 111–166. That is the heading `## GATE DECISIONS (append-only; filled by the orchestrator from the operator's answers)`, the table header and separator (112–113), and **53 dated rows (114–166; 24,907 bytes; sha256 `baec891da75e0e082d37cc69639fdf6e4910133dde1ebd9f32c9e04eef182bd8`)**. |
| added | `## GATE DECISIONS` (the append-only annotation dropped) + a blank line + two bullets, GL-GATE-07 and GL-GATE-08 (18 lines). |
| row dates | 2026-09-08 ×15 · 09-09 ×21 · 09-10 ×4 · 09-13 ×1 · 09-15 ×8 · 09-16 ×4 |
| secrets check | 0 token shapes, 0 e-mail addresses, 0 literal project ids in the 53 rows. Credentials appear only as `provided: no` (×5). Row R35 is already in its post-b1250f62 redacted form. Safe to restore verbatim. |
| still in HEAD? | **0 of 53 verbatim.** 32 survive as paraphrase, 14 in part, 6 have no decision record, 1 is orphaned (table below). |
| orphaned citations | HEAD `GATE DECISIONS` (LEDGER 112–188) contains 0 mentions of GL-GATE-01…06. **GL-GATE-06** (R53) is still cited by `P26.2__source-expansion.md:12` ("GL-GATE-06 (LEDGER GATE DECISIONS, 2026-09-16)"), 58 `sources.toml` lines and 21 `reports/rights/*.md` packets. HEAD LEDGER mentions it only in 4 PHASE LOG lines (402, 406, 407, 409). The decision text is gone: the question, the answer and the scope limit ("covers only resolved-clear licences; UNRESOLVED / share-alike-ambiguous / `not_contacted` stay false"). |
| sole-record rows | The P21.3, P21.5 and P21.7 contracts state that gate answers "may arrive via the build ledger's `GATE DECISIONS` table instead of an edit to this file". R17/R18 (P21.3 HG-03/HG-09), R24/R25 (P21.5 HG-07/HG-12) and R27/R28 (P21.7 HG-08/HG-10) were therefore the only decision record. |
| dependent transitions | R51/R52 (09-16 go-public, "HG-11 RESOLVED-BY-OPERATOR — SIG-PUB-008 independence waived, not satisfied", HG-04/HG-10/DNS skips) justified the `b542f236` DEFERRALS WONTFIX/DONE transitions. Those states now rest on the agent's paraphrase in the cells (NEW-8). The GATE-G2 readout still carries only 2026-09-10 (see E1 NEW-11). |

### The 53 deleted rows (from `eb9a23d0:docs/build/LEDGER.md` 114–166; items truncated, full text in the source)

Survival key: **paraphrase**: the decision's substance is recorded elsewhere, but not the verbatim answer. **partial**: only part of it survives. **none**: no decision record at all. **orphaned**: the id is cited but its record is gone.

| # | date | ticket | gate | item (truncated) | survives in HEAD? |
|---|---|---|---|---|---|
| R01 | 2026-09-08 | P19.5 (post-ticket) | HG-14 | ACCEPTED-deviations §(b) Family 1 — 75 charter/process/epi | partial — the 76-row list survives in `CAPSTONE_CLOSURE.md` §(b) (headed 'PROPOSED for signature'); the signing act does not |
| R02 | 2026-09-08 | P19.5 (post-ticket) | HG-14 | ACCEPTED-deviations §(b) Family 2 — SIG-UI-038 zero-JS sta | partial — the 76-row list survives in `CAPSTONE_CLOSURE.md` §(b) (headed 'PROPOSED for signature'); the signing act does not |
| R03 | 2026-09-08 | P19.5 (post-ticket) | HG-14 | Net result: full 76-row ACCEPTED list signed | partial — `CAPSTONE_CLOSURE.md` addendum refers to 'the signed §(b) table'; no signature record |
| R04 | 2026-09-08 | P20.1 (deliverable 0) | HG-14 | Recorded the signed ACCEPTED list into CAPSTONE_CLOSURE.md | paraphrase — `CAPSTONE_CLOSURE.md`, `pr/P20.1_body.md` |
| R05 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A1 — §40/ADR-018 zero-JS static map as conforming default, | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R06 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A2 — §32.2 add not_researched to the absence vocabulary (A | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R07 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A3 — §11.2 canonical_name scalar (ADR-056, LD-D12) | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R08 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A4 — §16.2 item 6 "MAY partition; MUST keep the PK/FK cont | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R09 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A5 — §30/§32/§33 accept compute-on-read as conforming (ADR | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R10 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A6 — §34 accept CLI+JSONL as Phase-5 conforming curation f | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R11 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A7 — §47 layout add evidence/ as a member package (ADR-023 | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R12 | 2026-09-08 | P20.2 (pre-ticket) | HG-13 | A8 — any further normative items P19.2/P19.5 routed P20.2: | paraphrase — `P20.2` contract ticks '[x] A1…A8 TICKED — APPLIED' citing GATE DECISIONS |
| R13 | 2026-09-08 | P21.1 (pre-ticket) | HG-03 | Which sources to flip to ingestion_permitted=true now | paraphrase — `P21.1` Gate-status block ('SKIP … build ledger GATE DECISIONS') |
| R14 | 2026-09-08 | P21.1 (pre-ticket) | HG-04 | Stage-0 outreach outcomes to record now | paraphrase — `P21.1` Gate-status block ('SKIP … build ledger GATE DECISIONS') |
| R15 | 2026-09-08 | (orchestrator) | CI-RED-01 | Fix the CI python-job red (test_s8 needs web/node_modules) | paraphrase — LEDGER OPEN FINDINGS CI-RED-01 + LEGACY PLAN row 54.5 |
| R16 | 2026-09-09 | (orchestrator) | P22 scope | Are P22.1/P22.2 part of this run? | paraphrase — LEDGER PHASE LOG 2026-09-09 'OPERATOR RECONCILIATION' |
| R17 | 2026-09-09 | P21.3 (pre-ticket) | HG-03 | Any sources flipped to green review-status to fetch LIVE n | none as a decision record — `P21.3` contract says answers 'arrive via GATE DECISIONS instead of an edit to this file'; `runs/P21.3.md` echoes `provided: no` |
| R18 | 2026-09-09 | P21.3 (pre-ticket) | HG-09 | Live API tokens/keys provided (SIG_MUCKROCK_TOKEN/SIG_DATA | none as a decision record — `P21.3` contract says answers 'arrive via GATE DECISIONS instead of an edit to this file'; `runs/P21.3.md` echoes `provided: no` |
| R19 | 2026-09-09 | P21.4 (pre-ticket) | HG-12 | Hosting/staging target | paraphrase — `P21.4` Gate-status block (filled at 6a0c1888 from GATE DECISIONS); R22 text ~83% in `PUBLICATION_CHECKLIST.md` |
| R20 | 2026-09-09 | P21.4 (pre-ticket) | HG-01 | Legal home named? | paraphrase — `P21.4` Gate-status block (filled at 6a0c1888 from GATE DECISIONS); R22 text ~83% in `PUBLICATION_CHECKLIST.md` |
| R21 | 2026-09-09 | P21.4 (pre-ticket) | HG-11 | Two reviewer roles + concurrence + takedown contact live? | paraphrase — `P21.4` Gate-status block (filled at 6a0c1888 from GATE DECISIONS); R22 text ~83% in `PUBLICATION_CHECKLIST.md` |
| R22 | 2026-09-09 | P21.4 (pre-ticket) | HG-02 | ODbL 4.4(b) disposition for OSM-derived layer | paraphrase — `P21.4` Gate-status block (filled at 6a0c1888 from GATE DECISIONS); R22 text ~83% in `PUBLICATION_CHECKLIST.md` |
| R23 | 2026-09-09 | P21.4 (pre-ticket) | Go-public | DNS/host cut-over now? | paraphrase — `P21.4` Gate-status block (filled at 6a0c1888 from GATE DECISIONS); R22 text ~83% in `PUBLICATION_CHECKLIST.md` |
| R24 | 2026-09-09 | P21.5 (pre-ticket) | HG-07 | Zenodo/object-store credentials provided? | none — `P21.5` contract defers answers to GATE DECISIONS |
| R25 | 2026-09-09 | P21.5 (pre-ticket) | HG-12 | Paid infra budget or zero-cost? | none — `P21.5` contract defers answers to GATE DECISIONS |
| R26 | 2026-09-09 | P21.5 (pre-ticket) | A1 state | MapLibre island or zero-JS static map? | paraphrase — `P21.5` contract '[x] A1 ticked' |
| R27 | 2026-09-09 | P21.7 (pre-ticket) | HG-08 | MapRoulette API key + OSM Organised-Editing page URL provi | none as a decision record — `P21.7` contract defers to GATE DECISIONS; later status only in DEFERRALS D-P21.7-1/2 |
| R28 | 2026-09-09 | P21.7 (pre-ticket) | HG-10 | ≥5 naïve usability-study participants scheduled? | none as a decision record — `P21.7` contract defers to GATE DECISIONS; later status only in DEFERRALS D-P21.7-1/2 |
| R29 | 2026-09-09 | P21.8 (pre-ticket) | HG-03/HG-04 (per new source) | Flip eff_data_driven / MuckRock / aspi / carnegie / facial | paraphrase — `P21.8` Gate-status block (d2ec5364) |
| R30 | 2026-09-09 | P21.9 (pre-ticket) | HG-03/HG-04 (per Stage-5 source) | Flip any RTCC/federation, FR/CSS/forensics, acoustic/drone | paraphrase — `P21.9` 'OPERATOR ANSWER … SKIP' |
| R31 | 2026-09-09 | P22.2 (pre-ticket) | clean-slate option | Clean-slate bootstrap or default deep refresh of AGENTS.md | partial — `runs/P22.2.md` |
| R32 | 2026-09-09 | (decompose-spec extend / spec §0.1 | GL-GATE-01 (HG-01 legal home) | Legal home for public cutover | partial — pre-answers originate in `docs/3_sig_golive_spec.md` §0.1 (55–71% of text); the recorded disposition row is gone |
| R33 | 2026-09-09 | (decompose-spec extend / spec §0.1 | GL-GATE-02 (HG-02 counsel) | Publish the SIG graph / OSM compartment / OKC dossiers? | partial — pre-answers originate in `docs/3_sig_golive_spec.md` §0.1 (55–71% of text); the recorded disposition row is gone |
| R34 | 2026-09-09 | (decompose-spec extend / spec §0.1 | GL-GATE-03 (HG-03/04 flips) | Which sources to flip, in what order? | partial — pre-answers originate in `docs/3_sig_golive_spec.md` §0.1 (55–71% of text); the recorded disposition row is gone |
| R35 | 2026-09-09 | (decompose-spec extend / spec §0.1 | GL-GATE-04 (HG-12 host) | Hosting target | partial — pre-answers originate in `docs/3_sig_golive_spec.md` §0.1 (55–71% of text); the recorded disposition row is gone |
| R36 | 2026-09-09 | (decompose-spec extend / spec §0.1 | GL-GATE-05 (Go-public) | DNS/public cutover + v0.2.0 | partial — pre-answers originate in `docs/3_sig_golive_spec.md` §0.1 (55–71% of text); the recorded disposition row is gone |
| R37 | 2026-09-10 | P23.1 (marker GATE-G1 / REL.1) | HG-05 (integrate & release v0.1.0) | Merge #47–#68 bottom-up, make check on main, tag v0.1.0, m | paraphrase — `readouts/GATE-G1.md` (2026-09-10) |
| R38 | 2026-09-10 | P23.2 (marker HUMAN-H1 / GOV.1) | HG-01, HG-11 | Legal home named? governance roles + concurrence + takedow | paraphrase — `readouts/HUMAN-H1.md` |
| R39 | 2026-09-10 | P23.3 (marker HUMAN-H2 / LEGAL.1) | HG-02 (counsel) | Publish the SIG graph / OSM compartment / OKC dossiers? | paraphrase — `readouts/HUMAN-H2.md` |
| R40 | 2026-09-10 | P23.4 (marker HUMAN-H3 / ACCT.1) | HG-07, HG-08, HG-09, HG-12 | Accounts/tokens/host provided? | paraphrase — `readouts/HUMAN-H3.md` |
| R41 | 2026-09-13 | P24.9 (marker GATE-ACCEPT) | HG-14 (re-sign of the ACCEPTED lis | Sign the Round 3–4 go-live accepted-deviations delta (CAPS | paraphrase — `readouts/GATE-ACCEPT.md` (2026-09-13, PASSED) |
| R42 | 2026-09-15 | (post-chain operator action) | HG-01 (legal home) | Name the legal home | paraphrase — DEFERRALS D-P21.4-1 'DONE 2026-09-15', `readouts/HUMAN-H1.md` |
| R43 | 2026-09-15 | (post-chain operator action) | HG-11 (governance roles + concurre | Establish two named independent reviewer roles + written c | partial — `readouts/HUMAN-H1.md`; D-P21.4-2 cell (its 09-15 annotation later erased by b542f236) |
| R44 | 2026-09-15 | (post-chain operator action) | HG-02 (counsel) | Engage counsel for the four opinions (ODbL 4.4(b)/RISK-P0- | partial — DEFERRALS D-LEGAL.1-1 cell |
| R45 | 2026-09-15 | (operator determination) | crawler conduct (SIG-INGEST-037) | Treat documented API access as distinct from crawling? | paraphrase — ADR-083 (crawler-conduct carve-out) |
| R46 | 2026-09-15 | (post-chain operator action) | HG-11 (governance) | Name reviewer roles + takedown contact now? | partial — `readouts/HUMAN-H1.md`; D-P21.4-2 cell (its 09-15 annotation later erased by b542f236) |
| R47 | 2026-09-15 | (operator determination) | HG-07/HG-09 credentials | Which credentials are available now? | partial — DEFERRALS D-ACCT.1-1 cell (`provided:` flags) |
| R48 | 2026-09-15 | (operator determination, unblock p | HG-03 (rights flips) | Approve the gated cohort: France per-source, CCOPS×3, path | paraphrase — ADR-085 + `reports/rights/PROPOSED_DISPOSITIONS.md` |
| R49 | 2026-09-15 | (counsel, HG-02) | HG-02 counsel — the five held sour | May madada, declarationcamera_be, aspi_mapping_chinas_tech | partial — ADR-086 / ADR-079 mention the held sources; counsel answer row gone |
| R50 | 2026-09-16 | (counsel, HG-02) | HG-02 counsel — derived-facts publ | May the derived-facts/citations claims from the eleven Lic | paraphrase — ADR-086 |
| R51 | 2026-09-16 | (operator, GL-GATE-05 / GATE-G2) | Go-public + the remaining human ga | Proceed to public launch now, and how are the remaining ga | paraphrase only in DEFERRALS cells (D-P21.4-3 'DONE 2026-09-16'); `readouts/GATE-G2.md` carries only 2026-09-10 |
| R52 | 2026-09-16 | (operator dispositions, post-go-pu | Remaining human-gate clean-up | Resolve HG-11, HG-02 remainder, outreach, HG-10, DNS, SWH/ | paraphrase only in DEFERRALS WONTFIX/DONE cells written by b542f236 (HG-11 waiver 'waived, not satisfied', HG-04/HG-10 skips, DNS skip) |
| R53 | 2026-09-16 | (operator, source-expansion direct | HG-03 blanket disposition | May sources whose rights packet resolves to a clear public | orphaned — cited as 'GL-GATE-06 (LEDGER GATE DECISIONS, 2026-09-16)' by the P26.2 contract, 58 `sources.toml` lines, 21 rights packets; the record itself is gone |

### 4.1 Restoration of the 53 rows (Stage B; needs an explicit operator go, because it touches the control ledger)

1. **Source bytes.** `git show eb9a23d0:docs/build/LEDGER.md | sed -n '112,166p'` is the header, the separator
   and the 53 rows. Check that `sed -n '114,166p'` hashes to `baec891d…82bd8`.
2. **Placement.** Append at the **end** of the current `## GATE DECISIONS` section, after the P27.2 Part VIII
   bullet (HEAD line 188) and before `## CROSS-CUTTING INVARIANTS`. Do not re-insert at the top, do not reorder
   the bullets that came later, and do not rename the live heading. The original heading annotation is quoted
   inside the caption instead.
3. **Block format:**
   ```
   - <date -u> **RESTORED from `c2055d96^` (`eb9a23d0`) — B2 next-phase planning, operator go <ref>.** The 53 rows
     below were deleted by `c2055d96` (2026-09-18T20:14:45Z) and carried into the chain by merge `e2175c93`. They
     are restored verbatim, in original order, from the table then headed "## GATE DECISIONS (append-only; filled
     by the orchestrator from the operator's answers)". Nothing below is re-decided; rows sha256 baec891d…82bd8.

   | Date | Ticket | Gate | Item | Answer (tick / value / skip) | Notes |
   |---|---|---|---|---|---|
   <53 rows, byte-for-byte>
   ```
4. **Verification.**
   - Every one of the 53 source lines occurs exactly once in the new LEDGER.
   - The contiguous 53-line slice hashes to `baec891d…`.
   - `git diff <pre>..<post> -- docs/build/LEDGER.md` has **0 removed lines**.
   - `check-build-memory` stays green.
   - A regression test pins the containment: "every row of `eb9a23d0` GATE DECISIONS is in HEAD".
5. **Follow-ups.**
   - B3 decides whether the section keeps the table form or the bullet form for new entries. Either way the
     restored table stays as-is.
   - The GL-GATE-06 citations in `sources.toml` and the rights packets then resolve again. No change is needed
     to those files.

---

## 5. Other losses and transitions

### 5.1 `obligations/events.jsonl` — three wholesale rewrites (F-26, NEW-2)

Field-level diff by `event_id` across the four versions:

| commit (UTC) | events | ids removed | fields rewritten on existing events | what was lost |
|---|---|---|---|---|
| `6bade66e` 2026-09-27T08:37Z (P32.7, created) | 89 | — | — | — (recorded_at 2026-10-14 on every event: a future date) |
| `b132bbbb` 10:50Z (P32.10a) | 90 | 0 | source_commit 89 · recorded_at 89 (→ 2026-09-27) · observed_at 82 · anchor row_sha256 5 | the original anchors and dates (the wrong date was corrected, but in place) |
| `30d401dc` 11:20Z (P32.11) | 90 | 0 | source_commit 90 · anchor 1 | the per-event source commits |
| `7a2ff9fa` 2026-09-28T05:13Z (P33.1) | 97 | 0 | source_commit 90 · recorded_at 90 (→ **2026-10-21**) · observed_at 80 · **from_status/to_status/owner/landing/reason/evidence_refs 8** · anchor 14 | **8 e0 anchors mutated OPEN/PARTIAL → DONE** (D-P30.1-2, D-P30.2a-1, D-P30.2a-2, D-P30.3-1, D-P30.3-2, D-P30.3-3, D-P31.1-2, D-P31.3-1) with `interpretation` preserved → reconciled. No e1 was appended. |

Every version holds `seq = 0` only, and no event has `from_status ≠ to_status`. The log has never recorded a
transition. **Restoration:** freeze the file as append-only and never regenerate it. Then append `kind:
"correction"` records that name each rewritten line's prior sha256 and source commit. For the 8 mutated events,
append real `transition` e1 events: from the pre-rewrite status (taken from `30d401dc`) to DONE, with
`observed_at` = the git date of the landing the cell cites, `recorded_at` = `date -u` at repair, and
`expected_previous_event` = e0. The tool change (append, never regenerate) is owed to B3. The date anchoring is
B1 NEW-7.

### 5.2 DEFERRALS

- **Status transitions.** 74 primary-row leading-token rewrites: 50 OPEN→DONE, 13 OPEN→PARTIAL, 9 PARTIAL→DONE
  and 4 OPEN→WONTFIX. **None is backed by an obligation event.**
  - 58 carry a dated note on or before the commit's UTC date: *justified*.
  - 11 (`6bade66e` ×3, `7a2ff9fa` ×8) carry a reconciliation stamp dated 2026-10-14 or 2026-10-21, but the same
    cell holds an earlier valid dated DONE: *justified, misdated stamp*.
  - **5 are unjustified**: D-P30.2b-3 "DONE 2026-10-02" at `4e0dd070` (2026-09-25); D-P27.5-1 "DONE 2026-10-03"
    at `be7bab69` (2026-09-26); and D-P31.1-1, D-P31.1-3 and D-P31.5-2 "DONE 2026-10-14" at `6bade66e`
    (2026-09-27), whose cited "dated DONE 2026-10-11 / 09-28 / 10-12" is itself after the commit (NEW-3).

  Restoration: never edit the cell. Append a dated correction line with the landing commit's git date and an e1
  transition event.
- **Erased cell history.** `b542f236` (2026-09-16T19:49Z) replaced whole status cells on 6 rows when it recorded
  the 09-16 operator dispositions: D-P21.1-2, D-P21.4-2, D-P21.7-2 (368 chars incl. "re-confirmed 2026-09-10 …
  DEFERRED past go-public 2026-09-16 … P25.9 sweep"), D-LEGAL.1-1, D-JURIS.2-2 and D-CCOPS.1-2 (NEW-8).
- **Snapshot falsified.** The table "### P30.4 sweep — every OPEN / PARTIAL row … (2026-09-24)" was edited on
  09-25 and 09-26: D-P30.2b-3 and D-P27.5-1 flipped to DONE, D-P30.2b-1's item text was rewritten, and D-P30.3-2
  was annotated. The "11,625 proposals" figure survives only in `LAUNCH_RECORD_2026-09-24.md` (NEW-4).
- **Proxy / owed cells rewritten** (S3): c180c748, c37daa71 and 761bbb30 (the 09-13 re-runs), and dc8688ba.
  Interim D-SOURCES.12-1 wave counts were overwritten by f52bc7ac, 99a7794b, cba41b2b and 99517730.

Restoration for the last three bullets: append a `## Restored cell history (append-only; B2)` table
(`id | removed text verbatim from <sha>^ | removed by | date`). For the snapshot, append a "restored as-of
rows" block directly under it.

### 5.3 Executed ticket contracts (BM-TICKET-04; NEW-5)

`grep -l '^> Amended' docs/tickets/*.md` returns 0 files, so no amendment has ever used the required form. The
losses:
- **P25.4 / P25.5, `b87c279c` (2026-09-16T00:14Z).** Both tickets had already executed: P25.5's first
  implementation commit was 7c9ab116 at 23:05Z, and P25.4's BUILD_INDEX row 91 says it landed 2026-09-15. The
  commit replaced the Gate status and Live stage, struck and rewrote deliverables, and changed P25.5's AC
  "fetched live … with typed/evidenced claims" to "[x] … provenance rows (document capture) OR gate recorded".
  The stronger clause was re-added as a new unticked AC. This is the "MET on reduced scope" shape of F-16.
- **P29.3, `b4bd0068` (its own implementation commit).** The AC "`ingestion_permitted=false` until HG-03"
  became "flipped under GL-GATE-07", and the ACs were ticked `[x]`/`[~]` with results written inside the
  contract.

Transition-justified, but in the wrong form:
- **P25.1, `03450cb8`.** Deliverable 1 was rewritten mid-execution to "implement the adopted ADR-083". The
  justification is the 09-15 crawler-conduct determination, which is itself one of the rows c2055d96 deleted.
- **Gate-status fills.** The 9 fills listed in §3.

Benign, but they still owe a note: the path edits a583df05 (7 P21.x contracts) and d8bcd3ab (P22.3).

**Restoration:** append a `> Amended <date -u>: restored from <sha>^` block that quotes the replaced lines, plus
a matching `## Plan extensions` line. The current text stays as the amended state.

### 5.4 Readouts (F-29 + NEW-6)

- **ACCEPT-R8, `0a715fcc` (2026-09-24).** The signing commit deleted the pending text, including "(pending; the
  signature is the operator's, and no agent signs it)".
- **GATE-G3, `95c8a73f` (2026-09-28T03:49Z).** The signing commit deleted "Status: PENDING", "an agent must not
  sign or assume silence is approval" and the unmet-criteria lines. It ticked boxes citing "operator decision
  2026-10-19", which is after the commit date.
- **ACCEPT-R10, `4127dbf3`.** The same deletion of the pending text and guard line.
- **GATE-G1, `3259ca81`.** The criterion "records the outcome here as PASSED" was reworded to "cleared" with no
  note.

In each signing case the signature itself traces to a recorded operator statement. What was lost is the readout's
own pre-signature record and its guard criterion. **Restoration:** append a `## Readout history (restored from
<sha>^)` section with the removed lines verbatim. For GATE-G3, also append a dated correction noting that
2026-10-19 is not a git or tool date.

### 5.5 Progress written over closed records (NEW-7)

- **P26.16 on 2026-09-19.** The PHASE LOG entry, BUILD_INDEX row 113 and D-SOURCES.12-1 were rewritten by
  `7671b511` → `f52bc7ac` → `99a7794b` → `cba41b2b` → `99517730`, after the ticket had closed at `376f65ae`
  (06:33Z). The interim readings "@12Z 644,487", "@13:30Z 782,583" and "@15:30Z 993,503" are in no HEAD file.
  `7671b511` also deleted the closed run ledger's section "### Hosted execution — NOT run (infrastructure,
  recorded not claimed)", which held the verbatim ADC error. `git grep 'not a valid json file' docs` finds 0
  files. That text names the operator's account address; redact it on restore, following the D3 redaction
  precedent.
- **P26.17, `755dbd3f`.** "in flight at write time / owed" was replaced by the final evidence (justified, but
  done in place).
- **P31.16, `3fd71041`.** The pre-gate paragraph "Stop line: … Nothing public was touched … HG-11 was not
  ticked" was deleted after the HG-11 grant.
- **Restoration:** one PHASE LOG correction entry per ticket, quoting each superseded clause in commit order. For
  the run ledgers, a `## Superseded record (restored from <sha>^)` section.

### 5.6 Manifest (NEW-9)

- **Spec amendments applied:** 0 removals ever.
- **Plan extensions:** two in-place edits. `d8bcd3ab` changed the seed-spec path, rewriting the historical fact
  that `~/MetaHarness/sig-golive-spec.md` was used. `b132bbbb` changed "row 170.5 … fractional stable index" to
  "sequence cell 170a", 23 min after `42bb286a` wrote the line.
- **Round-2 tail.** `cbe5fd48` removed it (rows 67–73 and 7 never-executed contracts). The removal is recorded as
  "REMOVE (P23.x tail)", but ids **P23.1–P23.7 were reused** the same day by the `32bea406` RENUMBER.
- **Restoration:** append correction lines quoting the original Plan-extension wording, plus one id-disambiguation
  line: "P23.1–P23.7 before 32bea406 = CAP.1…REC.3; after = GATE-G1…GATE-G2 markers".

### 5.7 Not found

- No ADR body was edited after landing.
- No Appendix G (`99c_*`) line was ever removed.
- No RETURN PASS row disappeared without a strike-through and a dated DONE, except the table-level staleness that
  B3 already owns (F-25).
- No OPEN FINDINGS entry was deleted. All 6 edits appended a RESOLVED note.

---

## 6. Restoration design — procedure (all classes)

**Principle (P7).** Restore by appending, never by re-inserting. Every restored block:
- is dated with `date -u` at restore time;
- names its source as `RESTORED from <sha>^`, together with the removing commit and its UTC date;
- quotes the removed text **verbatim**, with only one exception: the operator e-mail in the P26.16 run ledger is
  redacted with a dated note;
- carries the sha256 of the restored bytes;
- states "nothing below is re-decided".

Current text stays as the latest state.

**Owner and gate.** Stage B / a T-row ticket, run under an explicit operator go, because it edits `LEDGER.md` and
`DEFERRALS.md` (P10). One commit per artifact family, each citing this row and the CSV rows it closes. Order:

| step | artifact | CSV rows closed | mechanism |
|---|---|---|---|
| 1 | LEDGER GATE DECISIONS | c2055d96, e2175c93 | §4.1 block |
| 2 | DEFERRALS | b542f236 ×4, 4e0dd070/be7bab69 snapshot, c180c748, c37daa71, 761bbb30, dc8688ba, f52bc7ac/99a7794b/cba41b2b/99517730, 4 unjustified transitions + 11 misdated stamps | `## Restored cell history (append-only; B2)` table + snapshot "restored as-of rows" + dated correction lines |
| 3 | events.jsonl | b132bbbb, 30d401dc, 7a2ff9fa | append correction + e1 transition records through the (B3-fixed) tool |
| 4 | LEDGER PHASE LOG + BUILD_INDEX | P26.16 ×4 (+ 7671b511, 755dbd3f, f6641b06 notes) | one PHASE LOG correction entry per ticket; a `## Row corrections (append-only)` section at the end of BUILD_INDEX |
| 5 | readouts | 0a715fcc, 95c8a73f, 4127dbf3, 3259ca81 | `## Readout history (restored from <sha>^)` |
| 6 | contracts + manifest | b87c279c ×5, b4bd0068, 03450cb8, a583df05, d8bcd3ab, b132bbbb, cbe5fd48 | `> Amended` blocks + Plan-extension correction and id-disambiguation lines |
| 7 | run ledgers | 7671b511 P26.16, 3fd71041 P31.16 | `## Superseded record` sections |

**Verification of the whole restore:**
- `git diff <pre-restore>..<post-restore>` over the protected paths shows **0 removed lines**.
- Every restored block's hash matches `git show <sha>^:<path> | sed -n <range>p | sha256sum`.
- `check-append-only` (§7), run with `--base <pre-restore>`, passes.
- The CSV rows marked `loss` and `transition-unjustified` each resolve to a restored block.

---

## 7. Proposed guard — `check-append-only` (feeds B4)

A history-aware check to add alongside the structural validators. `check-build-memory` exits 0 on today's tree
(F-27) because it checks shape, not history.

- **Where it runs.** CI `docs` job on every PR (`git diff <base>...<head>`; in the stacked chain the base is the
  previous branch). It also runs on push, including merge commits diffed against their first parent: c2055d96
  entered through a merge, and PR #108's diff would have shown the deletion. It is also a local pre-commit hook.
  A read-only history mode (`--since <sha>`) doubles as the backtest.
- **Policy file.** `docs/build/APPEND_ONLY.toml` (committed; path + optional heading glob + mode):
  - `append-only`: removed lines must be 0, apart from whitespace/escaping-equivalent pairs and verbatim moves
    within the region. Applies to LEDGER `## GATE DECISIONS`, `## PHASE LOG*` and `## OPEN FINDINGS*`; manifest
    `## Plan extensions*` and `## Spec amendments applied`; `spec_src/99c_*`; readouts, except placeholder lines;
    and the ADR set.
  - `placeholder-fill`: a removal is allowed only if the old line differs from the new one by declared
    placeholder tokens (`PR pending`, `#TBD`, `<pending>`, `pending push`, `PENDING-COMMIT-SHA`, `(pending)`,
    `______`) in declared columns or lines. Applies to PHASE LOG PR fields, BUILD_INDEX PR/branch cells and
    readout `Disposition:` / `Signed by:` lines.
  - `row-annotate` (DEFERRALS, OPEN FINDINGS, RETURN PASS): for each id-matched row, the old row's text must be
    contained in the new row, with strike-through allowed. A change of the leading status token needs (a) an
    appended `obligation-event/1` transition for that id in the same diff, with `expected_previous_event`
    matching, and (b) a date in the new lead that is ≤ the commit's UTC date.
  - `frozen-snapshot`: any heading that carries a `(YYYY-MM-DD)` date and one of the words "sweep", "snapshot"
    or "as of". No removals and no additions after the commit that created it.
  - `frozen-after-execution` (`docs/tickets/*__*.md`): execution starts at the first commit whose subject starts
    with the ticket id, or when `runs/<ID>.md` or a BUILD_INDEX row exists at base. After that, only appended
    blocks that start `> Amended YYYY-MM-DD:` are allowed, plus a Gate-status fill in the executing ticket's first
    commit.
  - `frozen-after-close` (`runs/<ID>.md`, BUILD_INDEX rows): after the ticket's closeout commit, only
    `placeholder-fill` and appended `## Correction` sections are allowed.
  - `frozen-after-landing` (`docs/adr/ADR-*.md`): after the ticket's closeout, only a Status line change to
    `Superseded by ADR-NNN` is allowed, and ADR-NNN must exist.
  - `prefix` (`reports/obligations/*.jsonl`): the head bytes must begin with the base bytes. New lines must be
    valid schema, carry `recorded_at ≤ commit UTC`, and chain to the obligation's last event.
- **Global rule.** No added date token may be later than the commit's UTC date, unless the line carries an
  explicit `scheduled:` / `cron` marker. This covers the B1/F-21 class. B1 owns the legitimately-future
  allow-list.
- **Waivers.** None in code. A deliberate restructure is a new section plus an appended pointer, so the guard
  never needs bypassing.
- **Backtest oracle.** Run over this history, the guard must flag exactly the 42 `loss` rows and 4
  `transition-unjustified` rows in `data/append_only_violations.csv`, and each misdated stamp. It must pass the
  405 benign rows. The in-place-but-justified rows (e.g. RETURN PASS strike-through, same-ticket ADR edits,
  pre-execution contracts) must also pass.

| class found here | example | guard rule that fails it |
|---|---|---|
| Whole-section deletion in GATE DECISIONS | c2055d96 / e2175c93 | `append-only` + first-parent merge check |
| Wholesale JSONL regeneration and in-place status mutation | b132bbbb, 30d401dc, 7a2ff9fa | `prefix` |
| DEFERRALS history erased, proxy cells rewritten | b542f236, c180c748 | `row-annotate` containment |
| Status transition without an event or valid date | 4e0dd070, 6bade66e | `row-annotate` (a)+(b); global date rule |
| Dated snapshot edited later | 4e0dd070, be7bab69 | `frozen-snapshot` |
| Executed contract rewritten | b87c279c, b4bd0068, a583df05 | `frozen-after-execution` |
| Readout pending text / guard line overwritten | 0a715fcc, 95c8a73f, 4127dbf3 | `append-only` + `placeholder-fill` (only `Disposition:` lines are fillable) |
| Closed PHASE LOG / BUILD_INDEX / run ledger rewritten | P26.16 series, 3fd71041 | `append-only`, `frozen-after-close` |
| Plan-extension line edited in place | d8bcd3ab, b132bbbb | `append-only` |
| Future-dated notes, stamps and decisions | 6bade66e, 7a2ff9fa, 95c8a73f | global date rule |

B4 should add one requirement for this guard, e.g. **SIG-MEM-00x** "protected build-memory regions change only by
appending; CI proves it per PR". Each mode needs a fixture test: one passing diff and one failing diff drawn from
the commits above.

---

## 8. New findings (`findings/incoming/B2.csv`)

| id | title (short) | sev | relation |
|---|---|---|---|
| NEW-1 | c2055d96 rows were sole or authoritative records; GL-GATE-06 orphaned (58 `sources.toml` lines, 21 packets); 0/53 verbatim survivors | S1 | refines F-22 |
| NEW-2 | P33.1 mutated 8 e0 events' status in place; every regeneration rewrote source_commit | S2 | refines F-26 |
| NEW-3 | 5 DEFERRALS transitions unjustified (no valid date, no event); 11 misdated stamps; 0/74 event-backed | S2 | overlaps F-21 / B1 |
| NEW-4 | Dated snapshot "P30.4 sweep (2026-09-24)" edited after its date | S2 | new |
| NEW-5 | Executed contracts rewritten in place; 0 `> Amended` notes repo-wide; P25.5 AC weakened+ticked; P29.3 ACs rewritten | S2 | new (F-16 shape) |
| NEW-6 | ACCEPT-R8 signing also deleted the "no agent signs" guard text; GATE-G1 criterion reworded | S3 | extends F-29 |
| NEW-7 | P26.16 records overwritten 5× on 09-19; closed run ledger lost its failure record; P31.16 stop-line lost | S3 | new |
| NEW-8 | b542f236 erased 6 cells' dated history; its justifying gate row was then deleted by c2055d96 | S2 | links F-22 |
| NEW-9 | Plan-extension lines edited in place ×2; ticket ids P23.1–P23.7 reused | S3 | new |

---

## 9. Open questions for the orchestrator / later rows

1. **B3.** Should GATE DECISIONS return to one form? The design keeps the restored table verbatim either way.
2. **B1 / B3.** Who owns the true dates for the 5 unjustified transitions and the GATE-G3 "2026-10-19" decision?
   This design only says they must come from git and the operator, never from inference.
3. **Operator (Track 0 / Stage B).** Is a restore commit to `LEDGER.md` / `DEFERRALS.md` acceptable before the
   B3 ledger redesign lands? Recommended: restore first, so B3 migrates a complete record.
