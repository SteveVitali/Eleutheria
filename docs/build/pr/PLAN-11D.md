# PLAN-11D — Contracts for 11D rows and the tail (rows 421–510)

**Twelve-context plan row (D1–D12, one shared branch, one PR).**
**Requirement ids:** the 11D-owned §56 ids — each written contract
stamps its own `Owner:` set (served) · **SIG-ENG-003 / SIG-ENG-041 /
SIG-ENG-042** (cited) · **OM-03 / OM-20** (the plan-row rules) ·
**U-009** (GATE-ANNOUNCE's never-auto posture) · **Ticket:**
`docs/tickets/418_PLAN-11D__contracts-for-11d-and-tail.md` (manifest
row 418; `decompose-spec mode=extend`) · **Base:**
`r11/P36.70-second-release-acceptance` (stacked; merge after
P36.70's chain) · **Gate:** none (`none (plan only, OM-03)` — the
plan cell, verbatim) · **Live stage:** none
(`live_verification=false`; this row writes contracts, it does not
execute them) · **Production mutations:** none · **OM-20:** not an
OM-20 row — it drafts the 11D list for GATE-G6, approves nothing ·
**CI config changed:** no.

## Why

Rows 421–510 of the Round-11 manifest were `Kind: skeleton`
placeholders — the whole of sub-round 11D (P37 hardening/lifecycle,
the keyed-API unblocks, the entity/graph/map tails, the coverage
closeout, the UX capstone journeys) plus the P38 tail (capstone-lite,
reconcile, docs, announce-readiness and both closing gate markers).
Before GATE-G6 each must read as an execute-grade contract — the
operator's verbatim gate words and times, live stage/window/legs with
re-run prompts, production mutations, token-counted Load lists and
requirement ids — so that GATE-G6's packet (drafted by P36.73) can
cite written contracts for its 11D OM-20 list.

## What this branch ships (D1–D12, all landed)

- **D1–D10** — full contracts for rows 421–500 in ≤ 8-row batches:
  the hardening block (P37.3–P37.8 incl. the OM-20 named mutations),
  P37.71's true-deletion path (the sole SIG-STORE-011 exception —
  constitutional posture verbatim), the deferral-closing rows
  (`D-FEDERAL.1-1` → P37.11, `D-SOURCES.7-2` → P37.12,
  `D-SOURCES.8-2` → P37.70, `D-P32.18/19/20/21-1` → P37.16a/b,
  `D-P32.16-1` → P37.59), the entity/graph/map tails, the Wave-D
  screened lanes (flips stay the operator's OP-26 lines), the P37.54
  activation (ING-GO-D + HG-11 windows verbatim), the release cut /
  HG-11 readout pair (P37.65a/b), the closeout rows and the
  P37.68a–d UX capstone set (OP-22 requested, never simulated).
- **D11** — the tail: capstone-lite P38.1a/b, closure P38.2, the
  GATE-ACCEPT-R11 and GATE-ANNOUNCE markers (hand-authored; U-009's
  guard sentence, S6-F3's REVIEW-R11 precondition, the S6R-18 waiver
  keep/lift lines, the S6R-19 re-anchoring rule — all verbatim), the
  P38.3a–c reconcile triple, P38.4 docs, P38.5 announce-readiness.
- **D12** — the fresh-context Phase-4 sizing review: no skeletons,
  no forward deps, all 90 Load lists under the ~150k ceiling (largest
  ≈ 35k tokens ÷3); the §8.1 re-split rule evaluated with counts —
  **76 engineering rows / 65.0 runs, not fired**; the draft 11D
  OM-20 list (15 rows, each traceable to a written `Production
  mutations` header; `expires:` GATE-ACCEPT-R11); the 11D
  outreach-owed list (19 acquisition/connector rows — ADR-171's
  Stage-0 set owed, never stamped); the placements audit. Full text:
  `docs/build/runs/PLAN-11D.md`.

## Requirement index + manifest

`docs/tickets/REQUIREMENT_INDEX_R11.md` regenerated after the last
contract landed (`req_index.py check` — `req_index: current`). The
manifest's `## Decomposition decisions` gains the D12 record —
counts, watch/flag set, OM-20 list summary, dispatch actual.

## Verification

- `python3 docs/build/planning/2026-09-30-next-phase/tools/s13/gen_t3.py check` — 310 Round-11 rows, 0 errors
- `bash scripts/docs/check-build-memory.sh .` — no violations (37 pre-existing warnings, unchanged class)
- `python3 docs/build/planning/2026-09-30-next-phase/tools/s13e/req_index.py check` — `req_index: current`
- docs gates (`ledger_contract`, `return_pass`, `obligation_events`, `memory_guard all --staged`, trailers, live-claims corpus+range) — see commit record
- `make check` + `make docs-check` — see commit record

## Dispatch note

The plan cell's "one fresh sub-agent each" fan-out ran as the D1–D12
sequence inside one dispatched worker session; each batch kept its
≤ 8-row seam (D11 the 10-row tail), per-batch load records and
`date -u` stamps — the sizing rule held per batch. Recorded, not
pretended separate.
