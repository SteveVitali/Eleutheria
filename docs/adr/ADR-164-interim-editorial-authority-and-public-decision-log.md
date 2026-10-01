# ADR-164: Interim editorial authority and a public decision log: one maintainer, disclosed; the SIG-GOV-015 editorial board waived (WV-02)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P in two steps.
  - A-4 adopted the posture package (2026-10-01T04:03:25Z, round 3).
  - A-23 adopted waiver WV-02 (2026-10-01T04:28:49Z, round 9).

  The operator's words are recorded verbatim below.
- **Requirement ids:**
  - SIG-GOV-015 (WAIVED, WV-02).
  - SIG-GOV-014 (the published governance document; not waived).
  - SIG-GOV-008 (true deletions are logged here; ADR-181).
  - SIG-STORE-011 (purge uses are logged here; ADR-189).
  - SIG-PUB-008 (naming stays off; ADR-163).
- **Spec:** `docs/2_canonical_design_spec.md` §43.4, §45.4, §46.2
- **Implemented by:** P34.16 (corrections to the governance doc and other repo text); P34.17 (site wording, republish
  #1, R1.5); P37.7 (the public editorial decision log page) (`PD/data/round11_plan.csv`). P34.46 handles the API `/terms`
  correction; PLAN §5.1 Table R2 keeps the interim N-7 notice until then.
- **Sources:**
  - `PD` = `docs/build/planning/2026-09-30-next-phase/`.
  - `PD/feedback/RATIFICATION_LOG.md` rounds 3 and 9.
  - `PD/data/decision_catalog.csv` rows Q-7, Q-E2-07 and WV-02.
  - `PD/design/E2-governance-options.md` §0.1 (H-5) and E2-03.
  - `PD/research/E1-contradictions.md` E1-03.
  - `PD/NEXT_PHASE_PLAN.md` §5.1, §5.10, §6.3, §6.5, §7.
- **Relationship to landed ADRs:** none superseded, amended, qualified or extended (PLAN §7 lists no status line for
  ADR-164). Related: ADR-163 (single-maintainer publication posture), ADR-165 (interim legal home), ADR-181 (WV-06: true
  deletion, publicly logged), ADR-189 (WV-11: the purge function, publicly logged).
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). This file records
  operator decisions taken at GATE-P; the record text is agent-drafted.

## Context

SIG-GOV-015 (MUST): *"An **editorial board** MUST exist for contested claims, officer-naming decisions (§43.4), and
sensitivity classifications, distinct from the technical maintainers. These are editorial judgments and should not be
made by whoever happens to hold commit access."*

E1-03 and E2-03 found that one person holds every role. Among the decisions made by that one person: on 2026-09-22 the
operator signed off the Part-VIII-sensitive classes (`facial_recognition_world_map`, `pathways_rtcc_federation`,
`pathways_acoustic_drone_location`, person naming).

Public text says otherwise. Both statements were confirmed at writing:

- The public governance document (`docs/governance/governance-and-code-of-conduct.md`) says *"An **editorial board
  exists**, distinct from the technical maintainers."*
- The live API terms (`api/src/api/terms.py`) refer re-identification attempts *"to the SIG editorial board and, where
  applicable, to counsel"*.

A board needs 2–3 people distinct from the maintainer (E3 R6). There are no humans on the project besides the operator
(U-008), and no outside contact (U-011).

Code invariants cover part of what a board would guard: no person or plate fields, tier coordinate reduction, and the
officer gate. They do not cover classification judgments such as publishing a world map of facial-recognition
deployments.

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

**A-4.** Round 3, 2026-10-01T04:03:25Z.

- Question, as logged: "governance stance: disclosed single-maintainer, no-counsel posture (… interim editorial
  authority + public decision log …)".
- Operator answer, verbatim: **Adopt disclosed posture (Recommended)**.
- sha256: `8509460b2536605180168be29f10318fbc6122f2b26c582d4f7dd4dd623ce626`.
- Label: option label **agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z**.

**WV-02.** A-23 part 1, round 9, 2026-10-01T04:28:49Z. The operator ticked *"WV-02 editorial board (Recommended)"*. The
waiver sentence adopted by that selection, verbatim:

> *"I waive SIG-GOV-015's editorial board: I hold interim single-maintainer editorial authority, and every
> naming/sensitivity decision goes in a public decision log."*

- sha256: `bee2cd2b1501a8b59faab90a901a486dde459a4ccaf03522d6a2b08d69fa52fd`. Computed with
  `printf '%s' "<sentence>" | shasum -a 256` at writing; it matches S6's value in `PD/design/S6-ratification-applied.md`
  §5.
- Label: **agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z**.

**The A-4 member this ADR records.** `PD/data/decision_catalog.csv` Q-E2-07, `operator_answer`, verbatim:

> *"c — text corrected; ADR records interim single-maintainer editorial authority + a public decision log; the
> SIG-GOV-015 board waived (WV-02)"*

Q-7's answer records that A-4 adopted each member "as recommended". E2-03's recommended decision line therefore also
binds:

> *"Correct the governance doc and API terms now; record by ADR an interim single-maintainer editorial authority (naming
> off, Part VIII invariants in code, a public editorial-decisions log to be built, with the 2026-09-22 class sign-offs
> logged retroactively); constitute a board when a legal-home entity exists or naming is wanted."*

### What is decided

1. **SIG-GOV-015's editorial board is WAIVED (WV-02).**
   - The operator holds **interim single-maintainer editorial authority** over contested claims and sensitivity
     classifications. This is disclosed, never presented as a board.
   - Officer and person naming stays off (ADR-163). Single-maintainer authority therefore never extends to naming an
     individual.
2. **A public editorial decision log** (P37.7).
   - **What it records.** Every naming or sensitivity decision and every contested-claim decision gets an append-only
     entry: date, decision, class, rationale and evidence links (E2-03).
   - **Logged retroactively.** The 2026-09-22 class sign-offs are logged retroactively, dated as such.
   - **Deletions and purges.** The same log records every WV-06 true deletion with its reason (ADR-181; P37.7 notes)
     and every use of the WV-11 purge function (ADR-189). A deletion or purge is a tombstone entry: category and date,
     never the deleted content.
   - **No personal data.** Entries name no private person (Part VIII).
3. **The false text is corrected.**
   - The governance doc and other repo text: P34.16.
   - Site pages: P34.17, R1.5.
   - The API `/terms` text: with the next API roll. The interim is the N-7 notice on `/status/` (PLAN §5.1 Table R2).

   E2-03 drafted the replacement wording below. It is agent-drafted and ships only after the operator confirms it
   verbatim in a copy batch (B-2):

   > *"SIG does not yet have an editorial board. Until it does, editorial decisions (contested claims and sensitivity
   > classifications) are made by the maintainer and recorded publicly in the editorial decisions log. Officer and
   > person naming is turned off."*

   For the API terms, E2-03 drafted: *"…and — where the violation is an attempted re-identification of an individual —
   review by the SIG maintainer and any further action that review warrants."*
4. **Compensating controls** (PLAN §6.5, WV-02 row):
   - the decision log (P37.7);
   - the officer-naming gate, default-deny (P35.28);
   - the Part VIII invariants in code;
   - the disclosure that no board exists.
5. **Coverage.** T4 records SIG-GOV-015 as **WAIVED(ADR-164)** (PLAN §6.6). SIG-GOV-014, the published governance
   document, is not waived. Its "how contested claims are adjudicated" clause is met by the disclosed interim authority
   plus the log, after P34.16's correction.

## Consequences

- **Sensitivity calls rest on one person.** Examples are the facial-recognition world map, RTCC federation and acoustic
  drone location. These are the decisions most likely to cause harm if wrong, and nobody gives them a second look. The
  public log stands in for separation: every such call can be read, dated and contested.
- **Public text stops claiming a board.** Before P34.16 merges, public `main` keeps the false governance text, so the
  operator's merge sitting (OP-08) is a safety item (PLAN §5.10).
- **The log has a fixed scope.** It holds every naming/sensitivity decision, every WV-06 deletion and every WV-11 purge,
  so it is append-only and Part VIII-screened. It never states deleted content.
- **The board is owed later.** The board E2-03 described becomes owed under the triggers below. No recruiting happens
  in Round 11 (U-011).

## Alternatives considered

- **Amend SIG-GOV-015 outright to a single-maintainer model** (E2-03 option a). Not chosen as such. The operator
  waived the requirement in their own words for the interim and kept the board as the target (option c).
- **Constitute a board now** (E2-03 option b). Ruled out by U-008 and U-011, and hard to recruit while the legal home is
  an individual (E2-03, inference).
- **Keep SIG-GOV-015 owed with no waiver** (the A-23 default if unanswered). Not chosen. It would stay on GATE-ANNOUNCE's
  "spec MUSTs unmet at launch" list, with no route to meeting it.

## Revisit trigger

- **A second maintainer joins** (PLAN §6.5, WV-02 row).
- **A naming or sensitivity decision is contested publicly** (PLAN §6.5), or a contested-claim dispute comes from a
  documented organisation (E2-03).
- **Naming of an individual is wanted** (E2-03; ADR-163).
- **A legal-home entity or fiscal sponsor exists** (E2-03; ADR-165). At that point a board becomes recruitable.
- **The operator authorises outside contact** (U-011 revisited, LATER-04). That makes recruiting board members possible.
