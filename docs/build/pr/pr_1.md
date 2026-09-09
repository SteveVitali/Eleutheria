Implements ticket **P00.1 — Repository skeleton and CI** (`docs/tickets/P00.1__repo-skeleton.md`), the first ticket in the 46-PR build chain. Stands up the monorepo skeleton every later ticket forks from. **No ingestion or domain code.**

## Summary
- **uv workspace** (SIG-ENG-011): a *virtual* root `pyproject.toml` defining the workspace + shared dev toolchain (ruff, mypy, pytest); committed `uv.lock`; a standards-based **PEP 751 lock export** (`pylock.toml`); and a CycloneDX **SBOM target** (`make sbom`).
- **§47 package layout** (SIG-ENG-012): the exact 16-entry layout as empty-but-real packages — 13 Python member packages (`ontology db connectors parsing resolution reconcile inference tasks api exports orchestration policy ops`), plus `web/` (TypeScript, SIG-ENG-010), `docs/`, `tests/`.
- **Plain-CLI convention + orchestrator boundary** (SIG-ENG-013): every package is runnable as `python -m <pkg>` and installs a `sig-<pkg>` console script; only `orchestration/` may import a workflow orchestrator, enforced by an AST test.
- **`policy/` as real, tested code** (SIG-ENG-014) — package + test, no logic yet.
- **CI** (SIG-ENG-015/016 wiring): GitHub Actions runs lint → type-check → test → a "generated artifacts match a fresh generation" gate, installing strictly from the committed lockfile.
- **Licence headers** on every source file (SPDX `LicenseRef-SIG-Undetermined`) + a placeholder `LICENSE` (final posture decided in P00.2).

## What changed
- Root: `pyproject.toml`, `uv.lock`, `pylock.toml`, `.python-version`, `Makefile`, `LICENSE`, `.gitignore`, `README.md` (layout + dev docs).
- 13 Python packages (`<pkg>/pyproject.toml`, `src/<pkg>/{__init__,cli,__main__}.py`, `py.typed`).
- `orchestration/src/orchestration/pipeline.py` — the orchestrator seam / single source of truth for orchestrator modules.
- `web/` TS placeholder; `.github/workflows/ci.yml`; `tests/` skeleton suite.

## Requirement IDs
Satisfies **SIG-ENG-010, SIG-ENG-011, SIG-ENG-012, SIG-ENG-013, SIG-ENG-014**; wires **SIG-ENG-015 / SIG-ENG-016**.

## Phase-gate (§51.3)
- Risk register **R-11 (zero-cost mode fails silently)** noted: CI runs on free GitHub Actions minutes on a public repo; the "bootstrap" cost scale (§50) remains order-of-tens-of-dollars. Keepalive / tested degraded mode (R-11 mitigation, §46.4) is owned by later ops tickets.

## Acceptance criteria → evidence
| AC | Status | Evidence |
|---|---|---|
| uv workspace resolves; lockfile committed; CI installs from lockfile | ✅ | `uv lock` resolves 26 pkgs; `uv.lock` committed; CI `make sync` = `uv sync --all-packages --frozen` |
| All §47 packages exist + import cleanly; test asserts set matches §47 | ✅ | `tests/unit/test_package_layout.py` (dirs exist; members == §47; each imports + has `__version__`) |
| Test asserts no package outside `orchestration/` imports the orchestrator | ✅ | `tests/unit/test_import_boundary.py` (AST scan) |
| CI runs lint + type-check + tests green on empty skeleton | ✅ | `.github/workflows/ci.yml`; `make check` green locally |
| §51.3 gate: CI green; requirement IDs in PR; R-11 noted | ✅ | this PR body |

## Verification (local: uv 0.12.6, Python 3.12.14)
- `make lint` — all checks passed
- `make format-check` — 46 files already formatted
- `make typecheck` — mypy: no issues in 40 source files
- `make test` — **104 passed**
- `make verify-gen` — `pylock.toml` regenerates identically (exit 0)
- `make sbom` — CycloneDX SBOM, 25 components

## Deviations
- Two `docs/` files (`2_canonical_design_spec.md`, `research/_meta/spec_src/96_partX_s51to54_plan.md`) had pre-existing uncommitted edits unrelated to this ticket; intentionally **not** included.

Generated with [Devin](https://devin.ai)
