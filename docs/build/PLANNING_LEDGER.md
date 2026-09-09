> Committed copy; the live machine build ledger stays gitignored at `.agents/scratch/planning/sig-postbuild-build-ledger.md`.

# SIG — post-build planning ledger v2 (the plan for the plan)

- **Created:** 2026-09-08 after P18.2 (ticket 46/46, PR #46). **Revised v2** the same day after operator
  corrections (remote state, scratch unification, tickets-in-git, spec_src explanation, "added tickets",
  retro live verification, capstone, ticket-digest goal).
- **Purpose:** durable, compaction-proof plan for how we produce the forward design / implementation /
  operationalization plan — and, per the operator's stated goal, how that plan becomes **`docs/tickets/`
  entries appended to the ordered ticket backlog**, so the exact specs that led to the implemented system
  stay legible. Every later session reads this first, executes one bounded phase, appends to §9, updates §10.
- **Branching rule (operator):** all future work branches from the **tip of `devin/p18-2-france-belgium`**
  (PR #46), continuing the stacked chain. Do not branch from `main`.

---

## 1. Operator prompt → TODO ledger (every requirement and investigation, tracked)

Status: ☐ open · ◐ investigated, action pending · ☑ done · ✗ dropped (with reason)

| # | Requirement / question (from the two prompts) | Investigation done | Action / where it lands | Status |
|---|---|---|---|---|
| T1 | Verify the 46-ticket chain is complete; correct my stale "main has 1 commit" | `git fetch`: origin/main = 45 commits; PRs #1–#19 (P00.1–P07.3) **merged**; **27 open** (P08.1–P18.2) stacked; HEAD +28 over origin/main. **Phase A (9.A):** per-ticket index done — `planning/BUILD_INDEX.md` (46 rows, no unknown cells); local `main` = `a33177c`, **44 behind** origin/main | Index recorded; fast-forward of local `main` stays in P19.1 | ☑ verified / ◐ housekeeping → **ticket P19.1 written** |
| T2 | Future work branches off the P18.2 tip | — | Rule recorded above; every new ticket's `base_branch` = current checkout (manifest convention holds) | ☑ |
| T3 | Unify `.agents/scratch/` and `scratch/`; reorganize the final scratch dir | Both gitignored (`scratch/` pattern matches any depth; `.devinignore` re-includes `.agents/scratch/`). `scratch/` holds 2 early ledgers + 6 one-off scripts + `p052_live/`; `.agents/scratch/` holds ~44 ledgers, PR bodies, commit msgs, ~4.5 MB of check logs | **Decision (judgment):** single root `.agents/scratch/` (matches implement-spec's default + `.devinignore`), layout in §4.1; move `scratch/*` in; delete the large `*check*.log` files (reproducible by `make check`); keep `.gitignore` `scratch/` pattern (harmless), remove nothing else. Executed as part of ticket **P19.1** | ◐ → **ticket P19.1 written (§4.7 move included)** |
| T4 | Add `docs/tickets/` to git? | Gitignored by design ("derived; regenerate, don't commit"), but it is **not regenerable** (no decompose ledger/inputs on disk) and it is the only record of each PR's contract | **Operator confirmed 2026-09-08: yes** — remove `docs/tickets/` from `.gitignore`, commit the 46 contracts + manifest + template + all future tickets (in PRs), amend the manifest's "gitignored" paragraph. In **P19.1** | ☑ decided / ◐ executed → **ticket P19.1 written** |
| T5 | Rework structured backlogs so operationalization lives in one clear place | Sources: risk register (272 `RISK-P*` rows, per-phase "Deferred / out of scope" tables), 58 ADRs (Deviations / Revisit trigger), ledger gap tables, `CHECKLIST_ITEMS→None`, manifest "Human prerequisites" | **Decision (judgment):** do NOT rewrite the spec-mandated §53 risk register; instead create committed `docs/backlog/` with (a) `BACKLOG.md` (normalized ids, one row per item, cross-ref'd back to RISK/ADR ids) and (b) `OPERATIONAL_READINESS.md` (capability → readiness map + human prerequisites). Risk register rows gain a backlog-id cross-ref only. Phases C + F produce them; **P20.1** commits them | ◐ → **ticket P20.1 written** (home = `docs/build/`, §4.7) |
| T6 | Explain `spec_src` and how to amend the spec | `docs/research/_meta/spec_src/` = 37 ordered section files (`00_front_part0.md` … `99c_appG_corrections.md`); `BUILD.sh` concatenates them into `docs/2_canonical_design_spec.md`. **Verified byte-identical reproduction today.** Amend = edit section file → `sh docs/research/_meta/spec_src/BUILD.sh` → ADR (SIG-ENG-003) → Appendix F/G entry. Precedent: manifest "Spec amendments applied" (§33.2 34-vs-32 fix) | Explained in §2.3; Phase D plans the amendments; **P20.2** executes | ☑ (explained) / ◐ → **ticket P20.2 written** (A1–A8 gate block, HG-13) |
| T7 | "We added several tickets (…lettered sub-tickets) not in the spec/spec_src — sort this out" | All 48 files in `docs/tickets/` have mtime **Aug 26 21:52** (decomposition time); **no lettered files exist anywhere**; spec Part X defines **19 phases**, manifest has **46 `PXX.Y` sub-tickets** from the start. Conclusion: nothing was added mid-build; the "additions" are sub-ticket scopes that exceed the spec's per-phase text (e.g. P00.4 source-registry, P06.1 hard gate, P08.3 contradiction object, P10.2 catalog, P15.x splits), created at decomposition | **Operator confirmed 2026-09-08: no such tickets exist (recollection was from another project).** Phase D item D.1 still tags each ticket deliverable `in-spec` / `spec-implied` / `ticket-added` (decomposition-time scope beyond the spec text), because those remain the fold-back candidates for P20.2 | ☑ resolved; tagging → **P20.2** (`TICKET_VS_SPEC.md`) |
| T8 | Retroactively perform "live" agentic verification (implement-spec 5.3) where it was skipped | **Phase A audit done (9.A):** 15 run / 18 fixture-only / 3 not-applicable / 10 not-recorded (`BUILD_INDEX.md` §A.3); the P06.1 hard gate itself was fixture-only; API served only over an in-memory ReadStore; reconcile/inference/tasks never persisted; web rendered from fixtures. Runtime surfaces: PG18+PostGIS (testcontainers), OCFL + Playwright, CLIs, DuckDB, uvicorn API, Astro `web/`. Real-source fetch is **legally gated** — "live" = local stack over fixtures, never real crawling (except P07.3's USAspending trace, public-domain) | `LEDGER_DEFERRALS.md` §1 (LD-V01..12) is the P19.3 worklist; blockers recorded honestly (never fabricate green). **P19.3** | ◐ audited → **ticket P19.3 written** (LD-V11 already closed by CI, §9.B′) |
| T9 | Canonical-spec-wide final gap analysis + verification, like orchestrate-build's CAPSTONE | Read `~/.claude/skills/orchestrate-build/SKILL.md` §3: (1) fresh-context whole-chain gap analysis vs the spec as a whole, classify MET / MET-DIFFERENTLY / PARTIAL / MISSING / AT-RISK-INTEGRATION, hunting cross-ticket seams; (2) close real gaps on a capstone branch; (3) **composed end-to-end verification** of the fully-wired path; (4) record blockers, await operator. **Never run for this build** | Adopt it verbatim as the spine of Phases B + E' + G': **P19.2** (capstone gap analysis, independent context), **P19.3** (composed E2E + retro live verification), **P19.4** (spine wiring) + **P19.5** (gap closure) | ◐ → **tickets written** |
| T10 | Digest the meta-plan into `docs/tickets/` entries appended to the ordered backlog | Ticket format = `_TEMPLATE.md`; manifest table is the order; decompose-spec produces contracts + manifest rows | §6 proposes the P19–P21 chain; Phase G finalizes it via `decompose-spec` with the planning artifacts as its "spec"; tickets are committed (T4) so the record is durable | ☑ **decomposition done 2026-09-08: 17 tickets P19.1–P21.9 + manifest rows 47–63 + build ledger** (committed by P19.1) |
| T11 | Fold ticket-added requirements back into the canonical spec (Direction 1) | Depends on T7's tagging | Phase D → **P20.2** | ◐ → **ticket P20.2 written** |
| T12 | Holistic review of history / codebase / risk register / scratch → forward plan (Direction 2) | — | Phases A–F → G decision memo | ☑ `planning/DECISION_MEMO.md` (2026-09-08) |
| T13 | If too big for one context, provide a fresh-context prompt | — | §8 prompts (generic + per-phase) | ☑ |
| T14 | "Come back with a revised meta-plan and a way forward" | — | This v2 + the reply | ☑ |
| T15 | (implicit) No `AGENTS.md` exists anywhere — agents onboard from README only | Confirmed | `agent-docs` skill in **P19.1** | ◐ → **ticket P19.1 written** |
| T16 | (implicit) Local `main` is stale; `tests/db` Docker path unverified this session | 9.A: local `main` 44 commits behind origin/main; `tests/db` last recorded green at P14.1 (ledger L51) and P16.1 (L7), never recorded for P17.x–P18.2 (LD-V11) | Housekeeping in P19.1; Docker DB tests first step of P19.3 | ◐ confirmed; **CI half closed** (tests/db runs in CI, §9.B′ item 4) → P19.1 / P19.3 tickets written |

---

## 2. Ground truth (verified 2026-09-08 v2)

**2.1 Build/PR state.** origin/main: 45 commits (spec + 19 merged ticket PRs). Open, stacked: 27 PRs (#20–#46, P08.1→P18.2), each based on the previous ticket's branch; tip = `devin/p18-2-france-belgium`. `make check` at tip: lint/format/mypy clean, 2363 tests, verify-gen byte-clean. `tests/db` skips without Docker (not run this session). 46 local branches.

**2.2 Durable memory.** `docs/tickets/` (46 + manifest + template; gitignored; not regenerable — no decompose ledger on disk; all created Aug 26). Ledgers: ~44 in `.agents/scratch/` (three naming styles) + 2 in `scratch/`. PR bodies / commit msgs / ~4.5 MB check logs in scratch. **No `AGENTS.md`.**

**2.3 The spec is assembled, not authored in place.** `docs/2_canonical_design_spec.md` (8,888 lines, 668 req ids) = `cat docs/research/_meta/spec_src/[0-9]*.md` via `BUILD.sh`; reproduction verified byte-identical. To amend: edit the section source (e.g. `96_partX_s51to54_plan.md` for Part X, `99a_appF_adr.md` for the ADR index, `99c_appG_corrections.md` for corrections) → run `BUILD.sh` → commit both → ADR per SIG-ENG-003. README "Regenerating the specification" documents this.

**2.4 Committed knowledge.** 58 ADRs; `docs/traceability.md` (1,945 lines, ticket-scoped union); `docs/risk_register.md` (1,198 lines, 272 RISK rows, per-phase deferred tables); research R1–R13 + `_meta/{OUTLINE_TRACE,GAP_ANALYSIS,LEAD_SPOTCHECKS}.md`; `docs/governance/`, `docs/slice/`, `docs/studies/`.

**2.5 Spec plan vs tickets.** Spec §52: 19 phases (0–18). Manifest: 46 sub-tickets, fixed since decomposition. One spec amendment already applied via spec_src (§33.2 task count).

---

## 3. Tensions (hypotheses to confirm)

3.1 **Integration:** 27 stacked PRs unmerged; merging bottom-up (or squashing) is a workstream; `ontology/generated` + `pylock.toml` are conflict magnets. Operator rule: keep building on the tip; integration is its own decision (Phase E).
3.2 **Memory:** the contracts and ledgers are uncommitted and not regenerable → T3/T4 fix this first.
3.3 **Four overlapping backlogs** → one normalized `docs/backlog/` (T5).
3.4 **"Shape + gate, not live"** everywhere → operationalization is the thin layer; the capstone's composed E2E will surface exactly which composed paths never ran.
3.5 **Spec fidelity:** 58 ADRs of deviation + ticket-added scope (T7) vs a spec that claims completeness → Phase D.
3.6 **No global coverage statement** for 668 ids → Phase B (folded into the capstone gap analysis).
3.7 **Capstone never ran** (T9) — the single biggest missing rigor step of the whole build.

---

## 4. Decisions taken in v2 (operator may override)

**4.1 Scratch unification + layout** (gitignored; executed in P19.1):
```
.agents/scratch/
  README.md            # what lives here, naming rule, retention
  ledgers/             # one per ticket: implement-spec_<PXX.Y>.md (renamed copies; originals kept until verified)
  pr/                  # <PXX.Y>_pr_body.md, <PXX.Y>_commit_msg.txt
  tools/               # one-off scripts (from scratch/: gen_adrs.py, scaffold_pkgs.sh, drive_gates.py, …)
  fixtures/            # er_fixture.json, p052_live/ …
  planning/            # THIS ledger + next-phase artifacts (BUILD_INDEX, COVERAGE_MATRIX, …)
  logs/                # (pruned) — delete *check*.log > 1 MB; they are reproducible
```
`scratch/` at repo root is emptied and removed; `.gitignore` keeps `scratch/` (harmless) and gains nothing else.

**4.2 Tickets in git:** remove `docs/tickets/` from `.gitignore`; commit all 48 files; amend the manifest paragraph ("gitignored… not committed") to "committed as the build's contract record; P19+ appended in order"; note in README. Rationale: not regenerable; they *are* the spec-to-implementation trace the operator wants.

**4.3 Backlog home:** new committed `docs/backlog/{BACKLOG.md,OPERATIONAL_READINESS.md}`; risk register untouched except backlog-id cross-refs; ADRs untouched.

**4.4 Capstone adoption:** run orchestrate-build's CAPSTONE (§3 of that skill) retroactively as tickets P19.2–P19.4, with the whole-chain gap analysis in an **independent fresh context** (the skill's anti-bias rule).

**4.5 Ticket digest:** the forward plan is delivered as `docs/tickets/P19.x…P21.x` + manifest rows (§6), produced by `decompose-spec` over the planning artifacts, then run with `orchestrate-build` (which will also run its own capstone at the end of the *new* chain).

**4.6 Autonomy boundary:** Phases A–F autonomous; Phase G stops for the operator; P19.1 (hygiene) may be cut and run immediately since its scope is already decided here.

**4.7 Artifact home (operator, 2026-09-08 after Phase A) — supersedes the `docs/build/` half of 4.1 and folds 4.3's `docs/backlog/` in:** every planning and capstone artifact that is not regenerable lives **committed under `docs/build/`**: this ledger (renamed `docs/build/PLANNING_LEDGER.md`), `BUILD_INDEX.md`, `LEDGER_DEFERRALS.md`, `DECISION_MEMO.md`, and every later ticket deliverable (`COVERAGE_MATRIX.csv`, `CAPSTONE_GAP_ANALYSIS.md`, `COMPOSED_E2E_REPORT.md`, `BACKLOG.md`, `OPERATIONAL_READINESS.md`, `SPEC_RECONCILIATION_PLAN.md`, `INTEGRATION_PLAN.md`, `CI_STATUS.md`). `.agents/scratch/` keeps only raw agent ledgers, PR-body/commit drafts, one-off tools, fixtures and logs (4.1 layout minus `planning/`). **P19.1 performs the move** (`git mv` is impossible for untracked files — copy, then delete the scratch copies once committed). Until P19.1 lands, new artifacts are still written to `docs/build/` (the planning sessions commit nothing).

**4.8 Planning depth (operator, 2026-09-08) — supersedes §5's "B–F as separate sessions":** planning is **streamlined**. One scoping session **B′** collects only the numbers needed to write precise tickets, then Phase G (`DECISION_MEMO.md`) and decomposition follow — in the same session if context allows, otherwise the next. The full analyses become **committed deliverables of the tickets themselves** (so they land in `docs/build/` by construction and are done once, not twice): Phase B → P19.2; Phase C + F → P20.1; Phase D → P20.2; Phase E → P20.3. Rationale: ledger §6's chain is already stable; what remains is sharpening ACs, and redoing a 668-id matrix inside P19.2 after drafting it in scratch would be double work.

---

## 5. Planning phases (each = one fresh context; A first, then B–F in parallel, then G)

| Phase | Purpose | Key inputs | Output artifact (→ `docs/build/`) | Done when |
|---|---|---|---|---|
| **A** Build index + memory extraction | T1, T3, T8 prep | all ledgers, PR list (`gh pr list --state all`), `git log --all`, docs/tickets | `BUILD_INDEX.md` (46 rows: ticket→branch→commits→PR#/state/base→ledger→ADRs→traceability §→risk §→**5.3 live-verification status**), `LEDGER_DEFERRALS.md` (every non-met gap / deviation / deferral / "not run", with source) | no `unknown` cells except flagged for E |
| **B** Whole-spec coverage matrix (= capstone step 1, mechanical half) | T9, 3.6 | 668 SIG-* ids from spec (Part 0 grammar: MUST/SHOULD/RATIONALE), traceability, tests, src, ADRs, risk register | `COVERAGE_MATRIX.csv` + `COVERAGE_SUMMARY.md`; classes: covered+tested / covered+untested / deferred(RISK) / deviated(ADR) / rationale-only / **unreferenced**; 10-row spot-check by running the named tests | every id classified; top-20 gaps listed |
| **C** Unified backlog | T5 | risk register deferred+observation rows, ADR Deviations/Revisit, A's deferrals, `CHECKLIST_ITEMS→None`, manifest human prerequisites, §51–54 open items | `BACKLOG.csv/.md` (id, sources, type ∈ {defect, deferred-feature, **operational-prereq**, rights/legal, docs-drift, schema-refinement, external-dep}, req ids, package, blocks, size) + `BACKLOG_THEMES.md` | every RISK deferred row + ADR revisit trigger has exactly one backlog id |
| **D** Spec drift + reconciliation plan | T6, T7, T11 | §52 phase text vs each ticket's Load/Deliverables/ACs; ADR deviations; Appendix F/G; spec_src layout | `TICKET_VS_SPEC.md` (per deliverable: in-spec / spec-implied / ticket-added) + `SPEC_RECONCILIATION_PLAN.md` (amendment → target spec_src file → ADR? → order; ADR-001…057 dispositions: no-op / F-index / G-correction / amendment) | every ticket deliverable tagged; every ADR dispositioned |
| **E** Integration + release readiness | 3.1, T16 | PR graph, `.github/`, Makefile, `web/`, Docker `tests/db`, LICENSE state | `INTEGRATION_PLAN.md` (merge options for the 27 open PRs; conflict dry-run in a scratch worktree; `v0.x` criteria) + `CI_STATUS.md` | merged-main candidate green in a worktree, or blockers enumerated |
| **F** Operationalization gap analysis | T5, 3.4 | C's operational rows; `sig-connectors validate` (UNDETERMINED / ingestion_permitted counts); §35.1 Stage-0 + 19-project compact; SIG-GOV-012 legal home; `docs/slice/` (was J-1 real?); infra implied (PG18+PostGIS, OCFL, PMTiles, Zenodo, MapRoulette acct) | `OPERATIONAL_READINESS.md` (capability → code / rights / infra / human-prereq / first target; minimum viable live slice + critical path) | critical path to one real jurisdiction live has no TBD |
| **G** Synthesis → decision memo → ticket digest | T10, T12 | A–F | `DECISION_MEMO.md` (3–5 directions, sequence, rationale) → **operator chooses** → `decompose-spec` → `docs/tickets/P19.x–P2x.x` + manifest rows | operator-approved chain committed |

Capstone steps 2–3 (gap closure, composed E2E, retro live verification) are **execution**, not planning → tickets P19.3/P19.4 (§6).

**5.1 Streamlined plan (per §4.8; the table above stays as the definition of what each ticket must eventually produce).**

| Step | Purpose | Inputs | Output (→ `docs/build/` now, `docs/build/` after P19.1) | Done when |
|---|---|---|---|---|
| **B′** scoping | Enough facts to write precise ACs for P19.2–P21.x; **no full matrices** | (i) grep the 668 `SIG-*` ids from `docs/2_canonical_design_spec.md` and count how many appear in ≥1 PR body (`gh pr view N --json body`) / ADR `Requirement ids` / `tests/` / `src` — one number per class + the list of ids that appear **nowhere** (unreferenced candidates for P19.2); (ii) `uv run sig-connectors validate` (read-only) → counts of `ingestion_permitted` true/false/UNDETERMINED per source, the J-1 (OKC) sources' status; (iii) merge-conflict dry-run of PRs #20–#46 onto origin/main in a **throwaway worktree** (`git worktree add /tmp/sig-merge origin/main` → sequential `git merge --no-commit` of each branch tip; record conflicts, abort, remove the worktree) — no push, no PR change; (iv) CI facts: `.github/workflows/*` jobs, whether `tests/db` runs in CI, LICENSE state; (v) human-gate inventory from `LEDGER_DEFERRALS.md` §5 + risk register Phase 0 + manifest "Human prerequisites" | `SCOPING_NUMBERS.md` (one section per (i)–(v), every number with its command) | each of (i)–(v) has a number or an explicit "could not determine: <why>" |
| **G** memo | Sequence ALL work; mark human/decision gates; operationalization critical path with no TBD | Phase A artifacts + `SCOPING_NUMBERS.md` + §6 | `DECISION_MEMO.md` | every T-item, §5 output, LD row, RISK deferred row and ADR revisit trigger maps to exactly one ticket or an "accepted, no ticket" line |
| **Decomp** | Ticket files + manifest rows | `DECISION_MEMO.md` as the spec; `docs/tickets/_TEMPLATE.md`; §4.7 paths | `docs/tickets/P19.1…P21.x`, manifest rows 47+ with "post-build chain" preamble | one fresh `implement-spec` run per ticket is plausible for a weaker model |

---

## 6. Proposed next ticket chain (draft — **superseded 2026-09-08 by `planning/DECISION_MEMO.md` §3 and `docs/tickets/00_MANIFEST.md` rows 47–63: 17 tickets P19.1–P21.9**; kept for provenance)

| # | Ticket (draft id) | Scope | Depends |
|---|---|---|---|
| 47 | **P19.1 build-memory-and-hygiene** | fast-forward local main; unify scratch per §4.1; commit `docs/tickets/` (§4.2) + manifest amendment; `BUILD_INDEX.md` committed as `docs/build/BUILD_INDEX.md`; `AGENTS.md` hierarchy via `agent-docs`; prune logs | — (scope decided) |
| 48 | **P19.2 capstone-gap-analysis** | orchestrate-build CAPSTONE step 1 in an **independent fresh context**: whole-spec MET / MET-DIFFERENTLY / PARTIAL / MISSING / AT-RISK-INTEGRATION over all 668 ids + cross-cutting invariants + inter-ticket seams; = Phase B output promoted to `docs/build/CAPSTONE_GAP_ANALYSIS.md` | 47 |
| 49 | **P19.3 capstone-composed-verification** | step 3: one composed E2E over the real local stack (Docker PG18+PostGIS claim spine → connector fixtures → resolve → reconcile → API → exports → `web/` build) + **retroactive 5.3 live verification** for every ticket A flags; blockers recorded, never fabricated | 47 |
| 50 | **P19.4 capstone-gap-closure** | step 2: fix CODE gaps + tests, run VERIFICATION gaps, consciously accept sound deviations (recorded); ADR; traceability; risk register | 48, 49 |
| 51 | **P20.1 backlog-and-operational-readiness** | commit `docs/backlog/{BACKLOG.md,OPERATIONAL_READINESS.md}` (Phases C+F), cross-ref RISK rows | 48 |
| 52 | **P20.2 spec-reconciliation** | execute `SPEC_RECONCILIATION_PLAN.md`: spec_src edits → `BUILD.sh` → ADRs → Appendix F/G; fold ticket-added requirements back (T7/T11) | 48, 51 |
| 53 | **P20.3 integration-release** | execute `INTEGRATION_PLAN.md`: merge the 27 open PRs bottom-up (or agreed strategy), CI on main, `v0.1` tag, `refresh-repo-docs` | 50 |
| 54+ | **P21.x operationalization** | from `OPERATIONAL_READINESS.md` critical path: rights reviews → `ingestion_permitted` flips; Stage-0 outreach record; legal home; infra; first real J-1 ingest → publish | G decision |

---

## 7. Artifact registry

| Artifact | Phase | Path | Status |
|---|---|---|---|
| This ledger (v2) | — | `.agents/scratch/NEXT-PHASE_planning-ledger_20260908.md` (→ `planning/` after P19.1) | done |
| BUILD_INDEX.md (46 rows + §A.1 ground truth, §A.3 5.3 roll-up, §A.4 column notes) | A | `docs/build/BUILD_INDEX.md` → `docs/build/` (P19.1) | **done 2026-09-08** |
| LEDGER_DEFERRALS.md (90 rows: LD-V 12, LD-F 18, LD-D 14, LD-H 13, LD-P 7, LD-X 11, LH 15) | A | `docs/build/LEDGER_DEFERRALS.md` → `docs/build/` (P19.1) | **done 2026-09-08** |
| SCOPING_NUMBERS.md (+ companion SCOPING_ID_LISTS.md: the 98 / 253 / 250 / 13 id lists) | B′ | `docs/build/` → `docs/build/` (P19.1) | **done 2026-09-08** |
| DECISION_MEMO.md (15-ticket chain P19.1–P21.8, gate register HG-01..14, 90/90 LD mapping, critical path) | G | `docs/build/` → `docs/build/` (P19.1) | **done 2026-09-08** |
| docs/tickets/P19.1…P21.9 (17 files, P19.1 revised) + manifest rows 47–63 with "Post-build chain" preamble | Decomp | `docs/tickets/` (committed by P19.1) | **done 2026-09-08** |
| sig-postbuild-build-ledger.md (orchestrate-build machine state; **stays gitignored**, §9.G item 7) | Decomp | `docs/build/sig-postbuild-build-ledger.md` | **done 2026-09-08** |
| CAPSTONE_CLOSURE.md (ACCEPTED list) | **P19.5 deliverable** | `docs/build/` | produced by the ticket |
| RIGHTS_REVIEW_INDEX.md + rights/*.md, STAGE0_OUTREACH_RECORD.md, LIVE_WIRING_REPORT.md, FIRST_JURISDICTION_REPORT.md, PUBLICATION_CHECKLIST.md, INFRA_RUNBOOK.md, DEPOSITS.md, SUCCESSION.md, CURATION_UI.md, USABILITY_STUDY.md, CONTRIBUTION_BACK_LIVE.md, ECOSYSTEM_CONNECTORS.md, STAGE5_CONNECTORS.md | **P21.x deliverables** | `docs/build/` | produced by the tickets |
| COVERAGE_MATRIX.csv, CAPSTONE_GAP_ANALYSIS.md (+ `docs/build/tools/check_coverage_matrix.py`) | (was B) → **P19.2 deliverable** | `docs/build/` | produced by the ticket |
| COMPOSED_E2E_REPORT.md (+ retro 5.3 results, `tests/e2e/test_composed_stack.py`) | **P19.3 deliverable** | `docs/build/` | produced by the ticket |
| BACKLOG.md, OPERATIONAL_READINESS.md | (was C + F) → **P20.1 deliverable** | `docs/build/` (§4.7 folds `docs/backlog/` in) | produced by the ticket |
| TICKET_VS_SPEC.md, SPEC_RECONCILIATION_PLAN.md | (was D) → **P20.2 deliverable** | `docs/build/` + spec_src edits | produced by the ticket |
| INTEGRATION_PLAN.md, CI_STATUS.md | (was E) → **P20.3 deliverable** | `docs/build/` | produced by the ticket |
| This ledger | — | → `docs/build/PLANNING_LEDGER.md` (P19.1) | move pending |

---

## 8. Fresh-context prompts

**8.1 Generic**
```
Continue the SIG post-build planning in /Users/stevenvitali/Eleutheria (checkout: devin/p18-2-france-belgium,
tip of the stacked chain; PRs #1–#19 merged to main, #20–#46 open). Read
.agents/scratch/NEXT-PHASE_planning-ledger_20260908.md in full (§1 TODO ledger, §2 ground truth, §4 decisions,
§5 phases, §6 draft ticket chain). Execute exactly ONE phase: <X>. Mechanical before judgmental; cite file:line /
PR / ADR / RISK ids; commit nothing unless §4 records that decision. Write outputs to
docs/build/ (mkdir -p). Append "## 9.<X> findings" to the ledger, update §1 statuses, §7, §10;
report to the operator with the recommended next step. Do not start another phase in this context.
```
**8.2 Phase A (run first)** — as 8.1 with: build `BUILD_INDEX.md` (46 rows incl. per-ticket implement-spec 5.3 live-verification status: run / fixture-only / skipped / not-applicable, quoting the ledger) and `LEDGER_DEFERRALS.md`; inputs: `.agents/scratch/{implement-spec_*,ledger_*}`, `scratch/*ledger*`, `gh pr list --state all --limit 100 --json number,title,state,baseRefName,headRefName,mergedAt`, `git log --all --oneline`, `docs/tickets/*`.
**8.3 P19.1 (may run now via implement-spec once the ticket file exists)** — write `docs/tickets/P19.1__build-memory-and-hygiene.md` from `_TEMPLATE.md` using §4.1/§4.2/§6 row 47, add manifest row 47, then `implement-spec spec=docs/tickets/P19.1__build-memory-and-hygiene.md`.
**8.4 Phase G** — as 8.1 with: read all §7 artifacts; write `DECISION_MEMO.md` (3–5 directions, sequence, rationale); **stop and present** to the operator; on approval run `decompose-spec` over the planning artifacts to emit P19.2+ ticket files + manifest rows.

**8.5 Streamlined continuation (current path, per §4.8) — paste the same PLANNING-agent prompt used for Phase A.** It reads §10, finds row **B′** as the first non-done step, and executes §5.1 B′ (read-only; the merge dry-run happens only in a throwaway `git worktree` under `/tmp`, aborted and removed). It writes `SCOPING_NUMBERS.md`, appends `## 9.B′ findings`, updates §7/§10, and — if context allows — continues to G (`DECISION_MEMO.md`, sequencing ALL work with explicit gate lines; no operator stop needed since §4.8 already approved the streamlined chain) and then decomposition (`decompose-spec` skill, tickets_dir=`docs/tickets`, base_branch = `devin/p18-2-france-belgium`, revising the P19.1 draft to include the §4.7 move). Each step writes its artifact and updates §10 before the next begins.

---

## 9. Findings log (append-only)

**9.0 (v1 session):** chain closed at P18.2; "shape + gate, not live" and `CHECKLIST_ITEMS→None` patterns noted.
**9.0b (v2 session):** origin/main has 45 commits (19 merged PRs); 27 open stacked PRs; spec_src BUILD.sh reproduces the spec byte-identically; no tickets were added after Aug 26 and no lettered sub-tickets exist (T7); orchestrate-build CAPSTONE never ran; 11 ledgers flag skipped/fixture-only live verification.

## 9.A findings (Phase A — build index + deferral extraction; planning-only, read-only; 2026-09-08)

Artifacts: `docs/build/BUILD_INDEX.md`, `docs/build/LEDGER_DEFERRALS.md`. Method: `gh pr list --state all` (46 PRs: #1–#19 MERGED, #20–#46 OPEN, each base = previous head; #20 bases on `main`), `git rev-list`/`rev-parse` per branch, ADR `**Phase:**` fields, risk-register `## Phase` headings (line ranges), traceability ticket-mention counts, and a three-subagent full read of all 44 ledgers with hand spot-checks (one subagent contamination — P01.1 quoting P02.3 — caught and corrected, `BUILD_INDEX.md` §A.6).

1. **Chain integrity:** all 27 open branches are exactly +1 commit over their base except P14.1 (+2: `d663089` + hardening `4493b14`, a P12.1 analytics fix landed on P14.1's branch, no ADR — LD-D14). Local == origin for every surviving branch; `devin/p02-1-claim-spine` was deleted after merge (tip = `128342a^2` = `2fb80b8`). Local `main` = `a33177c`, **44 behind** origin/main (T16).
2. **Memory:** 44 ledgers for 46 tickets — **P00.4 and P04.2 have none**; 15 ledgers are stubs or self-contradictory (LH-01..15: gap table/evidence "TBD" in P06.1, P08.2, P12.2, P13.2, P15.2, P16.1, P17.2; P07.2/P07.3 stopped mid-run; unticked ACs in P10.1/P10.3/P13.1). For those the PR body is the only evidence record → P19.1's committed BUILD_INDEX must link PR bodies, and P19.3 must regenerate rather than trust their evidence.
3. **5.3 live verification (T8):** run 15 / fixture-only 18 / not-applicable 3 / not-recorded 10 (`BUILD_INDEX.md` §A.3). Material: the **P06.1 hard gate was fixture-only** ("J-1 acceptance query runs in CI without Docker", PR #16); the API was served live but over an **in-memory ReadStore** ("No DB fetch-by-id layer exists", P14.1 ledger L107); the entire reconcile/inference/tasks layer is pure-Python value objects never persisted (ADR-037/038/039/054); `web/` was rendered from fixtures; every connector ran over committed fixtures except P07.3's real USAspending trace. No two runtime surfaces were ever driven together → the composed E2E (P19.3) has a precise seam list (§A.3 last paragraph).
4. **Deferrals:** 90 rows extracted (LD-V 12, LD-F 18, LD-D 14, LD-H 13, LD-P 7, LD-X 11, LH 15). **Orphaned seams** (named a later owner that never picked them up): curation web UI (P05.2→"P15", LD-F05), vector-tile generation (P14.2→P15.3→nobody, LD-F07), `derivative_permitted` export gate (P14.2→P00.4 already closed, LD-F08), jurisdiction-conditional web render (P18.1→P15/P18.2, never built, LD-V12), osm live wiring (RISK-P4-06, LD-F03), Stage-5 connectors for P17.x pathways (LD-H12), and **P08.1 has neither an ADR nor a risk-register section** (LD-X05). These go straight into the P19.2 gap analysis as PARTIAL/MISSING candidates.
5. **Spec-fidelity inputs for Phase D:** ledgers cite spec Appendix-F logical ADR numbers that differ from `docs/adr/` numbering (P02.1 "ADR-013", P05.1 "ADR-016=Splink", P06.1 "ADR-024/025", P16.2 "ADR-017 (repo ADR-055)") — LD-X04/LD-D03; 14 recorded deviations (LD-D01..14) each need a Phase D disposition; the 32→34 spec amendment sat uncommitted in the working tree across P00.1–P02.3 (LD-X01) but is in the committed spec today.
6. **Human prerequisites already visible from the build** (LD-P01..07): Stage-0 outreach, legal home/counsel items, P16.1 usability study (AC7 never performed), MapRoulette account + Organised Editing registration, rights reviews for every `ingestion_permitted=false`/UNDETERMINED source, Zenodo + object-store accounts, Docker-capable CI for `tests/db`, R-11 zero-cost keepalive.
7. **Small P19.1 additions found:** manifest row 25 still reads "32/34 detectors" (LD-X10); `_TEMPLATE.md` says "of 43" (LD-X11, already in the draft); `.devinignore` re-includes become partly redundant once tickets are committed (LD-X09).
8. **Traceability is thematic, not ticket-sectioned** (`docs/traceability.md` headings are §-themes); Phase B should map ids→tickets via PR-body requirement tables + ADR `Requirement ids` fields, not via that file.

Not done here (by design): no tests run, no `make check`, no Docker; nothing committed.

**9.A-b operator decisions (same session, after the Phase A report):** (1) `BUILD_INDEX.md` row count confirmed 46/46 (P00.1→P18.2, 10 columns each; wide-table rendering had clipped it visually). (2) **Artifact home → `docs/build/`, committed** (§4.7): planning ledger + all planning/capstone artifacts in git; `.agents/scratch/` keeps raw ledgers/logs only; P19.1 executes the move. (3) **Planning depth → streamlined** (§4.8, §5.1): one scoping session B′ → `DECISION_MEMO.md` → decomposition; Phases B/C/D/E/F become deliverables of P19.2 / P20.1 / P20.2 / P20.3. §7 and §10 rewritten accordingly; §8.5 is the continuation prompt note.

## 9.B′ findings (step B′ — scoping numbers; planning-only, read-only except the throwaway merge worktree; 2026-09-08)

Artifacts: `docs/build/SCOPING_NUMBERS.md` (§(i)–(v) + corrections), `SCOPING_ID_LISTS.md` (id lists). Every number carries its command; throwaway scripts in `/tmp/sig-scope/` (not durable — re-derive in P19.2).

1. **Coverage (i):** 668 defined ids (646 MUST/13 SHOULD/2 MAY/7 RATIONALE; the 672 raw tokens include 4 reserved-unassigned ENG ids). Range notation (`SIG-GOV-001…011`) is pervasive (≈1,100 occurrences), so counts were range-expanded. Referenced in: PR bodies 364 · ADRs 358 · `tests/`+`web/tests` 415 · source 500 · traceability 421 · tickets 418 · risk register 232. **Union of everything = 570 → 98 ids referenced nowhere** (CHART 25, ENG 16, EPIS 16, INGEST 16 incl. Data-Driven-releases `INGEST-043*`, GOV 5 incl. Zenodo/SWH `GOV-022`, GEO 4, STORE 3 incl. zero-cost `STORE-003`, CONTRIB 2 = Stage-0 `012/012a`, …). **253 ids appear in no test file; 250 ids were never assigned to any ticket at decomposition** (spec §52 itself names only 21 ids — phases are described by section). 13 ids are claimed in traceability but absent from tests and source; 34 tested ids are never claimed in traceability.
2. **Rights (ii):** `sig-connectors validate` → 109 sources, **87 UNDETERMINED, 0 `ingestion_permitted=true`, 0 loadable**. The `ingestion_permitted` key is absent from every `sources.toml` row (defaults false). 18 sources need only the flip + recorded review (all OSM-family, deflock, eyes_on_flock, atlas, gleif, wikidata, raa_prefectures…). `compact_status`: no source is `permission_granted`/`partnership_active`; 43 `not_contacted`. **J-1/OKC: 7 of the slice's 8 fixture source ids are not in the registry**; `usaspending` (the only live fetch ever) is UNDETERMINED → the P07.3 trace bypassed the loader gate.
3. **Merge dry-run (iii):** all 27 open branches fork from P07.3's commit `2faf380`; `origin/main`'s later merge commits add no tree change. Independent merges (27× `--no-commit`, aborted) **and** a bottom-up accumulation on a detached worktree HEAD: **0 conflicts**, final tree identical to the P18.2 tip. Worktree removed; no ref/remote touched. §3.1's conflict-magnet hypothesis is falsified; integration strategy (merge-commit vs squash vs single) becomes a pure operator choice (HG-05).
4. **CI (iv):** one workflow, jobs `python` + `web`; **`tests/db` already runs in CI** (`SIG_REQUIRE_DB_TESTS=1`, 114 db tests, 2364 passed on #46 run `34273769189` today) → **LD-V11 closed; LD-P06's "Docker CI runner" prerequisite is void**. All 27 PRs green. 0 tags, no branch protection, repo PUBLIC, GitHub licence detection "Other", SBOM stale (Aug 26), no dependabot/CODEOWNERS/SECURITY.md.
5. **Human gates (v):** 14 gates `HG-01..14` (legal home, counsel items, 109 rights reviews, Stage-0 outreach, integration strategy, first jurisdiction, Zenodo/object-store/CDN, MapRoulette+OSM accounts, API tokens, usability study, operating governance, hosting/budget, spec-amendment sign-off, capstone accept-list sign-off).
6. **Corrections:** ledger §2.4 "272 RISK rows" → 269 unique ids (270 rows); 118 rows under Scaffolded/Deferred/Unverifiable headings + 57/57 ADR revisit triggers = the P20.1 backlog universe.

## 9.G findings (Phase G — decision memo; same session; 2026-09-08)

Artifact: `docs/build/DECISION_MEMO.md`. No operator stop (§4.8). Decisions recorded there:

1. **All six directions kept and ordered** D5 memory → D2 capstone → D6 backlog/readiness → D1 spec fidelity → D3 integration/v0.1 → D4 operationalization; rationale per direction in memo §1.
2. **Chain = 15 tickets, sequence 47–61:** P19.1 hygiene · P19.2 capstone gap analysis (independent context) · P19.3 composed verification + retro 5.3 (+ committed Docker-gated `tests/e2e/test_composed_stack.py` with LD-tagged xfails) · P19.4 closure (explicit CODE list: LD-F06 DB ReadStore, LD-V12, LD-F08, LD-F04, LD-F15, LD-X05, LD-D14, OKC registry rows + P19.2 `→P19.4` tags) · P20.1 backlog + readiness · P20.2 spec reconciliation · P20.3 integration + `v0.1.0` · P21.1 rights review packets/registry · P21.2 persist annotation layer (decision-gated) · P21.3 live connector wiring · P21.4 first jurisdiction (OKC) ingest + publish · P21.5 infra/deposit/tiles · P21.6 curation web UI · P21.7 contribution-back live + usability study · P21.8 Stage-5 connectors + Data Driven releases. §6's draft (P19.1–P20.3 + "P21.x") is confirmed and P21.x is made concrete.
3. **Gate mechanism:** a `Gate status` header field per gated ticket; unticked ⇒ ticket ships everything up to the gate and records `blockedOn: HG-nn`; the chain never blocks; re-run is idempotent. Gates HG-01..14 from SCOPING §(v). HG-06 (first jurisdiction) is *decided* = OKC.
4. **Traceability closed:** T1–T16 → tickets (memo §5.1); every §5/§5.1 artifact → a committing ticket (§5.2); **90/90 LD rows → exactly one ticket**, with one `accepted, no ticket` (LD-V10) (§5.3); 118 risk-register deferred rows + 57 ADR revisit triggers → P20.1 assigns one `BL-nnn` each with an asserting AC (§5.4); 98/253/250 id lists → P19.2 (§5.5).
5. **Critical path to OKC live** (memo §6): 8 steps, human actions marked ⧗, no TBD.
6. **Ledger corrections carried:** §6 row 51 dependency changed from "48" to "50" (backlog must see what P19.4 left open); P20.3 becomes the point where the stack collapses into `main` and P21.x fork from `main` @ `v0.1.0`.
7. **Build-ledger home exception to §4.7:** the `orchestrate-build` machine ledger (`sig-postbuild-build-ledger.md`, written by decomposition) must stay gitignored, so P19.1 leaves it in `docs/build/` (only that file) and moves everything else to `docs/build/`.

## 9.8 findings (decomposition; same session; 2026-09-08)

Artifacts: `docs/tickets/P19.1__build-memory-and-hygiene.md` (revised: §4.7 move, LD-X03/X07/X09/X10/X11, build-ledger exception), 16 new ticket files `P19.2…P21.9`, `docs/tickets/00_MANIFEST.md` "Post-build chain (rows 47–63)" preamble + 17-row table + post-build ownership notes, `docs/build/sig-postbuild-build-ledger.md` (orchestrate-build machine ledger — gitignored by design). `decompose-spec` skill followed (Phase 0 read → Phase 1 seams from `SCOPING_NUMBERS.md` §(vi) → Phase 2 table = memo §3 → Phase 3 contracts → Phase 4 adversarial review → Phase 5 ledger + manifest).

1. **Chain = 17 tickets (47–63)**, linear. The Phase-4 review (fresh read-only subagent) returned 15 findings, all applied: **2 BLOCKERS** — P20.3's merge loop would have merged its own PR (now merges #20–#53, never #54; PR count corrected to 34) and P19.3's `xfail("LD-F04")` violated its own `^LD-…:` regex (fixed); **2 overflow splits** — P19.4 → P19.4 spine wiring (`PgClaimSink`, `PgReadStore`, ER over PG) + P19.5 closure (gates, web render, `inference` CLI, docs, ACCEPTED list); P21.8 → P21.8 Data Driven + coarse-international, P21.9 Stage-5 pathway connectors + parser layers; **double-ownership** — `usaspending` rights block and the 6 OKC registry rows moved from closure to P21.1; **conditional ACs** marked in P21.2 (full vs shrunk), P21.7 (HG-10), P21.8/P21.9 (HG-03); handoff ids LD-H08 (→P21.5), LD-H09/H11 (→P19.5) now named in the receiving tickets; P19.2's Load states it is the classify/verify owner only; P21.4's `run_okc.sh` now names the actual CLIs (`sig-connectors run`, `sig-resolution match --dsn`, `python -m reconcile resolve --dsn`, `sig-db annotations rebuild`); every Phase-gate AC line (and `_TEMPLATE.md:33`) carries `*(deterministic)*`.
2. **Traceability check (mechanical):** all 90 LD ids appear in ≥1 ticket file; only LD-V05/LD-D07/LD-V08 appear in 3 (xfail hand-offs P19.3 → P19.5 lists as "remaining" → P21.2/P21.4 owner) — consistent with memo §5.3's single landing. ADR numbers pre-allocated without collision: ADR-058 (P19.1), 059 (P19.4), 060+061 (P19.5), 062 (P20.2), 063 (P21.1), 064 (P21.2), 065 (P21.3), 066 (P21.4), 067 (P21.5), 068 (P21.6), 069 (P21.7), 070 (P21.8), 071 (P21.9).
3. **Counts a weaker model will check:** `docs/tickets/` = 65 files (46 + manifest + template + 17); P19.1 commits 7 files to `docs/build/`; `sig-connectors validate` → 115 sources after P21.1; 27 rights packets; P19.2 §(e) = 24 seam rows; P19.3 §(c) = 28 retro rows; P20.1 asserts 118/118 RISK rows, ≥57 ADR triggers, 90/90 LD rows.
4. **Gate mechanism in the ticket files:** a `Gate status` header block per gated ticket (HG-03/04/05/07/08/09/10/12/13/14 + decision gates A5/A6); unticked ⇒ deliverables up to the gate + `blockedOn`. P20.2 carries the A1–A8 normative-amendment tick list; P20.3 carries the merge strategy + "Go" ticks.
5. **Base-branch switch:** rows 47–54 stack on `devin/p18-2-france-belgium`; P20.3 (row 54) merges #20–#53 into `main` + `v0.1.0`; rows 55–63 fork from `main` (or from the P20.3 branch if HG-05 is unticked) — recorded in the manifest and the build ledger.
6. **Nothing committed; nothing outside `docs/build/` and `docs/tickets/` written**; the throwaway merge worktree was removed; the main working tree, all branch refs and the remote are untouched (`git status` = `?? .devinignore`).
7. **Operator rules added after the report (same session):** (a) **no ticket merges, tags or pushes `main`** — P20.3 rewritten as plan-only (`merge_dryrun.sh`, `INTEGRATION_PLAN.md` §(d) operator procedure, version bump, release-notes draft, docs refresh); HG-05 becomes a post-chain operator action; **no base switch** — all 17 tickets stack on `devin/p18-2-france-belgium`; P21.1 `base_branch` = the P20.3 branch. (b) **Single resumable `orchestrate-build` call**: build ledger gains OPERATING MODE (with the verbatim prompt), GATE PROTOCOL (pause before each gated ticket, after P19.5 for HG-14; answers recorded in a GATE DECISIONS table; workers copy them into the ticket header; "skip" → RETURN PASS), `mergePolicy: NONE`, dispatch `subagent`, `autonomy: checkpoint`, worktree = main checkout, pinned base `1baf05f`. (c) P20.1 gains deliverable 0 (record the HG-14 signature into `CAPSTONE_CLOSURE.md` §(e)). (d) Memo §1/§3/§4/§6/§7/§9 and manifest preamble rules 3–4 updated accordingly.

---

## 10. Resume protocol + status (the bootstrap prompt drives this table)

> **MODE (operator, 2026-09-08): PLANNING-ONLY.** Do NOT execute rows 1, 2, or 9 (no `implement-spec`,
> no `orchestrate-build`, no code/spec/`.gitignore` changes, no commits or PRs). The planning session(s)
> produce: a read-only Phase A (`BUILD_INDEX.md` + `LEDGER_DEFERRALS.md` in `docs/build/`),
> Phases B–F, a DECISION_MEMO that **sequences ALL the work** (no direction pruning; decision-gated work is
> marked as such), and then the full ordered ticket chain as files in `docs/tickets/` + manifest rows.
> Planning uses the stronger model; implementation happens later with the weaker one. The existing
> `docs/tickets/P19.1__build-memory-and-hygiene.md` is a draft the planning session may revise/renumber.

**Protocol.** A fresh session reads this ledger, finds the **first row below whose State is not `done`**,
executes exactly that step (one step per session; steps marked ∥ may be run in parallel sessions), records
findings in §9 and the artifact in §7, sets the row's State (`done` / `blocked: <why>`), and ends by telling
the operator which row is next and what prompt to paste. Steps 1–2 and 8–9 are *execution* (they change the
repo, via `implement-spec`, and open stacked PRs off the current tip); steps 3–7 are *planning* (they write
only to `docs/build/`, commit nothing). Step 7 **stops for the operator's choice**.

| # | Step | How | State |
|---|---|---|---|
| 0 | Meta-plan v2 | this document | done |
| A | **Phase A (planning-only)** — read-only build index + deferral extraction, incl. per-ticket 5.3 status | §5 A; outputs `docs/build/{BUILD_INDEX,LEDGER_DEFERRALS}.md`; findings §9.A | **done 2026-09-08** |
| 1 | **P19.1** build memory & hygiene (commits tickets, unifies scratch, promotes Phase A outputs to `docs/build/`, AGENTS.md) | `implement-spec spec=docs/tickets/P19.1__build-memory-and-hygiene.md live_verification=false` on the current tip; opens PR #47. After it lands, this ledger lives at `docs/build/NEXT-PHASE_planning-ledger_20260908.md` | N/A in planning mode (execution; ticket re-cut in step 8) |
| 2 | Verify Phase A outputs exist (`docs/build/BUILD_INDEX.md`, `LEDGER_DEFERRALS.md`) and stay on the P19.1 tip | quick check; if P19.1 skipped anything, run 8.2 | N/A in planning mode (Phase A outputs already in `planning/`) |
| **B′** | Scoping numbers (replaces separate Phases B–F per §4.8): id-reference counts + unreferenced list; `sig-connectors validate` rights counts; merge dry-run of #20–#46 in a throwaway worktree; CI facts; human-gate inventory | §5.1 B′; prompt 8.5; output `planning/SCOPING_NUMBERS.md` + `SCOPING_ID_LISTS.md`; findings §9.B′ | **done 2026-09-08** |
| ~~3–6b~~ | ~~Phases B, C, D, E, F as separate sessions~~ | folded into ticket deliverables: B→P19.2, C+F→P20.1, D→P20.2, E→P20.3 (§4.8, §7) | superseded 2026-09-08 |
| 7 | Phase G — `DECISION_MEMO.md` sequencing ALL work (hygiene → capstone gap analysis → composed E2E + retro 5.3 → closure → backlog/readiness → spec reconciliation → integration + v0.1 → operationalization critical path with gate lines) | §5.1 G; prompt 8.5 (no operator stop: streamlined chain pre-approved in §4.8; memo still presented in the session report); output `planning/DECISION_MEMO.md`; findings §9.G | **done 2026-09-08** |
| 8 | Cut the chain into `docs/tickets/P19.1(revised)…P21.9` + manifest rows 47–63 with "post-build chain" preamble | `decompose-spec` over `docs/build/*` + `DECISION_MEMO.md`, tickets_dir=docs/tickets; P19.1 revised to execute the §4.7 move; Phase-4 adversarial review (fresh subagent) applied; findings §9.8 | **done 2026-09-08** |
| 9 | Run the chain ticket-by-ticket (P19.1 → P19.2 → P19.3 → P19.4 → P19.5 → P20.1 → P20.2 → P20.3 → P21.1 … P21.9) | single resumable `orchestrate-build` call — the verbatim prompt is in the build ledger's OPERATING MODE note (`docs/build/sig-postbuild-build-ledger.md`); pauses only at SETUP, human gates, real blocks, CAPSTONE; merges nothing — the operator integrates afterwards per `docs/build/INTEGRATION_PLAN.md` | **next (execution; leaves planning mode)** |
