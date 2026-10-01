# ADR-186: WV-08 — SIG-GOV-003's response-time SLAs waived; the handling priority is published without time commitments

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-GOV-003 (SLA-time clause WAIVED; priority clause MET-DIFFERENTLY)
- **Spec:** docs/2_canonical_design_spec.md §45.2 — SIG-GOV-003 at lines 6471–6472 (as built at `71e8bc83`; source `docs/research/_meta/spec_src/91_partVIII_s44to46_sec_gov.md`)
- **Decision:** the operator's answer to S6-F1 (waiver WV-08), 2026-10-01T06:05:22Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, round 24; with B-8, 2026-10-01T04:35:53Z (round 12)
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.8 (S6-F1), §5.1 (R1.2), §6.3 (SIG-GOV-003 row), §6.5 (WV-08 row), §6.6, §7 row 186, §13.5, §14 R-31 (resolved)
- **Related:** ADR-180 (WV-05: e-mail-only intake), ADR-161 (release model v2: 15-minute withdrawal); `design/S6-ratification-applied.md` §6 flag 1
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

At B-8 the operator chose e-mail-only intake with **no published response times** ("Email, no time promises"). S6
found that this conflicts with SIG-GOV-003, which requires published SLAs by category, and that WV-05 had waived only
SIG-GOV-001/002 (S6 flag 1; plan §14 R-31). The conflict was put to the operator in round 24 with three options:
publish the priority order without times (waiving the SLA clause), keep GOV-003 owed, or publish SLAs after all.

## Decision

### The operator's words

- **Answer to S6-F1, verbatim:** "Priority order, no times (Recommended)" — round 24, 2026-10-01T06:05:22Z.
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T06:05:22Z:**

  > I waive GOV-003's response-time SLAs; SIG publishes its handling priority without time commitments.

  sha256 `806faae385d94eb358900333b197ac6c04726a4cff879c4a9b9fd7a6e6a943fb` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals the value S6b recorded in plan §4.8).
- **B-8, verbatim:** "Email, no time promises" — round 12, 2026-10-01T04:35:53Z.

### The requirement and the clauses

> **SIG-GOV-003 (MUST).** Published SLAs by category, with **privacy-harm and safety claims
> prioritized above all others**, including above factual corrections.

— `docs/2_canonical_design_spec.md:6471-6472`

- **Waived — the SLA-time clause:** "Published SLAs by category" in so far as an SLA is a response-time commitment. No
  response time is published or promised.
- **Met differently — the priority clause:** "privacy-harm and safety claims prioritized above all others, including
  above factual corrections". The corrections / intake page publishes the handling order: **privacy-harm and safety
  reports first, then factual corrections, then everything else**, with no time commitment.

### Scope

Every intake channel while this ADR stands (in Round 11, e-mail only — ADR-180). Coverage: `WAIVED(ADR-186)` for the
SLA-time clause and `MET-DIFFERENTLY(ADR-186)` for the priority clause, both recorded in the row's `accepted_scope`;
if the coverage grammar cannot hold a clause-level split, the row takes the conservative `WAIVED(ADR-186)` and names
the priority clause in `accepted_scope` (S6b note; T4, SEED-14).

### Compensating controls

1. **The published order.** The corrections / intake page states the handling order above and that no response time is
   promised; text confirmed verbatim in copy batch #1 (B-2), shipped by row **P34.17** (plan §5.1 R1.2).
2. **WV-05's notice.** The same page says corrections come by e-mail and that senders disclose their address
   (ADR-180).
3. **Takedowns still fast where it matters.** Part VIII and safety takedowns are honoured by the operator through the
   withdrawal barrier (P34.41) — the release model's 15-minute technical withdrawal (D-G3-9, ADR-161).
4. **Announcement gate.** GOV-003 leaves GATE-ANNOUNCE's "spec MUSTs unmet" list, and GATE-ANNOUNCE requires a
   keep/lift answer for WV-08 in the operator's words (plan §13.5; S6R-18).

## Consequences

- A sender gets no promise of when they will hear back. Privacy-harm and safety reports are still handled first.
- Plan §14 R-31 is resolved by this ADR (kept for history).
- T4 records the verdicts and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **Keep GOV-003 owed (option b).** It would stay on GATE-ANNOUNCE's "unmet" list. Not chosen.
- **Publish SLAs after all (option c).** Would partly reverse B-8. Not chosen.

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- the first public intake form opens (P37.59's live leg or any successor) — the response-time question returns to the
  operator then;
- the announcement: GATE-ANNOUNCE records a keep/lift answer for WV-08 (plan §13.5);
- a second maintainer joins.
