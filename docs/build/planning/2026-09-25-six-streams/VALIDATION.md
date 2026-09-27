# Planning validation

Status: COMPLETE — planning validation and handoff ready. This document records planning checks, not future implementation acceptance. Final checks recorded 2026-09-25, approximately 19:13 UTC.

Baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`. Worktree: isolated `sig-six-stream-planning`; active Claude checkout untouched. Product/database/source runtime changes: none. Executable changes are limited to checkout-relative spec assembly, exact new-id/routing declarations in doc checks, a stale doc-check count assertion, and planning generation/validation tools.

Expected inventory: six research reports; 27 researched candidate rows with per-row review depth; 38 new normative requirements (715 total); 40 new manifest rows (161–200); four pending human/gate readouts; six new explicitly OPEN prerequisite/return-pass rows; one planning ADR (115 at the snapshot) and backlog home BL-058. The main LEDGER and BUILD_INDEX have no changes in this planning branch.

| Check | Result | Scope / limit |
|---|---|---|
| `make check` | PASS; **4,218 passed, 6 skipped**, one dependency deprecation warning; pytest 267.61 s | Ruff, formatting, mypy (255 source files), pytest and generated-artifact verification; executed in the isolated worktree. Later changes were planning text/count/sequence refinements, followed by the targeted checks below. |
| Staged documentation-sensitive regressions | PASS; **131 passed, 2 skipped** | `tests/connectors/test_secrets.py`, `tests/unit/test_policy_adrs.py`, `tests/unit/test_backlog_housekeeping.py`, after adding the new files to the index. Skips are unset credential/project environment controls, not fabricated successful scans. |
| Planning regression suite | PASS; **5 tests** | Reject duplicate/missing requirement ownership, forward dependencies, invalid tail; spec-builder execution from another cwd leaves that other checkout's sentinel unchanged. |
| Spec-source regression suite | PASS; **8 tests** | Includes byte-identical assembly, requirement grammar/reserved ids and the corrected exact extension count. |
| `check_plan.py` | PASS | 40 ordered new rows; 38 singly owned new requirements; all dependencies point backward; required research/contract/handoff files present; full nine-row tail; no colliding ADR prefix. |
| `render_plan.py --check` | PASS | Actual contracts, requirement map and §55 source match reviewed PLAN.json. |
| `check_spec_src.py` | PASS | Byte-identical canonical assembly; **715 requirements**, no duplicate/malformed/reserved definitions, closed references; **114 ADR files = Appendix F set** (ADR-064 is a pre-existing absent number). |
| Coverage/backlog/mirror | PASS | 715 coverage rows; 102/102 deferred risks, 114/114 ADR revisit homes, 90/90 legacy deferrals, 45/45 owed deferral homes; zero duplicate sources; BACKLOG.md current. |
| Repository-doc detector | PASS with one stale suspect | 358 scanned docs, zero critical broken references; existing root README is four days behind `docs/build/tools/run_okc.sh`. Semantic refresh is scheduled in S6; detector green is not a claim all prose is current. |
| Agent-doc detector | PASS | Eight AGENTS docs scanned, zero structural issues. Known semantic zero-JS/island drift is explicitly researched and scheduled; the detector does not establish semantic freshness. |
| Build-memory detector | PASS, zero violations, one warning | Output redirected in a private copy with unchanged detection logic. Its broad ADR scan reads the intentionally preserved ledger `canonicalSpec: docs/build/reports/DECISION_MEMO.md`, hence warns that its ADR mentions differ from current files. The dedicated canonical checker above verifies the real Appendix F exactly. Integration updates the control pointer at the appropriate boundary. |
| Candidate CSV | PASS | 27 unique researched candidates, 18 columns; per-row inspection depth/limitations retained. This is structural verification, not source-rights clearance or uniform full-document inspection. |
| Diff/scope check | PASS | All staged changes are under `docs/`; no LEDGER or BUILD_INDEX execution-state change, product/runtime/ontology-generated change, log, secret or dependency artifact. Historical coverage/backlog bytes are preserved with only new rows appended. |

The full suite's six skips were: live staging API unset/unreachable; GCP project leak-check variable unset; no credential variables exported for credential scanning; and three composed web-build checks without the web dependency environment. No web product code changed, so a separate npm install/build was not added solely for this planning package. No live deployment, source acquisition, human campaign or public write was run. The single warning was Starlette's existing httpx TestClient deprecation.

The coverage CSV already used CRLF. Its historical bytes and append style were retained; the diff whitespace check used `git -c core.whitespace=trailing-space,space-before-tab,cr-at-eol diff --check` so intentional CRLF is not misreported as trailing whitespace. This does not relax content or ownership checks.

Raw logs are only under ignored `docs/build/logs/`: `six-stream-make-check.log`, `six-stream-staged-doc-tests.log`, `six-stream-final-check-repo-docs-freshness.log`, `six-stream-final-check-agent-docs-freshness.log`, and `six-stream-final-memory-summary.log`, with uniquely named detector JSON beside them. The first freshness run used the tools' standard temporary report locations; final freshness/memory runs used isolated destinations. No checker edited the active Claude checkout.

Four independent review reports and follow-ups are preserved in `reviews/`. All material design findings were addressed in actual contracts; the final statistical recheck confirmed candidate selection precedes confirmatory sampling. The stale “post-H4” evaluator activation reference identified in that last pass was corrected to post-HUMAN-H5/P32.23 and contracts re-rendered. This is planning review closure, not a pass for future implementation.

Final integration still requires the actual P31 tip/ADR/BL/sequence collision check and the same validation commands on the combined tree. No test result from this older isolated base certifies the evolving active branch. HANDOFF.md makes that boundary explicit.

## Ticket-boundary integration preparation — 2026-09-25

Added INTEGRATION_RUNBOOK.md and a read-only local preflight after the operator requested a single-instruction future import. This is a follow-up to foundation commit `fdc775837b2808b23a9af690c427deec5ede0a5d`; the eventual import must include the complete source series. No PR or active-chain import has been performed. The active checkout, runtime ledger, existing build-stack branches and running Claude session remain unmodified by this preparation.

- Integration preflight regression suite: **6 tests passed**, including subtests for all six actual pause boundaries; current-vs-historical control parsing; duplicate keys; stale/blocked state; changed-snapshot refusal; and a real disposable Git repository proving a two-commit source series is retained, expected deferral changes are allowed, pause attestation is required, and dirty files are preserved. The macOS temporary-path alias was normalized so the same physical checkout compares correctly.
- Planning regression suite: **7 tests passed**, including consistent sequence-block relocation and collision rejection. PLAN now declares `first_sequence` as well as `last_sequence`; the delivered block remains 161–200.
- Both new Python tools pass Ruff. Plan/render, spec-source (8 tests), 715-row coverage, backlog and Markdown-mirror checks pass with the same inventory as the foundation package.
- A read-only preview against the active build correctly returned **not ready**: the session was still working, with an unfinished branch/ledger boundary and dirty files. This was expected and caused no intervention. Readiness will be assessed afresh only at the operator's explicit pause; this preview is not a reservation of that future state.
- Private detector outputs and raw verification logs are under ignored `docs/build/logs/round10-integration-*`; no shared checker report is used as evidence for this preparation.

Final integration-preparation checks: **`make check` PASS** (4,218 passed, 6 skipped, one existing Starlette deprecation warning; pytest 537.03 s), including clean generated-artifact verification. The six skips have the same live/credential/web-environment limits listed above. Repository detector: 358 docs, zero broken references, one existing stale suspect; agent detector: eight docs, zero issues (run with its required relative `.` scope); private build-memory detector: zero violations and the same preserved-DECISION_MEMO-pointer warning. Generated ontology/lock files are unchanged. Final change scope is ten files within this planning package; the combined future P31/import tree still requires fresh validation at the pause.

## Actual P31.19 integration — 2026-09-27 UTC

The snapshot results above remain historical. The combined tree at paused base `08d87c4` is validated in [the import receipt](integration/2026-09-26-after-p31-19.md): ADR-120, 715 obligations, 119 ADR files; plan/preflight/spec regressions 7/6/8; docs and build-memory checks zero violations/warnings; full `make check` 4,404 passed / three live-or-credential-environment skips, clean generated artifacts; web unit 222, browser 246, licence check 228 dependencies, all eight Lighthouse budget URLs. Clean CI-version npm install passes after a bounded inherited lockfile repair. The original checkout remains paused until the guarded PR/checkout handoff completes.
