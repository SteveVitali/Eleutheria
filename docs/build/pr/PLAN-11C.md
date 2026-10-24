# PLAN-11C — Contracts for 11C rows + the K13 UX requirement families

**Twelve-context plan row (C1–C12, one shared branch, one PR).**
**Requirement ids:** the K13 UX families (written here — spec §56.8,
plan §6.2) · **SIG-OPS-007** (owner re-confirmed → P35.2) ·
**SIG-ENG-003** (cited — spec changes land through `spec_src` +
`BUILD.sh`) · **SIG-ENG-041** (cited — MISSING rows and routing) ·
**Ticket:**
`docs/tickets/340_PLAN-11C__contracts-for-11c-and-k13-families.md`
(manifest row 340; `decompose-spec mode=extend`) · **Base:**
`r11/P35.62-round10-production-candidate` (stacked; merge after
P35.62's chain) · **Gate:** none (`none (plan only, OM-03)` — the plan
cell, verbatim) · **Live stage:** none (`live_verification=false`;
this row writes contracts, it does not execute them) · **Production
mutations:** none · **OM-20:** not an OM-20 row — it drafts the 11C
list for GATE-G5, approves nothing · **CI config changed:** no.

## Why

Rows 344–420 of the Round-11 manifest are skeletons. Before GATE-G5
each must read as an execute-grade contract — gate status with the
operator's verbatim words and times, live stage/window/legs with their
re-run prompts, production mutations, `live:` edges, token-counted
Load lists, and requirement ids — so that GATE-G5's OM-20 list names
written contracts. Separately, the K13 UX requirement set (spec §56.8:
UXR-01…38 new requirements and UXR-A01…A13 adoption rows over the
K-series draft families) needs final ids so the 11C contracts can cite
them.

## What C1 ships (this push)

(to be filled at C1 close)

## Still owed on this branch (later contexts)

- C2–C11: the remaining 11C contracts (rows 347–420) in ≤ 8-row
  batches, in order.
- C12: the fresh-context Phase-4 sizing review — the 11C re-split
  decision with counts, the draft 11C OM-20 list for GATE-G5, the 11C
  ADR-171 outreach-owed list, and the carried placements.
- Closeout: run ledger + this file completed, BUILD_INDEX row under
  `## Round 11`, LEDGER advanced, README `rows 1-N` line, projection
  regenerated and verified.

## Local verification

(filled per context)

## Deviations

(none yet)
