# Insert Round 10 into the paused P31 stack

Status: **Procedure prepared; execution is now tracked in [the P31.19 import receipt](integration/2026-09-26-after-p31-19.md).** This is the durable procedure for Codex to perform when the operator says, for example, **“Paused after P31.14 — integrate Round 10.”** The operator's request authorizes the branch/import/reconciliation/checks/feature-branch push/stacked PR and final checkout handoff described here. It does not authorize interrupting the running session now. No global skill, product, production resource or human gate changes as part of this import.

The operator pauses the orchestrator **and any outstanding ticket worker**, after the ticket's code, verification, PR push and build-memory closeout have finished. A quiet terminal, an open PR or a code commit alone does not prove a clean boundary. Codex will perform the surgery; the Claude session only reloads state and resumes afterward. No additional confirmation is needed for routine reconciliation already authorized here. If the actual boundary is incomplete or materially different, report the concrete discrepancy instead of discarding work or guessing a completion.

## 1. Capture the boundary without changing it

Work from the planning worktree until explicitly performing the final handoff. The active build path remains `/Users/stevenvitali/Eleutheria`. Re-read the installed `orchestrate-build` skill, root/package AGENTS, current LEDGER, DEFERRALS, manifest, BUILD_INDEX and completed ticket/run/PR body. Installed skill behavior may have changed since this runbook was prepared.

Use the read-only helper from this package (replace the completed id with the operator's actual boundary):

```sh
python3 /Users/stevenvitali/.codex/worktrees/sig-six-stream-planning/Eleutheria/docs/build/planning/2026-09-25-six-streams/tools/integration_preflight.py \
  --repo /Users/stevenvitali/Eleutheria --expect-last P31.14 --paused
```

Save its JSON in a unique operation directory under ignored `docs/build/logs/` **in the staging/planning worktree**, not the active checkout. `--paused` is an operator attestation, not an automated process detector. Omit it for a read-only preview; the helper correctly refuses readiness. Exit 2 means some prerequisite remains unresolved; it never edits a ledger, switches a branch, stashes files or contacts a remote.

Manually confirm the completed ticket's run and BUILD_INDEX evidence, PR base/head, pushed closeout commit and required acceptance. The helper verifies local structure, not these semantic/remote facts. Use read-only GitHub CLI/API checks against the repository's observed remote; do not infer the owner/repo. Confirm the working tree is clean, no sequencer/rebase/merge is active, the current branch equals ledger `chainTip`, and HEAD is the actual completed-ticket tip. Retain this exact `paused_branch` / `paused_sha` and control-file hashes for the final guard. `buildBranchBase` and `pinnedBaseSha` describe the original stack root; **do not change them to the import base**.

The actual runnable boundaries are:

| Last completed | Resume next | Round after import |
|---|---|---|
| P31.12 | P31.13 | 9 |
| P31.13 | P31.14 | 9 |
| P31.14 | P31.15 | 9 |
| P31.15 | P31.16, subject to its existing HG-11 protocol | 9 |
| P31.16 | P31.19 | 9 |
| P31.19 | P32.1 | 10 |

P31.17 was dropped and P31.18 moved; do not create, resurrect or dispatch them. Fresh manifest ordering takes precedence if a new intervening contract was deliberately added. Reconcile such a change explicitly; never skip that row to satisfy this table. A real `blockedOn` remains a block until its existing evidence/decision requirement is satisfied. An independently seeded Round 10 requires reconciliation with that seed, not a second import. A pending gate/RETURN PASS is not itself proof of an unfinished code closeout, but its authorized disposition must be preserved.

## 2. Freeze the complete source and prepare an isolated child branch

The source branch is `codex/sig-six-stream-research`. Record its **full resolved SHA** at the pause, then use that immutable SHA for the operation. Its base is `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`; its foundation commit is `fdc775837b2808b23a9af690c427deec5ede0a5d`. Import the **entire ordered series `base..source_tip`**, including both the foundation and all later integration-preparation commits. Importing only `git log -1` would omit the 40 contracts and spec amendment.

Check the source worktree for uncommitted work; do not silently omit pending changes. Inspect the complete source diff and every commit. The helper requires a linear series beginning with the foundation, docs-only changes, and no source edits to LEDGER or BUILD_INDEX. Manifest and DEFERRALS are expected append/merge inputs; they also appear in the active-checkout fingerprint so concurrent edits cannot be missed. Confirm source and paused tip share the expected repository ancestry.

Create a unique `codex/round10-seed-after-p31-<n>` branch **at `paused_sha`**, checked out in a new temporary integration worktree. Record its path. If that name or a previous receipt/PR already exists, inspect it and recover the operation instead of overwriting or opening a duplicate. The existing planning worktree stays intact; the active build worktree stays on `paused_branch` throughout preparation.

Apply the frozen commit series into the integration worktree. A no-commit cherry-pick of the ordered list permits semantic reconciliation and validation before the new import commit; if Git stops for conflicts, inspect the sequencer and resolve each file by role before continuing. Do not use automatic “ours/theirs” for memory/spec files. No original planning history needs to be rebased and no active branch needs to be reset. New import commits may consolidate the source series, with its SHAs recorded as provenance.

## 3. Reconcile by file role, preserving concurrent P31 work

Use [HANDOFF.md](HANDOFF.md) for detailed ownership and scope. The import must contain the following:

- **Execution memory:** retain the active versions of LEDGER, BUILD_INDEX, all completed run ledgers, PR bodies, gate answers and RETURN PASS history. Never copy their older planning-base versions. New contracts have not landed; do not add 40 completion rows to BUILD_INDEX. The planning PR is recorded in a dedicated import receipt and PHASE LOG event, not as a fake completed implementation ticket.
- **Manifest and contracts:** retain every P31 row and amendment, append the new 40 rows once, and preserve the complete nine-row tail. If 161–200 are occupied, allocate the next contiguous free block after the retained chain, change `PLAN.json.first_sequence`, `last_sequence`, every ticket sequence/filename and all affected links/row references, regenerate with `render_plan.py`, and run its checker. Remove obsolete filenames only from this unlanded package. Semantic ticket/marker/requirement collisions need an explicit scoped migration map; never silently repurpose an existing id.
- **ADRs:** P31.9 already used ADR-115, so the six-stream ADR will need the next unused number at the actual pause. Preserve landed ADR-115/116 and every other landed body. Rename only this unlanded planning ADR and its scoped references: PLAN, generated §55, exact Appendix F row, its backlog source, new coverage rows and package cross-references. Regenerate the ADR index with the installed build-memory tool, not by hand. Record old→new allocation in the receipt. Existing research references to earlier ADRs retain their original identities.
- **Canonical spec:** keep all P31 source amendments and appendices. Resolve `spec_src`, then run its checkout-relative `BUILD.sh`; never resolve the generated canonical file independently. Preserve added P31 requirement definitions and assessments. Recompute total declarations and validator expectations from the merged canonical definitions rather than restoring the snapshot's 715 blindly.
- **Coverage, backlog, deferrals:** append the 38 new obligations with their owners and honest MISSING status; preserve every P31 assessment. Allocate BL-058 elsewhere if occupied and update only this package's references. Merge all new backlog sources/homes, regenerate its Markdown mirror, and verify one home per owed item. Append six D-R10 rows and four PENDING marker readouts without changing existing closure evidence or signing anything. Existing dated source research remains a snapshot; P32.1 owns baseline reconciliation.

Review the entire diff against `paused_sha`: expected scope is planning/docs/tooling plus the minimum documented control/contract continuity amendments below. No product/runtime/ontology/source-permission/deployment changes are authorized by this import. Validate live acceptance through existing evidence; an older planning test result does not certify the new combined tree.

## 4. Make dispatch continuity explicit

Add a dated **Round-10 import operating amendment** near the current ledger control section and in the manifest's operating instructions. It supersedes conflicting historical fixed-base/terminal wording without erasing it:

> This planning PR is a real link in the current stack. Dispatch every next worker from the freshly read CURRENT STATE `chainTip` and the actual checked-out HEAD, retaining all previous commits. Historical ticket `base_branch` strings identify the originally expected predecessor; they must not cause a checkout of a branch that omits this seed. Resolve the effective base before dispatch and pass it explicitly to the worker. After successful P31.19 closeout, continue at P32.1 / round 10 / IN-PROGRESS. Do not re-run SETUP or stop globally at the Round-9 capstone while the seeded Round-10 rows remain outstanding.

For the **immediately next unstarted P31 contract**, append a dated dispatch amendment naming the new integration branch as its effective base, explicitly superseding its old `base_branch`. Do not rewrite completed contracts. Following workers use the newly advanced ledger tip, not a permanent pointer back to this seed branch. Verify the manifest and any legacy PHASE PLAN are clearly subordinate to CURRENT STATE/current manifest; no installation-wide skill edits are required.

If P31.19 has **not** run, append its dated closeout amendment with concrete postconditions:

1. Preserve all existing Round-9 deliverables, live checks, scope and gates.
2. Successful closeout records `lastCompleted: P31.19`, `nextTicket: P32.1`, `round: 10`, `projectStatus: IN-PROGRESS`, and the actual P31.19 branch as `chainTip`; the orchestrator continues after its usual verification. Round-9 capstone completion is not global completion of the seeded chain.
3. Human/evaluation obligations have actual homes **HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23**; old references to “Round 10/P31.18” are historical, not a second scheduled ticket. PROVISIONAL stays until the new evidence-backed decision permits a change.
4. Keep the 2026-10-10 replay obligation and its verify command OPEN if unperformed, and preserve every legitimate HG-11/other return pass. Scheduling P32 does not certify any of them.

If P31.19 **already** closed, do not replay it or edit its executed acceptance retroactively. Record a compatibility/activation note in the ledger/receipt linking its actual closeout; seed the new round from that evidence. A previous DONE or exhausted-next sentinel becomes IN-PROGRESS/P32.1 because the operator has now added a new plan. Any unexpected independently scheduled next row must first be reconciled.

Set CURRENT STATE minimally on the integration branch:

| Key | Value |
|---|---|
| `lastCompleted` | Actual paused P31 ticket, unchanged |
| `nextTicket`, `round` | Boundary table, reconciled with fresh manifest |
| `projectStatus` | IN-PROGRESS for the expanded chain |
| `chainTip` | New integration branch, until the next worker advances it |
| `canonicalSpec` | `docs/2_canonical_design_spec.md`; historical DECISION_MEMO references remain history |
| `buildWorktree` | `/Users/stevenvitali/Eleutheria`, even while preparing in staging |
| `pauseRequested` | `true` during import; `false` only in final resume-ready closeout unless operator asks to remain paused |
| `updatedAt` | Actual time and import event/receipt reference |
| All other keys/history | Preserve, including `blockedOn`, gates, RETURN PASS, dispatch/autonomy, original stack base and pinned SHA |

The operator's future “integrate” instruction in this workflow includes preparing a resumable checkout. Setting the final pause flag false does not launch a worker. The user resumes Claude after handoff; Codex never sends the session a prompt or starts implementation automatically.

## 5. Validate, commit, push and open the planning PR

Create `docs/build/planning/2026-09-25-six-streams/integration/<operation-id>.md` as the committed receipt (use a unique date/boundary suffix); keep raw logs ignored. Include:

- operator pause instruction and completed-ticket evidence; exact pre-import branch/head/control hashes;
- source base/foundation/tip and ordered imported commits; integration branch and staging/build paths;
- allocation map, resolved concurrent changes and effective-next-ticket amendment;
- old/new control values, P31.19 transition, preserved gates/return passes;
- commands/results/skips and log paths; before/after scope checks;
- PR URL/base/head verification and handoff procedure/status.

Do not claim a future switch has happened in a pre-switch receipt, and do not make a commit contain its own SHA. Record the validated import commit and PR URL in a subsequent closeout commit; verify the final commit/head externally after pushing. A later worker can append the observed handoff result. The final Codex response must report the actual checkout/remote head and any incomplete step.

Run [HANDOFF.md](HANDOFF.md)'s full validation block, including both new integration tests and the isolated memory detector. Run `make check` before **each** commit as required by AGENTS; use the merged tree's commands. Inspect skips and preserve honest live acceptance. Run applicable additional checks if reconciliation changes executable behavior. The import is docs/tooling-only, so do not initiate production jobs, publication or source acquisition as “verification.” If web/package changes unexpectedly enter the diff, investigate scope rather than absorbing them silently. Check CRLF-aware diff whitespace, no duplicate ids/manifest rows, spec byte identity, exact ADR appendix coverage, all paths, and correct dependency order.

Make an import commit with `pauseRequested: true`. Push only the new feature branch. Open its own stacked PR with **base = `paused_branch`**, never `main`; the base branch must still resolve remotely to the inspected paused tip. Existing ticket PRs remain untouched. Use a description file (`gh pr create --body-file ...`) describing the six streams, 40 rows, current boundary, source/allocation provenance, preservation of P31 and checks. Attach the created PR to this Codex task with `attach_artifact`. Write its body under `docs/build/pr/` using a descriptive planning-import filename, not an invented implementation id.

Then append the actual PR URL and validation evidence to the receipt/PHASE LOG, set resume-ready `pauseRequested: false` as above, run required checks, commit and push the closeout. Verify the remote PR head is exactly the final local commit and its base still matches the paused branch. Check any required CI on this exact head; stale successful CI on an earlier commit is not final evidence. If required CI is pending/failing, keep the handoff pending and report the precise state. Reuse the existing PR on retry. No force push, merge, tag, retarget of old PRs or push to main.

## 6. Guard and transfer the checkout, then hand back

Before switching the original worktree, rerun preflight with the frozen source SHA and `--compare <saved-preflight.json>` against the **original** checkout. Recheck remote base/head and the operator's pause still applies; no worker may have resumed. Confirm its branch, HEAD, cleanliness and control hashes exactly match the saved snapshot. Any drift stops the transfer for reinspection; do not reset, stash or clean another session's changes.

Git will not check out the same branch in two worktrees. After all validation/push/PR work succeeds, detach the **staging** worktree at the verified final commit to release the integration branch, then switch `/Users/stevenvitali/Eleutheria` to that existing integration branch. Do not create another branch or change the runtime path. Confirm the original checkout's HEAD equals the verified PR head, it is clean, and its ledger `chainTip`/next/round match the intended transition. Keep the old P31 branch unchanged and retain the staging worktree/logs until handoff is accepted; no automatic branch/worktree deletion.

Return the PR link, actual branch/head, exact next ticket and this pasteable resume instruction:

> Resume `~/.claude/skills/orchestrate-build/SKILL.md` with `ledger=docs/build/LEDGER.md dispatch=subagent autonomy=checkpoint build_worktree=/Users/stevenvitali/Eleutheria`. The operator paused you and Codex inserted the Round-10 planning PR into the stack. Reload the current checkout and CURRENT STATE from disk; discard cached branch/next-ticket assumptions. Read the dated import operating amendment, integration receipt, current manifest, DEFERRALS, BUILD_INDEX and root/nearest AGENTS before dispatch. Do not run SETUP. Fork the next worker from the current ledger chainTip/actual HEAD, including this seed. Finish the remaining P31 rows; after successful P31.19 use P32.1 / round 10 / IN-PROGRESS and execute the 40-row extension in manifest order. Preserve all existing human gates, return passes and truthful evidence requirements. Do not merge, tag or push main.

The 40 rows include human/gate markers and the full tail. They are not 40 unattended coding jobs. H4/H5 require actual independent human work; source-rights, publication and acceptance markers retain their protocols. This integration removes branch/state friction, not those deliberate decision points.

## Recovery and stopping conditions

Before the checkout transfer, the original worktree remains untouched. Resolve routine conflicts in staging and rerun relevant checks; preserve diagnostics on genuine failure. If the remote push/PR result is uncertain, query by exact head/base and existing receipt before retrying. If a previous attempt already imported the plan, inspect its ledger and PR and continue its unfinished closeout; never append the block twice. The preflight intentionally rejects already-present P32.1/package as a recovery case.

If the original session advanced, pin a new boundary with the operator instead of transplanting onto stale HEAD. If transfer fails because staging still holds the branch or original files changed, retain both branches and diagnose; no destructive recovery. If a failure happens after switching, report the actual resulting branch/state and repair additively under the continuing pause. Never report “ready to resume” until the exact checkout/ledger/PR-head invariants above hold.
