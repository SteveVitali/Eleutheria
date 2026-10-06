# F1: Owed-register adjudication (36 rows)

This is row **F1** of `META_PLAN.md` (Stage P, Wave 4). It was authored 2026-09-30T17:22–17:40Z (`date -u`) by
Claude Code (Opus 5.5), with planning HEAD `4aff9a48` and chain tip `b051732c`.

The pass was **read-only**. It used repo reads, `uv run` read-only CLIs (`sig-connectors gate` and the
memory-tool `check`/`verify`), GCP `describe`/`list`/`cat` against project `zeta-medley-508121-u7`, `gh repo view`,
and public GETs against the live site and API. No hosted database query was run, and no credential path was used.
No control file was edited: `DEFERRALS.md`, LEDGER, `sources.toml` and the manifest are untouched. Every status
change below is a **proposal** that Stage B/T4 applies as a dated, appended cell (P7, P10).

**Outputs**
- `data/owed_register_adjudication.csv`: one row per owed obligation (36), with the full columns.
- `findings/incoming/F1.csv`: NEW-1…NEW-8.

**Evidence classes (P1):** `code` · `recorded-execution` · `live-read` · `operator-statement` · `inference`.
Inferences are labelled as such.

---

## 0. Bottom line

1. **Dispositions.** The 36 rows break down as follows:

   | disposition | rows |
   |---|---|
   | `live-return-pass` | 9 |
   | `ticket` | 8 |
   | `operator-action` | 7 |
   | `human-marker` | 4 |
   | `wontfix` | 3 |
   | `later-phase` | 3 |
   | `already-done` | 2 |

   **32 of 36 rows are in reach without recruiting anyone.** Only the four `human-marker` rows need people the
   operator cannot supply: the S3 evaluation spine (`D-R10-HUMAN-1`, `D-R6.1-EVAL`, `D-P30.2b-2`) and usability
   participants (`D-R10-USERS-1`).
2. **Blocker classes, as re-verified:**

   | blocker class | rows |
   |---|---|
   | rights | 11 |
   | operator | 7 |
   | human | 6 (2 of them operator-fillable) |
   | engineering | 4 |
   | live-execution | 3 |
   | external | 2 |
   | scheduled | 1 |
   | none (already done) | 2 |

   Twelve of the 36 rows change class relative to A3/Appendix B (§4.3, NEW-6). Thesis T3 holds, but in a
   sharper form. The binding constraint is the **operator's decisions and production "go"s**, not recruited human
   labour. Only 4 rows need recruiting.
3. **Status corrections (proposals).**
   - **3 tokens are wrong on the evidence:**
     - `D-SOURCES.12-1` PARTIAL → **DONE 2026-09-26** (E4 S1, confirmed).
     - `D-SOURCES.7-1` OPEN → **PARTIAL** (E4 S4, confirmed).
     - `D-P21.3-2` OPEN → **DONE**. This one is new: the hosted scheduled jobs already exercise every credential
       (NEW-5).
   - **6 rows leave the owed register** on an operator answer:
     - `wontfix`: `D-JURIS.2-1`, `D-SOURCES.2-2`, `D-SOURCES.9-2`.
     - `later-phase`: `D-SOURCES.9-3`, `D-R7.1-AUTH`, `D-P21.7-1`.
   - **Effect on the count.** If all of these are applied, 28 of the original 36 rows stay owed. Adding the one
     missing row (NEW-4) and the two live legs owed by closed rows gives **31** (§4.4).
4. **Closed rows whose DONE does not hold (2 of the 13).** Both are DONE on engineered evidence only. Each row's
   own verify rule names the hosted API, and the hosted API still runs the 2026-09-25 image:
   - **`D-P31.1-1`**: live `/v1/contradiction` takes **13.6 s warm**; the rule is "< ~1 s" (NEW-2).
   - **`D-P31.5-2`**: the live `/v1/search?q=Vigilant` still labels a flagged partner organisation by name (NEW-3).

   The other 11 hold on their evidence. All 13 carry wrong closure dates, and their true dates are in §5.
5. **Two live checks overturn recorded premises.**
   - **`D-FEDERAL.1-1` cannot close on schedule (NEW-1).** The cron *is* firing: its last run was
     2026-09-28T05:00Z, with outcome `quota_reached`, 11 of 30 requests used and 330 claims emitted. But each run
     restarts at keyword 0, and the key allows about 10 requests a day. So the same seven tail keywords were deferred
     on both hosted runs and are never fetched.
   - **`D-P21.5-1`'s only blocker has lapsed.** The repo is now PUBLIC (E1 NEW-14), so the SWH leg can run.
6. **`D-P31.4-1` is intact.**
   - Trigger: `35 3 10 * *`, ENABLED, `scheduleTime 2026-10-10T03:35:00Z`, never attempted.
   - Job: pinned to `feff986c…`, 36 h timeout, 0 retries.
   - No `2026-10-10/` run prefix exists, which is correct before the fire.
   - Nothing has changed since 2026-09-28.
   - The B1 NEW-4 hazard stands: the read-back must gate on `date -u` **and** the scheduler's `lastAttemptTime`.
7. **A missing owed row (NEW-4).** ADR-124 makes the operator's `allow` dispositions for the HG-11-approved partner
   organisations an owed act, but no DEFERRALS row records it. If the Round-10 API ships before those allows exist,
   today's public vendor names become `pending_publication_review` tombstones. That act must be sequenced **before**
   the API activation.

---

## 1. Method

1. **Inputs read.**
   - META_PLAN §3, the F1 block, §7/§7.1, §8.1 and Appendix B.
   - `universe/UNIVERSE.csv` (97 deferral rows, 36 owed) and its README.
   - OPERATIONAL_READINESS §(f)/(f3).
   - E4, E3 (§§0–9), E1 (summary and E1-21), G1 (§§3.3–3.7, 6), B1 (§§3, 4, 5.7, 7) and B2 (§§1, 5.1–5.2), plus
     `data/append_only_violations.csv` and `data/date_drift.csv`.
   - A2's F-13/F-14/F-15/F-21/F-28 and the incoming finding titles, to avoid duplicates.
   - All 36 owed `DEFERRALS.md` rows and the 13 closed rows (§5), extracted by id with `grep -n '^| <id> '`. The
     file was not read whole.
2. **Re-verification per row.** Each row was checked against primary evidence: the code line its blocker names, the
   recorded execution (GCS run rows, Cloud Run executions, return-pass JSON status), or a live read (scheduler, API,
   site, `gh`). §9 logs every command.
3. **What F1 did not re-verify.** Hosted database state was **not** re-queried (no credential path was used).
   Hosted counts are therefore carried from the latest recorded execution and labelled with its date:
   - 11,625 pending and 0 decisions (P31.10, 2026-09-25).
   - `records_request` = 0 (P30.4, 2026-09-24).
   - the `sig.org.name` key count (never measured).
4. **Has anything changed since 2026-09-28?** `git log --since=2026-09-28 -- docs/tickets/DEFERRALS.md` shows only
   the P33.4–P33.8 closeout commits. The last is `c77bd45e`, 2026-09-28T22:45Z. Nothing has been appended since.
   The world has moved, though (§3).

---

## 2. Adjudication (summary; full columns in `data/owed_register_adjudication.csv`)

`sc` = status correct: y · n · p (proposal contingent on an operator answer). "→" marks a proposed status change.

| # | d_id | status | sc | blocker | proposed disposition | depends on |
|---|---|---|---|---|---|---|
| 1 | D-P21.3-2 | OPEN → **DONE** | n | none | already-done (hosted run rows: congress_gov 09-29, civicclerk 09-22, osm_overpass 09-28; muckrock auth 09-16) | — |
| 2 | D-P21.5-1 | PARTIAL | y | live-execution | live-return-pass(P21.5, SWH leg; optional non-GCS push → wontfix) | operator ack (the decline's premise lapsed) |
| 3 | D-P21.7-1 | OPEN → later-phase | p | operator | later-phase(the operator opts into contribution-back: rotate key, OE page, `registered=true`) | Track 0.3 (operator: not now) |
| 4 | D-JURIS.2-1 | PARTIAL → DONE + WONTFIX (eID) | p | external | wontfix(Belgian-eID leg; D-JURIS.2-2 precedent) | E4 R1=a |
| 5 | D-SOURCES.2-2 | OPEN → WONTFIX | p | rights | wontfix(DocumentCloud ToS forbids extraction; FLP excludes SIG) | E4 R2a/R2b |
| 6 | D-SOURCES.7-1 | OPEN → **PARTIAL** | n | rights | ticket(R11 rights-flip batch: `dot_511_tx`) | E4 R3, S4 |
| 7 | D-SOURCES.7-2 | OPEN | y | operator | operator-action(HG-09: register the 511 platform keys) | Stream I priority |
| 8 | D-SOURCES.8-1 | PARTIAL | y | rights | ticket(R11 rights-flip batch: edmonton/hk/qldc; bellevue after the NC statement) | E4 R4a–d |
| 9 | D-SOURCES.8-2 | OPEN | y | operator | operator-action(HG-09: QLD + NSW keys) | Stream I priority |
| 10 | D-SOURCES.9-1 | OPEN | y | rights | ticket(R11 rights-flip batch: `procportal_chicago_il`) | E4 R5 |
| 11 | D-SOURCES.9-2 | OPEN → re-scope → WONTFIX | p | rights | wontfix(2 tenants, no parser, login wall) | E4 S2=b |
| 12 | D-SOURCES.9-3 | OPEN → later-phase | p | external | later-phase(a documented endpoint + reviewable terms) | E4 S3=a |
| 13 | D-SOURCES.9-4 | OPEN | y | rights | ticket(R11: capture BidNet terms → decide; `periscope_s2g` superseded) | E4 R6a/R6b |
| 14 | D-SOURCES.12-1 | PARTIAL → **DONE 2026-09-26** | n | none | already-done(P26.16 + D-SOURCES.17-1 + 0/68 retry) | E4 S1 (confirmation) |
| 15 | D-FEDERAL.1-1 | OPEN | y | **engineering** | ticket(R11: persisted rotating sweep cursor, budget = measured quota, live cron `0 5 * * 1`, +0 count) | — (or a key-tier upgrade) |
| 16 | D-R6.1-EVAL | OPEN | y | human | human-marker(187 P32.23 via F4) | D-R10-HUMAN-1; Q-24, Q-28 |
| 17 | D-R7.1-AUTH | OPEN → later-phase | p | operator | later-phase(demand + moderation plan + threat model) | D-P32.16-1 first |
| 18 | D-R7.2-SEND | OPEN | y | operator | operator-action(Q-E3-10: the operator as consenting filer, else later-phase) | Q-E3-10 |
| 19 | D-P30.2b-1 | OPEN | y | human* | operator-action(the operator curates 50–100 seed items; then an R11 hosted verify leg) | operator time |
| 20 | D-P30.2b-2 | OPEN | y | human | human-marker(186 HUMAN-H5 → 187 P32.23 via F4) | D-R10-HUMAN-1 |
| 21 | D-P31.4-1 | OPEN | y | scheduled | live-return-pass(P31.4 read-back after the 2026-10-10T03:35Z fire; G1 §3.7) | clock + `lastAttemptTime` guard |
| 22 | D-R10-HUMAN-1 | OPEN | y | human | human-marker(184 → 185 → 186 → 187 via F4) | D-R10-LIVE-1, reviewer UI, live dossiers, Q-28 |
| 23 | D-R10-SOURCES-1 | OPEN | y | rights | operator-action(E4 B1–B6, after an R11 prep ticket: URLs, NEW-8, Part VIII drafts) | R11 prep; Q-19 |
| 24 | D-R10-LIVE-1 | OPEN | y | live-execution | live-return-pass(183 P32.22) as an R11 activation ticket | ops safety wave, hosted sqitch L44–52, B1 constants, operator go |
| 25 | D-R10-PUBLISH-1 | OPEN (annotate) | y | operator | live-return-pass(191 P32.25) over a **new** candidate + a candidate-specific readout | LIVE-1 → 23a-1; D-P32.16-1; Q-9, Q-12 |
| 26 | D-R10-MEMORY-1 | OPEN | y | **engineering** | ticket(R11 memory repair, then cutover at an operator-approved boundary) | B3/B4; Q-13, Q-14 |
| 27 | D-R10-USERS-1 | OPEN | y | human | human-marker(a new R11 usability row after recruiting; protocol → live site) | Q-28, Q-E3-2 |
| 28 | D-P32.3-1 | OPEN | y | human* | operator-action(the operator records dispositions after an R11 hosted audit sizes N) | R11 read-only hosted audit |
| 29 | D-P32.10a-1 | OPEN | y | engineering | ticket(R11 sqitch hygiene + full verify/revert CI) | before the hosted L44–52 deploy |
| 30 | D-P32.16-1 | OPEN | y | operator | operator-action(Q-27/Q-29: owner, retention, SLAs, alias) → receiver deploy | `/dispute/` honesty fix first |
| 31 | D-P32.16a-1 | OPEN | y | engineering | ticket(R11 sqitch hygiene; the same ticket as #29) | — |
| 32 | D-P32.18-1 | OPEN | y | **rights** | live-return-pass(179 P32.18) | D-R10-SOURCES-1, URL reconciliation, B1 NEW-3 |
| 33 | D-P32.19-1 | OPEN | y | **rights** | live-return-pass(180 P32.19) | same |
| 34 | D-P32.20-1 | OPEN | y | **rights** | live-return-pass(181 P32.20) | same + E4 B3/B4 |
| 35 | D-P32.21-1 | OPEN | y | **rights** | live-return-pass(182 P32.21) | same + E4 B6 + the NEW-8 fix |
| 36 | D-P32.23a-1 | OPEN | y | live-execution | live-return-pass(188 P32.23a) with corrected constants | D-R10-LIVE-1; B1 §5.4/5.8; Q-12 |

`*` = human, but the operator can fill the seat (E3 §6). **Bold** blocker = changed from A3/Appendix B.

---

## 3. What moved since 2026-09-28 (primary evidence)

- **D-FEDERAL.1-1.** The cron fired 2026-09-28T05:00:05Z (`lastAttemptTime`).
  - Run row `sam_gov/2026-09-28/2026-09-28T05-03-16+00-00.json`: `quota_reached`, `sweep_requests` 11/30,
    `claim_count` 330 (emitted), 8 slices in `sweep_skipped`, 1 disappearance (`acoustic gunshot`,
    `access_restricted`).
  - Nothing was appended to DEFERRALS.
  - Live cron `0 5 1 * 1`: the next fire is **2026-10-01T05:00Z** (a Thursday, due to OR semantics), then 10-05.
- **D-P21.5-1.** `gh repo view` returns `SteveVitali/Eleutheria` `visibility: PUBLIC`, so the SWH blocker has lapsed.
  E1 already saw this at 16:44Z.
- **D-P21.3-2.**
  - Hosted scheduled runs with the credentials: `congress_gov` 2026-09-29 ok, 20,008 emitted; `osm_overpass`
    2026-09-28 ok, 5,214; `civicclerk` 2026-09-22 ok, 5,311.
  - `sig-sched-muckrock` fires for the first time 2026-10-01T06:00Z.
- **Production posture (Track 0; §7.1).**
  - Backups and PITR are on, and `/curate/` has been removed from the public bucket.
  - The MapRoulette key stays unrotated (operator).
  - Production fixes are to be specified as Round-11 tickets; alerts route to the operator.
  - Nothing owed was closed by these actions. They change the prerequisites for D-R10-LIVE-1: a restore path now
    exists, but it is undrilled.
- **Unchanged.**
  - The rights-row gates: all 18 re-run, identical to E4 at 16:41Z.
  - The return-pass packets: 7/7 `prepared_not_executed`, `approval_refs: []`.
  - The `[intake]` flags and `registered=false`.
  - Both sqitch defects.
  - Readouts HUMAN-H4/H5: PENDING.
  - `USABILITY_SESSIONS.json`: absent.
  - The batch-05 trigger and image.
  - No Round-10 route live (`/releases/`, `/research-dossier/`, `/intake/`, `/intake/new` all 404).
  - `sig-api` on `40a47da8…` (`sig-api-00011-wic`, 2026-09-25).

---

## 4. Status and blocker corrections (proposals; T4 appends them, never edits)

### 4.1 Status tokens wrong on the evidence (3)

| row | today | proposed | evidence |
|---|---|---|---|
| D-SOURCES.12-1 | PARTIAL 2026-09-19 | **DONE 2026-09-26 (P31.13)** | `catalog_sweep_2026-09-26_retry.json` `counts` = {retried 68, link_rotted 40, non_target 21, unreachable 7}, `retried_at` 2026-09-26T09:39:44Z; D-SOURCES.17-1 DONE 2026-09-24; `camreg_stalbert_ab` LOADABLE. **E4 S1 verified.** |
| D-SOURCES.7-1 | OPEN 2026-09-17 | **PARTIAL (4/5)** | `dot_511_la` LOADABLE (the others in E4 §6); hosted run dirs `dot_511_{al,ga,la,md}`; `dot_511_tx` REFUSED. **E4 S4 verified.** |
| D-P21.3-2 | OPEN | **DONE** (credential leg) | The hosted run rows in §3; `muckrock` execution `fx2ch` 2026-09-16 exit 0 (auth ok; the API challenge is an access issue, NEW-7); secrets bound (`ops/cadence.toml:125,340`). **New (NEW-5).** |

### 4.2 Rows that leave the register on an operator answer (6)

`D-JURIS.2-1` (E4 R1/S5) · `D-SOURCES.2-2` (R2) · `D-SOURCES.9-2` (S2) · `D-SOURCES.9-3` (S3) · `D-R7.1-AUTH` (a
deliberate later decision by design, ADR-100) · `D-P21.7-1` (the operator deferred contribution-back and left the key
stale).

### 4.3 Blocker-class corrections vs A3/Appendix B (12; NEW-6)

| row | A3 class | re-verified class | why |
|---|---|---|---|
| D-P21.3-2 | operator | none | discharged (4.1) |
| D-SOURCES.12-1 | rights | none | discharged (4.1) |
| D-P21.5-1 | operator | live-execution | repo public; only the SWH call remains |
| D-JURIS.2-1 | rights | external | every rights leg is LOADABLE; a Belgian eID is a capability the operator lacks |
| D-SOURCES.9-2 | external | rights | the robots wall is disregarded under GL-GATE-08 (`procurement.py:1400-1403`); terms + parser are the real blockers |
| D-FEDERAL.1-1 | scheduled | engineering | sweep starvation (NEW-1); the schedule alone never closes it |
| D-P30.2b-2 | engineering | human | a fresh human holdout is the binding input |
| D-R10-MEMORY-1 | operator | engineering | the log must be repaired (B2 §5.1, B1 NEW-7) before a cutover approval means anything |
| D-P32.18/19/20/21-1 | live-execution | rights | `approval_refs: []`; nothing can execute until HG-03 decides |

The E4 corrections were checked (S1 and S4 confirmed on the gate plus artifacts; S2, S3 and S5 confirmed on code and
gate evidence). **B2's unjustified transitions** all concern closed rows, not owed rows (§5). **B1's future-dated
closures** hide no wrong *owed* status. They do hide two closed rows whose DONE does not hold at the live layer (§5).

### 4.4 Effect on the register

36 owed
− 3 closed (D-SOURCES.12-1, D-P21.3-2 DONE; D-JURIS.2-1 rights scope DONE with its eID leg WONTFIX)
− 5 other rows leaving on operator answers (4.2 minus D-JURIS.2-1)
+ 1 missing row (ADR-124 allows, NEW-4)
+ 2 re-opened live legs (D-P31.1-1 and D-P31.5-2, as "engineered; live leg owed" annotations)
= **31 owed**.

**Counting only the original 36 rows, 28 remain owed** (36 − 2 DONE − 3 WONTFIX − 3 later-phase).

---

## 5. The 13 closed-by-future-date or unjustified-transition rows (B1/B2)

B2 found **5 unjustified transitions**: the DONE note postdates the commit and no event backs it. It also found
**8 obligation events mutated in place to DONE** by P33.1, each of which carries a future-dated reconciliation stamp.
B2's summary table counts 4 CSV rows because one row holds both D-P31.1-1 and D-P31.1-3. Every row was re-checked
against its own "how to verify" rule. True dates come from B1 §3 and git.

| # | row | recorded DONE | true date (UTC) | closing work | re-check 2026-09-30 | DONE holds? |
|---|---|---|---|---|---|---|
| 1 | D-P30.2b-3 | 2026-10-02 (`4e0dd070`) | 2026-09-25T23:21Z (`4608f056`, PR #147) | P31.11 | the named tests exist (`tests/resolution/test_camera_sites.py`, `tests/db/test_camera_site_human_decisions.py`); the rule is test-based | **yes** (engineered, as the rule asks) |
| 2 | D-P27.5-1 | 2026-10-03 (`be7bab69`) | 2026-09-26T14:29–14:33Z (PR #151) | P31.14 (+P31.16 publish 09-27) | export emits `web/analytics/`; public since P31.16 | **yes** |
| 3 | D-P31.1-1 | 2026-10-11, stamped 10-14 | 2026-09-27T06:41Z (PR #159); stamp 2026-09-27T08:37Z | P32.4 | **live `/v1/contradiction` 13.559 s / 13.566 s warm (rule: < ~1 s, 8 concurrent without queueing)**; `sig-api` runs `40a47da8…` (2026-09-25), which predates P32.4 | **no**: engineered only; the live leg is owed (NEW-2) |
| 4 | D-P31.1-3 | 2026-09-28, stamped 10-14 | 2026-09-27T04:16Z (PR #157) | P31.8 registry half (09-25, live) + P32.2 route half | live OKC entity `/v1/entity/deployment/01a0a5da-…` → **200** in 0.36 s | **yes** on its rule; the P32.2 route generalisation is not deployed (note only) |
| 5 | D-P31.5-2 | 2026-10-12, stamped 10-14 | 2026-09-27T07:17Z (PR #160) | P32.5 (ADR-124: enforce, not moot) | **live `/v1/search?q=Vigilant` → label "Vigilant Solutions (LEARN)"**: the flagged organisation is still labelled on the served spine | **no**: engineered only; the live leg is owed (NEW-3); activation needs the ADR-124 allows first (NEW-4) |
| 6 | D-P30.1-2 | 2026-09-25 + stamp 10-21 | 2026-09-25T01:58Z (`71f1daa8`); stamp 2026-09-28T05:13Z | P31.4 | hosted slice resume recorded (15 fetches for 30 pages, +0) | **yes** |
| 7 | D-P30.2a-1 | 2026-09-25 + stamp 10-21 | 2026-09-25 (P31.8); stamp 09-28T05:13Z | P31.8 | hosted materialize +13,131 then +0 recorded | **yes** |
| 8 | D-P30.2a-2 | 2026-09-25 + stamp 10-21 | 2026-09-25T08:09Z (`062306e7`) | P31.7 | hosted +232,096 links recorded; batch-05 was excluded and still runs `feff986c`, without re-sightings (disclosed in the cell; G1 §3.3) | **yes** (with that disclosed exclusion) |
| 9 | D-P30.3-1 | 2026-09-27 + stamp 10-21 | 2026-09-27 (P31.16); stamp 09-28T05:13Z | P31.2 + P31.16 | live `/data-freshness/` 200 with 724 ISO date strings; the site content is frozen at 09-27 (F-08) | **yes** |
| 10 | D-P30.3-2 | 2026-09-27 + stamp 10-21 | 2026-09-27 (P31.16) | P31.15 + P31.16 | live `/map/points.json` → **404** | **yes** |
| 11 | D-P30.3-3 | 2026-09-27 + stamp 10-21 | 2026-09-27 (P31.16) | P31.14 + P31.16 | analytics render; F-05 (site-wide totals on every page) is a separate S1 truth finding | **yes** on its rule |
| 12 | D-P31.1-2 | 2026-09-25 + stamp 10-21 | 2026-09-25T01:58Z (P31.4) | P31.4 | probe sweep `2026-09-30T12-03-01`: `sig-api-health` ok=True. The sweep is red on the okc/france manifest targets (G1-02), not on this one | **yes** |
| 13 | D-P31.3-1 | 2026-09-25 + stamp 10-21 | 2026-09-25T01:58Z (P31.4) | P31.4 | `runs/P31.4.md:181` records 179,882 claims/min, +0 re-run | **yes** |

**Recommendation for T4.**
- Append a dated correction line to each of the 13 rows with the true date: the `true date` column above, or the
  P33.1/P32.7 commit time for the stamps. Also append the e1 transition events (B2 §5.1).
- For rows 3 and 5, append **"DONE (engineered) — live leg owed: hosted API runs a pre-P32 image; closes on Round-10
  API activation"**. Do not re-open them as OPEN, because the engineering is done. Record the owed live leg in the
  activation ticket (§6, step 4a).

---

## 6. Round-11 order for the owed register (dependency-ordered)

Legend: **[no-recruit]** = in reach without new human recruiting. **[go]** = needs a per-action operator go
(production).

**Step 0: Stage-B register repair (T4). [no-recruit]**
- Append the §4 and §5 corrections and annotations.
- Add the ADR-124 `allow` row (NEW-4).
- Record the operator's answers to E4 R1/R2/S1–S5 and to the D-P21.7-1/D-R7.1-AUTH later-phase proposals.
- Put the D-P31.4-1 clock guard into OPERATING MODE (B1 NEW-4).

**Step 1: scheduled read-backs, read-only (any session). [no-recruit]**
- **2026-10-01 05:00Z, `sam_gov`.** Expect the same starvation (NEW-1).
- **2026-10-01 06:00Z, `muckrock`.** First fire (NEW-7).
- **2026-10-10 03:35Z, batch-05.** This is **D-P31.4-1**. Read back only after `date -u` passes the fire time *and*
  `lastAttemptTime` is set. Follow the G1 §3.7 watch plan.

**Step 2: R11 wave 1, engineering only. [no-recruit]** These run in parallel.
- **2a. D-FEDERAL.1-1.** Persist the sweep cursor, set the budget to the measured quota, and apply cron `0 5 * * 1`
  live **[go]**. The row closes after two weekly fires, about 2 weeks.
- **2b. D-P32.10a-1 + D-P32.16a-1.** Sqitch hygiene, plus a full `verify`/`revert` CI job. This is a
  **prerequisite for any hosted deploy of L44–52**.
- **2c. D-R10-MEMORY-1.** Repair the event log (append-only corrections plus a date guard; B2/B3/B4). Then cut over
  at an operator-approved boundary.
- **2d. D-R10-SOURCES-1 prep.**
  - Reconcile the dossier URLs (E4 NEW-7).
  - Fix the pilot return pass (E4 NEW-8).
  - Draft the Part VIII screens and the 3 pilot registry rows (B6).
  - Capture the BidNet terms (R6a).
- **2e. B1 date-constant fix.** Fix `release_candidate.py` and the dossier packet dates. This is a prerequisite for
  D-P32.23a-1 and for the dossier rebuilds.
- **2f.** Not an owed row, but it gates the human spine: a reviewer UI and a credentialed import (E3 NEW-2).
- **Alongside:** the operator-approved ops-safety tickets (G1 QA-1 deletion protection, QA-9 restore drill,
  QA-3/4/5 alerts to the operator's address). They gate step 4.

**Step 3: operator decisions, one line each (E4 table; E3 R9 ≈ 6.5–26 h including reading). [no-recruit]**
- **Inputs:**
  - R1–R6, B1–B6, S1–S5.
  - The SWH ack (D-P21.5-1).
  - Q-27/Q-29 (intake).
  - Q-E3-10 (records filer).
  - Q-9 (what ships).
  - Q-12 (supersede `p-17b713`).
- **Outputs:**
  - **One R11 rights-flip batch ticket** covering D-SOURCES.7-1, 8-1, 9-1 and 9-4, using the E4 §2 recipe, not a
    bare flip (E4 NEW-11).
  - **live-return-pass(P21.5)** for SWH **[go]**.
  - Three rows become WONTFIX and three become later-phase.

**Step 4: production activation chain (critical path). [no-recruit] [go]**
- **4a. Round-10 API and schema deploy.**
  - **First**, the operator records the ADR-124 `allow` dispositions (NEW-4).
  - Then deploy sqitch L44–52 and the Round-10 API to hosted. This depends on 2b and on the ops-safety wave.
  - That closes the live legs of **D-P31.1-1** and **D-P31.5-2**.
- **4b. D-R10-LIVE-1.** Run P32.22 live: hosted audit → plan → bounded apply → freeze. This depends on 4a, 2e and the
  restore drill.
- **4c. D-P32.23a-1.** Build a new hosted candidate with the corrected constants; `p-17b713` is superseded.
- **4d. D-P32.18/19/20/21-1.** Run the live dossier and pilot return passes, in parallel with 4b. This depends on
  step 3's B-decisions and on 2d/2e.
- **4e. D-R10-PUBLISH-1.** Hold a candidate-specific operator readout (HG-11), then run P32.25 live over 4c's
  candidate. The intake half follows D-P32.16-1.

**Step 5: operator-fillable human work (E3 §6). [no-recruit]**

| row | work | effort | ordering |
|---|---|---|---|
| D-P32.3-1 | an R11 read-only hosted `partner-name-audit` sizes N, then the operator records dispositions | 1.7–42 h | may need the P32.3 schema on hosted, so after 4a |
| D-P30.2b-1 | the operator curates 50–100 seed items, then an R11 hosted verify leg runs | 2–8 h | — |
| D-P32.16-1 | owner, retention, SLAs, alias; the receiver deploys with 4e | 4–8 h + 2–4 h/week | the `/dispute/` honesty fix (F-03) comes first and is independent |
| D-R7.2-SEND | the operator acts as filer, if they choose | 1–4 h per request | — |
| D-SOURCES.7-2 / 8-2 | key registration, then an R11 wiring ticket | — | weigh against Stream I |

**Step 6: only if Q-28 authorises recruiting.**
- `D-R10-HUMAN-1`: rows 184 → 185 → 186 → 187, per F4.
- Then `D-R6.1-EVAL` and `D-P30.2b-2`, then a *final* candidate (a second pass of 4c/4e).
- `D-R10-USERS-1`.
- E3 estimates 145–375 h over 3–5 months, $0–25k. None of this is on the critical path of steps 0–5.

**What Round 11 can close without recruiting.** Up to **32 of 36** rows:
- **10 need only engineering, schedule or an operator go:** 2 already-done, 4 engineering tickets, D-P31.4-1,
  D-P21.5-1, D-R10-LIVE-1 and D-P32.23a-1.
- **22 need operator decisions or operator time:**
  - 11 rights rows: 4 flip tickets, 2 wontfix, D-R10-SOURCES-1, and 4 dossier/pilot passes after the B-decisions.
  - D-JURIS.2-1 (wontfix).
  - 3 later-phase rows.
  - 6 other operator-actions: D-SOURCES.7-2, D-SOURCES.8-2, D-R7.2-SEND, D-P30.2b-1, D-P32.3-1, D-P32.16-1.
  - D-R10-PUBLISH-1.

**The operator's decisions and production gos, not labour, set the pace.** On E3's own estimates the operator time
for the in-reach set is dominated by partner identity (up to 42 h) and rights review (up to 26 h); that range is an
inference from E3.

---

## 7. Register completeness notes (outside the 36, needed by S1/T4)

- **NEW-4.** The ADR-124 `allow` dispositions are an owed operator act with no row. They are sequencing-critical for
  step 4a.
- **Live legs owed by two closed rows.** D-P31.1-1 and D-P31.5-2 (§5); annotate them, do not re-open them.
- **Already filed by other rows** (not re-filed here):
  - Owed human legs with no DEFERRALS row: E3 NEW-4 (counsel: SIG-LIC-009, SIG-INGEST-037, EU DB right) and
    F2b NEW-6 (the hostile-reader review, among others).
  - HG-05/go-public tag with no row: A3 NEW-3.
  - The GATE-G3 signature bound to a withdrawn artifact: B1 NEW-2, which bears on D-R10-PUBLISH-1.
- **D-P31.4-1.** The pinned image lacks P31.7 re-sighting recording (G1 §3.3, inference). The 10-10 read-back should
  disclose this. It is not a new owed row.

---

## 8. Findings filed (`findings/incoming/F1.csv`)

| id | sev | title (short) | routed to |
|---|---|---|---|
| NEW-1 | S2 | SAM.gov sweep restarts at keyword 0; the tail is never fetched, so D-FEDERAL.1-1 cannot close on schedule | S1 → R11 ticket |
| NEW-2 | S2 | D-P31.1-1 is DONE, but its verify rule fails live (13.6 s) | T4 + G2 |
| NEW-3 | S2 | D-P31.5-2 is DONE, but the live API labels a flagged partner org | T4 + G2 |
| NEW-4 | S2 | The ADR-124 `allow` dispositions have no owed row, and activation would regress the public vendor names | S1 + G2 |
| NEW-5 | S3 | D-P21.3-2 is discharged by hosted jobs, yet OPEN on an obsolete blocker | T4 |
| NEW-6 | S3 | 12 of 36 owed rows carry the wrong blocker class | S1 + T4 |
| NEW-7 | S3 | MuckRock hosted ingest has produced 0 claims (API challenge), and no owed row tracks it; first fire 10-01 | G1 watch + Stream I |
| NEW-8 | S3 | The §(f3) D-P21.7-1 return-pass path points to a non-existent file | T4 |

Not re-filed, because another row already covers them: E4 NEW-1/2/3/4/7/8/9/11, E1 NEW-14 (repo public), G1 NEW-9
(the live cron's OR semantics), B1 NEW-2/3/4/7 and B2 NEW-2/3.

---

## 9. Command log (all read-only; `date -u` times; project `zeta-medley-508121-u7`)

| time (UTC) | command (abridged) | used for |
|---|---|---|
| 17:22:24 | `date -u`; `git log` on the planning branch and on `DEFERRALS.md` since 2026-09-28 | §1, §3 |
| 17:2x | `grep -n '^\| <id> ' docs/tickets/DEFERRALS.md` for the 36 owed + 13 closed rows (to scratch) | §2, §5 |
| 17:24:44 | `gcloud scheduler jobs describe sig-sched-sam-gov / sig-sched-camreg-batch-05` | D-FEDERAL.1-1, D-P31.4-1 |
| 17:25 | `gcloud storage ls/cat …/ops/runs/sam_gov/**` (2 rows, metadata fields only) | NEW-1 |
| 17:25 | `gcloud run jobs describe sig-ingest-camreg-batch-05`; `executions list`; `storage ls …/camreg_osm_surveillance/` | D-P31.4-1 |
| 17:25 | `sed`/`grep` of `procurement.py:830-910,1396-1405,2093-2100`, `runner.py:950-990`, `procurement_vocab.toml:603-640`, `ops/cadence.toml:305-325` | NEW-1, D-SOURCES.9-2 |
| 17:25 | `uv run sig-connectors gate --source <id>` × 18 | rights rows |
| 17:26:08 | `gh repo view --json visibility,nameWithOwner`; `gcloud secrets list` (names only); `storage ls …/ops/probes/` | D-P21.5-1, keys, D-P31.1-2 |
| 17:26 | `gcloud storage cat …/ops/probes/2026-09-30/2026-09-30T12-03-01+00-00.jsonl` | D-P31.1-2 |
| 17:26:37 | `curl` the API: `/v1/search?q=Vigilant`, `/v1/entity/deployment/01a0a5da-…`, `/v1/contradiction` ×2 (timed), `/health`, `/openapi.json`; `gcloud run services describe sig-api` | NEW-2, NEW-3, D-P31.1-3 |
| 17:27:17 | `curl` the site: `/map/points.json`, `/intake/`, `/intake/new`, `/releases/`, `/research-dossier/`, `/dispute/`, `/data-freshness/` | §3, §5 |
| 17:28 | `sed` of `db/verify/shared_temporal_contract.sql:25-32`, `db/revert/extensions.sql`, `ops/config.toml` flags, `tasks/detect.py:258-266`; `obligation_events.py check`; `current_projection.py verify`; return-pass JSON status × 7; readouts HUMAN-H4/H5 | engineering + human rows |
| 17:30 | `gcloud run jobs list` (grep recover/audit/candidate/release/eval/intake/freeze → none) | D-R10-LIVE-1 |
| 17:31 | `gcloud scheduler jobs list` (muckrock/civicclerk/overpass/congress/fbi); latest run rows for `civicclerk`, `osm_overpass`, `congress_gov`; `executions list sig-ingest-muckrock`; retry-artifact counts | D-P21.3-2, D-SOURCES.12-1, NEW-7 |
| 17:33 | `sed -n 105,130p docs/adr/ADR-124-one-publication-eligibility-policy.md` | NEW-4 |
| 17:35:22 | `date -u` (CSV generation) | outputs |

No secret value was read or copied. Only the Secret Manager *names* were listed (P14).
