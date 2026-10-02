# ADR-191 — Lighthouse performance gate samples three runs, asserts the median (P34.2)

- Date: 2026-10-02
- Status: accepted (engineering; `live_verification=false` — CI policy, verified
  by the PR's own head-bound check-runs)
- Ticket: P34.2 (Round 11 / P34, row 202; requirement SIG-MEM-007; cited:
  SIG-ENG-042, SIG-ENG-046, SIG-UI-041, ADR-134)
- Base: `r11/P34.1-toolchain-pin-and-ci-hygiene` (Round-11 chain)

## Context

The `web` job's performance-budget step (`npm run check:perf` → `lhci autorun`)
collected **one** Lighthouse run per URL (`web/lighthouserc.json`
`numberOfRuns: 1`). Lighthouse scoring under simulated throttling is a sampled
measurement: the same bytes, re-measured on the same sha, occasionally produce
a `categories.performance failure for minScore` red that a same-sha re-run
clears. Five recorded instances — runs 35051006427, 35263896936, 35889213151,
36065771273 and 36338778274 (the `LH-PERF-1` allow-list entry's evidence) —
red-marked green work. Every one re-ran green, which is the signature of
sampling noise rather than a real regression: a real regression stays red
under re-run.

P34.2's flake policy (H2 §4.4, B-15) permits exactly one `gh run rerun --failed`
per head for allow-listed flakes — a *mitigation*, not a fix: each occurrence
still costs a boundary read, a re-run and a flake-log row, and a second
sampling failure on the same head is plain red. The contract directs the
flake to be stabilised by ADR: either `numberOfRuns: 3` with median
aggregation, or moving the score assertion to nightly while keeping per-PR
byte budgets.

## Decision

`web/lighthouserc.json` `collect.numberOfRuns` moves from `1` to `3`.

With three runs lhci asserts each assertion on the **median** run (its
aggregation for a multi-run collect), so a single outlier sample — the flake's
mechanism — no longer fails the build, while a real regression (all three
samples low, or the median below the floor) still fails. The budget matrix is
untouched: `categories.performance` stays `error` at `minScore 0.9` on public
content pages, byte ceilings and the island blocks of ADR-134/P32.15 are
byte-identical, and `/curate/**`'s accessibility floor and advisory
performance band are unchanged. **No threshold was loosened** — the change
moves the sampling noise floor only, which is exactly what the contract's
first option prescribes.

Cost: three Lighthouse collections per `check:perf` run instead of one — a
bounded, build-time cost on the `web` job.

## Alternatives considered

- **Move the score assertion to nightly, keep per-PR byte budgets** — rejected:
  the score is the cheap, per-PR signal that a page regression lands *with the
  change that caused it*; a nightly-only score assertion delays that signal by
  up to a day and widens the blamed change set to "everything since last
  night". The byte budgets alone do not capture what the score captures
  (main-thread work, layout stability).
- **Raise `numberOfRuns` past 3** — rejected: three is the smallest sample for
  which a median exists; more runs buy little flake suppression at a linear
  build-time cost.
- **Keep `numberOfRuns: 1` and rely on the one re-run per head** — rejected:
  the flake would still fire; B-15's re-run is the safety valve, not the fix.
- **Loosen the `minScore`** — forbidden: no gate is loosened to pass (CI-5);
  the flake was noise, not a budget that was too tight.

## Consequences

- A single outlier Lighthouse sample can no longer red a green PR; two-out-of-
  three samples below the floor — i.e. the median below it — still can.
- `LH-PERF-1` remains in `ci_flakes.toml` (its expiry is dated) as cover while
  the change beds in; a flake entry that stops matching is removed deliberately.
- The `web` job's `check:perf` step takes ~3× the Lighthouse collection time —
  still a fraction of the job.

## Revisit trigger

- `LH-PERF-1` fires again under three-run median — the noise floor is deeper
  than sampling (throttling variance across the runner fleet) and the gate
  needs a different statistic or a runner-pinning investigation.
- The `web` job's duration grows past what the round accepts — revisit the run
  count or move collection to a pre-warmed server render.
- lhci changes its aggregation for multi-run collects — the median assumption
  here must be re-verified.
