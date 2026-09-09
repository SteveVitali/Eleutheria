## Summary
Finishes the capstone's closure step (CAPSTONE step 2, part 2): the remaining small/medium **CODE** gaps the whole-spec analysis routed to closure, the **documentation** gaps, and the **proposed ACCEPTED-deviations list** for the operator's signature (GATE **HG-14**, post-ticket). It also delivers the **ER-over-PostgreSQL** work P19.4 deferred here under its size guard (ADR-059 §6, `LD-F04`) — on the critical path.

Stacked on `devin/p19-4-capstone-spine-wiring`. Implements `docs/tickets/P19.5__capstone-gap-closure.md`.

## What changed
**ER over PostgreSQL (LD-F04 — moved from P19.4, critical path)**
- Additive `review_queue` sqitch change: `review_item` + **append-only** `review_decision` (`decided_at` set by the DB).
- `resolution/review_pg.py` `PgReviewQueue` — a JSONL-compatible backend; the JSONL/in-memory `ReviewQueue` **remains the default**.
- `sig-resolution match --dsn … --jurisdiction <id>` reads org candidates from the PG spine, scores them (tier-4/5 PROPOSED only), enqueues `review_item` rows; `sig-resolution review decide --dsn` appends **exactly one** `review_decision` row per call (history on repeat).
- Flips `tests/e2e` **S4 `LD-F04`** xfail → real PASS; `tests/resolution/test_pg_backend.py`.

**CODE gaps**
- **Export gate honours `derivative_permitted` (LD-F08/LD-H09):** `policy.licensing.assert_export_permitted` fails closed on `derivative_permitted=false` (machine reason `derivative_permitted=false`); `partition_exportable` non-raising companion. Reduce-only (§0.7). `sm_alpr`/`deflock_app_repo` refused.
- **Jurisdiction-conditional web render (LD-V12/LD-H11):** `web/src/lib/publication.ts` mirrors `adapter_publication_permitted`; `dossier.applyPublicationPolicy` withholds a public-employee name under FR-GDPR/BE-GDPR at **build time**; BCP-47 `lang` + localised titles; zero-JS preserved. `jurisdiction.spec.ts` (+ `.nojs`).
- **`inference` CLI (LD-F15):** `coverage` / `access-paths` / `completeness` / `freshness` wired to the existing modules.

**Documentation gaps + closure record**
- **ADR-060** (resolver P08.1, retro-fitted record) + risk register `## Phase 8 — Resolver (P08.1)` (RISK-P8-00a/00b) — LD-X05.
- **ADR-044** amended `## Post-hoc hardening (4493b14, landed on P14.1's branch)` — LD-D14.
- **ADR-061** (this ticket's decisions); risk register `## Phase 19 — Gap closure (P19.5)` (RISK-P19-09/10); traceability; `COVERAGE_MATRIX.csv` re-routed the 5 stale `P19.4:*` rows to their real homes (P21.2/P21.4).
- **`docs/build/CAPSTONE_CLOSURE.md`** (a)-(e).

## Design decisions
- ER-over-PG reuses ADR-059's fixed names unchanged (`review_decision`, `--dsn`, `sig-resolution match/review`).
- The TS publication mirror keeps the web build hermetic/zero-dependency; it only ever **withholds** (unknown jurisdiction → no-publish), so drift fails safe.
- The export gate enforces `derivative_permitted` at the single fail-closed choke point (`assert_export_permitted`), with a partition helper for mixed sets.

## GATE HG-14 — the equality assertion
`CAPSTONE_CLOSURE.md` §(b) has **exactly one row per `MET-DIFFERENTLY` id**: **76 rows == 76 MET-DIFFERENTLY rows** in `COVERAGE_MATRIX.csv` (verified: `md=76`, `section(b) rows=76`, equal). §(e) operator signature is left **unticked** — the orchestrator presents §(b) to the operator; P20.1 records the signature.

## Verification (live, over Docker Postgres)
| AC | Result |
|---|---|
| `SIG_REQUIRE_DB_TESTS=1 pytest tests/e2e -ra` | **13 passed, 1 xfailed, 0 failed**; only `LD-V08` → **P21.4** remains; **S4 `LD-F04` flipped to PASS** |
| `pytest tests/connectors tests/unit -k "derivative or export_gate"` | 12 passed; `sm_alpr` refused with reason `derivative_permitted=false` |
| `npm run test:e2e` (web) incl. `jurisdiction.spec.ts` + `.nojs` | 170 passed; a11y 23 passed; `check:perf` OK (script size 0) |
| `python -m inference {coverage,access-paths,completeness,freshness} --help` | all exit 0 |
| ADR-060/061 exist + indexed; `## Phase 8 — Resolver (P08.1)` at risk_register L460; ADR-044 contains `4493b14` | ✓ |
| `check_coverage_matrix.py` | exit 0; **0** rows `verdict∈{PARTIAL,MISSING} & routing=P19.4:*` |
| `CAPSTONE_CLOSURE.md` §(b) row count == MET-DIFFERENTLY | **76 == 76** ✓ |
| `make check` | green — **2417 passed, 1 xfailed** |

## Out of scope (guarded)
Annotation persistence (P21.2); web reads the live export/API path — `LD-V08` (P21.4); live transports (P21.3); tiles/MapLibre (P21.5/P20.2); curation UI (P21.6); registry rows (P21.1); backlog (P20.1); spec edits (P20.2).
