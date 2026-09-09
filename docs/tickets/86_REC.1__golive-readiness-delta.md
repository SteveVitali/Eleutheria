<!--
  Tail (minimal) — go-live round closeout. Filled by decompose-spec mode=extend over
  ~/MetaHarness/sig-golive-spec.md (2026-09-09). tail=minimal per spec D6 + Appendix B item 7:
  a REC-style readiness delta, NOT a full CAP.1–CAP.3 (PR #68 already capstoned the composed
  build; DOC.1/DOC.2 omitted because P22.1/P22.2 already ran). An ordinary implement-spec
  contract whose body invokes reconcile-build.
-->
# REC.1 — Go-live readiness delta (reconcile)

- **Sequence:** 86 of 87 · **Phase:** reconcile · **Kind:** reconcile
- **Tag:** golive-tail
- **base_branch:** current checkout
- **Depends on:** CCOPS.1 (row 85) — the last Round-4 unit
- **Run:** `implement-spec spec=docs/tickets/86_REC.1__golive-readiness-delta.md live_verification=false`
- **Gate status:** none
- **Live stage:** none

## Goal
Fold everything the go-live + productionize rounds left owed into an updated readiness picture —
a delta over the PR #68 capstone, not a re-verification — so the accepted-deviations list is
current before the operator signs it at GATE-ACCEPT.

## Load (read these — do not re-read others)
- **Invoke `reconcile-build mode=backlog`** and follow it completely (delta scope only).
- `~/MetaHarness/sig-golive-spec.md` Part I §3 (D6); `docs/build/OPERATIONAL_READINESS.md`,
  `docs/build/BACKLOG.csv`, `docs/tickets/DEFERRALS.md` (OPEN/PARTIAL rows, incl. the go-live
  `D-*` rows), `docs/build/LEDGER.md § OPEN FINDINGS`, `docs/build/CAPSTONE_CLOSURE.md`
  (the frozen Round-1 ACCEPTED list — the baseline).

## In scope — deliverables
1. A **readiness delta**: refresh `docs/build/OPERATIONAL_READINESS.md` and `docs/build/BACKLOG.csv`
   against the current DEFERRALS + open findings introduced/closed by Rounds 3–4 — no re-run of the
   full COVERAGE_MATRIX.
2. Append any **new** accepted deviation from Rounds 3–4 to `docs/build/CAPSTONE_CLOSURE.md`
   (append-only) for the operator to sign at GATE-ACCEPT; if none changed, state so explicitly.
3. The backlog check script `reconcile-build` provides runs green.

## Out of scope
- A full CAP.1–CAP.3 capstone (PR #68 already capstoned; spec D6). DOC.1/DOC.2 (P22.1/P22.2 ran).
- Spec reconciliation / integration plan beyond the delta (no REC.2/REC.3 in this minimal tail).
- Implementing backlog items.

## Acceptance criteria
- [ ] every OPEN/PARTIAL go-live deferral, OPEN FINDING and new ADR revisit trigger appears in exactly one BACKLOG source cell *(deterministic)*
- [ ] `OPERATIONAL_READINESS.md` reflects the Round 3–4 delta with `ticket:` + `proof:` on every new step and no TBD *(deterministic)*
- [ ] the CAPSTONE_CLOSURE ACCEPTED list is current (new deviations appended, or "no change" stated) *(deterministic)*
- [ ] verification green; every new behaviour has a test that fails if it is removed; requirement ids stamped in the PR; anything not automatically verifiable is a `DEFERRALS.md` row with its compensating control; ADRs written for every deviation and owned decision; `BUILD_INDEX.md` row and `LEDGER.md` advanced. *(agentic — the universal phase-gate AC)*

## Requirement IDs to satisfy and stamp in the PR
The go-live readiness ids of `~/MetaHarness/sig-golive-spec.md` (GL-* areas), delta scope.

## Cross-cutting invariants
- Cited from `docs/tickets/00_MANIFEST.md § Cross-cutting invariants`.

## Notes
- This ticket owns the readiness delta; GATE-ACCEPT (row 87) consumes its updated ACCEPTED list.
