# AGENTS.md — SIG (Surveillance Infrastructure Graph)

## Purpose

A `uv` workspace of Python packages (plus a TypeScript `web/`) that builds an evidence-first,
append-only graph of public surveillance infrastructure from the canonical design spec. This file
orients an agent working anywhere in the repo; nested `AGENTS.md` files (in `web/`, `db/`,
`connectors/`) add package-specific rules and win on conflict (nearest-file-wins).

## The gate — `make check`

`make check` is the single CI-mirrored gate. It runs, in order (see `Makefile`):

| step | command | notes |
|---|---|---|
| lint | `uv run ruff check` | import-order enforced |
| format | `uv run ruff format --check` | formatting must already be applied |
| typecheck | `uv run mypy` (every package) | |
| tests | `uv run pytest` | the unit/integration suite |
| generated-artifact gate | `make verify-gen` | see gotcha 1 |

- **`make test-db`** runs the claim-spine DB tests against **PostgreSQL 18 + PostGIS**
  (`postgis/postgis:18-3.6`, `tests/db/conftest.py`) via testcontainers, so it **needs a running
  Docker daemon**. It sets `SIG_REQUIRE_DB_TESTS=1`, which makes a missing/unreachable daemon
  **fail loudly** instead of skipping (`tests/db/conftest.py:48`). It is not part of `make check`.
- Run one package's CLI with `uv run python -m <package> --help` (every stage is a plain CLI,
  SIG-ENG-013).

## Critical gotchas (most dangerous first)

1. **`verify-gen` fails on uncommitted generated artifacts — commit `ontology/generated` first.**
   `make verify-gen` regenerates and runs `git diff --exit-code -- pylock.toml ontology/generated`.
   If you regenerate but don't commit, the gate is red *because the tree is dirty*, not because the
   output is wrong. Commit the regenerated `ontology/generated` (and `pylock.toml`) then re-run.
   (Ledger LD-X03.)
2. **RDF/ontology generation is canonicalised.** The generators are otherwise non-deterministic;
   the ontology build canonicalises graphs via `rdflib.compare.to_canonical_graph`
   (`ontology/src/ontology/generate.py:85`) and pins `PYTHONHASHSEED=0` (`Makefile` `gen-ontology`).
   Don't "fix" ordering churn by hand — regenerate with the make target. (Ledger LD-X07.)
3. **The §47 package layout is frozen (SIG-ENG-012).** The top-level package names
   (`ontology db connectors parsing resolution reconcile inference tasks api exports orchestration
   policy ops evidence`, plus `web/`) must not be renamed or moved without an ADR;
   `tests/unit/test_package_layout.py` enforces it.

## Amending the specification (SIG-ENG-003)

`docs/2_canonical_design_spec.md` is a **build artifact**, not authored in place. To change a
requirement: edit the section source under `docs/research/_meta/spec_src/*.md`, run
`sh docs/research/_meta/spec_src/BUILD.sh` to reassemble the spec, and record the change in an ADR
(`docs/adr/`, SIG-ENG-003). Never edit `docs/2_canonical_design_spec.md` directly.

- **When a new ADR is added, add its Appendix F row in the same PR (SIG-ENG-039).** Appendix F
  (`spec_src/99a_appF_adr.md`) must stay in one-to-one correspondence with the `docs/adr/ADR-*.md`
  file set; likewise a PR that adds a requirement id must add its `spec_src` paragraph and Appendix
  F/coverage rows in the same PR. Enforced by `docs/build/tools/check_spec_src.py` (PR-invoked).

## Where things live

- **`docs/tickets/`** — the ordered ticket backlog, **committed** as the build's contract record
  (`docs/tickets/00_MANIFEST.md` is the order; each `PXX.Y` file is one ticket's contract). Ticket
  docs cite the canonical spec, they never restate its design.
- **`docs/build/`** — durable **build memory**: `docs/build/PLANNING_LEDGER.md`,
  `docs/build/BUILD_INDEX.md`, `docs/build/LEDGER_DEFERRALS.md`, `docs/build/DECISION_MEMO.md`,
  scoping artifacts, and later capstone/backlog reports. Post-build tickets cite these by path.
- **`.agents/scratch/`** — **gitignored** agent scratch (never committed): `ledgers/` (one
  `implement-spec_<PXX.Y>.md` per ticket), `pr/`, `tools/`, `fixtures/`, `logs/`, and `planning/`
  (only the live `orchestrate-build` machine ledger). See `.agents/scratch/README.md`.
- **`docs/adr/`** — Architecture Decision Records (index in `docs/adr/README.md`).

## Working conventions

- **Python is primary; TypeScript is confined to `web/`** (SIG-ENG-010).
- **Stacked-PR chain:** every ticket forks from the **current checkout** (the branch the previous
  ticket left checked out) — no `base_branch` argument. Between tickets stay on the previous
  ticket's branch so the next one stacks on it. No ticket merges, tags, or pushes `main`; the
  operator integrates the stack after the chain.
- **Append-only build memory:** never edit the content of a historical ledger or PR body — move or
  rename only, and record the mapping.

## Do / Don't

- **Do** run `make check` before every commit; commit regenerated artifacts before re-running it.
- **Do** add per-package `AGENTS.md` only where a package has non-obvious conventions.
- **Don't** edit `docs/2_canonical_design_spec.md`, `ontology/generated`, or the frozen §47 layout
  directly; go through the source + generator + ADR.
- **Don't** commit anything under `.agents/scratch/` or raw logs/PR bodies.
