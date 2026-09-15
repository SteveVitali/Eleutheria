# Governance and Code of Conduct

*Adopts docs/2_canonical_design_spec.md §46.2 (SIG-GOV-014…016) and the
continuity/succession and degraded-mode posture of §46.4–§46.5 (SIG-GOV-021…023).*

## Legal home (SIG-GOV-012)

**The legal home of SIG (Surveillance Infrastructure Graph) is Steven Vitali, an
individual maintainer, operating the project in a personal capacity (2026-09-15).**

This resolves the interim "independent open-source project under maintainer
stewardship" posture (GL-GATE-01 / HUMAN-H1) with a real named home for the purpose
of governance, dispute-resolution escalation (above), and the corrections/takedown
contact of record.

*Scope note (honest):* naming an individual as the legal home carries real personal
exposure and is an **interim** designation. It is **not** legal advice, and it does
not settle the legal-defence posture (SIG-GOV-013), which remains a human
prerequisite tracked in the risk register. A more durable home (an entity or a
fiscal-sponsor umbrella) and a counsel opinion (HG-02) are recommended **before real
public exposure** (Go-public / GATE-G2). Until then the project runs at Finish-line A
(deployed, access-restricted), not a public launch.

## Reviewer roles & takedown contact (HG-11, interim — 2026-09-15)

**Interim posture, recorded 2026-09-15.** Pending a second independent reviewer:

- **Maintainer / first reviewer of record:** Steven Vitali (the legal home above).
- **Takedown / corrections contact of record:** Steven Vitali, via the served
  `/corrections` and `/dispute` mechanisms (SIG-PUB-008); this names a live human
  behind the already-built mechanism.
- **Second independent reviewer:** **still owed.** The two-reviewer written-concurrence
  workflow (`ReviewerConcurrence`, SIG-PUB-008) is not satisfied by a single reviewer.

*Scope note (honest):* one reviewer is an **interim** posture; **Go-public
(GATE-G2) remains blocked** until a second independent reviewer + written concurrence
exist (and HG-02 counsel confirms the publication posture). This records who is
accountable now; it does not satisfy HG-11 for public launch.

## Decision-making (SIG-GOV-014)

This governance document defines who decides what:

- **Schema, ruleset, and vocabulary changes** are decided by the **technical
  maintainers**, recorded as ADRs (SIG-ENG-003). A change to the canonical spec
  is an ADR, never an in-place edit of a landed decision.
- **Contested claims** are adjudicated by the **editorial board** (below), not by
  whoever holds commit access.
- **Code of Conduct.** SIG adopts a published Code of Conduct with **enforcement**:
  a named contact path, a defined escalation, and consequences up to removal.
  Contribution is conditional on it.
- **Dispute resolution.** Disputes that are not resolved at the maintainer or
  editorial level escalate to the legal home once established (SIG-GOV-012).

## The editorial board (SIG-GOV-015)

An **editorial board exists, distinct from the technical maintainers.** It owns
the judgments that are editorial rather than technical:

- contested claims;
- **officer-naming decisions** (the five-prong test of §43.4, whose *gate* is
  enforced in `policy/officer.py` but whose *concurrence* is a human judgment);
- **sensitivity classifications** (the C1–C5 coordinate matrix of §43.3).

These are editorial judgments and must not be made by whoever happens to hold
commit access. The board's two-reviewer concurrence is the human counterpart to
the deterministic officer-naming gate.

## Resistance to capture (SIG-GOV-016)

SIG documents how it resists capture by any single funder, ideology, or vendor
interest:

- **Funding it will not accept.** SIG will not accept funding from surveillance
  vendors, their trade bodies, or law-enforcement agencies whose infrastructure
  SIG documents, nor any funding conditioned on suppressing, delaying, or shaping
  particular claims. No funder buys editorial outcomes.
- **No single point of control.** Schema/ruleset authority (maintainers) is
  separated from editorial authority (the board); neither can unilaterally
  publish or suppress a contested person-named claim.
- **Ideological neutrality of method.** SIG documents institutions and
  infrastructure, not people (§0.7); the same provenance and confidence standards
  apply to every claim regardless of who it implicates.

## Continuity, succession, and degraded mode (SIG-GOV-021, SIG-GOV-022, SIG-GOV-023)

This document adopts the project's continuity posture; the executable pieces land
in their own phases and are cross-referenced here.

- **Degraded-but-alive mode (SIG-GOV-020/021).** SIG defines a mode that runs at
  approximately zero marginal cost — static exports, scheduled jobs on free
  infrastructure, object storage — serving the last-published dataset behind an
  honest staleness banner. This mode **must be tested**, and its known decay
  paths documented, including that free CI schedulers commonly disable dormant
  scheduled workflows after a period of repository inactivity, which will
  silently stop a zero-cost pipeline unless a keepalive is designed in. *A
  sustainability plan that fails silently is not a plan.* The keepalive and its
  test are delivered by the operations phase; this policy fixes the requirement.
- **Succession commitment (SIG-GOV-023).** If the project ends, the data and code
  are released in a form that lets others continue. The evidence store's OCFL
  layout (§17.3) means the archive stays readable **without SIG's software**.
- **Continuity (SIG-GOV-022).** Geographic mirrors; deposits to Zenodo and
  Software Heritage; an offline distribution path; and a documented plan for the
  disappearance of the primary domain.
