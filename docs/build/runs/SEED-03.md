# Run ledger — SEED-03 (Stage B, T2 — living-record pin conversions, PKG-02): tests over living build memory assert invariants, not current values

- Harness: claude-code/claude-opus-5-5/subagent
- Skills: 8aeb6dc
- Started: 2026-10-01T08:09:13Z
- Closed: 2026-10-01T08:22:21Z
- Unit: SEED-03 — plan Appendix A T2 "SEED-03 the six living-record pin conversions (PKG-02)"; F5 §3 + `data/eng_debt.csv`
  ED-07…ED-12 (the six PKG-02 conversions) ∪ T0c's four `living-pin?` files (`stageB/T0c_sync_obligations.md`), de-duplicated
  → 9 test files + the one production function ED-09's fix shape names (`check_pilot`).
- Worktree / branch: `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (no git state change made by this unit).
- Brief: `docs/build/planning/2026-09-30-next-phase/stageB/AGENT_BRIEF.md`; sources read: F5 §3/§4 PKG-02, `data/eng_debt.csv`
  ED-07…ED-13, B4 §4 G6 (inventory + why #165/#179/#185 went red), B3 §3.2/§3.4 (seed CURRENT STATE), T0c (key list, guards
  marker), the build-memory layout BM-LEDGER-02/-08, BM-COMPAT-06, BM-TEST-01.
- Records: **no** edit to LEDGER, BUILD_INDEX, DEFERRALS, the manifest, the coverage matrix, events.jsonl or any record.

## Union list (de-duplicated)

| source | file | living state pinned (before) |
|---|---|---|
| ED-08 + T0c `:85` | `tests/unit/test_agent_docs_current_state.py` | `lastCompleted: P33.8` / `nextTicket: HUMAN-H4` / `projectStatus: IN-PROGRESS` (off-enum, F-23); SIG-MEM-004 `== "MET"`; README `rows 1-200`; `>=22.12.0` literal |
| ED-07 | `tests/unit/test_capstone_closure_round10.py` | `== 18` P33.3 annotations all OPEN/PARTIAL; every *current* OPEN row in the frozen §(f5); P32*/P33*-owned matrix rows `==` PLAN ids; `split('## GATE DECISIONS')[-1]` (vacuous: the rest of the file) |
| ED-10 + T0c `:37` | `tests/unit/test_build_memory_audit.py` | real-tree status-conflict set `== {"D-P21.5-1"}`; 7 named rows stay OPEN/PARTIAL; fixture `IN-PROGRESS` |
| ED-09 | `tests/tasks/test_acquisition_pilot.py` + `tasks/src/tasks/acquisition_pilot.py` `check_pilot` | the real DEFERRALS must carry D-P32.18/19/20/21-1 OPEN forever (production `sig-tasks acquisition pilot-check` too) |
| ED-11 | `tests/unit/test_repo_docs_current_state.py` | README contains `D-R10-PUBLISH-1`, `operational=false`, `staging`; governance "Ten documents" |
| ED-11 | `tests/unit/test_round10_integration_plan.py` | prior plan contains the literal "Superseded for the current stack" + the P33.6 path |
| ED-12 | `tests/unit/test_source_registry.py` | the exact 236-id permitted set (`_FLIPPED_SUBSET`; comment said 77) |
| T0c `:66` | `tests/unit/test_closeout_protocol.py` | none — tmp_path fixtures only (F5 §3 false positive); fixture used off-enum `IN-PROGRESS` |
| T0c `:34` | `tests/unit/test_current_projection.py` | none — tmp_path fixtures only (F5 §3 false positive); fixture used off-enum `IN-PROGRESS` |

## What this unit did

| file | before → after (intent kept; the invariant that still catches the regression) |
|---|---|
| `test_agent_docs_current_state.py` | **deleted** `test_ledger_closed_the_manifest_honestly` from this P33.8 file — F5/B4 both say delete; its intent (the closeout left an honest cursor) moved to `test_build_memory_audit.py::test_real_tree_ledger_cursor_is_honest` (below), which checks it as invariants at every commit. SIG-MEM-004 → `test_coverage_matrix_sig_mem_004_row_is_well_formed`: exactly one row, verdict ∈ `check_coverage_matrix.VERDICTS` (the checker's own vocabulary, so a T4 re-verdict tracks the checker), an owner, MET-family ⇒ every evidence path exists, gap verdicts ⇒ routed. README range → `test_build_readme_index_range_matches_the_index`: the stated `rows 1-N` equals BUILD_INDEX's highest landed seq and the `as of <ticket>` equals that row's ticket. Node floor → every backticked `>=x.y.z` in `web/AGENTS.md` equals `web/package.json` `engines.node`. Kept the history check (row 200 = P33.8 + its runs/pr files; append-only). |
| `test_capstone_closure_round10.py` | Frozen snapshot of the register at the packet commit `e8bc0179` (36 owed ids, 18 annotated ids — the counts §(f5) itself states), with a provenance test that recomputes both from `git show e8bc0179:docs/tickets/DEFERRALS.md` (skips in a shallow clone). §(f5) must name every id owed **at the packet commit** and none of them may be deleted from DEFERRALS. Annotated rows: each still exists and either leads OPEN/PARTIAL, or leads a terminal status with a dated token **and** an obligation-event chain head that is a `transition` to that status citing an existing ref outside `docs/tickets/`. Plan ids: PLAN.json (frozen, `== 38` kept and labelled) ⊆ matrix with an owner; a P32*/P33* owner owns only PLAN ids. Gate test: reads the `## GATE DECISIONS` section body only and fails if the section is missing (the old split was vacuous). |
| `test_build_memory_audit.py` | Real tree: `test_real_tree_zero_errors_and_every_status_conflict_documented` (zero errors kept; the set-equality pin replaced by "every `deferrals/status-conflict` is reconciled by an events.jsonl migration anchor or listed in `reconciliations.json`" — the allowlist F5 asks for already exists in the records; detection of the documented manifest/ticket conflicts kept as the parser-regression guard). `test_real_tree_ledger_cursor_is_honest` (new; replaces the P33.8 literal test): no `ledger/*` finding of any severity, `projectStatus DONE ⇒ nextTicket DONE`, and under the guards marker (BM-COMPAT-06) `projectStatus` ∈ `NOT_STARTED|IN_PROGRESS|BLOCKED|PAUSED|DONE`. `test_parsing_preserves_each_rows_own_leading_status` (replaces the 7 named rows): every obligation row parsed, parsed status == the row's own leading token (no last-token-wins). Fixtures: `IN-PROGRESS` → `IN_PROGRESS`; new Round-11 seed-shape fixture (values only, `harness` slot, PAUSED, pointer comment, per-round PHASE LOG) with 3 passing tests and 1 **strict xfail** (see open issue 1). |
| `test_closeout_protocol.py` | Fixture `IN-PROGRESS` → `IN_PROGRESS`; `lstate` threaded through `_repo`/`_closeout_commit`/`_full_closeout`; new `test_full_closeout_on_the_round11_values_only_ledger` (the protocol reads the seed shape; acknowledges once). |
| `test_current_projection.py` | Fixture `IN-PROGRESS` → `IN_PROGRESS`; new `test_round11_values_only_control_state_projects` (control reads PAUSED / round 11 / harness, CURRENT.md line) + 1 **strict xfail** `…generates_and_verifies_clean` (open issue 1). |
| `test_repo_docs_current_state.py` | Honest bounds derived from records: while `D-R10-PUBLISH-1` leads OPEN/PARTIAL the README names it and "staging" (moved here from the deployed-surface test); `ops/config.toml [intake].operational` false ⇒ README says not operating, true ⇒ README may not say `operational=false`. Governance: the spelled count equals the `docs/governance/*.md` documents and every one is linked. All "must not contain" guards unchanged. |
| `test_round10_integration_plan.py` | Prior-plan test → the head blockquote still says "Superseded" and every INTEGRATION_PLAN link in it resolves (a later round may re-point it). The 8 tests over the dated P33.6 report are kept (frozen artifact; docstring says so). |
| `test_source_registry.py` | HG-03 tripwire as an invariant: every permitted source has `rights_reviewed_by` + `rights_reviewed_on`, a `FLIPPED … <date>` note citing a gate id or ADR, every cited ADR has a file, every cited gate id appears in the LEDGER `## GATE DECISIONS` section, and a named `review_packet` exists. Stale 25-line flip-history comment replaced (the history is in each row's notes). Holds today for all 236 permitted rows. |
| `tasks/src/tasks/acquisition_pilot.py` (**production**, ED-09 fix shape) | `check_pilot` decides on the row's **leading** status: OPEN/PARTIAL = owed home; DONE/WONTFIX/ACCEPTED-SKELETON passes only when the latest obligation-event `transition` for that id has that `to_status` and cites an existing ref outside `docs/tickets/`; anything else is refused. New read-only helper `_evidenced_closures`. This also closes a hole: the old substring test accepted any closed cell that still contained the word OPEN (T0c's flip form `DONE <date> (evidence) — was: OPEN …`, or the P33.3 "stays OPEN" annotation). |
| `tests/tasks/test_acquisition_pilot.py` | New tmp_path test for all states: PARTIAL accepted; cell-only closure refused (even with "was: OPEN"); register-only evidence refused; missing evidence refused; transition to a different status refused; evidence-backed transition accepted. |

## Checks run

| check | result |
|---|---|
| `uv run pytest <file> -q` per converted file, live worktree (08:20:41Z) | agent_docs 6 passed · capstone 8 passed · **audit 22 passed, 2 failed, 1 xfailed** · closeout 28 passed · projection 17 passed, 1 xfailed · repo_docs 8 passed · integration_plan 9 passed · source_registry 71 passed · acquisition_pilot 42 passed |
| the 2 audit failures | `test_real_tree_zero_errors_and_every_status_conflict_documented` and `test_real_tree_ledger_cursor_is_honest` — **not test pins**: the live tree now carries the seed LEDGER written by another unit during this run (its `updatedAt` reads 2026-10-01T08:14:19Z) and the audit reports `ledger/key-order` (no `harness` slot in the tool, open issue 1), `ledger/next-ticket P34.1` (no manifest row yet — the LEDGER comment says T3 writes it, open issue 2) and 88 `adr/*` errors from the concurrent ADR work (open issue 3). With those three simulated away, both pass (backtest (a)). |
| `uv run pytest tests/unit tests/tasks -q` (live) | 1889 passed, 3 failed, 2 xfailed — the 2 above + `test_backlog_housekeeping.py::test_check_backlog_exits_zero` (`check_backlog.py`: "unmapped ADR: ADR-146 … ADR-189" — concurrent ADR work, not a file of this unit) |
| `uv run ruff check` + `uv run ruff format --check` on the 10 touched `.py` files | All checks passed; 10 files already formatted |
| `uv run mypy -p tasks` (the `make typecheck` scope for the touched package; tests are outside MYPY_TARGETS) | Success: no issues found in 27 source files |
| `living-pin?` heuristic (`~/.claude/skills/build-memory/scripts/check-build-memory.sh .`, 0.5.0) | 4 → **3** warnings: `test_agent_docs_current_state.py` cleared; the 3 left (`test_build_memory_audit.py:44`, `test_closeout_protocol.py:66`, `test_current_projection.py:35`) name keys only in tmp_path fixtures (and, for the audit file, invariant-only real-tree reads) — reviewed false positives of the name-based heuristic; P34.31's AST lint replaces it. The run's 1 violation is `docs/adr/README.md does not match a fresh adr-index regeneration` (concurrent ADR work). |
| **Backtest** (scratch copy of the live worktree; nothing written to the worktree): (a) seed shape with the two out-of-unit fixes simulated (audit `harness` slot; a P34.1/P34.2 manifest row) and the real-tree ADR domain excluded | converted suite green except the 2 strict xfails, which flip to XPASS(strict) — i.e. they fail exactly when the audit fix lands, as intended |
| backtest (b): 12 legitimate Round-11 record changes — M1 close D-P32.10a-1, M2 new OPEN deferral, M3 a full closeout (LEDGER advance, BUILD_INDEX `## Round 11` row 201, README `rows 1-201 as of P34.1`, PHASE LOG done), M4 close D-P32.21-1, M5 SIG-MEM-004 → MET-ENGINEERED with the checker's vocabulary extended, M6 close D-R10-LIVE-1, M7 `IN_PROGRESS` under the guards marker, M8 activation (D-R10-PUBLISH-1 closed, intake operational, README updated), M9 an 11th governance document, M10 prior plan re-pointed, M11 a Round-11 source flip with its decision recorded, M12 guards marker on | converted tests: **12/12 green**. The original tests on the same scenarios: red in **10/12** (and red on the seed shape itself via `test_ledger_closed_the_manifest_honestly`); the original `check_pilot` stayed green on M4 only because the closed cell still contained "OPEN" |
| backtest (c): 16 real regressions — §(f5) drops a packet-time id; annotated row closed in the cell only; same for the pilot check; closeout without the README range; flip with no decision; nextTicket on a landed row; DONE while a row is next; `IN-PROGRESS` under the marker; unindexed governance doc; GATE DECISIONS section gone; off-vocabulary SIG-MEM-004; engines.node moved; an undocumented status conflict; a registered row deleted; README says intake live while the gate is off; SIG-MEM-004 row dropped; closure with register-only evidence | **all 16 caught** (17 checks — the cell-only closure is caught by both the capstone and the pilot test) |

## Open issues for the orchestrator / other units

1. **`docs/build/tools/audit_current_state.py` `EXPECTED_KEYS` has no slot for the optional `harness` key** (layout
   BM-LEDGER-02; skill 0.5.0; the seed LEDGER has it). Not a file of this unit — owner: SEED-02 (validator sync) or the
   orchestrator. Until fixed: `ledger/key-order` makes both real-tree audit tests red and `current_projection.py
   generate`/`verify` report INCOMPLETE on the seed LEDGER (orient read O4 of the OPERATING MODE). Fix shape: accept
   `got == EXPECTED_KEYS` or `EXPECTED_KEYS` with `harness` inserted before `updatedAt`. Two **strict xfails** record it —
   `test_build_memory_audit.py::test_round11_harness_slot_passes_key_order` and
   `test_current_projection.py::test_round11_values_only_ledger_generates_and_verifies_clean`; they turn red (XPASS strict)
   when the fix lands — **remove both markers in the fix commit**. `test_round11_harness_out_of_its_slot_is_a_key_order_error`
   guards that the fix stays slot-only.
2. **`nextTicket: P34.1` needs its manifest chain row** (T3 / SEED-13); until then `ledger/next-ticket` is an error.
3. **ADR-domain audit errors** (88 on the live tree): the ADR index is not yet regenerated, the spec is not yet rebuilt
   (Appendix F), and SEED-11's ADRs cite ticket-authored numbers that have no file (ADR-156, 160, 161, 174–177) →
   `adr/dangling-reference` stays an **error** after regeneration unless those citations are worded as reserved or the
   audit learns reserved numbers. Also turns `test_check_backlog_exits_zero` red (unmapped ADR-146…189 in the backlog).
4. **Every Round-11 closeout must keep `docs/build/README.md` "rows 1-N as of <ticket>" in step with BUILD_INDEX** — now a
   derived invariant, so it belongs in the closeout checklist / OPERATING MODE (SEED-17).
5. A coverage re-verdict to a new vocabulary word (e.g. MET-ENGINEERED, ADR-150) must extend
   `check_coverage_matrix.VERDICTS` in the same change (T4 / SEED-14).
6. Round-11 source flips (Stream I) must write `rights_reviewed_by`/`_on` and a `FLIPPED <date> (<gate id or ADR>)` note,
   with the gate id present in LEDGER GATE DECISIONS — the converted HG-03 tripwire checks exactly that.
7. Closing D-P32.18/19/20/21-1 (or any P33.3-annotated row) needs an obligation-event `transition` with evidence outside
   `docs/tickets/` (P34.8 / the return-pass ticket), or `sig-tasks acquisition pilot-check` and the capstone test refuse it.
8. Not done here (other rows own them): ED-13's lint + `tests/AGENTS.md` convention note (P34.31); B4's suggestion to move
   the remaining P33.7 "must contain" README/CHANGELOG checks into the docs-freshness detector; validator-side pins
   (`check_coverage_matrix.py` `EXPECTED_ROWS = 715`, `check_spec_src.py` id lists — B4 NEW-7, T1/T4).
