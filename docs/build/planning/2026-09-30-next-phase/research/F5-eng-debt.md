# F5 — Carried engineering debt: one register, thirteen fix packages

Row **F5** of `META_PLAN.md` (Stage P, owner R; depends A2, C4). Run window 2026-09-30T17:35:52Z → 18:05Z
(`date -u`). Worktree `/Users/stevenvitali/Eleutheria-next-phase`, branch `claude/next-phase-planning`, HEAD `12147ba3`.
`git diff --name-only b051732c HEAD` outside `docs/build/planning/` is empty, so all code evidence below is chain tip
`b051732c`. `PD` means `docs/build/planning/2026-09-30-next-phase`.

**Outputs.** This file; [`../data/eng_debt.csv`](../data/eng_debt.csv) (58 rows, the register: repro, root cause, fix
shape, size, risk, package); [`../findings/incoming/F5.csv`](../findings/incoming/F5.csv) (5 new findings). Nothing else
was written. Production was not touched (P3). Evidence classes: `code` (file:line read in this row),
`recorded-execution` (a command run in this row, with its time), and `cited` (another row's verified evidence, named by
its finding id; not re-run here unless stated).

**Sizes.** One agent context per ticket: **S** ≤ 0.5 day, **M** 0.5–2 days, **L** > 2 days (split before ticketing).

---

## 0. Summary

- **58 debt items in 13 packages.** Items by size: 37 S, 18 M, 3 L. Packages by size: 5 M
  (PKG-01, 02, 05, 11, 13) and 8 L (PKG-03, 04, 06, 07, 08, 09, 10, 12).
- **Both sqitch deferrals reproduced** on a throwaway PG18 + PostGIS container (podman; torn down, volume removed):
  - `sqitch verify` → `psql:verify/shared_temporal_contract.sql:30: ERROR: division by zero`, 1 error of 48 changes
    (17:38:12Z). `spine_watermark` has 28 rows.
  - `sqitch revert -y` → `extension postgis_topology depends on extension postgis` at `revert/extensions.sql:7`
    (17:38:18Z).
- **Recommendations. Both are append-only and both were verified end to end.**
  - **D-P32.10a-1:** use `sqitch tag` + `sqitch rework shared_temporal_contract`. The deploy and revert become no-ops,
    and a new verify asserts the 27 named facets. sqitch 1.6.1 does **not** run the earlier instance's verify script (I
    proved this with a deliberately broken `@tag` copy). A full deploy → verify → revert → deploy → verify round trip is
    green.
  - **D-P32.16a-1:** change no migration. The failure is caused by the test image: the `postgis/postgis` image
    pre-creates dependent extensions. In a database created from `template0`, the unmodified plan deploys, reverts
    fully and redeploys cleanly. So the test harness and a new CI round-trip job should deploy into a `template0`
    database.
- **Test pins, proven by mutation.** Routine Round-11 record changes turn **7 tests in 4 files** red because they pin
  living values (an 8th, the real-tree zero-errors audit, went red for legitimate validator reasons). The triggers
  include closing F5's own D-P32.10a-1, adding any new OPEN deferral, and the Stage-B LEDGER seed. Five of F-19's 11
  files pin no build-memory record: four build tmp_path trees, and test_source_registry only mentions DEFERRALS.md in a
  comment (it does pin the permitted-source set, ED-12). **PKG-02 must land in or before the Stage-B seed PR.**
- **Largest packages:**
  - PKG-06, jurisdiction identity and geometry QA;
  - PKG-07, technology typing plus backfill;
  - PKG-12, modules built and tested but never wired;
  - PKG-04, serving topology and a single-owner publish;
  - PKG-10, public number derivations.
- **New findings (F5.csv):**
  - NEW-1: living-record test pins proven by mutation (S2; complements B5 NEW-8).
  - NEW-2: `check_pilot` requires its return-pass deferrals to stay OPEN forever (S2).
  - NEW-3: D-P32.16a-1 is an image artifact (S3).
  - NEW-4: a full revert fails when two databases in one cluster carry the plan (S3).
  - NEW-5: the from-spine export never emits `leverage.json`, so every export-mode build fails (S2).

---

## 1. Method

1. I read META_PLAN §3 and the F5 row, FINDINGS.md (A2, 44 rows), R10_PREVIEW (C4), F2a-verdicts, H1-integration, and
   the 17 `findings/incoming/*.csv` present at the start (186 rows, scanned by title/category, with full text read for
   about 50 engineering rows). Seven files arrived during the run (B3, B5, C2, F1, F4, G2, J4); I scanned them by title
   and read B5 NEW-5/NEW-8, G2 NEW-1/NEW-3/NEW-6 and B3 NEW-5 in full, and cross-referenced them. I also read F1's
   adjudication of the two sqitch rows and B1 §5.7, the sqitch planned-date analysis.
2. I reproduced both sqitch deferrals in a throwaway container, then tested each repair shape against scratch copies of
   `db/` (scratchpad only; the repo's `db/` was mounted read-only).
3. **Mutation probe** for tests pinned to living records. I exported `git archive HEAD` to the scratchpad and applied
   one plausible Round-11 record change at a time. For each change I ran the 11 F-19 files with the worktree `.venv`
   (`PYTHONPATH` set to the copy's `tasks/src`) and recorded which tests failed.
4. I re-read code for every root cause cited in the register. Rows that rest on another row's verified evidence say so
   (`cited`).
5. **De-duplication.** Each defect appears once, under its earliest id, with every alias listed in `source_refs`. For
   example, F-44 = I1 NEW-1 = part of C3 NEW-14; F-41 = A1 NEW-2; G1 NEW-3 = J1 NEW-13.

**Environment.** podman 6.1.0 (applehv), `docker.io/postgis/postgis:18-3.6` (linux/amd64 under emulation),
`docker.io/sqitch/sqitch:latest` = **App::Sqitch v1.6.1**, Python 3.12.14, and uv (the pytest runs). Docker Desktop was
not running; I used podman instead, as C4 did.

**Container runs (all 2026-09-30).**

| time (Z) | action | result |
|---|---|---|
| 17:37:41 | `podman run -d --name f5-sig-pg … postgis/postgis:18-3.6` | ready 17:38:02 |
| 17:38:02 | `psql -c "select extname from pg_extension"` on `sig` | fuzzystrmatch, plpgsql, postgis 3.6.4, postgis_tiger_geocoder, postgis_topology |
| 17:38:02 | `sqitch deploy db:pg://…/sig` (repo `db/`, ro) | ok, 48 changes; `spine_watermark` 28 rows |
| 17:38:12 | `sqitch verify` | **1 error**: `shared_temporal_contract … division by zero` (line 30); rc 2 |
| 17:38:18 | `sqitch revert -y` | **not ok** at `extensions`: postgis_topology and postgis_tiger_geocoder depend on postgis; rc 2 |
| 17:40:00 | E-A1: verify fixed in place (scratch), DB from `template_postgis` | verify successful |
| 17:40:15 | revert with a second deployed DB in the cluster | **not ok** at `recovery_apply`: `role "sig_recovery" cannot be dropped … 23 objects in database e_a1` (NEW-4) |
| 17:40:40 | `select script_hash from sqitch.changes` | `shared_temporal_contract` = `877c70ae…` = sha1(**deploy** script); the verify sha1 is `ee460949…` |
| 17:40:41 | E-R: `sqitch tag f5-rework` + `sqitch rework shared_temporal_contract` (scratch) | new deploy/revert no-op, new verify = named facets; verify successful |
| ~17:41 | the `@tag` verify copy replaced by `SELECT 1/0` | verify **successful**, so the earlier instance's verify is not executed |
| ~17:42 | the **new** verify replaced by `SELECT 1/0` | 1 error, on the reworked instance only |
| 17:43:22 | E-B1: single DB `TEMPLATE template0`, repo scripts | deploy ok; full revert to `extensions … ok`, "No changes deployed"; redeploy ok |
| 17:43:54 | E-B2: appended `extension_dependents_teardown` change, DB from `template_postgis` | full revert ok; redeploy ok |
| 17:44:29 | E-B0 control: single DB from `template_postgis`, repo scripts | revert not ok (reproduces D-P32.16a-1 in a one-DB cluster) |
| 17:45:11 | E-C: DB from `template0`; deploy the landed plan, then the reworked plan on top, verify, full revert, fresh deploy, verify | all ok; `@tag` verify/revert byte-identical to the landed scripts (`cmp`) |
| 17:46:01 | `podman rm -f f5-sig-pg`; `podman volume rm c5965064…` (the anonymous volume created 17:37:44Z) | no F5 container or volume remains. The image cache was pre-existing and is left alone |

---

## 2. The two carried sqitch deferrals

### 2.1 D-P32.10a-1: whole-plan `sqitch verify` divides by zero (ED-01, ED-04, ED-06)

**Root cause (code).** `db/verify/shared_temporal_contract.sql:30` asserts
`(SELECT count(*) FROM spine_watermark) = 27`. That is a count over a shared, open-ended registry. The very next plan
line, `publication_dispositions` (P32.5, `sqitch.plan:47`), legitimately adds the 28th facet `publication_disposition`.
`sqitch verify` re-runs every deployed change's verify script against the *fully deployed* schema, so any assertion of
the form "the state right after this change" that counts shared rows goes stale. Nothing ran a whole-plan verify:
`make check` and `make test-db` only deploy (`tests/db/conftest.py:104`), and CI has no sqitch step (`ci.yml:71` is only
a comment).

**Repair options** (DEFERRALS lists "count-derived / `>=`" or "stop pinning exact global counts"):

| option | append-only? | tested | verdict |
|---|---|---|---|
| (a) edit `verify/shared_temporal_contract.sql` in place | **no** (an edit to a landed change's script) | E-A1 green | Operationally harmless: sqitch's `script_hash` covers the deploy script only (recorded above). But it breaks the convention, and would need an ADR carving verify scripts out of append-only. Fallback only |
| (b) a new, independent change with a correct verify | yes | reasoning | **Does not work.** The old change's verify still runs in a whole-plan verify, and nothing appended can change its result |
| (c) `>= 27` in place | no | — | Weaker than (d) and still an edit |
| **(d) `sqitch tag <t>` + `sqitch rework shared_temporal_contract`** | **yes** (sqitch's own mechanism for changing a deployed change) | **E-R, E-C green** | **Recommended** |

**Why (d) is append-only and sufficient.**

- `sqitch rework` preserves the landed deploy, revert and verify scripts byte-identically as `*@<t>.sql`, and sqitch
  uses those files for the earlier instance. It appends two plan lines: the tag and the reworked change. No landed plan
  line or deploy/revert script is edited.
- The reworked instance gets:
  - a no-op deploy and a no-op revert, because the schema does not change;
  - a verify that asserts the **27 named facets this change installs** (`facet = ANY(ARRAY[…27 names…])`), keeping every
    other original assertion.
- sqitch 1.6.1 reports the earlier instance "ok" without executing any verify script for it. This is empirical: a
  poisoned `@tag` copy still passes, while a poisoned new verify fails exactly once. So the whole-plan verify exits 0.
- Hosted impact is one no-op change in `sqitch.changes`. F1 and B1 record that `db/sqitch.plan` lines 44–52 (which
  include this change, L46) are very likely **not yet deployed** on hosted sig-pg. If that holds, the first hosted
  deploy applies the original instance (from the byte-identical `@tag` files) plus the no-op, and `sqitch verify` passes
  there too.
- Because `sqitch rework` stamps the real clock, the new plan lines satisfy B1's planned-date guard (ED-05).
- **Limit of any append-only repair.** A database that has not yet deployed L44/L46 (hosted, per B1/F1) will run the
  landed deploy scripts as written. So G2 NEW-3's hazard stays: L44 adds `bound_at … DEFAULT clock_timestamp()`, which
  rewrites the table under an ACCESS EXCLUSIVE lock, and L46 creates an index without CONCURRENTLY. The rework does not
  change it. That hazard is G2's rehearsal item (a PITR clone plus a lock window). Avoiding the rewrite would require an
  in-place edit of an undeployed landed change. That is an operator/ADR decision, which B1 §5.7 argues against, and F5
  does not recommend it.

**Prevent recurrence.**

- **ED-04:** a round-trip target, `make test-sqitch-roundtrip`, plus a CI step: in a `template0` database, run deploy →
  verify → revert -y → deploy → verify, and fail on any `not ok`.
- **ED-06:** a verify-lint unit test that rejects unscoped `count(*)` over shared registries or catalogs. It also flags
  two latent pins for rework-when-broken:
  - `temporal_invariants.sql:22-26` counts `pg_proc` rows by name, so it breaks on the first overload;
  - `intake_application_bridge.sql:63` and `recovery_apply.sql:70` pin the value `sig_visible_max_tier() = 2`.
- An ADR rule: "a verify script asserts what its change installed, never global totals."

### 2.2 D-P32.16a-1: whole-plan `sqitch revert` fails on postgis (ED-02, NEW-3)

**Root cause (recorded execution, refines the deferral).**

- The `postgis/postgis` image's initdb script creates postgis, postgis_topology, postgis_tiger_geocoder and
  fuzzystrmatch in `POSTGRES_DB` and in `template_postgis` *before* sqitch runs.
- `deploy/extensions.sql:12` (`CREATE EXTENSION IF NOT EXISTS postgis`) is therefore a no-op there.
- `revert/extensions.sql:7` then tries to drop an extension the plan never created and that has image-created
  dependents.
- In a database created from `template0` the plan owns its extensions: deploy creates btree_gist, pg_trgm and postgis,
  and the full revert drops them. The **unmodified** plan round-trips (E-B1).
- Conclusion: the plan is correct; the test environment is not what the plan assumes. No deploy/verify SQL depends on
  fuzzystrmatch, topology or tiger (grep). Cloud SQL's extension set was not read (P3). That it matches the `template0`
  case is an inference; G1 or Track 0 can confirm with one read-only `SELECT extname FROM pg_extension`.

**Repair options** (DEFERRALS lists "CASCADE vs ordered drops vs a new change that owns the teardown"):

| option | append-only? | tested | verdict |
|---|---|---|---|
| CASCADE in `revert/extensions.sql` | no | — | **Rejected.** An in-place edit, and it silently drops every dependent, including objects outside the plan on a shared database |
| ordered drops of topology and tiger in `revert/extensions.sql` | no | — | **Rejected.** An in-place edit of a landed revert, and it drops extensions the plan never created |
| an appended change `extension_dependents_teardown` [extensions]: no-op deploy; revert drops postgis_tiger_geocoder/postgis_topology IF EXISTS | yes | **E-B2 green** | Viable fallback, if the maintainer wants whole-plan revert to work on the stock image database |
| **deploy the test and CI round-trip into a `template0` database** (no migration change) | **n/a (no plan change)** | **E-B1 green** | **Recommended.** Test extensions then equal plan-owned extensions (closer to production); record "the plan owns only the extensions it creates" in the PKG-01 ADR |

**Side finding (NEW-4, ED-03).** Roles are cluster-global. Deploys create them idempotently, but reverts `DROP ROLE`
unconditionally. So a full revert fails (safely) whenever a second database in the same cluster carries the plan. This
matters for same-instance restore drills (G1 NEW-14). The recommended repair is to document the one-plan-per-cluster
assumption and keep the CI round trip to a single database.

### 2.3 The combined repair (PKG-01), exact steps

```bash
cd db
sqitch tag r11-sqitch-hygiene -n "Round 11: sqitch lifecycle hygiene (D-P32.10a-1, D-P32.16a-1)"
sqitch rework shared_temporal_contract -n "verify asserts the 27 facets this change installs, not the global count"
#  deploy/shared_temporal_contract.sql, revert/shared_temporal_contract.sql -> BEGIN; SELECT 1; COMMIT;  (no-op)
#  verify/shared_temporal_contract.sql -> the original assertions with line 30 replaced by the named-facet check
#  the *@r11-sqitch-hygiene.sql copies are written by sqitch and must stay byte-identical to the landed scripts
# tests/db/conftest.py + new `make test-sqitch-roundtrip`: CREATE DATABASE … TEMPLATE template0, then
#  deploy -> verify -> revert -y -> deploy -> verify, all exit 0 (CI python job; Docker is already present)
```

**Closure evidence** for both DEFERRALS rows: the CI round-trip log. **Co-requisite:** closing either row trips
`test_p33_3_annotations_preserve_open_status` (mutation M1), so PKG-02's rewrite of that test must land first or in the
same PR. **Sequence:** before the hosted L44–52 deploy (F1 plan 2b).

---

## 3. Tests that pin living build-memory state

F-19 counted 11 files by string reference. The mutation probe (§1, step 3; 2026-09-30T17:47:17Z–17:48:13Z; baseline
249 passed) sorts them:

| file | test | living state pinned | turns red on (probe) | rewrite rule | effort |
|---|---|---|---|---|---|
| `tests/unit/test_capstone_closure_round10.py` | `test_p33_3_annotations_preserve_open_status` | exactly 18 P33.3-annotated DEFERRALS rows, all OPEN/PARTIAL | M1 close D-P32.10a-1; M4 close D-P32.21-1; M6 close D-R10-LIVE-1 | an annotated row may close only with a dated token **and** an obligation-event transition with evidence; drop `== 18` | S |
| same | `test_every_open_deferral_appears_in_the_f5_register` | the frozen CAPSTONE_CLOSURE §(f5) must name every *currently* open deferral | M2 add any OPEN deferral | scope to the id set OPEN at the snapshot (a pinned list); living coverage belongs to `reports/current/` | S |
| same | `test_gate_accept_readout_state_matches_the_recorded_decision` | `ledger.split('## GATE DECISIONS',1)[-1]` contains ACCEPT-R10. It is **vacuous** today, because F-22 removed that heading, so the split returns the whole LEDGER | the B3 LEDGER redesign (moves decisions out) | resolve from the B3 decision register, and fail if the section is missing | S |
| same | `_round10_requirement_ids` / `test_plan_requirements_match_coverage_matrix_ownership` | `len == 38`; matrix rows owned by `P32*`/`P33*` equal PLAN.json ids | T4 re-homing an id to a P34 row | assert PLAN.json ids ⊆ matrix, each with a non-empty owner | S |
| `tests/unit/test_agent_docs_current_state.py` | `test_ledger_closed_the_manifest_honestly` | `lastCompleted: P33.8`, `nextTicket: HUMAN-H4`, `projectStatus: IN-PROGRESS` (off-enum, F-23) | M3 LEDGER advance; M7 the enum fix, **so the Stage-B seed PR itself goes red** | delete it; `audit_current_state` already validates the cursor, the enum and next-ticket resolution | S |
| same | `test_coverage_matrix_marks_sig_mem_004_met` | verdict `== "MET"` | M5 the S5 vocabulary (MET-ENGINEERED) | verdict in the validator enum, and evidence non-blank for the MET family | S |
| same | `test_build_readme_index_range_is_current` | README contains `rows 1-200` | the README update for row 201 | derive the max row from BUILD_INDEX and assert README states it | S |
| same | `test_web_agents_names_all_island_exceptions_and_node_floor` | web/AGENTS.md contains `>=22.12.0` | PKG-13 node pinning | equal to `web/package.json` `engines.node` | S |
| `tests/tasks/test_acquisition_pilot.py` + **production** `tasks/…/acquisition_pilot.py:1746-1765` | `test_check_pilot_zero_violations`, `test_cli_pilot_check_green` | the real DEFERRALS carries D-P32.18/19/20/21-1 **OPEN** | M4 the live return pass closes D-P32.21-1 | `check_pilot` accepts OPEN **or** an evidence-backed closure; tmp_path tests for all three states (NEW-2) | S |
| `tests/unit/test_build_memory_audit.py` | `test_no_existing_gate_or_deferral_is_closed_by_parsing` | 7 named rows OPEN/PARTIAL | M6 | assert that the parsed status equals each row's raw leading token (the real invariant) | S |
| same | `test_real_tree_expected_conflicts_and_zero_errors` | zero errors (**keep**: a true invariant that caught #165/#179) **plus** `flagged == {"D-P21.5-1"}` | when D-P21.5-1 is reconciled | move the expected conflicts into a committed allowlist owned with the records | S |
| `tests/unit/test_round10_integration_plan.py` | 8 snapshot tests; `test_prior_plan_points_at_current_plan` | pins the dated P33.6 report (immutable: acceptable) plus a living pointer text | a Round-11 plan superseding the pointer | the pointer resolves to an existing plan | S |
| `tests/unit/test_backlog_housekeeping.py` | all | invariants (checker exit 0, render parity, BL homes) plus historical closed rows | — | keep; strengthen `check_backlog` itself (ED-54) | 0 |
| `tests/unit/test_source_registry.py` | `test_ingestion_permitted_defaults_false_across_the_seed` | the exact 236-id permitted set (the comment says 77) | every Round-11 source flip (Stream I) | a deliberate HG-03 tripwire; convert to "every permitted source cites a recorded rights decision" and fix the comment | S |
| `test_check_build_memory_report`, `test_closeout_protocol`, `test_current_projection`, `test_obligation_events` | — | **none**: tmp_path trees only (false positives) | — | — | 0 |
| *(outside the 11)* `tests/unit/test_repo_docs_current_state.py` | `test_readme_round10_honest_bounds`, `test_governance_readme_counts_all_documents` | README contains `D-R10-PUBLISH-1` / `operational=false`; governance "Ten documents" | activation; the next governance document | keep the "must not contain X" guards; derive "must contain" from config and the index | S |

**Totals.** 16 test functions across 7 files need a rewrite, plus one production-code change (`check_pilot`). That is
about 1 agent-day (PKG-02, M). Add a guard (ED-13): tests may read living control records only through the validators,
or against an explicit snapshot commit. Literal cursor, status or verdict values are rejected. The same rule forbids
the #186 pattern of relaxing a pinned test to accept a changed record (H1 NEW-6).

**Sequencing consequence.** Mutation M7 (the F-23 enum fix) and M3 (any LEDGER advance) are exactly what the Stage-B
LEDGER seed (T5) does. **PKG-02 must be part of the Stage-B seed PR, or precede it.** Otherwise the seed PR is red on
the python job.

---

## 4. Packages (candidate Round-11 tickets)

Each package lists its register items (ED ids in `data/eng_debt.csv`), its scope, an acceptance-criteria sketch, and
its dependencies. "co-own" means another Stage-P row owns the design; the package owns the code change.

### PKG-01 — Sqitch lifecycle hygiene and round-trip CI · **M** · ED-01…ED-06
- **Scope:** §2.3 (tag + rework; a `template0` harness; `make test-sqitch-roundtrip` plus a CI step; the plan-date
  guard; the verify-lint); one ADR (verify contract, extension ownership, one plan per cluster).
- **AC:**
  - whole-plan `sqitch verify` exits 0 on a fully deployed container;
  - `sqitch revert -y` followed by redeploy exits 0;
  - CI runs the round trip on every PR;
  - the `@tag` copies are byte-identical to the landed scripts (a test runs `cmp`);
  - a new plan line with `planned_at` later than its commit fails a unit test;
  - D-P32.10a-1 and D-P32.16a-1 close DONE with the CI log as evidence.
- **Depends on:** PKG-02 (the capstone test); B1 (date guard wording). **Must precede** the hosted L44–52 deploy (F1
  2b; G2).

### PKG-02 — Decouple tests from living build memory · **M** · ED-07…ED-13
- **Scope:** §3 rewrites; the `check_pilot` fix; the lint/convention; an AGENTS.md test-convention note.
- **AC:**
  - the §1 mutation set (M1–M7) runs with 0 failures, except legitimate validator errors (e.g. a next ticket missing
    from the manifest, an unknown verdict enum);
  - `check_pilot` refuses a closure without evidence and accepts one with evidence.
- **Depends on:** the S5 vocabulary (for the verdict-enum test) and B3's decision register (for the gate test). Both
  can be stubbed to the current validators. **Must land in or before the Stage-B seed PR.**

### PKG-03 — Release archive and export-mode build repair · **L** (split 03a/03b) · ED-14…ED-20
- **03a (M):**
  - link depth in `release_pages.py`, plus a link-resolution crawl in `validate_release`;
  - `run_spine_export` emits `web/leverage.json` (the zeroed metric), or `data.ts` treats its absence honestly;
  - an honest empty tile state;
  - a CI export-mode web build from a from-spine fixture export;
  - island budgets and Lighthouse over that build, with the R10 URLs added to `lighthouserc`.
- **03b (M):**
  - nginx deny map: tombstone body and alias coverage; entity stubs from the deny set;
  - a `/r/<pub>/` landing page; non-data compartments excluded from search; completeness "not evaluable" at 0
    records;
  - search scope counts include runtime denies;
  - content-negotiated HTML error pages.
- **AC:**
  - a crawl of the corpus tree returns 0 unexpected non-200s;
  - the export-mode build of a from-spine export passes in CI;
  - every withdrawn alias returns 410 with the tombstone;
  - DR-C4-01, 08, 09, 10 and 13 are met.
- **Depends on:** nothing for 03a; 03b coordinates with PKG-04 on nginx. **Precedes** G2 activation step 1 (a real
  candidate must build).

### PKG-04 — Serving topology and single-owner publish · **L** · ED-21…ED-24
- **Scope:**
  - G3's topology decision implemented: `/v1/releases/*` and `/intake/*` proxied through nginx or the LB, or absolute
    API links with `SIG_RELEASE_SEARCH_BASE`;
  - the registry mounted, with `--release-registry` in `ops/Dockerfile:112`;
  - **one publish command** that composes web/dist and the staged namespaces, asserts the denylist (`curate/`, demo
    `task/new` pages, `presentation/`) and that immutable prefixes are unchanged, then syncs once, with `--delete`
    excluding `/r/`, `/releases/<pub>/`, `/entity/` and `conf/`;
  - a post-sync absence probe;
  - the sig-web bucket made private.
- **AC:**
  - the composed e2e answers search and `/intake/new` through the web origin;
  - a dry-run shows zero deletions under immutable prefixes;
  - a planted `curate/` file aborts the sync.
- **Depends on:** G3 (topology), G1 (regression test, IAM change as an operator action), PKG-03b.

### PKG-05 — Intake and moderation hardening before `operational` flips · **M** · ED-25…ED-28
- **Scope:**
  - UUID-safe serialisation, with route tests parametrized over both the Memory and the PG store (the missing seam
    behind the 500);
  - the gate fails closed unless `owner` is set and `staffed = true`;
  - no demo tokens when a DSN is set;
  - a forwarded-client limiter key, with refusals not charged;
  - a reporter-facing outcome, response and link;
  - proposal shape validated at proposal time.
- **AC:**
  - `GET /v1/curation/intake/{receipt}` returns 200 over PG (Docker test);
  - DR-C4-11 and DR-C4-12 are met.
- **Depends on:** D-P32.16-1 staffing (operator) for the actual flip; PKG-04 for routing.

### PKG-06 — Jurisdiction identity and geometry QA · **L** (split 06a/06b) · ED-29…ED-32
- **06a (M):** a canonical jurisdiction key `(scheme, code)` mapped to ISO 3166-2 at `shaping.py:1041`, with slugs,
  labels and redirects or tombstones for the old slugs. `/v1/dossier` and `/v1/coverage` resolve through the same key
  (see PKG-09).
- **06b (L):**
  - point-in-polygon QA at export that quarantines mismatches into an explicit state;
  - axis-order and null-island detectors, with a per-target `axis_order`;
  - corrections to the 7 identified target rows as new claims;
  - investigate the IDOT/FL511 conflicts and the same-source exact-point duplicates;
  - one row per entity in the portal files.
- **AC:**
  - no bucket mixes schemes;
  - 0 published points outside their declared jurisdiction without a disclosed state;
  - the portal `row_count` equals distinct entities or is disclosed as rows.
- **Depends on:** a republish (G2/G3). Coordinates with I-stream new sources, which need the same QA.

### PKG-07 — Technology typing of registry records · **L** · ED-33
- **Scope:**
  - a `technology` slug per `camera_registry_targets.toml` target;
  - `dot_511.py:541,602` emits it (claim plus subtype);
  - an export column; dossier/map facets;
  - an append-only backfill of technology claims for existing subjects (about 200k).
- **AC:**
  - Flock/DeFlock layers read ALPR;
  - the sites exports carry a technology column;
  - no record is typed `traffic_camera` unless its target says so.
- **Depends on:** PKG-11 (SKOS slug hygiene); a republish.

### PKG-08 — Rights attribution integrity · **L** · ED-34, ED-35
- **Scope:**
  - rights resolution keyed on (source, spdx, attribution, terms) instead of SPDX alone (`claim_sink.py:950-975`), with
    new `rights_record` and `rights_decision` rows (ADR-095 pattern);
  - per-row attribution in every compartment;
  - per-compartment map attribution;
  - correct SPDX ids (OGL-UK-3.0) and LicenseRef URLs.
- **AC:**
  - every exported row's attribution equals its registry source's attribution;
  - 0 rows with `attribution_required=1` and an empty attribution.
- **Depends on:** a re-export; the E-stream rights review for the texts.

### PKG-09 — Public API truth and placeholder-identity purge · **L** (split 09a/09b) · ED-36…ED-40
- **09a (M):**
  - `/v1/dossier/{scope}` and `/v1/coverage/{scope}` return 404, or the real jurisdiction scope, and never an
    arbitrary 25-subject sample (C3 NEW-1 is **S0**; recommend the first Round-11 code ticket after PKG-01/02);
  - `bytes_available` only for public byte-bearing captures;
  - `sig_read_public` grants cut down to the §37 read surface by a new sqitch change.
- **09b (M):** one identity-base setting across the API IRIs, `provenance.ttl` and the crawler UA (operator picks the
  base), a published `/data-collection` page, provenance with retrieval times, upstream URLs and digests.
- **AC:**
  - no scope returns unrelated subjects;
  - no `sig.example` or `sig-project.org` literal in shipped code;
  - a DB test allowlists what `sig_read_public` can SELECT.
- **Depends on:** PKG-06a (the jurisdiction key), an operator decision on the IRI base, PKG-01 (sqitch CI).
- **Shipping constraint (G2 NEW-6).** The live sig-api image is `ba3dca61`, 128 commits behind the chain. The S0 fix
  reaches production only with an API image roll: either the Round-10 API roll after hosted L44–52 and the ADR-124
  allows, or an operator-approved hotfix off the live image. The code can land in wave 0; the deploy timing is G2's.

### PKG-10 — Public number derivations · **L** · ED-41…ED-44 (co-own C6/C3)
- **Scope:**
  - per-dossier "How we know this" provenance;
  - coverage numerators without the clamp and with filters;
  - freshness emits `not_evaluable` and volatility classes, and covers non-site sources;
  - map-table suppression.
- **AC:** C3's number-trace rows for these surfaces (PD/data/number_trace.csv) re-derive exactly.
- **Depends on:** C6 requirements; PKG-06 (jurisdiction keys).

### PKG-11 — Ontology and vocabulary conformance · **M** · ED-45, ED-46 (plus F2a group 13)
- **Scope:**
  - the Mobility mapping fixed, with the test corrected;
  - a connector-output conformance test against the generated enums;
  - a CHECK added `NOT VALID` through a new sqitch change;
  - the reflexive `skos:broader` removed, with a generator check;
  - F2a group 13 carried in: the operator-unknown count, the MFA slot, the carrier test, the RTCC organization type,
    lossy-flag propagation, and the QID-to-vendor link.
- **AC:** every connector's emitted enum values are in the generated schema; the SKOS graph has no reflexive or cyclic
  broader.
- **Depends on:** nothing. Unblocks PKG-07.

### PKG-12 — Built but unwired · **L** (maps to F2a groups 5 and 10 and F2b NEW-2) · ED-47…ED-51
- **Scope:**
  - lifecycle into the dossier timeline;
  - disappearance persisted as append-only events and research tasks;
  - `derived_from` set for republication sources and read by materialization;
  - the INGEST-004 spec amendment with a test;
  - run telemetry (per-fetch URL, status, bytes) and `/v1/changes`.
- **AC:**
  - the timeline section is non-empty where events exist;
  - `disappeared_observed_at` has a writer;
  - mirrors of one origin share an independence class;
  - run rows carry per-fetch fields.
- **Depends on:** J3 (the public run-log design); E2/T1 (the amendment).
- **Recommendation:** add F2a §6.5's mechanical scan for public functions with only test callers as the package's
  first step.

### PKG-13 — Toolchain pinning and CI / scheduled-workflow truth · **M** · ED-52…ED-58
- **Scope:**
  - pin node and npm (`.nvmrc` or `node-version-file`, `packageManager`, `engines`), and fail CI if `npm ci` would
    rewrite the lockfile;
  - add `check_spec_src.py` and `check_coverage_matrix.py` to `docs-check` and CI, then add truth rules after S5;
  - `check_backlog` requires an open home;
  - `observability.yml` measures production read-only or is retired, and a skipped probe is never reported as success;
  - retire the `reingest.yml` schedule and fix OPERATIONAL_READINESS:90;
  - cancel-in-progress for PRs only;
  - a cron lint that rejects schedules restricting both day-of-month and day-of-week.
- **AC:**
  - node and npm versions are identical in local and CI (a CI assertion);
  - the checkers run in CI;
  - no scheduled workflow reports success on a no-op;
  - 0 cancelled push runs on main.
- **Depends on:** S5 (vocabulary, for the coverage truth rules), B4 (validator redesign), G1 (live scheduler re-sync).
  **H1 recommends it as the first engineering ticket** (lockfile drift recurrence).

### Suggested order (critical path)

1. **Stage-B seed PR:** PKG-02, so the LEDGER seed and first closeouts stay green.
2. **PKG-13 and PKG-01:** CI truth and sqitch round trip, before any hosted sqitch deploy.
3. **PKG-09a:** the S0 API dossier endpoint. The code lands now; the deploy follows G2's image roll or a hotfix.
4. **Before G2 activation:** PKG-03, PKG-04 and PKG-05.
5. **Before the next public republish:** PKG-06, PKG-08, PKG-10, PKG-11 and PKG-07. The public data-truth defects
   ship with every republish.
6. **PKG-12**, in parallel with the J and I streams.

---

## 5. Considered and left with another owner (so each item keeps exactly one disposition)

| item | why not an F5 package row | owner |
|---|---|---|
| C4 NEW-2, 3, 4, 6, 7, 20, 22, 23, 27, 28, 32; NEW-5, NEW-19, NEW-21, NEW-24 (copy, epistemic labels, navigation, print, licence text, reflow, form UX) | product requirements (DR-C4-02…06, 14, 15), not engineering defects with a single code root | C6 → S |
| C4 NEW-11, F-15 (the staging candidate is a fixture) | activation decision (it must not be the production candidate) | G2 |
| F-12, G1 NEW-2 (sig-probe stale targets), NEW-8, NEW-10 (cadence baked into images; fleet on 4 builds), F-43, F-42, G1 NEW-1, NEW-4, NEW-12, NEW-14 | operations and IaC state; the code-side cron lint is ED-58 | G1 |
| B1 NEW-1, NEW-2 (`release_publish_verify.py` hard-coded 2026-10-19), NEW-7 (event-log date ordering); B2 NEW-2 (migrate rewrites events); F-26; F3 NEW-2, NEW-11; A3 NEW-5 | build-memory truth and validator redesign (the code change lives with the correction record) | B1 / B4 / B3 |
| F2a groups 1–4, 6–9, 11–12, 14 (officer gate, promotion gate, redaction, rights refusal state, projection rebuild CI, security baseline, statute leads, registry sweep, inference distinguishability) | already ticket-shaped by F2a with scope lines; not re-listed | F2a → S1 |
| BL-049 / SIG-STORE-045 (generated DDL vs sqitch), F3 NEW-10 | existing open home; a decision, not a defect | F3 / E2 |
| F-39 (Dagster not wired), E3 NEW-2 (reviewer workflow needs PG logins), J1 NEW-1, NEW-5…NEW-7, NEW-11, NEW-12 (downloads page, permalinks, registry export, data dictionary, CDN) | architecture/verdict or transparency design | F2 / E3 / J3 |
| G2 NEW-1 (no operator verb to record the ADR-124 `allow` dispositions), G2 NEW-2 (the live sig-web image lacks the withdrawal-barrier nginx), G2 NEW-3 (L44/L46 lock/rewrite on hosted), G2 NEW-10 (no hosted execution host for the live return passes); F1 NEW-2/NEW-3 (DONE rows whose hosted verification fails because the API image is old) | activation tooling and sequencing; G2 routes them to ACT-08…ACT-11 | G2 |
| B3 NEW-1 (the vendored validator's PHASE LOG check is vacuous), B3 NEW-5 (`closeout_protocol.authoritative_root` defaults to the main worktree), F4 NEW-3 (nextTicket rule vs HUMAN markers) | memory-tooling defects inside the B3/B4 validator redesign | B3 / B4 |
| J4 NEW-1, NEW-4…NEW-7 (terms forbid redistribution; raw bytes keep OSM user/uid; digest-only capture history; OKC fixture sources served live; CC0 labels) | rights and provenance review; J4 NEW-2/NEW-3/NEW-6 are cited in ED-34/35/36 | E4 / J |
| C3 NEW-2 (**S0**: personal ArcGIS handles in source ids; also C2 NEW-2) | Part VIII/C2 remediation (id aliasing plus a rename in the registry); flagged here because it touches `source_id` stability across exports and URLs | C2 / E4 |

---

## 6. New findings (`findings/incoming/F5.csv`)

| f_id | sev | title (short) | routed |
|---|---|---|---|
| NEW-1 | S2 | Mutation probe: 7 pinning tests in 4 files go red on routine Round-11 record transitions (incl. F5's own closure and the Stage-B seed); 5 of F-19's 11 files pin no build-memory record; complements B5 NEW-8 | B4; S1; T5 |
| NEW-2 | S2 | `check_pilot` (a CI invariant and CLI) requires D-P32.18-1…21-1 to stay OPEN, so the live return pass cannot close them cleanly | G2; S1 |
| NEW-3 | S3 | D-P32.16a-1 is an artifact of the postgis image; in a `template0` DB the unmodified plan round-trips | S1; F1 |
| NEW-4 | S3 | A full revert fails when a second DB in the same cluster carries the plan (cluster-global roles) | G1; S1 |
| NEW-5 | S2 | The from-spine export never emits `web/leverage.json`, so every production export-mode build fails, not only the C4 candidate | G2; H2; S1 |

## 7. Limits

- Docker Desktop was down, so I used podman with the amd64 image under emulation. CI uses Docker on ubuntu-latest; I
  expect the same sqitch behaviour (sqitch 1.6.1 in the same image), but that is an inference.
- The hosted `sqitch.changes` and `pg_extension` were not read (P3). Whether L44–52 are deployed on hosted is cited
  from B1 and F1 ("very likely undeployed").
- The C3, I1, J1, E1 and G1 data defects are cited from those rows' live reads. Here I re-read the code root causes:
  `shaping.py:1041`, `dot_511.py:541,602`, `claim_sink.py:950-975`, `store_pg.py:927-956`, `dereference.py:23`,
  `osm_tag_vocab.toml:87-89`, `intake.py:132-139`, `deploy.py:92`, `Dockerfile:112`, `release_pages.py:117,193` and the
  leverage emitters. I did not re-query production data.
- The mutation probe used plausible record edits, not the actual future records. A real closeout may trip additional
  validator errors, and those are legitimate.
