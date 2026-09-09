<!--
  Lane C (new code) contract — productionize Round 4. Filled by decompose-spec mode=extend over
  ~/MetaHarness/sig-golive-spec.md (2026-09-09). CITES the spec's §§ and GL-* ids.
-->
# OBS.1 — Observability & alerting (GL-OBS-01)

- **Sequence:** 81 of 87 · **Phase:** 22+ (productionize) · **Kind:** ticket
- **Tag:** golive-round4
- **base_branch:** current checkout
- **Depends on:** DEPLOY.1 (a live stack to observe); SCHED.1 (scheduled runs to alert on)
- **Run:** `implement-spec spec=docs/tickets/81_OBS.1__observability-alerting.md live_verification=false`
- **Gate status:** none
- **Live stage:** offline-only

## Goal
Make the live stack observable and self-alerting within the zero-cost posture: metrics/logs,
a wired egress-budget alarm, keepalive verification, uptime + error budgets, bounded log retention.

## Load (read these — do not re-read others)
- `~/MetaHarness/sig-golive-spec.md` Part II § OBS.1 (GL-OBS-01); Part I §3 (D4 zero-cost).
- `docs/2_canonical_design_spec.md` §§ on egress budget / degraded mode / keepalive; `ops/`;
  the egress-budget alarm from `docs/tickets/P21.5__infra-deposit-and-tiles.md` (INFRA.1).

## In scope — deliverables
1. Metrics / logs / alerting for the live stack (GL-OBS-01).
2. Wire the egress-budget alarm (INFRA.1) to a real notifier; keepalive verification (GL-OBS-01).
3. Uptime + error budgets; log retention within the zero-cost posture; a dashboard/readout.

## Out of scope
- The hosting substrate — DEPLOY.1 (row 79). Scheduling itself — SCHED.1 (row 80).
- The egress alarm's *creation* — INFRA.1 (P21.5, row 76); this ticket wires it to a notifier.

## Acceptance criteria
- [ ] an egress-threshold breach fires a recorded alert *(deterministic)*
- [ ] a keepalive failure fires a recorded alert *(deterministic)*
- [ ] a dashboard/readout exists; no secrets appear in logs *(deterministic)*
- [ ] verification green; every new behaviour has a test that fails if it is removed; requirement ids stamped in the PR; anything not automatically verifiable is a `DEFERRALS.md` row with its compensating control; ADRs written for every deviation and owned decision; `BUILD_INDEX.md` row and `LEDGER.md` advanced. *(agentic — the universal phase-gate AC)*

## Requirement IDs to satisfy and stamp in the PR
GL-OBS-01.

## Cross-cutting invariants
- Cited from `docs/tickets/00_MANIFEST.md § Cross-cutting invariants`.

## Notes
- Consumes INFRA.1's egress alarm; do not re-implement it. Re-confirm the notifier seam at build time.
