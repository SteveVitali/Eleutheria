# H1: Integration state record and merge-readiness notes

Row **H1** of `META_PLAN.md` (Stage P, Wave 2). Owner D, read-only. It was re-scoped at GATE-M (§7.1, Q-11): *the operator
merges later, and Round 11 builds on the chain tip.* This document **merges, retargets, pushes and tags nothing**. Every
command in §4 is for the operator to run later. None of them was executed by this row.

- **Authored:** 2026-09-30T16:40Z to 16:55Z (`date -u`) by Claude Code (Opus 5.5), in the planning worktree
  `/Users/stevenvitali/Eleutheria-next-phase` (`claude/next-phase-planning` @ `b210aa95`).
- **Baseline:** `baseline/BASELINE.md` (A1, frozen 2026-09-30T16:31:55Z). Re-checked here: `origin/main` is still
  `b7c9e2e3` (`git ls-remote`), and `gh.open_heads_sha256` is still `8331f062…d088`, recomputed from `gh pr list` at
  16:50Z. The stack has not moved since A1.
- **Evidence classes (P1):** `live-read` (git objects, `gh` API, Actions logs), `recorded-execution` (CI runs, and
  this row's merge simulation, §2c), `code`, and `inference` (labelled wherever it is used).
- **Read-only method.** This row used only `git log/diff/rev-parse/ls-remote/merge-base/merge-tree`, `gh pr/run/api`
  GETs, and a merge simulation. The simulation used `git merge-tree --write-tree` chained with `git commit-tree`, plus
  `git hash-object -w` for §2b's fix-forward what-ifs. That wrote dangling objects only: **no ref, branch, worktree or
  index of the repo was touched.** The temporary index files live in the session scratchpad, and git gc prunes the
  objects in the normal way. No temporary worktree was created.

---

## 1. Integration state (2026-09-30T16:50Z)

### 1.1 `origin/main`

| key | value | evidence |
|---|---|---|
| SHA / tree | `b7c9e2e3e925ba8220d459de037202f0f03b03f2` / `53fa9d041b462f06249428d6a379ce5828577b45` | `git ls-remote origin refs/heads/main`; `git rev-parse origin/main^{tree}` |
| last merge | #140, `mergedAt` 2026-09-30T02:46:38Z | `gh pr view 140` |
| first-parent shape | root `a33177c7` plus **142** "Merge pull request #N" commits (no squash, no rebase, no direct commits) | `git log --first-parent origin/main` |
| content vs chain | the tree equals the P31.4 closeout `13782968` tree **plus one file**, `web/package-lock.json` (blob `da838491`, from `d4522d82`) | `git diff --stat 13782968 b7c9e2e3` shows 1 file, +51/−19 |
| branch protection | none. `protected:false`, `required_status_checks` off, the ruleset "main" is `enforcement: disabled`. The repo allows merge commits, and `delete_branch_on_merge=false` | `gh api repos/…/branches/main`, `…/rulesets`, `repos/…` |
| tags / releases | **none** (`git ls-remote --tags origin` is empty; `gh release list` is empty) | live-read |

### 1.2 What is merged, and how

**Merged: 142 PRs.** These are #1–#140, #148 (`devin/deploy-gcp-live`, 2026-09-26T03:07:03Z, landed between #86 and
#87) and #191 (`devin/p27-launch-planning`, 2026-09-29T03:15:50Z, landed before #112). `gh pr list --state merged` shows
no gaps in #1–#140.

**How.** The operator retargets each PR's base to `main` and then uses GitHub "Create a merge commit". Every merged PR
shows `baseRefName=main`. Branches are kept. The work happens in sittings with merges about 12 s apart. The last two
sittings were:

| sitting (UTC) | PRs | main-CI push runs |
|---|---|---|
| 2026-09-29T03:15:49–03:28:49Z | #191, #112–#130 | 20 runs, 19 **cancelled**, 1 success (`eac36390`, run 36517314483) |
| 2026-09-30T02:44:56–02:46:38Z | #131–#140 | 10 runs, 9 **cancelled**, 1 success (`b7c9e2e3`, run 36661393143) |

`ci.yml` sets `concurrency: ci-${{ github.ref }}` with `cancel-in-progress: true`. So when merges land back-to-back,
only the last push of a sitting is ever CI-verified (see NEW-4).

**Operator commits made on PR branches before merging.** They are all on `main` now and none is on the #141–#190 chain.
All are agent-assisted per their `Co-Authored-By` trailers.

*a) Lockfile regenerations on #131–#140 (2026-09-30T02:30–02:35Z; commit dates are −04:00 on 09-29).* All ten are
byte-identical. Each changes only `web/package-lock.json`, from blob `7fba196a` to blob **`da838491`**, with
`web/package.json` unchanged at `da0885dc`.

| PR | branch | regen commit | CI on the regen commit |
|---|---|---|---|
| #131 | `devin/p30-1-osm-land-and-settled-reaudit` | `cadd5acf` (then main-merge `332865ff`) | 5/5 success (02:30–02:34Z) |
| #132 | `devin/p30-2-hosted-round6-materialization` | `7db83f19` | — |
| #133 | `devin/p30-2a-camera-predicate-registry` | `f89b83b8` | — |
| #134 | `devin/p30-2b-geospatial-camera-site-resolution` | `2656a2ae` | — |
| #135 | `devin/p30-3-national-export-and-public-cutover` | `b2d2f474` | — |
| #136 | `devin/p30-4-post-launch-closeout` | `3804f11f` | 5/5 success (02:33–02:36Z) |
| #137 | `devin/p31-1-api-db-resilience-and-bounded-search` | `dcf6070f` | — |
| #138 | `devin/p31-2-ingest-run-completion-and-freshness` | `e877c11b` | — |
| #139 | `devin/p31-3-sink-identity-guard-and-batched-writes` | `202cafff` | — |
| #140 | `devin/p31-4-incremental-restart-and-osm-replay-readiness` | **`d4522d82`** (A1 NEW-1) | 5/5 success (02:35–02:39Z) |

"—" means not read individually. Sampling covers the first, the middle and the last. Evidence: `gh api
commits/<sha>/check-runs`. The pre-regen heads were red on `web` and `composed` (for example `df7b1278` #136, `ffccd244`
#139 and `13782968` #140, all failing since 2026-09-24/25).

*b) Main-into-branch merges (conflict resolutions).*

- `332865ff` (#131, 09-30T02:44:27Z) resolved a `web/package-lock.json` conflict. It kept the branch's regenerated
  lockfile `da838491` rather than main's `43024607`, the npm-10 regen that #120–#130 carried from 09-23. The commit
  message records that the two differ only in the optional nested `@types/node` peer, 26.6.2 against 26.6.3.
- `f8567912` (#113) and `4c185056` (#117), both 09-29T03:16–03:21Z, resolved `docs/tickets/DEFERRALS.md` by taking the
  branch side. Each merge tree equals its branch parent (`git diff --stat <c>^1 <c>` is empty). These are exactly the
  two DEFERRALS conflicts P33.6 predicted.
- Older ones: `bfffef03` (#109), `a1eb3949` (#105), `213ee0a7` (#103), `04edaacc` (#97), `a5a09396` (#82),
  `a888a0a4`, `d003a673`, `15bdcf5d`.

None of these operator merges or regenerations is recorded in build memory (F-17).

### 1.3 The open stack #141–#190

There are **49 open PRs**: #141–#190 minus #148. All are MERGEABLE and none is a draft. The stack is strictly linear:
every head is an ancestor of the next one, checked with `git merge-base --is-ancestor` for all 48 consecutive pairs.
That means there are **no out-of-chain tip commits**, unlike P33.6 §(c)'s twelve. Every head has merge-base `13782968`
with `main`. #141's base is `devin/round9-waveb-seed` (`34406ffc`), which is the P31.4 closeout plus two seed commits,
`91521187` and `34406ffc`. Merging #141 carries those two in.

CI below is reused from the baseline (C05), plus the Actions logs read here. Every PR runs 5 checks: python, docs,
composed, security, web.

| PRs | head lockfile | CI on own head | cause |
|---|---|---|---|
| #141–#147, #149–#154 (13) | `7fba196a` (stale) | red: `composed` + `web` (completed 09-25…09-27) | `npm ci`: "Missing: @emnapi/runtime@1.11.3 / @emnapi/core@1.11.3 / @types/node@26.6.2 from lock file" (run 36092963615, #141) |
| #155 (`codex/round10-seed-after-p31-19`, `c8d72cc3`) | **`da838491`** (`d6c562e5`, 2026-09-26, "repair CI lockfile") | 5/5 green | — |
| #156–#164, #166–#178, #180–#184, #186–#190 (30) | `da838491` | 5/5 green | — |
| #165 `42bb286a` | `da838491` | red: `python` (attempt 1, 09-27T10:31Z) | §2b |
| #179 `a33cd6ec` | `da838491` | red: `python` (attempt 2 re-run, 09-30T03:07Z) | §2b |
| #185 `4127dbf3` | `da838491` | red: `python` (attempt 2 re-run, 09-30T03:07Z) | §2b |

Totals: 33 PRs all green, 16 failing (`gh.ci_all_pass_count`, `gh.ci_failing_count`). #190 is `MERGEABLE/CLEAN` with 5/5
green.

### 1.4 How the chain tip relates to `main` (A1 NEW-1, refined)

`b051732c` does **not** descend from `b7c9e2e3` (`merge-base --is-ancestor` is false). The gap is in **ancestry only,
not content.** The only file on which `main` differs from the fork point is `web/package-lock.json`. There, `main` holds
`da838491`, and #155–#190 hold the **same blob `da838491`**, committed independently three days earlier (`d6c562e5`).
`git diff b7c9e2e3 b051732c` is therefore pure chain additions: 2,238 files, +235,936/−3,499, and no lockfile hunk.

---

## 2. Merge-readiness notes (for the operator's later bottom-up merge from `main`@#140 through #190)

### 2a. The #141–#154 `npm ci` lockfile failure

**Diagnosis** (live-read and recorded-execution):

1. **Inputs are identical.** `web/package.json` is blob `da0885dc` on `main`, on every #141–#190 head and on every
   #131–#140 regen commit. The only variable is the lockfile: `7fba196a` on #141–#154, `da838491` on `main` and on
   #155–#190.
2. **`7fba196a` has been red on CI since it was created.** It was introduced by P27.9 `3d3eeb75`, whose CI failed at
   2026-09-23T03:58Z, and every later head carrying it fails the same way. The diff to `da838491` covers these entries:
   - It adds `@emnapi/core` and `@emnapi/runtime` 1.11.3 and nested `@types/node` 26.6.3 entries under
     `@astrojs/react` and `astro`.
   - It moves `peer: true` flags.
3. **Root cause (inference).** The lockfile is written by a local npm that differs from CI's pinned-major environment,
   which is `setup-node "22"` giving node 22.23.2 and npm 10.9.8 in the #141 log. Independent regenerations also resolve
   optional peers such as `@types/node` 26.6.2 against 26.6.3 differently. Nothing pins the toolchain: no
   `packageManager`, no `.nvmrc`, and `engines` is `node >=22.12.0` only. The CI log also shows `EBADENGINE`:
   `license-checker-rseidelsohn@5.0.1` requires node ≥24 and npm ≥11. This has now needed repair 5 times, see NEW-2.

**Does the operator's #131–#140 regeneration fix it on #141–#154?** Yes. The inputs are the same (pre-blob `7fba196a`,
same `package.json`), so cherry-picking `d4522d82` onto any #141–#154 head yields `da838491`. With that exact blob,
`cadd5acf`, `3804f11f` and `d4522d82` went 5/5 green, and so did #155–#190.

**Caution: cherry-pick, never re-run `npm install`.** A fresh regeneration may produce a *different* blob, as the
26.6.2/26.6.3 split showed. A different blob would then conflict with `main` at that PR and again at #155. That is
exactly the conflict P33.6 predicted when `main` held `43024607`.

**Would merging `main` into each branch fix it, as the operator did for #131?** Yes, and without conflict.
`merge-tree origin/main <head>` is clean for all 49 heads (Pass A). Because the merge-base is `13782968` (`7fba196a`),
each branch simply gains `da838491`. It has to be done on **each** of the 14 branches, though. PR CI tests
`refs/pull/N/merge`, which is the head merged into *its current base*, so each branch needs its own push to retrigger
(`pull_request` default types: a base retarget does not trigger a run; inference from `on: pull_request` with no
`types:`).

**Is any per-branch fix needed for the merge into `main`?** **No** (recorded-execution, §2c). Merging #141–#154 into
`main` keeps `main`'s `da838491` at every step, because the main side changed the file and the PR side did not. So the
merged `main` never carries the stale lockfile. The red badges on #141–#154 are an artifact of those PRs' *old bases*.
They are not a prediction of `main`'s state. They will stay red after retargeting unless re-triggered.

**Recommendation.**

- **Option A (preferred, minimal).** Merge #141–#154 as they are. Optionally pause once after #154 so one `main` CI run
  completes on the "Round 9 complete" state.
- **Option B**, the operator's earlier practice, is sound if every PR should show green before its merge. Per branch,
  `git cherry-pick d4522d82` (or merge `origin/main`), push, and wait for CI.
  - It costs 14 pushes to chain branches, which is operator-only work.
  - It moves the A1 heads digest.
  - Its one real benefit is CI evidence for the #151/#152 intermediate web states, which have never been exercised
    (NEW-3).
  - If B is chosen, use the byte-identical cherry-pick, not a fresh regeneration.

### 2b. The three memory-coupled reds (#165, #179, #185)

Each fails exactly one test in the `python` job (`make test` with `SIG_REQUIRE_DB_TESTS=1`). Each failure is caused by a
**build-memory record** commit, not by code, and the next PR's head is green. (Recorded-execution: Actions logs.)

| PR | failing test (log) | what it asserts / what it found | causing commit on the head | how the successor turned green |
|---|---|---|---|---|
| #165 `42bb286a` | `tests/unit/test_build_memory_audit.py::test_real_tree_expected_conflicts_and_zero_errors` (run 36312594389, 1 failed / 4838 passed) | the real tree has zero audit errors. Found `manifest/malformed-row` (`00_MANIFEST.md`) and `ledger/next-ticket P32.10a` | `42bb286a` "insert P32.10a (row 170.5)", a **post-close insert** after closeout `13ade2b2`. The sequence cell `170.5` is not parseable by `audit_current_state.py` | #166 closeout `e8f8764d` rewrote the cell to `170a` (records fixed; no test change) |
| #179 `a33cd6ec` | same test (run 36366041520 attempt 2, 1 failed / 5407 passed) | found `ledger/done-uncovered P32.22` (`audit_current_state.py:572-612`: a PHASE LOG "done" entry whose BUILD_INDEX row names no parseable, existing evidence file) | **the P32.22 closeout itself, `a97aaca2`**. BUILD_INDEX row 183's evidence cell contains `` `db/{deploy\|revert\|verify}/recovery_apply.sql` `` with *unescaped* pipes, which split the Markdown row. The later pause (`c4aafa20`) and S3-deferral (`a33cd6ec`) commits did not touch BUILD_INDEX | #180 closeout `22b773f8` rewrote the cell as `db/{deploy,revert,verify}/…` (records fixed) |
| #185 `4127dbf3` | `tests/unit/test_capstone_closure_round10.py::test_gate_accept_readout_stays_pending_and_section_is_honest` (run 36467709050 attempt 2, 1 failed / 5510 passed) | `assert "PENDING" in readout`. The readout now says "SIGNED" | `4127dbf3` "GATE-ACCEPT signed", a **post-close signature** that the pinned test forbade | #186 `a711333d` **rewrote the test** (`…_state_matches_the_recorded_decision`: PENDING *or* SIGNED with provenance markers and a LEDGER entry) |

This refines F-19. Only two of the three reds come from post-close commits. #179's comes from a malformed closeout
record. #186 relaxed a test so that it accepts a changed living record. That is the pattern B4 is asked to guard against.

**Does bottom-up merging make `main` transiently red?** Yes, at exactly three states, for **one merge step each**:

- After #165, `main`'s tree equals the #165 head tree (§2c), so it is red. After #166 it is green again.
- The same holds for #179 then #180, and for #185 then #186.

A pause at any of those three would leave `main` red until the next merge. In a one-sitting run the concurrency group
cancels those intermediate push runs (§1.2), so no completed red run appears. The three merge commits stay red forever
in history, though: a later `git bisect` should `skip` them.

There is a second, uncounted exposure (NEW-3). The `web`/`composed` gates never ran on any #141–#154 state. `web/` at
#153 and #154 equals #155's apart from the lockfile, and #155 is green. So only the states after **#151 and #152** are
unverified for web. That is an inference that they are probably fine, since #153/#155 are green, but they are unproven.

Separately, CI results on these heads date from 09-25 to 09-30. Some tests read living records and dates, so a result
could differ when re-run after real time passes the future-dated records (F-21). That is an inference and cannot be
tested here, which is one more reason to verify the *final* `main` state rather than trust stale per-PR badges.

**Options (operator's choice).**

| option | what | cost / risk | simulated result |
|---|---|---|---|
| (i) accept transient red | merge straight through, pausing only if needed | `main` is red only if you stop at #165/#179/#185 | final tree == #190, green on its PR CI |
| (ii) fix-forward tiny commits on #165/#179/#185 | push a one-hunk fix identical to the successor's change | 3 pushes to chain branches, and 3 new out-of-chain tip commits (the P33.6 §(c) pattern). #179 **conflicts** | #165 fix (manifest `170.5`→`170a`) merged with #166: clean. #185 fix (#186's test file) merged with #186: clean. #179 fix (row 183 from #180) merged with #180: **CONFLICT in `docs/build/BUILD_INDEX.md`**, because #180 also appends row 188 next to it. Resolve by taking theirs |
| **(iii) merge through to #190 in one sitting, then verify** (recommended) | pause only at green checkpoints (after **#154, #164, #178, #184**) if a break is needed; never stop at #165/#179/#185 | none beyond (i); the final verification (§2d/§4) is mandatory | 0 conflicts; final tree == #190 head tree |

### 2c. Expected conflicts: simulation over the actual sequence

**Method** (recorded-execution, 2026-09-30T16:45Z). Start from `origin/main` `b7c9e2e3`. For each open PR in ascending
order:

1. Run `git merge-tree --write-tree <accumulated> <head>`.
2. On a conflict, take the incoming PR's file (P33.6's rule).
3. Run `git commit-tree -p <accumulated> -p <head>` to mimic GitHub's merge commit.
4. Compare the step tree with the PR head tree.

**Result:** **zero conflicts in all 49 steps.** Pass A (each head merged into `main` independently) is also clean for all
49.

| steps | step tree vs that PR's head tree |
|---|---|
| #141 … #154 | equal **except `web/package-lock.json`** (`main` keeps `da838491`) |
| #155 … #190 | **byte-equal** (e.g. #155 `5a4d2611`; #187 `51dcab80`, matching P33.6's recorded #187 head tree; #190 `64a23cd7`) |

**Final accumulated tree `64a23cd7c0330fa23c93d659c96e7da94df59934` == `b051732c^{tree}`.**

Compared with P33.6 §(c):

- **#113 and #117 (DEFERRALS):** already merged. The operator resolved both by taking the branch side (`f8567912`,
  `4c185056`), which is exactly P33.6's prescription.
- **#155 (`web/package-lock.json`):** **no longer conflicts.** P33.6 predicted it when `main` held `43024607` (the
  `@types/node` 26.6.2 variant). `main` now holds `da838491`, byte-identical to #155's `d6c562e5`, so both sides make
  the same change.
- **P33.6's twelve out-of-chain tip commits (#112–#130):** all merged. The #141–#190 chain has none.
- **`db/sqitch.plan`:** the chain appends 13 lines and removes 0 relative to `main`, so ascending order preserves deploy
  order (P33.6 §(b) still applies: never reorder).
- **Caveat:** the simulation is a snapshot at heads digest `8331f062…`. It becomes stale in several cases:
  - any head moves;
  - option (ii) or option B is applied;
  - Round-11 PRs are included;
  - a fresh lockfile regeneration is made.

  In any of those cases, re-run `docs/build/tools/merge_dryrun.sh` (P33.6 §(e) step 0). Given the above it should now
  exit 0 (inference).

### 2d. Tree-equality verification and the tag

- **Invariant.** After #190 merges, `git rev-parse origin/main^{tree}` must equal `git rev-parse
  devin/p33-8-agent-docs-refresh^{tree}` = **`64a23cd7…`**. No "modulo the operator's lockfile commits" allowance is
  needed. `d4522d82` and its nine siblings contribute zero net content at the end, because #155–#190 carry the identical
  blob.
  - If option B was used on #141–#154, the invariant still holds, since those commits also carry `da838491`.
  - If option (ii) was used, it still holds when conflicts are resolved by taking theirs.
  - A mismatch means a resolution went wrong. Use the P33.6 §(f) rollback: `git revert -m 1`, never reset or
    force-push.
- Also check that `merge-base --is-ancestor devin/p33-8-agent-docs-refresh origin/main` succeeds and that the **last**
  `main` push run of the sitting is `success`. Cancelled intermediate runs are expected.
- **Tag.** No tag or release exists. REL.1/HG-05 (`readouts/GATE-G1.md`) is still SKIPPED-BY-OPERATOR. `CHANGELOG.md`
  `[0.1.0]` is "unreleased" and `web`/`api` are at version `0.1.0`. P33.6 deliberately had no tag step.
  - H1 does **not** recommend a tag name. That is the operator's call, and G3 designs the versioning and release model.
  - If the operator wants a marker before G3, the least committal choice is an annotated tag on the post-#190 merge
    commit, cut only after that commit's `main` CI is green. Name it as an integration point (not a version) so that it
    does not pre-empt HG-05's `v0.1.0`.

---

## 3. Round 11 stacked on #190: how it extends the order, and what that implies

1. **Order.** The sequence is #141 → … → #190 (`devin/p33-8-agent-docs-refresh`) → **#192** → #193 → …. #191 is taken
   (merged). The first Round-11 PR is based on `devin/p33-8-agent-docs-refresh`. That PR is either the Stage-B seed from
   `claude/next-phase-planning`, which exists only locally for now (A1), or the first ticket.
   - The operator's merge of Round-11 PRs is the same bottom-up procedure: retarget to `main` immediately before each
     merge.
   - Round-11 branches must **never** be rebased or retargeted onto `main` by an agent. Doing so would break the tree
     invariant and the stack.
2. **No lockfile fix is needed on the new stack.** #190 already carries `da838491`, the same content as `d4522d82`, and
   is 5/5 green. Round-11 PR CI tests `head ⊕ its base` (a chain branch), so `npm ci` passes. Round-11 branches lack
   `d4522d82` as an *ancestor* only, and the simulation shows that is harmless.
   - Round 11's first engineering ticket should instead **prevent recurrence**: pin the npm/node toolchain (NEW-2) and
     make any lockfile repair a byte-identical cherry-pick. This is routed to H2/B4.
   - The #141–#154, #165, #179 and #185 reds do not carry into Round-11 CI.
3. **Keep the tree invariant exact while Round 11 runs.** If the operator commits to `main` or to a pre-#190 branch
   again (as `d4522d82` did), ancestry diverges once more. H2 should adopt two rules:
   - Any such fix is mirrored into the Round-11 stack tip, or made as a Round-11 PR.
   - The orchestrator records `git merge-base --is-ancestor origin/main <chainTip>`, plus the diff of the paths `main`
     changed, at each ticket boundary, as A1 did.
4. **The merge loop must be bounded.** P33.6 §(e)'s loop merges every open PR in ascending order. Once #192+ exist it
   would sweep Round-11 PRs, including an unratified Stage-B seed, into `main` (NEW-5). Use `TOP=190` (§4) or an
   explicit list.
5. **Date corrections (B1) against merging #143+.** A simple scan of added lines finds the first post-commit event
   dates at **#143** (P31.7 `a14869fd`, committed 2026-09-25). They are a `db/sqitch.plan` line
   `resolution_supersede … 2026-10-02T12:00:00Z` and an ADR `Date: 2026-10-02`. Earlier PRs add only the legitimate
   2026-10-10 replay cron date and a 2026-12-31 contract end date. B1 owns the authoritative inventory. H1's view:
   - **Correction cannot land before #143 merges without rewriting chain history.** A correction PR must stack on #190,
     because the chain's own later commits rewrite the same append-only files. Rebasing or retargeting chain branches
     is forbidden (P3/P10).
   - Corrections are append-only (P7), so the wrong dates stay in history either way. Holding #143+ back only delays
     when `main` shows them.
   - Merging does not touch hosted Cloud SQL. Deployed `sqitch.plan` lines are never edited; B1 confirms which ones are
     deployed.
   - **Recommendation:** do **not** gate the operator's merge on B1. Land B1's correction records (the ADR plus
     append-only entries) as an early Round-11 PR, or in the Stage-B seed. If the operator wants `main` never to show
     uncorrected dates without the correction next to them, merge #143 through #190 **and** that correction PR in the
     same sitting. Merging #141–#142 earlier is optional.
6. **Not fixed by integration.** The failing scheduled `reingest` workflow (A1 NEW-2) stays broken. The chain changes
   only `.github/workflows/ci.yml` and never touches `reingest.yml`. This is routed to G1.

---

## 4. Operator checklist: for when you resume (not executed by this row)

```bash
# ── 0. Preflight (read-only) ───────────────────────────────────────────────────
date -u
git fetch origin
git rev-parse origin/main                          # expect b7c9e2e3…  (else: re-run the dry-run and re-read §2c)
gh pr list --state open --limit 200 --json number,headRefOid \
  --jq '[.[]|select(.number<=190)]|sort_by(.number)[]|"\(.number) \(.headRefOid)"' | shasum -a 256
                                                   # expect 8331f062…d088  (else a head moved: re-run the dry-run)
sh docs/build/tools/merge_dryrun.sh                # expect exit 0 (0 conflicts; bottom-up tree == top PR)
                                                   # (it includes any open Round-11 PRs; read the table only to #190)

# ── 1. Lockfile (§2a) — default: do nothing. Only if you want #141–#154 green first (option B), per branch:
#   git checkout <branch> && git cherry-pick d4522d82 && git push   # byte-identical blob; NEVER a fresh npm install

# ── 2. Merge bottom-up, bounded (§3.4). Green checkpoints if you must pause: 154, 164, 178, 184. Never stop at 165/179/185.
TOP=190
for n in $(gh pr list --state open --limit 200 --json number --jq "[.[].number|select(. <= $TOP)]|sort[]"); do
  gh pr edit "$n" --base main
  gh pr merge "$n" --merge --delete-branch=false || { echo "STOP at #$n — see §2c; do not improvise"; break; }
done

# ── 3. Verify (§2d) ────────────────────────────────────────────────────────────
git fetch origin
test "$(git rev-parse 'origin/main^{tree}')" = "$(git rev-parse 'origin/devin/p33-8-agent-docs-refresh^{tree}')" \
  && echo TREE-EQUAL                               # expect 64a23cd7c0330fa23c93d659c96e7da94df59934
git merge-base --is-ancestor origin/devin/p33-8-agent-docs-refresh origin/main && echo ANCESTOR
gh pr list --state open --json number --jq '[.[].number|select(.<=190)]'   # expect []
gh run list --branch main --workflow CI --limit 3  # newest push run must be success (earlier ones cancelled = expected)
# then P33.6 §(h): make check · make test-db · SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra ·
#                  npm --prefix web run check · check_spec_src.py · check_coverage_matrix.py · check_backlog.py

# ── 4. Optional tag (§2d) — your decision; HG-05 stays deferred; G3 owns naming.
# ── 5. Record: tell the planning orchestrator main's new SHA/tree + `date -u` (A1 delta will flag git.*/gh.*).
# Rollback if anything is wrong: git revert -m 1 <merge> (newest first); never reset/force-push (P33.6 §(f)).
```

---

## 5. New findings (→ `findings/incoming/H1.csv`)

| id | title | sev | routed |
|---|---|---|---|
| NEW-1 | F-18 amended: the #141–#154 `npm ci` red is a PR-base artifact; merging them onto `main` keeps the in-sync lockfile, gives 0 conflicts, and needs no per-branch fix | S3 | H1 |
| NEW-2 | Web lockfile drift recurs because the npm toolchain is unpinned (5 repair episodes, 25 repair commits, 09-13…09-29; CI npm 10.9.8 against a devDependency that needs npm ≥11) | S2 | H2, B4 |
| NEW-3 | `web`/`composed` gates never executed on any #141–#154 state; the #151/#152 intermediate web states have no CI evidence | S2 | H1, B4 |
| NEW-4 | `main` CI `cancel-in-progress` plus rapid merging leaves intermediate `main` states unverified (28 of 30 push runs cancelled in the last two sittings) | S2 | H2 |
| NEW-5 | P33.6's merge loop is unbounded and would sweep Round-11/Stage-B PRs into `main` | S2 | H1, H2 |
| NEW-6 | F-19 refined: #179's red comes from a malformed BUILD_INDEX closeout row (unescaped `\|`), not a post-close commit, and #186 relaxed a pinned test to accept a signed readout | S2 | B4 |
