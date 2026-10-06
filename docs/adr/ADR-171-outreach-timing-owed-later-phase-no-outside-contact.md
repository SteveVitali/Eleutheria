# ADR-171: Outreach timing — outreach, records-request sending, recruiting and contribution-back are owed later-phase

- **Status:** Accepted
- **Phase:** Round 11 / Stage B, T1 (seed; `NEXT_PHASE_PLAN.md` §7 row 171)
- **Ticket:** SEED-11
  (Stage-B unit SEED-11c; run ledger `docs/build/runs/SEED-11c.md`)
- **Date:** 2026-10-01 — decided by the operator at GATE-P: B-6 (member Q-E2-12) at 2026-10-01T04:33:54Z (log round 11),
  on the operator's standing instruction U-011 (2026-09-30T21:58:23Z)
- **Written:** 2026-10-01T07:42:45Z (`date -u`; Claude Code, Opus 5.5, Stage-B sub-agent)
- **Base:** `r11/seed` tip `f66b2450`
- **Decision owner:** the operator (GATE-P). This ADR records the decision.
- **Relation to landed ADRs:** none named by §7. ADR-041 (records-request generator), ADR-055 and ADR-069
  (contribution-back) are unchanged; their live legs stay behind their own gates.
- **Related:** SIG-CONTRIB-012, SIG-CONTRIB-012a, SIG-CONTRIB-013, SIG-INGEST-029, SIG-INGEST-030a, SIG-GOV-024,
  SIG-CHART-033; Q-28; DEFERRALS D-P21.1-2, D-R7.2-SEND, D-P21.7-1; RISK-P16-13; LATER-03, LATER-04; ADR-168 (crawler
  conduct, opt-outs), ADR-169 (rights), ADR-187 (WV-09: rule 6 waived for DocumentCloud/MuckRock). `PD` =
  `docs/build/planning/2026-09-30-next-phase/`: `PD/NEXT_PHASE_PLAN.md` §4.1 (Q-28, autonomy), §4.4 B-6, §6.3, §6.5,
  §13.5, §15; `PD/feedback/OPERATOR_FEEDBACK.md` U-011; `PD/feedback/RATIFICATION_LOG.md` round 11;
  `PD/design/E2-governance-options.md` E2-09; `PD/data/decision_catalog.csv` row Q-E2-12;
  `PD/universe/UNIVERSE_DISPOSED.csv` (the outreach ids → LATER-04).

## Context

The spec makes **Stage-0 outreach a precondition**: before a connector is written for an ecosystem or federation-compact
project, SIG MUST have attempted contact and recorded the outcome (SIG-CHART-033, SIG-INGEST-029, SIG-CONTRIB-012);
outreach remains a Phase-0 deliverable even where the data is already accessible, to agree ShareAlike attribution, honour
the upstream's refresh rate and offer archival succession (SIG-INGEST-030a, SIG-CONTRIB-013, SIG-GOV-024); a project's
public ask for help SHOULD be the opening offer (SIG-CONTRIB-012a).

What happened instead (E1-09/E2-09): the operator skipped Stage-0 outreach (WONTFIX "optional", 2026-09-16, no ADR —
DEFERRALS D-P21.1-2, D-CCOPS.1-2, D-JURIS.2-2); ecosystem connectors run live (e.g. Eyes on Flock into the CC-BY-SA
portal compartment); some ecosystem data is live with missing or wrong credit (E2-12); the unsent outreach letter says
SIG honours robots (E2-07); and the five outreach ids carry four different verdicts.

The operator then set a standing rule (U-011, 2026-09-30T21:58:23Z): *"agents should have maximal autonomy but budgets
on money spent should always be made clear and transparent to human who approves any budgets or increases, and no one
should be contacted outside the project."* Q-28 (recruiting) was answered **no** on the same basis (plan §4.1).

The operator was asked B-6 (log round 11): "residual E2 lines incl. registering sig-project.org + moving the UA; SWH after
history scan", options *As stated (Recommended)* · *Move UA, don't buy domain* · *As stated, no SWH deposit*. Its member
Q-E2-12 read: *Stage-0 outreach MUST vs U-011 ('no one should be contacted outside the project')*, options a) amend by
ADR: outreach becomes an owed later-phase obligation with trigger 'operator authorizes outside contact' · b) keep as a
MUST, MISSING.

## Decision

1. **Outreach timing is amended, not waived** (B-6 answered *"Move UA, don't buy domain"*, 2026-10-01T04:33:54Z;
   Q-E2-12 **a**, as recommended). Stage-0 outreach changes from a pre-connector precondition to an **owed later-phase
   obligation**, with the trigger **"the operator authorises outside contact"** (U-011 revisited). It covers
   SIG-CONTRIB-012, SIG-CONTRIB-012a, SIG-CONTRIB-013, SIG-INGEST-029, SIG-INGEST-030a, SIG-GOV-024 and SIG-CHART-033.
   These ids are verdicted **owed later-phase (LATER-04) — not WAIVED** (plan §6.5, §6.6; Appendix B row 2), with one
   consistent verdict across the outreach set (Q-E2-12's decision line; T4 applies it), and they stay on GATE-ANNOUNCE's
   "spec MUSTs unmet at launch" list that the operator signs verbatim (§13.5). *Agent note (labelled):* plan §6.3 lists
   "SIG-CONTRIB-012/012a/013/030a"; the spec has no SIG-CONTRIB-030a — the id meant is SIG-INGEST-030a, and E2-09 also
   names SIG-INGEST-029; both are included here.
   B-6 as a whole was answered **against the recommendation**, but only on its domain line: the operator declined
   *"As stated (Recommended)"*, which would have registered `sig-project.org` defensively (Q-E2-03 a; recorded in
   ADR-168). The outreach member Q-E2-12 was answered as recommended.
2. **The same timing governs every other outward contact by the project:**
   - **sending records requests** — the generator stays *draft, never send* (D-R7.2-SEND; LATER-04; its trigger also
     needs a consenting, residency-valid filer);
   - **recruiting** reviewers, contributors, volunteers or a second maintainer through outreach (Q-28 = no; LATER-04);
   - **contribution-back posting** — MapRoulette challenges and the OSM changeset feed stay dry-run (D-P21.7-1, HG-08;
     LATER-03), and the OSM Organised Editing filing waits (RISK-P16-13; LATER-04);
   - **asking a source's owner** — e.g. a Nation's consent for tribal data (I7 TR lines option b, not chosen; B-37 took
     facts + citations), a rights-holder's written permission, or a vendor's consent.
3. **Agents contact no one.** No agent sends an e-mail, form, records request, issue, comment, pull request, post or
   sign-up to anyone outside the project. The operator's own scheduled actions (plan §11.2 — e.g. the `contact@` alias,
   key registrations after it, deposits, the eventual announcement) are the operator's acts, not outreach under this
   ADR, and are not delegated to agents.
4. **Meanwhile, compensating posture** (from E2-09's option a/c controls, as the plan carries them):
   - honest registry postures (`compact_status` such as `public_terms_only`), published once the registry export ships;
   - structural attribution fixed and gated at publish (P34.21a/b), so ecosystem data carries the right credit;
   - licence compartments kept (e.g. the CC BY-SA 4.0 compartment for the Eyes on Flock data, ADR-169);
   - any opt-out from an upstream honoured at once under §26 rule 7 (ADR-168);
   - the outreach letter's text corrected (P36.1b, Q-E2-02) before any future send;
   - SIG publishes no claim that it contacted, consulted or partnered with any project.
5. **Rule 6 of §26 ("ask first" for small civil-society projects)** keeps binding every source except
   DocumentCloud/MuckRock, for which the operator waived it (WV-09, ADR-187) — because asking first is outside contact.
   *Agent interpretation (labelled):* for any other small civil-society source whose compact is unresolved, rule 6 and
   U-011 together mean the source waits rather than being asked.

## Operator words recorded (verbatim)

sha256 = `printf '%s' '<text between the quote marks>' | shasum -a 256` (UTF-8), computed by SEED-11c when writing this
ADR (after the fact, by the method S6 used).

| line | time | words | label | sha256 |
|---|---|---|---|---|
| U-011 | 2026-09-30T21:58:23Z (`OPERATOR_FEEDBACK.md`, consolidated round) | *"agents should have maximal autonomy but budgets on money spent should always be made clear and transparent to human who approves any budgets or increases, and no one should be contacted outside the project."* | the operator's own words | `fd508cbda91312bf85ac3123bc9bc661823f8511683b4e8e9f17dc73dee550d1` |
| B-6 (incl. Q-E2-12 a) | 2026-10-01T04:33:54Z | *"Move UA, don't buy domain"* | option label selected by the operator (against the recommendation on the domain line; Q-E2-12 as recommended) | `7a31095fa9947a22d967f8b20f7ccb6f05a7596f0b0f282359c226d61073de68` |

## Consequences

- No outreach, records-request sending, recruiting or contribution-back happens in Round 11; the outreach ids are
  reported as owed later-phase, never as MET and never as waived.
- **Exposure, plainly:** ecosystem projects are SIG's natural allies and its reviewer pool (E2-09, citing E3); finding their
  data republished without contact — and, until the attribution fix, sometimes with the wrong credit — risks those
  relationships. The share-alike terms apply whether or not anyone is contacted.
- The archival-succession offer (SIG-CONTRIB-013, SIG-GOV-024) is not made while an upstream SIG depends on could
  disappear (SIG-INGEST-030a calls the Eyes on Flock API a single point of failure for the portal layer).

## Alternatives considered

- **Keep Stage-0 outreach a MUST, MISSING** (Q-E2-12 b) — not chosen; it would record a permanent failure the operator's
  standing rule makes certain.
- **Contact the projects whose data is live after the attribution fix** (E2-09's original hybrid, c) — not offered at
  GATE-P once U-011 ruled out outside contact; it becomes the natural first step when the trigger fires.
- **Waive the outreach MUSTs** (F2b's proposal) — rejected at planning (Appendix B row 2): the obligation is owed later,
  not removed.

## Revisit trigger

- **The operator authorises outside contact** (U-011 revisited; LATER-04, and LATER-03 for contribution-back with
  HG-08) — then outreach to the ecosystem projects whose data is live comes first (E2-09 names Eyes on Flock, DeFlock and
  the EFF Atlas), with the attribution correction and the archival-succession offer.
- An **ecosystem project or upstream objects, opts out, changes its terms or licence, or publicly asks for help** with a
  problem SIG is solving (SIG-CONTRIB-012a).
- An upstream SIG depends on **stops publishing** (the succession case SIG-INGEST-030a names).
- A consenting, residency-valid **records-request filer** is available and outside contact is authorised (D-R7.2-SEND).
- **GATE-ANNOUNCE**: the outreach MUSTs appear on the "unmet at launch" list the operator signs.
