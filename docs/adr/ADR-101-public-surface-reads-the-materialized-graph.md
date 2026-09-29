# ADR-101 — The public surface reads the materialized graph (reconciling ADR-092)

- **Status:** Accepted
- **Phase / ticket:** Phase 28 / P28.5 (`docs/tickets/P28.5__refresh-surface-materialized-graph.md`) — Round 6 (Depth & Resolution) `DEPTH.5`; the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-23
- **Related:** **ADR-092** (the P27 launch posture this reconciles — export built from the spine, launch resolution left **compute-on-read + honest observation-level framing**), **ADR-066** (spine-built export, generalised by ADR-090/092), **ADR-090** (national public surface from a spine-built export), **ADR-099** (materialized resolution at scale — the rows this surface now reads), **ADR-005** (resolution is a stored decision), **ADR-037** (compute-on-read Contradiction/Coverage family, materialized by P28.3/P28.4), `exports/src/exports/shaping.py` (P27.3 — the compute-on-read observation-envelope shaper), `exports/src/exports/spine_export.py` (P27.4 — the read-only-snapshot national export producer), **§38 / §42.3** (export + published compartment), **§32 / SIG-METRIC-008** (named denominators, never a total), **§19.4** (coordinate reduction), backlog home **BL-057**.

## Context

P27 shipped the public surface on a deliberately conservative posture (ADR-092): the national export is
built from the live spine, but because the modeling tables were empty at launch audit, the resolved
layer was **computed on read at export-build time and never written back**. Concretely,
`exports/src/exports/shaping.py` (P27.3) computes a per-`(subject, predicate)` **observation envelope**
(`resolved`/`conflicted`/`unreported`) inside a read-only session, framing each site as "N observations
across M sources" (SIG-RECON-058); `exports/src/exports/spine_export.py` (P27.4) reads that shaped
dataset inside a single `REPEATABLE READ READ ONLY` snapshot and emits the ten P27.1 web surfaces + the
per-compartment PMTiles + PROV-O. Nothing is materialized: `run_shaping`/`run_spine_export` never write
`value_geom`, `resolution`, `relationship`, `contradiction`, or `coverage_record`.

Round 6 changes the ground truth. P28.1 (ADR-099) **materializes `resolution` envelopes** into the spine;
P28.2 materializes sharing/access **relationship** edges; P28.3 materializes **contradiction** rows;
P28.4 materializes **`coverage_record`** / §32 metrics. Once those rows exist, the public export should
be **re-derived off the materialized graph** rather than recomputing an observation envelope at export
time — otherwise the surface would keep showing observation-level framing while the spine holds a richer
resolved, related, contradicted, coverage-measured graph.

## Decision

1. **Re-derive the P27.4 export (and the P27.9 islands) from the materialized graph** (P28.5). The
   `spine_export`/`shaping` producers read the now-materialized `resolution` (ADR-099), `relationship`
   (P28.2), `contradiction` (P28.3), and `coverage_record` (P28.4) rows instead of computing the resolved
   layer on read. The read-only snapshot discipline and the fail-closed licence compartmentation
   (`assert_separated`, the exclusions report, per-`(source, rights_id)` slicing) are **unchanged** —
   this ADR changes *what the producer reads*, never that the producer only reads.

2. **Reconcile — and supersede — ADR-092's compute-on-read posture for the resolved layer.** ADR-092's
   launch framing ("N observations across M sources", compute-on-read, materialized resolution deferred
   to a follow-up ADR) is now the *pre-materialization* posture; ADR-099 is that follow-up ADR, and this
   ADR is where the **public surface** migrates onto the materialized rows: "N resolved sites (from M
   observations)" replaces the observation-level framing **only where ADR-099's measured precision floor
   is cleared**. The observation-envelope path in `shaping.py` is retained as the honest fallback for
   predicates ER cannot yet decide and for surfaces without materialized rows — absence stays an honest
   gap, never a fabricated row (§32, never a total).

3. **Provisional-eval disclosure carries through.** Because ADR-099's gold set is provisional
   (`D-R6.1-EVAL`, OPEN), any "resolved sites" the surface now shows carries the provisional-eval
   disclosure until that deferral closes.

4. **Gate.** If re-deriving the surface **materially changes what is published**, it is an HG-11
   (Go-public) decision, per the P27 publication-gate posture.

## Consequences

- The public surface becomes the real depth graph: resolved sites, a real sharing/access network, live
  contradictions (SIG's signature), and honest computed coverage — read from durable spine rows, not
  recomputed each export.
- The compute-on-read shaper (`shaping.py`) is no longer the source of the resolved layer, but stays in
  the codebase as the documented fallback for un-materialized predicates/surfaces; the producer's
  read-only + compartment invariants are untouched.
- Export builds get simpler and more consistent (the resolved layer is a read, not a recompute), at the
  cost of depending on the Round-6 materialization passes having run — staleness is now a function of ER
  cadence, not export cadence (see Revisit trigger).
- The launch claim strengthens from observation-level to resolved-level **only** behind ADR-099's
  measured floor + the `D-R6.1-EVAL` disclosure — no census is claimed the eval does not support.

## Alternatives considered

- **Keep computing the resolved layer on read (ADR-092 unchanged).** Rejected: it wastes the Round-6
  materialization and would show observation-level framing over a spine that already holds the resolved
  graph — an avoidable understatement.
- **Materialize *and* keep computing (dual path as the norm).** Rejected as the default: two sources of
  the resolved layer invites drift; compute-on-read is retained only as the explicit fallback for
  un-materialized predicates/surfaces, not as a parallel canonical path.
- **Publish resolved counts regardless of the eval floor.** Rejected: ADR-099 gates "resolved" on
  measured precision; the surface must not claim resolution the eval does not support, and must disclose
  the provisional basis (`D-R6.1-EVAL`).
- **Move resolution computation into the API/web read path instead of the export.** Rejected: the public
  surface is a static, spine-built export (ADR-066/090); the resolved layer belongs materialized in the
  spine (ADR-005/099) and read by the export producer, not recomputed at request time.

## Revisit trigger

- **Materialization cost or staleness changes the tradeoff** — if re-running the Round-6 materialization
  passes to keep the surface fresh becomes expensive or the export lags the spine unacceptably, reconsider
  the compute-vs-materialize boundary (e.g. incremental materialization, or compute-on-read for the
  fast-moving layer) in a **new ADR** (SIG-ENG-003).
- **Spine growth** past what the materialization passes or the read-only export snapshot can process in a
  reasonable window — reconsider incremental/partitioned materialization.
- **`D-R6.1-EVAL` closes with a different resolved posture** (a re-derived auto-vs-human balance) — re-tune
  what "resolved" the surface shows to match the new floor.
- **A materialized layer must front restricted-compartment bytes** — a hard stop requiring a governance
  decision (Part VIII / §42.3), never a producer-config change.
