# ADR-072 — Documentation freshness gates: two vendored detectors, `make docs-check`, and a CI step

- **Status:** Accepted
- **Phase / ticket:** P22.2 — Agent-facing documentation refresh (the `AGENTS.md` hierarchy + `CLAUDE.md` bridge)
- **Date:** 2026
- **Related / amends:** P22.1 (vendored the human-facing `check-repo-docs-freshness.sh` + `make docs-check-repo`); P19.1 (the first `AGENTS.md`); SIG-ENG-001 (the repo is executable from its documents), SIG-ENG-015/016 (the CI gate), SIG-ENG-031 (risk register); RISK-P22-01/02/03/04.

## Gate status (copied from the run contract)

- **None.** P22.2 has no human gate. The operator answered the one ticket option
  (clean-slate vs refresh): **REFRESH, not clean-slate** — keep P19.1's `AGENTS.md`, run the
  `agent-docs` skill in `mode=refresh deep=true`, preserve hand-written gotchas that still hold.

## Context

The repo is meant to be *executable from its documents* (SIG-ENG-001), yet documentation drift is
silent: research (DOCER, EMSE 2023) found broken references in ~29% of top-1000 GitHub repos,
typically unnoticed for years, precisely because checking was manual. SIG maintains **two** document
sets that drift independently — the human-facing corpus (README/CONTRIBUTING/CHANGELOG/`docs/**`,
refreshed by P22.1) and the agent-facing `AGENTS.md` hierarchy (this ticket) — and both had
accumulated stale references against the finished 65-ticket build. P22.1 vendored a deterministic
detector for the human docs and exposed `make docs-check-repo`, but left CI wiring to P22.2.

## Decision

1. **Vendor both detectors under `scripts/docs/`** (MIT, with a provenance header): P22.1's
   `check-repo-docs-freshness.sh` and, added here, `check-agent-docs-freshness.sh` (byte-for-byte
   from the `agent-docs` skill). Vendoring means the checks run without the skills installed.
2. **`make docs-check` runs BOTH** detectors over the whole repo (`.`); each is structural,
   read-only, and exits non-zero on a critical issue. `make docs-check-repo` / `make docs-check-agent`
   remain available individually.
3. **CI runs `make docs-check` on pull requests** — a dedicated `docs` job in
   `.github/workflows/ci.yml`, structural-only and LLM-free, so drift is caught at change time.
4. **`make docs-check` is NOT added to `make check`.** Measured locally, the two detectors together
   take ~30s (the agent detector's file-index walk alone is ~23s) — over the ~10s budget for the
   inner-loop gate — so it stays a CI/opt-in target. `make check` semantics are unchanged.
5. **The LLM-driven generation and `--deep` semantic verification stay human-triggered** (the
   `refresh-repo-docs` / `agent-docs` skills). Only the deterministic detectors are automated.

## Consequences

- Broken references, coverage gaps (a ≥5-source-file package with no `AGENTS.md`), and key-file/line
  drift now fail a PR check instead of rotting silently. Trust in the docs is defensible.
- A known detector quirk: `check-agent-docs-freshness.sh` excludes any path containing `/build/`
  (intended for build-output dirs), so backticked references to `docs/build/*.md` files read as
  "missing". The docs therefore reference `docs/build/` as a directory; contributors should keep that
  convention rather than "fixing" the vendored logic.
- Refresh cadence: per `docs/build/INTEGRATION_PLAN.md` §(d), a docs refresh (P22.1 then P22.2, both
  idempotent) is part of every release cut.

## Alternatives considered

- **A single merged detector.** Rejected: the two skills own distinct corpora and evolve separately;
  vendoring each verbatim keeps upstream parity and provenance clean.
- **Add `docs-check` to `make check`.** Rejected on the measured ~30s cost — it would slow the
  inner-loop gate every developer runs, for a check that only needs to gate merges.
- **Auto-fix drift in CI.** Rejected: generation/fixing is LLM-driven and needs human review; only
  the deterministic *detector* belongs in CI (per both skills' "Optional CI Integration").

## Revisit trigger

Revisit if the detectors' **false-positive rate exceeds 1 per PR** (e.g. the `/build/` exclusion or
reference heuristics flag valid docs often enough to erode trust), or if a third document set is
introduced that neither detector covers. At that point, either patch the vendored logic (recording
the deviation in the provenance header) or replace `make docs-check` with a maintained upstream.
