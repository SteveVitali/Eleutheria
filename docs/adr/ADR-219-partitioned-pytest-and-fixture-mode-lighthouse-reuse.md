# ADR-219 — Partitioned pytest and fixture-mode Lighthouse pass reuse (P35.41a)

- Date: 2026-10-21
- Status: accepted
- Ticket: P35.41a (CI wait, phase 1, on `r11/P35.41a-ci-wait-phase-1`)
- Base: `r11/P35.41-freshness-semantics-v2`
- Related: SIG-ENG-046 (CI and local run the same commands), SIG-ENG-042
  (fail-closed gates; a vacuous pass is red), GL-CI-01 (the five required
  checks), ADR-151 (CI hygiene invariants), ADR-155 (public-surface budgets)

## Context

Every boundary read waits for the slowest required job. Two jobs dominate:

- `python` runs one serial `pytest` (~19.4 minutes of the job), and
- `web` runs two Lighthouse passes (~11 minutes), of which the fixture-mode
  `Performance budgets` step measures only committed site bytes plus fixture
  evidence — inputs a records-only push (docs/build minus docs/build/tools,
  docs/tickets, docs/adr) cannot change.

Actions minutes are free, so the cheap win is concurrency for pytest and a
*bounded* reuse of the fixture-mode measurement — never a broad reuse of any
verdict, and every non-performance gate untouched.

## Decision

**D1 — partitioned pytest.** The `python` job's Test step runs
`make test-par`, which dispatches `scripts/ci/pytest_partitions.py run`. The
committed table `scripts/ci/pytest_partitions.txt` names each partition's
directories; exactly one line is `*` ("every `testpaths` entry minus the
named directories"). The runner validates the table (`check` exits 2 with
every reason: missing/out-of-testpaths/equal-or-nested directories, zero or
two `*` lines), launches all partitions at once with `-p no:cacheprovider`
and a per-partition `--basetemp` under a fresh `RUNNER_TEMP` directory, and
replays each partition's log. A partition is green only when its recorded
exit code is 0 **and** its log carries pytest's final `=… passed …=` line —
a nonzero rc, pytest's 5, a missing rc file, or a missing summary line is
red; the runner never retries and reports `nproc=` plus one summary line
per partition. The union of partition collections equals the serial
collection as a multiset (verified per run). `make test` stays the serial
local gate; `make ci-local` reaches `test-par`. No new dependency.

Two measured constraints shape the table: `tests/db` and `tests/e2e` test
modules re-import helpers as `from conftest import …`, which resolves
through `sys.modules['conftest']` — a second directory's conftest in the
same partition can shadow it (observed: tests/api's conftest shadowed
tests/db's, 27 collection errors), so each pairs only with conftest-free
directories; and test files whose assertions are heap/session-sensitive keep
their serial collection context inside `*`.

**D2 — fixture-mode Lighthouse reuse.** `scripts/ci/perf_reuse.py` decides
whether the fixture-mode `Performance budgets` step may reuse a prior pass.
The fingerprint is the SHA-256 of NUL-joined `git ls-tree -r -z --full-tree`
entries whose paths lie outside the records set — mode, type, object id and
path all participate, so mode-only changes also invalidate. `decide` answers
`reuse` only when all fail-closed conditions hold: event `pull_request`;
same-repo head (forks get no secrets and never reach the cache); the
supplied fingerprint is valid 64-hex **and** equals a fresh HEAD scan; a
strictly-shaped nine-key record (base, head, pr, run, attempt, image,
imageFull, fingerprint, webSha) exists under `perf-pass-v1-<fingerprint>`
with matching fingerprint and PR number; HEAD contains no symlink or
gitlink; the coupling lint passes (every `web/` match of
`docs/(build|tickets|adr)/|"docs"` — less lines whose matches are all
`docs/build/tools/` — is an audited row of
`scripts/ci/perf_reuse_allow.txt`); and the runner image label matches the
record. Every other shape — push, dispatch, any exception — answers `run`,
and `decide` exits 0 either way so a crash fails closed, never silent.
`record` writes the nine-key record only for exactly-two-parent HEADs with
a valid `ImageOS-ImageVersion` label; the record and `actions/cache/save`
steps are same-repo-PR attempt-1 only and `continue-on-error` bookkeeping,
never gates. The reuse `if:` lives on exactly the fixture-mode
`Performance budgets` step; the export-mode budgets and Lighthouse, and
every other required check, run on every head. A `reuse` emits a
`ci-perf-reuse` notice naming the prior run and head — the skipped
measurement is always recorded as reuse, never presented as fresh.

## Consequences

- A records-only head waits on the `python` partition pole instead of two
  serial Lighthouse passes — roughly ten minutes instead of twenty; a code
  head pays the partition pole plus one fixture pass.
- No test changed and no required check weakened: all five required checks
  run on every head, and the reuse boundary is pinned by wiring tests (one
  reuse gate, decide ungated, restore/save `@v6`, record PR-only).
- The cache record is scoped to `perf-pass-v1-<sha256>`; an image bump or
  any non-records byte change misses and re-measures.

## Revisit trigger

Revisit if the runner image label scheme changes (the
`ImageOS-ImageVersion` pattern), if the records-path set changes
(docs/build minus tools, docs/tickets, docs/adr — e.g. a new records root),
if a `web/` code path legitimately reads a records path (the allow-list is
for non-read hits only), if partition flakiness exceeds a repair round a
month, or if a phase-2 ticket needs reuse of any gate other than the
fixture-mode performance step.
