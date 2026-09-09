# AGENTS.md — `tests/` (the whole-repo test suite)

## Purpose

pytest + Hypothesis (ADR-019) suite for every package, mirrored per package plus cross-cutting
`unit/`, `acceptance/`, `property/`, and the Docker-gated `db/` and `e2e/` suites. `make check` runs
this suite; CI runs the same. Nearest-file-wins: this file adds to the root `AGENTS.md`.

## Module Layout

```
tests/
├── support.py          shared constants (REPO_ROOT, the frozen §47 dir list)
├── unit/               cross-cutting invariants (package layout, ADR revisit triggers, …)
├── acceptance/         end-to-end acceptance checks (non-Docker)
├── property/           Hypothesis property tests
├── db/       (Docker)  claim-spine schema/RLS/append-only over PG18+PostGIS
├── e2e/      (Docker)  the composed-stack seams S1…S8 (LD-/xfail convention)
└── <pkg>/              one dir per package (api, connectors, exports, ops, …)
```

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `tests/support.py` | ~30 | `REPO_ROOT` + the exact §47 dir tuple used by layout tests |
| `tests/db/conftest.py` | ~230 | PG18+PostGIS testcontainer; `SIG_REQUIRE_DB_TESTS` fail-loud switch |
| `tests/e2e/test_composed_stack.py` | ~860 | the composed-stack seams + the `LD-`/xfail convention |
| `tests/unit/test_package_layout.py` | ~30 | asserts the frozen §47 layout (SIG-ENG-012) |
| `tests/unit/test_policy_adrs.py` | ~40 | asserts every ADR names a `## Revisit trigger` (SIG-STORE-007) |

## Build & Test

| command | what it runs |
|---|---|
| `uv run pytest` | the whole non-Docker suite (part of `make check`) |
| `uv run pytest tests/<pkg>` | one package's tests |
| `uv run pytest tests/unit/test_package_layout.py -q` | a single test file |
| `make test-db` | `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db` (**needs Docker**) |
| `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e` | the composed-stack e2e (**needs Docker**) |

## Critical Gotchas

1. **`tests/db` and `tests/e2e` skip silently without a Docker daemon.** A green `uv run pytest` on a
   Docker-less machine has **not** run them (`tests/db/conftest.py`). Set `SIG_REQUIRE_DB_TESTS=1`
   (as `make test-db` does) to turn a missing daemon into a hard failure, so the RLS/append-only and
   composed-stack suites can never silently skip.
2. **`tests/e2e` xfails carry an `LD-` reason and are flipped only by the closing ticket.** A
   never-yet-wired seam is an `xfail` whose reason begins with its `LEDGER_DEFERRALS` id
   (`^LD-[A-Z]+[0-9]+[a-z]?:`) — never a loosened or removed assertion. Don't flip one to a pass
   unless your ticket closes that seam.
3. **Layout/ADR invariants are enforced here.** `test_package_layout.py` fails if the frozen §47
   directory set changes without an ADR; `test_policy_adrs.py` fails if a new ADR lacks a revisit
   trigger. A new ADR file must carry `## Revisit trigger` or `make check` goes red.

## Terminology

- **Seam (S1…S8)** — a wiring boundary between two stages, verified once in `tests/e2e`.
- **xfail (`LD-…`)** — an expected failure standing in for a not-yet-wired seam, tagged by its
  `LEDGER_DEFERRALS` id.

## Do

- Put a package's tests in `tests/<pkg>/`; assert behaviour/contracts, not just code paths.
- Run `make test-db` (with Docker) before touching `db/` schema or the claim spine.

## Don't

- Don't loosen or delete an assertion to make a seam pass; record an unwired seam as an `LD-` xfail.
- Don't rely on a Docker-less `pytest` run to cover the DB/e2e suites.
