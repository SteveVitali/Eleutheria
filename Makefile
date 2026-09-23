# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# One set of commands, used identically by humans and by CI (coverage guard):
# whatever CI runs, `make check` runs. Every §47 pipeline package is a plain CLI
# (SIG-ENG-013): `uv run python -m <package> --help`.

# Import names of the workspace's Python packages (the §47 layout minus the
# non-Python dirs web/ docs/ tests/). Kept in sync by tests/unit/test_package_layout.py.
PY_PACKAGES := ontology db connectors parsing resolution reconcile inference \
	tasks api exports orchestration policy ops evidence
MYPY_TARGETS := $(foreach p,$(PY_PACKAGES),-p $(p))
# Python source this repo owns: each package's src tree, plus the test suite.
LINT_PATHS := $(foreach p,$(PY_PACKAGES),$(p)/src) tests

.PHONY: sync lint format-check typecheck test test-db check lock export sbom gen gen-ontology verify-gen docs-check docs-check-repo docs-check-agent docs-check-build-memory

## Install every workspace member + the dev toolchain from the committed lockfile.
sync:
	uv sync --all-packages --frozen

## Lint + import-order.
lint:
	uv run ruff check $(LINT_PATHS)

## Formatting must already be applied.
format-check:
	uv run ruff format --check $(LINT_PATHS)

## Static type-check every Python package.
typecheck:
	uv run mypy $(MYPY_TARGETS)

## Run the test suite.
test:
	uv run pytest

## Run only the claim-spine database tests (PG18+PostGIS via Docker; P02.1).
## These skip if the Docker daemon is unreachable unless SIG_REQUIRE_DB_TESTS is
## set — which this target does, so a missing daemon fails loudly.
test-db:
	SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db

## The full local gate — mirror of CI.
check: lint format-check typecheck test verify-gen

## Refresh the uv lockfile.
lock:
	uv lock

## Regenerate all committed generated artifacts (SIG-ENG-015/016 gate):
## the standards-based (PEP 751) lock export plus every ontology-derived
## artifact (SQL DDL, JSON Schema, OWL/SHACL, Pydantic, docs, SKOS, registry).
gen: export gen-ontology

## Ontology artifacts from the single LinkML source (§20.1, ADR-007).
## PYTHONHASHSEED is pinned so set-ordered generator output is byte-deterministic.
gen-ontology:
	PYTHONHASHSEED=0 uv run python -m ontology generate

## Standards-based lock export (SIG-ENG-011): PEP 751 pylock.toml.
export:
	uv export --frozen --no-emit-project --format pylock.toml -o pylock.toml

## Verify committed generated artifacts match a fresh generation (SIG-ENG-016).
verify-gen: gen
	git diff --exit-code -- pylock.toml ontology/generated

## Both documentation freshness detectors (P22.2, ADR-072): the human-facing
## repo-docs detector (P22.1) plus the agent-facing AGENTS.md detector. Both are
## vendored under scripts/docs/, structural-only, read-only, and exit non-zero on
## a critical issue. Run over the whole repo (`.`). Wired into CI on pull requests.
docs-check: docs-check-repo docs-check-agent docs-check-build-memory

## Human-facing docs freshness check (P22.1): the vendored refresh-repo-docs
## detector over the in-scope doc corpus (README/CONTRIBUTING/CHANGELOG/docs).
## Read-only; exits non-zero on a broken reference.
docs-check-repo:
	bash scripts/docs/check-repo-docs-freshness.sh .

## Agent-facing docs freshness check (P22.2): the vendored agent-docs detector
## over the AGENTS.md hierarchy (broken references, key-file/coverage/line-count
## drift). Read-only; exits non-zero on a critical issue.
docs-check-agent:
	bash scripts/docs/check-agent-docs-freshness.sh .

## Build-memory layout check (P22.3 / build-memory v2, ADR-073): the vendored
## check-build-memory.sh validates the committed docs/build/ + docs/tickets/ +
## docs/adr/ layout (allowlist, ticket sequence, DEFERRALS ids, ADR index<->files,
## LEDGER key set, secret/size scans). Read-only; exits non-zero on a violation.
docs-check-build-memory:
	bash scripts/docs/check-build-memory.sh .

## Software Bill of Materials (SIG-ENG-011), CycloneDX, generated per release.
## Run ephemerally via uvx (so it need not live in the runtime lockfile), against
## the project virtualenv that `make sync` populates.
sbom: sync
	uvx --from cyclonedx-bom cyclonedx-py environment .venv -o sbom.cdx.json
