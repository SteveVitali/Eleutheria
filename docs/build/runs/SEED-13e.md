# Run ledger — SEED-13e (Stage B, T3 close-out): requirement → ticket index, fresh-context Phase-4 sizing review of 11A, contract patches

- Harness: claude-code/claude-opus-5-5/subagent
- Skills: 8aeb6dc
- Started: 2026-10-01T16:16:20Z (this unit's first `date -u`, after its read-only orientation)
- Closed: 2026-10-01T16:36:31Z
- Unit: SEED-13e — plan Appendix A T3 last bullet ("Requirement → ticket index; a fresh-context decompose-spec Phase-4 sizing
  review of 11A against the 256k window") plus the T3 contract patches the CARRY list routes here. Fresh context: this unit
  wrote none of the 60 11A contracts (SEED-13b/c/d did). Concurrent unit SEED-14b (BACKLOG / COVERAGE / risk register; it
  committed `4b5c5398` during this run) — none of its files touched.
- Worktree / branch: `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (no git state change made by this unit; HEAD at
  close `4b5c5398`). No network, no production, no sub-agents (AGENT_BRIEF rule 8).
- Read (targeted): `PD/stageB/AGENT_BRIEF.md`; `PD/stageB/CARRY.md`; `docs/build/runs/SEED-13a.md`…`SEED-13d.md`; plan §8.4,
  §8.5, §8.8, §13.5, Appendix A T3; `~/.claude/skills/decompose-spec/SKILL.md` (objective, Phases 3–4); the build-memory
  `layout.md` manifest section; the 60 11A contracts' Load / requirement / live-leg sections (whole files for P34.40, P34.8,
  PLAN-11B, P34.7's Load and deliverables); the 250 skeletons by script; spec §56 (`96c_…`) and Appendix G.7 (`99c_…`);
  ADR-171 § Decision; `PD/feedback/RATIFICATION_LOG.md` rounds 15–16 (B-32, B-37); `PD/data/decision_catalog.csv` (I7-S8,
  I7-TR1/2); `PD/data/acquisition_plan.csv` (AP-T2-093/201/210); `docs/build/reports/later-register/LATER_REGISTER.md`;
  `docs/tickets/DEFERRALS.md` (SEED-14a sections); `docs/build/reports/memory-repair/date_corrections.csv` (recs 277–279);
  `docs/build/tools/memory_guard.py` (manifest/contract judges) and `scripts/docs/check-build-memory.sh` (companions).

## What this unit did

| file | change |
|---|---|
| `docs/tickets/REQUIREMENT_INDEX_R11.md` | **new**, generated — every requirement id cited by the 310 Round-11 contracts (162 ids: 61 of the 62 §56 ids + 101 earlier ids) → owner / delivering / also / citing rows; §1 the 62 §56 ids against their `Owner:` lines (0 unresolved owners; 4 seed-owned ids flagged — SIG-ENG-041 SEED-15, SIG-ENG-044/SIG-MEM-005/SIG-MEM-012 SEED-02; SEED-12a's four agent-assigned owners flagged as confirmed at T3, agent reading); §2 every waived (G.7.2, 16 ids), amended (G.7.3, 29 ids incl. the ADR-171 outreach set) and checked-not-amended (G.7.5, 18 ids) id with its ADR or authority; §3 the full index. Location: no earlier index existed in `docs/tickets/`; the build-memory layout puts a `## Requirement-ID → ticket index` in the manifest, so the file is a listed companion and the manifest section points to it. |
| `docs/build/planning/2026-09-30-next-phase/reviews/T3-sizing-review.md` | **new** — the fresh-context Phase-4 review: method, findings F1–F10, per-row verdicts for all 60 rows (re-measured Load ÷3/÷4, Δ, DEFERRALS share vs allowance, modelled peak and headroom), fixes applied, proposals. Verdicts: 56 ok (P34.8 after its fix), 3 tight (P34.37, P34.38, PLAN-11B after re-seam), 1 split proposed (P34.7). |
| `docs/build/planning/2026-09-30-next-phase/tools/s13e/` | **new** (stdlib): `measure_11a.py` (re-measure + working-set model; read-only), `req_index.py` (`write`/`check`; imports SEED-13a's `s13/gen_t3.py` for spec ids, §56 owners and id expansion), `fix_load_totals.py` (re-derives a contract's self-entry, header and token line to a fixed point; verified idempotent on untouched contracts 201 and 258). |
| `docs/tickets/249_P34.40__serving-topology-dark.md` | **orchestrator decision (conservative) applied:** the `/v1/*` LB step (NEG + backend + URL-map rule) is a public-surface change, not covered by S5-3 "dark LB/nginx" → its own in-ticket go (L2); only the `sig-web` nginx roll (L1) runs pre-authorised; Gate status, OM-20 status, live stage, window, production mutations, ACs, OM-14/19/20 lines and notes updated; mentioned for the GATE-B packet. Load 186,464 → 188,694 B. |
| `docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md` | deliverable 8: (a) the **outreach-owed list for GATE-ANNOUNCE** (SIG-CHART-033, SIG-INGEST-029, SIG-INGEST-030a, SIG-CONTRIB-012 + ADR-171's rest; amended not waived; P36.77 leaves them unmet), (b) the **tribal candidate group** (B-32 "Include S8 screened lane", 2026-10-01T04:43:37Z; B-37 "Capture IU; TR facts+cite (Recommended)", 04:46:04Z; AP-T2-201/210 IND-TRIBAL placed by PLAN-11B; `doj_ctas_awards` AP-T2-093 is IND-P8/RB-05, not covered by I7-S8 — agent reading), (c) `D-R11-OSMUID-1` placement, (d) P34.40's `/v1/*` seam for P35.53/P35.59; contexts re-seamed from 8 (~12-row batches) to **13 contexts of ≤ 8 rows** (review F9); ADR-171 § Decision and the C2/C5/C13-only rows added to Load; AC for deliverable 8; requirement-index deliverable points to the generator. Load 311,556 → 291,176 B (upper bound). |
| `docs/tickets/210_P34.8__obligation-events-repair.md` | per the orchestrator's mid-run change: deliverable 8 records that the **26 SEED-14a anchors and the verdict/letter-suffixed-id parsing fix are SEED-15's (applied in the seed)** — not added as P34.8 work; stop-and-ask if `check` still reports them at dispatch. MIGRATION.md L55–57 correction kept, now with the true dates from `date_corrections.csv` recs 277–279 (P32.4 2026-09-27T06:41Z, P32.2 04:16Z, P32.5 07:17Z — re-verify at ticket time). Load: `coverage_assessments.jsonl` narrowed to its four lines (it had grown to ≈ 130 KB), `pending_transitions.csv` re-measured 154 → 2,674 B. Load 226,163 → 229,188 B. |
| `docs/tickets/209_P34.7__append-only-checker-full-modes.md` | Load trimmed (test file → lines 1–305 + test index; register → header, five samples, class counts) and a sizing note proposing the P34.7a/b seam. Load 358,037 → 286,069 B. |
| `docs/tickets/202_P34.2__recorded-ci-verifier-and-flake-policy.md` | self-containment fix: `tests/api/test_curation_onboarding_timing.py` (deliverable 5) added to Load. Load 230,463 → 233,299 B. |
| `docs/tickets/00_MANIFEST.md` | `companions:` line made parseable (it was wrapped in backticks, so the validator never read it) and `REQUIREMENT_INDEX_R11.md` added; new `## Requirement-ID → ticket index` section (layout position, before `## Spec amendments applied`) pointing to the companion; **one appended `## Plan extensions` line** recording the leg-level `live:` edges (P34.45 → P34.46; P34.43 L2 → P34.46; P34.21b L2 → P34.21a + P34.18), their feasibility before GATE-G4 and the fallback; an appended `### Round 11 — T3 close-out` block at the end of `## Decomposition decisions` (the Phase-4 review record, the layout's home for it). Nothing removed. |
| `docs/build/runs/SEED-13e.md` | this ledger. |

### Feasibility of SEED-13d's `live:P34.46` edges before GATE-G4 (CARRY)

Feasible, with no slack: P34.46 L2 opens ≥ 2026-10-14T14:00Z (Wed) on its own in-ticket go; P34.43 L2 (`sig_recovery`
login) and P34.45's ER re-run follow in the 14:00–20:00Z weekday slots inside the plan's GATE-G4 estimate (≈ 10-15 → 10-17,
plan §8.8). P34.47 cannot pass while a leg is due (a held go included), so a slip of P34.46 moves GATE-G4 rather than
voiding the S5-3 pre-authorisations; if GATE-G4 is held with a leg unrun, the leg goes on the 11B OM-20 list or gets its own
go. Both contracts already state that fallback (P34.43 § Live stage + OM-20 line; P34.45 § Live stage expiry bullet), so they
were not edited; the edges and this reading are recorded in the manifest's Plan extensions line. P34.21b's leg-level
dependency on P34.18 + P34.21a is satisfied by row order (221 < 223 < 224) and recorded in the same line.

## Checks run

| check | result |
|---|---|
| `python3 PD/tools/s4c/check_order.py` | **0 errors** (310 chain rows; gates 260/343/420/504/510) |
| `python3 PD/tools/s13/gen_t3.py check` | **0 errors** — "310 Round-11 manifest rows, 310 plan rows, errors 0" (the index file does not match the Round-11 contract glob, so it is not a stray file) |
| `bash scripts/docs/check-build-memory.sh .` | **exit 0 — no violations, 44 warnings** (the same 44 pre-existing legacy warnings). One intermediate run failed with `filename: ticket file REQUIREMENT_INDEX_R11.md does not match the filename grammar` because the manifest's `companions:` line was wrapped in backticks and so never parsed; fixed by making the line plain. |
| `python3 docs/build/tools/memory_guard.py all --worktree` | **exit 0 — no violations, 0 warnings** (1,572 items evaluated at the last run, over this unit's and the worktree's uncommitted changes) |
| `python3 PD/tools/s13e/req_index.py check` | **current** (regenerated after SEED-14b's commit, since §3 reads the coverage matrix at HEAD) |
| `python3 PD/tools/s13e/measure_11a.py` | all 60 header totals equal their entries; every self-entry equals its file size; flags only the expected partial entries |
| `python3 PD/tools/s13e/fix_load_totals.py` on copies of 201 and 258 | byte-identical (idempotent); applied to the five edited contracts |
| `uv run ruff check PD/tools/s13e/` (informational; `docs/` is excluded from the repo's lint scope) | 95 E501 line-length + 8 B023/B905 false positives (lambdas consumed inside the same `re.sub` call); the sibling `s13/` reports 119 of the same kinds |
| `python3 docs/build/tools/obligation_events.py check` (read-only, for P34.8) | 26 `events/missing-anchor` (the SEED-14a rows) + 46 `coverage/malformed` (verdict words such as `WAIVED(ADR-…)`, `MET-ENGINEERED(…)`, `AT-RISK-INTEGRATION` and the letter-suffixed id `SIG-PUB-014b`) — the orchestrator routed both to SEED-15 |

## Open issues for the orchestrator / other units

1. **P34.7 split (proposed, not added):** P34.7a (deliverables 1, 2, 6, 7) · P34.7b (3, 4, 5), by `mode=extend` at dispatch (≈ +0.5 run); unsplit it runs trimmed as a tight row (review F10).
2. **GATE-B packet:** mention P34.40's `/v1/*` LB step as an in-ticket go (orchestrator decision) and offer the operator the choice of covering it there; the P34.6 "drill clone" question (SEED-13b) stays open.
3. **SEED-17 (OPERATING MODE):** count the fixed skill text (implement-spec + self-review ≈ 17.5k tokens ÷3) and Devin's own prompt in every dispatch-time count; adopt the copy-batch file convention and the "next free ADR ≥ 191" rule (CARRY); a context nearing ~200k stops at a seam. Optional: run PLAN-11B/11C/11D contexts through `decompose-spec` directly (review F9).
4. **SEED-15:** the 26 anchors and the `obligation_events.py` verdict-list / letter-suffixed-id fix are now its items (P34.8 deliverable 8 says so).
5. **PLAN-11B/11C/11D:** re-run `PD/tools/s13e/req_index.py write` (then `check`) after writing contracts; never load a living register whole (review F4).
6. **T6:** re-measure the estimate entries at dispatch (files earlier rows write; ADR-151; `ADR_TRIGGERS.csv`).
7. **CARRY.md** is the orchestrator's file and was not edited; the SEED-13e items in it are all addressed above (the SEED-14a anchor item re-routed to SEED-15 by the orchestrator).
