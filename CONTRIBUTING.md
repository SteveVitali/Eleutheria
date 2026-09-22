<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Contributing to SIG

Thanks for helping build the Surveillance Infrastructure Graph. This project is **evidence-first and
append-only**; the same discipline applies to the code and docs. Please read
[`AGENTS.md`](./AGENTS.md) (the agent/developer orientation) and the governance policies under
[`docs/governance/`](./docs/governance/) before contributing — Part VIII of the spec (safety,
publication policy, threat model) is **binding, not aspirational**.

## Setup

The repo is a [**uv**](https://docs.astral.sh/uv/) workspace. Install everything from the committed
lockfile:

```sh
make sync          # uv sync --all-packages --frozen
```

A running **Docker daemon** is needed for the claim-spine (`tests/db`) and composed (`tests/e2e`)
suites, which stand up PostgreSQL 18 + PostGIS via testcontainers.

## The gate — `make check`

`make check` is the single CI-mirrored gate (`.github/workflows/ci.yml` runs the same targets). Run
it before every commit; it must be green.

```sh
make check         # lint (ruff) + format-check + typecheck (mypy) + pytest + verify-gen
```

Other useful targets:

```sh
make test-db       # claim-spine DB tests on PG18 + PostGIS (needs Docker)
make lock          # refresh uv.lock after changing a dependency
make export        # regenerate the PEP 751 lock export (pylock.toml)
make sbom          # produce a CycloneDX SBOM (cut per release)
```

Every §47 pipeline package is a plain CLI (SIG-ENG-013):

```sh
uv run python -m policy --help      # (any of the 14 members: ontology, db, connectors, …, evidence)
```

The composed end-to-end suite:

```sh
SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra    # needs Docker
```

> **`verify-gen` gotcha.** `make verify-gen` regenerates `pylock.toml` and `ontology/generated` and
> runs `git diff --exit-code`. If you regenerated but did not commit, the gate is red because the
> tree is dirty — commit the regenerated artifacts, then re-run.

## The stacked-PR workflow

The build is a chain of reviewable PRs (`docs/tickets/00_MANIFEST.md` is the order). Each ticket
**forks from whatever branch is currently checked out** and opens a PR based on it, so the PRs
**stack** — you do not merge one before starting the next. Branch names are `devin/<pxx-y-slug>`
(more generally `username/short-description`).

**No contributor branch merges to `main`, tags a release, or pushes `main`.** Integration is a
single **operator action after the chain**, following the copy-pasteable procedure in
[`docs/build/INTEGRATION_PLAN.md`](./docs/build/INTEGRATION_PLAN.md) §(d): re-run the read-only merge
dry-run, merge the open PRs bottom-up, `make check`, then cut the tag and release.

```sh
sh docs/build/tools/merge_dryrun.sh   # read-only proof the open-PR stack integrates cleanly
```

History is **append-only** (P1–P3): never force-push or rewrite a shared branch; roll back with
`git revert`, not `git reset --hard`.

## Amending the specification (SIG-ENG-003)

`docs/2_canonical_design_spec.md` is a **build artifact** — never edit it directly. To change a
requirement: edit the section source under `docs/research/_meta/spec_src/*.md`, reassemble the spec,
record the change in an ADR under `docs/adr/`, and — because SIG-ENG-039 requires it — add the ADR's
**Appendix F row in the same PR** (and, if you add a requirement id, its `spec_src` paragraph and
Appendix F/coverage rows in the same PR):

```sh
sh docs/research/_meta/spec_src/BUILD.sh              # reassemble docs/2_canonical_design_spec.md
uv run python docs/build/tools/check_spec_src.py     # byte-clean rebuild + Appendix F ↔ docs/adr/ + id count
```

## Licence headers

SIG is a multi-licence project (SIG-LIC-005; see [`LICENSE`](./LICENSE)): **code is Apache-2.0**, data
is CC-BY-4.0 (ODbL/CC-BY-SA for the separate compartments), documentation is CC-BY-4.0, and
ontology/vocabularies are CC0-1.0. **Every source file carries an SPDX header.** Match the header of
the files around your change, e.g. for code:

```python
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
```

The `web/` dependency licence gate is OSI-only and enforced in CI; do not add a CC-BY-NC /
source-available / BUSL dependency.

## Pull requests

- Keep the PR scoped to one ticket/change; write a descriptive summary and cite the spec ids /
  ADRs it touches.
- `make check` must be green; new requirements need tests; deviations need an ADR; update the
  traceability and risk register (the §51.3 phase gate).
- Be mindful of the safety rules in `docs/governance/` — SIG documents **institutions and
  infrastructure, not people**.
