# Round-10 handoff to the running SIG orchestrator

This is a complete **planning/specification package**, not an implemented product change. It contains six researched streams, a reviewed design, 38 new canonical obligations, 28 feature contracts, three prerequisite/publication markers, and the full nine-row capstone/reconciliation/docs tail: **40 new chain rows, 161–200**. The four human/gate markers overall are HUMAN-H4, HUMAN-H5, GATE-G3 and the tail's GATE-ACCEPT. No implementation ticket has been dispatched or claimed complete by this session.

## Integrated checkpoint

The operator invoked this handoff after P31.19. [PR #155](https://github.com/SteveVitali/Eleutheria/pull/155) imports the complete package on `codex/round10-seed-after-p31-19`, based on `08d87c4`; P32.1 / round 10 are prepared. Do not import the source series a second time. Read [the import receipt](integration/2026-09-26-after-p31-19.md) for actual validation/PR/transfer status before resuming. The original source-worktree facts below describe preparation, not current execution control.

## Location and starting state

- Planning branch: `codex/sig-six-stream-research`.
- Isolated worktree: `/Users/stevenvitali/.codex/worktrees/sig-six-stream-planning/Eleutheria`.
- Base: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e` (P31.8 code commit before its closeout).
- Original active checkout: `/Users/stevenvitali/Eleutheria`; this planning run did not edit it, send its agent a message, or change its execution state.
- Integrated allocation: **ADR-120**, `docs/adr/ADR-120-six-stream-integrity-investigation-and-memory-extension.md`. The original isolated review called this ADR-115; P31 used 115–119 before import. Historical review references retain that snapshot identity; the integrated normative links now use ADR-120.
- Foundation commit: `fdc775837b2808b23a9af690c427deec5ede0a5d`. At import, pin the source branch tip and import the entire ordered series from the base above through that tip, including later preparation commits. Never cherry-pick only the latest commit or use a moving `main` as the planning baseline.

## Read order

1. Root/package AGENTS and the current DEFERRALS; retain the main ledger's actual CURRENT STATE.
2. This handoff, `BRIEF.md`, `DESIGN.md`, and `RESEARCH_LEDGER.md`.
3. `REVIEW_CLOSURE.md` and `VALIDATION.md`, then the specific `research/S1…S6` report needed for the next decision.
4. `PLAN.json`, `REQUIREMENTS.csv`, canonical §55, and the actual contract in `docs/tickets/`.

The canonical spec was updated through `spec_src/96b_partXI_s55_six_streams.md` and `BUILD.sh`. The builder now resolves its own checkout; the old hardcoded path would have overwritten the other agent's file. In the original planning series, this small tooling fix and strict planning/coverage validators were the only executable changes. The actual import also repairs the inherited npm lockfile install failure as documented in the receipt, with no existing package version changed. Product, database, ingestion and deployment code are unchanged.

## Safe integration while P31 is running

**Do not interrupt a worker mid-ticket.** The operator will pause Claude after a completed P31.12–P31.19 ticket and tell Codex to integrate. Codex then performs the complete [INTEGRATION_RUNBOOK.md](INTEGRATION_RUNBOOK.md): pin the actual clean tip, prepare and validate a child branch in an isolated staging worktree, open its own stacked PR, and transfer the original build checkout only after a final unchanged-state guard. This authorization does not permit changing the active checkout before the pause. Claude resumes afterward with fresh on-disk state; it does not perform the import itself.

Import the complete pinned planning series as a stacked planning change. Do not copy this worktree's old LEDGER over the current one: **the source branch deliberately has no LEDGER/BUILD_INDEX execution-state changes**. Integration adds only the documented control/dispatch amendments to the actual current ledger. Preserve completed tickets, gate decisions, run ledgers and RETURN PASS records. If P31 has advanced or repaired a finding, use P32.1 to reconcile the delta rather than re-running SETUP or replaying completed work. The runbook handles fixed `base_branch` references and P31.19's round-transition postcondition explicitly.

Handle conflicts by file role:

- Manifest: retain every newly landed P31 row/amendment; append the Round-10 block once. Reallocate sequence numbers only if another planned extension already occupies 161–200, updating PLAN first_sequence/last_sequence and filenames together and re-running the plan checker.
- DEFERRALS: append the six D-R10 rows; never replace later closure evidence or flip existing statuses from this package.
- ADRs: if P31 has used ADR-115, rename **only this six-stream ADR** to the next unused numeric id. Update `PLAN.json.planning_adr`, its new §55 reference (via renderer), its exact Appendix F row, BL-058's source, the new 38 coverage rows' `adrs` cells, and this handoff/validation reference. Do not globally replace ADR-115, which may now identify a different landed decision. Regenerate the ADR index and canonical spec. The plan checker rejects duplicate ADR prefixes.
- Spec: merge source amendments and appendices; regenerate the canonical build artifact. Never resolve generated-spec conflicts by hand or discard another ADR's Appendix F row.
- Coverage: preserve old and newly landed assessments; append each new id once as MISSING until implemented. Keep exact id-count declarations and routing ownership consistent with the combined spec.
- Backlog: preserve new sources/homes and allocate a different BL id if BL-058 has been taken; update this package's explicit references only. Regenerate BACKLOG.md and retain one theme home.

Run the validation block below on the integrated tree before resuming the next worker. If integration is done before P31.19, keep round 9 and its actual `nextTicket`; do not redirect it into P32 early. After P31.19 closes, record the new Round-10 plan in the ledger, retain outstanding gates/return passes, set the next row to P32.1 and round to 10, and point canonicalSpec to the actual canonical spec as supported by the orchestrator format. Do not mark the new round DONE simply because its contracts exist. Resume the existing orchestrator; do not re-run SETUP.

## Execution and human boundaries

The Run lines start engineering with `live_verification=false`. They do not waive a contract's live acceptance. A bounded live stage reuses the same ticket after the recorded scope/approval, with `live_verification=true`; its owed row cannot close from a fixture pass. Marker dependencies block their actual consumers and cannot be skipped without an explicit operator decision.

- P32.1 reconciles the settled P31 baseline and remaining known defects. P31.9–16 ownership is preserved.
- P32.2–8 establish integrity and memory tooling. Event/closeout enforcement remains shadow-only until the actual worker/orchestrator entry points have undergone an approved boundary cutover (D-R10-MEMORY-1). This package does not change installed global skills.
- P32.9–10 build independent-label/evaluation tooling, initially shadow-only. P31's existing PROVISIONAL posture is not silently certified or globally replaced by installing a new evaluator.
- Source/dossier work has concrete target and size limits. Existing valid permissions persist within their scope; only genuinely new/changed rights or exposure requires its gate. Metadata-only network-audit targets are not raw workbook acquisition instructions.
- P32.22 freezes the repaired snapshot. HUMAN-H4 completes human development/calibration labels and separate documentary semantic review. P32.22a then selects/freezes the candidate and draws its confirmatory frame/sample. HUMAN-H5 completes the final independent blinded labels for that candidate-specific sample. Development labels cannot become final holdout.
- P32.23 unseals once to evaluate the already-frozen P32.22a candidate. It cannot tune or select a new candidate from the final results; a subsequent candidate requires a new independent assessment. P32.23a rematerializes every affected artifact afterward. P32.24 tests that exact candidate.
- GATE-G3 presents the actual release and intake operating packet for HG-11 and separately scoped approvals. P32.25 publishes only the accepted bytes. Current withdrawal controls also apply during rollback.
- The full tail audits independently, executes composed checks, records actual accepted deviations, reconciles spec/backlog/integration, and refreshes repo/agent docs. No ticket merges, tags, or pushes main.

## Validation commands

Run from the integrated checkout:

```sh
python3 docs/build/planning/2026-09-25-six-streams/tools/check_plan.py
python3 docs/build/planning/2026-09-25-six-streams/tools/render_plan.py --check
python3 docs/build/planning/2026-09-25-six-streams/tools/test_planning_tools.py
python3 docs/build/planning/2026-09-25-six-streams/tools/test_integration_preflight.py
python3 docs/build/tools/check_spec_src.py
python3 docs/build/tools/test_check_spec_src.py
python3 docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv
python3 docs/build/tools/check_backlog.py
python3 docs/build/tools/build_backlog_md.py --check
make docs-check
make check
```

While another checker is running, the current vendored memory validator's `/tmp/build-memory-check.json` path is shared. Use the isolated-output validation wrapper in this package until P32.8 changes the actual protocol, or wait for the other check to finish; do not consume a report whose input identity is uncertain. Test results and any baseline failures/skips are recorded in VALIDATION. Production/database/evaluation acceptance still belongs to the future tickets.

## Pause and resume

Tell Codex: **“Paused after P31.<completed ticket> — integrate Round 10.”** The supported actual boundaries are P31.12/.13/.14/.15/.16/.19; P31.17 is dropped and P31.18 moved. Codex follows INTEGRATION_RUNBOOK.md and returns the PR plus verified resume state. Its final section contains the exact prompt for the existing Claude session. Do not resume that session while Codex is preparing or transferring the branch.
