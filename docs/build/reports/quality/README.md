# `docs/build/reports/quality/` — the graph-quality suite's committed records

The committed counts summaries of the `sig.quality-*` records. The records
themselves — `sig.quality-report/1`, `sig.probe-run/1`, `sig.quality-baseline/1`
— are the authoritative objects and land under the restricted bucket's
conditioned `ops/probes/` scope (append-only, versioned bucket); what is
committed here is the *counts summary* the contract asks to keep in-tree
(P34.44b deliverable 5), dated with `date -u` (OM-04).

## The record surface (P34.44a → P34.44b; ADR-154/204/205)

| record | writer | where it lands |
|---|---|---|
| `sig.quality-report/1` | `sig-ops quality run|nightly|baseline` | `ops/probes/quality/<yyyy-mm-dd>/<stamp>-quality-report.json` |
| `sig.probe-run/1` | same — the per-run envelope (incl. `suppressed`/`error` runs) | `ops/probes/quality/<yyyy-mm-dd>/<stamp>-probe-run.json` |
| `sig.quality-baseline/1` | `sig-ops quality baseline` (the L2 leg) | `ops/probes/quality-baseline/<yyyy-mm-dd>/<stamp>-baseline.json` |
| `sig.quality-gate/1` | `sig-ops quality gate` (V15 hook; P35.58) | the release gate's record |
| `sig.quality-baseline-apply/1` | `sig-exports quality apply-baselines` | printed on apply — the registry is the artifact |

## Files

- `P34.44b-baseline.md` — the L2 baseline leg's committed summary (queued
  state until `live:P34.43` lands the `sig_audit` login and the window
  opens; the measured counts land here with the leg's `date -u`).
