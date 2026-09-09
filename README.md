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
shell, and nine fixture-tested connectors. It is a buildable, fully-tested reference implementation —
**not a running service**: nothing is deployed and no source has been fetched live (see
*Repository layout & development* and `docs/build/RELEASE_NOTES_v0.1.0.md`).

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
ADR-023 records the deviation.

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

### Releases

Versions follow [Semantic Versioning](https://semver.org/); the current version is **0.1.0** (each
member `pyproject.toml`). The change history is in [`CHANGELOG.md`](./CHANGELOG.md)
(Keep a Changelog format). No ticket merges, tags, or pushes `main` — the operator **integrates the
stacked-PR chain and cuts the tag after the build**, following the copy-pasteable procedure in
[`docs/build/INTEGRATION_PLAN.md`](./docs/build/INTEGRATION_PLAN.md) §(d): re-run
`sh docs/build/tools/merge_dryrun.sh`, merge the open PRs bottom-up, `make check`, then
`git tag -a v0.1.0`, `make sbom`, and `gh release create` with
[`docs/build/RELEASE_NOTES_v0.1.0.md`](./docs/build/RELEASE_NOTES_v0.1.0.md). Contribution workflow:
[`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Method note

Load-bearing findings from delegated research were not adopted on report alone. Several were
re-verified first-hand before entering the spec; two delegated findings were **declined** after
failing verification, and two of the project's own earlier findings were **withdrawn** the same way.
`docs/research/_meta/LEAD_SPOTCHECKS.md` records all of it, including the errors.

The specification documents **institutions and infrastructure, not people**. Part VIII is binding,
not aspirational: several architectural decisions elsewhere exist because of it.
