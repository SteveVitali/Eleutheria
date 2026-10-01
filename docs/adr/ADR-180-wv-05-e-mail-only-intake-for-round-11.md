# ADR-180: WV-05 — e-mail-only intake for Round 11 (SIG-GOV-001's one-click clause and SIG-GOV-002 waived)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-GOV-001 (one-click clause WAIVED for Round 11), SIG-GOV-002 (WAIVED for Round 11); related SIG-GOV-003 (ADR-186), SIG-UI-033
- **Spec:** docs/2_canonical_design_spec.md §45.1 — SIG-GOV-001 at lines 6462–6464, SIG-GOV-002 at lines 6466–6467 (as built at `71e8bc83`; source `docs/research/_meta/spec_src/91_partVIII_s44to46_sec_gov.md`)
- **Decision:** the operator's answers to A-23 part 2 (waiver candidate WV-05), 2026-10-01T04:28:49Z, and to B-8, 2026-10-01T04:35:53Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, rounds 9 and 12
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.4 (B-8), §5.1 (R1.2), §6.3 (SIG-GOV-001/002 row), §6.5 (WV-05 row), §7 row 180, §13.5
- **Related:** ADR-186 (WV-08: GOV-003's SLA-time clause waived; handling priority published), ADR-135 (the isolated intake receiver, non-operational), ADR-161 (release model v2: 15-minute withdrawal); plan §14 R-22
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

SIG-GOV-001 requires a public intake channel reachable in one click from any claim; SIG-GOV-002 forbids requiring the
submitter to identify themselves. In Round 11 nothing can operate an anonymous, one-click receiver: the receiver built
in Round 10 (ADR-135) answers `503 receiver_not_operating`, its operation needs a named moderation owner and staffed
review (D-P32.16-1), and the operator is the only human (Q-8). The live site nevertheless promised "one-click dispute"
on every page (F-03, S0). At B-8 the operator chose e-mail-only intake with no published response times, which means
a sender discloses an e-mail address — the conflict with SIG-GOV-002 that WV-05 put to the operator (S4 TS-05;
`data/decision_catalog.csv` row WV-05).

## Decision

### The operator's words

- **Answer to A-23 part 2 (multi-select; a tick waives), verbatim:** "WV-04 hostile-reader block (Recommended), WV-05
  anonymous intake (Recommended), WV-06 two-person deletion" — round 9, 2026-10-01T04:28:49Z.
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z:**

  > I waive one-click, unidentified intake (SIG-GOV-001/002) for Round 11: corrections come by e-mail, and the site says plainly that senders disclose their address.

  sha256 `bf1f65d5aaa1103dfdaedd98d1e793190ac5d3b688a42ffa10032bec1ffe6142` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals S6's value, `design/S6-ratification-applied.md` §5).
- **B-8, verbatim:** "Email, no time promises" — round 12, 2026-10-01T04:35:53Z (the operator chose it over the
  recommendation to publish response times).
- **C-12 (the withdraw-instead-of-fix list, which includes one-click dispute and `/intake/`), adopted sentence —
  agent-drafted, adopted by the operator at 2026-10-01T05:03:05Z:** *"I accept that these features are withdrawn or
  labelled this round rather than made to work."* sha256
  `da7889afdff5cab3aba0b6e348341dc4f4b94fbc477f09517733ffb0e95d2a16`.

### The requirements and the clauses waived

> **SIG-GOV-001 (MUST).** A public intake channel MUST exist, reachable **in one click from any
> claim** (SIG-UI-033), accepting: factual error; privacy harm; legal demand; security concern;
> copyright claim.
>
> **SIG-GOV-002 (MUST).** Intake MUST NOT require identifying the submitter, except where a legal
> demand requires standing.

— `docs/2_canonical_design_spec.md:6462-6467`

- **Waived for Round 11:** SIG-GOV-001's "reachable **in one click from any claim**" clause, and SIG-GOV-002 in full —
  an e-mail necessarily discloses the sender's address.
- **Not waived (agent reading, labelled):** SIG-GOV-001's first and last clauses — a public intake channel exists (the
  e-mail address the dispute page names) and it accepts all five categories (factual error, privacy harm, legal
  demand, security concern, copyright claim).

### Scope

Round 11 only, as the sentence says. The coverage verdicts are `WAIVED(ADR-180)` for SIG-GOV-002 and for SIG-GOV-001's
one-click clause, recorded by T4 (SEED-14) with the scope in `accepted_scope`.

### Compensating controls

1. **The notice.** The dispute / corrections page and the task pages name the intake address, say plainly that senders
   disclose their address, promise no response time (B-8), and publish the handling priority — privacy-harm and
   safety reports first, then factual corrections, then everything else (WV-08, ADR-186). The text is confirmed verbatim
   in copy batch #1 (B-2) and ships in republish #1 — row **P34.17** (plan §5.1 R1.2).
2. **Every false promise removed.** Every "one-click dispute" and "anonymous" promise is removed from the site (R1.2,
   F-03); `/intake/` is labelled "not operating" (B-8; C-12).
3. **Takedowns still work.** Part VIII and safety takedowns are honoured by the operator through the withdrawal barrier
   (P34.41; the 15-minute technical withdrawal of the release model, D-G3-9, ADR-161).
4. **The receiver stays dark.** P37.59 lands its engineering dark and does not run its live leg (B-8); the intake
   receiver keeps answering `503 receiver_not_operating` (ADR-135).
5. **Which address.** The dispute notice names the operator's address until the `contact@` alias exists (B-8
   interpretation; OP-10; C-8 "alias first"); GATE-ANNOUNCE asks whether to keep that address or require the alias
   before announcing (Q-29 revisited, plan §13.5).

## Consequences

- A person who fears identification has no anonymous way to report an error or a privacy harm this round. That is the
  exposure the operator accepted; it is listed in plan §14 R-22.
- The intake address is public. The safety of that choice is revisited at GATE-ANNOUNCE (Q-29).
- T4 records the verdicts and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **Keep SIG-GOV-001/002 owed (option b).** They would be listed unmet at GATE-ANNOUNCE. Not chosen.
- **Open the one-click receiver (E2 A-1 option b/c).** Needs a moderation owner and staffed review (D-P32.16-1) that a
  single maintainer cannot provide; withdrawn by C-12.

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- the announcement: GATE-ANNOUNCE records a keep/lift answer for WV-05 in the operator's words (plan §13.5, S6R-18);
- a privacy-harm report arrives, or a sender is harmed by having had to disclose an address;
- a public intake form opens (P37.59's live leg or any successor) — the same event re-opens WV-08 (ADR-186);
- Round 11 ends (the waiver's own scope), or a second maintainer joins.
