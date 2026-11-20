# ADR-253 — Round-11 spec reconciliation to the landed design (proposals-only)

- Date: 2026-11-19
- Status: accepted (records-only — changes no behaviour and no normative spec
  text; the amendment set it names stays unticked until the operator ticks it)
- Ticket: P38.3b (Round 11 / P38, sub-round 11D-tail, manifest row 506 — on
  `r11/P38.3b-round11-spec-reconciliation`)
- Base: `r11/P38.3a-round11-backlog-and-operational-readiness` (`df02787e`)
- Authority: the P20.2/ADR-062 and P33.5/ADR-145 reconciliation pattern applied
  to the landed Round-11 state; GATE-ACCEPT-R11 **SIGNED** 2026-11-19
  (`ede12a67`) is the authoritative accepted-deviations list — re-read, never
  re-decided; reconcile-build `mode=spec` with `apply_amendments=false` (the
  skill default; the row 506 contract's "spec-source amendment proposal")
- Relates: ADR-145 (the Round-10 landed-design reconciliation), ADR-146/147/150
  (the memory-truth set), ADR-152…190 (the Round-11 waivers and amendments of
  Appendix G.7), SIG-ENG-039/041, SIG-MEM-005/011

## Context

Round 11 closed at GATE-ACCEPT-R11: the operator signed the accepted-deviations
list verbatim — 13 waivers (R11-W1…W13, covering 16 requirement ids), the §4.6
descopes and withdrawals (including the six C-12 withdrawals), the accepted
risks, the re-homed/split/dropped row set, and the GAP-RP-1 anomaly carried for
disposition. The tail's `reconcile-build` row (P38.3, split a/b/c for context
ceiling) reconciles records against what the round landed; **b** is the spec
reconciliation: `docs/2_canonical_design_spec.md`'s 994 requirement ids re-read
against the committed build state.

Unlike Round 10's reconciliation, most of Round 11's spec↔build drift was
already recorded at planning time: Appendix G.7 carries the adopted waivers
with the operator's verbatim sentences and sha256 prefixes, the non-weakening
amendments (R11-A1…A17), and the G.7.5 "checked and deliberately not amended"
register. What remains at the tail is the *classification* — which ids are
satisfied, engineered-only, carried to deferrals, waived, or N/A — plus the
narrow residual where the spec's own dated-record anchors have not yet been
extended.

## Decision

1. **The reconciliation is recorded, not applied.** Every requirement id is
   classified by its committed coverage verdict — 650 satisfied (646 `MET` +
   4 `MET-DIFFERENTLY`), 246 `MET-ENGINEERED(D-…)` (each owed remainder a real
   OPEN DEFERRALS row), 16 `WAIVED(ADR-…)` (mapping one-to-one onto the 13
   signed waivers), 73 open (60 `PARTIAL` + 12 `MISSING` + 1
   `AT-RISK-INTEGRATION`, each routed to a live home), 9 `N/A-RATIONALE` —
   `coverage two-sum: engineering closed = 896 · requirement satisfied = 650`.
   The full classification, the deviation-coverage check and the
   checked-consistent register live in
   `docs/build/reports/p38.3b-round11-spec-reconciliation.md`.
2. **Every signed deviation maps to a recorded state.** The waivers sit in
   G.7.2 + the owning sections' dated notes + `WAIVED` verdicts; the
   descopes/withdrawals ride their requirement notes (SIG-CONF-010's recorded
   "no maintainer check", the §45.1 intake label, R11-A15's outreach-owed
   note) or operational records where no spec text exists; the accepted risks
   ride ADR-167…185's recorded postures; the superseded/dropped/inserted rows
   ride the manifest and §55.4's Round-11 disposition. No signed line is
   unrecorded; no spec amendment is owed for them.
3. **Three `spec_src` amendment proposals are registered, unticked.** In
   `docs/build/SPEC_RECONCILIATION_PLAN.md` § Round 11 (P38.3b): **R11-REC-1** —
   the dated Round-11 landed-status record appended to §56.9 (the Part-XII
   mirror of §55.9's R10-A6); **R11-REC-2** — `## G.8 Round-11 landed-design
   reconciliation` appended to Appendix G with the disposition tables; and
   **R11-REC-3** — the Part-0 spec-date line gaining
   "Round-11 landed-design reconciliation 2026-11-19 (P38.3b, ADR-253)". All
   add dated record and remove no obligation — none weakens a MUST, so none is
   a waiver — but like every amendment they wait for the operator's tick; the
   apply is owed as `D-P38.3b-1` and runs
   `reconcile-build mode=spec apply_amendments=true` through `spec_src` +
   `BUILD.sh`, never a direct spec edit.
4. **Nothing else moves.** `TICKET_VS_SPEC.md` stays the declared frozen
   Phase-0…P18 view; `COVERAGE_MATRIX.csv` stays the live traceability
   authority with no verdict re-judged or re-routed (the five rows P38.3a
   re-pointed to P38.5 stand); no requirement id is minted — the count stays
   **994**; no ADR body, DEFERRALS lead token, gate record or `sqitch.plan`
   line is edited.

## Consequences

- The spec's normative text remains exactly as G.7 left it until the operator
  ticks the proposals — honest, since the spec's own convention is that
  landed-status text is *appended*, and an appended record is still owed.
- `D-P38.3b-1` carries the apply explicitly; a later reconcile run applies the
  ticked set under this ADR, and the Appendix G.8 record then cites the
  applying commit.
- This ADR's own Appendix F row lands now (SIG-ENG-039: file-set == index-set);
  the normative-text proposals do not.

## Revisit trigger

- **The operator ticks the proposals:** apply them through `spec_src` +
  `BUILD.sh` per `D-P38.3b-1`; this ADR is not edited — G.8 records the apply.
- **A signed deviation is found unmapped:** any GATE-ACCEPT-R11 §1a–1e line
  discovered without a recorded spec or operational state is drift — it
  becomes a `D-…` row or a further proposal, never a silent fix.
- **A verdict disputes the classification:** verdict changes follow
  SIG-ENG-041's `coverage-assessment/1` event path on their own rows' landings;
  the classification here is a dated read of `df02787e`, not a verdict.
