# Eleutheria — Surveillance Infrastructure Graph (SIG)

Design and implementation specification for an open, vendor-agnostic, temporally versioned,
claim-level-provenance knowledge graph of surveillance infrastructure.

> **Build an open, vendor-agnostic, temporally versioned, claim-level-provenance knowledge graph of
> surveillance infrastructure that federates existing public-interest datasets and primary records
> to show what surveillance capabilities exist, where and by whom they are deployed, how they are
> connected and accessed, what rules and contracts govern them, how they are actually used when
> evidence exists, how they change over time, and exactly which sources support or contradict every
> material claim.**

This repository contains the full **specification and research base** and the **implemented build**:
all §47 packages built and tested (`make check` green), the claim spine over PostgreSQL 18 + PostGIS,
the OCFL evidence store, the read API, exports with licence-compartment computation, the Astro web
surface (zero-JS public content pages plus three opt-in interactive islands), and twenty registered
connectors behind the fail-closed `ingestion_permitted` gate.

**It is also deployed.** The public surface runs on GCP at
**[surveillancegraph.org](https://surveillancegraph.org)** — launched 2026-09-24 and republished
2026-09-27 over a ~2.4M-claim spine assembled from live fetches of the green-reviewed sources
(`docs/build/reports/LAUNCH_RECORD_2026-09-24.md`,
`docs/build/reports/REPUBLISH_LIVE_2026-09-27.md`). What is *not* yet public: the Round-10
provisional-policy release candidate is published to a **staging namespace only** — production
exposure, the hosted recovery/freeze it depends on, and the independent human evaluation all remain
open obligations (see *Deployed state* below). The anonymous correction receiver is built
but deliberately **not operating** (`/intake/` answers `503 receiver_not_operating` by design).

## Contents

| Path | What it is |
|---|---|
| `docs/1_deep_research_overview.md` | The source outline: landscape synthesis and project definition (3,314 lines) |
| `docs/2_canonical_design_spec.md` | **The canonical design and implementation specification** (9,377 lines, 715 numbered requirement ids, v1.1.0) |
| `docs/research/` | The evidence base: 13 research workstreams, 26,818 lines, 501 evidence-formatted findings |
| `docs/research/_meta/` | Traceability index, adversarial gap analysis, lead-agent spot-checks, and the spec's section sources |
| `docs/governance/` | The adopted governance and safety policies: takedown/corrections/suppression, governance & Code of Conduct, the anti-misuse statement, contributor safety, the intake-receiver operating packet, publication-scope analyses |
| `docs/evaluation/` | The independent human-evaluation campaign packet: rubric, training pilot, reviewer provisioning, shadow-gate readout (prepared — **no human labels exist yet**) |
| `docs/adr/` | Architecture Decision Records (144 — Appendix F) |
| `docs/tickets/` | The ordered ticket backlog — the build's committed contract record (`00_MANIFEST.md` is the order; each `PXX.Y` file is one ticket) |
| `docs/build/` | Durable build memory: planning ledger, build index, decision memo, capstone/backlog/reconciliation reports, the integration plan and release notes |

## The specification

`docs/2_canonical_design_spec.md` is written to be executed by a long-running coding agent across
19 sequential phases, each with testable acceptance criteria. It is organised as:

- **Part 0** — how to use it; requirement grammar; the execution model
- **Part I** — charter, goals, non-goals, the federation compact
- **Part II** — domain model: temporal semantics, epistemic model, entities, relationships, vocabularies, identity
- **Part III** — data architecture: storage, schema, evidence store, analytics boundary, geospatial
- **Part IV** — acquisition: connector architecture, source registry, parsing, LLM policy, crawler conduct
- **Part V** — resolution, reconciliation, inference, contradiction, coverage metrics
- **Part VI** — research coordination: task generation, contributors, contribution-back
- **Part VII** — delivery: API, exports, the product surfaces, editorial standards
- **Part VIII** — governance, safety, and law: licensing, publication policy, threat model, continuity
- **Part IX** — engineering practice
- **Part X** — the phased implementation plan
- **Part XI** — the Round-10 contract extension (§55: typed assertions, dossiers, human evaluation,
  immutable releases + FTS5 discovery, correction intake, acquisition, build memory)
- **Appendices A–G** — traceability matrix, the 37 mandatory questions answered, consolidated DDL, a worked example, glossary, ADR index, corrections to the outline

### Three properties it asserts, and how they are checked

1. **Superset.** Every obligation in the outline is discharged. Proven by Appendix A, a matrix over
   **480 atomic obligations** extracted into `docs/research/_meta/OUTLINE_TRACE.md`. Current state:
   **480/480 COVERED**.
2. **Independently corroborated.** The outline's factual claims were re-verified against primary
   sources rather than restated. Corrections are in Appendix G.
3. **Executable.** Every requirement is testable; requirements that cannot be expressed as a test
   are marked `(RATIONALE)` and bind nothing.

## Regenerating the specification

The canonical spec is a **build artifact**. Edit the section sources, not the output:

```sh
sh docs/research/_meta/spec_src/BUILD.sh
```

## Repository layout & development

The repo is a [**uv**](https://docs.astral.sh/uv/) workspace (SIG-ENG-011). Its top-level layout is
the canonical §47 package layout (SIG-ENG-012) — these package names are frozen; renaming one
requires an ADR:

```
ontology/  db/  connectors/  parsing/  resolution/  reconcile/  inference/
tasks/  api/  exports/  orchestration/  policy/  ops/  evidence/  # 14 Python packages
web/                                                              # TypeScript (SIG-ENG-010)
docs/tickets/  docs/build/  docs/                                 # tickets, build memory, docs
tests/                                                            # the test suite (incl. tests/db, tests/e2e)
```

The 14 workspace members (SIG-ENG-011/012) are `ontology`, `db`, `connectors`, `parsing`,
`resolution`, `reconcile`, `inference`, `tasks`, `api`, `exports`, `orchestration`, `policy`, `ops`,
and `evidence` (added by ADR-023 / amendment A7). `evidence/` is not in the original frozen §47 list;
ADR-023 records the deviation. Each is a plain CLI (`uv run python -m <pkg> --help`):

| Package | What it owns |
|---|---|
| `ontology` | The single LinkML source of truth + SKOS vocabularies and the deterministic generators (§20.1, ADR-007). |
| `db` | The physical claim spine: the L0–L3 schema on PostgreSQL 18 + PostGIS, sqitch migrations, append-only + RLS, and the DuckDB/Parquet analytics boundary (§16, §18, ADR-001). |
| `connectors` | The eight-stage connector framework, the source registry + fail-closed ingestion gate, and twenty registered connectors — fixture-replayable offline; live fetch only where the source's review record is green (§21–§23, ADR-026/088). |
| `parsing` | The layered document-parsing stack — the §24 parser interface every connector extracts through, incl. the layer-3/4 table + clause engines (ADR-033/071). |
| `resolution` | The jurisdiction/organization identity registries and deterministic + probabilistic (Splink) entity resolution (§11, §14, ADR-029). |
| `reconcile` | The deterministic `RESOLVE` engine, the §29 reconciliation workflows, and `Contradiction` as a first-class object (§28–§29, ADR-036/037). |
| `inference` | Coverage / negative-space metrics and access-path closure over the resolved graph (§30, §32, ADR-038/045). |
| `tasks` | The §33 research-task engine, the contributor system, and human-mediated contribution-back (§33–§35, ADR-039/054/055). |
| `api` | The hand-written, versioned FastAPI read contract: resolution envelope, as-of, dereferenceable IDs, `/changes` (§37, ADR-047). |
| `exports` | Bulk export builders with per-compartment licence computation + the ODbL split, Zenodo deposits, object-store push and tiles (§38, §42, ADR-048/067). |
| `orchestration` | The pipeline-composition boundary — the only package allowed to import a workflow orchestrator (SIG-ENG-013, ADR-016). |
| `policy` | The executable crawler / licence / publication / threat / sensitivity policy (real tested code, not prose — §42–§46, SIG-ENG-014). |
| `ops` | Runtime composition (`sig-ops`) of the PG spine + read API + static site — deposits/egress/degraded-mode, hosted deploy + scheduled ingest (`ops/gcp/`), recovery/release/dossier-packet verification verbs (P21.4/P21.5/P24.1, ADR-066/067/075/081, Round-10 ADR-125/132/137–139/142/144). |
| `evidence` | The OCFL 1.1 write-once evidence store: content addressing, the capture pipeline, and sensitivity tiers (§17, ADR-006/023). |

The TypeScript `web/` package (SIG-ENG-010) is the zero-JS-by-default Astro public shell; it consumes
export artifacts and is built and tested with `npm` (see [`web/README.md`](./web/README.md)).

The phased build's contract record lives in the repo: the ordered ticket backlog is
`docs/tickets/00_MANIFEST.md` (each `PXX.Y` ticket is a committed contract), and the durable build
memory — planning ledger, build index, decision memo and later capstone/backlog artifacts — lives
under `docs/build/`.

Conventions established here that every later ticket depends on:

- **Python is primary; TypeScript is confined to `web/`** (SIG-ENG-010).
- **Every pipeline stage is a plain CLI** (SIG-ENG-013): each package `<pkg>` is runnable as
  `uv run python -m <pkg>` and installs a `sig-<pkg>` console script (`<pkg>/src/<pkg>/cli.py`).
- **Only `orchestration/` may import a workflow orchestrator** (SIG-ENG-013); the list of
  orchestrator modules lives in `orchestration/pipeline.py` and the boundary is enforced by
  `tests/unit/test_import_boundary.py`.
- **`policy/` is real, tested code**, not prose (SIG-ENG-014).
- **Every source file carries an SPDX header.** The licence posture is resolved (P00.2, SIG-LIC-005):
  code is Apache-2.0; data/documentation carry per-artifact licences — see `LICENSE`.

Common commands (humans and CI run the same `make` targets):

```sh
make sync          # install the workspace from the committed lockfile (uv --frozen)
make check         # lint + format-check + type-check + tests + generated-artifact gate (the CI gate)
make test-db       # claim-spine tests on PostgreSQL 18 + PostGIS via testcontainers (needs Docker)
make lock          # refresh uv.lock
make export        # regenerate the PEP 751 lock export (pylock.toml)
make sbom          # produce a CycloneDX SBOM (per release)
```

Run one package's CLI with `uv run python -m <package> --help` (every stage is a plain CLI,
SIG-ENG-013). The composed end-to-end suite is `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e`
(needs Docker).

### Running SIG — three local ways

There are three ways to exercise the build locally, in increasing scope — all zero-cost and local:

1. **Verify the build** — `make check`. Lint, format, type-check, the full unit/integration suite,
   and the generated-artifact gate. This is the CI gate and needs no services.
2. **Stand it up for one jurisdiction (local staging)** — `uv run sig-ops up --jurisdiction okc --seed`
   brings up the PG18 + PostGIS spine (with `db/sqitch.plan` deployed), the read API, and a static
   server for `web/dist`; `uv run sig-ops status` reports health and `uv run sig-ops down` tears it
   all down. The whole first-jurisdiction path (up → shadow connector runs → resolution → reconcile →
   export → web build → acceptance queries) is driven end-to-end by
   [`docs/build/tools/run_okc.sh`](./docs/build/tools/run_okc.sh). Needs Docker. Details:
   [`ops/README.md`](./ops/README.md).
3. **Run the low-cost degraded posture** — `uv run sig-ops degraded` builds the fully static site
   with **no API** and a last-export "degraded-but-alive" banner, so the project survives on only a
   static host when the dynamic services are down (the $0-beyond-static continuity posture,
   SIG-GOV-021, P21.5).

On a clean checkout none of these fetches a live source: the `ingestion_permitted` gate is
fail-closed per-source (HG-03), so local connector runs are fixture-backed replay/shadow —
`sig-connectors run --mode live` refuses (exit 3) any source whose review record is not green.
A subset of sources *is* green-reviewed and the hosted scheduled jobs do fetch them live
(`docs/build/reports/SOURCE_LIVE_OPS_MATRIX.md`); the remaining gated sources are tracked in
[`docs/tickets/DEFERRALS.md`](./docs/tickets/DEFERRALS.md). See
[`docs/build/OPERATIONAL_READINESS.md`](./docs/build/OPERATIONAL_READINESS.md).

#### Deployed state (Round 10, 2026-09-28)

Distinct from the local paths above, the hosted deployment exists and is public:

- **Public surface** — `https://surveillancegraph.org` serves the HG-11-signed national publish
  (GCP; `docs/build/reports/GCP_DEPLOYMENT.md`, `LAUNCH_RECORD_2026-09-24.md`,
  `REPUBLISH_LIVE_2026-09-27.md`).
- **Staging only** — the Round-10 provisional-policy release candidate (`p-17b713…`,
  `provisional-ruleset/1`, `evaluation.status=deferred`) was published and verified inside a
  bounded staging registry; it is *staged, not served*. Production exposure is an open operator
  obligation (`D-R10-PUBLISH-1`, with `D-R10-LIVE-1` + `D-P32.23a-1` upstream).
- **Built, not operating** — the anonymous correction receiver is implemented and gated off:
  `[intake].operational=false`, so intake answers `503 receiver_not_operating`
  (ADR-135; operator packet `docs/governance/intake-receiver-operating-packet.md`; `D-P32.16-1`).
- **Deferred** — the independent human-evaluation spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23)
  was deferred wholesale by recorded operator decision; the dossier packets are
  `mechanical_complete` with `review.status=not_run`. Authoritative current state:
  [`docs/build/OPERATIONAL_READINESS.md`](./docs/build/OPERATIONAL_READINESS.md) §(f) and
  [`docs/build/CAPSTONE_CLOSURE.md`](./docs/build/CAPSTONE_CLOSURE.md) §(f).

### Releases

Versions follow [Semantic Versioning](https://semver.org/); the declared version is **0.1.0** (each
member `pyproject.toml`) and **no tag has been cut** — the REL.1 release-marker gate was deferred by
the operator and `v0.1.0` remains untagged. The change history is in
[`CHANGELOG.md`](./CHANGELOG.md) (Keep a Changelog format). No ticket merges, tags, or pushes
`main` — the operator integrates the stacked-PR chain following the current, read-only-verified
procedure in
[`docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md`](./docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md)
(re-run `sh docs/build/tools/merge_dryrun.sh`, retarget + merge the open PRs in ascending order with
the documented conflict resolutions, then the post-merge verification; it has **no tag step** — the
P20.3 [`docs/build/INTEGRATION_PLAN.md`](./docs/build/INTEGRATION_PLAN.md) it supersedes is kept as
the dated record). Contribution workflow: [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Method note

Load-bearing findings from delegated research were not adopted on report alone. Several were
re-verified first-hand before entering the spec; two delegated findings were **declined** after
failing verification, and two of the project's own earlier findings were **withdrawn** the same way.
`docs/research/_meta/LEAD_SPOTCHECKS.md` records all of it, including the errors.

The specification documents **institutions and infrastructure, not people**. Part VIII is binding,
not aspirational: several architectural decisions elsewhere exist because of it.
