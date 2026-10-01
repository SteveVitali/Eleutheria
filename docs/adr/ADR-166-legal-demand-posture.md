# ADR-166: Legal-demand posture: a written posture before the first demand, published counts, and the warrant canary declined (SIG-SEC-003)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P. A-4 adopted the posture package at 2026-10-01T04:03:25Z (round 3); the operator's words are
  recorded verbatim below.
- **Requirement ids:** SIG-SEC-003 (owned; the SHOULD-level warrant canary is declined). Related: SIG-SEC-002 (data
  minimisation) and SIG-GOV-012 (ADR-165).
- **Spec:** `docs/2_canonical_design_spec.md` §44.3
- **Implemented by:** P37.8 (legal-demand posture and published counts; posture text through a copy batch, B-2). G1
  owns the data-holdings inventory and the J1 NEW-9 grant fix. (`PD/data/round11_plan.csv`; PLAN §5.10)
- **Sources:**
  - `PD` = `docs/build/planning/2026-09-30-next-phase/`
  - `PD/feedback/RATIFICATION_LOG.md` round 3
  - `PD/data/decision_catalog.csv` rows Q-7 and Q-E2-09
  - `PD/design/E2-governance-options.md` E2-10
  - `PD/research/E1-contradictions.md` E1-10
  - `PD/NEXT_PHASE_PLAN.md` §5.10, §6.3, §7
- **Relationship to landed ADRs:** PLAN §7 lists no status line for ADR-166, so it supersedes, amends, qualifies and
  extends none. Related ADRs:
  - ADR-135: isolated, durable, anonymous correction intake. The receiver is built but not operating.
  - ADR-164: the public decision log.
  - ADR-165: the interim legal home.
  - ADR-167: counsel basis.
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). This file records an
  operator decision taken at GATE-P; the record text is agent-drafted.

## Context

**What the requirement says.** SIG-SEC-003 (MUST): *"SIG MUST publish a transparency report covering legal demands
received, complied with, and refused, and SHOULD maintain a warrant canary. The response posture for demands directed
at SIG MUST be documented **before** the first demand arrives."*

**What exists today** (E1-10, E2-10):

- None of the three parts exists, and no row or owner is recorded.
- `/corrections/` shows intake counts from a channel that cannot receive anything.

**What a legal demand could target** (E2-10, planning-time reads, cited):

- the `evidence_access_log` (requester, purpose), which the public API role can read through a blanket grant (J1
  NEW-9; the fix is G1's);
- infrastructure logs (G1 NEW-12: no Data Access audit logs);
- intake personal data, if the receiver ever operates.

Today the intake is e-mail only. The receiver is not operating (B-8; ADR-135; WV-05, ADR-180).

**Why a canary is hard here.** A warrant canary needs one person to re-publish it on schedule, and a missed update
signals a demand that did not happen (E2-10, inference). SIG has one maintainer (U-008) and no counsel (U-013).

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

**A-4.** Answered in round 3, at 2026-10-01T04:03:25Z.

- The question, as logged: "governance stance: disclosed single-maintainer, no-counsel posture (… SEC-003 demand
  posture + counts …)".
- The operator's answer, verbatim: **Adopt disclosed posture (Recommended)**.
- sha256 `8509460b2536605180168be29f10318fbc6122f2b26c582d4f7dd4dd623ce626`, computed at writing with
  `printf '%s' "<answer>" | shasum -a 256`.
- Label: option label **agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z**.

**The A-4 member this ADR records.** `PD/data/decision_catalog.csv` Q-E2-09. The options presented were:

- (a) relax the requirement;
- (b) full, incl. warrant canary;
- (c) *"written posture now + published legal-demand counts; canary declined with rationale (no counsel review)"*.

The `operator_answer`, verbatim:

> *"c — written legal-demand posture + published counts; warrant canary declined"*

### What is decided

1. **SIG owns SIG-SEC-003.** The operator adopts a **written demand-response posture**, published on the site (P37.8).
   - **Outline.** E2-10's outline, agent-drafted:
     - what SIG holds, and how it minimises what it holds;
     - who receives legal process (the operator, as the interim legal home, ADR-165);
     - how preservation requests are handled;
     - the user-notice policy;
     - the publication of counts.
   - **Wording.** The posture text is agent-drafted. It ships only after the operator confirms it verbatim in a copy
     batch (B-2).
   - **No counsel review.** Q-E2-09's option (c) says "(no counsel review)". The text states that it is not legal
     advice and has not been reviewed by counsel (ADR-167).
2. **Legal-demand counts are published.** The site shows demands received, complied with and refused, with an as-of
   date (P37.8).
   - Counts only: no requester identity and no case detail.
   - Each count follows the transparency scrub and Part VIII rules (ADR-162).
3. **The warrant canary is declined.** SIG-SEC-003 makes the canary a SHOULD, and this ADR records the deviation.
   - **Rationale (E2-10).** One maintainer cannot guarantee scheduled re-publication. A lapsed canary is itself a false
     signal. A canary raises legal questions that SIG has no counsel to answer.
4. **Data minimisation stays the main protection** (SIG-SEC-002). G1 keeps the data-holdings inventory alongside the
   J1 NEW-9 grant fix. The posture page describes what is held only as specifically as is safe.
5. **Coverage and timing.**
   - SIG-SEC-003's "before the first demand" clause stays an owed obligation until P37.8 lands. T4 opens it as a new
     OPEN row, "SEC-003 owner" (PLAN Appendix A, T4).
   - This ADR does not claim the posture already exists.

## Consequences

- **A plan exists before it is needed.** A subpoena, preservation letter or takedown demand meets a written posture,
  not an improvised one, once P37.8 lands.
- **The gap until then.** Until P37.8 (11D) lands, a demand arriving earlier meets no published posture. That gap is
  recorded as the OPEN SEC-003 row, not hidden.
- **What the site may claim.** Its public statement is limited to the posture and the counts. No canary is claimed.
- **Exposure falls on one person.** Every demand lands on the operator as the interim legal home (ADR-165), with no
  counsel. The posture records that rather than removing it (not legal advice).
- **The data-access surface** is the `evidence_access_log` grant (J1 NEW-9). Fixing it reduces what a demand could
  reach. That fix is G1's, not this ADR's.

## Alternatives considered

- **Relax SIG-SEC-003** (E2-10 option a): document the posture only when the first demand arrives, or drop the report
  until volume exists. Rejected: this defeats the requirement's "before".
- **The full requirement, including a warrant canary** (E2-10 option b). Rejected: a lapsed canary is a false signal,
  and canary maintenance has no second person and no counsel.
- **Request a counsel review of the posture** (E2-10's original option c). Not taken: there is no counsel (U-013), and
  Q-E2-09's option (c) as answered says "(no counsel review)".

## Revisit trigger

- **The first legal demand arrives:** a subpoena, warrant, preservation letter, takedown demand or threat letter. It is
  handled under the posture, the counts update, and the posture is re-read against what happened. This is also WV-01's
  trigger (ADR-165).
- **The legal home changes:** a fiscal sponsor or entity is formed (ADR-165).
- **What SIG holds changes:** for example, the intake receiver starts operating and holds personal data (ADR-135;
  D-P32.16-1), or a new access log or contributor data store is added.
- **Counsel is obtained** (LATER-05).
- **A second maintainer joins,** or the operator asks for a canary. A canary may then be maintainable; recording that
  needs a new ADR.
