# ADR-054: The contributor system — five write tiers, L0 entry, revert-as-new-assertion, and poisoning resistance

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P16.1
- **Requirement ids:** SIG-CONTRIB-001, SIG-CONTRIB-002, SIG-CONTRIB-003, SIG-CONTRIB-004, SIG-CONTRIB-005, SIG-CONTRIB-006, SIG-CONTRIB-009, SIG-CONTRIB-010, SIG-CONTRIB-011, SIG-CONTRIB-011a, SIG-CONTRIB-011b, SIG-CONTRIB-011c
- **Spec:** docs/2_canonical_design_spec.md §34.1 (tiers), §34.2 (onboarding), §34.3 (safety), §34.4 (vandalism and poisoning resistance); §16.6 (corrections as new assertions — the revert mechanism)
- **Relates to:** ADR-002 (the append-only claim table the revert rides on), ADR-039 (the research-task engine this extends), ADR-046/the governance primitives (`policy.governance.BeliefLog`, the in-memory append-only model this mirrors), the contributor-safety governance policy (§34.3)

## Context

P16.1 builds the contributor system end to end: the five write tiers, onboarding,
safety, and vandalism/poisoning resistance. It sits in the `tasks` package (Part
VI: research coordination, contributors, contribution-back). Four forces shape the
design.

1. **The engine is modelled in memory, ahead of persistence.** Every prior `tasks`
   surface (`ResearchTask`, `TaskPool`, the disposition bridge) and the governance
   primitives (`policy.governance.BeliefLog`) are pure, tested Python that mirror
   the SQL shape they will later persist to. The contributor system follows the
   same pattern: it owns the *rules* and their tests; DB wiring to the
   `research_task` table and the claim spine is downstream.

2. **The revert is a claim-spine operation, not a new concept.** §34.4's
   "revertible as a unit, recorded as a new assertion (never a deletion)" is
   exactly §16.6's correction mechanism applied to a *contribution* (a group of
   claims): close each open claim's `sys_period` and append a claim with
   `retraction_of` set. The claim table already carries `retraction_of`; no schema
   change is needed.

3. **The threat is inflationary, not honest error (R12-F12.28).** The live failure
   mode is panic-driven or adversarial *over*-reporting — fabricated nodes
   attributed to vendors in countries where they do not operate. A data-quality
   model that assumes good faith will not catch it, and false *absence* is as
   damaging as false presence while looking like helpfulness.

4. **Safety is achieved by not collecting (SIG-CONTRIB-005).** "What is not stored
   cannot be subpoenaed" is a design requirement. The model must be structurally
   unable to hold a contributor real name, device id, or precise contributor
   geolocation, and must expire transient operational identifiers.

## Decision

1. **Five tiers as a cumulative write model (SIG-CONTRIB-001).**
   `tasks.contributor` declares the exact five tiers (`ContributorTier`), each
   tier's *added* `WriteScope` set and `ReviewRequirement`, and derives the
   cumulative scope up the ladder. `may_create_person` is `PERSON_CREATION ∈
   scopes(tier)` — true only for Curator and Maintainer, encoding "no tier below
   Curator may create a `Person`" (§34.1 Notes; §11.3/§43.4 enforce the substance
   upstream).

2. **Submissions enter at L0; no claim without provenance (SIG-CONTRIB-002).** The
   entry level is a constant `SUBMISSION_ENTRY_LEVEL = L0`; `tasks.submission.submit`
   returns an `SubmissionReceipt` that is L0 with `produces_l1_claim=False` and has
   no code path to write an L1 claim. `assert_has_provenance` refuses an empty
   provenance for any tier. Device observations are routed to OSM/DeFlock
   (`route_device_observation`), not captured (SIG-CONTRIB-004).

3. **Pseudonymity is structural (SIG-CONTRIB-006).** `Contributor` is keyed by a
   pseudonymous `handle` and has **no real-name field**, so a legal-identity
   requirement is unrepresentable; `supports_pseudonymous` is true for every tier
   including trusted-reviewer.

4. **Data minimisation is structural (SIG-CONTRIB-005).** `SubmissionRecord`
   retains only the observation's own location (never the contributor's) and a
   pseudonymous handle; `FORBIDDEN_CONTRIBUTOR_DATA` names the categories a schema
   test asserts are absent. Transient identifiers (IP) live in an `OperationalLog`
   that `purge_expired` empties past a short `PII_MINIMISATION_WINDOW`.

5. **Onboarding is gated by a re-runnable study (SIG-CONTRIB-003).**
   `tasks.onboarding` owns the two intended paths and a `UsabilityStudy` harness
   whose `meets_requirements` checks ≥5 ontology-naïve participants and a median
   ≤10 minutes over the naïve cohort. The as-run study is committed data
   (`data/usability_study.toml`), published in prose at
   `docs/governance/contributor-onboarding-usability-study.md`; re-running the
   study is a data swap that the gate re-checks.

6. **Revert is append-only, over the real spine (SIG-CONTRIB-009).**
   `tasks.revert.ContributionLedger` is the in-memory model — no delete path;
   reverting a contribution closes every open assertion and appends a retraction
   pointing back at it, preserving prior beliefs. `tests/db/test_reverts.py` proves
   the same on live Postgres via `claim.retraction_of` (a novalue claim appended,
   the original only closed, a belief-time query still reproducing the pre-revert
   values).

7. **Poisoning resistance assumes bad faith (SIG-CONTRIB-010/011/011a/011b/011c).**
   `tasks.poisoning` provides: an `AnomalyDetector` whose `RoutingDecision` has no
   `reject` value — bursts, coordinated-similar, and contested-resolving
   submissions can only `route_to_review` — and which never branches on polarity,
   so false-absence campaigns are guarded identically (SIG-CONTRIB-011);
   `check_operating_territory`, which holds a vendor-in-region claim with no
   independent supporting evidence at the lowest confidence and emits a
   verification task instead of an observation (SIG-CONTRIB-011a);
   `apply_reverts_automatically`, a hard refusal so SIG is never the proximate
   cause of a mass revert — only human-reviewed `RevertSuggestion`s are produced
   (SIG-CONTRIB-011b); and a `visual_weight` map placing unverified community
   observations strictly below records-derived claims (SIG-CONTRIB-011c).

## Consequences

- The contributor-tier model, the retention-minimisation posture, and the
  revert-as-new-assertion contract are now executable and tested; P16.2's
  contribution-back can depend on the revert contract.
- Auto-rejection of contributions and SIG-applied mass reverts are *unrepresentable*
  in the API, so a future change cannot regress them by prose alone.
- The onboarding ≤10-minute gate is a deterministic, re-runnable check rather than
  a one-time claim.

## Deviations

- **The system is modelled in memory, not yet persisted.** Consistent with the
  established `tasks`/`policy.governance` pattern; DB wiring (a contributor/submission
  read path and the `retraction_of` revert on the live spine beyond the test) is a
  tracked downstream deliverable, recorded in the risk register.
- **The revert reuses the existing `retraction_of` column** rather than introducing a
  contributor-submission schema; the contribution grouping is modelled in
  `ContributionLedger` and (in the DB test) by the shared origin of a contribution's
  claims. No new migration is added by this ticket.

## Revisit trigger

When the contributor system gains a DB-wired persistence path (a `contributor` /
`submission` store and the live `retraction_of` revert beyond the test fixture),
revisit whether the in-memory models should be thinned to adapters over the store.
Any change to the tier table, the disposition of an anomaly (still never
auto-reject), the PII-minimisation window, or the vendor operating-territory rule
is a spec amendment (SIG-ENG-003), not an edit here.
