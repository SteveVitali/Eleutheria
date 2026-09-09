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
the OCFL evidence store, the read API, exports with licence-compartment computation, the zero-JS web
shell, and twelve fixture-tested connectors. It is a buildable, fully-tested reference implementation —
**not a running service**: nothing is deployed and no source has been fetched live (see
*Repository layout & development* and `docs/build/reports/RELEASE_NOTES_v0.1.0.md`).

## Contents

| Path | What it is |
|---|---|
| `docs/1_deep_research_overview.md` | The source outline: landscape synthesis and project definition (3,314 lines) |
| `docs/2_canonical_design_spec.md` | **The canonical design and implementation specification** (9,047 lines, 671 numbered requirements) |
| `docs/research/` | The evidence base: 13 research workstreams, 26,818 lines, 501 evidence-formatted findings |
| `docs/research/_meta/` | Traceability index, adversarial gap analysis, lead-agent spot-checks, and the spec's section sources |
| `docs/governance/` | The adopted governance and safety policies: takedown/corrections/suppression, governance & Code of Conduct, the anti-misuse statement, contributor safety |
| `docs/adr/` | Architecture Decision Records (Appendix F) |
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
| `connectors` | The eight-stage connector framework, the source registry + fail-closed ingestion gate, and the fixture-tested connectors (§21–§23, ADR-026). |
| `parsing` | The layered document-parsing stack — the §24 parser interface every connector extracts through, incl. the layer-3/4 table + clause engines (ADR-033/071). |
| `resolution` | The jurisdiction/organization identity registries and deterministic + probabilistic (Splink) entity resolution (§11, §14, ADR-029). |
| `reconcile` | The deterministic `RESOLVE` engine, the §29 reconciliation workflows, and `Contradiction` as a first-class object (§28–§29, ADR-036/037). |
| `inference` | Coverage / negative-space metrics and access-path closure over the resolved graph (§30, §32, ADR-038/045). |
| `tasks` | The §33 research-task engine, the contributor system, and human-mediated contribution-back (§33–§35, ADR-039/054/055). |
| `api` | The hand-written, versioned FastAPI read contract: resolution envelope, as-of, dereferenceable IDs, `/changes` (§37, ADR-047). |
| `exports` | Bulk export builders with per-compartment licence computation + the ODbL split, Zenodo deposits, object-store push and tiles (§38, §42, ADR-048/067). |
| `orchestration` | The pipeline-composition boundary — the only package allowed to import a workflow orchestrator (SIG-ENG-013, ADR-016). |
| `policy` | The executable crawler / licence / publication / threat / sensitivity policy (real tested code, not prose — §42–§46, SIG-ENG-014). |
| `ops` | Runtime composition (`sig-ops`) of the PG spine + read API + static site, plus deposits/egress/degraded-mode (P21.4/P21.5, ADR-066/067). |
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

### Running SIG — three ways

SIG is a buildable reference implementation, not a running service; nothing is deployed and no
source has been fetched live (see below). There are three ways to exercise it, in increasing
scope — all zero-cost and local:

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

None of these fetches a live source: no source is "green" (the `ingestion_permitted` gate is still
fail-closed, HG-03 pending), so every connector run is fixture-backed replay/shadow, not live
acquisition — see [`docs/build/OPERATIONAL_READINESS.md`](./docs/build/OPERATIONAL_READINESS.md).

### Releases

Versions follow [Semantic Versioning](https://semver.org/); the current version is **0.1.0** (each
member `pyproject.toml`). The change history is in [`CHANGELOG.md`](./CHANGELOG.md)
(Keep a Changelog format). No ticket merges, tags, or pushes `main` — the operator **integrates the
stacked-PR chain and cuts the tag after the build**, following the copy-pasteable procedure in
[`docs/build/INTEGRATION_PLAN.md`](./docs/build/INTEGRATION_PLAN.md) §(d): re-run
`sh docs/build/tools/merge_dryrun.sh`, merge the open PRs bottom-up, `make check`, then
`git tag -a v0.1.0`, `make sbom`, and `gh release create` with
[`docs/build/reports/RELEASE_NOTES_v0.1.0.md`](./docs/build/reports/RELEASE_NOTES_v0.1.0.md). Contribution workflow:
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Method note

Load-bearing findings from delegated research were not adopted on report alone. Several were
re-verified first-hand before entering the spec; two delegated findings were **declined** after
failing verification, and two of the project's own earlier findings were **withdrawn** the same way.
`docs/research/_meta/LEAD_SPOTCHECKS.md` records all of it, including the errors.

The specification documents **institutions and infrastructure, not people**. Part VIII is binding,
not aspirational: several architectural decisions elsewhere exist because of it.
