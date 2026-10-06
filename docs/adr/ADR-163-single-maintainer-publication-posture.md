# ADR-163: Single-maintainer publication posture: SIG-PUB-008 stands, nobody is named, the naming gate denies by default, and the HG-11 second-reviewer role is waived for Round-11 releases (WV-03)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P, in two steps:
  - A-4 adopted the posture package (2026-10-01T04:03:25Z, round 3).
  - A-23 adopted waiver WV-03 (2026-10-01T04:28:49Z, round 9).

  The operator's words are recorded verbatim below.
- **Requirement ids:** SIG-PUB-008 (stands; nothing in it is waived for naming individuals), SIG-PUB-004…010 (the §43.4
  officer-naming test), SIG-PUB-017; HG-11's second-reviewer role (WAIVED for Round-11 releases, WV-03)
- **Spec:** `docs/2_canonical_design_spec.md` §43.4, §43.8; the gate register in `docs/3_sig_golive_spec.md` (HG-11)
- **Implemented by:**
  - P35.28: the officer-naming gate on the publication path, default deny (PUB-007, E2 H-9).
  - The readout generator: P35.60, and every Class S readout row (P35.63, P36.72b, P37.65b).
  - The repo honesty corrections: P34.16 and P34.17.

  Rows are from `PD/data/round11_plan.csv`.
- **Sources:**
  - `PD` = `docs/build/planning/2026-09-30-next-phase/`.
  - `PD/feedback/RATIFICATION_LOG.md` rounds 3 and 9.
  - `PD/data/decision_catalog.csv` rows Q-7, Q-E2-06, WV-03.
  - `PD/design/E2-governance-options.md` §0 and E2-01.
  - `PD/research/E1-contradictions.md` E1-01.
  - `PD/NEXT_PHASE_PLAN.md` §5.10, §6.3, §6.5, §7, §13.5.
- **Relationship to landed ADRs:** PLAN §7 lists no status line for ADR-163, so it supersedes, amends, qualifies and
  extends none.
  - ADR-145 recorded SIG-PUB-008 "checked + unchanged" with the sole-maintainer state as an operator disposition. This
    ADR is the first ADR that records that posture.
  - Related: ADR-124 (publication eligibility), ADR-152 (every Class S readout says "no human check performed"),
    ADR-159 (persons are never auto-allowed), ADR-164 (interim editorial authority), ADR-179 (WV-04).
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). This file records
  operator decisions taken at GATE-P; the record text is agent-drafted.

## Context

**What the spec requires.** SIG-PUB-008 (MUST): *"Two independent reviewers MUST concur in writing. Disagreement
defaults to no-publish. The decision, its reasoning, and its reviewers MUST be recorded."* It is the last prong of the
§43.4 officer-naming test.

**What the record says** (E1-01, E2-01; `docs/tickets/DEFERRALS.md` row D-P21.4-2):

- **2026-09-16, the recorded "waiver".** The operator filled both reviewer roles personally. The *independence*
  requirement was recorded as "waived by explicit operator decision, not satisfied". The row was closed `DONE`, and
  the coverage matrix carries SIG-PUB-008 as `MET`.
- **No ADR.** No ADR recorded this, and ADR-145 left the spec text unchanged.
- **Go-public.** It later ran with HG-11's second reviewer "skipped-by-operator".

**Facts re-read at planning (E2-01) and confirmed at writing:**

- **The Python gate is enforced.** `policy/src/policy/officer.py` (`_concurrence_ok`) requires at least two distinct
  reviewer ids, each flagged independent and each with a written rationale. The production caller passes no reviewers,
  so every person-naming predicate is refused.
- **The web gate has a latent gap** (E1 NEW-12). `web/src/lib/publication.ts` lets a US public-employee name through
  on jurisdiction alone. The gap is not live, because no person is named today.
- **Nobody is named.** The recorded "waiver" therefore excuses nothing until someone wants to name a person.

**People available.** There are no humans on the project besides the operator (U-008), and no one outside the project
is contacted (U-011). A second independent reviewer cannot be the operator.

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

**A-4 (2026-10-01T04:03:25Z, round 3).**

- **The question, as logged:** "governance stance: disclosed single-maintainer, no-counsel posture (PUB-008 stands;
  interim editorial authority + public decision log; interim individual legal home; SEC-003 demand posture + counts;
  counsel records re-labelled as operator determinations; DB-right / ODbL bases as operator determinations with
  guardrails)".
- **Options:** *Adopt disclosed posture (Recommended) · Keep spec as is*.
- **The operator's answer, verbatim:** **Adopt disclosed posture (Recommended)**.
  - sha256: `8509460b2536605180168be29f10318fbc6122f2b26c582d4f7dd4dd623ce626`
  - Label: the option label is **agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z**.

**WV-03 (A-23 part 1, 2026-10-01T04:28:49Z, round 9).** The operator ticked *"WV-03 second reviewer (Recommended)"*.
The waiver sentence adopted by that selection, verbatim:

> *"I waive the second-reviewer role (SIG-PUB-008 / HG-11) for Round-11 releases; each readout states 'single
> maintainer, no second reviewer'."*

- sha256: `44644f6bd6ffdcf7d2319f9369592d8d115236be78dbad4cc4f9468ad69c9157`
- Label: **agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z**.
- How the sha256 was computed: `printf '%s' "<sentence>" | shasum -a 256` at writing. It matches the value S6 computed
  (`PD/design/S6-ratification-applied.md` §5).

**The A-4 member this ADR records.** `PD/data/decision_catalog.csv` Q-E2-06, `operator_answer`, verbatim:

> *"c — SIG-PUB-008 stands unamended; nobody named; web gate default-deny; the HG-11 second-reviewer role waived for
> Round-11 releases (WV-03)"*

### What is decided

1. **SIG-PUB-008 stands unamended.**
   - **Posture.** The operated posture is that **no named individual is published**. Officer and person naming stay
     off. It is not a waiver of the two-reviewer test: nothing in this ADR lets one person decide to name someone.
   - **Python gate.** It is unchanged.
   - **Web gate.** It becomes **default-deny** for person names unless a concurrence record exists (P35.28; E2 H-9).
2. **The HG-11 second-reviewer role is WAIVED for Round-11 releases (WV-03).**
   - **Who signs.** The operator alone signs HG-11 and Class S readouts.
   - **The readout sentence.** Each readout states **"single maintainer, no second reviewer"**. Under ADR-152 it also
     states "no human check performed".
   - **Scope.** The waiver ends with Round 11. A Round-12 release needs a new decision.
   - **What it does not cover.** It does not waive SIG-PUB-008's concurrence for naming an individual.
3. **Compensating controls** (PLAN §6.5, WV-03 row):
   - the readout sentence in every Class S readout;
   - nobody named;
   - the default-deny web gate;
   - ADR-159: a person-shaped name is never auto-allowed as an organisation.
4. **The disclosure the site carries.** E2-01 drafted this text; it is agent-drafted and ships only after the operator
   confirms it verbatim in a copy batch (B-2):

   > *"SIG does not publish the names of individual officers or officials. Our standard requires two independent
   > reviewers to agree in writing before anyone is named; SIG currently has one maintainer, so no one is named."*

   Until it is confirmed, no text may claim a second reviewer or an independent concurrence (P34.17 removes the fixture
   two-reviewer claims).
5. **Correcting the earlier record.** D-P21.4-2's 2026-09-16 "waiver" and RISK-P0-05's description of a two-reviewer
   control get appended dated corrections. These are not rewrites, and they cite this ADR (T4, SEED-14; OM-13).
   - T4 records the coverage verdicts (PLAN §6.4, §6.6) as follows:
     - **WAIVED(ADR-163)** for the HG-11 second-reviewer role, `accepted_scope` = Round-11 releases.
     - SIG-PUB-008's naming concurrence keeps a non-waiver verdict. Q-E2-06 = c named MET-ENGINEERED, with the human
       leg owed when naming is wanted.

## Consequences

- **Honest public text.** No public claim of a second reviewer or an independent review survives, and the
  `/editorial-standards/` fixture is replaced (ADR-179, WV-04).
- **One person's sign-off.** Round-11 releases ship on one person's sign-off. A wrong publication decision gets no
  second look before release. The sentence in every readout says so, and withdrawal (ADR-124; the 15-minute technical
  withdrawal, ADR-161) is the recovery path.
- **Accountability by role, not by name.** Accountability stories that hinge on a named official stay unpublishable in
  Round 11. Names that appear inside quoted source documents (for example, contract signature blocks) remain the
  residual exposure. The Part VIII screens handle them (ADR-185).
- **GATE-ANNOUNCE must re-decide.** It asks for a keep/lift answer on WV-03, because the waiver's scope ends with
  Round 11 (PLAN §13.5; S6R-18).

## Alternatives considered

- **Waive SIG-PUB-008's independence so that the maintainer may name people alone** (E2-01 option a). Rejected.
  Naming individuals is the publication most likely to bring harassment or a reputation complaint, and a single
  reviewer is exactly what the spec was written to avoid.
- **Recruit a second independent reviewer** (E2-01 option b). Ruled out by U-008 (no other humans) and U-011 (no outside
  contact).
- **Keep the spec as is, with no ADR** (A-4 option "Keep spec as is"). Not chosen. The 2026-09-16 "waiver" would stay
  unrecorded, and HG-11 readouts would keep an obligation nobody can meet.
- **Keep the second-reviewer role owed instead of waiving it** (A-23 default if unanswered). Not chosen. Every Round-11
  release would carry an unmet MUST on GATE-ANNOUNCE's list.

## Revisit trigger

- **A second independent reviewer becomes available.** T-EVAL-IND: two or more independent people plus an operator
  contact exception to U-011 (`PD/design/S2-round-structure.md`; PLAN §6.5 WV-03 row).
- **GATE-ANNOUNCE.** The operator's keep/lift answer for WV-03 (PLAN §13.5, S6R-18).
- **The end of Round 11.** WV-03's scope is "Round-11 releases". The next round's planning re-decides it; it is not
  carried over silently.
- **Naming is wanted.** A naming decision about an individual is wanted, or a published text is found to name an
  officer or official.
- **A second maintainer joins.**
