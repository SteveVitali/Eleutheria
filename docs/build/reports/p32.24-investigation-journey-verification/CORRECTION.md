# CORRECTION — P32.24 investigation-journey acceptance portfolio (a fixture run)

Written 2026-10-01T08:21:03Z (`date -u`) by Claude Code, harness `claude-code/claude-opus-5-5/subagent`, Round-11 Stage-B unit SEED-08 (ADR-146 Decisions 2 and 4; B1 §5.5). **Every other file in this directory is kept byte-for-byte**: they are historical run evidence whose digests later records cite. Nothing here re-runs or regenerates them; the code fix and superseding artifacts belong to P34.22a/b. This file is append-only.

## What was fixture

- The whole run (`README.md`: `live_verification=false` — offline over committed bytes and a throwaway PG18 container; nothing fetched, published or activated). The record-layer journeys ran on a declared acceptance corpus (`sig.journey-corpus/1`, built by the run), and the release subject was the committed P32.23a candidate `p-17b713…`, verified read-only — a fixture build with 0 released records (F-15).
- The run: PR #181 (`createdAt` 2026-09-28T03:08Z), implementation `1c926c95` (2026-09-28T03:08:05Z), closeout `da146260`; executed in the Devin CLI session `carefree-caption`, model `swe-2-high` (B7 §3 S9).

## What was claimed on it

- `docs/build/COVERAGE_MATRIX.csv` records `SIG-FIND-007` MET by P32.24 on this portfolio (F-16's bounded-scope pattern); the Round-11 re-verdicts under ADR-150 (B-5) replace that headline, and ACCEPT-R10's "34 MET" that included it is superseded (C-13, 2026-10-01T05:03:05Z).
- The portfolio's checks that name the deferral date carry the date the S3 deferral was recorded with, not the time it was given — table below. The candidate it verified is superseded (B-4, 2026-10-01T04:32:16Z; `docs/build/reports/p32.23a-release-candidate/CORRECTION.md`).

## Date corrections (register `docs/build/reports/memory-repair/date_corrections.csv`)

| file · field / line | recorded → true (UTC) | evidence | register recs |
|---|---|---|---|
| `JOURNEY_PORTFOLIO.json` L1; `JOURNEY_PORTFOLIO.md` L37 | S3 deferral: recorded 2026-10-19 → true 2026-09-28T01:15:49Z (B7; before `a33cd6ec` 01:27:21Z) | commit a33cd6ec "operator defers S3 human-eval spine" (local 2026-09-27 21:27 -04:00) | 372, 373 |
