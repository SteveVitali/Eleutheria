# AGENTS.md — SIG (Surveillance Infrastructure Graph)

## Purpose

A `uv` workspace of Python packages (plus a TypeScript `web/`) that builds an evidence-first,
append-only graph of public surveillance infrastructure from a canonical design spec. Everything is
derived from committed evidence: claims carry provenance, resolution is a recorded decision, and no
fact is asserted the evidence does not support (the "defining standard", §3.1). This file orients an
agent working anywhere in the repo.

**Precedence is nearest-file-wins.** Agents read the closest `AGENTS.md` in the directory tree; a package file
(`web/`, `db/`, `connectors/`, `api/`, `exports/`, `ops/`, `tests/`) adds package-specific rules and
**wins on conflict** with this root file. Read the root first, then the nearest package doc.

## Architecture

A staged pipeline, each stage a plain CLI (SIG-ENG-013), over one canonical store:

- `connectors/` acquire evidence from external sources and emit **claims** (behind a fail-closed
  ingestion gate) → `parsing/` extracts structured facts → `resolution/`/`reconcile/`/`inference/`
  resolve entities and reconcile counts → `db/` (PostgreSQL 18 + PostGIS) is the append-only
  **claim spine** → `exports/` produces licence-compartmented bundles → `api/` (FastAPI) serves the
  spine read-only → `web/` (Astro, static, zero-JS) renders the public surface from export bytes.
- `ontology/` is the single LinkML source of truth; `db` DDL, JSON Schema, OWL/SHACL and Pydantic
  are **generated** from it. `orchestration/`, `tasks/`, `policy/`, `evidence/`, `ops/` are the
  cross-cutting glue (scheduling, contribution-back, gates, the OCFL evidence store, runtime).

## Module Layout

The §47 package layout is **frozen** (SIG-ENG-012) — 14 Python workspace members + `web/`:

| package | responsibility |
|---|---|
| `ontology/` | LinkML source of truth; generates DDL, schema, OWL/SHACL, Pydantic (`make gen`) |
| `db/` | physical claim spine: PG18+PostGIS, sqitch migrations, append-only, RLS |
| `connectors/` | source registry + eight-stage connector framework; fail-closed ingestion gate |
| `parsing/` | the §24 layered parser stack (genre, tables, clauses) connectors extract through |
| `resolution/` | entity resolution / envelope logic |
| `reconcile/` | §29 count reconciliation and sharing-edge / snapshot-diff logic |
| `inference/` | derived-claim inference over the spine |
| `tasks/` | contribution-back (MapRoulette, OSM changeset feed), onboarding aggregates |
| `api/` | FastAPI read API + the loopback-only authenticated curation app |
| `exports/` | licence-compartmented export bundles, deposits, tiles, dossiers |
| `orchestration/` | Dagster-based scheduling glue |
| `policy/` | executable governance: sensitivity tiers, licensing, publication gates |
| `ops/` | runtime composition (`sig-ops`, docker-compose), egress, degraded mode |
| `evidence/` | OCFL 1.1 write-once evidence store (added by ADR-023 after §47 froze) |
| `web/` | public Astro surface; the **only** TypeScript package (SIG-ENG-010) |

Every Python package is `<pkg>/src/<pkg>/…` and exposes a CLI: `uv run python -m <pkg> --help`.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `Makefile` | ~80 | the single source of build/test/gen commands — humans and CI run the same targets |
| `.github/workflows/ci.yml` | ~102 | CI: the `python` job mirrors `make check`; the `web` job runs `npm run check` |
| `connectors/src/connectors/loader.py` | ~170 | the fail-closed ingestion gate (`assert_loadable`, `ingestion_permitted`) |
| `ontology/src/ontology/generate.py` | ~550 | ontology generation; canonicalises graphs (`to_canonical_graph`) |
| `db/src/db/claim_sink.py` | ~490 | `PgClaimSink` — insert-only writes to the claim spine |
| `api/src/api/store_pg.py` | ~600 | `PgReadStore` — read-only view over the spine |
| `tests/db/conftest.py` | ~230 | PG18+PostGIS testcontainer; `SIG_REQUIRE_DB_TESTS` fail-loud switch |
| `tests/e2e/test_composed_stack.py` | ~860 | Docker-gated composed-stack e2e; the `LD-`/xfail convention |
| `docs/tickets/00_MANIFEST.md` | ~180 | the ordered ticket backlog and how to drive the build |

## Build & Test

`make check` is the single CI-mirrored gate (`Makefile`, `.github/workflows/ci.yml` `python` job):

| command | what it runs |
|---|---|
| `make check` | `lint` → `format-check` → `typecheck` → `test` (pytest) → `verify-gen` — the full local gate, mirror of CI |
| `make test-db` | `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db` — the claim-spine DB suite (**needs Docker**) |
| `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e` | the composed-stack e2e (**needs Docker**) |
| `npm --prefix web run check` | the web gate: `typecheck` → `test:unit` → `build` → `check:licenses` → `test:e2e` |
| `make docs-check` | both vendored doc detectors (repo docs + agent docs); structural, read-only |

- One package's CLI: `uv run python -m <package> --help` (every stage is a plain CLI, SIG-ENG-013).
- Regenerate committed generated artifacts with `make gen`; verify with `make verify-gen`.

## Code Conventions

- **Python is primary; TypeScript is confined to `web/`** (SIG-ENG-010). Ruff lints (`E,F,I,UP,B`)
  with import-order enforced; `ruff format` must already be applied; `mypy` type-checks every package.
- **Additive, append-only, back-compat.** New DB changes are new sqitch changes (never in-place
  edits); corrections are new claim rows, never `UPDATE`/`DELETE`.
- **Every ADR needs a `## Revisit trigger`** section — `tests/unit/test_policy_adrs.py` fails without
  it (SIG-STORE-007). A decision change is a **new** ADR, never an edit of a landed one (SIG-ENG-003).

## Critical Gotchas

1. **`verify-gen` fails on uncommitted generated artifacts — commit `ontology/generated` first.**
   `make verify-gen` regenerates then runs `git diff --exit-code -- pylock.toml ontology/generated`.
   If you regenerate but don't commit, the gate is red *because the tree is dirty*, not because the
   output is wrong. Commit the regenerated `ontology/generated` (and `pylock.toml`), then re-run.
2. **Ontology/RDF generation is canonicalised.** The generators are otherwise non-deterministic; the
   build canonicalises graphs via `rdflib.compare.to_canonical_graph`
   (`ontology/src/ontology/generate.py`) and pins `PYTHONHASHSEED=0` (`Makefile` `gen-ontology`).
   Don't hand-fix ordering churn — regenerate with `make gen`.
3. **`tests/db` and `tests/e2e` skip silently without Docker.** They stand up `postgis/postgis:18-3.6`
   via testcontainers (`tests/db/conftest.py`); a missing daemon **skips** them — so a green
   `make check` on a Docker-less machine has *not* run them. Set `SIG_REQUIRE_DB_TESTS=1` (as
   `make test-db` does) to make a missing/unreachable daemon **fail loudly** instead of skip.
4. **`ingestion_permitted` defaults false; the loader gate refuses un-reviewed sources.** Sources are
   declared in `connectors/src/connectors/data/sources.toml`; `assert_loadable`
   (`connectors/src/connectors/loader.py`) fails closed unless `ingestion_permitted` is true **and**
   the compact/custody posture permits it. `sig-connectors run --mode live` **refuses** (exit 3) any
   source whose review-status is not green. Never bypass the gate — flipping a source is a
   human/rights decision (gate **HG-03**), not a code change.
5. **The claim spine is insert-only.** `PgClaimSink` (`db/src/db/claim_sink.py`) and `PgReadStore`
   (`api/src/api/store_pg.py`) never `UPDATE`/`DELETE`; there is no update/delete path anywhere in
   `db/`. Model corrections as new claims.
6. **The public web budget is zero-JS.** Public pages must render with **no `<script>` tags**;
   `web/lighthouserc.json` asserts script size `0` and total ≤ 150 KB, and `test:e2e` enforces WCAG
   2.2 AA. Adding client JS to a public page fails `check:perf`/`test:e2e` (the `/curate/**` island
   allowance is the only exception, ADR-068).
7. **`tests/e2e` xfails carry an `LD-`/`accepted:` reason and are flipped only by the closing
   ticket.** A never-yet-wired seam is an `xfail` whose reason begins with its `LEDGER_DEFERRALS` id
   (`^LD-[A-Z]+[0-9]+:`) — never a loosened assertion. Do not flip an xfail to a pass unless your
   ticket is the one that closes that seam.
8. **Deferred obligations — read `docs/tickets/DEFERRALS.md` first, every run.** It is the append-only
   register of owed gate-pending work (build-memory v2). A deferral not in that file did not happen; if
   your ticket or a landed prerequisite unblocks an `OPEN` row, closing it (verify + flip to `DONE` with
   evidence) is part of your run. Gates refuse to pass while an `OPEN` row scoped to that phase remains.

## Where build memory lives (build-memory v2, ADR-073)

`docs/build/` is the **committed** memory root (opted in by the `<!-- build-memory: v2 -->` marker in its
README): its LEDGER holds the machine state (CURRENT STATE / GATE DECISIONS / RETURN PASS / PHASE LOG); its
BUILD_INDEX is one row per landed ticket; `docs/build/runs/` holds the per-ticket run ledgers, `docs/build/pr/`
the PR bodies, `docs/build/reports/` the project reports, and `docs/build/logs/` is the one gitignored
subtree. `.agents/scratch/` is retired. The layout is validated by `scripts/docs/check-build-memory.sh .`
(run in `make docs-check`). The ADR index under `docs/adr/` is generated by `build-memory adr-index` — never
hand-edited.

## Terminology

- **Claim spine** — the append-only L0–L3 claim/evidence/resolution store in `db/` (§16).
- **Resolution envelope** — the recorded decision that some claims describe the same entity.
- **Contradiction** — two evidenced claims that disagree; kept visible, never silently reconciled.
- **Compartment** — a licence-scoped partition of the data (e.g. the ODbL/OSM compartment, §42.3).
- **Custody posture / compact status** — a source's rights state; gate inputs for ingestion.
- **Ticket / manifest / build memory** — `docs/tickets/` is the committed contract backlog
  (`00_MANIFEST.md` is the order, `DEFERRALS.md` the owed-obligations register); `docs/build/` is the
  committed build memory (its LEDGER is the machine state, `docs/build/runs/` the per-ticket ledgers); a
  **gate** (`HG-nn`) is a human decision a ticket may pause on.

## Do

- Read the ticket contract in `docs/tickets/` and the relevant build memory in `docs/build/` before
  implementing; stamp the requirement ids you satisfy in the PR.
- Run `make check` before every commit; commit regenerated artifacts **before** re-running it.
- Stack every PR from the current checkout (the branch the previous ticket left checked out).
- Add a per-package `AGENTS.md` only where a package has non-obvious conventions.

## Don't

- Never edit `docs/2_canonical_design_spec.md` directly — it is a build artifact: edit the section
  source under `docs/research/_meta/spec_src/`, run `docs/research/_meta/spec_src/BUILD.sh`, and
  record the change in an ADR (SIG-ENG-003).
- Never rewrite ADR bodies, the risk register, or traceability history — **append** (P1–P3).
- Never hand-edit `ontology/generated` or the frozen §47 layout without an ADR.
- Never commit build logs under `docs/build/logs/` (gitignored) or `sbom.cdx.json`; the rest of
  `docs/build/` **is** committed build memory (build-memory v2, ADR-073). `.agents/scratch/` is retired.
- Never tick a human gate (`HG-nn`) or flip a source to `ingestion_permitted=true` — operator action.
- Never merge, tag, or push `main`; the operator integrates the stack after the chain.
- Never store secrets in files — tokens/keys are environment variables only (**HG-09**).

## Boundaries

- **Safe:** add tests, add a new sqitch change with deploy/revert/verify, add a source registry row
  (left `ingestion_permitted=false`), add a package `AGENTS.md`, extend a CLI additively.
- **Ask first / gated:** anything under Part VIII protections — no plate/person data, the
  officer-naming gate, ODbL compartment separation; publication (`HG-01`/`HG-02`/`HG-11`); rights
  flips (`HG-03`); the frozen §47 layout (needs an ADR).
- **Forbidden:** editing the generated spec, generated ontology, or a landed ADR body directly;
  bypassing the ingestion gate; writing `UPDATE`/`DELETE` against the claim spine; committing scratch
  or secrets; merging/tagging/pushing `main`.
