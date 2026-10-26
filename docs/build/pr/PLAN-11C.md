# PLAN-11C — Contracts for 11C rows + the K13 UX requirement families

**Twelve-context plan row (C1–C12, one shared branch, one PR).**
**Requirement ids:** the K13 UX families (written here — spec §56.8,
plan §6.2; 174 new final ids) · **SIG-OPS-007** (owner re-confirmed →
P35.2) · **SIG-ENG-003** (cited — spec changes land through `spec_src`
+ `BUILD.sh`) · **SIG-ENG-041** (cited — MISSING rows and routing) ·
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

Rows 344–420 of the Round-11 manifest were skeletons. Before GATE-G5
each must read as an execute-grade contract — gate status with the
operator's verbatim words and times, live stage/window/legs with their
re-run prompts, production mutations, `live:` edges, token-counted
Load lists, and requirement ids — so that GATE-G5's OM-20 list names
written contracts. Separately, the K13 UX requirement set (spec §56.8:
UXR-01…38 new requirements and UXR-A01…A13 adoption rows over the
K-series draft families) needed final ids so the 11C contracts can
cite them.

## What this branch ships (C1–C12, all landed)

- **C1** — the K13 UX requirement families appended to the spec
  through `spec_src` + `BUILD.sh` (§56.11; 174 new final ids —
  `SIG-UI-051…156`, `SIG-GEO-014`, `SIG-EXPORT-014/015`, and the new
  prefixes `SIG-SRCH/JUR/DSRC/WATCH/EVUI/RQ-*`; the draft→final map at
  `docs/build/reports/plan-11c/K13_id_map.csv`; prefixes registered in
  §0.3; an Appendix G correction row; 174 MISSING coverage rows +
  `coverage-assessment/1` records routing each id to an unlanded 11C
  row; `check_spec_src`'s fold-back expectation updated 820→994) —
  plus contracts 344–346.
- **C2–C9** — contracts 347–410 in ≤ 8-row batches (rights/connector
  block, K13 platform rows, component kits/lints/figures/identifiers,
  search + basemap + dossier index + maps, search serving + entity
  pages + share-list claims + status lane, cadence/publish
  matrix/backfill/source surfaces, dossier sources/downloads/template/
  scoped search/tasks/watch, evidence hub/queue/drafts/home/snapshots).
- **C10** — contracts 411–418: the changes API, per-source extracts
  (OM-20 mirror writes), source page B, search acceptance (the only
  context allowed to read the sealed held-out set), the core-surfaces
  acceptance pair (P36.72b carries the HG-11 Class S readout — never
  pre-authorised), second-release acceptance (Class R conditional),
  and the nested **PLAN-11D** plan-kind contract (rows 421–510, ~12
  contexts + a fresh Phase-4 review, written before GATE-G6).
- **C11** — contracts 419–420: the 11C capstone (read-only live sweep
  after P36.72b's promote + the agent-drafted GATE-G6 packet) and the
  GATE-G6 gate marker (guard sentence; collects ING-GO-D, the Wave-D
  flip list, the 11D OM-20 list, the standing-go renewal;
  title/note drift `ING-GO-C/D` recorded verbatim) — plus the
  regenerated `REQUIREMENT_INDEX_R11.md` (`req_index.py check` green).
- **C12** — the fresh-context Phase-4 review of all 77 contracts: Load
  lists re-measured (two stale headers corrected — 352, 353), no
  forward `Depends on:` edges (one prose token repaired on 418),
  owner bullets completed for 13 contracts (the §56.10 SIG-TRANSP
  family + SIG-REL-008/015, SIG-OPS-008, SIG-REL-011 — index now lists
  zero 11C-owned ids unlisted), K13 routing verified (174 ids, each to
  exactly one row, all MISSING), the re-split rule evaluated with
  counts (76 engineering rows / 66.5 runs at S6c — under both
  thresholds, not fired), the watch/flag set recorded (P36.64, P36.2 —
  both fit), the **draft 11C OM-20 list for GATE-G5** (13 rows with
  written `Production mutations` headers; §8.1's count of 10 vs 13
  recorded as drift, not resolved), and the **11C outreach-owed list**
  (ADR-171 — P37.1, P37.2, P36.75, P36.76, P36.77, P36.78; the Stage-0
  set stays owed-unmet; nobody was contacted).

## Local verification

- `docs/research/_meta/spec_src/BUILD.sh` — reproduction byte-identical
  (935,118 bytes); `check_spec_src.py` — 994 ids (668 + 326
  fold-backs), no duplicate/malformed/reserved ids.
- `check_coverage_matrix.py` — 994/994 rows OK.
- `obligation_events.py check` — green (3 pre-existing stale-ref
  warnings on superseded rows).
- `memory_guard.py all --staged` — clean before every commit;
  `check-history.sh --range da2cea19..HEAD` — clean (22,331 items)
  after three declared `seed-commit` exemptions in `history.policy`
  (cf587926, c1c08a94, ff03e193 — commit subjects naming later-row ids
  `PLAN-11D`/`GATE-G6` set the executed flag mid-range and the
  sanctioned skeleton→contract rewrites read as frozen edits; the
  same class as PLAN-11B's f9c407c8 exemption; the declared-consequence
  note is in the policy file).
- `check_trailers.py --range` — every commit trailered (OM-01).
- `check_live_claims.py range` — 0 violations (ledger prose carries
  inline negations; contract live legs are gate-pending or
  conditional).
- `current_projection.py generate` + `verify` — fresh, 1106/1106
  digests.
- `make docs-check` — green (pre-existing warnings only: deferral
  owner/trigger cells, manifest banner rows, one ADR index owner cell).
- `req_index.py write` + `check` — regenerated, current.
- `make check` — 9,851 passed · 629 skipped · **3 failed** (all
  pre-existing/environmental, recorded verbatim in the run ledger):
  `SIG_GCP_PROJECT` unset (fail-closed by design, OP-07); the two
  `test_p34_18_aliases` failures on handle entries that predate the
  dispatch boundary `da2cea19`. Docker-gated `tests/db`/`tests/e2e`
  skipped — no daemon; they run in CI's `python`/`composed` jobs.

## Deviations

- The plan-internal run-count drift (`est_runs=7.0` vs §8.1's 6.0) is
  recorded verbatim, not resolved; actual dispatch was twelve ≤1-run
  contexts.
- The §8.1 OM-20 count (10) vs the thirteen written `Production
  mutations` headers is recorded as drift; the GATE-G5 packet's own
  wording ("any further row a written header names") covers it.
- `history.policy` gained three declared seed-commit exemptions
  (above) rather than rewriting subjects — the branch rule forbids
  force-push.

## Non-goals

No 11C row is executed; no production action is taken; no gate is
ticked; no `ingestion_permitted` flips; PLAN-11D's own contexts are
not dispatched (row 418's contract describes them — written before
GATE-G6); `docs/2_canonical_design_spec.md` is rebuilt, never edited;
ADR bodies and landed records are untouched (append-only).
