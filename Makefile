# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# One set of commands, used identically by humans and by CI (SIG-ENG-046,
# P34.1): `make check` is the fast gate — the `python` job's commands;
# `make ci-local` runs all five CI jobs (python, docs, composed, security, web).
# Every §47 pipeline package is a plain CLI (SIG-ENG-013):
# `uv run python -m <package> --help`.

# Import names of the workspace's Python packages (the §47 layout minus the
# non-Python dirs web/ docs/ tests/). Kept in sync by tests/unit/test_package_layout.py.
PY_PACKAGES := ontology db connectors parsing resolution reconcile inference \
	tasks api exports orchestration policy ops evidence
MYPY_TARGETS := $(foreach p,$(PY_PACKAGES),-p $(p))
# Python source this repo owns: each package's src tree, plus the test suite.
LINT_PATHS := $(foreach p,$(PY_PACKAGES),$(p)/src) tests

.PHONY: sync lint format-check typecheck test test-db check ci-local lock export sbom gen gen-ontology verify-gen docs-check docs-check-repo docs-check-agent docs-check-build-memory docs-check-memory docs-check-spec docs-check-matrix docs-check-trailers security-scan scan-secrets scan-licenses audit-deps

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

## The fast local gate — the `python` CI job's commands.
check: lint format-check typecheck test verify-gen

## Local mirror of all five CI jobs (P34.1 / SIG-ENG-046, ADR-151). Runs the
## jobs' own commands: the SIG_REQUIRE_DB_TESTS suite and docs, security,
## composed (web deps present) and web gates. Needs Docker (tests/db + tests/e2e)
## and a Node/npm matching web/.nvmrc + package.json `engines` — `engine-strict`
## fails the web steps on drift. The docs job's range checks judge CHANGE_RANGE
## when set, else this branch's unpushed commits (origin/<branch>...HEAD), else
## the last commit — the same records the PR-range and push first-parent steps
## judge in CI.
ci-local: sync
	$(MAKE) lint format-check typecheck
	SIG_REQUIRE_DB_TESTS=1 TESTCONTAINERS_RYUK_DISABLED=true $(MAKE) test
	$(MAKE) verify-gen
	$(MAKE) docs-check
	bash scripts/docs/check-build-memory.sh .
	@range="$(CHANGE_RANGE)"; \
	if [ -z "$$range" ]; then \
	  base="$$(git rev-parse -q --verify "origin/$$(git branch --show-current)" 2>/dev/null || git rev-parse HEAD^)"; \
	  range="$$base...HEAD"; \
	fi; \
	echo "ci-local: build-memory history + trailer range $$range"; \
	bash scripts/docs/check-build-memory.sh . --range "$$range" --json docs/build/logs/build-memory-history.json && \
	python3 docs/build/tools/check_trailers.py --range "$$range" --json docs/build/logs/trailer-check.json && \
	{ base="$${range%%...*}"; \
	  echo "ci-local: recorded-CI verifier over $$base"; \
	  python3 docs/build/tools/verify_recorded_ci.py --diff-base "$$base" --json docs/build/logs/recorded-ci-verify.json; }
	@# The CI jobs' drift gate is `git diff --exit-code` (the checkout is clean, so
	@# worktree==index). Locally the tree is dirty by construction — the same
	@# predicate is "does the pinned npm rewrite the file": hash-stability across
	@# the regeneration, green even over an intentional uncommitted regen.
	@before="$$(git hash-object web/package-lock.json)"; \
	npm --prefix web install --package-lock-only --ignore-scripts; \
	after="$$(git hash-object web/package-lock.json)"; \
	echo "ci-local: lockfile stability $$before -> $$after"; \
	[ "$$before" = "$$after" ] || { echo "ci-local: the pinned npm would rewrite web/package-lock.json" >&2; exit 1; }
	npm --prefix web ci
	SIG_REQUIRE_DB_TESTS=1 TESTCONTAINERS_RYUK_DISABLED=true uv run pytest tests/e2e
	$(MAKE) scan-secrets
	uv run pytest tests/connectors/test_secrets.py::test_gcp_project_id_is_env_resolved_not_committed
	$(MAKE) scan-licenses
	@# P34.2: the per-PR npm advisory gate — production deps, high+; the same
	@# driver the `security` job runs, reports into docs/build/logs (gitignored).
	bash scripts/ci/npm_audit_gate.sh --out docs/build/logs
	npm --prefix web run typecheck
	npm --prefix web run test:unit
	npm --prefix web run build
	npm --prefix web run check:licenses
	npm --prefix web run test:e2e
	npm --prefix web run check:perf

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
## Round 11 (SEED-02b; B4 G7 item 1): docs-check also runs the build-memory
## history guard, the spec-source checker and the coverage-matrix checker — all
## stdlib python3, so the uv-less CI `docs` job runs them too.
docs-check: docs-check-repo docs-check-agent docs-check-build-memory docs-check-memory docs-check-spec docs-check-matrix

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
## P32.8 (SIG-MEM-003): the JSON report goes to the caller-selected, per-worktree
## gitignored logs path — never a shared /tmp file across concurrent worktrees.
docs-check-build-memory:
	bash scripts/docs/check-build-memory.sh . --json docs/build/logs/build-memory-check.json

## The change judged by the history guards (SEED-02b). Empty = the uncommitted
## working tree; CI sets the PR range: CHANGE_RANGE=<base.sha>...<head.sha>.
CHANGE_RANGE ?=

## Build-memory history guard (Round 11 SEED-02; B4 G1/G2/G4, BM-HIST-01): judges
## the lines a change adds or removes in build-memory records — record dates,
## append-only regions, record shape, gate records, readouts. With CHANGE_RANGE the
## vendored validator's history mode runs (check-history.sh hands off to
## docs/build/tools/memory_guard.py); without it memory_guard.py judges the
## uncommitted working tree against HEAD. Exits 1 violation / 3 vacuous / 5 unknown
## (shallow clone, bad range) are all red.
docs-check-memory:
ifeq ($(strip $(CHANGE_RANGE)),)
	python3 docs/build/tools/memory_guard.py all --worktree --json docs/build/logs/memory-guard.json
else
	bash scripts/docs/check-build-memory.sh . --range $(CHANGE_RANGE) --json docs/build/logs/build-memory-history.json
endif

## Spec-source checker (P20.2, SIG-ENG-039): the canonical spec is a byte-identical
## BUILD.sh concatenation of docs/research/_meta/spec_src/, Appendix F lists every
## ADR file, the requirement-id count and reference closure hold.
docs-check-spec:
	python3 docs/build/tools/check_spec_src.py

## Coverage-matrix checker (P19.2): row count, ids defined in the spec, enums,
## routing and evidence rules of docs/build/COVERAGE_MATRIX.csv.
docs-check-matrix:
	python3 docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv

## OM-01 commit-trailer check (SEED-02b; plan §3.3, A-21): every commit of
## CHANGE_RANGE carries a recognised harness trailer or is an operator commit.
## Needs CHANGE_RANGE (e.g. CHANGE_RANGE=origin/<base>...HEAD); CI passes the PR range.
docs-check-trailers:
ifeq ($(strip $(CHANGE_RANGE)),)
	@echo "docs-check-trailers: set CHANGE_RANGE=<base>...<head> (the commits to judge)" >&2; exit 2
else
	python3 docs/build/tools/check_trailers.py --range $(CHANGE_RANGE) --json docs/build/logs/trailer-check.json
endif

## The CI.1 / GL-CI-01 scanning gates (ADR-078) — the same commands CI runs.
## `security-scan` runs all three; the nightly workflow does the same. The two
## offline scanners run on every PR; `audit-deps` needs network (OSV advisory
## DB) so it rides the nightly.
security-scan: scan-secrets scan-licenses audit-deps

## Tracked-file secret scan — high-confidence credential shapes, no literals
## echoed (HG-09: secrets are env-only; a committed secret is a permanent leak).
scan-secrets:
	uv run python scripts/ci/secret_scan.py

## Python dependency licence gate — the SIG-UI-039 excluded categories plus a
## review-required fail on unresolvable licences and on new strong-copyleft deps.
scan-licenses:
	uv run python scripts/ci/license_scan.py

## Dependency vulnerability audit — uv export → uvx pip-audit (needs network).
audit-deps:
	bash scripts/ci/dep_audit.sh

## Software Bill of Materials (SIG-ENG-011), CycloneDX, generated per release.
## Run ephemerally via uvx (so it need not live in the runtime lockfile), against
## the project virtualenv that `make sync` populates.
sbom: sync
	uvx --from cyclonedx-bom cyclonedx-py environment .venv -o sbom.cdx.json
