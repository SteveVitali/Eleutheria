# ADR-239 — The §22.7 Data Library roster artifact and the recurring discovery sweep (P37.13)

- Date: 2026-11-07
- Status: accepted
- Ticket: P37.13 (Round 11 / P37, row 435 — F2a group 12; SIG-INGEST-041 + SIG-INGEST-048)
- Base: `r11/P37.70-keyed-au-traffic-camera-apis`
- Related: SIG-INGEST-041 (the roster is the Phase 17 backlog), SIG-INGEST-048
  (membership turns over — a recurring sweep, never a one-time census),
  NEW-8/F2a (11 of 16 rows unregistered at the verdict), P35.6/ACQ-01 (which
  pre-covered three entries), P26.2 (the earlier registry-widening sweep),
  HG-03 (flips stay the operator's line), `connectors/data_library_roster.py`,
  `data/data_library_roster.toml`, `docs/build/reports/discovery-sweep/`.

## Context

SIG-INGEST-041 makes the EFF Data Library index the Phase 17 ingestion backlog:
its entries must be registered, `LINK` posture until rights are reviewed. F2a
measured 11 of the 16 roster rows unregistered. Between the verdict and this
ticket the ACQ-01 generation (P35.6) registered three of them under
`statrep_*`/`camreg_*` ids — a registry write per entry would have duplicated
an already-registered upstream (NEW-1 dedupe forbids it), so the roster needs
a **mapping**, not just more rows. SIG-INGEST-048 separately requires the
discovery pass to recur: the ecosystem's membership turns over, so a one-time
census rots.

## Decision

1. **The roster is a committed artifact, not a count.** `data_library_roster.toml`
   (`sig.data-library-roster/1`) carries one `[[entry]]` per spec-roster row —
   `spec_dataset` verbatim, `covers` naming the registry id(s) carrying it,
   `registered_by`, and a `mapping` verdict: `exact` (the same upstream
   artifact) or `equivalent` (the same dataset from the authoritative upstream
   where the index links a mirror — Collier's cell-site aggregation vs the
   ACLU set; the State Auditor's own publication vs EFF's CPRA mirror). An
   `equivalent` is a recorded claim, never a silent conflation.
2. **Register only the genuinely uncovered entries — eight LINK rows.** The
   three ACQ-01-covered entries map to their generated ids; the eight
   remainder enter as `datalib_*` rows, `custody_posture = "LINK"`,
   `ingestion_permitted = false`, rights UNDETERMINED — the operator's HG-03
   line flips them, never this registration (the "11 missing" of the F2a
   verdict resolves as 8 new + 3 pre-covered, recorded in the sweep report).
3. **The audit is executable.** `connectors/data_library_roster.py` re-derives
   the roster from the spec source table (never a hand-copied count), joins
   each entry to `registry()` fail-closed, and `sig-connectors roster` prints
   the coverage; the roster test (`tests/connectors/test_data_library_roster.py`)
   fails on an uncovered entry, a dangling cover, spec-table drift or a
   `datalib_*` row that is not LINK + gated.
4. **The sweep recurs under `sig.discovery-sweep/1`** — Stream I's method
   (query log + per-candidate dispositions + honest negatives) on a per-round
   cadence: enumerate the documented surfaces (index fetch, byte-recorded;
   the §22.7 table parsed from spec source; the §22.6 H2 list), map every
   entry (`registered:` / `new-linked:` / `related:` /
   `candidate-unregistered`), commit `SWEEP.md` + `query_log.csv` +
   `candidates.csv` in a dated directory. Non-roster discoveries are
   candidates for a future registration decision — the 2026-11-07 sweep's 23
   ride `D-P37.13-1` — never scope creep inside the sweep itself; a sweep
   never flips a source and never contacts anyone (U-011).

## Consequences

- The roster is enforced, not narrated: a dropped cover or a spec-roster
  change fails `make check` loud.
- Coverage is honest about artifact identity: `equivalent` mappings are
  inspectable claims a reviewer can dispute, not silently counted covers.
- The next sweep diffs `candidates.csv` — moved dispositions are coverage
  gain; new index sections are the discovery yield the cadence exists for.
- All eight new rows stay gated at the loader (`assert_loadable` refuses) —
  registration changes the map, never the gate.

## Revisit trigger

- The Data Library index drops, splits or relocates its dataset sections
  (re-enumerate + re-map at the next sweep).
- A rights review (HG-03) resolves any `datalib_*` row — the flip is a new
  record on that row, not an edit of this ADR.
- A new roster-bearing artifact appears (a spec-roster change or a second
  index of the same class) — extend the roster file + the sweep's documented
  surfaces in a new ticket.
- `D-P37.13-1` closes (the non-roster candidates dispositioned) — a later
  sweep may fold them into the registry.
