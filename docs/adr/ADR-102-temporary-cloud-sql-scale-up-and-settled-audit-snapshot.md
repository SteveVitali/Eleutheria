# ADR-102 — Temporary Cloud SQL scale-up for the OSM land, and a settled audit snapshot status

- **Status:** Accepted
- **Phase / ticket:** Phase 30 / P30.1 (`docs/tickets/P30.1__osm-land-and-settled-reaudit.md`) — Round 8 `GO-LIVE.1`; the ticket this ADR is owned by and lands with.
- **Date:** 2026-09-24
- **Related:** **D-SOURCES.17-1** (the hosted OSM land, closed by P30.1), **D-P27.1-1** (the settled re-audit, closed by P30.1), **D-P30.1-1 / D-P30.1-2** (the write-path throughput follow-ups this ADR's context motivates), P26.18 (the chunked-commit `PgClaimSink` path), P27.1 (the `sig-exports audit` verb), `docs/build/reports/LAUNCH_BASELINE_2026-09-24.md`, backlog homes **BL-055** / **BL-057**.

## Context

The P26.18 / D-SOURCES.17-1 procedure and the P30 tickets default to **no Cloud SQL scaling**: the
chunked-commit write path makes a ~1.37M-record land *durable and resumable* on `db-f1-micro`, and the
fix for throughput is the write path, not the hardware. In practice the first land execution
(`sig-ingest-camreg-batch-05-p964s`, started 2026-09-22T16:49Z) was I/O-bound at ~400–470 claims/min
on `db-f1-micro` and was projected to hit the Cloud Run task deadline at ~89% done — which would have
forced a *second* full replay (a restart is an idempotent full re-fetch + re-walk, not a checkpoint).

Separately, the P27.1 audit verb hard-coded a "PROVISIONAL pre/mid-OSM snapshot" banner. The settled
re-audit (D-P27.1-1) needs to state that it was taken after the land completed without dropping the
as-of + named-denominator discipline (§32 / SIG-METRIC-008).

## Decision

1. **Operator-approved temporary scale-up (a recorded deviation from the tickets' default).** The
   operator patched `sig-pg` **`db-f1-micro` → `db-custom-2-8192`** at ~22:25Z 2026-09-23, cancelled
   `…-p964s` (930,000 claims already committed in 93 chunks), and re-executed the OSM-only ingest as
   `…-tjqdq`, which completed successfully at 2026-09-24T03:35:13Z. The instance is **kept** at
   `db-custom-2-8192` through the P30.2 materialization and **scaled back at P30.4**. No agent ticket
   changes the tier; P30.1 only records it.
2. **The audit verb gains an opt-in `settled` snapshot status** (`sig-exports audit --settled`;
   `build_spine_audit(..., settled=True)` / `run_audit(..., settled=True)`; JSON `snapshot_status`,
   schema `p30.1/1.0.0`). It is additive and defaults to `provisional`, so every existing caller and
   the P27.1 behaviour are unchanged. `--settled` replaces only the in-flight caveat with a settled
   banner that still says the numbers are as-of, named-denominator counts, never a population total;
   the query set, the read-only session, and every number are identical either way (test-pinned).
   Asserting `--settled` is an operator/ticket judgement made only after the awaited land is verified.

## Consequences

- The OSM land finished within one execution instead of timing out and replaying again; the launch
  baseline could be frozen on 2026-09-24.
- Hosting cost is temporarily higher until P30.4 scales `sig-pg` back down; the P30.4 contract owns that.
- The throughput root cause is unchanged — the sink is still row-at-a-time and restarts still fully
  replay. Those are recorded as D-P30.1-1 / D-P30.1-2 (BL-057) rather than masked by the hardware.
- The audit's markdown and JSON now self-describe their snapshot status, so a downstream reader (P30.2
  / P30.3) can tell a settled baseline from a mid-land snapshot without reading the note text.

## Alternatives considered

- **Stay on `db-f1-micro` and let p964s run out.** Rejected by the operator: projected to time out at
  ~89%, costing a further full replay (~12h+) before any launch number could be frozen.
- **Implement batched writes / incremental restarts first.** Correct long-term fix, but a write-path
  change inside a verification ticket, re-opening the P26.18 proofs mid-launch; deferred as
  D-P30.1-1 / D-P30.1-2.
- **Signal "settled" only through `--note` free text.** Rejected: the hard-coded PROVISIONAL banner
  would still claim the land was in flight, contradicting the note; a typed status is machine-readable.

## Revisit trigger

Revisit when P30.4 scales `sig-pg` back down (confirm the tier is restored and record the date), or
when D-P30.1-1 / D-P30.1-2 land (a future large land should then need no scale-up), or if any future
audit is labelled `--settled` while a land it depends on is still running.
