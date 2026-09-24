# Readout — GATE-G1 (REL.1 / GL-REL-01) — Integrate & release v0.1.0

- **Chain row:** P23.1 · **Kind:** gate marker (milestone, non-blocking) · **Gate register:** HG-05
- **Ticket:** `docs/tickets/P23.1__integrate-and-release-v0-1-0.md`
- **Dispositioned:** 2026-09-10 by orchestrate-build (operator-delegated per the resume prompt rule 3)

## Verdict: SKIPPED-BY-OPERATOR (deferred to post-chain operator action)

REL.1 is the operator's release action: re-run `docs/build/tools/merge_dryrun.sh`, merge PRs
#47–#68 bottom-up per `docs/build/INTEGRATION_PLAN.md §(d)` retargeting each base to `main`,
`make check` on `main`, `git tag -a v0.1.0`, `make sbom`, `gh release create v0.1.0`. **No worker
merges, tags, or pushes `main`** (mergePolicy: NONE; spec Appendix B item 1). Per the operator
resume prompt this milestone is explicitly deferred: recorded SKIPPED → RETURN PASS, the chain
continues (REL.1 is non-blocking — spec Part I §4: it may precede or follow the go-live work).

## What would pass it
The operator performs the merge/tag/release, records the outcome here as cleared with the `v0.1.0`
tag + `main` CI link and dates `docs/build/CHANGELOG.md 0.1.0`.

## Consequence recorded
Added to LEDGER RETURN PASS (`REL.1 / HG-05`). Not `blockedOn` (a deferred milestone is a pause,
not a block). No DEFERRALS row is scoped to release (DEFERRALS rule 4 satisfied).
