# B1 — Date-drift forensics and correction design

Row **B1** of `META_PLAN.md` (Stage P, stream B). **Design only: no date was changed anywhere.** Worker run
2026-09-30T16:38:44Z → 17:08:37Z (`date -u`). The scan covers chain tip `b051732c`
(`devin/p33-8-agent-docs-refresh`); every file this row reads is byte-identical in the planning worktree (BASELINE.md, C07).
Outputs:

- `data/date_drift.csv`: 1,051 rows covering 2,891 dated occurrences, each classified and given a fix mechanism.
- `findings/incoming/B1.csv`: NEW-1 … NEW-7.
- Scratch, scripts and raw captures: `docs/build/logs/next-phase/B1/` (gitignored). See §10.

Evidence classes (P1) are `code` for git, blame and file reads; `recorded-execution` for run ledgers and PR
bodies; `live-read` for gcloud reads, marked **(L)**; `inference`, marked **(I)**. Dates come only from git committer time,
GitHub PR `createdAt`, or `date -u` (P2). The repo mixes EDT (-04:00) and UTC, so "local" means -04:00. The hosted
database was **not** queried, because no read-only path to it exists (§5.7, Q-B1-1).

---

## 1. Summary

| | rows | occurrences |
|---|---:|---:|
| **(a) not an event-date error**: scheduled, real-world, synthetic test value or illustrative | 456 | 608 |
| **(b) event recorded on a date it did not happen** | 595 | 2,283 |

| artifact_kind | (b) rows | (b) occurrences | (a) rows | fix mechanism for (b) |
|---|---:|---:|---:|---|
| memory (LEDGER, BUILD_INDEX, runs, pr, readouts, DEFERRALS, manifest, closure/readiness, COVERAGE_MATRIX, reports/current, tools) | 322 | 528 | 125 | append-only CORRECTION entries; regenerate the projection |
| fixture (test pins, committed fixture-run outputs, fixture provenance) | 56 | 935 | 207 | update pins with the code fix; keep historical outputs and append CORRECTION.md |
| release-identity (P32.23a candidate + P32.25 staging/rehearsal copies) | 75 | 493 | 6 | never edit; supersede (§5.8) |
| jsonl (`obligations/events.jsonl`, `coverage_assessments.jsonl`) | 6 | 187 | 1 | append `date-correction` events |
| code (ops/web/connectors constants, registry data) | 70 | 71 | 52 | constant fix + regression test |
| adr (`Date:` headers + body mentions) | 33 | 33 | 10 | appended correction footer + correction ADR table |
| spec (§55, App F/G, generated spec, six-streams `render_plan.py`) | 15 | 18 | 55 | spec_src amendment + new App-G row |
| sqitch (`db/sqitch.plan`) | 18 | 18 | 0 | never edit (§5.7) |

- **The correction table (§3) has 37 rows.** 35 are wrong-dated events or event groups (the Round-3 session is one
  group of 15 PHASE LOG entries), 1 is the propagation of the S3/G3 date into later correctly dated records, and 1 is the
  fabricated dossier "replay" label. Every (b) row in the CSV maps to one of them or to its writing commit.
- **Deployed or signed (b) rows: 94**:
  - 75 release-identity rows;
  - 7 code lines that feed or pin the candidate identity;
  - 3 hosted-deployed sqitch lines with future dates, plus 6 hosted-deployed lines with same-day timestamps;
  - 3 lines in signed readouts (GATE-G3 ×2, ACCEPT-R10 ×1).

  Nine more sqitch rows (L44–52) are `unknown`: undeployed per the run ledgers, but the hosted database was not queried.
- **Sqitch:** the planned timestamp is hashed into each change id, and through `parent` into every later id. Lines 41–43
  are deployed on hosted `sig-pg` and must never be edited. Lines 44–52 are, per the record, undeployed; they are left
  unedited by default and corrected through comments and the ADR.
- **Candidate identity:** `p-17b713…` embeds 2026-10-19 in three places: its publication id (`sha256(descriptor.json)`),
  its release id / as-of, and its `identity_digest`. **Recommendation: supersede it and do not re-sign it.** It holds 0
  records (F-15) and was only ever "published" to a repo folder. The next real candidate is built with true dates and gets
  a fresh GATE-G3 signature from the operator (§5.8).
- **Cause:** the agents kept a *chain date* separate from the machine clock, and said so in the record. Round 3 ran
  3 days behind; Round 9–10 ratcheted forward by "previous entry + 1 day", and in places jumped ahead. The memory
  tooling takes hand-typed dates with format-only validation (§6).

## 2. Method

1. **Blame scan.** `git grep` found 2,283 tracked files containing a date of 2026 or later. Each was run through
   `git blame -w --line-porcelain b051732c`, and every ISO date occurrence was compared with the committer time of the
   commit that last wrote that line. A date is flagged when it is later than both the UTC and the local date of that
   commit, or later than 2026-09-30. Timestamps within the same day are flagged when they run more than 1 h ahead. This
   gave 2,806 flagged occurrences. Blame gives the *last* writer, so the true event is at or before that commit.
2. **Backward scan.** Every line written by the Round-3 session (commits `eb72be5f^..759fcbac`, 2026-09-13) that carries
   2026-09-10…12 was checked, plus the P25 BUILD_INDEX rows: 87 rows. LEDGER PHASE LOG entry dates (193 entries) and
   BUILD_INDEX `landed` cells (rows 47–200) were compared with blame and PR `createdAt`. Every ADR `Date:` header was
   compared with its adding commit (`git log --diff-filter=A`).
3. **Classification** (`classify.py`) is per occurrence, using ±200 characters of context. True dates come from the
   nearest adjacent ticket token (PR `createdAt`, else the closeout commit), from named decision commits, or from the
   writing commit as an upper bound (`<=`). Two scanner false positives were dropped: window strings in
   `p31.11-hosted/camera_site_run.json` that parse as timezone offsets.
4. **Limits.** Dates written as prose were checked separately; only "October 1, 2026" (OKC) exists. Differences of ±1
   day explained by EDT/UTC are not flagged. Rule classification was spot-checked on a random sample of 25 rows plus
   every row with an unmapped true date. Residual misclassification risk is low but not zero (I).

## 3. The wrong events and their true dates (the correction table)

Each true date is the latest time at which the event can have happened: the commit that recorded it, or the PR
`createdAt`. Operator decisions may have been spoken earlier. "≤" marks cases where only that upper bound is known.

| # | event (as recorded) | recorded | true (UTC) | evidence |
|---|---|---|---|---|
| 1 | P21.3 ADR-065 `Date:` | 2026-09-10 | 2026-09-09T06:12Z | `305f94d5`; PR #59 06:13Z |
| 2 | Round-3 session: P23.1–P23.4 markers, P21.1/.3/.4/.5/.7/.8(+.9) re-runs, P23.5, P23.6, P24.1, P24.2; readouts GATE-G1/G2, HUMAN-H1–H3; ADR-074/076; 21 `sources.toml` rights fields | 2026-09-10 | 2026-09-13T19:40Z–22:10Z | `eb72be5f`…`759fcbac`; `runs/P21.5.md:23` |
| 3 | P25.1 / P25.3 landed (BUILD_INDEX rows 88, 90) | 2026-09-14 | 2026-09-15T17:28Z / 19:11Z | `8670a4da`/`38841865`; LEDGER PHASE LOG 392/396 say 09-15 |
| 4 | P25.5 fixtures "added" (ccops/pathways `SOURCES.md`) | 2026-09-17 | 2026-09-16T02:04Z | `7b52f2b4` (local 09-15 22:04) |
| 5 | P27.3 run-ledger entries | 2026-09-23 | 2026-09-22T20:25Z | PR #114 |
| 6 | P31.6 ADR-113 + `p31.6-hosted/inventory_before.json` | 2026-09-26 | 2026-09-25T06:32Z | `184e3644` |
| 7 | P31.7 ADR-114; sqitch `resolution_supersede` | 2026-10-02 | 2026-09-25T08:09Z | `062306e7`; PR #143 11:56Z |
| 8 | P31.10 landed; sqitch `review_campaign` | 2026-10-02 | 2026-09-25T22:11–22:18Z | `b884ae73`; PR #146 |
| 9 | P31.11 ADR-116; sqitch `camera_site_human_decisions` | 2026-10-02 | 2026-09-25T23:21Z | `4608f056`; PR #147 |
| 10 | P31.14 landed; ADR-117 | 2026-10-03 | 2026-09-26T14:29–14:33Z | PR #151 |
| 11 | P31.15 landed / ADR-118 / ACCEPT-R8 R8-1 note | 2026-10-03 / 10-05 | 2026-09-26T15:16Z | PR #152 |
| 12 | P32.2 landed; ADR-121; sqitch `claim_assertion_bindings` | 2026-09-28 / 10-03 | 2026-09-27T04:16Z | PR #157 |
| 13–20 | P32.3, .4, .5, .6, .7, .8, .9, .10 landed + ADR-122…129 + sqitch lines 45–48 | 10-10, 10-11, 10-12, 10-13, 10-14, 10-15, 10-16, 10-18 | 2026-09-27T05:27Z, 06:41Z, 07:17Z, 08:06Z, 08:37Z, 09:11Z, 09:51Z, 10:12Z | PRs #158–#165 |
| 21–26 | P32.15, .16, .16a, .17, .18, .19 landed + ADR-134…138 + sqitch 50–51 | 10-04, 10-18, 10-19, 10-02, 10-02, 10-01 | 2026-09-27T14:13Z, 15:05Z, 15:58Z, 16:35Z, 17:31Z, 17:56Z | PRs #171–#176 |
| 27 | P32.22 sqitch `recovery_apply` | 2026-10-19T21:00Z | 2026-09-27T20:03Z | `2404edb0`; PR #179 (its BUILD_INDEX row correctly says 09-27) |
| 28 | Orchestrator pause at HUMAN-H4 | 2026-10-19 | 2026-09-27T20:07Z | `c4aafa20` |
| 29 | **Operator defers the S3 human-evaluation spine** | 2026-10-19 | **≤ 2026-09-28T01:27Z** (local 09-27 21:27) | `a33cd6ec` |
| 30 | P32.23a landed; candidate built with as-of 2026-10-19; ADR-142 | 2026-10-19 | 2026-09-28T02:11Z | `9bf11201`; PR #180 |
| 31 | P32.24 landed; ADR-143 | 2026-10-20 | 2026-09-28T03:08Z | PR #181 |
| 32 | Orchestrator pause at GATE-G3 | 2026-10-19 | 2026-09-28T03:09Z | `e4be1b84` |
| 33 | **GATE-G3 signed** ("Date: 2026-10-19") | 2026-10-19 | **≤ 2026-09-28T03:49Z** (local 09-27 23:49) | `95c8a73f` |
| 34 | P32.25 landed; ADR-144 | 2026-10-20 | 2026-09-28T04:36Z | PR #182 |
| 35 | P33.1 landed + reconciliation cells "DONE 2026-10-21" + all 97 `events.jsonl` `recorded_at` | 2026-10-21 | 2026-09-28T05:13–05:19Z | `7a2ff9fa`/`08b3135f`; PR #183 |
| 36 | Propagation: P33.2–P33.8 (correctly dated 09-28) copied #29/#33's date into §55, App F/G, ADR-145, CAPSTONE_*, OPERATIONAL_READINESS, ACCEPT-R10, `render_plan.py` | 2026-10-19 | as #29 / #33 | `71e8bc83`, `e8bc0179`, `4127dbf3`, `c77bd45e` |
| 37 | Dossier "replay" retrieval/observation/search/generation dates (packets, web fixture, candidate) | 2026-10-01 / 10-02 | **no such event**: stand-ins authored 2026-09-27T12:06Z | `f73a997e`; `tests/connectors/fixtures/dossier/SOURCES.md:10` |

The Round 9–10 correct-date tickets were P31.8, P31.9, P31.12, P31.13, P31.16, P31.19, P32.1, P32.10a–P32.14, P32.20–P32.22
and P33.2–P33.8 (BUILD_INDEX compared with PR `createdAt`).

## 4. Class (a): legitimately future or not an event claim (456 rows)

- **Scheduled (122 rows).**
  - The D-P31.4-1 OSM replay. **(L)** At 16:59:38Z, `gcloud scheduler jobs describe sig-sched-camreg-batch-05` returned
    `35 3 10 * *` Etc/UTC, ENABLED, no `lastAttemptTime`, `scheduleTime 2026-10-10T03:35:00Z`.
  - The gate-Q4 deadline 2026-10-08.
  - The muckrock scheduler's next run, 2026-10-01T06:00Z (P25.7), and P26.15's next scheduled run, 2026-10-05.
  - The SAM.gov quota reset (2026-09-19 00:00Z) and P26.12/P26.16 fire times and deadlines.
  - §55 SIG-TRUST-008 ("reserved 2026-10-10 replay") is correct as written.
- **Real-world (209 rows).**
  - The OKC 30→7-day retention **effective 2026-10-01**. It was reported by the S2 research pass (`d6c562e5`,
    `S2-local-dossiers.md:21`) and not reconfirmed: HTTP 403 in `reviews/source-plan-review.md:56`. It is a
    document-stated fact, kept as `valid_from`, and is not a drift.
  - Contract expiries and terms (2027-06-30, 2027-04-02, 2028-05-01, …), statutes (VA reports due 2027-04-01), EOLs,
    fiscal periods and OpenStates session end dates.
- **Synthetic test values (105 rows).** Arbitrary timestamps in tests, for example `POST = "2026-10-01T00:00:00Z"`,
  review votes dated 10-01…10-03, and `as_of="2026-10-19"` in `tests/db/test_release_candidate.py`.
  - 58 of these copy the chain's believed date. They are harmless as test data, but they leak into signed
    artifacts: the P32.6 fixture-spine POST timestamp shows up as the watermark `max_bound_at 2026-10-01` inside
    `CANDIDATE_MANIFEST.json`.
  - B4 should require that synthetic future timestamps are marked as synthetic.
- **Illustrative (20 rows).** Spec and research examples from the original spec commit `a33177c7`, and the web
  editorial copy of the spec's "expires 2026-09-30" example.

## 5. Class (b): fix mechanism by artifact kind

### 5.1 Memory (322 rows)
- **Never edit the recorded line** (P7; AGENTS.md "append"). Add one dated **DATE CORRECTION** entry, with the real
  `date -u`, to each control file that carries wrong dates:
  - LEDGER PHASE LOG and GATE DECISIONS: one entry listing each affected entry's line and recorded value → true date → evidence.
  - BUILD_INDEX: an appended `## Corrections` table (rows 67–80, 88, 90, 151, 155, 156, 162–170 (the P32.10 row),
    175–180, 188, 189, 191, 192).
  - DEFERRALS: an appended correction section, not cell edits. The cells' leading tokens are derived from the event
    chain (ADR-126), and editing a cell rewrites history.
  - The manifest plan extension, readouts (as addenda), `runs/*.md` and `pr/*.md` (addenda) and CAPSTONE_*.
- The **correction register** is `data/date_drift.csv`. Stage T should promote it, with a stable name, under `reports/`
  (the layout forbids new root entries; B3 decides the location).
- `reports/current/*` is a derived projection. Regenerate it after the corrections exist as events (§5.6); never hand-edit it.
- The LEDGER CURRENT STATE / PRIOR chains (L34, L35, L52 carry 60+ wrong dates) are replaced by B3's LEDGER rewrite.
  The archived PRIOR chains go into the archive with a pointer to the correction register.
- Signed readouts (GATE-G3 L10/L23, ACCEPT-R10 L17) get an **agent-drafted addendum the operator confirms** (P4/F-29).
  The signed text itself is never touched.
- The Round-3 past dates (2026-09-10 → 09-13) use the same mechanism.

### 5.2 ADRs (33 rows)
- 22 Round-9/10 `Date:` headers, 8 body mentions (ADR-138 replay label ×2, ADR-142 ×2, ADR-143, ADR-144, ADR-145 ×2),
  ADR-065 (+1 day) and ADR-074/076 (Round-3 past-dated): 33 rows.
- Mechanism: append a one-line `> Date correction (2026-MM-DD, ADR-<corr>): recorded Date X; landed <true UTC>
  (<commit/PR>)` footer. This is an append, not a body rewrite (SIG-ENG-003).
- The correction ADR (§8) carries the full table.
- `docs/adr/README.md` has no date column, so it needs no regeneration.

### 5.3 Spec (15 rows)
- **Normative landed-status text** in `spec_src/96b_partXI_s55_six_streams.md`:
  - L13 "deferred wholesale on 2026-10-19";
  - L105 "GATE-G3 signature (2026-10-19)";
  - L117 ×2.
- **Appendix rows:**
  - App G `99c_appG_corrections.md:187` (R10-A6);
  - App F `99a_appF_adr.md:168` (ADR-145) and `:161` (ADR-138, replay label);
  - the generated `docs/2_canonical_design_spec.md` mirrors (7285, 7377, 7389, 9166, 9173, 9361).
- Mechanism: a Stage-T spec_src amendment through `BUILD.sh`. The §55 text is corrected to true dates, citing the
  correction ADR. App G is append-only, so add a **new R11-Ax row** ("R10-A6's dates corrected; see ADR-<corr>")
  instead of editing R10-A6. Regenerate the spec.
- `docs/build/planning/2026-09-25-six-streams/tools/render_plan.py:102/107/121` re-emits the same §55 text. Fix it or mark
  it historical; `BUILD.sh` does not call it (`git grep`).

### 5.4 Code (70 rows): constant fix plus regression test
| file:line | value | fix |
|---|---|---|
| `ops/src/ops/release_candidate.py:7,103,112,125` (`EVAL_DEFERRAL_NOTE`, `EVAL_DISCLOSURE`, `DEFAULT_NOTE`, docstring) | "2026-10-19 operator choice…" | Reference the recorded decision by id ("S3 deferral, GATE DECISIONS, `a33cd6ec`") or carry the true UTC date. **Changing these changes every future `identity_digest`, which is intended.** Couple the change with §5.8. |
| `ops/src/ops/journey_verify.py:792,1425,1874`; `ops/src/ops/cli.py:877` | "(2026-10-19)" | same |
| `ops/src/ops/release_publish_verify.py:94-96` | `DATA_RELEASE_ID="sig-2026-10-19-518afbaf"`, `AS_OF_*="2026-10-19"` | These pin the signed candidate. Replace them with values read from the candidate's manifest, and only as part of the §5.8 decision. |
| `ops/src/ops/tulsa_dossier_packet.py:86-88`, `san_diego_dossier_packet.py:104-106` (`_REPLAY_DATE`, `AS_OF_*` = 2026-10-01); `dossier_packet.py:69-70` (`AS_OF_*` = 2026-10-02) + comments/strings | fixture "retrieval" dates | `retrieved_at`/`observed_at`/`searched_at` equal the fixture's real authoring commit date, or carry an explicit `capture_kind: stand-in` field with no retrieval date. Require `as_of ≤ build date`. The OKC "announced vs operative" scenario becomes an explicit `scenario_as_of`, never a capture date. |
| `web/src/lib/research-dossier-fixture.ts` (17 lines) | `retrieved_date/searched_at/as_of` 2026-10-01 | same; update `web/tests/e2e/research-dossier.nojs.spec.ts:48` |
| `connectors/src/connectors/data/sources.toml` (21 lines: `rights_reviewed_on`, `last_verified`, `retrieval_date`, FLIPPED notes) | 2026-09-10 | A registry data correction in a new commit: verification/flip date 2026-09-13 (`e1cedcad`). GL-GATE-03 authority stays 2026-09-09. Do not re-flip anything (HG-03 unaffected). |

Regression tests (B4 to finalise):
1. An AST/regex test over `ops/src`, `exports/src`, `web/src` and `connectors/src` fails on any date literal later than
   the HEAD commit date, unless it sits in an allow-listed real-world field (`valid_from`, `expiry_date`, `end_date`, …)
   or carries a `# future-ok: <reason>` marker.
2. Packet builders assert `retrieved_at ≤ fixture commit time` and `as_of ≤ build time`.
3. The release candidate asserts that its notes contain no hand-typed dates.

### 5.5 Fixtures (56 rows)
- **23 test pins** move together with §5.4 (`tests/ops/test_{okc,tulsa,san_diego}_dossier_packet.py`,
  `tests/exports/test_research_dossier.py`, `tests/ops/test_release_candidate_orchestration.py:55`,
  `tests/ops/test_journey_verify.py:142`).
- **28 committed fixture-run outputs** (`reports/p32.18-`, `p32.19-`, `p32.20-` packets, `p32.24` portfolio) are historical run evidence.
  Keep their bytes, append a `CORRECTION.md` in each directory, and regenerate them as new superseding artifacts after
  the code fix. Their digests are cited by later tickets.
- 5 provenance or comment lines (P25.5 `SOURCES.md`, Round-3 test comments) get correction lines.

### 5.6 JSONL (6 rows, 187 occurrences)
- `events.jsonl`: all 97 lines were written by `7a2ff9fa` (2026-09-28T05:13:58Z) with `recorded_at 2026-10-21`, and 82
  also carry `observed_at 2026-10-21`. Lines 76/82 carry `observed_at` 10-11/10-12 (P32.4/P32.5).
- `coverage_assessments.jsonl`: 4 lines with `assessed_at 2026-10-14`, whose true date is 2026-09-27T08:37Z.
- Mechanism: **append** `date-correction` events. Use a new `kind` or a `reason: date-correction` on a no-op
  transition, citing `event_id`, recorded value and true value. **Never run `migrate` again** (F-26).
- Tool changes (B4):
  - `--recorded-at` defaults to `date -u`;
  - reject any date later than today or than the source commit;
  - reject `recorded_at` earlier than the previous event on the same chain, except for correction events.

### 5.7 Sqitch (`db/sqitch.plan`, 18 rows)
**How change ids work.** Source: `sqitchers/sqitch@develop` `b08e5c8a` (2026-09-26), fetched 2026-09-30 into
`logs/next-phase/B1/`.
- `App::Sqitch::Plan::Change` L110-144 builds `info` from `project`, `uri`, `change`, `parent <prev id>`, `planner`,
  `date <planned timestamp>`, requires/conflicts and note. The id is `SHA-1("change <len>\0" . info)`.
- `Plan.pm` L450-455 sets `parent => $prev_change`, so **a timestamp edit changes that change's id and every later id.**
- Standalone `#` lines parse as `Plan::Blank` (Plan.pm L196-197/L272-274). They belong to no change and **do not
  affect any id.**
- `Engine::_sync_plan` (L983-996) does `$plan->index_of($state->{change_id}) // hurl 'Cannot find change {id} ({change})
  in {file}'`.

**What is deployed on hosted** (recorded-execution; the database was not queried):
- L41 `resolution_supersede` (10-02T12): `runs/P31.7.md:75`, `reports/p31.7-hosted/VERIFICATION.md:24-26`.
- L42 `review_campaign` (10-02T13): `runs/P31.10.md:111-112`, "the only pending change".
- L43 `camera_site_human_decisions` (10-02T19): `runs/P31.11.md:168-169`.
- L27–L40 were all deployed before P31.10, which applied `review_campaign` as "the only pending change". Six of them
  (L27, L28, L33, L34, L39, L40) have same-day hand-written planned times a few hours after their commits; Claude-trailered
  commits wrote these.
- L44–52 (P32.2–P32.22) record `live_verification=false`, and Round 10 is not deployed (F-14). They are **very likely
  undeployed on hosted**; unverified (Q-B1-1).
- The three deployed changes' `planned_at` values are stored in hosted `sqitch.changes` and `sqitch.events`. Those rows
  are registry history and must not be updated.

**Conclusion and safe alternative.**
1. **Never edit L41–43**, or any line at or before the hosted head. Every later id would change, and the next hosted
   `sqitch deploy` would die with "Cannot find change".
2. **Do not edit L44–52 by default.** Re-stamping is technically safe for hosted *if* its head is L43. It would still
   break any persistent database holding those changes (the operator's `sig-ops up` volume, other worktrees' composed
   stacks), and it is an in-place edit that AGENTS.md forbids.
3. Correct the record with:
   - the correction ADR table (§8);
   - standalone comment lines such as `# planned_at correction: resolution_supersede was planned 2026-09-25T08:09Z
     (062306e7); the timestamp above is kept because it is hashed into the change id (ADR-<corr>)`, which leave ids
     unchanged;
   - a **guard** that new plan lines have `planned_at ≤` their commit time, or are written only by `sqitch add`, which
     stamps the clock.
4. Sqitch does **not** require monotonic `planned_at`: L49 (09-27T14) follows L48 (10-16) and deploys in `make test-db`.
   Round 11 must **not** continue the ratchet past 10-19T21:00.

### 5.8 Release identity: `p-17b713…` (75 rows)
**Where the date lives.**
- `publication_id` = `sha256(descriptor.json bytes)` = `17b713cee4f4…c98587`. The descriptor holds
  `as_of_world` = `as_of_belief` = `2026-10-19`, `data_release_id sig-2026-10-19-518afbaf`, and `input_manifest_sha256` of
  the export manifest (its `as_of_snapshot` is 2026-10-19).
- `identity_digest sha256:bc20d4bf…` hashes `deferred_by`=`EVAL_DEFERRAL_NOTE` and `disclosure`=`EVAL_DISCLOSURE`
  (`release_candidate.py:232-283`).
- GATE-G3 signed both (`readouts/GATE-G3.md:17`). The P32.25 staging and rehearsal registries hold 9 further copies.
- The candidate is fixture-only (16 claims, 0 released records; F-15) and was never on production.

| option | what | consequences |
|---|---|---|
| A. Leave, append a correction | add a `CORRECTION.md` + disclosure addendum in `reports/p32.23a…`; the id keeps saying 2026-10-19 | cheap; but any future promotion would publish a false future "as of" (S0 if public) and a future as-of breaks as-of pinning semantics |
| B. Re-issue + re-sign | fix §5.4 constants, rebuild from the same frozen snapshot with a true as-of, get a new identity and publication id, then a **fresh operator GATE-G3 signature** (the old signature does not transfer); mark `p-17b713` superseded in the staging registry, append-only | truthful, but spends a human gate and a rebuild on a 0-record fixture candidate that nobody will publish |
| **C. Supersede, do not re-sign (recommended)** | append a supersession/withdrawal record: "`p-17b713` is not eligible for production publication; its dates are wrong (ADR-<corr>)"; keep the bytes as P32.23a/P32.25 rehearsal evidence; parametrise `release_publish_verify.py` so it no longer hard-codes the id; the **next real candidate** (G2 activation on hosted data) is built with the fixed constants and signed at a real GATE-G3 | honest, no wasted gate; D-R10-PUBLISH-1's "release-exposure half satisfied by this signature" is re-opened or annotated, because the signed artifact is withdrawn; ACCEPT-R10's scope clause gets an operator-confirmed addendum |

## 6. Cause hypothesis (evidence first)

1. **A chain date deliberately decoupled from the clock.**
   - `runs/P21.5.md:23` (Round 3, `ad1f8abd`, 2026-09-13): "Environment clock read 2026-09-13; chain date for this
     re-run = 2026-09-10". `runs/P21.4.md:32` says the same.
   - `runs/P32.7.md:15-17` (`6bade66e`, 2026-09-27T08:37Z): "recorded dates use the chain's dated-entry convention —
     2026-10-14 (P32.6's entries are dated 2026-10-13; machine UTC at run time is 2026-09-27 … rather than wall-clock)".
     `P32.8.md:17-19`, `P32.9.md:17-19` and `P32.10.md:16-18` say the same.
   - This is exactly the **"latest recorded date + 1 day"** pattern: P32.6→P32.9 = 10-13, 10-14, 10-15, 10-16; P32.10 = 10-18.
2. **The sqitch ratchet started at P31.7.** Hand-written `planned_at` values rise monotonically: 10-02T12 (P31.7) →
   10-02T13 (P31.10) → 10-02T19 (P31.11) → 10-03T12 (P32.2) → 10-10T12 (P32.3) → 10-11 → 10-12 → 10-16 → [P32.10a
   09-27T14] → 10-18 → 10-19 → 10-19T21 (P32.22).
   - Before P31.7, the only future dates in memory were legitimate scheduled ones: the muckrock next run 10-01, the
     10-08 deadline and the 10-10 replay (`git grep` at `062306e7^`).
   - P31.7's jump to 10-02 has no clock source. (I) It was plausibly anchored on those salient future dates.
   - P32.3's jump to exactly **2026-10-10**, the replay date, supports that anchoring (I).
3. **Tooling made the date a manual input.**
   - `obligation_events.py migrate --recorded-at` is a required "YYYY-MM-DD fixed input" with regex-only validation (L717-719).
   - `current_projection.py:15` says "semantic payload timestamps are fixed inputs".
   - Other manual date inputs: the release candidate's `as_of`, the dossier `_REPLAY_DATE` constants and hand-typed
     sqitch lines.
   - Keeping the clock out of deterministic payloads is sound. The *choice* of date was left to the agent with no bound.
4. **Per-session variation shows agent choice, not one bug.**
   - P32.10a–P32.14 and P32.20–P32.22 recorded the true 2026-09-27.
   - P32.15 and P32.16 run ledgers claim "real UTC date at closeout" but recorded 10-04 and 10-18.
   - P32.17–P32.19 used 10-02/10-02/10-01, anchored on the OKC "October 1" scenario (I).
   - From the HUMAN-H4 pause, the orchestrator resumed at P32.16a's maximum (10-19) and ratcheted to 10-21.
   - P33.2–P33.8 returned to real dates but faithfully propagated the recorded "2026-10-19" decision date.
5. **Harness.** All forward drift of more than a day, and the Round-3 backward chain date, came from commits **without a
   `Co-Authored-By` trailer**. Each such stretch is bracketed by Devin-trailered orchestrator commits:
   - Round 3: `eb72be5f`, `3259ca81`;
   - P25: `f59cacaf`;
   - Round 9 Wave B resume: `d41f9737` "resume after P31.5 pause — dispatch P31.6", `ff82b41e`;
   - Round 10: the operator statement relayed in the Claude-Code memory note of 2026-09-30, "planned by Codex, executed
     by Devin 09-26→09-28".

   Commits trailered Claude Opus 4.8/5.5 contributed only 6 same-day sqitch times (L27, L28, L33, L34, L39, L40), a few hours ahead. Attributing the
   untrailered commits to Devin is **(I)**.
6. **No guard.** Validators check format and structure only (F-27). The "independent" P33.1 re-anchored every event at
   the drifted 10-21.
7. **The ±1-day cases** (ADR-065, P27.3, P31.6, P32.2) are one day ahead of both the local and the UTC commit date.
   They are guesses, not timezone effects.

## 7. Operational hazards

1. **Premature D-P31.4-1 action (NEW-4, S1).**
   - The memory's latest dates (10-19…10-21, 97 `recorded_at` 10-21) make the 10-10 replay look 11 days overdue.
   - **(L)** 16:59:38Z: `gs://…-sig-restricted/ops/runs/camreg_osm_surveillance/` holds only `2026-09-19/`, `09-23/`,
     `09-24/` and `09-25/`, and the scheduler has never attempted batch-05.
   - `LEDGER.md:240` says "If it failed or ran long: re-execute the job inside the window … or roll back with `sig-ops
     roll-jobs`".
   - A resuming orchestrator that believes it is ≥ 10-21 would find no `2026-10-10/` row, conclude "failed", and could
     run a production OSM re-ingest (~1.37M claims on the 1-vCPU tier) or roll back job images before the real fire.
   - Mitigation (T5/B3): state the true clock rule in OPERATING MODE; D-P31.4-1's verify step must first check `date -u`
     ≥ 2026-10-10T03:35Z **and** the scheduler's `lastAttemptTime`.
2. **Date-ordered views invert.** Genuine events after 09-30 sort before the phantom 10-21 anchors and PHASE LOG entries.
   "Latest" reads (projection `observed_at`, PHASE LOG order) pick stale items until 2026-10-22.
3. **Inconsistent orientation.** CURRENT STATE `updatedAt: 2026-09-28` is older than the PRIOR entries it heads
   (10-21). A fresh reader cannot tell which is true.
4. **Ages and SLAs.** Rows "OPEN 2026-10-19" have negative ages. Any time-to-close metric in Round 11 is wrong until corrected.
5. **Future public false claims.**
   - Promoting `p-17b713` would publish "As of 2026-10-19".
   - Deploying the Round-10 dossier surfaces (G2) would show "retrieved 2026-10-01" for documents that were never
     retrieved (NEW-3).
6. **Sqitch foot-guns.** A well-meaning "date fix" to L41–43 breaks hosted deploys. The next added change may continue
   the ratchet (> 10-19T21).
7. **Signature authority.** The signed GATE-G3 readout's date is false. Correcting it needs an operator-confirmed
   addendum; an agent must not edit it (F-29).

## 8. Draft correction ADR (text for T1; *agent-drafted*, not a file in `docs/adr/`)

> **ADR-<next> — Correcting recorded dates that were not taken from a clock**
>
> - **Status:** Proposed (Round 11, Stage B). **Date:** *(the real `date -u` at acceptance)*.
> - **Related:** F-21, NEW-1…NEW-7 (planning 2026-09-30), ADR-073 (build memory), ADR-126/127 (obligation events,
>   closeout), ADR-142/144 (candidate identity, publication), SIG-ENG-003, SIG-STORE-024.
>
> **Context.** Between 2026-09-13 and 2026-09-28, build sessions recorded event dates from a "chain date" instead of the
> clock. Round 3 recorded 2026-09-10 for work done on 2026-09-13. Round 9–10 recorded 2026-10-01…2026-10-21 for work done
> on 2026-09-25…09-28, including the operator's S3 deferral and the GATE-G3 signature (both committed on
> 2026-09-28 UTC). The dates reached build memory, 25 ADR `Date:` headers, §55 and Appendix F/G text, product
> constants, test pins, committed fixture outputs, 11 future-dated `db/sqitch.plan` timestamps (three deployed on hosted
> `sig-pg`), the obligation
> event log, and the identity of the GATE-G3-signed candidate `p-17b713…`. The inventory is
> `planning/2026-09-30-next-phase/data/date_drift.csv`: 595 wrong-date rows and 37 correction rows.
>
> **Decision.**
> 1. *Truth source.* A recorded event date is the `date -u` at the moment of recording. Where that is unknown, it is the
>    committer time of the commit that records it, or the PR `createdAt`, written "≤ <time>". Chain, convention or
>    guessed dates are prohibited.
> 2. *Append-only correction.* No recorded line, ADR body, readout, App-G row, jsonl event or committed artifact is
>    edited to fix a date.
>    - Each control file gets one dated DATE CORRECTION entry that points to the register, which is promoted from
>      `data/date_drift.csv`.
>    - ADRs get an appended correction footer.
>    - `events.jsonl` gets `date-correction` events.
>    - Signed readouts get operator-confirmed addenda.
> 3. *Spec.* §55 landed-status text is amended to the true dates through `BUILD.sh`, with a new Appendix-G row. R10-A6 is
>    not edited.
> 4. *Code.* Hand-typed event dates are removed from product constants: `release_candidate`, `journey_verify`, `cli`,
>    the dossier packet builders and the web research-dossier fixture. Replay/capture dates of stand-in fixtures become
>    their real authoring dates or an explicit stand-in marker, and regression tests forbid date literals later than
>    build time outside allow-listed real-world fields.
> 5. *Sqitch.* No `db/sqitch.plan` line is edited: a planned timestamp is part of the change id. True planned dates are
>    recorded in this ADR and in standalone comment lines. New lines must have `planned_at ≤` their commit time.
> 6. *Candidate.* `p-17b713…` is superseded: withdrawn from production-publication eligibility by an appended record,
>    and kept as rehearsal evidence. It is not re-signed. The next candidate is built with true dates and requires a new
>    GATE-G3 signature by the operator.
> 7. *Guard.* CI fails when a newly added dated record (memory, ADR, jsonl, plan line) is later than its commit time,
>    unless it carries an explicit `future-ok` scheduled or real-world marker.
>
> **Consequences.**
> - The record becomes truthful without losing history; readers must consult the correction register for affected lines.
> - The deferral note and constants change, so the next candidate's identity differs from `p-17b713`.
> - D-R10-PUBLISH-1's release-exposure half is re-opened or annotated.
> - Three hosted sqitch registry rows keep a false `planned_at` forever, which is documented and harmless.
> - One more guard in CI.
>
> **Alternatives rejected.**
> - (a) In-place rewrite of dates: violates append-only and breaks the signed digests and sqitch ids.
> - (b) Re-stamping undeployed sqitch lines: unsafe for any persistent database, and an in-place edit.
> - (c) Re-issuing and re-signing `p-17b713` now: spends a human gate on a 0-record fixture candidate.
> - (d) Doing nothing: leaves the D-P31.4-1 hazard and a future false "as of" on the public surface.
>
> **Revisit trigger.**
> - Any newly found wrong date not in the register.
> - A read-only check of hosted `sqitch.changes` shows L44–52 deployed.
> - The operator chooses to publish or re-issue the fixture candidate.
> - A tooling change reintroduces manual date inputs without the guard.

## 9. Open questions (recorded, not answered)

- **Q-B1-1 (operator or Track 0, read-only).** Run `SELECT change, change_id, planned_at, committed_at FROM sqitch.changes
  ORDER BY committed_at DESC LIMIT 5;` on hosted `sig-pg`. It confirms that the head is `camera_site_human_decisions`
  and that no Round-10 change is present. No existing read-only path was available to this row.
- **Q-B1-2 (operator).** Confirm when the S3 deferral and the GATE-G3 approval were actually given. The commits are
  2026-09-28T01:27Z and 03:49Z (local 2026-09-27 evening). The correction uses "≤ commit time" unless the operator states
  an earlier time.
- **Q-B1-3 (operator).** Confirm option C for `p-17b713`, versus B (re-issue + re-sign).
- **Q-B1-4.** Does any persistent non-hosted database hold Round-10 sqitch changes: the operator's `sig-ops up` volume,
  or the `.codex/worktrees` composed stacks? This only matters if re-stamping L44–52 is ever considered.

## 10. Reproduction (scratch, gitignored)

Everything is in `docs/build/logs/next-phase/B1/`. The pipeline is `scan.py` → `flagged.tsv`, then `classify.py
<out.csv>`, which also reads `build_index_dates.tsv`, `r3_stale.tsv` and `commits.tsv`. Other captures there:
`ledger_phaselog.tsv`, `adr_dates.tsv` and `prs.json` (`gh pr list --state all --json …createdAt…`).

| file | sha256 |
|---|---|
| `scan.py` | `dfcd770f…66ce95` |
| `classify.py` | `dde810c6…9ee6` |
| `flagged.tsv` | `c6b12698…70db74` |
| `data/date_drift.csv` | `46813219…dcb7c` |
| sqitch `Change.pm` | `6dde7b32…7bab7d` |
| sqitch `Engine.pm` | `a865a48f…57c` |
| sqitch `Plan.pm` | `73ec400d…45376` |

The CSV schema is `path, line_or_field, recorded_value, introducing_commit, commit_date_utc, true_event_date, class,
artifact_kind, fix_mechanism, deployed_or_signed, note`. `introducing_commit` is the line's blame commit, and `note`
starts with the sub-class followed by the true-date basis.
