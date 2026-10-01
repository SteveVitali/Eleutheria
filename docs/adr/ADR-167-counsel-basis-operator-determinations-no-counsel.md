# ADR-167: Counsel basis — past "counsel" determinations re-recorded as the operator's own determinations (no counsel)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P, in two answers. Both are recorded verbatim below, and both rest on the operator's earlier
  statement U-013 (2026-09-30T21:58:23Z).
  - A-4 (2026-10-01T04:03:25Z, round 3): the posture package.
  - C-3 (2026-10-01T04:54:19Z, round 19): the operator's own sentence.
- **Requirement ids:**
  - SIG-LIC-009: its counsel-referral clause is WAIVED by ADR-182 (WV-07); its risk-register clause stands.
  - SIG-INGEST-037: its counsel clause is WAIVED by ADR-182.
  - SIG-LIC-003, SIG-LIC-004a, SIG-LIC-005: the compartment bases of ADR-086 and ADR-106.
  - HG-02 and GL-GATE-02 in `docs/3_sig_golive_spec.md`.
- **Spec:** `docs/2_canonical_design_spec.md` §42.2, §42.3, §42.3a. The go-live spec's GL-GATE-02 and HG-02 entries.
- **Implemented by:**
  - P34.16: the governance doc, the five `sources.toml` `rights_reviewed_by = "counsel (HG-02)"` values, and the
    `PUBLICATION_CHECKLIST` wording.
  - P34.17: the site wording (R1.5) and the web half of the publication-basis label (E2 H-6).
  - P34.21a/b: the artifact half of the label (`manifest.json`, `LICENCES.json`, `datapackage.json`).
  - P34.46: the API `/terms` text.
  - T4 (SEED-14): appended DEFERRALS corrections to D-LEGAL.1-1 and D-P30.3-COUNSEL.
  - Rows are from `PD/data/round11_plan.csv` and `PD/data/ticket_catalog.csv` (R11-GOV-01, R11-ACT-06, R11-ACT-07).
- **Sources:**
  - `PD` = `docs/build/planning/2026-09-30-next-phase/`.
  - `PD/feedback/RATIFICATION_LOG.md` rounds 3, 9 and 19.
  - `PD/feedback/OPERATOR_FEEDBACK.md` U-013.
  - `PD/data/decision_catalog.csv` rows Q-7, Q-E2-10 and OD-12.
  - `PD/design/E2-governance-options.md` §0.1 (H-6, H-8) and E2-05.
  - `PD/research/E1-contradictions.md` E1-05.
  - `PD/reviews/S4-truth-safety.md` TS-09.
  - `PD/NEXT_PHASE_PLAN.md` §3.3 (OM-08), §5.10, §7.
- **Relationship to landed ADRs:** this ADR **qualifies ADR-086 and ADR-106**. SEED-11d appends their
  `Qualified by ADR-167` status lines (PLAN §7). Their bodies are not edited. This ADR supersedes, amends and extends
  nothing. Related ADRs:
  - ADR-085, the derived-facts basis.
  - ADR-169, the rights basis with guardrails.
  - ADR-170, the ODbL map basis recorded as the operator's own determination.
  - ADR-182, the counsel-review clauses waived (WV-07).
  - ADR-147, gate-record integrity, which also cites C-3.
  - ADR-152, confidence without independent review.
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). The record text is
  agent-drafted. It records the operator's decisions and statements as logged.

## Context

**What the spec asks for.** SIG-LIC-009 requires that four residual questions be referred to counsel before launch:

- ODbL 4.4(b);
- OSM boundary contamination;
- the regional-cut unit;
- the EU database right.

HG-02 and GL-GATE-02 asked for a counsel opinion recorded "in every artifact". GL-GATE-02 has the artifact label
*"operator/engineering disposition pending counsel; counsel review recommended before real public exposure."*

**What the record says.** E1-05 and E2-05 found that no counsel-authored document exists. "Counsel" nevertheless
appears in the records as follows:

- **2026-09-15.** Five held sources were recorded *"APPROVED by counsel (operator-reported)"* (LEDGER entry quoted in
  E1-05). The registry still carries `rights_reviewed_by = "counsel (HG-02)"` on those 5 rows (re-counted at writing).
  Registry notes elsewhere read "counsel approved ingestion" and "HG-02 resolved 2026-09-16 (counsel, ADR-086)".
- **2026-09-16.** ADR-086's body says *"On 2026-09-16 counsel resolved HG-02"*. That is the `derived_facts`
  compartment for the eleven `LicenseRef-DerivedFacts-Citations` sources.
- **2026-09-16.** D-LEGAL.1-1 was closed on *"operator-adopted drafted analyses (NOT counsel)"*. The analyses are in
  `docs/governance/publication-opinion-drafts.md`.
- **2026-09-24.** ADR-106 records the operator's words *"counsel says it's okay and we can publish it all together."*
  It calls the clearance "operator-reported". The share-alike compartments then went public.
- **2026-09-24.** D-P30.3-COUNSEL was closed *"BY OPERATOR ATTESTATION, no written opinion filed"*. The words were
  *"counsel opinion should just be to give us the green light"*, which E1 X-1 reads as instructional words recorded as
  an attestation.
- **Public text.** The governance doc, `api/src/api/terms.py` ("…and, where applicable, to counsel") and site pages
  imply counsel exists. No public artifact carries the GL-GATE-02 label (E1 NEW-3).

**What the operator said** (U-013, received 2026-09-30T21:58:23Z, `PD/feedback/OPERATOR_FEEDBACK.md`; quoted as the
plan quotes it, PLAN §1.1):

> *"\"counsel\" so far is just me …, we don't have counsel and for now we should just err on the side of not blocking
> on counsel decisions."*

RISK-P21-02 already warned that a recorded reviewer role could be mistaken for legal sign-off. S4 TS-09 found that the
plan's own vocabulary ("operator-reported counsel", "clearance") kept the false implication alive. It also found that
public ADR-086 and ADR-106 keep it.

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

**A-4** (round 3, 2026-10-01T04:03:25Z).

- **Question, as logged:** "governance stance: disclosed single-maintainer, no-counsel posture (… counsel records
  re-labelled as operator determinations …)".
- **Operator answer, verbatim:** **Adopt disclosed posture (Recommended)**.
- **sha256:** `8509460b2536605180168be29f10318fbc6122f2b26c582d4f7dd4dd623ce626`.
- **Label:** option label **agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z**.

The A-4 member this ADR records is `PD/data/decision_catalog.csv` Q-E2-10. Its `operator_answer`, verbatim:

> *"a — publication rests on the operator's recorded determinations, labelled on every artifact; past 'counsel' entries
> re-recorded as the operator's own determinations (no counsel); counsel clauses waived (WV-07)"*

**C-3** (round 19, 2026-10-01T04:54:19Z).

- **Question:** the operator's own words for (1) the 2026-09-16/24 "counsel" determinations, (2) the 09-28 deferral of
  the human legs, and (3) robots, as A-5.
- **Options:** *Adopt both sentences (Recommended) · Adopt (1) only · Neither*.
- **Operator answer, verbatim:** **Adopt both sentences (Recommended)**. Its sha256 is
  `6300639a40d90da1c428c311a63bc9fa24ee2df06f4753ef1fd98294e16ca0af`.

The sentence adopted by that selection, verbatim:

> *"The 'counsel' determinations of 2026-09-16 and 09-24 were my own; there was no counsel. My 09-28 message 'let's
> defer all the human review steps and proceed' was my decision to defer the human review legs."*

- **sha256:** `1461ae213fac4749cd26d24d1ca22de1db893686d1b0fdef88cb64c296eca6c6`. It was computed at writing with
  `printf '%s' "<sentence>" | shasum -a 256` and matches S6's value (`PD/design/S6-ratification-applied.md` §5).
- **Label:** **agent-drafted, adopted by the operator at 2026-10-01T04:54:19Z**.
- **How it is dated.** The sentence is recorded as a statement the operator made on 2026-10-01T04:54:19Z. It is never
  recorded as a 2026-09-16, 09-24 or 09-28 statement or decision (PLAN §5.10; TS-19).

This ADR rests on the sentence's first part. The second part, the 09-28 deferral of the human-review legs, is recorded
here only because the adopted text is one sentence and is stored whole. The record of that deferral belongs to
ADR-147 and ADR-152.

### What is decided

1. **Past "counsel" determinations are the operator's own determinations.** Every past determination recorded as made
   by "counsel" is re-recorded as **the operator's own determination (no counsel)** (OM-08). This covers:
   - ADR-086's 2026-09-16 `derived_facts` resolution;
   - ADR-106's 2026-09-24 share-alike publication;
   - the 2026-09-15 registry approvals;
   - D-P30.3-COUNSEL's attestation;
   - every "counsel" reviewer value in the registry.

   *Agent interpretation (labelled):* C-3 names the 09-16 and 09-24 determinations. The 2026-09-15 registry entries are
   covered by U-013, the operator's statement that "counsel" so far was the operator. They are re-recorded on that
   basis, not on C-3.
2. **The fixed vocabulary.** Records and public text say **"the operator's own determination (no counsel)"**. They never
   say "counsel", "counsel-approved", "operator-reported counsel" or "clearance" for these determinations (TS-09). A
   record may say "counsel" only with a reference to a dated document written by counsel; none exists.
3. **ADR-086 and ADR-106 are qualified, not superseded.**
   - Their decisions stand on the operator's own determination: the `derived_facts` compartment, and share-alike
     compartments published separately with attribution.
   - Their statements that "counsel" resolved or cleared anything are to be read as that determination.
   - ADR-170 records ADR-106's ODbL map basis in the same terms.
4. **Corrections are append-only.** Each is a forward fix that cites this ADR. None rewrites history (OM-13):
   - P34.16 corrects the governance doc, the five registry values (to "the operator's own determination (no counsel)")
     and the `PUBLICATION_CHECKLIST` wording.
   - P34.17 corrects the site wording (R1.5).
   - P34.46 corrects the API terms.
   - T4 appends dated corrections to D-LEGAL.1-1 and D-P30.3-COUNSEL.
   - SEED-12 updates the go-live spec's HG-02 and GL-GATE-02 records.

   The R11-GOV-01 catalog scope still reads "operator-reported". This ADR's wording governs (TS-09).
5. **A publication-basis label goes on every public artifact.**
   - **Where it goes:** manifests, `LICENCES.json`, `datapackage.json`, `/methodology/` and the footer (E2 H-6).
   - **What it replaces:** the GL-GATE-02 text, whose "before real public exposure" clause is past.
   - **The text.** PLAN §5.10 pins E2's agent-drafted text. **It has not yet been confirmed by the operator**, so it
     ships only after verbatim confirmation in a copy batch (B-2):

     > *"No lawyer's written opinion has been obtained; nothing here states that this publication has been cleared by
     > counsel."*

     Its sha256 is `f62f9e984c0d6d7b7a6f5065cef480d666a8da59b2a73e15c762dbf347333b4f`.
   - **E2's full draft** (E2-05) begins with one more sentence:

     > *"Published on the maintainer's own rights and publication decisions. No lawyer's written opinion has been
     > obtained; nothing here states that this publication has been cleared by counsel."*

     Its sha256 is `c7e4f78bcd07b99b9a656c2bc4e6e56a19be7fd86b5d2329b2447414348a6e02`. The copy batch decides which form
     ships.
   - **How confirmation is recorded.** The confirmation goes in the copy-batch record, against these sha256 values
     (OM-07). It is not an edit of this ADR. If the confirmed wording changes the meaning, that needs a new ADR.
6. **Counsel is not owed.** WV-07 waived the counsel-review clauses (ADR-182). A future written opinion is optional
   (LATER-05). If one is ever filed, a new ADR records it, and it does not retroactively turn these determinations into
   counsel's.

## Consequences

- **Records stop claiming a clearance that cannot be shown.** E2-05 identified this false claim as the larger
  credibility risk.
- **The exposure is now disclosed.** No qualified legal review exists for publication, robots, the database right or
  ODbL. The publication and rights bases rest on one individual's judgement, and the label says so (not legal advice).
- **Public `main` stays wrong for a while.** It keeps the false governance and "counsel" text until the operator merges
  P34.16. The plan calls that merge sitting (OP-08) a safety item (PLAN §5.10).
- **The old ADRs stay public.** ADR-086's filename and body ("…counsel resolution…") remain in the public repository,
  because landed ADR bodies are never edited. The `Qualified by ADR-167` status line and this ADR carry the correction.
- **TS-19's lint has a target.** A test can fail any record that presents C-3 as a 09-16, 09-24 or 09-28 statement
  (PLAN §5.10, "a G4 lint test").

## Alternatives considered

- **Seek one written counsel opinion first, with a dated fallback** (E2-05 option c, E2's own recommendation). Not
  chosen. It needs outside contact and counsel (U-011, U-013), and the operator chose not to block on counsel.
- **Keep "counsel" wording with an "operator-reported" qualifier** (the S4-era plan wording). Rejected by TS-09 and
  U-013. It still implies that a lawyer exists.
- **Supersede ADR-086 and ADR-106.** Not chosen. Their compartment decisions stand; only their basis wording is
  corrected, which is a qualification (PLAN §7).
- **Rewrite the earlier records in place.** Forbidden (OM-13; SIG-ENG-003).

## Revisit trigger

- **Counsel is obtained**, or a written opinion is filed (LATER-05). A new ADR records the opinion's scope and date.
- **A licensor, OSMF, vendor or agency objects**, or sends a legal demand, touching the bases of ADR-086, ADR-106 or
  ADR-170. ADR-106's own trigger also applies, and so does ADR-166's posture.
- **The operator confirms the label text with a change of meaning** in the copy batch. A new ADR records the label
  that ships.
- **Another record is found** that says "counsel" without a dated counsel document. Correct it forward under this ADR,
  and record the miss in the run ledger of the row that finds it.
