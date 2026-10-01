# Run ledger — SEED-02c (Round 11 Stage B, T2 — guard core, context 3 of 3): vendored validator sync to build-memory 0.5.0

- **Harness:** claude-code/claude-opus-5-5/subagent
- **Skills:** 8aeb6dc
- **Started:** 2026-10-01T07:48:00Z (the unit's first `date -u`, taken at the baseline run; reading the brief and T0c came a few minutes earlier, unclocked)
- **Closed:** 2026-10-01T08:16:12Z
- **Unit:** SEED-02c — sync `scripts/docs/check-build-memory.sh` (the P32.8 / ADR-127 fork) to build-memory release 0.5.0, vendor
  `adr-index.sh` 0.5.0 and `check-history.sh`, check every consumer; brief `PD/stageB/AGENT_BRIEF.md`, sync list
  `PD/stageB/T0c_sync_obligations.md` (`PD` = `docs/build/planning/2026-09-30-next-phase/`).
- **Worktree / branch:** `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (no git state changed by this unit; the
  planning orchestrator commits). HEAD moved 4685a0cb → 850805aa → 4a921bb9 → 02bf5d56 under other units during the run.
- **Source:** `~/agent-skills` at `8aeb6dcd55a26a049bfb2092dd32e0e286761f6f` (`.claude-plugin/plugin.json` version 0.5.0 =
  e172f52 "Release 0.5.0" + 4140fda + 8aeb6dc; skills tree clean; `~/.claude/skills/build-memory` is a symlink into it, and
  the live files hash-equal the HEAD blobs). Upstream sha256: check-build-memory.sh `f48a365d…e118` (same blob at 4140fda and
  8aeb6dc), adr-index.sh `f73fd585…` (unchanged since c814f8d), check-history.sh `508fe94b…` (8aeb6dc adds the closed-run-ledger rule).

## Files

| file | change |
|---|---|
| `scripts/docs/check-build-memory.sh` | replaced: upstream 0.5.0 + provenance banner + three `SIG-LOCAL` hunks (L1–L3 below); the banner keeps the words "LOCAL PATCH" that `test_no_unmodified_vendoring_claim` requires, truthfully |
| `scripts/docs/adr-index.sh` | replaced: upstream 0.5.0 + provenance banner; body byte-identical (the P22.3 banner wrongly described the validator's detection logic — corrected) |
| `scripts/docs/check-history.sh` | new (mode 755): upstream 0.5.0 + provenance banner; body byte-identical; one banner line corrected by hand after vendoring (noted here at 2026-10-01T08:16:41Z; the generated banner also said "replaces the P22.3 vendor", untrue for a new file) |
| `docs/build/runs/SEED-02c.md` | this ledger |

Each banner records the skill commit, the release, the upstream sha256, the vendoring time (`date -u` in the writing
command: 2026-10-01T08:02:02Z) and a one-line verification:
`diff <(sed '2,/^# ---- end of SIG vendoring banner ----/d' scripts/docs/<f>) ~/.claude/skills/build-memory/scripts/<f>`
→ only the three SIG-LOCAL hunks (validator), no output (the other two). Verified after writing: 13 diff lines / 0 / 0.

## Three-way review (upstream base 6e4a863 ↔ SIG fork P22.3+P32.8 ↔ 0.5.0)

SIG P22.3 (4d5a5d27) = upstream 6e4a863 + banner (14 lines). P32.8 (5f4772d8) patched output/reporting only. Upstream 360106b
(2026-09-10) later added duplicate-by-id and tolerant DEFERRALS parsing, which the SIG fork never took. Every P32.8 hunk:

| SIG-fork behaviour (P32.8 unless noted) | in 0.5.0? | disposition |
|---|---|---|
| `--json PATH` / `--json=PATH`; unique `mktemp` default; report path on the last stdout line; parent dir created | yes | upstream |
| report `build-memory-check/2`: `input {repo, commit, dirty, input_digest}`, `summary.exit`, diagnostics `{check, severity, file, obligation, evidence, message}`, atomic `.tmp` + `mv` | yes (+ `guards`, `counts`, `input.now`) | upstream; input_digest identical on the same tree (both scripts on a static HEAD export: `d7aa311d…` = `d7aa311d…`) |
| `dirty` also counts the canonical spec (`git status -- … ${SPEC_REL:-docs/2_canonical_design_spec.md}`) | no (dirty covers docs/build, docs/tickets, docs/adr only, though the digest reads the spec) | **kept — L1**: dirty covers the spec when it resolves inside the repo (`bash -x` shows `_sig_spec=docs/2_canonical_design_spec.md`) |
| unwritable report → stderr message + **exit 2** | no (prints the error, exits with the check code) | **kept — L2**; checked: `--json /dev/null/nope/r.json` → vendored exit 2, upstream exit 1 |
| human line `- check [obligation] file: message` | no (`- check: message`) | **dropped (D1)** per the unit prompt/T0c ("human output `- check: message`"); the JSON keeps file/obligation; no consumer parses stdout except the `JSON:` line |
| `input.repo` = the argument as passed (`.` from the Makefile) | no (resolved absolute path) | **dropped (D2)**: upstream names the real worktree; tests pass absolute paths and still match |
| not-a-build-memory report: top-level `repo` key, no `input` | no (full report, `input.repo`) | **dropped (D3)**: no consumer reads the top-level key; `test_non_repo_exit_2_report_agrees` passes |
| per-call-site slots: sequence-dup id as `evidence`, nextTicket value as `evidence`, manifest path literal | upstream puts the id in `obligation` and uses `$MANIFEST_REL` | upstream (no consumer reads these slots) |
| `--help` prints lines 24–44; an unknown `-x` becomes the repo argument | upstream prints the whole header; unknown flag → exit 2 | upstream |
| (6e4a863) duplicate key = NN prefix; DEFERRALS status = first word of the last cell | 0.5.0: duplicate **ticket id**; first canonical token anywhere in the last cell | upstream (T0c "inherited"); the SIG tree passed the stricter rules, so no finding changes |
| (6e4a863) PHASE LOG "done" scan over every `- ` line of LEDGER.md | 0.5.0: PHASE LOG regions only, markup stripped, region-aware severity, exit 3 when vacuous | upstream (contract change of 0.5.0, not SIG-local) |

**Found by this unit — L3 (kept as a SIG-local fix, an upstream candidate):** `emit_diags` read the tab-separated records with
`IFS=<tab>`; tab is IFS whitespace, so bash merges adjacent tabs and any diagnostic with an empty file/obligation/evidence
field put its message under the wrong key. Present in the P32.8 fork (old report on HEAD: `"obligation": "docs/adr/README.md
does not match…", "message": ""`) and in upstream 0.5.0 (68 of 69 warnings with an empty `message` on the base export).
L3 splits on `\037`; after it: 0 empty messages, human output unchanged (diff of the `-`/`~` lines is empty).
`check-history.sh`'s `diags()` has the same defect (an empty `commit` shifts `rule`/`message`); left unpatched
(byte-identical vendor; SIG's `memory_guard.*` takes over whenever present) and named in its banner.

## Consumers

| consumer | invocation | status |
|---|---|---|
| `Makefile` `docs-check-build-memory` (in `docs-check`) | `bash scripts/docs/check-build-memory.sh . --json docs/build/logs/build-memory-check.json` | works (report written; not edited) |
| `.github/workflows/ci.yml` docs job | `make docs-check` + `bash scripts/docs/check-build-memory.sh .` | works unchanged (not edited; SEED-02b) |
| `docs/build/tools/closeout_protocol.py` `VALIDATOR_DEFAULT` | same as the Makefile, `--json docs/build/logs/closeout-validator.json`; reads the exit code only | works |
| `tests/unit/test_check_build_memory_report.py` (8) | runs the vendored script on fixture trees | 8 passed |
| `tests/unit/test_ci_workflows.py` (2) | parses ci.yml | 2 passed |
| `check-build-memory.sh` → `adr-index.sh --check [--legacy]`, `--range/--staged/--first-parent` → `check-history.sh` → `docs/build/tools/memory_guard.py` | through `SELF_DIR` = `scripts/docs/` | works; with the hook: "delegating to docs/build/tools/memory_guard.py", exit 0 on `HEAD~1..HEAD` (4a921bb9) |
| `scripts/ci/secret_scan.py` | comment only (same token shapes) | unchanged — 0.5.0 keeps the same `SECRET_RE`, adds `--exclude-dir=logs` |
| `docs/build/tools/check_backlog.py` L119/L131 | comment/docstring: "the status is the first word of the row's last cell (the same convention … check-build-memory.sh uses)" | **now stale** (0.5.0: first canonical token anywhere in the cell); code unaffected; not my file — reported |
| `docs/build/tools/CLOSEOUT_WRITER_PROTOCOL.md` §contract/patch/3 | describes the vendored copy as the P32.8 fork, "detection logic … unchanged" | **now stale**; not my file — reported (an appended dated note is the append-only way) |
| `AGENTS.md` L139, `docs/build/README.md` L29, `docs/README.md` L30 | name the scripts and their use | still accurate |

## Checks

| check | result |
|---|---|
| `make -k docs-check` **before** (07:48Z, worktree at 850805aa + uncommitted) | make exit 2; repo-docs 0 broken refs; agent-docs 0 issues; build-memory exit 1: **1 violation** (`adr`: docs/adr/README.md ≠ a fresh adr-index regeneration), **1 warning** (BM-ADR-04 spec appendix ≠ file set) |
| `make -k docs-check` **after** (08:06Z, worktree at 4a921bb9 + uncommitted) | make exit 2; repo-docs 0; agent-docs 0; build-memory exit 1: **1 violation** (the same `adr` index violation), **74 warnings**, `guards: false` |
| old fork vs vendored, same moment, same tree (08:08Z) | old: 1 V / 1 W; vendored: 1 V / 74 W — same violation |
| both on a static export of the planning head 4685a0cb (before any SEED-11 ADR) | old: 0 V / 0 W; vendored: **0 V / 69 W**; vendored findings == the skill copy run directly |
| both on a static export of 850805aa | both 1 V (the index); vendored 69 W |
| `uv run pytest tests -q -k "build_memory or check_build_memory or docs"` | **63 passed, 1 failed**, 5514 deselected (files: test_build_memory_audit 20, test_check_build_memory_report 8, test_repo_docs_current_state 8, test_governance_docs 12, test_agent_docs_current_state 6, test_license_headers 5, test_ci_workflows 2, test_policy_adrs 1, test_source_registry 1, ontology/test_generation_gate 1) |
| skill suite `tests/run-tests.sh` on a scratch copy of the skill with the three vendored files swapped in, vs the same copy pristine | identical PASS/FAIL sets: adr-index, clock-tz, history, ledger-variants, new-files, planning-v14, seed-from-templates, truth-checks, v2-* PASS in both; the same 8 failures in both (memory-root / decompose-spec text — artefacts of running a copy outside the agent-skills tree, not of the vendored files) |
| `adr-index.sh` dry run | `--check docs/adr` → temp file, exit 0, 178 rows for 178 ADR files; write mode on a temp copy of docs/adr → same bytes as `--check`; `docs/adr/README.md` not written (177 of its rows would change under the 0.5.0 parser, plus the new ADRs) |
| history mode | `check-build-memory.sh . --range HEAD~1..HEAD --no-hook` → vendored check-history.sh runs (exit 1: 53 R2 "act date more than 48 h before its commit" on the restored GATE DECISIONS rows of 4a921bb9); without `--no-hook` → memory_guard.py, exit 0 |
| run time on the worktree | vendored 26 s, old fork 161 s (upstream batches the per-file hashing and size scan) |

**Attribution.** The one violation is the ADR index: ADR-146…189 from SEED-11a–d (committed 375a8728…850805aa, some still
uncommitted) are not yet in `docs/adr/README.md` — by plan, the orchestrator regenerates it at the end. Both scripts report
it; neither reports it at 4685a0cb. The one pytest failure, `test_build_memory_audit.py::test_real_tree_expected_conflicts_and_zero_errors`,
is `audit_current_state.py` (which never calls `scripts/docs/`): 88 errors, all ADR-146…189 — 34 `adr/index-mismatch`,
34 `adr/spec-appendix-mismatch`, 20 `adr/dangling-reference`; same cause. Warnings 1 → 74: all from 0.5.0's new checks
(none is a violation without the guards marker). Against the 4685a0cb export the extra live warnings are: 4 `living-pin?`
(need git; the export had none), the BM-ADR-04 appendix warning, and "the last region is '## DATE CORRECTIONS — LEDGER,
Rounds 1–10 (…SEED-07)', not a PHASE LOG heading" (SEED-07). The count moved 74 → 73 at 02bf5d56 as living-pin test files changed.

## For SEED-02b (CI wiring — Makefile and ci.yml not edited here)

1. Pull requests: `bash scripts/docs/check-build-memory.sh . --range ${{ github.event.pull_request.base.sha }}...${{ github.event.pull_request.head.sha }} --json docs/build/logs/build-memory-history.json`
   (`...` judges from the merge base; `..` also accepted). The docs job already has `fetch-depth: 0`; a shallow clone exits 5.
2. Pushes to main: `bash scripts/docs/check-build-memory.sh . --first-parent ${{ github.sha }}` — today the docs job has
   `if: github.event_name == 'pull_request'`, so it needs a push trigger or a separate job (fetch-depth 0).
3. History mode hands off to `python3 docs/build/tools/memory_guard.py all …` (exit codes 0/1/2/3/5 per T0c); the docs job has
   no uv — confirm memory_guard.py runs on the runner's system python3 with the stdlib only, or add a Python setup step.
4. Exit 3 (vacuous) and 5 (unknown) are non-zero and must stay red; do not `|| true` them.
5. Optional: a `make docs-check-history` target (`--staged` locally, `--range` at boundaries) mirroring CI; keep the tree-mode
   step named for GL-CI-01 (`test_ci_workflows.py` looks for `check-build-memory.sh` in the docs job).

## Open issues for the orchestrator / other units

1. Regenerate `docs/adr/README.md` with `bash scripts/docs/adr-index.sh docs/adr` after the last SEED-11 ADR lands (clears the
   validator violation and the 34 `adr/index-mismatch` audit errors); the spec Appendix F build clears BM-ADR-04 and the 34
   `adr/spec-appendix-mismatch` errors. The 20 `adr/dangling-reference` errors need the referenced ADRs to exist.
2. Under the guards marker (T5), SEED-07's trailing `## DATE CORRECTIONS …` section fails BM-LEDGER-06 (the last `## ` heading
   must be a PHASE LOG heading) — the T5 LEDGER restructure should place it before the final PHASE LOG region.
3. Stale prose outside this unit: `check_backlog.py` L119/L131 (status-parsing description) and `CLOSEOUT_WRITER_PROTOCOL.md`
   §contract/patch/3 (describes the retired fork; its item 4 "detection logic … unchanged" is no longer true).
4. Suggested regression tests (`tests/unit/test_check_build_memory_report.py`, not edited here): L3 — a violation with empty
   file/obligation lands its text in `message`; L2 — an unwritable `--json` path exits 2.
5. Upstream candidates for agent-skills (not edited): L1, L2, L3, and the same tab-IFS defect in `check-history.sh` `diags()`.
6. T0c recorded "both SIG trees: 0 violations, 73 warnings" for 0.5.0; this worktree's planning-head export gives 0 / 69 (the
   tree, not the script: the vendored copy and the skill copy agree finding-for-finding).
