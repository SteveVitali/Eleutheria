# ADR-151 — Toolchain pin and CI truth (P34.1)

- Date: 2026-10-01
- Status: accepted (engineering; `live_verification=false` — CI policy, verified
  by the PR's own head-bound check-runs)
- Ticket: P34.1 (Round 11 / P34, row 201; requirement SIG-ENG-046; plan §7
  assigns this number; cited: SIG-MEM-007, SIG-MEM-012, SIG-ENG-040)
- Base: `r11/seed` (Round-11 chain base)

## Context

CI and local runs drifted silently in four ways at once. The runner label
`ubuntu-latest` moves to Ubuntu 26 on 2026-10-19 (S6R-27, FEA-16 — the seed
already pinned `ubuntu-24.04` on every job), Node was a floating major (`"22"`),
npm was whatever the runner bundled, and uv was pinned in the workflows but not
for the local developer. `web/package-lock.json` could be regenerated under a
different toolchain than CI's with no gate to notice (H1 §2a's recorded
lockfile-failure history). `nightly.yml` ran every stage through `| tee` under
the runner's default `bash -e` — **without** `pipefail`, so a red stage exited
0 through `tee` and the nightly report could not see it (NEW-3). PR-only guards
(the build-memory history guard, the OM-01 trailer check) never judged pushes
to `main`, and `cancel-in-progress: true` tore down an in-flight run for a push
to `main` — a landed commit could exist with no completed CI run at all.
Finally `Makefile` claimed "whatever CI runs, `make check` runs" while `check`
ran only the python job.

## Decision

One pinned toolchain, identical locally and in CI, and CI policy that treats a
run's verdict as truth:

- **Node/npm.** `web/.nvmrc` pins the exact Node 24 LTS (`24.21.0` at ticket
  time — the lowest line every engine in the lockfile admits;
  license-checker-rseidelsohn 5.0.1 needs node ≥ 24 / npm ≥ 11);
  `web/package.json` carries `"engines": {"node": ">=24 <25", "npm": ">=11 <12"}`
  and `"packageManager": "npm@11.21.0"`; `web/.npmrc` sets `engine-strict=true`
  so a drifting local toolchain fails installs instead of producing a different
  lockfile. Every `setup-node` step resolves `node-version-file: web/.nvmrc` and
  is followed by an explicit `npm install -g` of the `packageManager` npm;
  every node-using job prints `node -v` / `npm -v` so the log records what ran.
- **Lockfile truth.** `web/package-lock.json` was regenerated exactly once
  under the pinned toolchain (recorded in the run ledger); a CI step
  `npm install --package-lock-only --ignore-scripts` + `git diff --exit-code`
  fails at PR time on any lockfile the pinned npm would write differently.
  Dependency installs are `npm ci` only — never `npm install`.
- **uv/Python.** `[tool.uv] required-version = "==0.12.6"` in `pyproject.toml`;
  `setup-uv` installs the same version in every workflow. `.python-version`
  stays a minor pin (`3.12`) — uv resolves and manages the interpreter, so the
  effective interpreter is already identical local/CI.
- **Runner/actions.** Every job stays `runs-on: ubuntu-24.04`; the actions
  (`checkout@v7`, `setup-node@v7`, `upload-artifact@v7`, `setup-uv@v10.2.0`) are
  the majors whose runtimes are Node 24, verified against their manifests at
  ticket time.
- **Pipefail.** Every workflow sets `defaults: run: shell: bash` (the runner's
  `bash --noprofile --norc -eo pipefail`), so a failure on the left of any pipe
  fails the step — nightly's `| tee` stages now report truth.
- **Runs that must complete.** `cancel-in-progress:` is
  `${{ github.event_name == 'pull_request' }}` — superseded PR runs may be
  cancelled; a run for a push to `main` never is, and the scheduled/dispatch
  workflows (`nightly`, `keepalive`, `observability`, `reingest`) set
  `cancel-in-progress: false` so a started sweep completes rather than leaving
  an unmeasured gap.
- **The `docs` job judges pushes too.** It runs on `pull_request` and on pushes
  to `main` (CF-01): the history guard takes the landed head's first-parent
  diff and the trailer check takes the push range (`event.before...sha`, the
  landed head as fallback) — a change cannot dodge the guards by merging.
- **`make ci-local`.** Runs the five jobs' commands locally — the
  `SIG_REQUIRE_DB_TESTS=1` suite, `docs-check` plus the history/trailer range
  checks, the scans, composed `tests/e2e` with web deps installed, and the web
  check + perf; a parity test maps every `run:` command in `ci.yml` to it.
- **CI truth.** Check-runs are read head-bound (per-head SHA) — never a run
  list or a display name; a red, pending or unreadable required check blocks
  closeout. Flakes ride an allow-list with at most one re-run per head
  (B-15; the recorded `ci_flakes.toml` verifier is P34.2's). A CI outage is a
  verbatim, time-boxed operator waiver — never a skipped gate. Tests assert
  invariants (structure and policy), never a living record's current value
  (SIG-ENG-040).

## Consequences

- Local and CI toolchains are one pin: `engine-strict` and `required-version`
  refuse drift, and the lockfile-diff gate makes a mismatched lockfile red at
  PR time instead of at the next regeneration (H1 §2a).
- `nightly`'s `| tee` stages can now go red — the report sees real outcomes.
- A push to `main` always carries a completed CI run, and the docs guards judge
  it — the last verifiable commit on `main` is always the landed head.
- `Makefile`'s "mirror of CI" claim is corrected: `check` is the python job;
  `ci-local` is the five-job mirror.
- The pre-2026-10-19 deadline is a landing deadline only; if it slips, the
  seed's `ubuntu-24.04` pins remain as the fallback (FEA-16).

## Alternatives considered

- **corepack for the npm pin** — rejected for now: `npm install -g` of the
  `packageManager` version is one explicit step and works without enabling
  corepack on the runner; recorded here so a later move is a decision, not
  drift.
- **Bump `@types/node` to 24** — deferred: it is a dev-typings package with no
  engine bound; the conservative 22 typings admit fewer APIs than the runtime
  provides, never more.
- **Keep PR-only guards** — rejected (CF-01): landed-but-unjudged commits are
  exactly the gap the seed left open.
- **An exact Node 22 pin + a Node-22-capable license-checker** (the contract's
  fallback) — not taken: Node 24 satisfied every engine in the tree, verified
  against the committed lockfile.

## Revisit trigger

- `ubuntu-24.04` approaches its own move (the Ubuntu 26 runner migration is a
  later ticket's work — this pin must be re-cut when the floor moves).
- Node 24 leaves LTS (October 2028), or npm 11 is superseded and
  `packageManager` must move majors.
- A gate added here is loosened — the drift check removed, pipefail narrowed to
  `pipefail`-only shells, a scheduled workflow made cancellable again, or the
  `docs` job re-scoped off `push` — or a flake list grows past one re-run per
  head (P34.2's `ci_flakes.toml`).
- The head-bound check reader cannot read the checks (API drift): CI truth then
  fails closed, never silently.
