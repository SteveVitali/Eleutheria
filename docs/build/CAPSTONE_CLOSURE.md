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

### (b) Addendum — 2026, sig-postbuild capstone verification (append-only; the signed table above is unchanged)

The signed §(b) table above (76 rows) is **not rewritten**. This addendum records a single
post-signature reconciliation made during the `sig-postbuild` capstone verification, when the
coverage-matrix integrity checker (`check_coverage_matrix.py`) flagged two rows carrying
enum values outside the checker's vocabulary (a MATRIX-INT gap, not a coverage regression):

- **`SIG-STORE-003`** — verdict was the invalid literal `COVERED`. The requirement ("start,
  ingest, resolve, serve with zero non-PostGIS extensions", §15.2) is proven by the zero-cost
  degraded rebuild + monthly-keepalive fail-loud test (`tests/ops/test_degraded.py`), so it is now
  **`MET`** (routing `—`), a straight test-cited pass — **not** a MET-DIFFERENTLY deviation. It adds
  nothing to the accepted-deviation set.
- **`SIG-UI-047`** — class was the invalid literal `deferred(A1-ticked)` and verdict `MISSING`. This
  is the **same** zero-JS static-map decision already accepted as `SIG-UI-038` in the signed table
  (A1 ticked → the zero-JS static PMTiles map is the conforming default; the MapLibre island is not
  built by decision, ADR-051/ADR-067). It is now recorded consistently as `class=deviated(ADR)`,
  `verdict=MET-DIFFERENTLY`, `routing=P20.2:spec` — the correct enum for that already-accepted
  deviation.

**Effect on the count:** the matrix `MET-DIFFERENTLY` count moves **76 → 77** (SIG-UI-047 crosses
`MISSING → MET-DIFFERENTLY`; SIG-STORE-003 becomes `MET`, not MET-DIFFERENTLY). The new row is the
same already-signed zero-JS-map deviation reasoning under its second fold-back id (`SIG-UI-047`
alongside `SIG-UI-038`), so **no new class of deviation is introduced** and the operator's HG-14
acceptance of Family 2 (zero-JS static map, ADR-051, `P20.2:spec`) already covers it. `MISSING`
moves 10 → 9. `check_coverage_matrix.py` now exits 0 (`671 rows OK`).

### (b) Addendum 2 — 2026-09-13, Round 3–4 readiness delta (P24.8 / REC.1; append-only)

The go-live (Round 3) and productionize (Round 4) tickets introduced **no new
accepted deviation**: the `COVERAGE_MATRIX.csv` `MET-DIFFERENTLY` count is **77**,
unchanged since the addendum above (verified by `grep -c MET-DIFFERENTLY` this
run). The signed §(b) table is not rewritten.

What Rounds 3–4 did produce, none of which is a `MET-DIFFERENTLY` deviation:

- **New spec requirements closed straight** — `SIG-INGEST-049`/`049a`–`049f` +
  `SIG-INGEST-050` moved `PARTIAL`/`MISSING` → **`MET`** with test evidence
  (P24.7 / CCOPS.1 / ADR-080), retiring OPEN FINDING P17-FLIP-01. Straight
  passes add nothing to this list.
- **Owned engineering decisions** the spec delegated to an ADR — ADR-074 (OKC
  document connectors), ADR-075 (e2-micro GCE vs Cloud SQL — DEPLOY.1's own
  "pick one" clause), ADR-076 (GitHub-Actions cron vs Prefect/Dagster —
  SCHED.1's "cron first" allowance), ADR-077 (record-first notifier), ADR-078
  (CI composed job), ADR-079 (France adapter dispositions), ADR-080 (CCOPS
  connector shape). These are decisions *within* spec latitude, not deviations
  from a requirement.
- **Deferred obligations** — every credentialed/gated remainder is a
  `DEFERRALS.md` `D-*` row citing exactly one `BL-*` backlog home
  (`OPERATIONAL_READINESS.md` carries the full map); none loosens a spec MUST.

**Net for GATE-ACCEPT (P24.9):** the ACCEPTED list the operator signs is the
signed 76-row §(b) table **plus the one addendum row** (`SIG-UI-047`, the same
already-accepted zero-JS-map deviation under its second fold-back id) —
**77 rows, 0 new since the capstone addendum.** No new deviation requires
signature beyond what HG-14 already accepted.

### Addendum 2 — operator signature (GATE-ACCEPT / P24.9)

**Confirmed: no change — Operator (project maintainer), 2026-09-13.** The operator reviewed the
Round 3–4 go-live accepted-deviations delta above and confirmed there is **no change** to the
accepted-deviations list: the 77-row ACCEPTED list (the signed 76-row §(b) table + the SIG-UI-047
fold-back, both accepted at HG-14) is current and accepted; **0 new deviations, 0 sent back to
closure.** Recorded in `docs/build/LEDGER.md § GATE DECISIONS` (P24.9 / GATE-ACCEPT) and
`docs/build/readouts/GATE-ACCEPT.md`. The go-live round (Rounds 3–4 against
`docs/3_sig_golive_spec.md`) is **DONE** (`projectStatus: DONE`, BM-TAIL-03).

- [x] Operator has reviewed the Round 3–4 delta and confirms the ACCEPTED list is unchanged
  (recorded in the build ledger `GATE DECISIONS`, P24.9). — **CONFIRMED "no change" (GATE-ACCEPT), 2026-09-13**

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

The ACCEPTED-deviations list in §(b) is **proposed**. The orchestrator paused after P19.5 and
presented §(b) to the operator; the decision is recorded in the build ledger `GATE DECISIONS`
(HG-14, 2026-09-08) and is transcribed here by P20.1.

**Signed: Operator (project maintainer), 2026-09-08 — full 76-row ACCEPTED-deviations list accepted; 0 rejected.**

- Family 1 (75 charter/process/epistemic/publication-safety principles, routing `accepted`) — **ACCEPTED (all 75)**.
- Family 2 (`SIG-UI-038` zero-JS static map, ADR-051, routing `P20.2:spec`) — **ACCEPTED (pending P20.2 A1)**.
- Net: the full 76-row ACCEPTED list is signed; **0 rejected**. Because nothing was rejected, there are
  **no** HG-14-rejection rows in `BACKLOG.csv` (backlog rows are spawned from the risk-register / ADR /
  LD / matrix sources, which is separate from this signature — see `BACKLOG.csv` + `check_backlog.py`).

- [x] Operator has reviewed §(b) and accepts the listed deviations (recorded in the build ledger
  `GATE DECISIONS`, HG-14). — **SIGNED (HG-14), 2026-09-08; transcribed by P20.1**

## (f) Round-10 capstone closure — P33.3 (2026-09-28, append-only)

The Round-10 counterpart of §(a)–(e): the bounded closure step for the six-stream
round (ADR-120, canonical spec §55, `docs/build/planning/2026-09-25-six-streams/`).
**This section is the acceptance packet GATE-ACCEPT (manifest row 195, HG-14 /
round acceptance) reviews.** It presents; it does not sign. The gate readout
`docs/build/readouts/ACCEPT-R10.md` stays `PENDING` — an operator or authorized
human record supplies the decision; silence is not approval. Nothing below marks
operator, reviewer, calendar, or live-stage work done, and no requirement id is
stamped here: P33.3 owns no requirement ids (its contract footer) and double-owns
none.

Inputs, consumed as evidence not as verdicts: the independent gap analysis
(`CAPSTONE_GAP_ANALYSIS.md` §(k), P33.1 — code/tests/artifacts inspected before
run-ledger claims) and the composed-verification proof (`COMPOSED_E2E_REPORT.md`
Round-10 addendum + `docs/build/reports/p33.2-composed-verification/`, P33.2),
re-checked on this branch (`d76c22eb` + this ticket's edits) against the live
obligation projection (`docs/build/reports/current/`, `current-projection/1` —
539 hashed inputs, `verify` fresh at run time).

### (f1) Round requirement coverage — the 38 §55 ids

Verdicts re-confirmed, not re-asserted — the P33.1 independent table
(`CAPSTONE_GAP_ANALYSIS.md` §(k)) stands; the machine record is
`COVERAGE_MATRIX.csv` (715 rows, `check_coverage_matrix.py` exit 0).

| verdict | count | ids | honest note |
|---|---|---|---|
| MET | 34 | `SIG-MEM-001` `SIG-MEM-002` `SIG-MEM-003` · `SIG-TRUST-001` `SIG-TRUST-002` `SIG-TRUST-003` `SIG-TRUST-004` `SIG-TRUST-005` `SIG-TRUST-006` `SIG-TRUST-007` `SIG-TRUST-008` `SIG-TRUST-009` `SIG-TRUST-010` · `SIG-EVAL-003` `SIG-EVAL-004` · `SIG-ACQ-001` `SIG-ACQ-002` `SIG-ACQ-003` `SIG-ACQ-004` · `SIG-FIND-001` `SIG-FIND-002` `SIG-FIND-003` `SIG-FIND-004` `SIG-FIND-005` `SIG-FIND-006` `SIG-FIND-007` `SIG-FIND-008` · `SIG-DOS-001` `SIG-DOS-002` `SIG-DOS-003` `SIG-DOS-004` `SIG-DOS-005` | each cites landed code/tests/artifacts (§(k) evidence column) |
| PARTIAL | 2 | `SIG-EVAL-001` `SIG-EVAL-002` | campaign machinery landed (digested preregistration, leakage-safe partitions, sealed samples, append-only blinded label store, RLS); **zero human labels exist** — status `awaiting_humans` under `D-R10-HUMAN-1` |
| MISSING | 4 | `SIG-EVAL-005` `SIG-EVAL-006` `SIG-EVAL-007` `SIG-MEM-004` | recorded, never unrecorded: the three EVAL ids' owners deferred wholesale with the S3 spine (`D-R10-HUMAN-1`, operator decision 2026-10-19); `SIG-MEM-004`'s owner is **P33.8 (row 200)** — scheduled chain work, not deferred |

### (f2) Cross-stream seams (6, `CAPSTONE_GAP_ANALYSIS.md` §(k))

| seam | verdict | state |
|---|---|---|
| P32.16 intake → P32.16a apply | MET | `intake.application` → `intake.event` bridge landed; role NOLOGIN — honest isolation |
| P32.22 recovery → P32.23a candidate | MET | candidate manifest pins frozen snapshot `sha256:138714a6…`; identity `sha256:bc20d4bf…` re-derived |
| P32.23a candidate → P32.25 publish | MET | `PUBLISH_PROOF.json` pins publication `p-17b713…` + GATE-G3 signed scope (provisional, review-only, `applied=[]`, `decision=null`) |
| dossier packets → P32.24 corpus | MET | 176 corpus artifacts rehashed clean; 75/75 records; completeness `complete` |
| eval machinery → human evaluation | PARTIAL (honest deferral) | `eval_confidence.toml mode=shadow`, `awaiting_humans`; owner chain deferred wholesale — recorded, not a gap |
| intake receiver → production | MISSING-by-design | `ops/config.toml [intake] operational=false`, `503 receiver_not_operating`; OPEN under `D-P32.16-1` |

### (f3) Verification evidence matrix — dated, this run

Revision: branch `devin/p33-3-capstone-closure` on `d76c22eb` (P33.2 tip, PR #184
OPEN/stacked) + this ticket's edits. `live_verification=false` — committed
offline evidence only; **no hosted probe, no production publication, no gate
signature, no human label, no outreach ran**. A skip is never a pass.

| gate | command | result | domain |
|---|---|---|---|
| local gate | `make check` | **5,506 passed / 3 skipped / 1 warning** (skips env-gated: live API URL, GCP project, credential env vars — recorded, never passes) | deterministic (Docker suites in-suite) |
| spec source | `python3 docs/build/tools/check_spec_src.py` | OK — byte-identical spec (710,858 bytes), 143 ADRs = file set, 715 ids, reference closure | deterministic |
| spec-source tests | `python3 docs/build/tools/test_check_spec_src.py` | 8 passed | deterministic |
| coverage | `python3 docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv` | 715 rows OK | deterministic |
| backlog | `python3 docs/build/tools/check_backlog.py` + `build_backlog_md.py --check` | 102/102 risk deferred, 143/143 ADR triggers, 90/90 LD rows, 36/36 deferral homes, 0 dup sources; BACKLOG.md == BACKLOG.csv | deterministic |
| planning | `check_plan.py` / `render_plan.py --check` / `test_planning_tools.py` / `test_integration_preflight.py` | 40 ordered rows, 38 singly-owned requirements, Round-9 tail, six streams / verified / 7 tests / 6 tests | deterministic |
| memory audit | `python3 docs/build/tools/audit_current_state.py` | 0 errors / 9 recorded baseline conflicts (manifest Lane-B pointer rows, P31.19 dependency references, D-P21.5-1 status-conflict) | deterministic |
| obligation events | `python3 docs/build/tools/obligation_events.py check` | green — 97 events, 4 coverage assessments, chains/cells consistent | deterministic |
| current projection | `python3 docs/build/tools/current_projection.py verify` | fresh — 539 input digests match at closeout | deterministic |
| docs freshness | `make docs-check` | 430 repo docs / 8 agent docs, 0 issues (1 stale suspect = standing warning) | deterministic |
| build memory | `bash scripts/docs/check-build-memory.sh .` | 0 violations, 0 warnings | deterministic |
| acceptance-register guard | `uv run pytest tests/unit/test_capstone_closure_round10.py` | 7 passed (new this ticket — fails if the packet drops an owed row or overclaims) | deterministic |
| **not run (recorded)** | `make test-db`, `tests/e2e`, `npm --prefix web run check`, live stage | no DB/web change in this ticket; live stage disabled — P33.2's `tests/db` 482 / `tests/e2e` 16 / web-check evidence stands as the most recent run (`COMPOSED_E2E_REPORT.md` Round-10 addendum) | recorded, not skipped silently |

Prior-round composed evidence the packet leans on (each dated + digested):
`sig.composed-verification/1` **verdict=pass 20/20** (P33.2, 2026-09-28, commit
`ad0bd84`, publication `p-8414a416…`) · `sig.release-publish-verification/1`
**verdict=pass 25/25** (P32.25) · `sig.journey-portfolio/1` **verdict=pass,
38 checks** (P32.24) · `sig.candidate-identity/1` `p-17b713…` over frozen
snapshot `sha256:138714a6…` (P32.23a) · GATE-G3 signed readout 2026-10-19
(reduced scope, provisional basis).

### (f4) Decisions and deviations — the ADR register

Round-10 decisions are **ADR-120 … ADR-144** (`docs/adr/`, all carrying
`## Revisit trigger`; `check_backlog.py` 143/143 triggers green). No landed body
was rewritten; every behavioural surprise was either a new ADR or a recorded
in-ticket repair:

| kind | items |
|---|---|
| planning allocation | ADR-120 — the six-stream round itself |
| build decisions | ADR-121 (typed assertions + actual-capture bindings) · ADR-122 (role semantics, conservative org identity) · ADR-123 (shared bitemporal occurrence selection) · ADR-124 (one publication-eligibility policy) · ADR-125 (legacy-evidence audit + recovery plan) · ADR-126 (obligation events + current projection) · ADR-127 (single-writer closeout protocol, SHADOW mode) · ADR-128 (preregistered blinded campaigns) · ADR-129 (design-aware evaluator + shadow gates) · ADR-130 (reviewed acquisition queue) · ADR-131 (dossier-documents adapter) · ADR-132 (immutable release namespaces) · ADR-133 (per-compartment FTS5 indexes) · ADR-134 (workspace state) · ADR-135 (isolated intake) · ADR-136 (research-dossier schema) · ADR-137/138/139 (three dossier packets) · ADR-140 (acquisition pilot) · ADR-141 (bounded recovery apply) · ADR-142 (candidate under deferred evaluation) · ADR-143 (journey acceptance portfolio) · ADR-144 (bounded publication + rollback rehearsal) |
| recorded deviations | **inserted row P32.10a** (manifest row 170.5 — server-side `decided_at` authority defect fix, no ADR: no semantics change, disclosed in row + run ledger) · **S3 spine wholesale deferral** (operator decision 2026-10-19; rows 184–187 recorded OPEN, manifest amendment) · **GATE-G3 reduced-scope signature** (dossiers publish `mechanical_complete`/`review.status=not_run`/`pilot_complete=False`) · **P32.25 hardlink write-through defect** (ADR-144-disclosed; repaired + regression-pinned) · **P33.1's three in-ticket repairs** (coverage-matrix re-verdicts, DEFERRALS dated-terminal regex blind spot + 8 reconciliations, committed-projection regeneration — all disclosed in §(k)) |
| this ticket | **no new ADR** — P33.3 decides nothing the spec didn't already delegate; its only behavioural surface is the register guard test |

### (f5) OPEN-obligation register — owner · landing · closure condition · compensating control

Every owed row in `DEFERRALS.md` / the live projection (36 rows = 32 OPEN +
4 PARTIAL) is listed exactly once. **Round-10-scoped** rows first; every row
below stays `OPEN`/`PARTIAL` — this ticket closes none and invents no progress.
Verification column cites the row's own `how to verify` field.

**Round-10-scoped obligations (15):**

| obligation | owes | owner | landing / return pass | compensating control now |
|---|---|---|---|---|
| `D-R10-HUMAN-1` | human development/calibration labels + dossier semantic review + confirmatory labels + measured decision | operator + independent reviewers | HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 (manifest rows 184–187, re-enter in order) | machinery shadow-only (`mode=shadow`, `applied=[]`); deferred evaluation disclosed on every published surface; `awaiting_humans` honest |
| `D-R6.1-EVAL` | human-grounded evaluation + threshold re-derivation | maintainer + reviewers | Round-10 human campaign → P31.18 re-derivation | `provisional-ruleset/1` labelled PROVISIONAL; shadow evaluator reports `historical_point_gate`, never eligibility evidence |
| `D-P30.2b-1` | human edge adjudication into clustering | engineering + reviewers | Round-10 human campaign → P31.18 | engineering half landed; no auto-write edge claimed; conservative split/merge posture |
| `D-P30.2b-2` | rules-v3 soft-conflict + re-measure on new holdout | engineering | Round-10 P31.18 evaluation refresh | current ruleset unchanged; tier-3g precision not re-claimed |
| `D-R10-SOURCES-1` | per-target rights review + bounded live acquisition | reviewer/operator (HG-03 family) | P32.18–P32.21 return passes | review-first acquisition queue + caps landed; nothing fetched unreviewed; no invented rights |
| `D-R10-LIVE-1` | production hosted recovery + final post-evaluation candidate | operator + engineering | P32.22/P32.23a live stage (`live_verification=true` re-run) | tooling fixture-proven; `prepared_not_executed` packets committed; no production claim anywhere |
| `D-R10-PUBLISH-1` | production public exposure | operator | GATE-G3 signed scope → P32.25 production half | release half signed at GATE-G3; bounded staging verified 25/25; `latest` pointer byte-pinned; production serve still owed |
| `D-R10-MEMORY-1` | closeout/writer protocol cutover decision | operator | P32.8 entry-point boundary | protocol landed + tested in SHADOW; `activation-check` honestly reports BLOCKED/READY; legacy path undisguised |
| `D-R10-USERS-1` | independent usability sessions (uncertainty/comprehension/accessibility) | operator recruiting | P32.24 (`UX.independent_sessions`) | `USABILITY_TASK_PROTOCOL.md` landed; no usability/comprehension/satisfaction claim anywhere |
| `D-P32.3-1` | legacy `sig.org.name` dispositions (split/merge/keep records) | reviewer session | BL-058 | `partner_org_scoped_identity_key` minting landed; ambiguous pairs stay distinct by default |
| `D-P32.10a-1` | whole-plan `sqitch verify` repair shape (`=27` vs 28 facets, `verify/shared_temporal_contract.sql:30`) | **maintainer decision** (count-derived/`>=`/stop pinning counts) | BL-058 | per-change verify green on real PG18; defect invisible to `make check`/`make test-db`; isolated to the whole-plan verify script; confirmed still present 2026-09-28 |
| `D-P32.16-1` | intake receiver operating prerequisites (owner, staffed rotation, retention, secrets, role grants, log exclusions) | operator | GATE-G3 scope + `docs/governance/intake-receiver-operating-packet.md` | receiver honestly `503 receiver_not_operating`; `operational=false` + env gates; never advertised; no synthetic submission |
| `D-P32.16a-1` | whole-plan `sqitch revert` repair shape (PostGIS dependents refuse `DROP EXTENSION postgis`, `revert/extensions.sql:7`) | **maintainer decision** (CASCADE vs ordered drops vs new teardown change) | BL-058 | per-change reverts green; deploy-only gate path unaffected; confirmed still present 2026-09-28 |
| `D-P32.18-1` `D-P32.19-1` `D-P32.20-1` `D-P32.21-1` | per-dossier + acquisition-pilot live return passes (4 rows) | operator-gated live stage | BL-058 return passes (`live_verification=true` re-runs) | dossier packets + funnel artifacts committed with fact-to-capture ledgers; all packets `prepared_not_executed` on disk; no pilot-completion claim |
| `D-P32.23a-1` | production release-candidate build over the hosted snapshot | operator-gated live stage | `LIVE_RETURN_PASS.json` command sequence over hosted DSN | candidate machinery staging-verified; manifest pins +0 rematerialization; pointer immutability proven |

**Carried-forward pre-Round-10 obligations (18):** owed by earlier rounds, still
owned, unchanged by this ticket — listed in `DEFERRALS.md` and the live
projection's obligations table (`reports/current/CURRENT.md`):

| obligation | status | owner | landing |
|---|---|---|---|
| `D-P21.3-2` | OPEN | operator | export `SIG_*` tokens (HG-09) in a networked shell; live-fetch re-run |
| `D-P21.5-1` | PARTIAL | operator | Zenodo/object-store credentials (HG-07); SWH save-now declined-by-operator recorded |
| `D-P21.7-1` | OPEN | operator | MapRoulette account + OSM OE page + `SIG_MAPROULETTE_API_KEY` (HG-08) |
| `D-JURIS.2-1` | PARTIAL | operator | jurisdiction-source rights decisions |
| `D-SOURCES.2-2` | OPEN | operator | per-source rights/access dispositions (decline is a valid close) |
| `D-SOURCES.7-1` | OPEN | reviewer | `dot_511_*` rights decisions |
| `D-SOURCES.7-2` | OPEN | operator | keyed live run for `dot_511_*` targets |
| `D-SOURCES.8-1` | PARTIAL | reviewer | remaining `camreg_*` rights decisions (10/14 done under GL-GATE-07) |
| `D-SOURCES.8-2` | OPEN | operator | keyed live run for `camreg_*` targets |
| `D-SOURCES.9-1` `D-SOURCES.9-2` `D-SOURCES.9-3` `D-SOURCES.9-4` | OPEN (4 rows) | reviewer / reviewer+external / external / reviewer | per-portal rights decisions + keyed live runs |
| `D-SOURCES.12-1` | PARTIAL | engineering | `camreg_stalbert_ab` rights + gated-row enumeration |
| `D-FEDERAL.1-1` | OPEN | scheduled | `sig-sched-sam-gov` cron + +0 re-run check |
| `D-R7.1-AUTH` | OPEN | operator | external-IdP OAuth decision (new ADR + ticket when unblocked) |
| `D-R7.2-SEND` | OPEN | operator | consenting-filer records-request send (never automatic) |
| `D-P31.4-1` | OPEN | scheduled (cron) | date-bound check of the 2026-10-10 batch-05 OSM replay per the row's exact command |

`SIG-MEM-004` is **not** a DEFERRALS row: it is scheduled chain work owned by
P33.8 (manifest row 200) — pending, not deferred, and listed here so no
requirement lacks a named owner.

### (f6) Honest scope state — exactly what exists today

- **Provisional policy published to staging.** `provisional-ruleset/1` is the
  active production-policy basis; the P32.23a candidate `p-17b713…` (identity
  `sha256:bc20d4bf…` over frozen snapshot `sha256:138714a6…`) carries
  `evaluation.status=deferred` + `decision=null` + `applied=[]`. GATE-G3 signed
  a **reduced scope**: dossiers publish `mechanical_complete` with
  `review.status=not_run`, `pilot_complete=False`; no completed-pilot or
  certified-count assertion exists anywhere. P32.25 verified the bounded staging
  publication (25/25) — that is staging evidence, not production exposure.
- **Evaluation deferred.** The S3 spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23)
  is deferred wholesale by recorded operator decision; the evaluator runs
  `mode=shadow` and never promotes; `awaiting_humans` is the honest state.
- **Intake non-operational.** `[intake].operational=false`; `/intake/new` +
  POST `/intake/v1/reports` → `503 receiver_not_operating`; no advertised
  submission surface; no synthetic submission fabricated.
- **Production exposure OPEN.** `D-R10-PUBLISH-1` (production serve half),
  `D-P32.23a-1` (production candidate), `D-R10-LIVE-1` (hosted recovery/final
  candidate) all remain owed — fixture and staging success is not a live pass.
- **Two whole-plan sqitch hygiene defects** (`D-P32.10a-1` verify count,
  `D-P32.16a-1` revert dependents) confirmed present and intentionally left for
  a maintainer decision on repair shape — in-place edits of landed
  deploy/revert/verify scripts are discouraged by the append-only sqitch
  convention (`db/AGENTS.md`), so the repair shape is a decision, not a
  mechanical fix.

### (f7) The acceptance list — what GATE-ACCEPT is asked to accept

Distinguished by kind, per the contract ("intentional design, unresolved
engineering, human/external obligations, dated verification"):

**Intentional design (no action needed; recorded posture):**
shadow-mode evaluator that never promotes · `document_only` evidence bindings
recorded distinctly from typed locators · honest `unavailable`/`awaiting_humans`
eval states · below-threshold dossiers publishing as `mechanical_complete` ·
`prepared_not_executed` return-pass packets · the zero-JS static public surface
(ADR-051 lineage) · intake `operational=false` fail-closed posture · staged
rollback rehearsal shape (`R.prior_release`/`R.no_prior_pointer`/`R.refused_deploy`).

**Unresolved engineering (owned, bounded, recorded):**
`D-P32.10a-1` + `D-P32.16a-1` (maintainer decision on sqitch repair shapes) ·
`D-P32.3-1` (legacy `sig.org.name` dispositions — reviewer session) ·
`SIG-MEM-004` (scheduled to P33.8, row 200) · the engineering halves of
`D-P30.2b-1/2` (landed; activation follows the human campaign).

**Human/external obligations:**
`D-R10-HUMAN-1` + `D-R6.1-EVAL` (independent labels/review) · `D-R10-USERS-1`
(usability sessions) · `D-R10-SOURCES-1` + `D-P32.18/19/20/21-1` (rights review
+ bounded live acquisition) · `D-R10-LIVE-1` + `D-P32.23a-1` +
`D-R10-PUBLISH-1` (production live stage) · `D-P32.16-1` (intake operating
prerequisites) · `D-R10-MEMORY-1` (protocol cutover decision) · the
carried-forward operator/reviewer/scheduled rows in (f5).

**Dated verification:** (f3) — every gate with its command, result and domain;
the three verdict-bearing proofs (`composed-verification/1`, `release-publish-
verification/1`, `journey-portfolio/1`) plus the signed GATE-G3 readout.

**What the signature would mean:** the operator accepts the recorded deviations
and the OPEN register **as presented** — it does not declare any deferred,
human, or live-stage row done. Rows the operator declines return to their
owners; nothing here silently becomes a gap.
