# ADR-013: uv as the workspace and lockfile tool

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-ENG-011
- **Spec:** docs/2_canonical_design_spec.md §47

## Context

A monorepo of many Python packages needs fast, reproducible dependency management with a committed lockfile and a standards-based export.

## Decision

Use uv for the workspace, the committed `uv.lock`, and a PEP 751 `pylock.toml` export; humans and CI run identical `make` targets.

## Consequences

Fast, reproducible, frozen installs; one toolchain. Adds a dependency on a relatively young tool (mitigated by the standards-based export).

## Alternatives considered

pip-tools + venv (slower, more moving parts); Poetry/PDM (heavier, or weaker workspace story at adoption time).

## Revisit trigger

uv's licence or maintenance changes adversely, or PEP 751 tooling in the wider ecosystem makes a different resolver clearly preferable.
