# ADR-146: Correcting recorded dates that were not taken from a clock

- **Status:** Accepted
- **Date:** 2026-10-01T04:59:05Z (decided by the operator at GATE-P — the latest of this ADR's lines, C-10, log round 21)
- **Phase:** Round 11 / Stage B seed (T1)
- **Ticket:** SEED-11 (unit SEED-11a)
- **Decided by:** the operator at GATE-P (`PD/feedback/RATIFICATION_LOG.md`; `PD` = `docs/build/planning/2026-09-30-next-phase/`):
  - **A-13**, round 5 (2026-10-01T04:09:43Z): **"Full seed (Recommended)"** — answers Q-14 (a: restore-first, correction
    ADR, guard core, PKG-02 pins) and Q-B4-1 (yes: the seed carries the guard core).
  - **B-4**, round 10 (2026-10-01T04:32:16Z): **"As stated (Recommended)"** — answers Q-12 (a: supersede `p-17b713`, no
    re-sign), Q-E2-19 (yes), Q-E2-20 (yes: correct every future-dated normative statement by appended amendment using
    commit dates), Q-B1-2 (confirm the true times) and Q-E2-18 (b: annotations; recorded in ADR-147).
  - **C-1**, round 19 (2026-10-01T04:54:19Z): **"Confirm (Recommended)"** — OD-10: the readout provenance is recorded as fact.
  - **C-10**, round 21 (2026-10-01T04:59:05Z): **"Let me inspect it (Recommended)"** — Q-B1-4; the operator-approved,
    local, read-only inspection reported its result at 2026-10-01T04:59:41Z.
- **Requirement ids:** SIG-ENG-003 (a change is appended, never an edit); SIG-TRUST-008 (calendar-dependent checks are not
  marked complete before they run); **SIG-MEM-005** "recorded dates come from the clock and are never later than their
  commit" (§56.2; drafted in B4 §5; final id per `PD/stageB/T1_id_map.csv`), and **SIG-ENG-045** (§56.3; deployed sqitch lines never
  re-stamped; L44–52 keep their stamped dates, C-10); the
  plan §6.3 row "§55 landed-status text; Appendix G" (true Round-10 dates through one new Appendix G.7 row; sqitch
  L44–52 never re-stamped).
- **Spec:** §55 (`96b_partXI_s55_six_streams.md` landed-status text, corrected to true dates); Appendix G (one new G.7
  row; R10-A6 untouched); Part XII §56.2 (SIG-MEM-005) and §56.3 (SIG-ENG-045).
- **Supersedes:** none — no landed ADR decision (plan §7, row 146). It replaces clause 2 of B1 §8's planning draft
  ("ADRs get an appended correction footer"; plan Appendix B row 1), which was never an ADR.
- **Amends / qualifies / extends:** none. It is the single correction record for the dates in 26 landed ADRs (table
  below); under CF-02 those ADRs receive **no** footer and no status line. The candidate `p-17b713…` built under ADR-142
  and staged under ADR-144 is withdrawn from production eligibility; the ADR-142/144 contracts themselves stand *(agent
  interpretation, labelled)*.
- **Sources:** plan §2.3, §5.2, §5.9, §6.3, §7 (row 146), Appendix A (T1; T2 SEED-04/06/07/08; T3 C-10 clause), Appendix B
  row 1; `PD/research/B1-date-drift.md` §1–§8 (§8 is the draft adopted here, amended by CF-02); `PD/design/S2-round-structure.md`
  CF-02, CF-03; `PD/design/B4-verification.md` §0 and G1; `PD/research/B7-harness-attribution.md` §0 items 4–5, §5;
  `PD/data/date_drift.csv`; `PD/data/decision_catalog.csv` (Q-14, Q-B4-1, Q-12, Q-E2-18/19/20, Q-B1-2, Q-B1-4, OD-10);
  log rounds 5, 10, 19 and 21 and the C-10 inspection record; `git log` of the adding commits (re-read for this ADR).
- **Recorded:** 2026-10-01T07:42:36Z by Claude Code (Opus 5.5), harness `claude-code/claude-opus-5-5/subagent` — an
  agent-drafted record of the operator's decisions; the operator's words are quoted verbatim from the log.

## Context

Between 2026-09-09 and 2026-09-28, build sessions recorded event dates from a "chain date" kept apart from the machine
clock, and said so in the record: `runs/P21.5.md:23` (2026-09-13) — *"Environment clock read 2026-09-13; chain date for
this re-run = 2026-09-10."*; `runs/P32.7.md:15-17` (2026-09-27T08:37Z) — *"this run's recorded dates use the chain's
dated-entry convention — 2026-10-14 (… machine UTC at run time is 2026-09-27 …)"*. Round 3 recorded 2026-09-10 for work done on 2026-09-13; Rounds 9–10
recorded 2026-10-01…2026-10-21 for work done on 2026-09-25…09-28, including the operator's S3 deferral and the GATE-G3
approval (B1 §1, §6).

B1 scanned chain tip `b051732c` (2026-09-30T16:38:44Z → 17:08:37Z) with `git blame` against committer time: **1,051 dated
rows / 2,891 occurrences**, of which **595 rows / 2,283 occurrences** record an event on a date it did not happen. They
fold into **37 correction rows** and reach build memory (322 rows), ADRs (33), spec §55 and Appendix F/G (15), product
constants (70), fixtures (56), the obligation-event and coverage-assessment logs (6 rows / 187 occurrences),
`db/sqitch.plan` (18) and the identity of the GATE-G3-signed candidate `p-17b713…` (75). Ninety-four are deployed or
signed. Every validator passed (F-27); B4's replay finds that a date guard would have failed 70 chain commits. B7 ties
the forward ratchet (P31.7 → P32.22) to Devin CLI · `swe-2-high` and the Round-3 backward chain date to Devin CLI · Claude
Opus 4.8; this planning round repeated the drift in its own ledger (F-074: 24 late stamps in 17 commits).

The hazards are operational, not cosmetic (B1 §7): the 2026-10-10 OSM replay (D-P31.4-1) reads as eleven days overdue to
a resumer who trusts the latest recorded date, inviting a premature production re-ingest; date-ordered views invert; a
signed readout carries a false date; promoting `p-17b713` would publish "as of 2026-10-19"; and a well-meant "date fix" to
`db/sqitch.plan` breaks deploys, because sqitch hashes each line's `planned_at` into its change id and, through `parent`,
into every later id (B1 §5.7, read from sqitch `b08e5c8a`).

The fix must keep the record append-only (SIG-ENG-003; `AGENTS.md`), leave landed ADR bodies frozen (CF-02), leave signed
texts untouched, and leave the hosted sqitch registry's history as it is.

## Decision

1. **Truth source.** A recorded event date is the `date -u` reading at the moment of recording. Where that is unknown it is
   the committer time of the commit that records it, or the PR `createdAt`, written "≤ <time>". Where the operator has
   confirmed a true time read from a recorded-execution source, that time governs (C-1; Q-B1-2). Chain dates, conventions,
   "previous entry + 1 day" and guesses are prohibited.

2. **One correction record, append-only.** The correction record is this ADR plus the register
   `docs/build/reports/memory-repair/date_corrections.csv` (SEED-04; promoted from `PD/data/date_drift.csv`, extended to
   the restored GATE DECISIONS block by SEED-06, and also listing F-074's 24 late planning stamps, S6R-10). No recorded
   line, landed ADR body or `Date:` header, signed readout text, Appendix-G row (R10-A6), jsonl event or committed artifact
   is edited to fix a date. Per artifact kind:
   - **LEDGER** PHASE LOG and GATE DECISIONS, and **BUILD_INDEX**: one dated DATE CORRECTION entry each / an appended
     corrections table (SEED-07).
   - **DEFERRALS**: an appended correction section, never cell edits; lead-token transitions are queued in
     `pending_transitions` and applied by P34.8 through the repaired obligation-event tool (CF-03). Manifest
     plan-extension correction lines, `runs/`, `pr/` and CAPSTONE addenda, and a `CORRECTION.md` in each committed
     fixture-run directory (SEED-08).
   - **Landed ADRs: no footer and no status line** (CF-02). The ADR table below is their correction. The ADR-index
     generator (P34.32) may derive a "date corrected → ADR-146" marker from the register (S2 CF-02).
   - **Signed readouts** (GATE-G3, ACCEPT-R10, ACCEPT-R8): an appended, labelled agent annotation with B7's facts; no
     operator addendum describing a past state of mind (B-4, Q-E2-18 b; ADR-147).
   - **Obligation-event log**: appended `date-correction` events; `migrate` is never re-run (F-26). `reports/current/*` is
     regenerated from the events, never hand-edited.

3. **Spec.** §55's landed-status text is amended to the true dates through `spec_src` and `BUILD.sh`, recorded by one new
   Appendix G.7 row; R10-A6 is not edited (SEED-12; plan §6.3).

4. **Code and fixtures.** Hand-typed event dates leave the product constants (`ops/src/ops/release_candidate.py`'s
   deferral note and disclosure, `journey_verify.py`, `cli.py`, the dossier packet builders, the web research-dossier
   fixture). A stand-in capture carries its real authoring date or an explicit `capture_kind: stand-in` marker and no
   retrieval date. Committed fixture-run outputs keep their bytes and gain a `CORRECTION.md` (P34.22a/b). Changing the
   deferral note changes every future candidate `identity_digest`, which is intended.

5. **Sqitch: no `db/sqitch.plan` line is edited or re-stamped.**
   - L41–43 are deployed on hosted `sig-pg` (run-ledger evidence, B1 §5.7); an edit would make the next hosted deploy die
     with "Cannot find change".
   - L44–52: the operator-approved, local, read-only C-10 inspection (2026-10-01T04:59:41Z) found the stopped P33.2 test
     container `sig-p332-db` holding **48 changes deployed 2026-09-28T05:42:14Z…05:42:33Z, including all nine of L44–52
     with their stamped `planned_at` values baked into their change ids** (e.g. `recovery_apply` = `d39b1f96…`). B1's "do
     not edit L44–52 by default" therefore becomes **never**: re-stamping would change their ids and orphan that database
     and any like it.
   - The true planned times are recorded in the sqitch table below and in the register. A standalone `#` line changes no
     change id (B1 §5.7: it parses as `Plan::Blank`), so a pointer comment above a line is permitted; B4 §6.3 places
     these "sqitch comment corrections" with the B1 code ticket (P34.22a/b). No seed unit adds one.
   - A new plan line has `planned_at` ≤ its commit time (written by `sqitch add` or from `date -u`); Round 11 does not
     continue the ratchet past 2026-10-19T21:00Z.
   - The whole-tree future-date literal test (P34.22a) allow-lists L44–52 by change id through an expiring G1 allow-list
     entry, valid until 2026-10-19T21:00Z, that points here (plan Appendix A T3, S6R-07).

6. **Candidate `p-17b713…` is superseded, not re-issued and not re-signed** (B-4, Q-12 a; B1 option C).
   `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587` (identity
   `sha256:bc20d4bfbc3845896b69c6bfde71b2b588d9e15d385d7c956e1c3f9c64bf4f2f`; as-of 2026-10-19 in its descriptor and its
   `identity_digest`; 16 claims, 0 released records; staging only, never production) is withdrawn from
   production-publication eligibility by an appended supersession record (SEED-08) and kept as P32.23a/P32.25 rehearsal
   evidence. The GATE-G3 signature that accepted it is superseded with it and is **not transferred**: the first real
   production candidate is built with true dates (P35.62, row 188's pass) and the first model release (P35.63,
   D-R10-PUBLISH-1) needs its own operator signature (plan §5.9 step 7).

7. **Guard.** G1 `record-dates` (SEED-02, diff mode, committed before any seed memory record) fails a PR when a newly added
   dated record in a record position — LEDGER, BUILD_INDEX, `runs/`, `pr/`, `reports/`, readouts, `docs/tickets/`,
   `docs/adr/` `Date:`, new `db/sqitch.plan` lines, jsonl `recorded_at` — is later than its commit time (+ 5 min) or the CI
   clock, unless it carries `future-ok: <class>: <reason>`, sits in an allow-listed real-world field, or matches an
   unexpired allow entry; a correction line passes only when it also carries the true date (B4 G1 R1, R3, R5, R6). G1
   never scans the forecast text under `docs/build/planning/**` (S6R-10); that tree's late stamps are registered
   instead. R2 (not back-dated), R4 (fixture captures) and the whole-tree literal test land with P34.22a/b.

### The wrong events and their true dates (B1 §3, with the operator's C-1 / Q-B1-2 confirmations applied)

"True" is the latest time at which the event can have happened (the recording commit or PR `createdAt`) unless the
operator confirmed an exact time. Per-line detail is in the register.

| # | event (as recorded) | recorded | true (UTC) | evidence |
|---|---|---|---|---|
| 1 | P21.3 ADR-065 `Date:` | 2026-09-10 | 2026-09-09T06:12Z | `305f94d5`; PR #59 06:13Z |
| 2 | Round-3 session (P23.1–P23.4, P21.x re-runs, P23.5–P24.2; GATE-G1/G2, HUMAN-H1–H3 readouts; ADR-074/076; 21 `sources.toml` rights fields) | 2026-09-10 | 2026-09-13T19:40Z–22:10Z | `eb72be5f`…`759fcbac`; `runs/P21.5.md:23` |
| 3 | P25.1 / P25.3 landed (BUILD_INDEX rows 88, 90) | 2026-09-14 | 2026-09-15T17:28Z / 19:11Z | `8670a4da` / `38841865` |
| 4 | P25.5 fixtures "added" | 2026-09-17 | 2026-09-16T02:04Z | `7b52f2b4` |
| 5 | P27.3 run-ledger entries | 2026-09-23 | 2026-09-22T20:25Z | PR #114 |
| 6 | P31.6 ADR-113 + `inventory_before.json` | 2026-09-26 | 2026-09-25T06:32Z | `184e3644` |
| 7 | P31.7 ADR-114; sqitch `resolution_supersede` | 2026-10-02 | 2026-09-25T08:09Z | `062306e7`; PR #143 |
| 8 | P31.10 landed; sqitch `review_campaign` | 2026-10-02 | 2026-09-25T22:11–22:18Z | `b884ae73`; PR #146 |
| 9 | P31.11 ADR-116; sqitch `camera_site_human_decisions` | 2026-10-02 | 2026-09-25T23:21Z | `4608f056`; PR #147 |
| 10 | P31.14 landed; ADR-117 | 2026-10-03 | 2026-09-26T14:29–14:33Z | PR #151 |
| 11 | P31.15 landed / ADR-118 / ACCEPT-R8 R8-1 note | 2026-10-03 / 10-05 | 2026-09-26T15:16Z | PR #152 |
| 12 | P32.2 landed; ADR-121; sqitch `claim_assertion_bindings` | 2026-09-28 / 10-03 | 2026-09-27T04:16Z | PR #157 |
| 13–20 | P32.3…P32.10 landed + ADR-122…129 + sqitch L45–48 | 10-10 … 10-18 | 2026-09-27T05:27Z … 10:12Z | PRs #158–#165 |
| 21–26 | P32.15, .16, .16a, .17, .18, .19 landed + ADR-134…138 + sqitch L50–51 | 10-04 … 10-01 | 2026-09-27T14:13Z … 17:56Z | PRs #171–#176 |
| 27 | P32.22 sqitch `recovery_apply` | 2026-10-19T21:00Z | 2026-09-27T20:03Z | `2404edb0`; PR #179 |
| 28 | Orchestrator pause at HUMAN-H4 | 2026-10-19 | 2026-09-27T20:07Z | `c4aafa20` |
| 29 | **Operator defers the S3 human-evaluation spine** ("let's defer all the human review steps and proceed") | 2026-10-19 | **2026-09-28T01:15:49Z** (operator-confirmed, C-1/Q-B1-2; recorded in `a33cd6ec` at 01:27:21Z) | B7 §0 item 5 (Devin session store) |
| 30 | P32.23a landed; candidate built with as-of 2026-10-19; ADR-142 | 2026-10-19 | 2026-09-28T02:11Z | `9bf11201`; PR #180 |
| 31 | P32.24 landed; ADR-143 | 2026-10-20 | 2026-09-28T03:08Z | PR #181 |
| 32 | Orchestrator pause at GATE-G3 | 2026-10-19 | 2026-09-28T03:09Z | `e4be1b84` |
| 33 | **GATE-G3 approved** ("Date: 2026-10-19") | 2026-10-19 | **2026-09-28T03:49:14Z** (operator-confirmed, C-1/Q-B1-2; signed text committed in `95c8a73f` at 03:49:46Z) | B7 §0 items 4–5 |
| 34 | P32.25 landed; ADR-144 | 2026-10-20 | 2026-09-28T04:36Z | PR #182 |
| 35 | P33.1 landed; reconciliation cells "DONE 2026-10-21"; all 97 `events.jsonl` `recorded_at` | 2026-10-21 | 2026-09-28T05:13–05:19Z | `7a2ff9fa` / `08b3135f`; PR #183 |
| 36 | Propagation: P33.2–P33.8 (correctly dated 09-28) copied #29/#33's date into §55, App F/G, ADR-145, CAPSTONE_*, OPERATIONAL_READINESS, ACCEPT-R10, `render_plan.py` | 2026-10-19 | as #29 / #33 | `71e8bc83`, `e8bc0179`, `4127dbf3`, `c77bd45e` |
| 37 | Dossier "replay" retrieval/observation/search/generation dates | 2026-10-01 / 10-02 | **no such event** — stand-ins authored 2026-09-27T12:06Z | `f73a997e` |

ACCEPT-R10 was approved at **2026-09-28T18:46:46Z** (operator-confirmed, C-1/Q-B1-2); its signed text was committed in
`4127dbf3` at 18:47:37Z. No gate approval or decision was given on 2026-10-19.

### Landed ADR dates (26 ADRs, 33 positions; no footer is appended to any of them — CF-02)

The `Date:` headers were checked again for this ADR against `git log --diff-filter=A` of each file.

| ADR | position | recorded | true (UTC) | basis |
|---|---|---|---|---|
| ADR-065 | `Date:` header | 2026-09-10 | 2026-09-09T06:13Z | P21.3: PR #59 `createdAt` 06:13Z; added in `305f94d5` at 06:12:38Z |
| ADR-074 | `Date:` header | 2026-09-10 | 2026-09-13T20:21:05Z | Round-3 chain date (`runs/P21.5.md:23`); added in `ea479fe8` |
| ADR-076 | `Date:` header | 2026-09-10 | 2026-09-13T22:10:36Z | Round-3 chain date (`runs/P21.5.md:23`); added in `759fcbac` |
| ADR-113 | `Date:` header | 2026-09-26 | 2026-09-25T06:32Z | P31.6: `184e3644`; PR #142 |
| ADR-114 | `Date:` header | 2026-10-02 | 2026-09-25T08:09Z | P31.7: `062306e7`; PR #143 `createdAt` 11:56Z |
| ADR-116 | `Date:` header | 2026-10-02 | 2026-09-25T23:21Z | P31.11: `4608f056`; PR #147 `createdAt` 23:22Z |
| ADR-117 | `Date:` header | 2026-10-03 | 2026-09-26T14:33Z | P31.14: PR #151 `createdAt` 14:33Z; closeout `fbb47a9c` |
| ADR-118 | `Date:` header | 2026-10-05 | 2026-09-26T15:16Z | P31.15: PR #152 `createdAt` 15:16Z; closeout `90264c8a` |
| ADR-121 | `Date:` header | 2026-09-28 | 2026-09-27T04:16Z | P32.2: PR #157; closeout `5677495a` 04:17Z |
| ADR-122 | `Date:` header | 2026-10-10 | 2026-09-27T05:27Z | P32.3: PR #158; closeout `2a329e37` 05:32Z |
| ADR-123 | `Date:` header | 2026-10-11 | 2026-09-27T06:41Z | P32.4: PR #159; closeout `03ac3b06` 06:43Z |
| ADR-124 | `Date:` header | 2026-10-12 | 2026-09-27T07:17Z | P32.5: PR #160; closeout `616b889c` 07:19Z |
| ADR-125 | `Date:` header | 2026-10-13 | 2026-09-27T08:06Z | P32.6: PR #161; closeout `c8d2856e` 08:06Z |
| ADR-126 | `Date:` header | 2026-10-14 | 2026-09-27T08:37Z | P32.7: PR #162; closeout `778a5e2e` 08:39Z |
| ADR-127 | `Date:` header | 2026-10-15 | 2026-09-27T09:11Z | P32.8: PR #163; closeout `5713f5dd` 09:13Z |
| ADR-128 | `Date:` header | 2026-10-16 | 2026-09-27T09:51Z | P32.9: PR #164; closeout `c31380fb` 09:52Z |
| ADR-129 | `Date:` header | 2026-10-18 | 2026-09-27T10:12Z | P32.10: PR #165; closeout `13ade2b2` 10:25Z |
| ADR-134 | `Date:` header | 2026-10-04 | 2026-09-27T14:13Z | P32.15: PR #171; closeout `4dd5a038` 14:15Z |
| ADR-135 | `Date:` header | 2026-10-18 | 2026-09-27T15:05Z | P32.16: PR #172; closeout `0669f65d` 15:05Z |
| ADR-136 | `Date:` header | 2026-10-02 | 2026-09-27T16:35Z | P32.17: PR #174; closeout `2c588cd6` 16:41Z |
| ADR-137 | `Date:` header | 2026-10-02 | 2026-09-27T17:31Z | P32.18: PR #175; closeout `0f2e0711` 17:32Z |
| ADR-138 | `Date:` header | 2026-10-01 | 2026-09-27T17:56Z | P32.19: PR #176; closeout `3e26a2dc` 17:56Z |
| ADR-138 | body L26, L85 | 2026-10-01 | no such event (synthetic replay/capture label) | the dossier replay-label convention (row 37 above) |
| ADR-142 | `Date:` header | 2026-10-19 | 2026-09-28T02:11Z | P32.23a: PR #180; closeout `22b773f8` |
| ADR-142 | body L15, L60 (S3 deferral) | 2026-10-19 | 2026-09-28T01:15:49Z | row 29 above (C-1) |
| ADR-143 | `Date:` header | 2026-10-20 | 2026-09-28T03:08Z | P32.24: PR #181; closeout `da146260` |
| ADR-143 | body L30 (S3 deferral) | 2026-10-19 | 2026-09-28T01:15:49Z | row 29 above (C-1) |
| ADR-144 | `Date:` header | 2026-10-20 | 2026-09-28T04:36Z | P32.25: PR #182; closeout `e4bd612e` 04:39Z |
| ADR-144 | body L12 (GATE-G3) | 2026-10-19 | 2026-09-28T03:49:14Z | row 33 above (C-1) |
| ADR-145 | body L13 (GATE-G3) | 2026-10-19 | 2026-09-28T03:49:14Z | row 33 above (C-1) |
| ADR-145 | body L16 (S3 deferral) | 2026-10-19 | 2026-09-28T01:15:49Z | row 29 above (C-1) |

B1's register rows give the commit-time upper bounds (01:27Z for the deferral, 03:49Z for GATE-G3); the operator's C-1
confirmation fixes the exact times shown. Only the recorded dates are corrected; every listed ADR's decision stands as
written.

### `db/sqitch.plan` (18 lines; none is edited)

| line | change | recorded `planned_at` | true (UTC; adding commit) | state | rule |
|---|---|---|---|---|---|
| L27 | `resolution_materialize` | 2026-09-23T12:00:00Z | 2026-09-23T05:57:28Z (`bb8dbbfb`) | hosted | same-day; never edit |
| L28 | `relationship_materialize` | 2026-09-23T13:00:00Z | 2026-09-23T06:35:43Z (`cc86bd0b`) | hosted | same-day; never edit |
| L33 | `materialize_role` | 2026-09-24T12:00:00Z | 2026-09-24T04:19:51Z (`3c090012`) | hosted | same-day; never edit |
| L34 | `camera_site_resolution` | 2026-09-24T18:00:00Z | 2026-09-24T10:58:49Z (`29b75f82`) | hosted | same-day; never edit |
| L39 | `ingest_run_capture` | 2026-09-25T00:00:00Z | 2026-09-24T23:39:09Z (`a1b9870a`) | hosted | same-day; never edit |
| L40 | `partner_org_identity_key` | 2026-09-25T12:00:00Z | 2026-09-25T03:52:43Z (`a29d3748`) | hosted | same-day; never edit |
| L41 | `resolution_supersede` | 2026-10-02T12:00:00Z | 2026-09-25T08:09Z (`062306e7`) | hosted | future-dated; never edit |
| L42 | `review_campaign` | 2026-10-02T13:00:00Z | 2026-09-25T22:18Z (`b884ae73`) | hosted | future-dated; never edit |
| L43 | `camera_site_human_decisions` | 2026-10-02T19:00:00Z | 2026-09-25T23:21Z (`4608f056`) | hosted | future-dated; never edit |
| L44 | `claim_assertion_bindings` | 2026-10-03T12:00:00Z | 2026-09-27T04:16Z (`6f9fab73`) | `sig-p332-db` (C-10) | future-dated; never re-stamp |
| L45 | `partner_org_scoped_identity_key` | 2026-10-10T12:00:00Z | 2026-09-27T05:27Z (`6b970335`) | `sig-p332-db` | future-dated; never re-stamp |
| L46 | `shared_temporal_contract` | 2026-10-11T00:00:00Z | 2026-09-27T06:41Z (`18bda164`) | `sig-p332-db` | future-dated; never re-stamp |
| L47 | `publication_dispositions` | 2026-10-12T00:00:00Z | 2026-09-27T07:17Z (`a705a588`) | `sig-p332-db` | future-dated; never re-stamp |
| L48 | `human_eval_campaign` | 2026-10-16T00:00:00Z | 2026-09-27T09:51Z (`f5a21263`) | `sig-p332-db` | future-dated; never re-stamp |
| L49 | `disposition_decided_at_authority` | 2026-09-27T14:00:00Z | 2026-09-27T10:50:13Z (`b132bbbb`) | `sig-p332-db` | same-day; never re-stamp |
| L50 | `intake_storage` | 2026-10-18T00:00:00Z | 2026-09-27T15:05Z (`aa5c5194`) | `sig-p332-db` | future-dated; never re-stamp |
| L51 | `intake_application_bridge` | 2026-10-19T00:00:00Z | 2026-09-27T15:58Z (`6cc5d9d8`) | `sig-p332-db` | future-dated; never re-stamp |
| L52 | `recovery_apply` | 2026-10-19T21:00:00Z | 2026-09-27T20:03Z (`2404edb0`) | `sig-p332-db` | future-dated; never re-stamp |

"Hosted" is recorded-execution evidence from the run ledgers (B1 §5.7); the hosted registry was not queried. L44–52 are
undeployed on hosted per the run ledgers (`live_verification=false`; F-14) and deployed in the local `sig-p332-db`
(C-10). Eleven lines are future-dated (L41–48, L50–52), three of them on hosted.

## Consequences

- The record becomes truthful without losing history. A reader of an affected line consults the register or this ADR;
  the original text stays where it was.
- Twenty-six landed ADRs keep false `Date:` headers or body dates permanently; this ADR and the register are the only place
  their true dates appear (CF-02's price for frozen bodies). P34.32's index generator can surface the marker.
- Three hosted sqitch registry rows (L41–43) and the local `sig-p332-db` keep false `planned_at` values forever — recorded
  and harmless, since sqitch does not require monotonic `planned_at` (L49 deploys after L48 in `make test-db`).
- The candidate's deferral note and constants change (P34.22a), so the next candidate's identity differs from
  `p-17b713`; GATE-G3's acceptance does not carry over, and the first model release needs its own operator signature.
- D-P31.4-1's verify step must check `date -u` ≥ 2026-10-10T03:35Z and the scheduler's `lastAttemptTime`, never the latest
  memory date (B1 §7 hazard 1); G1's expiring allow entries enforce the same clock rule.
- One more CI guard (G1) runs in the `docs` job; it checks the dates this round writes too, including this ADR's own
  `Date:` header.

## Alternatives considered

- **Rewrite the wrong dates in place:** rejected — violates append-only (SIG-ENG-003), breaks the signed digests of
  `p-17b713` and GATE-G3, and changes sqitch change ids.
- **Append a `Date correction` footer to each landed ADR** (B1 §8 clause 2): rejected by CF-02 (plan Appendix B row 1) —
  landed ADR bodies stay frozen; one register plus this ADR is one owner and leaves the frozen-after-landing policy with
  no exceptions.
- **Re-stamp the undeployed sqitch lines L44–52:** rejected — C-10 found a persistent database that holds them as
  stamped; re-stamping is also an in-place edit.
- **Re-issue and re-sign `p-17b713` now (B1 option B):** rejected (Q-12 a) — it spends a human gate and a rebuild on a
  0-record fixture candidate nobody will publish.
- **Leave the candidate with a correction note (B1 option A):** rejected — any later promotion would publish a false future
  "as of" and break as-of pinning.
- **Do nothing:** rejected — leaves the D-P31.4-1 hazard and a future false "as of" on the public surface.

## Revisit trigger

- A wrong recorded date is found that is not in the register: append it to the register (and, for an ADR date, a row in a
  new correction ADR — this ADR is not edited).
- A read-only check of hosted `sqitch.changes` shows any of L44–52 deployed, or shows a head other than
  `camera_site_human_decisions` before P34.46.
- The operator chooses to publish, re-issue or re-sign `p-17b713` or any other fixture candidate.
- A tooling change reintroduces a manual date input without G1, or G1 is weakened, disabled or allow-listed beyond an
  expiring entry.
- The expiring L44–52 allow-list entry reaches 2026-10-19T21:00Z.

## Clarification (2026-10-01T16:54:25Z)

Appended by Claude Code (Opus 5.5), Stage-B sub-agent SEED-15 (Round 11, T4); the record above is not rewritten. It
resolves a conflict between Decision 5 and the record policy for `db/sqitch.plan` (CARRY: SEED-13c).

- **What the record says:** Decision 5's third bullet permits "a pointer comment above a line" (a standalone `#` line
  changes no change id; B1 §5.7) and places these "sqitch comment corrections" with the B1 code ticket (P34.22a/b).
- **What holds:** `docs/build/tools/record_policy/history.policy` declares `append-only db/sqitch.plan` — the plan only
  gains lines at its end — and the history guard (`docs/build/tools/memory_guard.py`, `judge_policy_ao`; the skill's
  `check-history.sh`) reports any line inserted before the end of that file as a violation. **No comment, pointer or
  other line is inserted above any `db/sqitch.plan` line**, by P34.22a/b or any other row. A correction to a sqitch
  line's recorded date is made only by appended record: this ADR's table "`db/sqitch.plan` (18 lines; none is edited)",
  the date-correction register (`docs/build/reports/memory-repair/date_corrections.csv`), and, where a ticket needs to
  say more, an appended amendment in its own ADR text — consistent with `history.policy`'s C-10 note ("their true dates
  are corrected by appended record only").
- **Effect on the rest of this ADR:** none beyond that bullet. L41–52 are never edited or re-stamped; new plan lines
  still append at the end of the file with `planned_at` not later than their commit (from `sqitch add` or `date -u`);
  the expiring L44–52 allow-list entry (until 2026-10-19T21:00Z) is unchanged. A ticket contract that still names the
  comment form (P34.22a/b) reads through this clarification.
