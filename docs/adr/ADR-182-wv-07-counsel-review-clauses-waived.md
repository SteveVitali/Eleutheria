# ADR-182: WV-07 — the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037 waived; rights decisions rest on the operator's recorded determinations

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-LIC-009 (counsel-referral clause WAIVED; risk-register clause stands), SIG-INGEST-037 (counsel clause WAIVED; the ADR-level-decision rule and rule 4 stand)
- **Spec:** docs/2_canonical_design_spec.md §42.3 — SIG-LIC-009 at lines 6196–6200 (source `docs/research/_meta/spec_src/90_partVIII_s42to43_lic_pub.md`); §26 — SIG-INGEST-037 at lines 4494–4497 (source `docs/research/_meta/spec_src/52_partIV_s23to26_connectors_parse.md`); line numbers as built at `71e8bc83`
- **Decision:** the operator's answer to A-23 part 1 (waiver candidate WV-07), 2026-10-01T04:28:49Z — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, round 9
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §5.10, §6.3 (SIG-LIC-004/009 and SIG-INGEST-036/037/046c rows), §6.5 (WV-07 row), §7 row 182, §11.3, §14 R-19/R-20
- **Related:** ADR-167 (counsel basis: past "counsel" determinations re-recorded as the operator's own; E2's label text), ADR-168 (collection conduct), ADR-184 (the terms-conflicted fetch envelope — an ADR-level crawler-policy decision), ADR-187 (WV-09), ADR-188 (WV-10), ADR-166 (legal-demand posture); `docs/risk_register.md` RISK-P0-01…04, RISK-P0-06
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

Two MUSTs require counsel: SIG-LIC-009 requires four licensing questions to be referred to counsel before launch, and
SIG-INGEST-037 makes any deviation from the crawler-conduct policy "an ADR-level decision requiring counsel". SIG has
no counsel. The operator stated before S5 that "counsel" so far meant the operator, that there is no counsel, and
not to block on counsel (Q-26; U-013; META_PLAN §7.1); at C-3 they adopted the sentence that the 2026-09-16 and 09-24
"counsel" determinations were their own (recorded by ADR-167). Thirteen landed ADRs carry counsel-conditioned revisit
clauses that can never fire for that reason (F3 §5.4, NEW-8). WV-07 asked whether to waive the two counsel clauses or
keep them owed (LATER-05).

## Decision

### The operator's words

- **Answer to A-23 part 1 (multi-select; a tick waives), verbatim:** "WV-01 legal home (Recommended), WV-02 editorial
  board (Recommended), WV-03 second reviewer (Recommended), WV-07 counsel clauses (Recommended)" — round 9,
  2026-10-01T04:28:49Z.
- **Adopted sentence — agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z:**

  > I waive the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037; rights decisions rest on my recorded determinations, labelled as such.

  sha256 `c5a71e9d7fd90f0bab12252ec7a7b4da60c5463a582339c4d33d36f0418d25ac` (`printf '%s' "<sentence>" | shasum -a 256`,
  recomputed by SEED-11d; equals S6's value, `design/S6-ratification-applied.md` §5).

### The requirements and the clauses waived

> **SIG-LIC-009 (MUST).** The following MUST be referred to counsel before launch and MUST appear in
> the risk register: whether API responses returning device-linked claims constitute distribution of
> a Derivative Database under **ODbL clause 4.4(b)**; whether jurisdiction geometry sourced from OSM boundary
> relations contaminates the operator property under the Collective Database fourth bullet; the
> correct regional-cut unit; and the EU sui generis database right for the international phase.

— `docs/2_canonical_design_spec.md:6196-6200`

> **SIG-INGEST-037 (MUST).** Rule 4 is not merely ethical. Circumvention techniques have been held
> to support anti-circumvention claims independent of any computer-fraud theory, and vendor API terms
> in this sector expressly prohibit bulk extraction (R8). The policy is also a **legal posture**, and
> deviating from it is an ADR-level decision requiring counsel, not an engineering judgment.

— `docs/2_canonical_design_spec.md:4494-4497`

- **Waived in SIG-LIC-009:** "MUST be referred to counsel before launch".
- **Stands in SIG-LIC-009:** "MUST appear in the risk register" — RISK-P0-01…04 stay in `docs/risk_register.md`, and
  the plan carries the live exposures as §14 R-19 (express-terms rows) and R-20 (EU/UK database right on N1–N21).
- **Waived in SIG-INGEST-037:** "requiring counsel".
- **Stands in SIG-INGEST-037:** rule 4 and its legal posture, and "deviating from it is an ADR-level decision … not an
  engineering judgment". Every Round-11 deviation from the crawler-conduct policy is therefore still an ADR, now
  resting on the operator's recorded determination: GL-GATE-08 on every host (ADR-168), the terms-conflicted fetch
  envelope (ADR-184), rule 6 for DocumentCloud/MuckRock (ADR-187), the Flock portal probe (ADR-188).

### Scope

Every rights and crawler-policy decision while this ADR stands. Coverage: `WAIVED(ADR-182)` for the two counsel
clauses, the standing clauses named in `accepted_scope` (T4, SEED-14).

### Compensating controls

1. **Labelled determinations.** Every rights decision is recorded as the operator's own determination (no counsel),
   labelled as such in the registry and the records (ADR-167; row **P34.16**: `sources.toml` "counsel" reviewer values
   become "the operator's own determination (no counsel)").
2. **The label on every artifact.** ADR-167 and every release manifest carry E2's label text once the operator confirms
   it verbatim in a copy batch — agent-drafted (E2:569-571): *"No lawyer's written opinion has been obtained; nothing
   here states that this publication has been cleared by counsel."* (plan §5.10).
3. **No counsel claims.** The Round-11 acceptance counts 0 counsel claims without basis (plan §5.10; the 11A live probe
   and P38.1).
4. **The risk register keeps the questions.** SIG-LIC-009's four questions stay open risk-register rows; R-19 and R-20
   carry their mitigations and triggers.
5. **Deviation stays an ADR.** No crawler-policy deviation happens by engineering judgment; each is an ADR naming the
   operator's words (list above). RISK-P0-06 (INGEST-037 as a legal posture) is closed by the collection-conduct ADR
   (ADR-168) restating the posture in the operator's A-5 words (plan §6.5).

## Consequences

- SIG launches and fetches with no legal opinion behind any rights or conduct decision; a legal challenge lands on the
  operator's own determinations (plan §14 R-10, R-19, R-20, R-22).
- The counsel-conditioned revisit clauses of the thirteen landed ADRs F3 §5.4 lists (ADR-011, 034, 035, 041, 042, 055,
  083, 084, 085, 086, 088, 094, 106) cannot fire as written; Round 11 records such changes as the operator's
  determinations instead.
- T4 records the verdicts and a BACKLOG revisit row; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **Keep the clauses owed (option b; LATER-05).** Publication would rest on the operator's recorded risk acceptance only
  where they gave one, with the clauses listed unmet at GATE-ANNOUNCE. Not chosen.
- **Obtain a written opinion (E2-05 options b/c).** Estimated ≈ $0 pro bono to ≈ $3.5k–10.5k paid (plan §15 LATER-05);
  not sought this round.

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- the operator obtains counsel (LATER-05): each operator determination this ADR rests on is then put to counsel;
- a first legal demand arrives (handled under the legal-demand posture, ADR-166);
- a rights holder objects to a determination recorded under this ADR.
