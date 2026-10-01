# H2: PR model and CI policy for Round 11

Row **H2** of `META_PLAN.md` (Stage P, Wave 5). Owner D/J. The base was decided at GATE-M (§7.1, Q-11): Round 11
stacks on the unmerged chain tip `devin/p33-8-agent-docs-refresh` (PR #190), and the operator merges the chain later.
This row is **design only**. It changes no repository setting, pushes nothing, re-runs nothing and commits nothing.
It writes two files: this note and `findings/incoming/H2.csv`. Every settings change in §5 is an operator action.

- **Authored:** 2026-09-30T18:03:52Z to 18:28:10Z (`date -u`) by Claude Code (Opus 5.5), in
  the planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (`claude/next-phase-planning` @ `038e25b9`).
- **Builds on:** H1 (integration facts, merge simulation, lockfile, transient reds, bounded loop), B5 (OM-05 CI gate,
  OM-12 blocks, OM-18 stop-and-ask), B4 (G3a–G3e, `ci_required.toml`, the exit-code contract, Q-B4-3), and FINDINGS
  F-17…F-20 and F-40.
- **Evidence classes (P1):** `live-read` (`gh` GETs, Actions logs and annotations, `git ls-remote`, local tool
  versions), `recorded-execution` (a read-only local `pytest tests/unit` run and both docs detectors on this tree), `code`
  (workflow, Makefile and package files), and `inference`, marked **(I)**.
- **Read-only method.** The only GitHub calls were `gh pr list/view/checks`, `gh run list/view` and `gh api` GETs.
  Scratch output (the CI run history JSON, 571 runs) lives in the session scratchpad and is not committed. The local
  test run wrote only ignored caches: bytecode was disabled and pytest's cache provider was off.

---

## 0. Summary

**The policy in ten lines.**

1. **Stack.** One ticket, one branch, one PR. Each PR's base is the previous ticket's branch. The first Round-11 PR is
   the **seed PR**, based on `devin/p33-8-agent-docs-refresh`. Agents never merge, retarget, rebase, force-push or
   merge `main` into a stack branch. No agent pushes to a branch once a successor branch exists.
2. **Seed = planning history by ancestry.** At GATE-P a new branch `r11/seed` is created at the head of
   `claude/next-phase-planning`. Stage B (T1–T6) commits on top of it. The branch is pushed and the seed PR is opened in
   T6. The planning commits reach the chain unchanged, with no squash, cherry-pick or rewrite (§2.1). Before the first
   push, one credential-shaped literal in two committed planning notes must be fixed (NEW-1).
3. **Required checks.** Every Round-11 PR must pass all five `ci.yml` jobs, **python, docs, composed, security and web**,
   on its current head. "Green" means those five checks plus the local gates. Local-only is written `locally-green`
   (P11).
4. **No inherited red at the base.** #190 is 5/5 green on `b051732c` (run 36494519255), and a Round-11 PR's CI tests
   `head ⊕ its chain base`. The 16 pre-#190 reds are merge-readiness items for the operator (H1), not Round-11 blocks.
   Q-H2-1 asks the operator to confirm this reading of OM-05. Two kinds of red can still appear on the first Round-11
   run. Clock-dependent latent reds (B4 NEW-3) still block. So do reds that the seed introduces itself (§3.3).
5. **Boundary gate (G3a).** Read the check-runs **bound to the head sha** through `commits/<sha>/check-runs`, not the
   unbound `gh pr checks` table (NEW-12). Poll every 60 s. Allow a 5-minute registration grace and a 45-minute
   deadline. Any failure, cancellation, skip, missing or unknown check sets `blockedOn` and stops.
6. **One re-run, allowlisted flakes only.** A committed `ci_flakes.toml` lists known flakes. Today it has two entries:
   the Lighthouse performance score and a python substring assertion (NEW-8). A matching failure gets at most one `gh run rerun --failed` per head. Both
   attempts are recorded. Anything else is red.
7. **Workers never close red.** The closeout commit is written only after the pre-closeout head is green. The
   orchestrator then re-reads the final head before it dispatches the next ticket.
8. **Toolchain pin as the first engineering ticket (TC-PIN).** The ticket pins:
   - Node 24 LTS through `web/.nvmrc`, `engines`, `packageManager` and `engine-strict`, with one recorded lockfile
     regeneration under that toolchain;
   - uv through `required-version`;
   - `runs-on: ubuntu-24.04`, which must land **before 2026-10-19**, the date `ubuntu-latest` moves to Ubuntu 26
     (NEW-6).

   It also adds `pipefail` to every workflow (NEW-3), completes every `main` push run, and adds a real `make ci-local`
   mirror (NEW-10).
9. **Settings are operator actions (§5).** Activate a fixed "main" ruleset after the #141–#190 sitting (today it targets
   no branch, NEW-5). Add a "stack" ruleset that forbids force-push and deletion on `r11/**`. Allow merge commits only.
   Keep `delete_branch_on_merge=false`. Add no CODEOWNERS.
10. **CI unavailable is never green.** Billing blocks, outages and API failures produce `blockedOn: CI unavailable`.
    Continuing requires a verbatim, time-boxed operator waiver. Work under it is `locally-green`, and a `ci-owed`
    re-verification sweep follows. The chain has done this silently before: 40 run attempts could not start between
    2026-09-17 and 09-22, and nothing was recorded (NEW-2).

**New findings (§8):** 12 (NEW-1…NEW-12). **Operator questions (§9):** Q-H2-1…Q-H2-6.

---

## 1. Facts this policy rests on (2026-09-30T18:04–18:21Z)

### 1.1 CI configuration (`code`)

| item | value | where |
|---|---|---|
| PR workflow | `CI`, `on: push: [main]` + `pull_request` (all bases), jobs **docs · python · composed · security · web** | `.github/workflows/ci.yml` |
| concurrency | `group: ci-${{ github.ref }}`, `cancel-in-progress: true` for every event | `ci.yml:17-19` |
| `docs` job | PR-only (`if: github.event_name == 'pull_request'`), `fetch-depth: 0`, `make docs-check` + `check-build-memory.sh`. Pinned by `tests/unit/test_ci_workflows.py::test_ci_docs_job_runs_only_on_pull_requests` | `ci.yml:28-43` |
| `python` job | uv **0.12.6** (setup-uv), Python from `.python-version` (`3.12`), `make sync/lint/format-check/typecheck`, `make test` with `SIG_REQUIRE_DB_TESTS=1` (Docker-backed `tests/db` and `tests/e2e` run for real), `make verify-gen` | `ci.yml:45-80` |
| `composed` job | uv 0.12.6, `setup-node` **`node-version: "22"`** (floating major), `npm --prefix web ci`, `pytest tests/e2e` with `SIG_REQUIRE_DB_TESTS=1` | `ci.yml:91-125` |
| `security` job | `make scan-secrets`, the GCP project-id leak test armed by `vars.SIG_GCP_PROJECT` (skips when unset), `make scan-licenses` | `ci.yml:132-163` |
| `web` job | node `"22"`, `npm ci`, typecheck, unit, build, `check:licenses`, Playwright install, `test:e2e` (axe), `check:perf` (Lighthouse CI) | `ci.yml:169-209` |
| runner | `runs-on: ubuntu-latest` in all **9** jobs of the 5 workflows | `grep runs-on .github/workflows/*.yml` |
| scheduled | `nightly`, `observability`, `keepalive`, `reingest` run on `schedule` / `workflow_dispatch`, which means **`main` only**. They never exercise #141–#190 or Round-11 code until it is merged | the four workflow files |
| pin files | no `.nvmrc`, `.node-version`, `.tool-versions`, `web/.npmrc` or `packageManager`; `engines` is `node >=22.12.0` only; no `[tool.uv] required-version` | `ls -a`, `web/package.json`, `pyproject.toml` |

### 1.2 The chain tip and the open stack (`live-read`)

- **#190** `devin/p33-8-agent-docs-refresh` @ `b051732c`: OPEN, `MERGEABLE/CLEAN`, base `devin/p33-7-repo-docs-refresh`.
  Its checks bound to that sha (`commits/b051732c…/check-runs`) are **5/5 success**, all from run **36494519255**
  (attempt 1, 2026-09-28T22:48:19Z → 22:55:54Z). Job times: python 7m1s, web 3m46s, composed 57s, docs 51s,
  security 18s.
  - python: `5539 passed, 6 skipped`. Every skip reason is listed by `-ra`: 3 are web-build fixtures that the composed
    job covers, 2 are env-armed secrets tests, and 1 is the live staging API.
  - composed: `16 passed`.
- **Heads digest unchanged** since A1/H1: `8331f062…d088` (recomputed 18:13:03Z).
  - #155–#190: all 5/5 green except #165, #179 and #185 (`python` = FAILURE), as H1 §1.3 recorded.
  - #141–#154: 13 red (`composed` + `web`, the stale lockfile).
- **Next PR number:** the highest issue/PR number is #191, so the seed PR would be **#192** if nothing else is opened
  first.
- **PR body files:** `docs/build/pr/` holds 212 files. 118 follow `<ID>.md` (114 `PN.N.md` + 4 `PN.Na.md`). The rest
  use legacy names such as `pr_N.md`, `pN_N_pr_body.md` and `prbody.md`. The #190 body equals
  `docs/build/pr/P33.8.md` apart from one trailing newline.

### 1.3 CI history: 571 `CI` runs, 2026-08-27T03:44Z → 2026-09-30T02:46Z (`live-read`)

| measure | value |
|---|---|
| outcomes | PR: 204 success · 125 failure · 100 cancelled; push to `main`: 24 success · 1 failure · **117 cancelled** (82 % of main push runs) |
| green PR run wall time (first attempt, n=187) | median 3.6 min · p95 7.2 · **max 8.3**; since 09-26 (n=58): median 6.1 · p95 7.9 · max 8.3 |
| re-runs (`attempt > 1`) | 51 runs: 17 turned green, 34 stayed red |
| red → green on the same sha | Of the 17, **11** had a first attempt that never started (the billing block below), and **6 were flakes**.<br>• **5 Lighthouse runs:** `web` failed "`categories.performance failure for minScore` … expected >=0.9", then passed on re-run. The runs were 35051006427 (P25.4), 35263896936 (P21.9 re-run), 35889213151 (P28.1), 36065771273 (P21.5 re-run) and 36338778274 (P32.19/#176, re-run 3 days later on 09-30T03:06Z). `web/lighthouserc.json` has `numberOfRuns: 1` with an error-level `minScore 0.9` on content pages.<br>• **1 python run:** 35296544560 (P26.8, 09-18) failed `tests/api/test_curation_onboarding_timing.py::test_elapsed_time_never_written_to_the_submission_row` on `assert "8.5" not in str(row)`. That is a substring check over the whole recorded row, which can collide with generated content (I). The test is unchanged since `2981ce8c` (NEW-8) |
| **jobs never started** | **40 run attempts** on 14 PR branches, 2026-09-17T01:13:45Z → 2026-09-22T16:01:28Z. All 5 jobs "failed" in 2–40 s with 0 steps. The annotation read: *"The job was not started because recent account payments have failed or your spending limit needs to be increased."* There were two windows: 09-17T01:13–07:40Z (P26.2–P26.5, plus P25.10 at 20:19Z) and **09-18T08:22Z → 09-22T16:01Z** (P26.11–P26.19). The operator re-ran them 09-17T16:48–16:53Z and 09-22T23:06Z. No build record mentions it (NEW-2) |
| runner annotation on current jobs | *"The ubuntu-latest label will migrate to Ubuntu 26 beginning October 19, 2026"* (#190 web job 109170980091; also on 09-22 jobs). A second notice says `actions/checkout@v4` and `setup-node@v4` target Node 20 and are forced onto Node 24 (NEW-6) |
| toolchain in CI | `ubuntu-24.04` image 20260920.314.1; node **v22.23.2** / npm **10.9.8**. `EBADENGINE`: license-checker-rseidelsohn@5.0.1 requires node ≥24 / npm ≥11 (#190's web log) |
| npm advisories | `npm ci` prints "**14 vulnerabilities (… 7 high, 1 critical)**" on #190's web job (09-28) and "**18 … (10 high, 1 critical)**" on the 09-30 nightly for the **same lockfile blob** `da838491`. No step gates npm advisories: `dep_audit.sh` is pip-audit only (NEW-9) |
| nightly | 6/6 "success". Each gated stage runs `… 2>&1 \| tee <log>` under `shell: /usr/bin/bash -e {0}` (log), which has **no pipefail**, so a stage's outcome is `tee`'s. `nightly_report.py` gates only on those outcomes (NEW-3) |

### 1.4 Repository settings (`live-read`, `gh api` GET)

- **Visibility:** `SteveVitali/Eleutheria` is **PUBLIC**. There is one collaborator (`SteveVitali`, ADMIN). Agents use
  that identity and token (B4 §2.3).
- **`main` protection:** `protected:false`; `required_status_checks` off.
- **Ruleset 21702901 "main":** `enforcement: disabled` and **`conditions.ref_name.include: []`**, so it targets no
  branch even if enabled. Its rules are only `deletion` and `non_fast_forward`. `bypass_actors: []` (NEW-5).
- **Merge settings:** merge, squash and rebase are all allowed. `delete_branch_on_merge=false`,
  `allow_auto_merge=false`, `allow_update_branch=false`.
- **Actions:** enabled, all actions allowed, `sha_pinning_required:false`. **0 repo variables, 0 secrets and 0
  environments**, so `vars.SIG_GCP_PROJECT` is unset (NEW-4). No `CODEOWNERS`.

### 1.5 Local state of the build machine (`live-read`, 18:04–18:13Z)

- **Local toolchain:** uv **0.12.6**, the same as CI. Node **v25.2.1** / npm **11.6.2**, where CI runs 22.23.2 / 10.9.8.
  That is the live local side of H1 NEW-2's inferred root cause (NEW-7).
- **Docker daemon is down**, so a plain `make check` here would silently skip `tests/db` and `tests/e2e` (AGENTS.md
  gotcha 3).
- **`tests/unit` on this planning tree** (`b051732c` plus the planning directory, at 18:13Z): **1411 passed, 1 failed**.
  The failure is `tests/unit/test_security_scanners.py::test_secret_scan_real_tree_is_clean`, caused by the planning
  directory (NEW-1). `secret_scan.py` reports 2 hits at `038e25b9` (`review/PROTOCOL.md:538`, `review/R10_PREVIEW.md:82`,
  both `sig-credential-literal`). Their history is `4df1552f` (C1) and `2cf03075` (C4). No other credential shape
  occurs in the 32 planning commits.
- **Other checks on this tree:** `check-build-memory.sh .`: 0 violations. Repo-docs detector: 0 broken refs (430 docs).
  Agent-docs detector: 0 issues.

---

## 2. Branch and PR model

### 2.1 The planning branch and the Round-11 seed

**Facts.**

- `claude/next-phase-planning` forks from `b051732c`, #190's head (`merge-base --is-ancestor` true).
- It carries 32 commits (at `038e25b9`), linear with no merges, and **every changed path is under
  `docs/build/planning/2026-09-30-next-phase/`** (0 outside).
- It exists only locally (`git ls-remote origin 'refs/heads/claude/*'` is empty).

**Decision (recommended): the seed carries the planning directory by ancestry.**

1. **At GATE-P**, the planning orchestrator writes its final planning commit (the `NEXT_PHASE_PLAN.md` ratification
   record). It then creates `r11/seed` **at that same commit** (`git switch -c r11/seed`). This creates a new ref and
   rewrites nothing. `claude/next-phase-planning` is **frozen** from then on: it receives no further commits, and its
   head sha is recorded in the seed PR body and in the LEDGER seed (T5).
2. **Stage B (T1–T6)** commits land on `r11/seed`: spec_src and ADRs, the LEDGER repair, manifest rows 201+, contracts,
   registers, the guard core (B4 §6.1) and `docs/build/pr/R11-SEED.md`. Any planning correction needed during Stage B
   is appended on `r11/seed`, inside the planning directory, as a dated entry (P7).
3. **T6 publishes.** It pushes `r11/seed`, which is the **first publication** of the planning commits to a public
   repository, and opens the seed PR:

   ```bash
   gh pr create --base devin/p33-8-agent-docs-refresh --head r11/seed \
     --title "R11 seed — Round-11 plan, spec amendments, repaired build memory" \
     --body-file docs/build/pr/R11-SEED.md
   ```

   The operator's GATE-P words should say explicitly that this push and PR are approved (OM-07/OM-09: recorded
   verbatim, not pre-answered). GATE-B then requires G3a green on the seed PR (§4).
4. **The first ticket** (row 201) branches from `r11/seed`'s final head, and its PR base is `r11/seed`.

**Why ancestry, not a copy.**

- **The #155 copy destroyed history.** The Round-10 planning package was imported by #155 as 2 copy commits
  (+8,001 lines). Its research branch `codex/sig-six-stream-research` was never pushed, so the per-row commit history
  is not on the chain.
- **Commit times are evidence here.** They are what B4's G1 replay and B4 NEW-1 (this round's own ledger drift) are
  measured against. A squash or copy would erase them. Ancestry also makes the operator's merge carry them to `main`
  unchanged.
- **No merge commit is needed.** A merge of the planning branch into a seed cut from #190 would add one with no
  content benefit.

**Two preconditions for the first push (T6 checklist).**

- **P-1: the secret-shaped literal (NEW-1).** The flagged value sits on two loopback-only local-preview command lines.
  It is fixed, not generated, and it is not an obvious placeholder (checked by shape only; the value is not reproduced
  here, P14). Treating it as a throwaway, not a production credential, is **(I)**.
  - **Default:** before GATE-P the planning orchestrator appends a correction commit. It replaces the literal with
    `"$(openssl rand -hex 32)"`, as the neighbouring `SIG_INTAKE_ABUSE_SECRET` already does, with a dated note. The
    operator confirms the value was never used anywhere real (Q-H2-2). The history then publishes as is, and the
    tracked tree scans clean.
  - **If the operator says it was real:** rotate it, and either import the planning directory as a redacted copy
    (the #155 pattern, keeping the local planning branch as provenance and recording its head sha) or rewrite the
    **unpublished** planning commits. Either choice is an operator decision recorded verbatim. Never rewrite
    published history.
- **P-2: guard interplay (NEW-11).** If the Stage-B guard core (B4 §6.1) runs G1/G2 in `--range base...head` mode, it
  evaluates all planning commits. B4 NEW-1 (24 change-log stamps 5–152 min after their commits) will fail it unless:
  - the orchestrator's dated correction entry for NEW-1 lands first, **and**
  - `record_policy/dates.toml` carries an explicit, expiring entry naming those planning commits.

  The planning directory must not be blanket-exempted.

**After GATE-B.** The planning directory on the chain is read-only history: later changes to the plan go through
tickets. The operator may remove the planning worktree after the seed PR exists. The branch ref is kept until the seed
PR is merged; it is an ancestor, so deleting it would lose nothing, but keeping it avoids confusion.

**Backup.** Until T6 the planning commits exist on one disk only. Pushing `claude/next-phase-planning` earlier, as a
backup, is also a first publication. It is safe only after P-1 is fixed, and it is the operator's call (Q-H2-6).

### 2.2 Branch naming

- **Round-11 branches:** `r11/<id>-<slug>`. `<id>` is the ticket id lower-cased with `.` → `-` (`P34.1` → `p34-1`,
  `P34.1a` → `p34-1a`). `<slug>` is at most 5 kebab words. The seed is `r11/seed`.
- **Why harness-neutral.** The chain's prefixes (`devin/` 188, `codex/` 1, `svitali/` 1) never tracked the harness.
  B5 shows P27.4+ ran on `devin/` branches under Claude trailers. OM-01 moves harness identity into trailers and run
  ledgers. No repo tool parses the prefix: `closeout_protocol.py`, `merge_dryrun.sh` and the tests match exact names
  only.
- **Rules.**
  - Names are never reused and never renamed after the PR is created. A rename would retarget dependents.
  - No `r11` branch may exist (a git ref-namespace conflict).
  - The operator may choose a different prefix (Q-H2-3). What matters is uniqueness and a stable name.

### 2.3 One ticket, one PR: lifecycle

| step | who | rule |
|---|---|---|
| branch | worker | `git switch -c r11/<id>-<slug>` **from the previous ticket's final head**, which is the LEDGER `chainTip` and must equal the previous PR's `headRefOid` (G3a checks it) |
| local gates | worker | §3.4 (`make ci-local` once TC-PIN lands; until then the explicit list). Record `locally-green` with commands and counts |
| open PR | worker | `gh pr create --base <previous branch> --head <branch> --title "<ID> — <title>" --body-file docs/build/pr/<ID>.md`. Not a draft (CI runs either way; drafts hide the stack from the operator) |
| PR body source | worker | **`docs/build/pr/<ID>.md` is the single source.** Header fields in this order: `Round/row` · `Base` (branch, `#prev`, "merge after #prev") · `Run:` (verbatim) · `Ticket:` · `Requirement ids:` · `Harness/model` (OM-01) · `Production touched` (OM-14) · `Status layer` (OM-06) · `CI:` (G3a line; §4.5) · `CI config changed: yes/no` (§4.7). After the closeout, `gh pr edit <n> --body-file docs/build/pr/<ID>.md` keeps the PR equal to the file (tolerating a trailing newline). No separate "record PR #N" stamp commits (B5 NEW-7) |
| CI wait | worker | §4.6. Never push the closeout while a run on the pre-closeout head is still running. `cancel-in-progress` would cancel it and destroy the evidence |
| closeout | worker | one commit (OM-02), only after the pre-closeout head is green (§4.6) |
| boundary | orchestrator | G3a on the **final** head plus the Round-11 stack plus the G3c delta (§4). Only then is the next ticket dispatched |
| immutability | everyone | once the next ticket's branch exists, no one pushes to this branch. A later fix goes **forward on the tip** as a `repair` naming the red sha. A moved non-tip head is an off-protocol change, and G3c sets `blockedOn` (§4.2) |
| never | agents | merge; retarget; rebase; force-push; `git merge main` or "Update branch"; delete branches; change settings, rulesets, variables or secrets. **Sole exception:** the operator directs that a fix made on `main` or a pre-#190 branch be mirrored. Then it is a byte-identical cherry-pick as a new commit on the tip (H1 §3.3) |

Permitted agent GitHub writes: pushing new commits to the current tip branch; `gh pr create` and `gh pr edit
--body-file` on its own PR; and, if Q-H2-4 says yes, one `gh run rerun --failed` per head for an allowlisted flake
(§4.4). Scheduled workflows run on `main` only. A ticket that changes one must name `gh workflow run <wf> --ref <branch>`
in its contract if it wants a pre-merge execution. That is a GitHub write the contract must authorize.

### 2.4 The operator's later bottom-up merge: extending H1

H1 §3–§4 stands (the TOP=190 sitting, the green checkpoints #154/#164/#178/#184, and the tree invariant `64a23cd7…`).
Round 11 adds five things:

1. **Order.** The order is **#141 … #190 → seed (#192 expected) → the Round-11 tickets in stack order**. Derive the
   stack from base links, not from PR numbers: an unrelated PR or issue can take a number mid-round, as #191 did in
   Round 10. Walk the links (read-only):

   ```bash
   b=devin/p33-8-agent-docs-refresh; TOP=<last Round-11 PR whose ticket is DONE with a G3a pass>
   while :; do
     kids=$(gh pr list --state open --base "$b" --json number,headRefName --jq '.[]|"\(.number) \(.headRefName)"')
     [ -z "$kids" ] && break
     [ "$(printf '%s\n' "$kids" | wc -l | tr -d ' ')" = 1 ] || { echo "STOP: fork in stack at $b"; break; }
     echo "$kids"; n=${kids%% *}; b=${kids#* }; [ "$n" = "$TOP" ] && break
   done
   ```

   Merge each listed PR with `gh pr edit <n> --base main && gh pr merge <n> --merge --delete-branch=false` (H1 §4). The
   seed is merged only after GATE-B, and never a PR whose ticket is in progress (H1 NEW-5).
2. **Every Round-11 PR is a green checkpoint.** G3a guarantees each final head passes, so the operator can stop after
   any of them. That is unlike #165, #179 and #185.
3. **The tree invariant extends.** After merging through PR *k*, `origin/main^{tree}` must equal `<head of k>^{tree}`.
   A mismatch triggers H1 §2d's `git revert -m 1` rollback, never a reset.
4. **Merge commits only.** Squash or rebase of a stacked PR orphans its descendants: their diffs would re-include the
   squashed content and conflict. See the settings in §5 S-3.
5. **Merging while Round 11 runs is safe.** Prefix bases stay, because `delete_branch_on_merge=false` means dependents
   are not auto-retargeted. Merged branches are immutable by §2.3, and G3c records the merges (OM-17). A retarget does
   not trigger CI (H1, (I)). Once #190 is merged, `main`'s tree equals the Round-11 base's tree, so the recorded green
   stands. If `main` carries content outside the chain again (as `d4522d82` did), re-run `merge_dryrun.sh` and mirror
   the fix forward (§2.3) before merging further.

---

## 3. CI expectations per PR

### 3.1 Required checks

- **The set.** `ci_required.toml` (B4 §3) = **`python`, `docs`, `composed`, `security`, `web`**, the five `CI` jobs,
  on **every** Round-11 PR including docs-only and closeout-only changes. There are no path filters: #165/#179/#185
  show that record-only commits turn `python` red.
- **Adding a job.** A new required job is added to `ci_required.toml` in the same PR. The operator adds it to the ruleset
  (§5 S-1).
- **Not required per PR:** the scheduled workflows. They run on `main` only (§1.1).

### 3.2 Inherited or new: verified

- **No inherited red at the Round-11 base (live-read).** A Round-11 PR's `pull_request` run tests `refs/pull/N/merge`,
  its head merged into its chain base. The base content descends from `b051732c`, whose five sha-bound check-runs are
  `success` (run 36494519255). The #141–#154, #165, #179 and #185 reds are failures of **those PRs' heads against their
  own bases**. They are not in any Round-11 merge ref beyond what #155/#166/#180/#186 already fixed (H1 §2a–§2c). **H1's
  "none after #155" holds, as refined: none at #190.**
- **Scope of G3a.** Its stack scope therefore starts at the seed PR, with #190 @ `b051732c` checked once as the anchor.
  Pre-#190 reds are H1 merge-readiness facts. OM-05 says "a red inherited from the base is still a block". Whether the
  pre-#190 reds count as "inherited" is an interpretation the operator confirms at S5 (Q-H2-1); the agent does not
  decide it.
- **Latent reds (not yet red; they appear with time).**
  - *Clock-dependent tests:* B4 NEW-3's 2026-10-10 replay, G2 NEW-8's 10-01…10-21 trigger window. #190 last ran at
    2026-09-28T22:48Z. Such a red on an untouched test is classed `inherited-latent`. It **still blocks** (OM-05) and is
    fixed forward on the tip. It is never waived by an agent.
  - *Runner drift:* the 2026-10-19 `ubuntu-latest` → Ubuntu 26 switch (NEW-6). TC-PIN removes it.
  - *Advisory drift:* npm counts rose 14 → 18 with no commit (NEW-9). Not a red today, because nothing gates it.

### 3.3 Seed-PR preflight: expected **new** reds (T6 fixes them before asking for GATE-B)

| # | check | cause | fix owner |
|---|---|---|---|
| 1 | `security` (`make scan-secrets`) and `python` (`test_secret_scan_real_tree_is_clean`) | NEW-1: 2 credential-shaped literals in the planning notes (verified locally: 1 failed / 1411 passed) | planning orchestrator (a forward fix before GATE-P) + Q-H2-2 |
| 2 | `python` | B4 NEW-3: six real-tree pins that C6/C8/T4 edits would turn red | B4 §6.1 conversions in the guard-core commit |
| 3 | `docs` (guard core, if in the seed) | NEW-11: G1 on the planning ledger's late stamps (B4 NEW-1) | orchestrator correction entry + expiring `dates.toml` entry |
| 4 | any | latent clock reds, if T6 runs after 2026-10-10 | fix forward in the seed |

Carrying the planning directory alone caused exactly row 1 in the local run. The layout gate and both docs detectors are
clean on this tree (§1.5).

### 3.4 Local gates, `make check` parity, and the Docker suites

- **Parity is claimed but false (NEW-10).** `Makefile:5-6` says "whatever CI runs, `make check` runs". It does not.
  `make check` = lint, format-check, typecheck, test, verify-gen. It omits:
  - `docs-check` and `check-build-memory`;
  - `scan-secrets`, `scan-licenses` and the leak test;
  - composed e2e *with* `web/node_modules`;
  - the whole `web` job.

  Separately, `npm run check` omits `check:perf` and the Playwright browser install.
- **Docker.** In CI the `python` and `composed` jobs run the Docker suites for real (`SIG_REQUIRE_DB_TESTS=1`;
  ubuntu-24.04 ships dockerd; see the skip reasons in §1.2). Locally the daemon is down today, so a plain `make check`
  **skips** `tests/db` and `tests/e2e` silently.
- **Rule until TC-PIN lands.** Workers run, and record the counts of:

  ```bash
  SIG_REQUIRE_DB_TESTS=1 make check        # fails loudly without Docker
  make docs-check && make scan-secrets && make scan-licenses
  # web-touching tickets:
  npm --prefix web ci && npm --prefix web run check && npm --prefix web run check:perf
  ```

  - If Docker is unavailable, the record reads `locally-green (db/e2e not run: docker down)`. A ticket that touches
    `db/`, `api/` or `tests/e2e` may not close on that. Its CI run is then the only proof, and G3a requires it anyway.
  - **Never run `npm install` in `web/`** before TC-PIN. The local npm 11.6.2 rewrites the lockfile differently from
    CI's npm 10.9.8, which was the recurring repair loop (H1 NEW-2, NEW-7). Use `npm ci` only. A lockfile change
    before TC-PIN is a stop-and-ask.

### 3.5 Early tickets (working names; T3 numbers them and checks size)

**TC-PIN: toolchain pin and CI hygiene.** This is the first engineering ticket after the seed, or part of row 201
under B4's Q-14 fallback. It **must land before 2026-10-19.**

1. **Node.**
   - `web/.nvmrc` holds an exact **Node 24 LTS** version, chosen at ticket time from what `setup-node` resolves.
     Node 24 is the lowest line that satisfies every engine in the committed lockfile:
     - license-checker-rseidelsohn@5.0.1: `>=24`, npm `>=11`;
     - vitest 4.1.11: `^20 || ^22 || >=24`;
     - astro 7.2.4: `>=22.12`.

     Node 22 cannot satisfy the first under `engine-strict`.
   - `web/package.json`: `"engines": {"node": ">=24 <25", "npm": ">=11 <12"}` and
     `"packageManager": "npm@11.<x>.<y>"`.
   - `web/.npmrc`: `engine-strict=true`.
   - Every `setup-node` step (ci `composed`/`web`, nightly, keepalive) uses `node-version-file: web/.nvmrc`. It is
     followed by an explicit `npm install -g npm@<packageManager version>` (or corepack, chosen and justified in the
     ticket). The job log records `node -v` and `npm -v`.
   - **Fallback** if Node 24 breaks the web gates: an exact Node 22 pin plus a license-checker version whose engines
     admit 22. That choice is recorded in an ADR.
2. **Lockfile.** Regenerate **once** under the pinned toolchain in this PR (the one allowed regeneration; recorded
   blob sha).
   - Add a CI step, `npm install --package-lock-only --ignore-scripts && git diff --exit-code web/package-lock.json`,
     so any lockfile the pinned npm would write differently fails at PR time.
   - A later lockfile fix is a byte-identical cherry-pick or a regeneration under the pin, never an ad-hoc local
     install (H1 §2a).
   - This changes the blob from `da838491` for Round 11 only. The #141–#190 invariant (H1 §2d) is unaffected.
3. **uv and Python.**
   - `[tool.uv] required-version = "==0.12.6"` in `pyproject.toml`, so local drift fails loudly.
   - Keep `setup-uv` at 0.12.6, or have it read the project setting (verify support at ticket time).
   - Optionally pin `.python-version` to an exact patch.
4. **Runner and actions.**
   - `runs-on: ubuntu-24.04` in all 9 jobs.
   - Bump `actions/checkout`, `actions/setup-node` and `actions/upload-artifact` to the majors that target Node 24
     (verify at ticket time).
   - The move to Ubuntu 26 later is its own ticket.
5. **Pipefail (NEW-3).**
   - Workflow-level `defaults: run: shell: bash` in all 5 workflows. This gives `bash --noprofile --norc -eo pipefail`.
   - A unit test asserts it for every workflow. A mutation case in `tmp_path` shows that `false | tee x` now fails the
     step.
6. **`main` runs complete.**
   - `cancel-in-progress: ${{ github.event_name == 'pull_request' }}` (H1 NEW-4, B4 §3).
   - The `docs` job also runs on `push` to `main` (B4 NEW-9). This deliberately changes the invariant pinned by
     `test_ci_docs_job_runs_only_on_pull_requests`. The test is rewritten to the new policy in the same PR, with an ADR
     (a policy change, not a relaxed living-record pin; OM-15 does not apply).
7. **`make ci-local`.**
   - It runs the five jobs' commands locally: `SIG_REQUIRE_DB_TESTS=1` test, docs-check, scans, composed e2e with web
     deps, and the web check plus perf.
   - A parity unit test maps every `run:` line in `ci.yml` to a target reachable from `ci-local`.
   - `Makefile:5-6` is corrected.
8. **G3e test.** CI's node major equals `.nvmrc`, and every devDependency `engines` range is satisfiable by the pinned
   node/npm (B4 G3e).

**TC-TRUTH: the CI-truth verifier and gates.** This is B4's "CI-truth" ticket, extended.

- G3b recorded-CI verifier.
- G3c external-state delta.
- `ci_flakes.toml` plus the re-run log (§4.4).
- Lighthouse stabilisation (`numberOfRuns: 3` with median aggregation, or move the score assertion to nightly and keep
  the byte budgets per-PR; an ADR decides, ADR-134 budgets unchanged).
- A fix for the PY-SUBSTR-1 test defect: assert on fields, not on `str(row)`.
- An **npm advisory gate** (NEW-9): `npm audit --omit=dev --audit-level=high` per-PR, or nightly with an allowlist file
  carrying expiry. The level is decided in the ticket.
- The `security` leak check made non-vacuous (NEW-4): either the operator sets the variable (§5 S-4), or the step fails
  in CI when it is unset.

Both tickets change CI configuration and therefore carry the §4.7 disclosure.

---

## 4. The orchestrator's CI gate (G3a), exactly

This refines B4 G3a and B5 OM-05. It is harness-neutral: it uses only `git`, `gh` and the Python stdlib. It is binding
through the OPERATING MODE before `ci_boundary.py` exists. Until then the orchestrator performs the same steps by hand
and records them in the same shape.

### 4.1 Sources of truth

1. **The PR.** `gh pr view <n> --json number,state,isDraft,headRefOid,baseRefName,mergeable,mergeStateStatus`.
2. **The checks, bound to the sha.**
   `gh api repos/SteveVitali/Eleutheria/commits/<sha>/check-runs --paginate`, filtered to `app.slug == "github-actions"`
   and names in `ci_required.toml`. If a name has several check-runs (re-runs), take the one with the highest `id`.
   `run_id` comes from `details_url`.
   - `gh pr checks` is a convenience display only. Its JSON has no sha field (bucket, completedAt, description, event,
     link, name, startedAt, state, workflow), and its exit codes collapse states (8 = pending). A boundary that reads it
     can attribute a superseded head's result (NEW-12).
3. **Failure detail.** `gh api repos/…/check-runs/<id>/annotations` (the billing and runner messages live here), plus
   `gh run view <run> --log-failed` for the first failing line.
4. **The stack.** For the open Round-11 PRs (seed … *n*), each final head's recorded sha-bound result and the
   Round-11 heads digest (`sha256` of `number headRefOid`, as A1 did). The anchor #190 @ `b051732c` is checked once, at
   the seed boundary.

### 4.2 Green, pending, red

**Green:** all of the following hold at the boundary.

- (a) `headRefOid` == the local `chainTip` sha == the pushed branch head;
- (b) `baseRefName` == the previous stack branch (the anchor for the seed);
- (c) the PR is `OPEN`, not a draft, and `mergeable != CONFLICTING`;
- (d) **all five** required check-runs exist for that sha with `status: completed` and `conclusion: success`;
- (e) every open Round-11 ancestor is still green on its recorded final head, and the Round-11 heads digest changed only
  by this ticket's own PR.

**Pending:** a required check-run is `queued` or `in_progress`, or is not yet registered within the grace period.

**Red:** everything else.

- `failure`, `cancelled` (on this sha), `timed_out`, `action_required`, `startup_failure`, `stale`, `neutral`, or a
  **`skipped` required job**;
- a required check still missing after the grace period;
- head, base or stack mismatches;
- conflicts;
- a moved ancestor head.

"Mostly green", "green except web" and "green locally" are all red.

### 4.3 Wait, poll, timeout

- **Poll** every **60 s** from the moment the head was pushed (the push time is recorded).
- **Registration grace: 5 min.** Zero required check-runs is `pending` until then. After that, check
  `gh run list --commit <sha>`:
  - if no run exists at all, the result is `missing` (red; the workflow did not trigger);
  - if a run exists but is still `queued`, keep waiting.
- **Deadline: 45 min** from the push (B4's value). That is 5.4× the slowest green PR run in 187 first-attempt successes
  (8.3 min). At the deadline the result is `pending` → exit 4 → `blockedOn: CI pending …`. If **no job ever started**,
  classify as `unavailable-queue` (§6).
- **API or `gh` errors:** 3 retries with 30/60/120 s backoff, then exit 5 (`unavailable-api`). This is never green.
- **Don't cancel CI while waiting.** Never push another commit to the same branch while a run on the previous head is
  still running. The concurrency group would cancel it and destroy the evidence (100 PR runs were cancelled this way).

### 4.4 Flakes and re-runs

- **The allowlist.** `docs/build/tools/record_policy/ci_flakes.toml` has entries of the form
  `{id, job, step, pattern, evidence_runs, tracking (BL/ticket), expires}`.
  - **Initial entry `LH-PERF-1`:** job `web`, step "Performance budgets (build fails on regression)", pattern
    `categories.performance failure for minScore`, evidence 35051006427 / 35263896936 / 35889213151 / 36065771273 /
    36338778274. It expires when TC-TRUTH's Lighthouse fix lands.
  - **Initial entry `PY-SUBSTR-1`:** job `python`, pattern
    `test_elapsed_time_never_written_to_the_submission_row - assert '8.5' not in`, evidence 35296544560. This is a test
    defect, not an environment flake. TC-TRUTH fixes it by asserting on the row's fields, not a substring of
    `str(row)`, and the entry expires then.
  - Adding an entry is a PR diff with evidence runs. It is disclosed under §4.7.
- **One re-run.** A failure whose **first failing line** matches an unexpired entry gets **exactly one**
  `gh run rerun <run_id> --failed` per head (subject to Q-H2-4). Both attempts are recorded:

  ```
  ci: pass-after-rerun #<n>@<sha7> (web a1 fail LH-PERF-1 run <id>; a2 pass)
  ```

  A second failure is red. Every re-run is appended to `docs/build/reports/ci/flake_log.csv` (TC-TRUTH). Three uses of
  one entry in a round escalate its fix (OM-18).
- **Anything not on the allowlist is not re-run.** That includes Docker/testcontainers timeouts, Playwright timeouts and
  "it passed locally". It is red, and the fix goes forward or the operator is asked.
- **Never loosen to pass.** Agents never quarantine, skip, `xfail` or loosen a test or threshold to make CI pass. That is
  the #186 pattern (H1 NEW-6, OM-15). Quarantine is an operator-visible ticket with an ADR.
- **Re-runs after an outage** (§6) re-run runs that never executed. They are not flake re-runs, and they are recorded
  as `unavailable` → `pass`.

### 4.5 Recording and `blockedOn`

- **`ci-boundary/1` JSON** goes in the run ledger (B4). It holds `{pr, head_sha, base, checks:[{name, run_id,
  attempt, conclusion, completed_at, first_failing_line}], class, reruns, stack_digest, ci_now}`, plus the B4 G3c
  delta (`origin/main` sha; `merge-base --is-ancestor origin/main <chainTip>`; merges since the last boundary;
  off-stack PRs).
- **PHASE LOG / boundary line (OM-17):**
  `ci: pass #<n>@<sha7> (python <run>; docs <run>; composed <run>; security <run>; web <run>)`, or `locally-green` when
  CI never ran (§6).
- **Red → `blockedOn`, `nextTicket` unchanged, stop (OM-12/OM-18):**
  `blockedOn: CI <fail|cancel|missing|pending|unavailable|conflict|stack> on #<n>@<sha7> (<job>): <class>: <first failing line or annotation>`
- **`class` values:**
  - `new`: the failing test or step is touched by `base..head`, or the base head passed the same check;
  - `inherited-latent`: the base head's recorded check passed, and the diff does not touch the failing area (a clock,
    environment or advisory change);
  - `flake-exhausted`;
  - `unavailable-billing`, `unavailable-outage`, `unavailable-queue`, `unavailable-api`;
  - `stack`: a moved ancestor, a wrong base, or a head mismatch.

  Every class blocks. They differ only in who fixes: a forward fix on the tip, versus the operator (billing, settings,
  waivers).
- **Exit codes (B4 contract, extended):** 0 pass · 3 red · 4 pending · 5 unavailable (B4 had "`gh` unavailable"; H2
  widens it to every CI-cannot-run class).

### 4.6 Worker obligations: no close on red

1. **Wait on the pre-closeout head.** After pushing the implementation head, the worker waits (per §4.3) for that sha.
2. **Fix a red forward.**
   - A red `new` is fixed forward on the **same** branch. This is allowed because no successor exists yet. The limit is
     3 fix pushes, each recorded in the run ledger with its run id and first failing line.
   - After 3 fixes, or on any red that is not `new`, the worker writes **no closeout**. It reports `blocked` with the
     G3a line, and the orchestrator sets `blockedOn`.
3. **Write the closeout (OM-02) only when the pre-closeout head is green.** It is one commit carrying that head's `ci:`
   line. It is pushed only after that run has completed.
4. **Wait on the final head.** The closeout push re-triggers CI. The worker waits for the final head and reports its
   result, but the orchestrator re-reads it independently (P6).
   - A red on the final head is almost always a living-record pin or a malformed record: the #165/#179/#185 classes.
     The fix is a `repair` commit on the same branch (still no successor).
   - The PHASE LOG gets an appended `repair`/`blocked` entry. The `done` entry is never edited (P7).
   - The orchestrator does not dispatch until the final head is green.
5. **Audit (G3b, TC-TRUTH).** A `done` PHASE LOG entry without a `ci:` line that verifies against the GitHub API fails
   the `docs` job. The orchestrator's hand-check does the same until then.

### 4.7 PRs that change CI itself

A `pull_request` run uses the workflow files **from the PR's own merge ref**, so a PR that weakens CI is validated by
the weakened CI (I; documented Actions behaviour). With one collaborator, CODEOWNERS cannot supply independence (§5 S-6).

- **Scope.** Any PR that touches `.github/workflows/**`, the Makefile gate targets, `pyproject.toml`
  `[tool.pytest]`/`[tool.ruff]`/`[tool.mypy]`, `web/lighthouserc.json`, `web/playwright.config.*`, `ci_required.toml`,
  `ci_flakes.toml` or `record_policy/**` must:
  - set `CI config changed: yes` in its body and list the effect;
  - carry an ADR if it removes or loosens a gate;
  - be flagged by G3a in the boundary line and the operator digest (OM-17).
- **The seed and TC-PIN/TC-TRUTH are such PRs.**

---

## 5. Repository settings: operator actions (not executed)

| id | action | when | why / evidence |
|---|---|---|---|
| **S-1** | Make ruleset "main" (21702901) effective:<br>• `conditions.ref_name.include: ["~DEFAULT_BRANCH"]`, which is **empty today**;<br>• keep `deletion` + `non_fast_forward`;<br>• add `pull_request` with **0** required approvals;<br>• add `required_status_checks` {python, docs, composed, security, web} (GitHub Actions) with `strict_required_status_checks_policy: false`;<br>• no bypass actors;<br>• `enforcement: active` | **after** the #141–#190 sitting (Q-B4-3), or during it only with a recorded temporary bypass that is removed at the end | NEW-5; B5 NEW-2 (recommended 09-09, never applied).<br>• **Strict** would force stack branches to be updated with `main`, which is forbidden.<br>• **Approvals** are impossible for a solo author.<br>• An **admin bypass** is also the agents' bypass, because they act with the operator's admin token (B4 §2.3).<br>• Before the sitting, required checks would block #141–#154 and #165/#179/#185. Their recorded checks are red, and a retarget does not re-run them (H1) |
| **S-2** | New ruleset "stack": `refs/heads/r11/**` (optionally also `devin/**`, `codex/**`) with `non_fast_forward` + `deletion`, no bypass, active | before the seed push (T6) | Mechanically forbids agent rebases and force-pushes of the stack (H1 §3.1). Normal pushes are still allowed |
| **S-3** | Merge settings: `allow_squash_merge=false`, `allow_rebase_merge=false`; keep `allow_merge_commit=true`, **`delete_branch_on_merge=false`**, `allow_auto_merge=false`, `allow_update_branch=false` | any time | Squash or rebase orphans stacked descendants. Branch deletion on merge auto-retargets dependents to `main` mid-round. "Update branch" writes an out-of-chain merge commit (§2.3/§2.4) |
| **S-4** | Set repo **variable** `SIG_GCP_PROJECT`. It is not a credential (ADR-119). Alternatively approve TC-TRUTH making the step fail when unset | any time | NEW-4: 0 variables, so the leak check skipped on every run, although D-P30.4-4 was closed as "Armed in CI" |
| **S-5** | Check GitHub **Billing & plans** (payment method, Actions spending limit) and add a billing/usage alert routed to the operator's address (§7.1 routing) | before Round 11 | NEW-2: two block windows 09-17…09-22. The repo is public today, and standard hosted runners are free for public repos (I). The blocks show the account state can still stop CI |
| **S-6** | **No CODEOWNERS** and no required reviews | revisit when a second maintainer exists | One collaborator (ADMIN). An author cannot approve their own PR, and agents share the identity, so ownership adds no independence (B4 §2.3; G4c/Q-B4-2 is the signing-key route) |
| S-7 | Optional: restrict Actions to GitHub-owned, verified and `astral-sh/*` actions; consider `sha_pinning_required` later | low priority | Today `allowed_actions: all` |
| — | `main` run cancellation is **code**, not a setting: TC-PIN item 6 | TC-PIN | H1 NEW-4: 117 of 142 `main` push runs were cancelled. Until TC-PIN, verify the final `main` state after each sitting (H1 §4 step 3) |

The operator does these by hand, or with `gh api -X PUT/PATCH/POST`. No agent executes them (P3/§2.3), and each is
recorded in GATE DECISIONS with `date -u` when done.

---

## 6. When CI cannot run

**Detection signatures** (the classes of §4.5):

| class | signature | precedent |
|---|---|---|
| `unavailable-billing` | required jobs `failure` with **0 steps** and completed within seconds; annotation "The job was not started because recent account payments have failed or your spending limit needs to be increased" | 40 run attempts, 2026-09-17T01:13Z → 09-22T16:01Z (NEW-2) |
| `unavailable-outage` | `gh`/API 5xx, or runs stuck `queued` with no job started past §4.3's deadline; `https://www.githubstatus.com/api/v2/status.json` (read-only GET) shows an incident | none recorded |
| `unavailable-queue` | runs created but no job started by the deadline, with no incident | none recorded |
| `unavailable-api` | `gh` auth or network failure after retries | — |

**Procedure: honest recording, no fabricated green.**

1. **Stop.** G3a exits 5. The orchestrator writes
   `blockedOn: CI unavailable on #<n>@<sha7>: <class>: <annotation first line>`, leaves `nextTicket` unchanged, and
   stops (OM-12/OM-18). The OM-17 line names it. Nothing is written as `ci: pass`. No run id is cited that was not read
   from the API (G3b audits this).
2. **Ask the operator**, who chooses verbatim (OM-07/OM-09):
   - **(a) wait** and re-check hourly;
   - **(b) fix the cause** (billing, S-5), then re-run the never-started runs;
   - **(c) a CI-unavailable waiver W-n.** It names the ticket ids it covers, an expiry (date or ticket), and what voids
     it (OM-10).
3. **Under a waiver:**
   - Each ticket runs `make ci-local` in full, with Docker **up**. That means `SIG_REQUIRE_DB_TESTS=1`, the web
     check+perf and the scans.
   - It records `ci: unavailable (W-n) · locally-green (<commands, counts>)`.
   - Status never rises above `engineered` (OM-06).
   - If Docker is also down, the waiver cannot cover tickets touching `db/`, `api/` or `tests/e2e`. Those wait.
4. **`ci-owed` sweep.** Each waived head gets a `ci-owed` entry. When CI returns, the orchestrator runs G3a bottom-up on
   every waived head before any further dispatch. Waived heads received no pushes, so they are re-run as they stand. A
   red found then is `blockedOn`, and the fix goes forward on the tip as a `repair` naming the red sha. The waiver
   closes with a dated GATE DECISIONS entry listing each head's real result.
5. **Never allowed:**
   - re-running until green;
   - treating a never-started job as a pass;
   - writing a `ci:` line from memory or from `gh pr checks` without sha binding;
   - substituting local results for CI without a waiver.

---

## 7. Paste blocks for T5 (OPERATING MODE additions) and the ticket template

```
H2 — Round-11 PR/CI clauses (refine OM-05, OM-12, OM-17; binding on every harness)

PR-1 STACK. One ticket = one branch r11/<id>-<slug> = one PR; base = previous ticket's branch (seed: devin/p33-8-agent-docs-refresh);
     body = docs/build/pr/<ID>.md (single source; `gh pr edit --body-file` after closeout). Agents never merge, retarget,
     rebase, force-push, merge main, "Update branch", delete branches, or change settings/rulesets/variables/secrets.
PR-2 IMMUTABLE PREFIX. Once a successor branch exists, nobody pushes to a branch; later fixes go forward on the tip as a
     `repair` naming the red sha. A moved non-tip head sets blockedOn (stack).
CI-1 REQUIRED. python, docs, composed, security, web (ci_required.toml) on the current head, every PR incl. docs-only.
CI-2 SHA-BOUND READ. Truth = commits/<sha>/check-runs for the pushed head == chainTip == headRefOid; `gh pr checks` is display only.
CI-3 WAIT. Poll 60 s; 5-min registration grace; 45-min deadline; API errors retried 3× then unavailable. Never push to a branch
     while its previous head's run is in progress.
CI-4 RED. failure|cancelled|timed_out|action_required|startup_failure|stale|neutral|skipped-required|missing|conflict|stack
     → blockedOn: CI <state> on #<n>@<sha7> (<job>): <class>: <first failing line>; nextTicket unchanged; stop.
     Classes new / inherited-latent / flake-exhausted / unavailable-* / stack all block.
CI-5 FLAKES. Only failures matching an unexpired ci_flakes.toml entry get one `gh run rerun --failed` per head; both attempts
     recorded; never quarantine, skip, xfail or loosen to pass.
CI-6 CLOSE. Closeout only after the pre-closeout head is green; final head re-read by the orchestrator before dispatch.
CI-7 UNAVAILABLE. CI that cannot run is never green: blockedOn + operator choice (wait / fix / waiver W-n with ids+expiry);
     waived work is `locally-green` via `make ci-local` with Docker up, and owes a bottom-up re-verification when CI returns.
CI-8 CI CHANGES. PRs touching workflows, gate targets, test config, thresholds or record_policy say `CI config changed: yes`,
     carry an ADR if they loosen a gate, and are flagged in the boundary line.
CI-9 TOOLCHAIN. Before TC-PIN lands: `npm ci` only in web/, never `npm install`; any lockfile change is stop-and-ask.
```

Ticket-contract lines (add to B5 §6.2's block):

```
- [ ] Branch r11/<id>-<slug> from chainTip; PR base = previous branch; body = docs/build/pr/<ID>.md.       (PR-1)
- [ ] Pre-closeout head green on all 5 required checks (sha-bound), recorded as the `ci:` line; closeout pushed after. (CI-2/CI-6)
- [ ] Local: `make ci-local` (or the §3.4 list) with Docker up, or `locally-green (… not run: reason)`.        (P11)
- [ ] CI config changed: yes/no (+ ADR if a gate is loosened).                                              (CI-8)
```

---

## 8. New findings (`findings/incoming/H2.csv`)

| id | title (short) | sev | routed |
|---|---|---|---|
| NEW-1 | A credential-shaped `SIG_INTAKE_FORM_SECRET` literal in two committed planning notes (C1 `PROTOCOL.md:538`, C4 `R10_PREVIEW.md:82`) fails the tracked-tree secret scan, so a seed PR carrying the planning directory is red on `security` + `python`. Pushing the unpublished history would publish it to a public repo | S2 | planning orchestrator (forward fix), T6, Q-H2-2 |
| NEW-2 | Actions could not start any job for 40 run attempts on 14 PR branches (2026-09-17T01:13Z → 09-22T16:01Z; payment/spending-limit annotation). The chain landed P25.10 and P26.2–P26.19 through it, unrecorded | S2 | H2 §6, B4 G3a, G1 (billing alert) |
| NEW-3 | The nightly gate cannot go red on its four stages: `… \| tee` under `bash -e` (no pipefail) makes each outcome `tee`'s. "nightly 6/6 success" is not evidence; the same pattern is in `reingest.yml:69` | S2 | TC-PIN, B4 G11, A1 |
| NEW-4 | D-P30.4-4 closed as "Armed in CI", but the repo has 0 Actions variables, so the `security` job's GCP-id leak check skips on every run (1 skipped on #190) | S2 | F1, TC-TRUTH, §5 S-4 |
| NEW-5 | The disabled "main" ruleset targets no branch (`include: []`) and has only deletion/non-FF rules. Squash and rebase merges, which orphan stacked descendants, are enabled | S3 | §5 S-1/S-3 |
| NEW-6 | `ubuntu-latest` switches to Ubuntu 26 from 2026-10-19 and all 9 jobs use it; the actions run on a deprecated Node 20 target. Round-11 CI would change mid-round | S2 | TC-PIN (deadline 10-19) |
| NEW-7 | H1 NEW-2 amended with a live read of the local side: the build machine runs node v25.2.1 / npm 11.6.2 while CI runs 22.23.2 / 10.9.8, and no pin file exists | S2 | TC-PIN |
| NEW-8 | Two known CI flakes. Lighthouse `check:perf` (`numberOfRuns: 1`, error-level performance ≥0.9) went red → green on a same-sha re-run 5 times. A python substring assertion (`"8.5" not in str(row)`) did so once | S3 | TC-TRUTH (`ci_flakes.toml` LH-PERF-1, PY-SUBSTR-1) |
| NEW-9 | npm advisories are ungated: 14 (1 critical, 7 high) on #190 and 18 (1 critical, 10 high) on the 09-30 nightly for the same lockfile. The audit covers Python only (SIG-SEC-006) | S2 | TC-TRUTH, F5 |
| NEW-10 | `make check` is not a CI mirror despite `Makefile:5-6`. It omits docs, scans, composed-with-web and the web job; `npm run check` omits perf. With Docker down (18:12Z) plain `make check` also skips `tests/db` and `tests/e2e` | S2 | TC-PIN (`make ci-local`), OM-05 wording |
| NEW-11 | (I) Seeding by ancestry puts the planning commits in the seed PR's `--range`. B4 NEW-1's late stamps will fail the G1 guard core unless the correction entry and an expiring `dates.toml` entry land first | S2 | B4, T6, planning orchestrator |
| NEW-12 | `gh pr checks` JSON has no sha field, so a boundary reading it can attribute a superseded head's result. The sha-bound source is `commits/<sha>/check-runs` | S3 | B4 G3a amendment |

---

## 9. Open questions for the operator (recorded, not answered)

- **Q-H2-1 (S5).** Confirm that the pre-#190 PR reds (#141–#154 on `composed`/`web`; #165, #179 and #185 on `python`)
  are merge-readiness items for your integration and **do not** block Round-11 boundaries. Under this reading, OM-05's
  "inherited from the base" applies from the Round-11 anchor (#190 @ `b051732c`, 5/5 green) upward.
- **Q-H2-2 (before GATE-P).** Was the `SIG_INTAKE_FORM_SECRET` value in the C1/C4 notes a throwaway local value, never
  used in any deployed or staging configuration?
  - **Yes:** forward fix, and the history publishes as is.
  - **No:** rotate it, then choose a redacted copy import or a rewrite of the unpublished planning commits (§2.1 P-1).
- **Q-H2-3 (T5).** Branch prefix: harness-neutral `r11/<id>-<slug>` (recommended), or a harness prefix?
- **Q-H2-4 (T5).** May the orchestrator perform **one** `gh run rerun --failed` per head for an allowlisted flake? This
  is a GitHub write. If no, every flake becomes `blockedOn` for you to re-run.
- **Q-H2-5 (with Q-B4-3).** Timing of S-1 (after the #141–#190 sitting is recommended), plus S-2/S-3 before the seed
  push, S-4, and S-5 before Round 11.
- **Q-H2-6.** Push `claude/next-phase-planning` before T6 as an off-disk backup? It is a first publication, so only
  after NEW-1 is fixed. Or keep it local until T6?

---

## 10. Reproduction (read-only)

```bash
date -u                                                      # 18:03:52Z (start) … see closing stamp below
gh pr view 190 --json headRefOid,baseRefName,state,mergeable,mergeStateStatus
gh pr checks 190; gh pr checks 190 --json name,state,bucket,startedAt,completedAt,link,workflow,event
gh api repos/SteveVitali/Eleutheria/commits/b051732c3c6ed11d7ebb2343a4414f2fc281fd2a/check-runs
gh api repos/SteveVitali/Eleutheria/actions/runs/36494519255 --jq '{head_sha,run_attempt,conclusion}'
gh run view 36494519255 --job <id> --log | grep -E 'passed|SKIPPED|vulnerabilities|Image:|node:|EBADENGINE'
gh pr list --state open --limit 200 --json number,headRefOid,statusCheckRollup    # rollup per PR; digest 8331f062…d088
gh run list --workflow CI --limit 1000 --json databaseId,headSha,conclusion,attempt,event,headBranch,createdAt,updatedAt,startedAt
gh api repos/…/actions/runs/<id>/attempts/1/jobs ; gh api repos/…/check-runs/<job>/annotations   # never-started + flake classification
gh run view <id> --attempt 1 --log-failed | grep -E 'minScore|Assertion failed'
gh run list --workflow nightly.yml --limit 4; gh run view 36693848668 --log | grep -E 'shell: |verdict|vulnerabilities'
gh repo view --json visibility,…; gh api repos/SteveVitali/Eleutheria --jq '{allow_*,delete_branch_on_merge}'
gh api repos/…/branches/main --jq '{protected,protection}'; gh api repos/…/rulesets/21702901
gh api repos/…/actions/variables; …/environments; …/actions/secrets --jq '{total_count}'; …/collaborators; …/contents/.github/CODEOWNERS
git merge-base --is-ancestor b051732c HEAD; git rev-list --count b051732c..HEAD; git diff --name-only b051732c..HEAD
git ls-remote origin 'refs/heads/claude/*' 'refs/heads/codex/*'; gh pr view 155 --json commits,additions,baseRefName
uv --version; node --version; npm --version; docker info
PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest tests/unit -q -p no:cacheprovider   # 1411 passed, 1 failed (18:13:25Z)
uv run --frozen python scripts/ci/secret_scan.py; bash scripts/docs/check-build-memory.sh .
bash scripts/docs/check-repo-docs-freshness.sh .; bash scripts/docs/check-agent-docs-freshness.sh .
git log -p b051732c..HEAD | <secret_scan RULES over added lines>                     # 2 hits: 4df1552f, 2cf03075
python3 (web/package-lock.json engines scan)                                          # node ≥24 needed by 1 devDependency
```

**Timestamps (all `date -u`):** start 18:03:52Z; CI history fetched 18:05:41Z; heads digest re-checked 18:13:03Z;
local unit run 18:12:56–18:13:25Z; findings CSV written 18:27:12Z (NEW-8 amended 18:28:03Z); closing 2026-09-30T18:28:10Z.
