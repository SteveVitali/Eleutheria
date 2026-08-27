# SPDX-License-Identifier: LicenseRef-SIG-Undetermined
# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final
# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md §42).
#
# One set of commands, used identically by humans and by CI (coverage guard):
# whatever CI runs, `make check` runs. Every §47 pipeline package is a plain CLI
# (SIG-ENG-013): `uv run python -m <package> --help`.

# Import names of the workspace's Python packages (the §47 layout minus the
# non-Python dirs web/ docs/ tests/). Kept in sync by tests/unit/test_package_layout.py.
PY_PACKAGES := ontology db connectors parsing resolution reconcile inference \
	tasks api exports orchestration policy ops
MYPY_TARGETS := $(foreach p,$(PY_PACKAGES),-p $(p))
# Python source this repo owns: each package's src tree, plus the test suite.
LINT_PATHS := $(foreach p,$(PY_PACKAGES),$(p)/src) tests

.PHONY: sync lint format-check typecheck test check lock export sbom gen verify-gen

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

## The full local gate — mirror of CI.
check: lint format-check typecheck test verify-gen

## Refresh the uv lockfile.
lock:
	uv lock

## Regenerate all committed generated artifacts (SIG-ENG-015/016 gate).
## Today the only generated artifact is the standards-based (PEP 751) lock
## export; later tickets add ontology-derived artifacts here.
gen: export
	@:

## Standards-based lock export (SIG-ENG-011): PEP 751 pylock.toml.
export:
	uv export --frozen --no-emit-project --format pylock.toml -o pylock.toml

## Verify committed generated artifacts match a fresh generation (SIG-ENG-016).
verify-gen: gen
	git diff --exit-code -- pylock.toml

## Software Bill of Materials (SIG-ENG-011), CycloneDX, generated per release.
## Run ephemerally via uvx (so it need not live in the runtime lockfile), against
## the project virtualenv that `make sync` populates.
sbom: sync
	uvx --from cyclonedx-bom cyclonedx-py environment .venv -o sbom.cdx.json
