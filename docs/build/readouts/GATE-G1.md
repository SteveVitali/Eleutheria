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

## Addendum — DATE CORRECTION (SEED-08, appended 2026-10-01T08:21:03Z; ADR-146; append-only)

- *Agent record (labelled): written by Claude Code, harness `claude-code/claude-opus-5-5/subagent`, Round-11 Stage-B unit SEED-08.* The text above is unchanged; this changes no status.
- **DC-RO-01.** Line 5's disposition date is a Round-3 "chain date": recorded 2026-09-10 → true 2026-09-13T19:40:01Z (retro: the writing commit `eb72be5f`; `docs/build/runs/P21.5.md` line 23: "Environment clock read 2026-09-13; chain date for this re-run = 2026-09-10"). Register rec 1019.
- **Harness and model (B7 §3 S4).** The disposition was written in the Devin CLI session `polydactyl-author` with model `claude-opus-4-8-medium` (retro: B7 §1–§3). It applied a disposition the orchestrator recorded under the resume prompt's rule 3, not an answer given at this gate's pause. The annotation of the restored GATE DECISIONS block in `docs/build/LEDGER.md` (SEED-06) classes this gate's restored entry R37 as clock-false.
