# ADR-165: Interim legal home: an individual, disclosed; SIG-GOV-012/013 waived (WV-01)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P in two steps. A-4 adopted the posture package at 2026-10-01T04:03:25Z (round 3). A-23 adopted
  the waiver at 2026-10-01T04:28:49Z (round 9). The operator's words are recorded verbatim below.
- **Requirement ids:** SIG-GOV-012 and SIG-GOV-013 (both WAIVED, WV-01). Related: SIG-SEC-002 (data minimisation),
  SIG-SEC-003 (ADR-166).
- **Spec:** `docs/2_canonical_design_spec.md` §46.1; the go-live spec `docs/3_sig_golive_spec.md` (GL-GATE-01, HG-01)
- **Implemented by:** P34.16 (repo governance text) and P34.17 (site wording). The disclosure and the list of legal-defence
  resources ship through copy batches (B-2). (`PD/data/round11_plan.csv`; PLAN §5.10)
- **Sources:**
  - `PD` = `docs/build/planning/2026-09-30-next-phase/`.
  - `PD/feedback/RATIFICATION_LOG.md` rounds 3, 9 and 20 (C-5).
  - `PD/data/decision_catalog.csv` rows Q-7, Q-E2-08 and WV-01.
  - `PD/design/E2-governance-options.md` E2-04.
  - `PD/research/E1-contradictions.md` E1-04.
  - `PD/NEXT_PHASE_PLAN.md` §5.10, §6.3, §6.5, §7 and §13.5.
- **Relationship to landed ADRs:** PLAN §7 lists no status line for ADR-165, so it supersedes, amends, qualifies or
  extends no landed ADR. Related: ADR-163, ADR-164, ADR-166 and ADR-167.
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). This file records
  operator decisions taken at GATE-P; the record text is agent-drafted.

## Context

The two requirements this ADR waives:

- **SIG-GOV-012 (MUST):** *"Before public launch, SIG MUST establish a legal home — a fiscal sponsor or its own
  nonprofit — and document what it implies for liability, donations, and legal defence. Operating a project with this
  threat profile as an unincorporated individual effort exposes contributors personally."*
- **SIG-GOV-013 (MUST):** *"SIG MUST identify legal-defence resources appropriate to public-interest research and
  journalism **before** they are needed."*

What the record shows (E1-04, E2-04):

- **Legal home.** SIG has been public since 2026-09-16 with an individual in personal capacity as its legal home. On
  2026-09-15 the operator named it in `docs/governance/governance-and-code-of-conduct.md § Legal home`
  (`docs/tickets/DEFERRALS.md` D-P21.4-1; GL-GATE-01 recorded an interim posture).
- **Gaps.** No legal-defence resources are identified, and no ADR exists. RISK-P0-13 still reads "no public launch
  without it".
- **Visibility.** The live site names no operator. The public repository names the individual.

Options and their costs:

- **Fiscal sponsor.** Applying takes about 5–15 h of operator time. Fees are about 7–10 % of revenue, so they matter
  mainly if money flows (E3 R15, cited by E2-04).
- **Liability.** Whether any sponsorship or entity shields the operator from claims is a lawyer's question.
- **Constraints.** There is no counsel (U-013), no outside contact (U-011), and no humans besides the operator (U-008).

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

**A-4** — round 3, 2026-10-01T04:03:25Z.

- The governance-stance question, which included "interim individual legal home", was answered with this option label,
  verbatim: **Adopt disclosed posture (Recommended)**.
- sha256 `8509460b2536605180168be29f10318fbc6122f2b26c582d4f7dd4dd623ce626`.
- Label: option label **agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z**.

**WV-01** — A-23 part 1, round 9, 2026-10-01T04:28:49Z.

- The operator ticked *"WV-01 legal home (Recommended)"*. The waiver sentence adopted by that selection, verbatim:

  > *"I waive SIG-GOV-012/013 for now: SIG's legal home is me as an individual, disclosed on the site, revisited at
  > announcement, a first legal demand, funding, or a second maintainer."*

- sha256 `b9dc5a9128ac26a5bf8634f1cfb151d872dac43eaf0de4ae82dcf4e446ba9c3a`, computed with
  `printf '%s' "<sentence>" | shasum -a 256` at writing. It matches S6's value (`PD/design/S6-ratification-applied.md`
  §5).
- Label: **agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z**.

**The A-4 member this ADR records** — `PD/data/decision_catalog.csv` Q-E2-08, `operator_answer`, verbatim:

> *"c — interim individual legal home, disclosed, revisited at announcement, a first legal demand, funding or a second
> maintainer; SIG-GOV-012/013 waived (WV-01)"*

**C-5** — round 20, 2026-10-01T04:56:11Z. On the About page's "who runs SIG" section, the operator answered, verbatim:
**Omit until I write it**.

- This sets how the disclosure is worded (item 2).
- C-5 had no recommendation (log, closing table), so the answer is recorded as a selected option label.

### What is decided

1. **SIG-GOV-012 and SIG-GOV-013 are WAIVED for now (WV-01).**
   - SIG's legal home is **the operator as an individual**: an interim, disclosed posture.
   - There is no fiscal sponsor, nonprofit or incorporated entity.
   - No legal-defence resource is retained.
2. **The site discloses the posture.** The disclosure says that SIG's legal home is an individual, with no fiscal
   sponsor, nonprofit or incorporated entity (WV-01, "disclosed on the site"). PLAN §6.5's WV-01 row places it on the
   About and terms pages.
   - E2-04 drafted this wording. It is agent-drafted and ships only after the operator confirms it verbatim in a copy
     batch (B-2):

     > *"SIG is currently run by an individual maintainer, not by an organization. It has no fiscal sponsor or
     > incorporated legal entity yet."*

   - **Open point carried to the copy batch (not settled here).** At C-5 the options for the About page's "who runs
     SIG" section were *'A single independent maintainer' · My name · Omit until I write it*. The operator chose
     **Omit until I write it**, not the "single independent maintainer" wording.
     - So the legal-home disclosure must not reappear as a "who runs SIG" placeholder.
     - Its exact wording and placement are for the operator to confirm verbatim in the copy batch, reconciling WV-01
       with C-5.
     - *Agent interpretation (labelled):* a terms-page sentence about the legal home satisfies WV-01 without a "who
       runs SIG" section. The disclosure names no person unless the operator writes that text (E2-04 advised against
       naming the person beyond what the public repository already shows).
3. **Legal-defence resources are listed, not retained.** This is a compensating control (PLAN §6.5, WV-01 row: "public
   legal-defence resources listed").
   - The list is a page of referral routes taken from E2-04 and E3: EFF Cooperating Attorneys, a law-school clinic, and
     the RCFP hotline.
   - It goes through a copy batch. Listing a resource contacts no one (U-011).
4. **The interim record is corrected forward.**
   - RISK-P0-13 ("no public launch without it") gets an appended, dated correction citing this ADR (T4; OM-13).
   - The governance doc's scope note is reconciled with this ADR by P34.16, through a copy batch.
   - T4 records SIG-GOV-012 and SIG-GOV-013 as **WAIVED(ADR-165)** (PLAN §6.6).

## Consequences

- **Personal liability.** Any claim arising from publication lands on one person. By the spec's own reasoning
  (SIG-GOV-012), that is the exposure a legal home exists to reduce. How much an entity or sponsor would reduce it is a
  lawyer's question, and no lawyer is engaged (U-013; WV-07, ADR-182).
- **Remaining protections.**
  - SIG holds little data about anyone (SIG-SEC-002).
  - No person or plate data is held.
  - Naming is off (ADR-163).
  - There is a written legal-demand posture (ADR-166).
- **Money.** Donations and grants have no home. Funding is a revisit trigger.
- **Public statements.** The site makes no claim of an organisation, nonprofit or sponsor. Public `main` keeps the
  governance text until the operator merges P34.16 (OP-08), and the plan calls that merge sitting a safety item
  (PLAN §5.10).
- **GATE-ANNOUNCE.** It asks for a keep/lift answer on WV-01, because its first trigger is the announcement (PLAN §13.5;
  S6R-18).

## Alternatives considered

- **Pursue a fiscal sponsor or entity now** (E2-04 option b). Not chosen. It needs outside contact (U-011) and operator
  applications, and the liability question that would decide between the options needs counsel (U-013).
- **Amend the spec permanently to an individual home** (E2-04 option a). Not chosen. The operator waived the
  requirement "for now", with revisit triggers.
- **Keep SIG-GOV-012/013 owed with no waiver** (the A-23 default if unanswered). Not chosen. The MUSTs would stay on
  GATE-ANNOUNCE's "unmet at launch" list with no route to meet them.
- **Name the operator on the site** (E2-04's disclosure trade-off). Not decided here. C-5 leaves it to the operator's
  own text.

## Revisit trigger

From WV-01's own words (the operator's adopted sentence, verbatim: "revisited at announcement, a first legal demand,
funding, or a second maintainer"):

- the announcement (GATE-ANNOUNCE asks a keep/lift answer for WV-01; PLAN §13.5, S6R-18);
- a first legal demand or threat letter (also ADR-166);
- funding: a first donation, grant or sponsorship offer;
- a second maintainer.

Also, from E2-04's revisit triggers (agent-drafted):

- the first external contributor, reviewer or board member (ADR-163, ADR-164);
- any counsel advice obtained (LATER-05);
- naming of an individual is wanted.
