# SIG build manifest — the ticket chain

This directory is the **execution runbook** for building SIG (Surveillance Infrastructure Graph)
as a chain of **46 reviewable PRs**. Each `PXX[.Y]__*.md` file is a self-contained `implement-spec`
contract derived from `docs/2_canonical_design_spec.md` (Part X phases).

> **These ticket docs are a derived build artifact.** They *cite* canonical §§; they do not copy the
> design. To change a requirement, amend `docs/2_canonical_design_spec.md` via an ADR (SIG-ENG-003),
> then update the affected ticket's Load/AC lines — never fork the design into a ticket file.

> **Committed build memory (build-memory v2, P22.3 / ADR-073).** This directory is the committed
> **contract record**; the committed **machine state** is `docs/build/LEDGER.md` (CURRENT STATE, GATE
> DECISIONS, RETURN PASS, PHASE LOG — no longer gitignored under `.agents/scratch/`), the per-ticket run
> ledgers are `docs/build/runs/<ID>.md`, PR bodies `docs/build/pr/<ID>.md`, and the durable build
> memory is `docs/build/` (see `docs/build/README.md`). The layout is validated by
> `scripts/docs/check-build-memory.sh .` (in `make docs-check`).

> **Deferrals companion.** `docs/tickets/DEFERRALS.md` is the append-only register of owed obligations
> (read it first every run; a deferral not in the file did not happen). It cites `docs/build/BACKLOG.csv`
> for normalized debt.

`companions: DEFERRALS.md, _TEMPLATE.md`

## How to build (stacked PR chain)

Each ticket forks from **whatever branch is currently checked out** and opens a PR based on it, so the
PRs **stack** — you do NOT need to merge one before starting the next.

```
# --- first ticket only: start from main ---
git checkout main
implement-spec  spec=docs/tickets/P00.1__repo-skeleton.md      # creates branch p00-1, PR base = main

# --- every subsequent ticket, in a fresh session ---
# stay on the branch the previous ticket left checked out (do NOT switch back to main),
# then just run the next file — its PR stacks on the previous ticket's branch:
implement-spec  spec=docs/tickets/P00.2__policy-as-code.md     # PR base = p00-1
implement-spec  spec=docs/tickets/P00.3__governance-policies.md # PR base = p00-2
# … straight down the table.
```

**The prompt pattern in each fresh session is just:** `implement-spec spec=docs/tickets/<the next file>`
— no `base_branch` argument (it defaults to the current checkout). The only rules: (1) go in table
order; (2) between tickets, stay on the previous ticket's branch so the next one stacks on it. Merge the
stack bottom-up at the end (or progressively, rebasing the rest).

> These ticket docs are **committed** as the build's contract record (decision 2026-09-08, ledger T4 /
> ADR-058); P19+ tickets are appended in table order.

Language is **Python** (TypeScript confined to `web/`), per SIG-ENG-010.

## Human prerequisites (do before / alongside P00.x — not code tickets)
- **Stage 0 outreach** to the 19 federation-compact projects (§35.1); record outcomes incl. `no_response`. P00.4 consumes them.
- **Legal home** identified (SIG-GOV-012).

## The chain

| # | Ticket file | Phase | Scope |
|---|---|---|---|
| 1 | `P00.1__repo-skeleton.md` | 0 | uv monorepo, §47 layout, CI, licence headers |
| 2 | `P00.2__policy-as-code.md` | 0 | Executable policy (crawler/licence/publication/threat) as tested code + ADR-001..012 + stack ADRs |
| 3 | `P00.3__governance-policies.md` | 0 | Prose governance: takedown/corrections/suppression, CoC, anti-misuse statement, contributor safety |
| 4 | `P00.4__source-registry.md` | 0 | Source registry seeded; rights records, SPDX, ingestion_permitted gate |
| 5 | `P01.1__ontology-as-code.md` | 1 | LinkML ontology + SKOS vocabularies + generators + generalization suite |
| 6 | `P02.1__claim-spine.md` | 2 | Claim/evidence schema L0–L3, append-only, resolution table, RLS |
| 7 | `P02.2__evidence-store.md` | 2 | OCFL evidence store, content addressing, capture pipeline, tiers/sealed |
| 8 | `P02.3__temporal-provenance.md` | 2 | EDTF, as-of functions, temporal invariants, PROV-O, lineage |
| 9 | `P03.1__identity-registries.md` | 3 | Jurisdiction + org registries, geometry, temporal identity |
| 10 | `P03.2__deterministic-er.md` | 3 | Crosswalk, normalize_org_name, cascade 0–3, public-ID lifecycle |
| 11 | `P04.1__connector-framework.md` | 4 | 8-stage framework, rate-limit/robots, licence gate, replay, shadow mode |
| 12 | `P04.2__osm-connector.md` | 4 | osm connector + separate ODbL asset table |
| 13 | `P04.3__atlas-connector.md` | 4 | atlas (EFF) connector |
| 14 | `P05.1__probabilistic-er.md` | 5 | Splink matcher, blocking, gold set, tiers 4–5 to review, cluster alerts |
| 15 | `P05.2__curation-ui.md` | 5 | Curation UI + review queue + LLM-to-review scaffolding |
| 16 | `P06.1__vertical-slice.md` | 6 | **HARD GATE** — one jurisdiction end-to-end (J-1) + retrospective |
| 17 | `P07.1__parsing-stack.md` | 7 | Parsing stack, locators, file classification |
| 18 | `P07.2__records-connectors.md` | 7 | Records connectors + RecordsRequest |
| 19 | `P07.3__procurement-connectors.md` | 7 | Procurement + cooperative/federal + FundingInstrument + agenda registry |
| 20 | `P08.1__resolver.md` | 8 | Resolver, ruleset-as-data, four axes, ambiguity test, rationales |
| 21 | `P08.2__reconciliation-workflows.md` | 8 | The §29 reconciliation workflows (**owns §29.3/§29.7 sharing+snapshot logic**) |
| 22 | `P08.3__contradiction-object.md` | 8 | Contradiction as a first-class entity + lifecycle |
| 23 | `P09.1__coverage.md` | 9 | Coverage, completeness, negative space |
| 24 | `P10.1__task-engine.md` | 10 | Detector DSL, lifecycle, dispositions, geo queues, anti-abuse, registry |
| 25 | `P10.2__detector-catalog.md` | 10 | The §33.2 task catalog (all 34 detectors) + contradiction→task mapping |
| 26 | `P10.3__records-request-gen.md` | 10 | Records-request generation + statute templates |
| 27 | `P11.1__flock-portal.md` | 11 | `flock_portal` API connector (compartment, snapshot diff, backfill, fallbacks) |
| 28 | `P11.2__audit-structural.md` | 11 | `audit_structural` connector (Camera Count, ***≠empty, SharedNetworks, aggregates-only) |
| 29 | `P12.1__usage-analytics.md` | 12 | Usage aggregates + analytics boundary + small-cell suppression |
| 30 | `P12.2__network-inference.md` | 12 | Access edges (3 types) + access-path closure |
| 31 | `P13.1__accountability.md` | 13 | AccountabilityEvent + LegalProceeding + epistemic_status + connector |
| 32 | `P13.2__policy-legal.md` | 13 | Policy + LegalInstrument + policy/config divergence |
| 33 | `P14.1__public-api.md` | 14 | Read API, resolution envelope, as-of, dereferenceable IDs, /changes |
| 34 | `P14.2__exports.md` | 14 | Exports + licence computation + ODbL split + crosswalk + Zenodo |
| 35 | `P15.1__web-shell.md` | 15 | Astro shell + epistemic visual language + a11y/no-JS + citation |
| 36 | `P15.2__local-dossier.md` | 15 | Local dossier + print/PDF + "what we don't know" (production SIG-UI-010…015) |
| 37 | `P15.3__map-network.md` | 15 | Infrastructure map + network explorer (MapLibre) |
| 38 | `P15.4__watch-evidence.md` | 15 | Procurement/renewal watch + evidence recommender + evidence viewer |
| 39 | `P15.5__corrections-methodology.md` | 15 | Research queue + corrections log + methodology/coverage + editorial standards |
| 40 | `P16.1__contributors.md` | 16 | Contributor system (tiers, safety, L0 entry, revert, anti-poisoning) |
| 41 | `P16.2__contribution-back.md` | 16 | Contribution-back (OSM human-mediated, organised-editing page, hashtag) |
| 42 | `P17.1__broader-federation-rtcc.md` | 17 | Private-camera federation + RTCC integration |
| 43 | `P17.2__broader-fr-css-forensics.md` | 17 | Facial recognition + cell-site simulators + mobile forensics |
| 44 | `P17.3__broader-acoustic-drone-loc.md` | 17 | Gunshot detection + drones + commercial location data |
| 45 | `P18.1__international-framework.md` | 18 | Jurisdiction adapter framework + i18n + jurisdiction-conditional publication |
| 46 | `P18.2__france-belgium.md` | 18 | France/Belgium connectors + OSM-import study |

### Post-build chain (rows 47–65) — committed from here on

Planned 2026-09-08 after PR #46 by the planning sessions recorded in `docs/build/PLANNING_LEDGER.md`
(the plan-for-the-plan), `docs/build/DECISION_MEMO.md` (the sequence and rationale), `BUILD_INDEX.md`,
`LEDGER_DEFERRALS.md` and `SCOPING_NUMBERS.md` (the evidence). Until P19.1 lands those files are at
`.agents/scratch/planning/`. Three rules differ from rows 1–46:

1. **These ticket files are committed** (decision T4/ADR-058, executed by P19.1) — `docs/tickets/` is the
   build's contract record, no longer derived scaffolding. Every later ticket is appended here in order.
2. **Gates.** Some tickets carry a `Gate status` header block (`HG-nn`, see `DECISION_MEMO.md` §4): work a
   human must do (rights flips, legal home, accounts, counsel, the merge "go"). The operator ticks the block
   *before* the run. Unticked ⇒ the ticket still does everything up to the gate, opens its PR, and reports
   **complete with gate HG-nn pending** (it is added to the build ledger's RETURN PASS table — never `blockedOn`,
   which is reserved for real blocks); the chain never waits. Re-running the same ticket file after ticking is idempotent.
3. **No ticket merges anything.** All rows 47–65 stack on `devin/p18-2-france-belgium` (PRs #47–#63 on top of
   #20–#46). Integration is an **operator action after the chain**: P20.3 writes the dry-run script and the exact
   bottom-up merge + `v0.1.0` tag procedure (`docs/build/INTEGRATION_PLAN.md` §(d)); the operator runs it.
4. **Gates pause the orchestrator.** Under `orchestrate-build`, the loop STOPS before every gated ticket, presents
   the gate block, and records the operator's answers in the **committed** `docs/build/LEDGER.md` `GATE DECISIONS`
   table (no longer gitignored — build-memory v2, P22.3); the worker copies them into the ticket header in its
   first commit. "Skip for now" is a valid answer — the ticket then runs ungated and is listed in the ledger's
   RETURN PASS table (and seeded into `docs/tickets/DEFERRALS.md`) for a later re-run.

**How to drive it end to end:** one resumable `orchestrate-build` call (prompt in the build ledger's OPERATING MODE
note, now committed at `docs/build/LEDGER.md`) that pauses only at SETUP, human gates, real blocks and
CAPSTONE — then the operator integrates per `docs/build/INTEGRATION_PLAN.md`. Details: `docs/build/reports/DECISION_MEMO.md` §9. By hand,
use each ticket's own `Run:` line verbatim — the `live_verification` flag differs per ticket.

Phases 19–22 are not in the spec's Part X; 19 = capstone & consolidation (orchestrate-build CAPSTONE run
retroactively), 20 = reconciliation & release, 21 = operationalization toward one real jurisdiction live
(Oklahoma City, the P06.1 slice), 22 = documentation (human- and agent-facing docs converged on the finished code — last, on purpose). Human prerequisites for Phase 21 are the `HG-` gates, listed with their
"what unblocks it" in `docs/build/OPERATIONAL_READINESS.md` (P20.1).

| # | Ticket file | Phase | Scope | Gate |
|---|---|---|---|---|
| 47 | `P19.1__build-memory-and-hygiene.md` | 19 | Commit tickets + planning artifacts to `docs/build/`; unify `.agents/scratch/`; `AGENTS.md`; fix LD-X09/X10/X11; ADR-058 | — |
| 48 | `P19.2__capstone-gap-analysis.md` | 19 | **Independent fresh context.** 668-row `COVERAGE_MATRIX.csv` (MET / MET-DIFFERENTLY / PARTIAL / MISSING / AT-RISK-INTEGRATION) + seam hunt + routing; no code | — |
| 49 | `P19.3__capstone-composed-verification.md` | 19 | Composed E2E over real PG18+PostGIS/OCFL/API/exports/web as `tests/e2e/`; retro 5.3 for 28 tickets; `COMPOSED_E2E_REPORT.md` | Docker |
| 50 | `P19.4__capstone-spine-wiring.md` | 19 | `PgClaimSink`, `PgReadStore` (+ `_compute_on_read` seam), ER + review queue over PG, `python -m reconcile resolve --dsn`; flips xfails LD-F06b/F06/F04 | — |
| 51 | `P19.5__capstone-gap-closure.md` | 19 | `derivative_permitted` export gate, jurisdiction-conditional web render, `inference` CLI, remaining S/M rows, P08.1 ADR/§53, ADR-044 note; `CAPSTONE_CLOSURE.md` + ACCEPTED list | HG-14 (orchestrator pauses **after** this ticket; operator signs the ACCEPTED list; P20.1 records it) |
| 52 | `P20.1__backlog-and-operational-readiness.md` | 20 | One `BACKLOG.csv/.md` (118 RISK deferred rows + 57 ADR triggers + 90 LD rows → one `BL-` each); `OPERATIONAL_READINESS.md` with the OKC critical path | — |
| 53 | `P20.2__spec-reconciliation.md` | 20 | `TICKET_VS_SPEC.md`; ADR-001..061 dispositions; Appendix F/G fixes; approved fold-backs via `spec_src` → `BUILD.sh`; ADR-062 | HG-13 (normative amendments ticked) |
| 54 | `P20.3__integration-release.md` | 20 | **No merging.** `merge_dryrun.sh` + `INTEGRATION_PLAN.md` (operator's bottom-up merge + `v0.1.0` tag procedure); `CI_STATUS.md`; version bump to 0.1.0; release notes draft; README/CHANGELOG/CONTRIBUTING refresh | — (HG-05 is the operator's post-chain action) |
| 55 | `P21.1__rights-review-and-registry-completion.md` | 21 | 6 OKC registry rows; 27 rights packets (OKC set + 18 flip-ready + `usaspending`); review-metadata rule; `review-status` CLI; Stage-0 outreach record | HG-03, HG-04 (human flips/outcomes) |
| 56 | `P21.2__persist-annotation-layer.md` | 21 | Contradiction/coverage/task/contributor/inference rows in PG; API reads rows; ADR-037/038/039/054 revisited | decision-gated (capstone ACCEPTED list, A5) |
| 57 | `P21.3__live-connector-wiring.md` | 21 | `HttpxTransport` + `OcflCaptureStore` + `sig-connectors run --mode live` (refuses un-reviewed sources); first real fetches; `LIVE_WIRING_REPORT.md` | HG-03 (≥1 flipped), HG-09 (tokens via env) |
| 58 | `P21.4__first-jurisdiction-ingest-and-publish.md` | 21 | `sig-ops` compose runtime; export-backed `web/`; the OKC run (J-1 + Q-1…13 against the live API); staging; `PUBLICATION_CHECKLIST.md`; `FIRST_JURISDICTION_REPORT.md` | HG-12 staging; HG-01, HG-11, HG-02 for public |
| 59 | `P21.5__infra-deposit-and-tiles.md` | 21 | Zenodo (sandbox) deposit + DOI; object store/CDN + egress alarm + torrents; tile generation; MapLibre island iff A1 unticked; mirrors/SWH; degraded-mode keepalive | HG-07, HG-12 |
| 60 | `P21.6__curation-web-ui.md` | 21 | Authenticated curation service + `/curate/**` pages (ER queue, dispositions, L0 entry, revert); LLM-to-review as suggestions only | decision-gated (ADR-030 verdict, A6) |
| 61 | `P21.7__contribution-back-live.md` | 21 | MapRoulette client, OSM changeset feed → `LeverageLedger`, Organised Editing record, usability study protocol + results | HG-08, HG-10 |
| 62 | `P21.8__data-driven-and-coarse-international.md` | 21 | EFF/MuckRock Data Driven releases connector (`SIG-INGEST-043*`, `044`) with versioned re-ingest; coarse-international content path | HG-03/HG-04 per source |
| 63 | `P21.9__stage5-pathway-connectors.md` | 21 | Stage-5 connectors for the P17 pathways (RTCC/federation, FR/CSS/forensics, acoustic/drone/location) + the ADR-033-deferred parser layers | HG-03/HG-04 per source |
| 64 | `P22.1__repo-docs-refresh.md` | 22 | Human-facing docs: full `refresh-repo-docs` audit of README/CONTRIBUTING/CHANGELOG/governance/studies against the finished code; generated/frozen/historical docs report-only; `docs/README.md` map; `DOCS_REFRESH_REPORT.md`; vendored detector | — |
| 65 | `P22.2__agent-docs-refresh.md` | 22 | Agent-facing docs: `agent-docs` refresh (or clean-slate bootstrap) of the `AGENTS.md` hierarchy + `CLAUDE.md`; `make docs-check` + CI docs step; ADR-072 | option: clean slate (asked at the pause) |
| 66 | `P22.3__build-memory-v2-migration.md` | 22 | **Build-memory v2 migration (ADR-073).** Retire `.agents/scratch/`; commit the build's memory under `docs/build/` in the v2 layout; convert the machine ledger to `docs/build/LEDGER.md`; complete `BUILD_INDEX.md` rows 47–66; seed `docs/tickets/DEFERRALS.md`; regenerate the ADR index; vendor `check-build-memory.sh` into `make docs-check` | — |

### Round 2 — capstone-over-capstone + reconciliation tail (rows 67–73, build-memory v2)

> **Round 2 (instantiated by P22.3 from the v2 tail templates).** The round-1 capstone (PR #68,
> `devin/sig-postbuild-capstone`) already verified the composed build (`make check` 2718 passed, 0 failed,
> 0 xfailed; `tests/e2e` 16 passed; `run_okc.sh` 8/8). These tail rows are therefore a **delta over the
> completed Round 1**, not a re-run of that verification: their `Load` lines point at the existing
> `docs/build/reports/CAPSTONE_VERIFICATION.md`, `CAPSTONE_CLOSURE.md`, `COVERAGE_MATRIX.csv`, and the
> P19.x/P20.x reports. `DOC.1`/`DOC.2` are **omitted** because P22.1/P22.2 already ran (spec Appendix B item 6).
> Not started — `docs/build/LEDGER.md` `nextTicket: P23.1`.

| # | Ticket file | Phase | Scope | Gate |
|---|---|---|---|---|
| 67 | `P23.1__capstone-gap-analysis.md` | 23 | **CAP.1** — Round-2 gap-analysis delta (independent fresh context): re-classify only what changed since PR #68 into `COVERAGE_MATRIX.csv`; seam re-hunt; `CAPSTONE_GAP_ANALYSIS.md` addendum | — |
| 68 | `P23.2__capstone-composed-verification.md` | 23 | **CAP.2** — re-run the composed build as one unit only if the delta touched a seam; else cite PR #68's green composed run; `COMPOSED_E2E_REPORT.md` addendum | — (Docker if re-run) |
| 69 | `P23.3__capstone-closure.md` | 23 | **CAP.3** — close any newly-routed Round-2 gaps on a capstone branch; append the ACCEPTED-deviations delta to `CAPSTONE_CLOSURE.md` | — |
| 70 | `P23.4__gate-accept.md` | 23 | **GATE-ACCEPT** (marker) — operator signs the Round-2 accepted-deviations delta (nothing new expected) | operator signature |
| 71 | `P23.5__backlog-and-readiness.md` | 23 | **REC.1** — refresh `BACKLOG.csv`/`BACKLOG.md`/`OPERATIONAL_READINESS.md` against the current DEFERRALS + open findings | — |
| 72 | `P23.6__spec-reconciliation.md` | 23 | **REC.2** — refresh `TICKET_VS_SPEC.md`/`SPEC_RECONCILIATION_PLAN.md`; fold back any Round-2 amendments via `spec_src` → `BUILD.sh` | HG-13 (if any amendment) |
| 73 | `P23.7__integration-plan.md` | 23 | **REC.3** — refresh `INTEGRATION_PLAN.md` (PR graph now #47–#68 + this round), read-only merge dry-run, release-notes delta | — |

## Phase gates & special points
- **Integration is an operator action after the chain** (`docs/build/INTEGRATION_PLAN.md` §(d)); no ticket merges PRs; all rows 47–65 stack on `devin/p18-2-france-belgium`. P20.3 writes the read-only `merge_dryrun.sh` + the bottom-up merge + `v0.1.0` tag/release procedure and bumps versions to `0.1.0`, but merges/tags nothing (HG-05 is the post-chain operator action).
- **P06.1 is a hard synchronization barrier** (§54): its written retrospective MUST be committed before any ticket below it starts.
- Every ticket ends on the universal phase gate (§51.3): CI green incl. data-quality checks, tests for new requirements, ADRs for deviations, traceability + risk register updated.
- **P11.1 and P11.2 (Flock) depend on an external source** and must never block P12+ (SIG-ENG-035); if the source is unavailable, continue down the list and return.
- **Ownership note:** the §29.3/§29.7 sharing-edge + snapshot-diff reconciliation logic is owned by **P08.2**; P11.1, P11.2, and P12.2 *consume* it and must not re-implement it.
- **Post-build chain (47–63):** P19.2 runs in an **independent fresh context** (anti-bias rule of the capstone) and must not read ledger self-assessments before forming verdicts. P19.3 requires Docker and never fabricates green (blocked seams are `xfail`s tagged with an `LD-` id). P19.5's ACCEPTED-deviations list is signed by the operator at the orchestrator pause after P19.5 (HG-14) and recorded by P20.1. No ticket merges PRs; the operator integrates after the chain per `INTEGRATION_PLAN.md`. Gated P21 tickets are complete without their gate (they ship packets/plans/stubs and are listed in the build ledger's RETURN PASS table — not `blockedOn`); re-run the same file once the operator ticks the block.
- **Requirement-id → ticket index for rows 47–65:** `docs/build/COVERAGE_MATRIX.csv` (P19.2) columns `owning_tickets` and `routing`; rows 1–46 stamp ids in their own files and PR bodies.
- **Ownership notes (post-build):** `PgClaimSink`/`PgReadStore` names, the `_compute_on_read` seam and the `--dsn` CLI convention — **P19.4**; `CAPSTONE_CLOSURE.md` + the ACCEPTED list — **P19.5**; `BL-nnn` ids and the `landing` enum — **P20.1**; fold-back requirement ids and Appendix F ↔ `docs/adr/` equivalence — **P20.2**; the review-metadata flip rule and packet format — **P21.1**; `db.annotations` repositories — **P21.2**; `sig-connectors run` and the fetch-record format — **P21.3**; `ops/docker-compose.yml`, `sig-ops`, `web/src/lib/data.ts` — **P21.4**.

## Spec amendments applied
- **Task-type count reconciled (2026-08-26):** §33.2 enumerates **34** task types; the Phase-10 Part X AC said "32". Fixed at source (`spec_src/96_partX_s51to54_plan.md`) and rebuilt (`sh docs/research/_meta/spec_src/BUILD.sh`); the canonical spec now reads "All 34 task types". P10.2 covers all 34.
- **P20.2 spec reconciliation (2026-09-09, gate HG-13, ADR-062):** all eight amendments ticked and applied at `spec_src` → `BUILD.sh` → the canonical spec (byte-clean; `check_spec_src.py` exit 0):
  - **A1** (§40, ADR-018/051): zero-JS static map is the conforming default (SIG-UI-038); interactive MapLibre is an optional progressive-enhancement island — new **SIG-UI-047 (MAY)**.
  - **A2** (§32.1/§33, ADR-041): residency barrier recorded as `absence_kind = not_researched`; the closed absence vocabulary made binding.
  - **A3** (§11.2, ADR-056): `canonical_name` is a **scalar**; competing names remain claims.
  - **A4** (§16.2 #6, ADR-022): claim partitioning is **MAY**/deferred and MUST keep the `claim_id` PK/FK contract.
  - **A5** (§31/§32/§33, ADR-037/038/039): `Contradiction`/`CoverageRecord`/research tasks MAY be **compute-on-read**; persistence deferred to Phase 21.
  - **A6** (§34/§39.7, ADR-030): **CLI + JSONL** curation/review queue conforming for Phase 5; web surface deferred to Phase 21.
  - **A7** (§47, ADR-023): `evidence/` added to the SIG-ENG-012 layout.
  - **A8**: no further `P20.2:spec`-routed normative item exists (empty set).
  - **Fold-back ids (N=3):** SIG-UI-047, **SIG-EVID-020** (evidence blob-vs-capture dedup, ADR-023), **SIG-ENG-039** (Appendix F ↔ `docs/adr/` equivalence in CI, ADR-062). Spec id count 668 → **671**.
  - **Non-normative:** Appendix F rebuilt to repository ADR numbering (ADR-001…062; fixes LD-X04/LD-D03); `docs/adr/README.md` gained ADR-056/057 index rows; Appendix G.5 added; §52 "32"→"34" task types confirmed.
  - **Follow-up rule (SIG-ENG-039):** any PR that adds an ADR MUST add its Appendix F row in the same PR; a PR that adds a requirement id MUST add its `spec_src` paragraph and Appendix F/coverage rows in the same PR. Enforced by `docs/build/tools/check_spec_src.py`.
- **Build memory committed under `docs/build/` (2026-09-09, P22.3, ADR-073):** supersedes ADR-058 §3 (the `.agents/scratch/` gitignored-scratch home). No `spec_src` change and no new requirement id — a build-memory/layout decision, recorded as ADR-073 (Appendix F row added; `check_spec_src.py` exit 0, 72 ADRs).

## Plan extensions (append-only: inserts, splits, rounds)
- **2026-09-08 — SPLIT** P19.4 (capstone-spine-wiring): the ER-over-PG / LD-F04 deliverable moved into P19.5 per the ticket's size guard; both files kept; recorded in the ledger PHASE LOG + ADR-059 §6.
- **2026-09-08 — SPLIT** at planning: P21.8 split out of the original Phase-21 plan (data-driven + coarse-international as its own unit).
- **2026-09-08 — INSERT** P20.4 `fix-ci-e2e-webbuild` (row 54.5, inline spec, no ticket file): operator chose "fix CI-RED-01 now"; landed as PR #55.
- **2026-09-09 — INSERT** P22.0 plan-extension commit (PR #57): committed the operator's `00_MANIFEST.md` rows 64–65 edit + the two untracked `P22.1`/`P22.2` ticket files so the tree was clean; extended the chain to row 65, CAPSTONE after P22.2.
- **2026-09-09 — INSERT** P22.1 `repo-docs-refresh` (row 64) and P22.2 `agent-docs-refresh` (row 65): operator documentation pass over the finished build.
- **2026-09-09 — ROUND 1 CAPSTONE** ran as PR #68 (`devin/sig-postbuild-capstone` @ `625d802`, stacked on P22.2/PR#67; merges nothing): closed MATRIX-INT-01, APPENDIX-F-01, CHECK-BACKLOG-01; composed E2E green; `projectStatus: DONE`.
- **2026-09-09 — INSERT + ROUND 2** P22.3 `build-memory-v2-migration` (row 66, ADR-073): migrated the build memory to the v2 layout and instantiated the Round-2 tail rows 67–73 (`P23.1…P23.7`) from the v2 templates as a delta over the completed Round 1 (`DOC.*` omitted; `nextTicket: P23.1`).
