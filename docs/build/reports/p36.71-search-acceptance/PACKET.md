<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P36.71 — search acceptance: the verify-leg packet (`prepared_not_executed`)

`sig.search-acceptance-packet/1` — see `packet.json` for the machine row.

## What landed (this run, `live_verification=false`)

- `exports/search_acceptance.py` + `sig-exports search-acceptance` — the
  `sig.search-acceptance/1` battery: dev + held-out benchmarks through the
  verified `open_release` path (SIG-SRCH-011), seal digest check, thresholds
  (dev ≥ 0.90, held-out ≥ 0.80, 0 misleading, index bytes ≤ 150 MiB),
  A1/J2 journey legs, the SIG-UI-081 cost block, `--enforce` gating.
- **D-P36.56-1 closed** — the engine's `jurisdiction=` filter is now
  chain-aware (catalog place `meta.parent` subtree); `within=`/`location=`
  refuse a typed 422, never silently unscoped. Tests in
  `tests/exports/test_search_query_v2.py` + `tests/api/test_release_search_v2.py`.
- **The sealed set was read once, here** — `sig-ops held-out emit`
  re-derived the canonical bytes deterministically (the restricted-bucket
  write `D-P36.79-1` is still OPEN — no object exists to fetch);
  `sig-ops held-out verify` confirmed sha256
  `44c746836f709e9dde74e2a4834a1c8d0a3b447c7beb9cc43ffbdf91a7a8a1b0`
  equals the committed `sig.held-out-relevance-descriptor/1` — **seal
  intact**, the bytes never landed in the tree (B-28 = b).
- `acceptance-fixture.json` — the battery measured over a synthetic
  fixture release (`posture: fixture release`). The synthetic corpus
  honestly cannot answer registry-derived held-out subjects; the numbers
  are recorded as measured, never smoothed — the binding run is the
  verify leg's real-release run.

## Queued legs — run after P36.72b's promote (the OM-19 re-run)

1. **Real-release acceptance** — fetch/build the promoted release,
   `sig-exports search-acceptance --release <dir> --held-out <blob>
   --enforce` → dev ≥ 0.90, held-out ≥ 0.80, 0 misleading, bytes ≤ 150 MiB.
2. **Staging p95 ≤ 300 ms at 1 vCPU** — gcsfuse vs local copy measured on
   the staged service (needs the P36.38 roll `D-P36.38-1` applied +
   ADC/`SIG_GCP_PROJECT`).
3. **Budgets + Lighthouse on the real release** (`check:perf` path),
   **axe in both JS states** (e2e on the promoted build).
4. **Cost readout** (SIG-UI-081) — the billing export vs the $300/month
   ceiling, recorded via `--billing`.
5. **Journey walkthroughs** — A1 + J2 cold-walked on the promoted release,
   recorded `agent-verified` (P4), at 390 px and 1440 px.

## Re-run prompt (exact)

```
implement-spec spec=docs/tickets/414_P36.71__search-acceptance-and-activation.md live_verification=true
```

Obligation: `D-P36.71-1` (OPEN) — closed by the promoted-release verify
whose `sig.search-acceptance/1` report lands `verdict: pass`.
