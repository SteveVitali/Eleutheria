# A1 delta before T6 (SEED-18b)

> Written by Stage-B unit SEED-18b (Round 11, plan Appendix A **T6**, first bullet "A1 delta re-run") at 2026-10-01T17:41:25Z
> (`date -u`), harness `claude-code/claude-opus-5-5/subagent`, on branch `r11/seed` at HEAD `03effc4d`. Procedure:
> `baseline/BASELINE.md` § Delta procedure, run in full (the restricted SEED-01 run at 2026-10-01T07:35:56Z left 45 keys
> not re-run; CARRY "T2-α · full A1 delta incl. GCP + CI keys still owed before T6"). Read-only throughout: `git
> ls-remote/rev-parse/show/merge-base/cat-file`, `gh pr list/view/checks`, `gh run list/view`, `gh api` GETs, `gcloud …
> describe/list`, `curl` GETs. No `git fetch` was needed (`git.chain_tip_descends_from_origin_main` did not report
> `unknown`; every remote commit named below was already in the local object store). No secret value was read or printed.

## Run

| step | value |
|---|---|
| script | `a1_delta.py` extracted from BASELINE.md to `docs/build/logs/next-phase/T6/a1_delta.py` (gitignored); sha256 `c71ce1dfe3a687b3712d83d820adfe09572aeedd92ded27f82a17cb7b9965090` = the A1 value |
| auth | `gh auth status`: logged in (token scopes `gist`, `read:org`, `repo`, `workflow`; account not recorded); `gcloud`: an access token was available and every call passed `--project zeta-medley-508121-u7` explicitly (the CLI's default project is a different one). **No key was "not re-run (auth)".** |
| run 1 — `delta` | started 2026-10-01T17:23:36Z (`clock.captured_at_utc`), ended 17:24:17Z; exit 0; output `docs/build/logs/next-phase/T6/delta.out` (sha256 `d9373ff1deedd3af0e72f3db86019a303134156241c787199764b197f574b624`): **14 changed key(s)** |
| run 2 — `capture` | 2026-10-01T17:24:51Z; exit 0; `docs/build/logs/next-phase/T6/capture2.json` (sha256 `fb67f6922c87401c3c6cca9eaf88e213e4b54c1c700098ffc383d64910ecd06a`), taken so every current value below is a read, not an inference; **the same 14 keys changed, with the same values** |
| keys | 89 script-derived keys (every `baseline.json` key without `_provenance`); 87 compared (the procedure skips `clock.*` and `git.planning_head_sha`) |
| by family | `git.*` 3 changed · `gh.*` 8 changed · **`mem.*` 0 changed** · `prod.*` 3 changed |

Procedure step 4 routing: the `git.*`/`gh.*` changes mean the plan's integration inputs moved (the operator's merge sitting
and three mid-stack pushes, § D1–D3), so T6 re-read those sources (done below); the `prod.*` changes are expected drift
(backups) plus one unexplained `settingsVersion` bump, routed to G1/G2 as informational. `mem.*` = 0: the build-memory
control files at the chain tip `b051732c` are byte-identical to A1; the seed's own changes live on `r11/seed`, which the
procedure does not compare.

## Every key (baseline → current)

Long values are shortened (sha256 to 12 hex + `…`; long JSON to 87 characters); the raw values are in the two log files
above. "= baseline" means byte-equal JSON.

| key | baseline (2026-09-30T16:31:55Z) | current | changed? | explanation |
|---|---|---|---|---|
| `clock.captured_at_utc` | "2026-09-30T16:31:55Z" | "2026-10-01T17:24:51Z" | skipped | not compared by the procedure (step 3): the clock, and the planning head that moves with every planning commit (HEAD `03effc4d` at this run) |
| `gh.ci_all_pass_count` | 33 | 36 | **CHANGED** | #141–#154 left the open set (merged by the operator 2026-10-01T04:24:07Z–04:26:00Z, GitHub `mergedAt`); #165/#179/#185 turned green after new head commits pushed 2026-10-01T00:58:12Z–01:01:36Z (see § Manual re-checks); 36 open, all 5/5 green |
| `gh.ci_failing_count` | 16 | 0 | **CHANGED** | same cause: the 13 composed/web reds merged away; the 3 python reds fixed on their own heads |
| `gh.ci_failing_prs` | {"141": ["composed", "web"], "142": ["composed", "web"], "143": ["composed", "web"], "1… | {} | **CHANGED** | same cause |
| `gh.lowest_open_base` | "devin/round9-waveb-seed" | "devin/p31-19-round9-closeout" | **CHANGED** | #155 is now the lowest open PR; its base is #154's head branch (merged) |
| `gh.open_heads_sha256` | "8331f062ef27…" | "24a4f1b1637a…" | **CHANGED** | the open set changed (#141–#154 merged) and #165/#179/#185 have new heads |
| `gh.open_max` | 190 | = baseline | no |  |
| `gh.open_min` | 141 | 155 | **CHANGED** | #141–#154 merged |
| `gh.pr_closed` | 0 | = baseline | no |  |
| `gh.pr_merged` | 142 | 155 | **CHANGED** | +13 merges (#141–#147, #149–#154); #148 was already merged |
| `gh.pr_open` | 49 | 36 | **CHANGED** | −13 (the merges above) |
| `gh.pr_total` | 191 | = baseline | no |  |
| `git.chain_tip_descends_from_origin_main` | false | = baseline | no |  |
| `git.chain_tip_sha_local` | "b051732c3c6e…" | = baseline | no |  |
| `git.chain_tip_sha_origin` | "b051732c3c6e…" | = baseline | no |  |
| `git.origin_main_sha` | "b7c9e2e3e925…" | "00f67f4b62cd…" | **CHANGED** | `main` advanced by the operator's #141–#154 merge sitting; tip = merge of #154 (2026-10-01T04:25:59Z) |
| `git.origin_main_tree` | "53fa9d041b46…" | "7eb11d62e960…" | **CHANGED** | same cause |
| `git.origin_main_tree_equals_p31_4_tree` | true | false | **CHANGED** | expected after the merges: `main` now holds P31.5–P31.19 |
| `git.p31_4_branch_sha` | "d4522d8212fc…" | = baseline | no |  |
| `git.p31_4_branch_tree` | "53fa9d041b46…" | = baseline | no |  |
| `git.planning_head_sha` | "a23fca8a8399…" | "03effc4d03dd…" | skipped | not compared by the procedure (step 3): the clock, and the planning head that moves with every planning commit (HEAD `03effc4d` at this run) |
| `git.worktree_count` | 8 | = baseline | no |  |
| `mem.bytes.docs/build/BACKLOG.csv` | 41474 | = baseline | no |  |
| `mem.bytes.docs/build/BUILD_INDEX.md` | 295436 | = baseline | no |  |
| `mem.bytes.docs/build/COVERAGE_MATRIX.csv` | 201858 | = baseline | no |  |
| `mem.bytes.docs/build/LEDGER.md` | 679109 | = baseline | no |  |
| `mem.bytes.docs/build/OPERATIONAL_READINESS.md` | 42743 | = baseline | no |  |
| `mem.bytes.docs/build/reports/current/CURRENT.md` | 14203 | = baseline | no |  |
| `mem.bytes.docs/build/reports/obligations/events.jsonl` | 75653 | = baseline | no |  |
| `mem.bytes.docs/tickets/00_MANIFEST.md` | 102012 | = baseline | no |  |
| `mem.bytes.docs/tickets/DEFERRALS.md` | 339292 | = baseline | no |  |
| `mem.ledger.blockedOn` | "(nothing)" | = baseline | no |  |
| `mem.ledger.chainTip` | "devin/p33-8-agent-docs-refresh" | = baseline | no |  |
| `mem.ledger.lastCompleted` | "P33.8" | = baseline | no |  |
| `mem.ledger.nextTicket` | "HUMAN-H4" | = baseline | no |  |
| `mem.ledger.pauseRequested` | "false" | = baseline | no |  |
| `mem.ledger.projectStatus` | "IN-PROGRESS" | = baseline | no |  |
| `mem.ledger.round` | "10" | = baseline | no |  |
| `mem.sha256.docs/build/BACKLOG.csv` | "99b2dd03482f…" | = baseline | no |  |
| `mem.sha256.docs/build/BUILD_INDEX.md` | "7830dbc3864b…" | = baseline | no |  |
| `mem.sha256.docs/build/COVERAGE_MATRIX.csv` | "11b77c2ce907…" | = baseline | no |  |
| `mem.sha256.docs/build/LEDGER.md` | "d459173f7afd…" | = baseline | no |  |
| `mem.sha256.docs/build/OPERATIONAL_READINESS.md` | "581fcb5558ca…" | = baseline | no |  |
| `mem.sha256.docs/build/reports/current/CURRENT.md` | "0b693e7343a1…" | = baseline | no |  |
| `mem.sha256.docs/build/reports/obligations/events.jsonl` | "1439087e45a4…" | = baseline | no |  |
| `mem.sha256.docs/tickets/00_MANIFEST.md` | "e493c3d347f2…" | = baseline | no |  |
| `mem.sha256.docs/tickets/DEFERRALS.md` | "b688f3b49b33…" | = baseline | no |  |
| `prod.buckets` | ["zeta-medley-508121-u7-sig-backups", "zeta-medley-508121-u7-sig-public", "zeta-medley-… | = baseline | no |  |
| `prod.public_manifest.as_of_snapshot` | "2026-09-27" | = baseline | no |  |
| `prod.public_manifest.release_id` | "sig-2026-09-27-ce480ab1" | = baseline | no |  |
| `prod.public_manifest.ruleset_version` | "p27.3/1.0.0" | = baseline | no |  |
| `prod.public_manifest.sha256` | "717aeb449952…" | = baseline | no |  |
| `prod.run_jobs.count` | 88 | = baseline | no |  |
| `prod.run_jobs.distinct_images` | 8 | = baseline | no |  |
| `prod.run_jobs.latest_tag_refs` | 0 | = baseline | no |  |
| `prod.scheduler.count` | 79 | = baseline | no |  |
| `prod.scheduler.enabled` | 79 | = baseline | no |  |
| `prod.sig_alerts.image` | "us-central1-docker.pkg.dev/zeta-medley-508121-u7/sig/sig-api:latest" | = baseline | no |  |
| `prod.sig_alerts.max_instances` | "20" | = baseline | no |  |
| `prod.sig_alerts.min_instances` | "unset" | = baseline | no |  |
| `prod.sig_alerts.ready_transition` | "2026-09-16T17:46:52.529389Z" | = baseline | no |  |
| `prod.sig_alerts.revision` | "sig-alerts-00004-7xv" | = baseline | no |  |
| `prod.sig_api.image` | "us-central1-docker.pkg.dev/zeta-medley-508121-u7/sig/sig-api@sha256:40a47da8c2cf…" | = baseline | no |  |
| `prod.sig_api.max_instances` | "2" | = baseline | no |  |
| `prod.sig_api.min_instances` | "1" | = baseline | no |  |
| `prod.sig_api.ready_transition` | "2026-09-25T14:56:38.871017Z" | = baseline | no |  |
| `prod.sig_api.revision` | "sig-api-00011-wic" | = baseline | no |  |
| `prod.sig_pg.backup_enabled` | true | = baseline | no |  |
| `prod.sig_pg.backup_retained` | 7 | = baseline | no |  |
| `prod.sig_pg.backup_start_time` | "05:00" | = baseline | no |  |
| `prod.sig_pg.backups_count` | 2 | 3 | **CHANGED** | expected drift: one AUTOMATED backup `1790830800000` 2026-10-01T07:18:03Z→07:19:35Z, SUCCESSFUL |
| `prod.sig_pg.backups_successful` | 2 | 3 | **CHANGED** | same |
| `prod.sig_pg.deletion_protection` | false | = baseline | no |  |
| `prod.sig_pg.disk_gb` | "15" | = baseline | no |  |
| `prod.sig_pg.pitr_enabled` | true | = baseline | no |  |
| `prod.sig_pg.settings_version` | "63" | "64" | **CHANGED** | no UPDATE operation after 2026-09-30T16:31:41Z in `gcloud sql operations list` (newest 8: one BACKUP_VOLUME 2026-10-01T07:18:03Z); every readable setting re-checked equal (§ Manual re-checks) — cause not determinable read-only; *inference:* a service-side settings write. Routed to G1/G2 as informational |
| `prod.sig_pg.state` | "RUNNABLE" | = baseline | no |  |
| `prod.sig_pg.tier` | "db-custom-1-3840" | = baseline | no |  |
| `prod.sig_web.image` | "us-central1-docker.pkg.dev/zeta-medley-508121-u7/sig/sig-web@sha256:d8244804eb4f…" | = baseline | no |  |
| `prod.sig_web.max_instances` | "2" | = baseline | no |  |
| `prod.sig_web.min_instances` | "unset" | = baseline | no |  |
| `prod.sig_web.ready_transition` | "2026-09-27T01:32:09.206397Z" | = baseline | no |  |
| `prod.sig_web.revision` | "sig-web-00002-5nw" | = baseline | no |  |
| `prod.site.api_health_status` | 200 | = baseline | no |  |
| `prod.site.curate_apex_status` | 404 | = baseline | no |  |
| `prod.site.curate_run_status` | 404 | = baseline | no |  |
| `prod.site.home_last_modified` | "Sun, 27 Sep 2026 01:33:43 GMT" | = baseline | no |  |
| `prod.site.home_sha256` | "a007e380588b…" | = baseline | no |  |
| `prod.site.home_status` | 200 | = baseline | no |  |

## Manual keys re-checked (procedure step 3: only those whose related core key changed)

| manual key(s) | baseline | now (read 2026-10-01T17:25:38Z–17:28:18Z) | changed? |
|---|---|---|---|
| `git.origin_main_parents` / `_committed_at` / `_subject` | `42482a77…`+`d4522d82…` · 2026-09-29T22:46:38-04:00 · merge of #140 | `67d9e730…` + `8ee17dd7…` (#154's head) · 2026-10-01T04:25:59Z · "Merge pull request #154 from …/devin/p31-19-round9-closeout" | yes (the merge sitting) |
| `git.merge_base_origin_main_chain_tip` | `13782968` (P31.4 closeout) | `08d87c4d` (2026-09-27T02:06:32Z, "docs(P31.19): precise the leak-check negative-control count …"); GitHub compare `main...b051732c`: diverged, chain tip 93 ahead / 250 behind (the 250 are `main`'s merge commits and `d4522d82`) | yes |
| `git.main_only_commit_absent_from_chain` | `d4522d82` | still absent from `b051732c` (compare `d4522d82...b051732c`: 1 behind); plus every `main` merge commit | no (same commit) |
| `git.chain_tip_descends_from_origin_main` (script key) | false | false | no |
| `git.lowest_open_base_sha` / `_on_origin_main` | `34406ffc` / false | `8ee17dd7` (`devin/p31-19-round9-closeout`, #154's head) / **true** (compare: 0 ahead of `main`) | yes |
| `gh.open_number_gaps` / `gh.open_stack_contiguous` / `gh.open_non_devin_base` | [148] / true / {156: `codex/round10-seed-after-p31-19`} | [] (#155–#190) / true / unchanged | gaps only |
| `gh.highest_open` | #190 → #189's branch, head `b051732c` | unchanged | no |
| `gh.open_mergeable` / `gh.open_draft` | 49 / 0 | 32 MERGEABLE + 4 UNKNOWN (#155, #166, #180, #186 — GitHub still computing after base changes) / 0 | yes (expected) |
| `gh.open_last_updated` | 2026-09-28T22:48:14Z | 2026-10-01T01:01:38Z (#185; #165 00:59:12Z, #179 00:58:14Z) | yes (§ D1) |
| `gh.last_merged` | #140 2026-09-30T02:46:38Z | #154 2026-10-01T04:26:00Z (#141 first, 04:24:07Z) | yes |
| `gh.ci_failing_completed_range` | #141–#154, #165, #179, #185 | none failing; #165/#179/#185 all five jobs `pass`, completed 2026-10-01T00:58:36Z–01:06:53Z | yes |
| `gh.main_ci_push_latest` | run 36661393143 success on `b7c9e2e3` | run 36815092432 `CI` push **success** on `00f67f4b` (2026-10-01T04:26:02Z); the 13 intermediate pushes were cancelled by concurrency | yes (expected) |
| `gh.main_sched_reingest` | 6/6 failure | **7/7 failure** (latest 36855561801, 2026-10-01T11:28:15Z, same `--sink pg requires --dsn`; NEW-2 persists — P34.4 owns `gh workflow disable reingest.yml`) | count only |
| `gh.main_sched_nightly` / `_observability` | 6/6 / 6/6 success | success on `00f67f4b` (2026-10-01T09:31:53Z / 12:51:32Z) | no new failure |
| `gh.main_sched_keepalive` | 0 runs on main | **1 run, success** (2026-10-01T13:58:13Z on `00f67f4b`) — the merged P31.x code brought it | yes |
| `prod.sig_pg.*` manual (version, edition, availability, disk type, autoresize, PITR log retention/storage, IPv4, authorised networks, SSL mode, maintenance window) | POSTGRES_18 · ENTERPRISE · ZONAL · PD_SSD · true · 7 d / CLOUD_STORAGE · true · 0 · ALLOW_UNENCRYPTED_AND_ENCRYPTED · unset | identical | no |
| `prod.sig_pg.backups` | 2 (ON_DEMAND `1790785111976`, AUTOMATED `1790785806842`) | 3: + AUTOMATED `1790830800000` 2026-10-01T07:18:03Z→07:19:35Z SUCCESSFUL | yes (expected) |

Not re-checked (no related core key changed): the site, manifest, bucket, scheduler and Run-job manual keys — their core
keys (`prod.site.*` incl. `home_sha256`, `prod.public_manifest.*` incl. `sha256`, `prod.buckets`, `prod.scheduler.*`,
`prod.run_jobs.*`) are all unchanged, so the public release is still `sig-2026-09-27-ce480ab1` and the home page bytes
are the A1 bytes.

## What the delta found beyond the key list (T6 re-read the affected sources)

**D1 — three mid-stack pushes the planning record does not mention.** On 2026-10-01, before GATE-P, one new commit each
landed on the heads of #179, #165 and #185 (GitHub committer times; authored with the operator's identity, trailer
`Co-Authored-By: Claude Opus 4.8`):

| PR | commit | time (UTC) | file | what |
|---|---|---|---|---|
| #179 (`devin/p32-22-bounded-recovery`) | `b01ef231` | 00:58:12Z | `docs/build/BUILD_INDEX.md` (+1/−1) | escapes the pipes in row 183's evidence cell |
| #165 (`devin/p32-10-resolution-evaluator-and-confidence-gates`) | `f8377011` | 00:59:09Z | `docs/tickets/00_MANIFEST.md` (+1/−1) | sequence cell `170.5` → `170a` |
| #185 (`devin/p33-3-capstone-closure`) | `4a2ce75d` | 01:01:36Z | `docs/build/readouts/ACCEPT-R10.md` (+5/−12) | "fix(gate): restore ACCEPT-R10 to PENDING — agents must not sign HG-14" |

They turned the three python reds (F-19) green. Their successors (#166, #180, #186) were not updated, so **the chain tip
`b051732c` (#190) and `r11/seed` contain none of the three**. The manifest and BUILD_INDEX fixes have equivalents at the
chain tip (row `170a` is present; the piped evidence text is gone, though row 183's text differs from `b01ef231`'s).
**ACCEPT-R10 does not:** at `b051732c` and on `r11/seed` the readout still says "SIGNED — Round-10 closure accepted as
presented", followed by SEED-08's appended B7 annotation (2026-10-01T08:21:03Z) and the C-13 supersession, while #185's
head now says "PENDING. No approval, human work or publication is asserted." The two records disagree about the same
gate; no planning or seed record cites `4a2ce75d`. *(Agent reading, labelled:)* the seed's annotation (the operator's
words reached the session at 2026-09-28T18:46:46Z, confirmed at GATE-P as C-1; superseded by C-13) and `4a2ce75d`'s
message ("no corroborating operator GATE DECISION record") cannot both stand on `main` — this is an operator question
(GATE-B packet Q-9).

**D2 — the bottom-up merge sitting no longer replays cleanly (H1's simulation is stale).** Simulated read-only in a
throwaway `git clone --shared` under the session scratch directory (never pushed; the worktree untouched): from `main`
`00f67f4b`, `git merge --no-ff` of each open head #155 → #190 in order.

- **One conflict, at #180**, in `docs/build/BUILD_INDEX.md` (row 183: `b01ef231` on #179's head vs. the stack's later
  edit). Resolved for the simulation only with the stack's side (`-X theirs`, an agent choice for the dry run, not a
  recommendation for the sitting), the remaining 10 merges are clean.
- The final tree is **not** #190's tree (`64a23cd7…`): it differs in exactly one file, `docs/build/readouts/ACCEPT-R10.md`
  (the PENDING text from #185's head survives).
- **Merging `r11/seed` (`03effc4d`) on top then conflicts in `docs/build/readouts/ACCEPT-R10.md`.**

So plan §12's "zero conflicts in 49 steps and ends tree-identical to #190" no longer holds for the remaining sitting
#155–#190; OP-08 needs one BUILD_INDEX resolution and an ACCEPT-R10 decision, and the seed PR's later merge needs the same
decision (§ D1).

**D3 — the recorded merge window is a minute late.** Plan §11.2/§12 and the manifest's OP-08 row record the merges as
"2026-10-01T04:25–04:26Z"; GitHub's `mergedAt` runs from **04:24:07Z (#141) to 04:26:00Z (#154)**. *(Agent reading:)* a
dated, appended correction where the orchestrator chooses (OM-13); no record is edited here.

**D4 — `main` workflows.** Push CI green on the new `main`; `reingest` still fails daily (7/7); `keepalive` now runs on
`main` (1 success).

**D5 — Cloud SQL `settingsVersion` 63 → 64** with no matching UPDATE operation and every readable setting unchanged
(table above). Informational for G1/G2; nothing to do before row 201.

**D6 — repository settings for OP-05/OP-07 (read for the GATE-B packet; not A1 keys).** `gh api repos/…` (2026-10-01T17:28Z):
visibility **public**; the only ruleset is "main" (id 21702901, enforcement **disabled**); **no "stack" ruleset** for
`refs/heads/r11/**` (H2 S-2); `allow_squash_merge` and `allow_rebase_merge` still **true** (H2 S-3 wants false);
`delete_branch_on_merge` false, `allow_auto_merge` false, `allow_update_branch` false (as S-3 wants); `main` unprotected;
**0 Actions variables** (S-4's `SIG_GCP_PROJECT` absent); Actions `allowed_actions: all` (S-7 optional). OP-05 is due
**before the T6 push**; OP-07 before row 201.

**D7 — the seed is still local.** `git ls-remote origin` lists neither `r11/seed` nor `claude/next-phase-planning` (B-16
holds until the T6 push). The private bundle `~/SIG-planning-backup-20261001T0503Z.bundle` exists (3,911,365 B, written
2026-10-01T05:03Z per its name); META_PLAN says it is "refreshed at T6" — not done by this unit (it should capture the
final `r11/seed` after the orchestrator's last commit).

**D8 — what did not move.** Chain tip `b051732c` local = origin; #190 still the top of the stack; the public release, home
page, `/curate/` 404s, API `/health` 200, Cloud Run revisions/images, scheduler (79) and Run-job (88) counts, buckets and
`:latest` usage are all as at A1.
