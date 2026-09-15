# CAPSTONE_GAP_ANALYSIS — the whole spec vs the whole build (P19.2, CAPSTONE step 1)

The first whole-spec coverage judgement of the SIG build: every one of the **668** requirement
ids in `docs/2_canonical_design_spec.md` classified MET / MET-DIFFERENTLY / PARTIAL / MISSING /
AT-RISK-INTEGRATION / N/A-RATIONALE, with evidence, and every gap routed to exactly one later
ticket. Companion data: `docs/build/COVERAGE_MATRIX.csv` (668 rows, ids + paths only — no data,
§0.7). **No code was changed by this ticket.**

> **Independence (orchestrate-build §3.1 anti-bias).** Every verdict here was formed from the
> **spec + code + tests** first. The prior build's machine ledger and the `implement-spec`
> per-ticket self-assessments under `.agents/scratch/**` were **not** read before forming verdicts.
> PR bodies (`gh pr view N` for N=1..46) supplied the id→owning-ticket map; `LEDGER_DEFERRALS.md`
> and `BUILD_INDEX.md` were consulted **only** in the seam hunt (§e) and disposition (§j) as a
> checklist of claims to confirm against code — never as a source of verdicts. Where confirmation
> was not possible, the verdict is PARTIAL, never MET ("no synthetic certainty", §3.1).

## (a) Method + commands

1. **Universe (668).** `grep -oE '\*\*SIG-[A-Z]+-[0-9]+[a-z]? \((MUST|SHOULD|MAY|RATIONALE)'
   docs/2_canonical_design_spec.md | sort -u | wc -l` → 668 (646 MUST · 13 SHOULD · 2 MAY ·
   7 RATIONALE). `SIG-ENG-006/009/028/029` are reserved-but-unassigned (spec L84) and are **not**
   in the universe. `(MUST NOT)` forms count as level MUST.
2. **Evidence index.** A read-only scanner built a per-id reference index across seven classes —
   package `src/` (14 workspace members + `web/` + DDL), `tests/**` + `web/tests/**`, `docs/adr/*`
   (both the `Requirement ids:` field and body citations), PR bodies #1–#46, `docs/traceability.md`,
   `docs/risk_register.md` — with **range-notation expansion** (`SIG-X-034…037`, `…`, `–`, `..`,
   ranges ≤120 wide) per SCOPING §(i). Re-derived counts match `SCOPING_NUMBERS.md` closely
   (in_tests 373, in_src 464, in_adr 359, in_pr 361, in_trace 424, in_risk 232, in_webtests 64).
3. **Classification rubric (orchestrate-build §3 item 1).** For each id: `covered+tested` if a test
   references it → **MET**; `covered+untested` if only `src`/DDL/ADR-recorded → **MET** (test
   backfill tracked by RISK-P19-04); a recorded sound deviation (ADR-030/037/038/039/041/051/054) →
   **MET-DIFFERENTLY**; charter/process/epistemic/publication-safety principle satisfied by design +
   the policy package (P00.2/P00.3) but not cited by id → `process/governance` **MET-DIFFERENTLY**
   (compensating control named); a claimed-but-unbuilt or unverifiable id → **PARTIAL**; a concrete
   feature with no evidence anywhere → **MISSING**; a unit-tested behaviour whose **composed** path
   was never run green → **AT-RISK-INTEGRATION**; RATIONALE level → **N/A-RATIONALE**. Spine seams
   were confirmed by reading the code directly (§e).
4. **Routing.** `routing ∈ {—, P19.3, P19.4:S, P19.4:M, P21.1, P21.2, P21.3, P21.4, P21.5, P21.6,
   P21.7, P21.8, P21.9, P20.1:backlog, P20.2:spec, accepted}`. Every non-MET verdict
   (MET-DIFFERENTLY / PARTIAL / MISSING / AT-RISK-INTEGRATION) carries a non-`—` routing; MET and
   N/A-RATIONALE carry `—`. **`P19.4:L` is not allowed** (0 rows). `P19.4:*` = capstone closure:
   spine-seam rows (claim sink, read store, ER/annotations over PG) are P19.4; every other
   `P19.4:S/M` row is P19.5's work list (§i). Routing targets P21.1–P21.9 are the DECISION_MEMO §3
   rows 55–63. **Enum note:** the ticket body lists P21.2–P21.8, but the ticket's own notes and
   DECISION_MEMO §5.5 route two id groups to **P21.1** (Stage-0 outreach) and **P21.9** (P17 pathway
   ingestion). The enum is therefore extended to include P21.1 and P21.9; the consistency script
   accepts them. No other enum change.
5. **Consistency gate.** `python docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv`
   → `668 rows OK` (asserts 668 rows, all ids spec-defined, no duplicates, valid enums, non-MET rows
   routed, MET/MET-DIFFERENTLY rows have evidence). Runs in <1 s.

## (b) Roll-up

**By verdict (668 total):**

| verdict | count |
|---|---|
| MET | 502 |
| MET-DIFFERENTLY | 76 |
| PARTIAL | 50 |
| MISSING | 23 |
| AT-RISK-INTEGRATION | 10 |
| N/A-RATIONALE | 7 |

**By class:**

| class | count |
|---|---|
| covered+tested | 412 |
| covered+untested | 142 |
| process/governance | 87 |
| deferred(RISK) | 7 |
| rationale-only | 7 |
| unreferenced | 12 |
| deviated(ADR) | 1 |

**By prefix (MET / MET-DIFF / PARTIAL / MISSING / AT-RISK / N/A · total):**

| prefix | MET | MET-DIFF | PART | MISS | AT-RISK | N/A | total |
|---|---|---|---|---|---|---|---|
| API | 11 | 0 | 0 | 0 | 2 | 0 | 13 |
| CHART | 9 | 24 | 0 | 0 | 0 | 2 | 35 |
| CONTRIB | 30 | 0 | 2 | 2 | 0 | 0 | 34 |
| ENG | 12 | 18 | 2 | 0 | 0 | 0 | 32 |
| EPIS | 11 | 18 | 0 | 0 | 1 | 0 | 30 |
| EVID | 17 | 0 | 1 | 1 | 0 | 0 | 19 |
| EXPORT | 11 | 0 | 0 | 0 | 0 | 0 | 11 |
| GEO | 10 | 0 | 3 | 0 | 0 | 0 | 13 |
| GOV | 14 | 2 | 5 | 3 | 0 | 0 | 24 |
| IDENT | 33 | 1 | 0 | 0 | 0 | 0 | 34 |
| INGEST | 52 | 0 | 14 | 12 | 2 | 3 | 83 |
| LIC | 17 | 0 | 1 | 0 | 0 | 1 | 19 |
| LLM | 7 | 0 | 0 | 0 | 0 | 0 | 7 |
| METRIC | 14 | 0 | 0 | 0 | 0 | 0 | 14 |
| ONTO | 57 | 4 | 11 | 0 | 0 | 0 | 72 |
| PARSE | 8 | 0 | 0 | 0 | 0 | 0 | 8 |
| PUB | 14 | 5 | 1 | 2 | 1 | 0 | 23 |
| RECON | 53 | 1 | 1 | 0 | 2 | 0 | 57 |
| SEC | 2 | 1 | 2 | 1 | 0 | 0 | 6 |
| STORE | 39 | 0 | 6 | 1 | 0 | 1 | 47 |
| TASK | 20 | 0 | 0 | 0 | 0 | 0 | 20 |
| TIME | 14 | 1 | 0 | 0 | 1 | 0 | 16 |
| UI | 47 | 1 | 1 | 1 | 1 | 0 | 51 |

(Per-prefix counts are computed from `COVERAGE_MATRIX.csv`, the record of truth.)

**Reading of the roll-up.** The build is functionally near-complete at the **unit** level (554 of
668 = 83% MET or covered-untested-MET). The real story is in three buckets: (i) the **10
AT-RISK-INTEGRATION** rows — behaviours that pass in isolation but whose **composed** path (connector
→ PG → API → web) has never run green (§e); (ii) the **76 MET-DIFFERENTLY** rows, almost all
`process/governance` charter/epistemic/publication-safety principles satisfied by design + the policy
package rather than by an id-cited feature (§c); and (iii) the **73 PARTIAL/MISSING** rows, which are
overwhelmingly *not-yet-built infrastructure and outreach* (deposits, tiles, live transports, Data
Driven / municipal-ordinance connectors, the usability study) that the plan already sequences into
P21.x, plus claim-without-code traceability drift routed to P20.1.

## (c) The 98 nowhere-referenced ids (SCOPING_ID_LISTS §L1), each classified

All 98 are classified in the CSV; **0 are `covered+tested`** (the deterministic L1 cross-check). By
(class, verdict):

| class | verdict | count | disposition |
|---|---|---|---|
| process/governance | MET-DIFFERENTLY | 64 | charter/process/epistemic principle with a **compensating control**: enforced by the six-layer architecture + the executable policy package (P00.2), the governance/takedown/contributor-safety policies (P00.3), the prohibited-endpoint bar (P14.1), and the honest-rendering rules (P15.3). Not cited by id → not a code gap. Routing `accepted`. |
| covered+untested | MET | 3 | satisfied by design with a concrete anchor but uncited by id: `SIG-GEO-001` (EPSG:4326, `db/deploy/claim.sql:36`), `SIG-ONTO-004` (denormalized read models = `db/deploy/domain_entities.sql`), `SIG-TIME-015` (UTC+offset in `db/src/db/temporal.py`). |
| unreferenced | MISSING | 11 | genuinely-unbuilt concrete features: `SIG-INGEST-043/043a-d` (Data Driven source → P21.8), `SIG-INGEST-049a-d`+`046b/c` split across P21.9/P21.3, `SIG-GOV-022/023/024` deposits/succession → P21.5. |
| covered+untested | PARTIAL | 8 | plausibly-satisfied framework/data-quality reqs with no id-linked evidence: `SIG-INGEST-004/005/007/008`, `SIG-GEO-002`, `SIG-RECON-052`, `SIG-STORE-004/005` → P20.1 or P21.5. |
| process/governance | MISSING | 7 | governance obligations not yet performed: `SIG-GOV-022/023/024`, `SIG-STORE-003`, `SIG-EVID-019`, `SIG-CONTRIB-012/012a` → P21.1/P21.5. |
| process/governance | PARTIAL | 2 | `SIG-GEO-005/007` (OSM tag-coverage data-quality observations) → P20.1. |
| rationale-only | N/A-RATIONALE | 3 | `SIG-CHART-031/035`, `SIG-INGEST-044` — rationale statements, no build obligation. |

The headline: **the majority of the "nowhere-referenced" set is not a hole in the build** — 64 are
charter/process principles the architecture satisfies structurally, and 3 are DDL-satisfied — but
the **18 MISSING** among them are real and are all routed to a P21 ticket, and the 10 PARTIALs are
honest "verify me" flags.

## (d) The 250 never-ticketed ids (SCOPING_ID_LISTS §L3) — roll-up

Never assigned to a ticket at decomposition, yet mostly implemented anyway (ownership was by spec
section, not by id):

| verdict | count |
|---|---|
| MET | 120 |
| MET-DIFFERENTLY | 67 |
| PARTIAL | 37 |
| MISSING | 19 |
| N/A-RATIONALE | 4 |
| AT-RISK-INTEGRATION | 3 |

**187 of 250 (75%) are MET or MET-DIFFERENTLY** — decomposition-by-section captured them without an
explicit id assignment. The 19 MISSING + 37 PARTIAL are the same infrastructure/outreach/claim-drift
buckets as §(b), already routed. This confirms the "250 never-ticketed" number is a *decomposition
bookkeeping* artefact, **not** a 250-wide coverage hole.

## (e) Seam hunt — LD-H01…H13 + 7 orphaned seams + 4 composed-path seams = **24 rows**

Each row: landed / not landed, with a code anchor confirmed by reading the file at build time.

**LD-H handoff seams (13):**

| # | seam (from → to) | landed? | evidence |
|---|---|---|---|
| H01 | P02.x → P08.1: resolver **writes** the `resolution` table | **partly / write NOT landed** | `resolution` table DDL exists (`db/deploy/resolution.sql:15`) but `reconcile/src/reconcile/resolve.py` emits value objects with no `INSERT` (LD-V05) → AT-RISK (see composed seam #1/#2) |
| H02 | P02.2 → P04+/P08: live-connector WACZ per-PR + connector reproducibility | **landed** | WACZ capture `evidence/src/evidence/capture.py`; per-PR/connector reproducibility scaffolding (LD-F02 → MET, §j) |
| H03 | P04.1 → P04.2: plain-CLI stages / per-connector runner | **landed** | `connectors/src/connectors/cli.py` (`list-connectors`, `run` stages; `build_parser`) |
| H04 | P05.2 → P15: curation **web UI** | **NOT landed (orphaned)** | no `web/src/pages/curate*`; curation is CLI + JSONL review queue only (LD-F05, ADR-030) |
| H05 | P06.1 → P15.2: production dossier supersedes slice renderer | **landed** | `web/src/pages/dossier/**` (P15.2) |
| H06 | P08.x/P09/P10/P13 → P14.1: API endpoints (contradiction/coverage/tasks/accountability) | **landed (contract); AT-RISK on store** | `api/src/api/routes.py` (`coverage_statement`, contradiction/task routes) over `InMemoryStore` (LD-F06) |
| H07 | P09.1 → P15.5: methodology/coverage web pages (§32) | **landed** | `web/src/pages/methodology.astro`, `web/src/pages/coverage-metrics.astro` |
| H08 | P14.2 → P15.3 → ∅: vector-tile **rendering** | **NOT landed (orphaned)** | PMTiles *format/contract* exists (`exports/src/exports/formats.py`) but no tile-generation pipeline (LD-F07) |
| H09 | P14.2 → P00.4: `derivative_permitted` **export gate** | **NOT landed (orphaned)** | field is *read* (`exports/src/exports/bundle_io.py:49`) but not enforced as a gate condition (LD-F08) |
| H10 | P16.2 → P10.3: records-request link (SIG-CONTRIB-019) | **landed** | `tasks/src/tasks/records_request.py` (§36, P10.3) |
| H11 | P18.1 → P15/P18.2: jurisdiction-conditional **web render** | **NOT landed** | fixtures name jurisdiction (`web/src/lib/*-fixture.ts`); conditional-publication rendering not wired to the web layer (LD-V12) |
| H12 | P17.x → "Stage-5 connectors": live population of the P17 pathways | **NOT landed** | expressibility only, no ingestion (RISK-P17-03); no ticket existed → P21.9 |
| H13 | P11/P12 → P08.2: §29.3/§29.7 sharing-edge + snapshot-diff | **landed (single home, no re-impl)** | `reconcile/src/reconcile/sharing.py` (§29.3), `reconcile/src/reconcile/snapshot_diff.py`; consumed downstream without duplication |

**Orphaned seams (7)** — seams with no owner anywhere (LEDGER_DEFERRALS §8):

| # | orphaned seam | landed? | evidence / route |
|---|---|---|---|
| O1 | curation web UI (LD-F05/H04) | not landed | no `/curate` pages → P21.6 |
| O2 | tile generation (LD-F07/H08) | not landed | format only, no generator → P19.5/P21.5 |
| O3 | `derivative_permitted` export gate (LD-F08/H09) | not landed | field read, not gated (`exports/bundle_io.py:49`) → P19.5 |
| O4 | jurisdiction-conditional web render (LD-V12/H11) | not landed | fixtures only → P19.5 |
| O5 | osm live wiring (LD-F03) | not landed | `PoliteFetcher` exists (`connectors/src/connectors/net.py:153`) but no live Overpass `HttpxTransport`/`CaptureStore` (RISK-P4-06) → P21.3 |
| O6 | Stage-5 connectors (LD-H12) | not landed | no ticket → P21.9 |
| O7 | P08.1 §53 section (LD-X05) | not landed | P08.1 shipped with **no ADR and no risk-register (§53) section** → P19.5 |

**Composed-path seams (4)** — unit-green, composed-never-run → **AT-RISK-INTEGRATION** (confirmed in
code):

| # | composed seam | status | anchor → route |
|---|---|---|---|
| C1 | connector → claim spine | AT-RISK | only `InMemoryClaimSink` (`connectors/src/connectors/stages.py:280`); `pipeline.py:125` asserts only when a sink is present → **connector claims have never been written to PG** → **P19.4** (`SIG-INGEST-016/017`) |
| C2 | API → claim store | AT-RISK | API served over `InMemoryStore` (`api/src/api/store.py:148`); no DB-backed `ReadStore` (LD-F06) → **P19.4** (`SIG-API-001/002`, `SIG-TIME-008`) |
| C3 | annotation persistence | AT-RISK | no `psycopg`/`sqlalchemy` in `reconcile/`, `inference/`, `tasks/`; `Contradiction`/`CoverageRecord`/`ResearchTask` computed in memory (ADR-037/038/039/054) → **P21.2** (`SIG-RECON-039/040`, `SIG-EPIS-018`) |
| C4 | web → data | AT-RISK | `web/` renders from `web/src/lib/*-fixture.ts`, not the live export/API path → **P19.4/P21.4** (`SIG-UI-010`, `SIG-PUB-007`) |

## (f) J-1 registry seam + P07.3 gate bypass (process findings)

- **7/8 OKC slice sources unregistered.** `connectors/src/connectors/data/sources.toml` has no
  Oklahoma rows; the slice fixture `tests/acceptance/fixtures/okc_sources.json` names 8 `source_id`s
  of which only `src:deflock` (→ `deflock_repo`) is registered. `SIG-INGEST-023/038` (source
  registry completeness) are MET for the *registered* set but the OKC slice sources
  (`okc-procurement`, `okc-council`, `okcpd-policy`, `ok-statute`, `journalrecord`, `oklahoman`, and
  the CivicClerk tenant) are **not** registry rows. This is the P06.1 slice-vs-registry seam →
  **P21.1** owns the 6+1 new registry rows + rights packets. Recorded as a finding, not a code gap
  in this ticket.
- **P07.3 gate bypass (LD-X08).** `usaspending` is the only source ever fetched live (P07.3, PR #19)
  yet its `sources.toml` row is `custody_posture=REFERENCE`, `compact_status=public_terms_only`,
  **no `[rights]` block and no `ingestion_permitted`** → rights **UNDETERMINED**. The live trace
  therefore ran **outside** the `assert_ingestion_permitted` loader gate
  (`connectors/src/connectors/loader.py:93`). The data is US-Government public-domain, so the fetch
  was defensible, but the **gate was bypassed** rather than passed. Process finding → P21.1 records
  the `usaspending` rights block; the fail-closed gate itself is MET (`SIG-INGEST-028`).

## (g) Top-20 gaps (MUST-level, MISSING first, then critical-path relevance to DECISION_MEMO §6)

| # | id | verdict | route | gap |
|---|---|---|---|---|
| 1 | SIG-INGEST-016/017 | AT-RISK | P19.4:M | connector claims never written to PG (no `PgClaimSink`) — **blocks the whole composed path** (§6 step 2) |
| 2 | SIG-API-001/002, SIG-TIME-008 | AT-RISK | P19.4:M | API has never read the claim spine (in-memory `ReadStore`) — blocks OKC live serve |
| 3 | SIG-RECON-039/040, SIG-EPIS-018 | AT-RISK | P19.4:S / P21.2 | annotation entities not persisted (ADR-037/038/039/054) |
| 4 | SIG-UI-010, SIG-PUB-007 | AT-RISK | P19.4:M | web renders fixtures, not live export/API |
| 5 | SIG-GOV-022 | MISSING | P21.5 | mirrors / Zenodo / Software Heritage deposits |
| 6 | SIG-EVID-019 | MISSING | P21.5 | quarterly Zenodo deposit of each release |
| 7 | SIG-STORE-003 | MISSING | P21.5 | zero-cost start / degraded mode |
| 8 | SIG-PUB-015/016 | MISSING | P21.4 | redaction-as-new-capture + irreversible published artifact |
| 9 | SIG-INGEST-046b/046c | MISSING | P21.3 | robots.txt / rights-reservation live-fetch compliance |
| 10 | SIG-INGEST-043/043a-d | MISSING | P21.8 | Data Driven releases as a first-class source |
| 11 | SIG-INGEST-049/049a-d | MISSING | P21.9 | municipal-ordinance + coarse-international connector class |
| 12 | SIG-UI-001 | MISSING | P21.7 | personas / moderated usability study (≥5 users) |
| 13 | SIG-CONTRIB-012/012a | MISSING | P21.1 | Stage-0 outreach before any ecosystem connector |
| 14 | SIG-GOV-023/024 | MISSING | P21.5 | succession commitment + archival insurance |
| 15 | SIG-SEC-003 | MISSING | P20.1 | transparency report (legal demands) |
| 16 | SIG-UI-038 | MET-DIFF | P20.2:spec | zero-JS static map, not interactive MapLibre (ADR-051) |
| 17 | SIG-UI-040 | PARTIAL | P20.1 | search over Postgres FTS not wired |
| 18 | SIG-PUB-012 | PARTIAL | P21.6 | asset-promotion gate not wired to a curation service |
| 19 | SIG-GEO-002 | PARTIAL | P20.1 | proximity-cast-to-geography serving rule untested |
| 20 | SIG-STORE-044 | PARTIAL | P20.1 | Wikidata-QID-as-first-class crosswalk unverified |

The top-4 (the spine seams) are the whole capstone story: **the composed path stops at the PG/API
seam** exactly as DECISION_MEMO §2/§6 predicted. Everything below is scheduled P21.x
infrastructure/outreach.

## (h) Spot-check — 10 seeded `covered+tested` rows, tests run

Selection: `random.seed(20260908); random.sample(covered+tested-rows-with-a-test, 10)` over
`COVERAGE_MATRIX.csv`. Each named test run with `uv run pytest`; the DB row run under the
Docker/testcontainers harness (`SIG_REQUIRE_DB_TESTS=1`). **10/10 pass, 0 failures** (142 tests):

| id | test | result |
|---|---|---|
| SIG-IDENT-033 | `tests/resolution/test_crosswalk.py` | `12 passed in 0.09s` |
| SIG-IDENT-005 | `tests/resolution/test_jurisdiction.py` | `7 passed in 0.07s` |
| SIG-LIC-010 | `tests/connectors/test_osm.py` | `28 passed in 0.12s` |
| SIG-EVID-014 | `tests/evidence/test_disappearance.py` | `5 passed in 0.06s` |
| SIG-STORE-020 | `tests/db/test_corrections.py` (Docker) | `2 passed in 8.75s` |
| SIG-ONTO-068 | `tests/connectors/test_france_belgium.py` | `23 passed in 0.33s` |
| SIG-LIC-009a | `tests/unit/test_policy_licensing.py` | `21 passed in 0.06s` |
| SIG-INGEST-003 | `tests/connectors/test_audit_structural.py` | `26 passed in 0.07s` |
| SIG-API-008 | `tests/api/test_api_dereference.py` | `5 passed in 0.13s` |
| SIG-IDENT-002 | `tests/resolution/test_ori.py` | `13 passed in 0.06s` |

No UI ids were drawn by the seed, so `npm --prefix web run test:unit` was not required for this
sample. (A failure would have been a finding routed `P19.4:S`, not a reason to fake a pass — none
occurred.)

## (i) P19.4:S/M work list + per-P21 routing (this **is** the downstream work list)

**P19.4 (capstone spine wiring) — the S/M rows:**

- `P19.4:M` (7): `SIG-API-001`, `SIG-API-002`, `SIG-INGEST-016`, `SIG-INGEST-017`, `SIG-PUB-007`,
  `SIG-TIME-008`, `SIG-UI-010`
- `P19.4:S` (3): `SIG-EPIS-018`, `SIG-RECON-039`, `SIG-RECON-040`

Per the ticket rule, the spine-seam rows (claim sink → `SIG-INGEST-016/017`; read store →
`SIG-API-001/002`, `SIG-TIME-008`) are **P19.4**; the remaining `P19.4:S` annotation rows and the
web-data rows are closed by P19.5 or fold into P21.2/P21.4 as noted in the CSV `note` column.

**Routed to each P21 ticket:**

| route | ids |
|---|---|
| P21.1 | SIG-CONTRIB-012, SIG-CONTRIB-012a |
| P21.3 | SIG-INGEST-046b, SIG-INGEST-046c |
| P21.4 | SIG-PUB-015, SIG-PUB-016 |
| P21.5 | SIG-EVID-019, SIG-GOV-022, SIG-GOV-023, SIG-GOV-024, SIG-STORE-003, SIG-STORE-004, SIG-STORE-005 |
| P21.6 | SIG-PUB-012 |
| P21.7 | SIG-UI-001 |
| P21.8 | SIG-INGEST-043, 043a, 043b, 043c, 043d |
| P21.9 | SIG-INGEST-049, 049a, 049b, 049c, 049d, 049e, 049f, 050 |
| P20.2:spec | SIG-UI-038 |
| P20.1:backlog | 44 ids (claim-without-code drift + unverified framework/data-quality reqs; see CSV) |
| accepted | 75 ids (charter/process/epistemic/publication-safety principles, MET-DIFFERENTLY) |

## (j) Dispositions for the P19.2-owned deferral rows

| LD | disposition | evidence |
|---|---|---|
| LD-F02 | **MET** — live-connector WACZ + connector reproducibility landed | `evidence/src/evidence/capture.py`; connector replay `connectors/src/connectors/replay.py` |
| LD-F12 | **MET** — research-task auto-gen (§33) landed in `tasks/` (P10.1), not left in P08.1 | `tasks/src/tasks/lifecycle.py:247` (`TaskPool.generate`) |
| LD-F13 | **MET** — the §32 metrics "UI half" landed as P15.5 methodology/metrics pages | `web/src/pages/methodology.astro`, `coverage-metrics.astro` |
| LD-F17 | **MET (differently)** — parser layers landed in the `parsing/` package (not deferred to connectors as ADR-033 first framed) | `parsing/src/parsing/layers.py`, `extraction.py`, `locator.py`, `classification.py` |
| LD-F18 | **MET** — aggregates landed with the DuckDB substrate in P12.1 | closed per LEDGER_DEFERRALS §8 |
| LD-X01 | **MET** — the 32→34 task-type amendment is carried in the committed spec (BUILD.sh byte-identical); manifest row 25 reads "all 34 detectors" | `docs/tickets/00_MANIFEST.md:71` |
| LD-X08 | **process finding** — `usaspending` fetched live while rights UNDETERMINED → loader gate bypassed (not passed); route the rights block to P21.1 | `connectors/src/connectors/data/sources.toml` (usaspending row, no `[rights]`/`ingestion_permitted`); `loader.py:93` |

## Provenance

Append-only (P1–P3): this document and `COVERAGE_MATRIX.csv` sit **beside** the earlier build-memory
docs; no earlier claim was edited. Produced on branch `devin/p19-2-capstone-gap-analysis` off
`devin/p19-1-build-memory-and-hygiene` @ `33aaf02`. The matrix columns
(`id, level, spec_section, class, verdict, evidence, owning_tickets, tests, adrs, risk_rows, routing,
note`) are the stable contract consumed by P19.3/P19.4/P19.5/P20.1/P20.2 — do not rename.
