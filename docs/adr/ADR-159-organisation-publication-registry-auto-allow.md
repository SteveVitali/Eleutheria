# ADR-159: Organisation publication — registry auto-allow, a typed "not yet reviewed" state, no operator review queue

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P. A-10 (2026-10-01T04:07:45Z, round 4) chose the rule; B-18 (2026-10-01T04:39:45Z, round 13)
  folded in the legacy organisation keys (D-P32.3-1). The operator's words are recorded verbatim below.
- **Requirement ids:** SIG-TRUST-006, SIG-ONTO-013, SIG-PUB-002, SIG-PUB-008 (persons are never auto-allowed); drafts
  SIG-UI-D21, SIG-UI-D22 and SIG-UI-D24 (K2 §8; adopted by K13 as UXR-A03, numbered by PLAN-11C); SIG-CONF-D13 (L3 CONF-13;
  numbered by SEED-12)
- **Spec:** `docs/2_canonical_design_spec.md` §11.2, §43, §55.2
- **Implemented by:** P34.26 (the ADR-124 allow-disposition row, the `sig-ops` disposition verb, the flagged-organisation
  census), P34.46 (allows applied with the Round-10 schema), P35.29, P35.30, P36.41, P37.22–P37.27 (labels, entity
  pages, overviews), P37.46a/b (the identifier crosswalk intake and the tier 0–1 cascade materializer)
  (`PD/data/round11_plan.csv`)
- **Sources:**
  - `PD` = `docs/build/planning/2026-09-30-next-phase/`.
  - `PD/feedback/RATIFICATION_LOG.md`, rounds 4 and 13.
  - `PD/data/decision_catalog.csv`, rows D-K2-1, G2-ADR124 and D-P32.3-1.
  - `PD/design/K2-graph-and-entities.md` §0, §3.4, §8, §11, §14 (NEW-1).
  - `PD/design/L3-confidence-program.md` CP-10 / CONF-13.
  - `PD/NEXT_PHASE_PLAN.md` §4.2, §7.
- **Relationship to landed ADRs:** **extends ADR-124** (one publication eligibility policy, P32.5). Its appended
  `Extended by ADR-159` status line is SEED-11d's (PLAN §7). Nothing superseded, amended or qualified. Related:
  ADR-122 (conservative organisation identity), ADR-153 (derivation, not identity), ADR-158 (graph exploration),
  ADR-163 (no person is named).
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). This file records
  operator decisions taken at GATE-P; the record text is agent-drafted.

## Context

ADR-124 (P32.5) made one eligibility rule binding on every public consumer.

- **The hold.** An organisation flagged `publication_review_required` stays withheld until a recorded `allow`
  disposition lifts the flag. ADR-124 calls that disposition "the ONLY thing that lifts a pending review flag".
- **Who records it.** ADR-124 expected the operator to record those allows: *"Recording those allows is an operator
  action … not a code change."*

**K2 NEW-1 (S1).** All 969 referenced organisations are review-flagged. Once the P32.5 gate deploys, every
organisation label and **all 42,488 organisation edges** would be withheld. In degree order, 50 reviews would unlock
96.5 % of the edges.

**D-K2-1 asked how the 969 become publishable.** The options were:

- (a) an operator batch review in degree order through the G2 allow tool;
- (b) an ADR rule auto-allowing organisations matched to an authoritative public registry (Census of Governments, SAM
  UEI, Wikidata QID), with the person-name screen always applied and the basis shown;
- (c) the rest withheld with a typed absence.

The recommendation was a + b + c.

**Other constraints.**

- There are no humans on the project besides the operator (U-008).
- SIG-ONTO-013 requires that organisations seen only inside a vendor network listing (an HOA, an apartment complex, a
  small business) carry a review flag routing them through §43.4 before any public exposure, decided "case by case".
- Separately, the legacy `sig.org.name` keys (D-P32.3-1; 1.7–42 h of per-key review) needed a disposition.

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

| line | round time (UTC) | question as presented (summary, log) | operator answer, verbatim | sha256 of the answer text |
|---|---|---|---|---|
| A-10 | 2026-10-01T04:07:45Z (round 4) | how the 969 review-flagged organisations become publishable. Options: *All three (Recommended) · Auto-allow + absence only · Withhold all* | **Auto-allow + absence only** | `36fba6d510c91f49a963d5e62d0e3ff8f3bbdc187b393ec7cb7b5012f9c2704a` |
| B-18 | 2026-10-01T04:39:45Z (round 13) | US 511 + QLD/NSW keys; fold D-P30.2b-1 and D-P32.3-1. Options: *US + AU keys, fold rest (Recommended) · US keys only · No keys* | **US + AU keys, fold rest (Recommended)** | `fac770c7ec457ffd044f52ba8428b00dfd51df27140551e9b52dbaa72462bf70` |

Each answer is an option label the operator selected. Labels: **agent-drafted, adopted by the operator at
2026-10-01T04:07:45Z** (A-10) and **at 2026-10-01T04:39:45Z** (B-18). The sha256 is
`printf '%s' "<answer>" | shasum -a 256`, computed at writing.

The log's labelled agent interpretation of A-10 (round 4): *"no operator review queue; an ADR auto-allows organisations
matched to the Census of Governments, a SAM UEI or a Wikidata QID (person-name screen always runs); every other
organisation shows a typed "not yet reviewed" state; the top-50 allow tool is not built for the operator (it may still
exist as the ADR's mechanism)."*

The decision rows, quoted from `operator_answer`:

- **D-K2-1:** *"b + c (not a) — 'Auto-allow + absence only': registry auto-allow ADR (Census of Governments / SAM UEI /
  Wikidata QID; person-name screen always runs; basis shown) and a typed 'not yet reviewed' state for every other
  organisation; no operator top-50 review"*.
- **G2-ADR124:** *"a — the ADR-124 allow list is D-K2-1's output, i.e. the registry auto-allow set (no operator review
  queue)"*.
- **D-P32.3-1:** *"a — fold into A-10's registry auto-allow ADR + CONF-13 (P37.46); no operator per-key review"*.

### What is decided

1. **The auto-allow rule.** An ADR-124 `allow` disposition may be recorded for an organisation only when all of the
   following hold:
   - **(a) Registry match.** It is matched to an identifier in one of three authoritative public registries: a
     **Census of Governments** government unit, a **SAM Unique Entity ID (UEI)**, or a **Wikidata QID**.
     - A match is an identifier crosswalk with a match record: tier 0–1 of the CONF-13 cascade (P37.46a/b; L3 CP-10).
     - Name similarity is never a match. Name tiers stay "possibly the same" (L3 CP-10; D-K2-7).
   - **(b) Person-name screen.** The screen **always runs**, over the label, the matched registry name and the literal
     party values the label is built from (K2 §3.4). A person-shaped name is never allowed as an organisation
     (SIG-PUB-002; persons are never named, ADR-163).
   - **(c) The rest of ADR-124's conjunction holds.** There is no denying disposition; the organisation is not
     withdrawn or suppressed; it is at sensitivity tier 0; its rights are redistributable through the `rights_decision`
     chain; and the Part VIII screens apply. This ADR adds a basis for `allow`; it removes no condition.
   - **(d) The basis is shown.** The entity page and label state the registry and identifier the publication rests on
     (K2 §3; draft SIG-UI-D22).
2. **The mechanism is ADR-124's, unchanged.**
   - Allows are append-only `publication_disposition` rows carrying `policy_version`, a reason, and an `authority` that
     names this rule and the matched registry identifier.
   - Tooling writes them: the P34.26 disposition verb and census, then P37.46a/b's materializer. No person reviews
     them.
   - The hosted write follows its row's gate:
     - P34.46 is an in-ticket pause.
     - P37.46a/b need GATE-G6's OM-20 list, or an in-ticket go.
3. **Every other organisation is in a typed "not yet reviewed" state.**
   - ADR-124's `pending_publication_review` hold stays on it. Its label, node, entity page, edges and search hits are
     withheld and shown as that typed absence (K2 H-9), never as a guess or a UUID.
   - **There is no operator review queue.** The top-50 degree-ordered review (option a) is not built for the operator
     (OP-14 dropped, PLAN §4.2). In Round 11 an organisation leaves this state only through a registry match recorded
     under item 1.
4. **The allow list is this rule's output** (G2-ADR124 = a).
   - ADR-124 named the "HG-11-approved partner organisations" as the first allows. They are released through this rule,
     like any other organisation.
   - There is no separate hand-kept list.
5. **Legacy organisation keys are folded in** (D-P32.3-1 = a). The legacy `sig.org.name` keys get no per-key operator
   review. They pass through the same crosswalk matching (CONF-13, P37.46a/b) and the same rule.
6. **Registry identifiers come only from permitted sources.**
   - A registry source that is not yet `ingestion_permitted` needs its own HG-03 line, flipped by the operator (OP-26;
     the P37.46a/b gate cell names Census of Governments and Wikidata as examples).
   - Until that flip, no match to that registry is recorded.
   - Agents never flip a source.
7. **SIG-ONTO-013 is not waived.** An organisation seen only inside a vendor network listing, with no external
   identifier, keeps its review flag. Since no review exists in Round 11, it stays unexposed.
   - *Agent interpretation (labelled):* an organisation matched under item 1 carries an external identifier, so it is
     outside ONTO-013's "no external identifier" case. The person-name screen still runs on it.

## Consequences

- **Organisation labels, pages and edges ship for every registry-matched institution.** No operator time is spent
  (A-10 saves the ~1–2 h top-50 review; D-P32.3-1 saves up to ~40 h).
- **Coverage depends on registry coverage.**
  - US governments: Census of Governments.
  - Federal contractors: SAM UEI.
  - Anything with a QID: Wikidata.
  - Agencies, councils and vendors that match none of these stay "not yet reviewed". So do most share-list partners
    (HOAs, businesses) and many non-US bodies (S5-4 kept non-US acquisition, mostly reachable only through Wikidata).
  - *Inference:* part of the U-003.2 graph will read "not yet reviewed" for the whole round.
- **Matching precision is the safety margin.** A wrong identifier crosswalk would publish an organisation under the
  wrong identity. That risk sits with P37.46's match records and ADR-153's derivation rule, and the person-name screen
  is the backstop for individuals. Every allow row names its basis, so each can be audited and withdrawn (ADR-124
  `withdraw`).
- **ADR-124's third revisit trigger** ("operator tooling makes `allow`-recording routine") is engaged in substance,
  because allows become rule-driven.
  - *Agent interpretation:* the `publication_review_required` flag is still needed. It is the hold that keeps every
    unmatched organisation withheld.
  - SEED-11d records the evaluation of fired triggers.
- **Coverage verdicts.** SIG-TRUST-006 is consumed, not bypassed. The ADR-124 allow row becomes an OPEN obligation
  owned by P34.26/P34.46 (Appendix A T4).

## Alternatives considered

- **All three: operator top-50 review + auto-allow + absence** (A-10's recommended option). Not chosen by the operator.
  It would have unlocked about 96.5 % of edges sooner, but it needs operator review time and a review tool built for
  the operator.
- **Withhold all** (A-10 option 3). Not chosen. Organisations, entity pages, network labels and organisation search
  would all ship "pending publication review", and U-003.2 would be largely unmet.
- **Name-based auto-allow** (fuzzy matching to registry names). Rejected. Names are not identity (L3 CP-10; ADR-153),
  and the "possibly the same" tier exists for this reason.
- **Declaring the review flag moot.** Rejected by ADR-124 itself (D-P31.5-2 option B). It would leave no gate for the
  next flagged identity.
- **A separate per-key review of the legacy organisation keys** (D-P32.3-1 option b). Not chosen; folded in.

## Revisit trigger

- **The screen or a match fails.** A registry-matched organisation is found to be a person, a private individual's
  entity, or a wrong match. Withdraw it through ADR-124. Then suspend the rule for that registry until a new ADR
  tightens the match or the screen.
- **Someone proposes adding a registry** to the auto-allow set, for example ORI, GEOID or a non-US register. This needs
  a new ADR. The three registries here are the operator's answer.
- **A second maintainer or reviewer becomes available, or the operator asks for a review queue.** Option (a) can then
  be reconsidered by a new ADR.
- **The "not yet reviewed" share blocks an acceptance journey.** The share is large enough that a journey (P37.64,
  ACC-EXPLORE) cannot pass. Raise it with the operator; do not loosen the rule silently.
- **A named organisation objects** to its publication. Handle it through the correction and withdrawal paths (ADR-124
  `withdraw`) and re-examine the basis.
- **ADR-124 moves to a new version.** If it moves to `publication-eligibility/2`, or its `allow` semantics change,
  re-check this rule against the new conjunction.
