# Build memory (`docs/build/`)

Durable, committed record of how this repository was planned and built — the "memory" every
post-build ticket (P19.2+) cites by path. Established by **P19.1** (ADR-058, ledger §4.7). The
live `orchestrate-build` machine ledger is the single exception: it stays gitignored under
`.agents/scratch/` as the sole `planning/sig-postbuild-build-ledger.md` (never committed).

## Files committed here now (P19.1)

- **`PLANNING_LEDGER.md`** — the post-build "plan for the plan": the operator prompt → TODO ledger
  (T1–T16), ground truth, decisions (§4.1 scratch, §4.2 tickets-in-git, §4.7 this home), planning
  phases, and the findings log. Committed copy of `.agents/scratch/NEXT-PHASE_planning-ledger_20260908.md`.
- **`BUILD_INDEX.md`** — the 46-ticket index: ticket → branch/commits → PR#/state/base → ledger →
  ADRs → traceability → risk § → per-ticket implement-spec 5.3 live-verification status.
- **`LEDGER_DEFERRALS.md`** — every non-met gap / deviation / deferral / "not run" extracted from the
  44 run ledgers, each with its source and its owning post-build ticket (the `LD-*` rows).
- **`SCOPING_NUMBERS.md`** / **`SCOPING_ID_LISTS.md`** — the scoping facts (requirement-id coverage
  counts, connector `ingestion_permitted` counts, merge-conflict dry-run, CI facts, human-gate
  inventory) and the id lists behind them, that made the ticket ACs precise.
- **`DECISION_MEMO.md`** — the synthesis: the 17-ticket post-build chain (rows 47–63), sequence and
  rationale, gate register (HG-01..14), LD/RISK/ADR → ticket mapping, and the critical path.

## Files later tickets append here

`COVERAGE_MATRIX.csv` + `CAPSTONE_GAP_ANALYSIS.md` (P19.2); `COMPOSED_E2E_REPORT.md` (P19.3);
`CAPSTONE_CLOSURE.md` (P19.5); `BACKLOG.*` + `OPERATIONAL_READINESS.md` (P20.1); `TICKET_VS_SPEC.md`
+ `SPEC_RECONCILIATION_PLAN.md` (P20.2); `INTEGRATION_PLAN.md` + `CI_STATUS.md` (P20.3); and the
P21 reports (`LIVE_WIRING_REPORT.md`, `FIRST_JURISDICTION_REPORT.md`, `PUBLICATION_CHECKLIST.md`, …).
