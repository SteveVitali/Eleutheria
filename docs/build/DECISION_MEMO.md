# DECISION_MEMO — sequencing all post-build work for SIG (Phase G)

- **Produced:** 2026-09-08, planning-only session, on `devin/p18-2-france-belgium` @ `1baf05f`. Inputs: planning ledger `.agents/scratch/NEXT-PHASE_planning-ledger_20260908.md` (§1 T1–T16, §4 decisions, §5/§5.1, §6 draft chain), `BUILD_INDEX.md`, `LEDGER_DEFERRALS.md` (90 LD rows), `SCOPING_NUMBERS.md` + `SCOPING_ID_LISTS.md` (B′), `~/.claude/skills/orchestrate-build/SKILL.md` §3 (CAPSTONE), `docs/tickets/_TEMPLATE.md`, `docs/tickets/00_MANIFEST.md`.
- **Status:** the streamlined chain is pre-approved (ledger §4.8); this memo does **not** wait for an operator choice between directions. It sequences **all** directions and marks every step that a human must unblock with a `GATE:` line. It is the "spec" that `decompose-spec` turns into `docs/tickets/P19.1…P21.9` + manifest rows 47–63.
- **After P19.1 lands this file lives at `docs/build/DECISION_MEMO.md`** (ledger §4.7).

---

## 1. What we are deciding

The 46-ticket build (PRs #1–#46) is code-complete against its ticket contracts but has never been judged **as a whole**: no capstone gap analysis, no composed end-to-end run, 27 PRs unmerged, 0 sources loadable, and the build's own memory (tickets, ledgers, this planning) uncommitted. Six directions were on the table; **none is pruned** — they are ordered so each produces the inputs the next needs:

| Dir | Direction | Why it is where it is |
|---|---|---|
| D5 | **Memory & hygiene** (tickets + planning artifacts into git, scratch unified, AGENTS.md) | Everything after it cites committed paths; cheapest; already decided (§4.2/§4.7) |
| D2 | **Capstone rigor** (whole-spec gap analysis → composed E2E + retro live verification → closure) | The single largest missing rigor step (ledger §3.7); produces the verdicts every later direction consumes |
| D6 | **One backlog + operational readiness** | Needs the capstone verdicts to know what is still open; feeds spec reconciliation and P21 ordering |
| D1 | **Spec fidelity** (fold ticket-added scope back; disposition 58 ADRs; fix Appendix F numbering) | Needs D2's per-id verdicts and D6's accepted-deviation list; touches normative text → operator gate |
| D3 | **Integration + v0.1** | Mechanically trivial (0 conflicts, SCOPING §(iii)). **No ticket merges** (operator rule): P20.3 writes the dry-run script + the exact merge/tag procedure; the operator integrates the whole stack after the chain (HG-05 is a post-chain action, not a ticket gate) |
| D4 | **Operationalization** toward one real jurisdiction (OKC) live | Everything before it is prerequisite; the human gates (rights, legal home, accounts) are interleaved explicitly |

## 2. Ground truth the sequence rests on (numbers from `SCOPING_NUMBERS.md`)

- 668 requirement ids; **98 referenced nowhere**, **253 in no test**, **250 never assigned to a ticket**; 13 claimed in traceability without code. → P19.2's matrix is not optional.
- `sig-connectors validate`: **109 sources, 87 UNDETERMINED, 0 `ingestion_permitted`, 0 loadable**; 18 need only the flip + recorded review; **7 of 8 OKC slice sources are unregistered**. → operationalization starts with rights reviews, not code.
- Merge dry-run: **0 conflicts** for all 27 PRs, final tree == tip. `tests/db` **already runs in CI** (114 db tests; 2364 passed on #46). → LD-V11 closed; integration is a decision, not a workstream.
- Runtime seams never crossed together (BUILD_INDEX §A.3): PG spine ↔ connectors ↔ resolution ↔ reconcile/inference/tasks (no persistence, ADR-037/038/039/054) ↔ API (**in-memory ReadStore**, LD-F06) ↔ exports ↔ web (fixtures). → the composed E2E will stop at the API seam until P19.4 builds the DB-backed ReadStore.
- 14 human gates `HG-01..14` (SCOPING §(v)).

## 3. The chain (sequence 47–63; every ticket forks from the branch the previous one leaves checked out)

Phase 19 = capstone & consolidation; Phase 20 = reconciliation & release; Phase 21 = operationalization. Every ticket ends on the §51.3 phase gate (`make check` green; ADR for any deviation; traceability + risk register sections). "Commits" below are the durable deliverables under `docs/build/` (ledger §4.7).

| # | Ticket | One-line scope | Commits to `docs/build/` | Depends | Gate |
|---|---|---|---|---|---|
| 47 | **P19.1 build-memory-and-hygiene** | Commit `docs/tickets/`; move planning ledger + all `planning/*` to `docs/build/`; unify `.agents/scratch/` (§4.1 minus `planning/`); `AGENTS.md` via `agent-docs`; fast-forward local `main`; fix LD-X09/X10/X11; ADR-058 | `PLANNING_LEDGER.md`, `BUILD_INDEX.md`, `LEDGER_DEFERRALS.md`, `SCOPING_NUMBERS.md`, `SCOPING_ID_LISTS.md`, `DECISION_MEMO.md` | P18.2 | none |
| 48 | **P19.2 capstone-gap-analysis** (CAPSTONE step 1, **independent fresh context**; read-only w.r.t. code) | 668-row coverage matrix with MET / MET-DIFFERENTLY / PARTIAL / MISSING / AT-RISK-INTEGRATION; seam hunt over LD-H01..13 + orphaned seams; 10-row spot-check by running named tests; classifies the 98/253/250 lists; owning-ticket column; closure routing tags (`→P19.4 S/M`, `→P21.n`, `→P20.1 backlog`, `accepted`) | `COVERAGE_MATRIX.csv`, `CAPSTONE_GAP_ANALYSIS.md` | 47 | none |
| 49 | **P19.3 capstone-composed-verification** (step 3 + retro 5.3) | Drive the real local stack as one unit (Docker PG18+PostGIS via sqitch → OCFL → connector fixture replay through the real pipeline → resolution → reconcile → API → exports → `web/` build); a committed Docker-gated composed test that asserts what works and `xfail`s each recorded blocker by LD id; retro CLI matrix (LD-V02); ISOLATION re-proof (LD-X06); LH-01..15 evidence regenerated | `COMPOSED_E2E_REPORT.md` + `tests/e2e/test_composed_stack.py` | 48 | none (blockers recorded, never faked) |
| 50 | **P19.4 capstone-spine-wiring** (step 2, part 1) | Cross the three spine seams the composed run proved unwired: `PgClaimSink` (SCOPING §(vi): connector claims never reached PG), `PgReadStore` over PG with a `_compute_on_read` seam for annotations (LD-F06), ER + review queue over PG (LD-F04), `python -m reconcile resolve --dsn`; flips xfails LD-F06b/F06/F04 | (code + tests; `COVERAGE_MATRIX.csv` `closed_by=P19.4`) | 49 | none |
| 51 | **P19.5 capstone-gap-closure** (step 2, part 2) | Remaining S/M CODE gaps: `derivative_permitted` export gate (LD-F08/H09), jurisdiction-conditional web render (LD-V12/H11), `inference` CLI (LD-F15), every other `P19.4:S/M` matrix row; P08.1 ADR + §53 section (LD-X05); ADR-044 note for `4493b14` (LD-D14); the **ACCEPTED-deviations list** | `CAPSTONE_CLOSURE.md` (incl. ACCEPTED list) | 48, 49, 50 | **GATE HG-14**: ACCEPTED list proposed by the ticket, signed by the operator in PR review; rejected items become P20.1 backlog rows, never silent drops |
| 52 | **P20.1 backlog-and-operational-readiness** (Phases C + F) | One normalized backlog: every RISK row under Scaffolded/Deferred/Unverifiable headings (118), every ADR revisit trigger (57+), every open LD row, every `CHECKLIST_ITEMS→None`, every open P19.2 row → exactly one `BL-nnn`; risk register rows gain a `→ BL-nnn` cross-ref only; readiness map capability → code/rights/infra/human/first-target; **critical path §6 of this memo re-verified with no TBD** | `BACKLOG.md` + `BACKLOG.csv`, `BACKLOG_THEMES.md`, `OPERATIONAL_READINESS.md` | 51 | none |
| 53 | **P20.2 spec-reconciliation** (Phase D) | Tag every ticket deliverable `in-spec` / `spec-implied` / `ticket-added`; disposition ADR-001..061 (`no-op` / `F-index` / `G-correction` / `amendment`); apply **non-normative** edits (Appendix F ↔ `docs/adr/` numbering, Appendix G corrections, §52 phase-text alignment recorded in ADRs) via `spec_src` → `BUILD.sh`; list **normative** amendments A1–A8 (MapLibre vs zero-JS LD-F09, `not_researched` LD-F14, `canonical_name` LD-D12, partitioning LD-F01, persistence A5, curation A6, `evidence/` A7) with the exact `spec_src` diff proposed | `TICKET_VS_SPEC.md`, `SPEC_RECONCILIATION_PLAN.md`, spec_src edits + rebuilt spec | 52 | **GATE HG-13**: normative amendments applied only if pre-ticked by the operator in the ticket's "Approved amendments" block; unticked ones ship as proposals |
| 54 | **P20.3 integration-release** (Phase E; **plan only, merges nothing**) | Committed `merge_dryrun.sh` (re-runnable over all open PRs); `INTEGRATION_PLAN.md` with the operator's copy-paste bottom-up merge + `v0.1.0` tag + release procedure; `CI_STATUS.md`; version bump to 0.1.0 in this PR; release notes draft; `refresh-repo-docs` (README/CHANGELOG/CONTRIBUTING) | `INTEGRATION_PLAN.md`, `CI_STATUS.md`, `RELEASE_NOTES_v0.1.0.md`, `CHANGELOG.md` | 53 | none (HG-05 = operator, after the chain) |
| 55 | **P21.1 rights-review-and-registry-completion** | Registry rows for the 6 OKC slice sources (`UNDETERMINED`) + `usaspending` rights block; per-source **review packets** (`docs/build/rights/<source>.md`) for the 27 critical-path/flip-ready rows; review-metadata rule (a flip without reviewer+date is invalid); `sig-connectors review-status`; Stage-0 outreach record template + `compact_status` update path | `RIGHTS_REVIEW_INDEX.md`, `rights/*.md`, `STAGE0_OUTREACH_RECORD.md` | 54 | **GATE HG-03/HG-04**: the *flip* and outreach outcomes are human edits; the ticket makes each a one-line, checked change |
| 56 | **P21.2 persist-annotation-layer** | Persist contradiction / coverage / task / contributor / inference objects to their `graph_annotations.sql` tables (ADR-037/038/039/054 revisit); DDL ↔ dataclass alignment tests; API reads rows via the P19.4 store | `ANNOTATION_PERSISTENCE.md` | 55 | **decision-gated**: full only if P19.5's ACCEPTED list did not keep compute-on-read (and A5 unticked); else shrinks to alignment tests + ADR notes |
| 57 | **P21.3 live-connector-wiring** | `HttpxTransport` (Overpass 429/504 semantics) + `OcflCaptureStore` (LD-F03); MuckRock token mint + real HTTP (LD-F16); CivicClerk OKC tenant live verification; document connectors for the OKC government records; `sig-connectors run --mode live` refuses any source whose `review-status` is not green; real FETCH only for flipped sources, else fixture replay + blocker recorded | `LIVE_WIRING_REPORT.md`, `live_runs/*.json` | 55, 56 | **GATE HG-03** (≥1 flipped source) and **HG-09** (tokens as env secrets) |
| 58 | **P21.4 first-jurisdiction-ingest-and-publish** (OKC) | `sig-ops` compose runtime; export-backed `web/` data layer; composed pipeline over real fetched OKC data → resolve → reconcile → API → exports → `web/` build → J-1 + Q-1…13 against the live API; staging deploy; publication checklist | `FIRST_JURISDICTION_REPORT.md`, `PUBLICATION_CHECKLIST.md` | 56, 57 | **GATE HG-12** (staging host; local compose acceptable), **HG-01** (legal home), **HG-11** (two reviewers), **HG-02** (ODbL counsel): staging unconditional; *public* publish requires all ticked |
| 59 | **P21.5 infra-deposit-and-tiles** | Zenodo sandbox deposit + concept DOI (HG-07); object store + CDN/egress alarm + torrents (ADR-015); tile generation → PMTiles (LD-F07/H08); MapLibre island **only if** A1 unticked (LD-F09); zero-cost/degraded mode keepalive (SIG-GOV-021, LD-P07); mirrors + Software Heritage (SIG-GOV-022) | `INFRA_RUNBOOK.md`, `DEPOSITS.md`, `SUCCESSION.md` | 58 | **GATE HG-07/HG-12** (accounts, budget) |
| 60 | **P21.6 curation-web-ui** | The curation/review web surface never built (LD-F05/H04; ADR-030 CLI+JSONL): authenticated curation service + `/curate/**` pages over the persisted review queue; L0 entry; LLM-to-review as suggestions only | `CURATION_UI.md` | 56, 58 | decision-gated only by P19.2/P19.5's verdict on ADR-030 and A6 |
| 61 | **P21.7 contribution-back-live** | MapRoulette client + OSM changeset feed into `LeverageLedger` (LD-F11); Organised Editing registration record (HG-08); moderated usability study protocol + results (HG-10, P16.1 AC7) | `USABILITY_STUDY.md`, `CONTRIBUTION_BACK_LIVE.md` | 60 | **GATE HG-08** (accounts), **HG-10** (≥5 humans) |
| 62 | **P21.8 data-driven-and-coarse-international** | Data Driven releases as first-class source (`SIG-INGEST-043/043a–d/044`, unreferenced) with versioned re-ingest + agency crosswalk; coarse-international trio content path beyond LINK | `ECOSYSTEM_CONNECTORS.md` | 57 | **GATE HG-03/HG-04** per source |
| 63 | **P21.9 stage5-pathway-connectors** | Stage-5 connectors for the P17 pathways (LD-H12, RISK-P17-03) + the ADR-033-deferred parser layers (LD-F17) | `STAGE5_CONNECTORS.md` | 62 | **GATE HG-03/HG-04** per source |

**Chain shape.** Strictly linear (stacked PRs), **17 tickets** (sequence 47–63; the Phase-4 adversarial review split P19.4 at the store seam and P21.8 at the connector-family seam). P19.2/P19.3 could run in parallel logically but stack linearly for a single `chainTip`. **No ticket merges anything**: all 17 tickets stack on `devin/p18-2-france-belgium` (PRs #47–#63 on top of #20–#46); the operator integrates after the chain per `INTEGRATION_PLAN.md`. The plan is revisable at run time by `orchestrate-build` (split/merge written back to the build ledger).

## 4. Gate semantics (how a ticket behaves at a `GATE:` line)

1. A gate is a **field in the ticket header** (`- **Gate status:** …`). Under `orchestrate-build` the loop **pauses before the gated ticket** (after P19.5 for HG-14), asks the operator item by item (tick / value / skip), records the answers in the build ledger's `GATE DECISIONS` table, and the worker copies them into the ticket header in its first commit (build ledger → GATE PROTOCOL). By hand, the operator edits the block before the run.
2. "Skip for now" is a valid answer: the ticket does everything up to the gate, ships the prepared artifact (plan / packet / proposal), opens its PR, and is listed in the ledger's RETURN PASS table; the next ticket forks from it regardless. Gated work is finished by re-running the same ticket file (idempotent ACs) once the answers exist. `blockedOn` is reserved for real blocks.
3. **Never fabricate green** (orchestrate-build §3.3): a composed run blocked by credentials/infra is a recorded finding with the exact blocker and the command that would close it.
4. Secrets (tokens, keys) enter only via environment variables named in the ticket; never files in the repo; `.env*` stays gitignored.

Gate register: **HG-01** legal home · **HG-02** counsel items (ODbL 4.4(b), sui generis, RISK-P0-01..04/06/11/14) · **HG-03** per-source rights flips · **HG-04** Stage-0 outreach · **HG-05** integration strategy + go (post-chain operator action) · **HG-06** first jurisdiction (default OKC — *decided here*, no gate unless the operator overrides) · **HG-07** Zenodo/object store/CDN · **HG-08** MapRoulette/OSM accounts · **HG-09** API tokens · **HG-10** usability study humans · **HG-11** operating governance (board, two reviewers) · **HG-12** hosting/budget · **HG-13** normative spec amendments · **HG-14** capstone ACCEPTED list. HG-02 gates the *public export* of the ODbL compartment (P21.4/P21.5 publish steps), not any code ticket.

## 5. Traceability — everything tracked maps to exactly one ticket

**5.1 Ledger §1 T-items.** T1 → P19.1 (local `main` fast-forward; index committed) · T2 → satisfied (rule; every ticket's `base_branch` = current checkout) · T3 → P19.1 · T4 → P19.1 · T5 → P20.1 · T6 → P20.2 (explanation done; amendments executed there) · T7 → P20.2 (tagging `ticket-added`) · T8 → P19.3 · T9 → P19.2 + P19.3 + P19.4/P19.5 (the three CAPSTONE steps; the *decision* to adopt is done) · T10 → this memo + decomposition (done in this session; tickets committed by P19.1) · T11 → P20.2 · T12 → this memo (done) · T13 → done (§8 prompts) · T14 → done · T15 → P19.1 · T16 → P19.1 (main) + P19.3 (Docker tests locally; CI half already closed).

**5.2 Ledger §5 output artifacts.** A: `BUILD_INDEX.md`, `LEDGER_DEFERRALS.md` → committed by P19.1 · B: `COVERAGE_MATRIX.csv`, `COVERAGE_SUMMARY.md` (folded into `CAPSTONE_GAP_ANALYSIS.md`) → P19.2 · C: `BACKLOG.csv/.md`, `BACKLOG_THEMES.md` → P20.1 · D: `TICKET_VS_SPEC.md`, `SPEC_RECONCILIATION_PLAN.md` → P20.2 · E: `INTEGRATION_PLAN.md`, `CI_STATUS.md` → P20.3 · F: `OPERATIONAL_READINESS.md` → P20.1 · G: `DECISION_MEMO.md` → this file, committed by P19.1 · B′: `SCOPING_NUMBERS.md`, `SCOPING_ID_LISTS.md` → committed by P19.1 · capstone steps 2–3: `COMPOSED_E2E_REPORT.md` → P19.3, `CAPSTONE_CLOSURE.md` → P19.5.

**5.3 LEDGER_DEFERRALS rows (90).**

| Landing ticket | LD rows |
|---|---|
| P19.1 | LD-X03 (verify-gen semantics → AGENTS.md), LD-X07 (RDF canonicalisation note → AGENTS.md; otherwise accepted), LD-X09, LD-X10, LD-X11 |
| P19.2 (verify / classify) | LD-F02, LD-F12, LD-F13, LD-F17, LD-F18 (mark MET), LD-H01, LD-H02, LD-H03, LD-H04 (→ then P21.6), LD-H05 (MET), LD-H06, LD-H07, LD-H08 (→ then P21.5), LD-H09 (→ then P19.4), LD-H10, LD-H11 (→ then P19.4), LD-H12 (→ then P21.9), LD-H13, LD-X01 (confirm MET), LD-X08 (process finding: gate bypassed) |
| P19.3 (drive / regenerate evidence) | LD-V01, LD-V02, LD-V03 (fixture replay through real pipeline), LD-V04, LD-V05 (alignment test), LD-V06, LD-V07 (local real build with optional deps), LD-V08, LD-V09 (what exists), LD-V11 (local run; CI half closed), LD-X06, LH-01…LH-15 |
| P19.4 (spine wiring) | LD-F04, LD-F06 |
| P19.5 (closure) | LD-V12, LD-F08, LD-F15, LD-D14, LD-X05 |
| P20.1 (backlog id) | LD-F01 |
| P20.2 (spec disposition) | LD-D01, LD-D02, LD-D03, LD-D04, LD-D05, LD-D06, LD-D07, LD-D08, LD-D09, LD-D10, LD-D11, LD-D12, LD-D13, LD-F09, LD-F14, LD-X04 |
| P20.3 | LD-X02 |
| P21.1 | LD-P01, LD-P05 |
| P21.2 | LD-F10 (persistence half; usability half = LD-P03 → P21.7) |
| P21.3 | LD-F03, LD-F16 |
| P21.4 | LD-P02 (legal home gates the publish step) |
| P21.5 | LD-F07, LD-P06 (Zenodo/object store; the Docker-CI part is void), LD-P07 |
| P21.6 | LD-F05 |
| P21.7 | LD-F11, LD-P03, LD-P04 |
| accepted, no ticket | **LD-V10** (P17.x "expressibility, not ingestion" is the designed behaviour, RISK-P17-03; the *ingestion* half is LD-H12 → P21.8) |

Count: 5 + 20 + 26 + 2 + 5 + 1 + 16 + 1 + 2 + 1 + 2 + 1 + 3 + 1 + 3 + 1 = **90** ✓ (LD-V 12, LD-F 18, LD-D 14, LD-H 13, LD-P 7, LD-X 11, LH 15).

**5.4 Risk-register deferred rows (118 under Scaffolded/Deferred/Unverifiable headings) and ADR revisit triggers (57/57 ADRs at B′; P19.1–P19.5 add ADR-058..061).** Rule: **P20.1 assigns exactly one `BL-nnn` to each** and records the landing (`P19.4-done` / `P21.n` / `accepted` / `human-gate HG-nn`); its deterministic AC asserts 118/118 and 57/57 with a script that parses `docs/risk_register.md` headings and `## Revisit trigger` sections. Rows already closed by P19.4/P19.5 are marked `closed-by: P19.x` (still one backlog id). This is the "exactly one ticket" for those 175 items: P20.1.

**5.5 The 98 / 253 / 250 id lists.** → P19.2 classifies every id (`COVERAGE_MATRIX.csv` has 668 rows, no blank class). Functional MISSING ids already visible: `SIG-INGEST-043*` → P21.8; P17 pathway ingestion ids (`SIG-INGEST-046b/c`, `049a–d`) → P21.9; `SIG-GOV-022` mirrors/deposits → P21.5; `SIG-STORE-003/004/005` zero-cost → P21.5; `SIG-UI-001` personas → P21.7 (study) ; `SIG-CONTRIB-012/012a` Stage-0 → P21.1; `SIG-GEO-001/002/005/007` → P19.2 decides (likely MET-by-DDL, unreferenced by id).

**5.6 Human gates HG-01..14** → §4 above; each named in the gated ticket's header. HG-02 and HG-06 have no ticket of their own (HG-02 gates publish steps; HG-06 is decided = OKC).

## 6. Operationalization critical path — one real jurisdiction (Oklahoma City, J-1) live, no TBD

Each step names the ticket, the artefact that proves it, and the human gate (if any). Steps 1–7 are code/docs the model does; ⧗ marks a human action.

1. **P19.1** — memory committed (`docs/build/*`, tickets in git). Proof: `git ls-files docs/build docs/tickets | wc -l` ≥ 72 (65 tickets/manifest/template + 7 build files).
2. **P19.2 → P19.3 → P19.4 → P19.5** — capstone: verdict matrix; composed local stack run over the OKC fixtures with PG18 + OCFL + API + exports + web; `PgClaimSink` + `PgReadStore` + ER over PG built (P19.4); remaining gaps closed (P19.5). Proof: `tests/e2e/test_composed_stack.py` green under Docker with 0 xfails left tagged `LD-F06b`/`LD-F06`/`LD-F04`/`LD-V12`/`LD-F08`; `CAPSTONE_CLOSURE.md` ACCEPTED list. ⧗ **HG-14** operator signs ACCEPTED list in PR review.
3. **P20.1 → P20.2 → P20.3** — backlog + readiness; spec reconciled (⧗ **HG-13** operator ticks normative amendments); integration plan + dry-run script + release notes + docs refresh (**no merge**). Proof: `merge_dryrun.sh` exits 0; `INTEGRATION_PLAN.md` §(d) complete. ⧗ **HG-05** (after the chain, or at any boundary the operator prefers): operator runs the procedure — merge bottom-up, tag `v0.1.0`, release.
4. **P21.1** — the 6 OKC registry rows + rights packets for OKC's 8 sources (`deflock_repo`, `okc_procurement`, `okc_council` [CivicClerk], `okcpd_policy`, `ok_statute`, `journalrecord`, `oklahoman`, + `osm_overpass`) and the 18 flip-ready rows. ⧗ **HG-03**: operator (or counsel-reviewed reviewer) sets `ingestion_permitted = true` + `last_verified` + reviewer for at least: `okc_procurement`, `okc_council`, `okcpd_policy`, `ok_statute` (public government records, R1/R2) and `osm_overpass` (ODbL; export stays in the ODbL compartment pending ⧗ HG-02). ⧗ **HG-04**: Stage-0 outreach to DeFlock recorded (`compact_status`). Proof: `uv run sig-connectors validate` shows `loadable now ≥ 5`.
5. **P21.2** (if not ACCEPTED) — annotations persisted; **P21.3** — live transports behind the gate; real FETCH for the ≥5 flipped sources; WACZ captures into OCFL. Proof: `LIVE_WIRING_REPORT.md` lists each source with fetch timestamp, capture digest, and claim count > 0. ⧗ **HG-09** any token set as env secret.
6. **P21.4** — full OKC run from live data: ingest → ER → reconcile (the 299-vs-190 contradiction stays visible) → API → exports (ODbL split) → `web/` build → J-1 traversal + dossier; deployed to **staging** (⧗ **HG-12** a host; default: static `web/dist` on any static host + API on one small VM/container with PG18). Proof: `FIRST_JURISDICTION_REPORT.md` with the acceptance-query outputs and Lighthouse/axe results from the staging URL.
7. **Public publish** — `PUBLICATION_CHECKLIST.md` all ticked: ⧗ **HG-01** legal home named in `docs/governance/`; ⧗ **HG-11** two named reviewers concur in writing (policy officer gate `test_policy_officer.py` semantics), takedown/corrections contacts live; ⧗ **HG-02** counsel disposition on ODbL 4.4(b) recorded (until then OSM-derived layer is served link-only/not exported). Then DNS → public.
8. **P21.5** — Zenodo deposit of the first export (⧗ HG-07), tiles, mirrors, degraded mode. **P21.6–P21.9** widen the surface (curation UI, contribution-back, Data Driven releases, Stage-5 pathway connectors) — not on the critical path to "live", on the path to "sustained".

Nothing above says TBD; the only unknowns are *dates* of the ⧗ human actions, each of which has a ticket that prepares everything up to the human edit.

## 7. Sizing, risks, and conscious tradeoffs

- **Closure was the overflow risk** and was split at planning time (Phase-4 review): P19.4 = the three spine seams; P19.5 = everything else + docs + the ACCEPTED list. Both are bounded by P19.2's `P19.4:S/M` tags; anything L is re-tagged to a P21 ticket by P19.2. P21.8/P21.9 were likewise split (Data Driven vs P17 pathways). `orchestrate-build` may still split further at run time and write it back.
- **P19.2 must be an independent context** (anti-bias rule): its Load list forbids reading the ledgers' self-assessments before forming per-id verdicts; `LEDGER_DEFERRALS.md` is consulted only afterwards as a checklist.
- **No base switch.** P20.3 merges nothing (operator rule); every ticket stacks on the previous branch. Squash-merge would be conflict-free but destroys one-commit-per-ticket history — the plan's recommended default is **merge commits, bottom-up**; the operator decides at HG-05 after the chain.
- **Docs-only tickets (P19.2, P20.1, P20.2) still end on `make check`** so the phase gate is uniform; they add a risk-register/traceability section rather than tests.
- **P21 order** puts persistence (P21.2) before live wiring (P21.3) so live claims land in real tables; if P21.2 is ACCEPTED-away, P21.3 proceeds unchanged.
- **No lettered tickets; no ticket beyond P21.9 is invented here.** New scope discovered by P19.2 lands as backlog rows in P20.1 and, if needed, as new `P22.x` tickets cut by a later planning pass — recorded, not guessed.

## 8. What the implementation model runs first

```
implement-spec spec=docs/tickets/P19.1__build-memory-and-hygiene.md live_verification=false
```
then, per `docs/tickets/00_MANIFEST.md` rows 47–63, the next file from the branch each ticket leaves checked out — or `orchestrate-build ledger=.agents/scratch/planning/sig-postbuild-build-ledger.md`.

## 9. Operator runbook — driving the whole plan end to end

The plan is executed in **four passes plus a steady state**. Nothing outside these passes exists; if it is not here it is in `BACKLOG.csv` (P20.1) by construction.

**9.0 Single-call mode (the operator's chosen mode).** One `orchestrate-build` invocation from a fresh session drives rows 47→63 with `subagent` dispatch and pauses **only** at SETUP, each human gate (ledger GATE PROTOCOL), real blocks, and CAPSTONE. Nothing in the run merges, tags, or pushes to `main`. If the session dies, paste the same prompt again — the build ledger is the only state and the loop resumes where it stopped. The exact prompt is in the build ledger's OPERATING MODE note and in `docs/tickets/00_MANIFEST.md` "How to drive".

**9.1 Forward pass (rows 47→63; by hand = 17 fresh sessions).** By hand: in each fresh session, on the branch the previous ticket left checked out, paste the ticket's own `Run:` line **verbatim** — the `live_verification` flag differs per ticket (`false` for the docs-only P19.1, P19.2, P20.1, P20.2, P21.1; `true` for P19.3, P19.4, P19.5, P20.3, P21.2–P21.9). Never merge between tickets; the PRs stack on `devin/p18-2-france-belgium`. The orchestrator does exactly this loop for you, with the ledger's SETUP note 0 overrides (main checkout as worktree, pinned base `1baf05f`, no sibling branch).

**9.2 Your inputs, keyed to the pass (in single-call mode the orchestrator asks you for exactly these, at these points; "skip" sends the ticket to the return pass):**

| When | Row | Your action | Where it is recorded |
|---|---|---|---|
| pause after P19.5 | 51 | Read `docs/build/CAPSTONE_CLOSURE.md` §(b); accept/reject each deviation (**HG-14**); P20.1 writes the signature | ledger GATE DECISIONS → `CAPSTONE_CLOSURE.md` §(e) |
| pause before P20.2 | 53 | A1–A8 tick/untick (**HG-13**); unticked = proposal only | ledger GATE DECISIONS → ticket gate block |
| — (no pause) | 54 | Nothing during the run. **After the chain** (or whenever you like): `sh docs/build/tools/merge_dryrun.sh`, then `INTEGRATION_PLAN.md` §(d) — merge bottom-up, tag `v0.1.0`, release (**HG-05**) | `docs/build/INTEGRATION_PLAN.md` |
| pause before P21.1 (and again before P21.3) | 55, 57 | Which sources to flip (**HG-03**) and outreach outcomes (**HG-04**). Realistic answer at P21.1: "skip — I'll read the packets first"; then at the P21.3 pause name the flipped sources; minimum for OKC: `okc_procurement, okc_council, okcpd_policy, ok_statute, osm_overpass` | ledger GATE DECISIONS; `sources.toml` via the ticket |
| pause before P21.3 | 57 | Export env tokens in the orchestrator's shell if you have them (**HG-09**): `SIG_MUCKROCK_TOKEN`, `SIG_DATA_GOV_KEY`; answer `provided: yes/no` | shell env only (never the ledger) |
| pause before P21.4 | 58 | Staging target (**HG-12**; local compose is fine); for *public*: legal home (**HG-01**), two reviewer roles + takedown contact (**HG-11**), ODbL counsel disposition (**HG-02**), Go-public | ledger GATE DECISIONS; `PUBLICATION_CHECKLIST.md` |
| pause before P21.5 | 59 | Zenodo sandbox token, object-store creds if any (**HG-07**, env); confirm A1 state | env + ledger GATE DECISIONS |
| pause before P21.7 | 61 | MapRoulette key + OE registration (**HG-08**, env); ≥5 participants scheduled? (**HG-10**) | env + ledger GATE DECISIONS |
| pause before P21.8 / P21.9 | 62–63 | Flip any newly packeted sources (**HG-03/04**) | ledger GATE DECISIONS |

**9.3 Return pass.** The build ledger's `RETURN PASS` table lists every ticket whose gate you answered "skip". Before CAPSTONE the orchestrator offers to re-run them (it sets `nextTicket` to that id; the re-run is a fresh worker on the ticket's own branch; ACs are idempotent and the conditional ACs now apply). By hand: re-run the ticket's `Run:` line. Order does not matter except P21.3 before P21.4 (live data feeds the OKC run). "Go public" (P21.4 step 7) is the last return-pass item and is a single human decision.

**9.4 Capstone of the new chain.** After row 63 (and the return pass), the orchestrator pauses for your go-ahead and runs the `CAPSTONE checklist`: independent gap analysis vs this memo §3/§5/§6 + `COVERAGE_MATRIX.csv`, closure on a `sig-postbuild-capstone` branch **stacked as one more PR (no merge)**, composed E2E = `sh docs/build/tools/run_okc.sh` on a clean machine + `tests/e2e` with 0 xfails not routed `P22+`. `projectStatus=DONE` only when that is green or its blocker is recorded. **Then you integrate:** `sh docs/build/tools/merge_dryrun.sh` → `INTEGRATION_PLAN.md` §(d) (merge #20…#64 bottom-up, tag `v0.1.0`, release).

**9.5 Completeness check (how you know nothing fell through).** Four mechanical assertions cover every tracked item; run them at the end and after every return pass:
1. `python docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv` → 668 (+ fold-backs) rows, no `PARTIAL/MISSING` routed to a ticket that has already run.
2. `python docs/build/tools/check_backlog.py` → `risk deferred rows N/N`, `ADR revisit triggers M/M`, `LD rows 90/90`, `duplicate sources 0`; then `grep -c 'status,open\|,open$' docs/build/BACKLOG.csv` — every remaining `open` row must have `landing ∈ {P22+, human-gate:HG-nn}`. Anything else is a miss.
3. `docs/build/OPERATIONAL_READINESS.md` §(d): every HG-01..14 is ticked or has a named owner + "what unblocks it".
4. T1–T16 (§5.1), §5 artifacts (§5.2), LD 90/90 (§5.3) are closed at planning time by this memo; P19.1 commits the evidence.

**9.6 After DONE — steady state and P22+.** (a) `BACKLOG.md` "P22+ unscheduled" is the only open-ended residue; when you want to schedule it, paste a planning prompt: *"Decompose `docs/build/BACKLOG.md` §P22+ (+ any `blockedOn` still open) into `docs/tickets/P22.x` per `_TEMPLATE.md`, base = `main`"* — the same `decompose-spec` → `orchestrate-build` pair. (b) Steady state = re-running `run_okc.sh` on new fetches, `keepalive.yml` monthly, a production Zenodo deposit per release (`sig-exports deposit` without `--sandbox`), and a second jurisdiction by cloning `run_okc.sh` (that is the first P22 candidate).
