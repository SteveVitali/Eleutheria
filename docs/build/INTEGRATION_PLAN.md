<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# INTEGRATION_PLAN — how the operator merges the stack and cuts `v0.1.0` (P20.3, Phase E)

**This ticket (P20.3) merges nothing, tags nothing, and does not touch `main` or any branch.** It
produces the *procedure* and *proof* the operator uses to integrate the stack **after the chain**
(gate HG-05 — a post-chain operator action, `OPERATIONAL_READINESS.md §(d)`). Everything below is a
runbook; the only commands this ticket actually ran are the read-only `merge_dryrun.sh` and
`make check` (see §(b)). Requirement ids: SIG-ENG-011/015/016/031, SIG-LIC-005, SIG-GOV-021.

---

## (a) The PR graph at ticket time

The build is a single linear stack: every PR's base is the previous ticket's head branch, so the
whole chain fast-forwards cleanly. Three segments exist when P20.3 is written:

**Already merged into `origin/main` by the operator (bottom of the stack, before this ticket ran).**
`origin/main` = `5435e5d` ("Merge pull request #26"). Their trees are already in `main`; the ten
merge commits add no tree change over the chain fork point `2faf380` (P07.3 tip).

| PR | ticket | head branch |
|---|---|---|
| #20 | P08.1 | devin/p08-1-resolver |
| #21 | P08.2 | devin/p08-2-reconciliation-workflows |
| #22 | P08.3 | devin/p08-3-contradiction-object |
| #23 | P09.1 | devin/p09-1-coverage |
| #24 | P10.1 | devin/p10-1-task-engine |
| #25 | P10.2 | devin/p10-2-detector-catalog |
| #26 | P10.3 | devin/p10-3-records-request-gen |

> **Note on the ticket's `#20…#53` wording.** P20.3 was written assuming #20–#53 were all *open*.
> By the time it ran, the operator had already merged #20–#26 (progressive integration is explicitly
> allowed — see §(c)). `merge_dryrun.sh` and this plan therefore operate over the **currently open**
> PRs (#27–#53) plus this ticket's PR (#54); the merged-count of PRs ≥ 20 is a **pre-existing 7** and
> P20.3 leaves it unchanged (it merges nothing). The script is generic (`gh pr list --state open`),
> so the operator re-runs it verbatim when #55–#63 also exist.

**Open at ticket time (#27–#53), base = previous head, with head SHAs:**

| PR | ticket | head branch | base branch | head SHA |
|---|---|---|---|---|
| #27 | P11.1 | devin/p11-1-flock-portal | main | dcf02f1c8f94 |
| #28 | P11.2 | devin/p11-2-audit-structural | devin/p11-1-flock-portal | 249f567bd5fa |
| #29 | P12.1 | devin/p12-1-usage-analytics | devin/p11-2-audit-structural | f62d200427e6 |
| #30 | P12.2 | devin/p12-2-network-inference | devin/p12-1-usage-analytics | ce9cde1f87b5 |
| #31 | P13.1 | devin/p13-1-accountability | devin/p12-2-network-inference | 388e851b8323 |
| #32 | P13.2 | devin/p13-2-policy-legal | devin/p13-1-accountability | ea8fdc6c4863 |
| #33 | P14.1 | devin/p14-1-public-api | devin/p13-2-policy-legal | 4493b1497585 |
| #34 | P14.2 | devin/p14-2-exports | devin/p14-1-public-api | cb2df2d9ff63 |
| #35 | P15.1 | devin/p15-1-web-shell | devin/p14-2-exports | fdddec04ed60 |
| #36 | P15.2 | devin/p15-2-local-dossier | devin/p15-1-web-shell | 99d246c7b112 |
| #37 | P15.3 | devin/p15-3-map-network | devin/p15-2-local-dossier | 43d5b1669a0e |
| #38 | P15.4 | devin/p15-4-watch-evidence | devin/p15-3-map-network | b8f5da8a0755 |
| #39 | P15.5 | devin/p15-5-corrections-methodology | devin/p15-4-watch-evidence | 2b361f18e4b1 |
| #40 | P16.1 | devin/p16-1-contributors | devin/p15-5-corrections-methodology | 02fb3fbab303 |
| #41 | P16.2 | devin/p16-2-contribution-back | devin/p16-1-contributors | e914ede0d284 |
| #42 | P17.1 | devin/p17-1-broader-federation-rtcc | devin/p16-2-contribution-back | c79fdbdb5681 |
| #43 | P17.2 | devin/p17-2-broader-fr-css-forensics | devin/p17-1-broader-federation-rtcc | bca8ad1fca42 |
| #44 | P17.3 | devin/p17-3-broader-acoustic-drone-loc | devin/p17-2-broader-fr-css-forensics | 29b3a28b425f |
| #45 | P18.1 | devin/p18-1-international-framework | devin/p17-3-broader-acoustic-drone-loc | b6fa41477051 |
| #46 | P18.2 | devin/p18-2-france-belgium | devin/p18-1-international-framework | 1baf05f66301 |
| #47 | P19.1 | devin/p19-1-build-memory-and-hygiene | devin/p18-2-france-belgium | 33aaf02e3f6f |
| #48 | P19.2 | devin/p19-2-capstone-gap-analysis | devin/p19-1-build-memory-and-hygiene | 4ffae4fbbf21 |
| #49 | P19.3 | devin/p19-3-capstone-composed-verification | devin/p19-2-capstone-gap-analysis | a5f18adb0af8 |
| #50 | P19.4 | devin/p19-4-capstone-spine-wiring | devin/p19-3-capstone-composed-verification | 4682f9d21278 |
| #51 | P19.5 | devin/p19-5-capstone-gap-closure | devin/p19-4-capstone-spine-wiring | 89d275287fc0 |
| #52 | P20.1 | devin/p20-1-backlog-and-operational-readiness | devin/p19-5-capstone-gap-closure | 7ef6be6c5255 |
| #53 | P20.2 | devin/p20-2-spec-reconciliation | devin/p20-1-backlog-and-operational-readiness | b43a524132c3 |

**This ticket:** **#54** P20.3 `devin/p20-3-integration-release`, base `devin/p20-2-spec-reconciliation`.

**Appended by later tickets:** **#55–#63** (P21.1 … P21.9) will stack on `devin/p20-3-integration-release`
in the same way; re-run `merge_dryrun.sh` once they exist. The tag may be cut at any ticket boundary
(the stack stays valid either way) — the recommendation is after P21.9, but progressive integration
is explicitly supported (`00_MANIFEST.md`).

---

## (b) Merge dry-run result (produced now by `sh docs/build/tools/merge_dryrun.sh`; exit 0)

Read-only over every ref: a throwaway `git worktree add --detach /tmp/sig-merge origin/main`,
`git merge --no-commit --no-ff` per PR (Pass A), then a bottom-up accumulation on the detached HEAD
(Pass B) asserting the final tree equals the top PR's tree, then `git worktree remove --force`.
**Result: all 27 open PRs merge clean (0 conflicts); bottom-up tree matches PR #53.** `main` and
`origin/main` were unchanged before/after; `git worktree list` returned to the single main tree; no
tag or branch was created.

```
PR      head                                         base                                 rc  conflicts
------  -------------------------------------------  -----------------------------------  --  ---------
#27     devin/p11-1-flock-portal                     main                                 0   [none]
#28     devin/p11-2-audit-structural                 devin/p11-1-flock-portal             0   [none]
#29     devin/p12-1-usage-analytics                  devin/p11-2-audit-structural         0   [none]
#30     devin/p12-2-network-inference                devin/p12-1-usage-analytics          0   [none]
#31     devin/p13-1-accountability                   devin/p12-2-network-inference        0   [none]
#32     devin/p13-2-policy-legal                     devin/p13-1-accountability           0   [none]
#33     devin/p14-1-public-api                       devin/p13-2-policy-legal             0   [none]
#34     devin/p14-2-exports                          devin/p14-1-public-api               0   [none]
#35     devin/p15-1-web-shell                        devin/p14-2-exports                  0   [none]
#36     devin/p15-2-local-dossier                    devin/p15-1-web-shell                0   [none]
#37     devin/p15-3-map-network                      devin/p15-2-local-dossier            0   [none]
#38     devin/p15-4-watch-evidence                   devin/p15-3-map-network              0   [none]
#39     devin/p15-5-corrections-methodology          devin/p15-4-watch-evidence           0   [none]
#40     devin/p16-1-contributors                     devin/p15-5-corrections-methodology  0   [none]
#41     devin/p16-2-contribution-back                devin/p16-1-contributors             0   [none]
#42     devin/p17-1-broader-federation-rtcc          devin/p16-2-contribution-back        0   [none]
#43     devin/p17-2-broader-fr-css-forensics         devin/p17-1-broader-federation-rtcc  0   [none]
#44     devin/p17-3-broader-acoustic-drone-loc       devin/p17-2-broader-fr-css-forensics  0   [none]
#45     devin/p18-1-international-framework          devin/p17-3-broader-acoustic-drone-loc  0   [none]
#46     devin/p18-2-france-belgium                   devin/p18-1-international-framework  0   [none]
#47     devin/p19-1-build-memory-and-hygiene         devin/p18-2-france-belgium           0   [none]
#48     devin/p19-2-capstone-gap-analysis            devin/p19-1-build-memory-and-hygiene  0   [none]
#49     devin/p19-3-capstone-composed-verification   devin/p19-2-capstone-gap-analysis    0   [none]
#50     devin/p19-4-capstone-spine-wiring            devin/p19-3-capstone-composed-verification  0   [none]
#51     devin/p19-5-capstone-gap-closure             devin/p19-4-capstone-spine-wiring    0   [none]
#52     devin/p20-1-backlog-and-operational-readiness  devin/p19-5-capstone-gap-closure     0   [none]
#53     devin/p20-2-spec-reconciliation              devin/p20-1-backlog-and-operational-readiness  0   [none]

bottom-up accumulation: clean (27/27)
final tree == top PR:   yes (== PR #53 tree 42448f199658f76590a7942d04849af7ce58646f)
RESULT: all 27 open PRs merge clean; bottom-up tree matches the top PR. (exit 0)
```

**Interpretation.** Integration is mechanically trivial. There are no conflicts because nothing
touched `main` after the chain forked; the `ontology/generated` / `pylock.toml` "conflict magnets"
never materialised. Merging the single top PR would bring the identical tree; merging bottom-up
gives one merge commit per ticket and per-PR review granularity — the recommended default in §(c).

---

## (c) The three strategies and their consequences

| Strategy | What it produces | Bisectability | History | Recommended? |
|---|---|---|---|---|
| **A. Merge-commit bottom-up** | one `--no-ff` merge commit per PR, in number order, onto `main` | good — each ticket is a first-parent step; `git bisect --first-parent` walks tickets | preserves the 1-commit-per-ticket history and every PR reference | **YES — default** |
| **B. Squash per PR** | one squashed commit per PR | good at ticket granularity, but intra-ticket commits are lost | also conflict-free (identical hunks both sides) but **destroys** the per-commit history within a ticket | no (loses provenance) |
| **C. Single merge of the top PR** | one merge bringing the whole tree | poor — the entire build is one step | smallest graph, but no per-ticket boundary on `main` | no (loses reviewable boundaries) |

Notes that apply to all three:

- **GitHub auto-retarget.** When a base branch is deleted on merge, GitHub automatically retargets any
  open child PR onto the merged PR's base. The default procedure below merges bottom-up **without**
  deleting branches (`--delete-branch=false`, append-only P1–P3), and re-points each next PR's base to
  `main` explicitly if GitHub has not already — so retarget behaviour never surprises the operator.
- **Bisectability.** Strategy A keeps `git bisect --first-parent` meaningful: each first-parent hop is
  exactly one ticket. B is coarser; C collapses the build to a single commit.
- **`4493b14` provenance.** The P12.1 analytics-boundary hardening (reason_raw / rights_record /
  forbidden org-id columns / COMPLEMENTARY rationale; SIG-STORE-028/030/031, §11.16/§18.4) landed on
  **P14.1's branch**, so it is the head SHA of **PR #33** above (LD-D14). It merges naturally in every
  strategy; its ADR-044 note was added in P19.5. No history rewrite is needed to "relocate" it.
- **Append-only.** No strategy rebases or force-pushes; branches are kept (`--delete-branch=false`).

---

## (d) The operator's procedure — copy-pasteable (Strategy A, the default)

> Run from a clean checkout of the repo with `gh` authenticated and Docker running (for `make test-db`
> and `tests/e2e`). Nothing below is run by P20.3; it is the post-chain operator runbook (HG-05).

```bash
# 0. Re-run the dry-run FIRST — it is stale the moment new PRs (e.g. #55–#63) appear (RISK-P20-05).
sh docs/build/tools/merge_dryrun.sh    # must exit 0 with conflicts=[none] for every open PR

# 1. Merge every open PR bottom-up, in ascending number order, as merge commits, keeping branches.
#    GitHub retargets child PRs to the merged base automatically; the `|| gh pr edit` re-points the
#    NEXT PR to `main` if it did not (belt-and-braces; append-only — branches are NOT deleted).
prev_base=""
for n in $(gh pr list --state open --json number --jq 'sort_by(.number)[].number'); do
  gh pr merge "$n" --merge --delete-branch=false
  # ensure the next PR (if any) is based on main once its base has been merged:
  next=$(gh pr list --state open --json number --jq 'sort_by(.number)[0].number')
  if [ -n "$next" ]; then
    base=$(gh pr view "$next" --json baseRefName --jq '.baseRefName')
    [ "$base" = "main" ] || gh pr edit "$next" --base main
  fi
done

# 2. Update the local main and run the full gate against the integrated tree.
git checkout main && git pull --ff-only origin main
make check                                   # expect: 2418 passed, 1 xfailed
SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db # expect: 114 passed (Docker)
SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra  # expect: 0 failed, 1 xfailed (LD-V08 → P21.4)

# 3. Tag the release, generate the SBOM, and create the GitHub release (this is where the tag is cut).
git tag -a v0.1.0 -m "SIG v0.1.0"
git push origin v0.1.0
make sbom                                    # writes sbom.cdx.json (CycloneDX)
gh release create v0.1.0 \
  --title "SIG v0.1.0" \
  --notes-file docs/build/RELEASE_NOTES_v0.1.0.md \
  sbom.cdx.json

# 4. (Optional, recommended) Protect main now that it carries the release (RISK-P20-03). NOT applied
#    by any ticket — this is an operator decision. Requires admin on the repo.
gh api -X PUT repos/SteveVitali/Eleutheria/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["python", "web"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

If you instead choose **Strategy B**, replace `--merge` with `--squash` in step 1. For **Strategy C**,
merge only the top PR: `gh pr merge "$(gh pr list --state open --json number --jq 'sort_by(.number)[-1].number')" --merge`.

---

## (e) Rollback

Merges are `--no-ff` merge commits on `main`, so a bad integration is reverted **without rewriting
history** (append-only P1–P3). Revert in **reverse** merge order (newest merge first) so each revert
applies cleanly:

```bash
# List the merge commits that landed the stack, newest first:
git log --first-parent --merges --oneline origin/main
# For each merge commit M you want to undo, in reverse order (newest first):
git revert -m 1 <merge-commit-sha>          # -m 1 keeps main's first parent, undoes the merged side
git push origin main
# The tag, if already pushed, is left in place (append-only); cut v0.1.1 after re-integration.
```

Do **not** `git reset --hard` / force-push `main`; reverts are the append-only rollback.

---

## (f) What to verify on `main` afterwards

- **CI green on `main`.** The push to `main` triggers `.github/workflows/ci.yml` (`python` + `web`);
  confirm the run is green: `gh run list --branch main --limit 1` then `gh run view <id>`.
- **The top branch is an ancestor of `main`** (the whole stack really landed):
  `git merge-base --is-ancestor origin/devin/p21-9-stage5-pathway-connectors origin/main && echo ANCESTOR`
  (substitute the actual top branch at integration time — e.g. `devin/p20-3-integration-release` if
  tagging at the P20.3 boundary).
- **Tag points at the integrated tip:** `git rev-parse v0.1.0^{commit}` == `git rev-parse origin/main`.
- **Release assets present:** `gh release view v0.1.0` shows `sbom.cdx.json` and the notes body.
- **`make check` green on the integrated `main`** (2418 passed, 1 xfailed) — the release ships a green
  tree, not an aspirational one.
