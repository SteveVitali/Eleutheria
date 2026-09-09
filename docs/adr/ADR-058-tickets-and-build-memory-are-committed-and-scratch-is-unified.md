# ADR-058: Tickets and build memory are committed; agent scratch is unified

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P19.1
- **Requirement ids:** SIG-ENG-001, SIG-ENG-003, SIG-ENG-012, SIG-ENG-031

## Context

The 46-ticket build chain (P00.1–P18.2) treated `docs/tickets/` as a **derived, gitignored** artifact
("regenerated from the canonical spec, not committed"). In practice the ticket contracts are **not
regenerable** — there is no decompose ledger or inputs on disk — and they are the only durable record
of each PR's contract (planning ledger T4). At the same time the build's memory was scattered and
uncommitted: ~44 run ledgers in three naming styles across two scratch roots (`.agents/scratch/` and a
root `scratch/`), plus PR-body/commit drafts, one-off tools, fixtures and ~7 MB of reproducible check
logs, and there was **no `AGENTS.md`** anywhere (agents onboarded from the README only, T15). The
post-build planning sessions (recorded in `docs/build/PLANNING_LEDGER.md`) decided to make this memory
durable before any capstone work (decisions T3 / T4 / §4.1 / §4.2 / §4.7).

## Decision

1. **Commit the ticket contracts.** Remove `docs/tickets/` from `.gitignore` and commit all 65 files
   (46 contracts + `00_MANIFEST.md` + `_TEMPLATE.md` + the 17 post-build P19.1–P21.9 contracts).
   `docs/tickets/` is the build's committed **contract record** from here on; P19+ tickets are appended
   in manifest table order. Ticket docs still **cite** the canonical spec and never restate its design
   (SIG-ENG-003); amendments go to `docs/research/_meta/spec_src/*.md` → `BUILD.sh` → an ADR.
2. **Commit the durable build memory under `docs/build/`** (§4.7): the planning ledger
   (`PLANNING_LEDGER.md`), `BUILD_INDEX.md`, `LEDGER_DEFERRALS.md`, the scoping artifacts, and
   `DECISION_MEMO.md`, with a `README.md`. Later tickets append their capstone/backlog/integration
   reports here.
3. **Unify agent scratch** into the single gitignored root `.agents/scratch/` with a fixed layout
   (`ledgers/ pr/ tools/ fixtures/ logs/ planning/` + `README.md`); one ledger per ticket named
   `implement-spec_<PXX.Y>.md`. Historical ledgers are **moved/renamed only** (append-only provenance,
   with the mapping recorded in `.agents/scratch/README.md`); logs are deleted (reproducible by
   `make check`). The live `orchestrate-build` machine ledger
   (`.agents/scratch/planning/sig-postbuild-build-ledger.md`) is the single exception — it stays
   gitignored and is neither committed nor moved.
4. **Introduce an `AGENTS.md` hierarchy** (SIG-ENG-031): a root `AGENTS.md` plus per-package docs for
   `web/`, `db/`, and `connectors/`, stating the gate (`make check`), the DB-test / `verify-gen`
   gotchas, the frozen §47 layout (SIG-ENG-012), the spec-amendment path (SIG-ENG-003), and the
   stacked-PR rule.

## Consequences

- `docs/tickets/` is **no longer derived-only**: it is a committed, first-class part of the repo and
  the audit trail of the build. The manifest's "gitignored" paragraph is replaced accordingly.
- Build memory is auditable in-tree and citeable by path; every post-build ticket references
  `docs/build/*` rather than transient scratch paths.
- Agents onboard from `AGENTS.md` (nearest-file-wins) rather than the README alone.
- No code or schema changed; `make check` is unaffected apart from the one parametrized
  revisit-trigger test this ADR itself adds (SIG-STORE-007, `tests/unit/test_policy_adrs.py`).
- Three small manifest/template defects are fixed alongside (LD-X09 `.devinignore`, LD-X10 the "32/34
  detectors" count, LD-X11 the template's "of 43" sequence), and two build gotchas are documented in
  `AGENTS.md` (LD-X03 `verify-gen` commit-state semantics, LD-X07 RDF canonicalisation).

## Revisit trigger

Revisit if raw run ledgers or PR bodies are ever wanted **in git** (this ADR deliberately keeps them
gitignored under `.agents/scratch/`, committing only the promoted build-memory artifacts under
`docs/build/`), or if the committed `docs/tickets/` record needs a different home or format.
