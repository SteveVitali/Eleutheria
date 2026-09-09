# CAPSTONE_CLOSURE — the capstone's closure step (P19.5, CAPSTONE step 2 part 2)

The closure record for the SIG build's post-build capstone: the small/medium CODE gaps the whole-spec
gap analysis (`CAPSTONE_GAP_ANALYSIS.md` §(i)) routed to closure, the P08.1 documentation gaps, the
moved ER-over-PostgreSQL work (P19.4's size guard, ADR-059 §6), and — for the operator's signature
(GATE HG-14) — the **proposed** ACCEPTED-deviations list. P20.1 (backlog) and P20.2 (amendments)
read §(b) as the signed input.

> **Append-only (P1–P3).** This document sits beside the earlier build-memory docs; it edits none of
> them. `COVERAGE_MATRIX.csv` is the record of truth and was updated in place (its provenance note
> names P19.5 as a sanctioned writer); no historical ledger or report content was rewritten.

## (a) Closed items — LD / matrix id → change → test

Both P19.4's spine seams (recorded here for completeness) and P19.5's closures.

| LD / matrix id | ticket | what closed it | test |
|---|---|---|---|
| LD-F06b (SIG-INGEST-016/017) | P19.4 | `PgClaimSink` — connector claims persist to the PG spine, append-only, idempotent on `content_digest` | `tests/db/test_claim_sink.py`; `tests/e2e` S3 |
| LD-F06 (SIG-API-001/002, SIG-TIME-008) | P19.4 | `PgReadStore` — the read API served over PG, publication at the store boundary, as-of belief | `tests/api/test_store_pg.py`; `tests/e2e` S6 |
| **LD-F04** (SIG-IDENT-020/021/025/026) | **P19.5** | ER over PG: `sig-resolution match --dsn` reads org candidates + scores; additive `review_queue` sqitch (`review_item` + append-only `review_decision`); `PgReviewQueue`; `sig-resolution review decide --dsn` (one row/call, history on repeat). JSONL default unchanged. **Flips `tests/e2e` S4 `LD-F04` xfail → PASS.** | `tests/resolution/test_pg_backend.py`; `tests/e2e` S4 |
| **LD-F08 / LD-H09** (SIG-INGEST-048b, SIG-LIC-004/010) | **P19.5** | export gate honours `derivative_permitted`: `policy.licensing.assert_export_permitted` fails closed on `derivative_permitted=false` (reason string `derivative_permitted=false`); `partition_exportable` companion (reduce-only, §0.7) | `tests/unit/test_registry_export_gate.py` (`sm_alpr`/`deflock_app_repo`) |
| **LD-V12 / LD-H11** (SIG-PUB-017) | **P19.5** | jurisdiction-conditional web render: `web/src/lib/publication.ts` mirrors `adapter_publication_permitted`; `dossier.applyPublicationPolicy` withholds a public-employee name under FR-GDPR/BE-GDPR at build time; BCP-47 `lang` + localised titles; zero-JS budget preserved | `web/tests/e2e/jurisdiction.spec.ts` (+ `.nojs`); `web/tests/unit/publication.test.ts` |
| **LD-F15** (SIG-INGEST-021, §32) | **P19.5** | `inference` CLI wired: `coverage` / `access-paths` / `completeness` / `freshness` over the existing modules | `tests/inference/test_cli.py` |
| **LD-X05** (SIG-ENG-030/031) | **P19.5** | P08.1 documentation gap: ADR-060 (resolver, retro-fitted record) + risk register `## Phase 8 — Resolver (P08.1)` with RISK-P8-00a (ruleset drift → `check_ruleset`) and RISK-P8-00b (rationale quotability → live test) | `docs/adr/ADR-060-*.md`; `docs/risk_register.md`; `tests/reconcile/test_ruleset.py` |
| **LD-D14** (SIG-STORE-028/030/031, §11.16/§18.4) | **P19.5** | ADR-044 amended with `## Post-hoc hardening (4493b14, landed on P14.1's branch)` — reason_raw / rights_record / forbidden org-id columns / COMPLEMENTARY rationale, and why no separate ADR was written then | `docs/adr/ADR-044-*.md`; existing `tests/db` analytics suite |

ADR-061 records this ticket's decisions (gate placement, web render approach, ER-over-PG naming).

## (b) ACCEPTED deviations — PROPOSED for the operator's signature (GATE HG-14)

Every `MET-DIFFERENTLY` row in `COVERAGE_MATRIX.csv` is an **accepted deviation**: a requirement met by
a documented, sound alternative, never a silently loosened requirement (defining standard §3.1). This
table has **exactly one row per `MET-DIFFERENTLY` id**, so its row count equals the matrix's
MET-DIFFERENTLY count (**76**) — asserted in the PR body.

Two families dominate:

- **Process/governance charter principles (75 rows, routing `accepted`).** Charter / epistemic /
  publication-safety principles satisfied *structurally* — by the six-layer architecture, the
  executable policy package (P00.2), the governance/takedown/contributor-safety policies (P00.3), the
  prohibited-endpoint bar (P14.1), and the honest-rendering rules (P15.3) — rather than by an
  id-cited feature. The deviation is "satisfied by design + a named compensating control, not by a
  test-cited code path"; it is documented, not loosened.
- **The zero-JS static map (1 row, `SIG-UI-038`, ADR-051, routing `P20.2:spec`).** The served map is a
  zero-JS static PMTiles surface with a tabular equivalent, not the interactive MapLibre runtime the
  spec's stack section implies — a recorded deviation that keeps the zero-JS + perf gates green,
  pending the P20.2 spec amendment (A1).

The illustrative families the P19.5 ticket named — ADR-022 (no partitioning), ADR-030 (CLI curation
*pending P21.6*), ADR-037/038/039/054 (compute-on-read *pending P21.2 verdict*), ADR-051 (zero-JS map
*pending P20.2 A1*), ADR-023 (`evidence/` package) — are the reasoning behind these rows; the
authoritative, complete set is the 76 matrix rows enumerated below.

| matrix id | spec § | ADR / route | accepted-deviation reasoning |
|---|---|---|---|
| SIG-CHART-001 | 1.3 What SIG is not building | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-002 | 1.3 What SIG is not building | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-003 | 1.4 The core intellectual shift | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-004 | 1.4 The core intellectual shift | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-005 | 1.4 The core intellectual shift | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-006 | 2.1 The thirteen questions | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-007 | 2.1 The thirteen questions | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-011 | 3.1 The defining standard | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-012 | 3.2 The twelve data-quality principles | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-014 | 3.4 The federation principle | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-015 | 3.4 The federation principle | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-016 | 3.4 The federation principle | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-017 | 3.5 The six defining characteristics | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-018 | 3.6 Authority claim | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-019 | 3.6 Authority claim | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-020 | 3.7 No single source of truth | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-021 | 4.1 Goals | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-022 | 4.2 Non-goals | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-023 | 4.2 Non-goals | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-024 | 4.2 Non-goals | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-025 | 5.1 The initial wedge | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-026 | 5.1 The initial wedge | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-033 | 6. The federation compact | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-CHART-034 | 7. Success criteria | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-002 | 0.4 The execution model | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-005 | 0.6 Definition of Done | ADR-041 / accepted | Done needs automated evidence - enforced by make check + ticket ACs; this matrix records where automated evidence is missing |
| SIG-ENG-018 | 48. Testing | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-019 | 49. Observability | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-020 | 49. Observability | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-021 | 49. Observability | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-022 | 49. Observability | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-023 | 50. Deployment and cost | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-024 | 50. Deployment and cost | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-025 | 50. Deployment and cost | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-026 | 50. Deployment and cost | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-027 | 50. Deployment and cost | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-030 | 51.1 Philosophy | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-032 | Phase 11 — Flock portal layer **(ungated 2026-08-20)** | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-033 | 53. Risk register | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-035 | 54. Sequencing and parallelization | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-037 | A.4 Maintenance | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-ENG-038 | A.4 Maintenance | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-001 | 10.1 The evidence → claim chain | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-002 | 10.1 The evidence → claim chain | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-003 | 10.2 Source, EvidenceArtifact, and EvidenceCapture are three | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-004 | 10.2 Source, EvidenceArtifact, and EvidenceCapture are three | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-005 | 10.3 Field specifications | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-007 | 10.3 Field specifications | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-008 | 10.3 Field specifications | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-009 | 10.3 Field specifications | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-010 | 10.3 Field specifications | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-012 | 10.3 Field specifications | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-013 | 10.4 Source reliability `R` — a property of the publisher, n | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-016 | 10.4 Source reliability `R` — a property of the publisher, n | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-019 | 10.6 Integrity `I`, currency `C`, and the composed weight `W | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-022 | 10.6 Integrity `I`, currency `C`, and the composed weight `W | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-024 | 10.7 The confidence vocabulary: three orthogonal fields, not | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-026 | 10.8 Source dependence | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-027 | 10.8 Source dependence | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-EPIS-029 | 10.8 Source dependence | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-GOV-017 | 46.3 Anti-misuse, stated honestly | — / accepted | prohibition (MUST NOT build/publish X) enforced by scope + policy package (P00.2/P00.3) + prohibited-endpoint bar (P14.1); not cited by id |
| SIG-GOV-018 | 46.3 Anti-misuse, stated honestly | — / accepted | prohibition (MUST NOT build/publish X) enforced by scope + policy package (P00.2/P00.3) + prohibited-endpoint bar (P14.1); not cited by id |
| SIG-IDENT-014 | 14.4 Surrogate identity for organizations with no external i | — / accepted | org failing 43.4 publicity tests MUST NOT be created - enforced by identity-registry publicity gate; not cited by id |
| SIG-ONTO-005 | 8.3 The domain layers (what the sources look like) | — / accepted | architectural invariant (layer separation / reconciliation-not-authority) enforced by the six-layer model + schema; not cited by id |
| SIG-ONTO-006 | 8.3 The domain layers (what the sources look like) | — / accepted | architectural invariant (layer separation / reconciliation-not-authority) enforced by the six-layer model + schema; not cited by id |
| SIG-ONTO-008 | 8.5 The reconciliation core | — / accepted | architectural invariant (layer separation / reconciliation-not-authority) enforced by the six-layer model + schema; not cited by id |
| SIG-ONTO-009 | 8.5 The reconciliation core | — / accepted | architectural invariant (layer separation / reconciliation-not-authority) enforced by the six-layer model + schema; not cited by id |
| SIG-PUB-001 | 43.1 The bright line | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-PUB-003d | 43.2a SIG must never become the de-pseudonymisation join | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-PUB-006 | 43.3 Coordinate sensitivity | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-PUB-014 | 43.5 Candidate assets and RF-derived leads | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-PUB-014b | 43.6a The republisher absorbs the consequence — a worked pre | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-RECON-051 | 30.3 Prohibited inferences | — / accepted | MUST NOT infer person identity/location - enforced by inference guards + no such code path; not cited by id |
| SIG-SEC-002 | 44.3 Warrant-resistant architecture | — / accepted | charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id |
| SIG-TIME-003 | 9.2 The five temporal dimensions | — / accepted | T1 MUST NOT be inferred at ingestion - enforced by temporal model design; not cited by id |
| SIG-UI-038 | 40. Implementation stack and design system | ADR-051 / P20.2:spec | served map is zero-JS static PMTiles + tabular equivalent, not the interactive MapLibre runtime the spec implies (ADR-051, LD-F09/D11) |

## (c) Items routed to P21.x (unchanged from the gap analysis)

The gap analysis routed the remaining non-MET rows to later tickets; P19.5 does not change that routing
(it is out of scope here). Counts from `COVERAGE_MATRIX.csv`:

| route | rows | what |
|---|---|---|
| P21.1 | 2 | Stage-0 outreach (`SIG-CONTRIB-012/012a`) |
| P21.2 | 3 | annotation persistence (`SIG-EPIS-018`, `SIG-RECON-039/040`) — re-routed from `P19.4:S` by P19.5 |
| P21.3 | 2 | live-fetch robots/rights compliance (`SIG-INGEST-046b/046c`) |
| P21.4 | 4 | web reads the live export/API path (`SIG-PUB-007`, `SIG-UI-010` re-routed from `P19.4:M`; `SIG-PUB-015/016`) — `LD-V08` |
| P21.5 | 7 | deposits / succession / zero-cost start (`SIG-GOV-022/023/024`, `SIG-EVID-019`, `SIG-STORE-003/004/005`) |
| P21.6 | 1 | asset-promotion → curation service (`SIG-PUB-012`) |
| P21.7 | 1 | moderated usability study (`SIG-UI-001`) |
| P21.8 | 5 | Data Driven as a first-class source (`SIG-INGEST-043/043a-d`) |
| P21.9 | 8 | municipal-ordinance + coarse-international connector class (`SIG-INGEST-049…050`) |
| P20.1:backlog | 45 | claim-without-code drift + unverified framework/data-quality reqs |
| P20.2:spec | 1 | zero-JS map spec amendment (`SIG-UI-038`) |

**No P19.5 deliverable turned out L-sized** — every §(i) code gap was S/M and closed here; nothing was
re-routed to a P21 ticket for being oversized. (The 5 rows previously tagged `P19.4:*` were reviewed at
closure and re-routed to their real homes P21.2/P21.4 per the gap analysis §(i) note; they are AT-RISK
future work, not P19.5 code gaps.)

## (d) `tests/e2e` xfail count — before / after P19.5

| | xfails | which |
|---|---|---|
| before P19.5 (P19.4 tip) | 2 | `LD-F04` (ER not DB-wired), `LD-V08` (web reads fixtures) |
| after P19.5 | 1 | `LD-V08` → P21.4 |

`SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra`: 0 failed; the single remaining xfail carries an LD
id routed to a P21 ticket (`LD-V08` → P21.4).

## (e) Operator signature (GATE HG-14)

The ACCEPTED-deviations list in §(b) is **proposed**. The orchestrator pauses after this ticket and
presents §(b) to the operator; P20.1 writes the signature here and turns any rejected items into
backlog rows. This ticket does not tick this line.

- [ ] Operator has reviewed §(b) and accepts the listed deviations (or the exceptions are recorded in
  the build ledger `GATE DECISIONS`). — **pending operator (HG-14); not ticked by P19.5**
