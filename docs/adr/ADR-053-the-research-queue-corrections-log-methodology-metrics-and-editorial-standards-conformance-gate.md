# ADR-053: The research queue, public corrections log, methodology/metrics pages, and the editorial-standards conformance gate

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P15.5
- **Requirement ids:** SIG-UI-031, SIG-UI-032, SIG-UI-033, SIG-UI-034, SIG-UI-042, SIG-UI-043, SIG-UI-044, SIG-UI-045, SIG-UI-046, SIG-GOV-001…011, SIG-METRIC-006, SIG-METRIC-007, SIG-METRIC-008, SIG-METRIC-009, SIG-METRIC-010, SIG-TASK-008, SIG-TASK-009, SIG-TASK-010, SIG-TASK-011, SIG-TASK-012
- **Spec:** docs/2_canonical_design_spec.md §§39.7 (research queue), 39.8 (corrections, methodology, metrics), 41 (editorial standards); §32.4 (freshness), §32.5 (coverage/no capture–recapture), §33.2/33.4/33.5 (task catalog, dispositions, geographic queues), §45 (corrections, disputes, takedown)
- **Relates to:** ADR-049 (the no-JS archivable web shell + epistemic visual language P15.5 consumes), ADR-050 (the production dossier — the template the hostile-reader review gates), ADR-052 (the P15.4 surfaces P15.5 sits beside), ADR-038 (the coverage-metrics layer + the executable capture–recapture prohibition), the takedown/corrections/suppression governance policy (§45)

## Context

P15.5 lands the last Phase-15 public surfaces on P15.1's epistemic visual language and
no-JS/a11y/archivability baseline: the research **queue** (§39.7), the public
**corrections log** (§39.8) — the required *eighth* surface the outline omits — the
one-click **dispute/correction** submission path (§45), the **methodology**,
**data-freshness** (§32.4), and **coverage-metrics** (§32.5) pages, and the
**editorial-standards conformance gate** (§41). TypeScript is confined to `web/`
(SIG-ENG-010). Four tensions shape the design.

1. **The queue, corrections, freshness, coverage, and dispute channel are all live
   engine/governance concerns — but the shell is static-first (SIG-UI-036).** There is
   no build-time API dependency and no feed/intake server. The surfaces must render the
   real *shapes* from committed fixtures while staying wire-compatible with the live
   `tasks` / governance / metrics data.

2. **Coverage is where SIG could quietly lie by arithmetic.** SIG-METRIC-008/009/010
   forbid a capture–recapture population estimate and any total or completeness
   percentage implying a known denominator of reality. A coverage page is one careless
   division from publishing exactly that.

3. **"How we know this" and the dispute path are per-page invariants (SIG-UI-044,
   SIG-UI-033).** They must appear on *every* page — including every dossier and every
   surface a later ticket adds — without each page re-implementing them.

4. **Editorial conformance must be a gate, not an aspiration.** The register rules
   (SIG-UI-043/046) and the hostile-reader review (SIG-UI-042) are the property that
   keeps generated and hand-written text usable as evidence; "release blocked until
   every finding is dispositioned" has to be *executable*.

## Decision

1. **Each surface is pure, colour-free logic + committed fixtures + a static page.**
   `web/src/lib/research-queue.ts` (task-card view model + geographic filtering +
   claiming-with-expiry + the §33.4 disposition-by-assignee mapping),
   `corrections.ts` (the log entry, the §45.1 intake categories with published
   priority, the one-click `disputeHref`, the transparency report), `metrics.ts`
   (freshness rows + coverage metrics), `provenance.ts` (the "How we know this"
   module), and `editorial.ts` (register rules + conformance checker + the three
   example cases + the hostile-reader review model) carry the logic. Field names mirror
   the engine's controlled vocabularies (`tasks/src/tasks/vocabulary.py`,
   `catalog.py`), so wiring to live data is a source swap, not a component change.

2. **The queue reflects the coordination guarantees structurally.** Dispositions are
   derived from a task's assignee class, so a search task (field/records/analyst/local)
   always carries `resolved_no_evidence_exists` ("searched, found nothing", writes a
   coverage record — the mechanism by which the queue can *shrink*, SIG-TASK-009) and a
   curator/developer clean-up task never does. A claim grants priority in ordering but
   `claimStatusFor` always reports `anyone_may_work: true` (SIG-TASK-011); claims
   expire without renewal (`claimIsActive`); and there is no volume leaderboard
   (SIG-TASK-012).

3. **The coverage prohibitions are executable (SIG-METRIC-009/010).** A `CoverageMetric`
   MUST carry a NAMED denominator and MUST NOT present it as "reality"/"all … that
   exist", and `is_population_total` is typed `false` so a total is unrepresentable;
   `assertCoverageMetric` throws at build otherwise. The four legitimate kinds are
   counted-quantity, records-derived bound, reconciliation ratio, and survey-recall —
   there is no capture–recapture kind (SIG-METRIC-008). Freshness is stated per source
   against a predicate **volatility class**, not absolute days (SIG-METRIC-006).

4. **"How we know this" and the dispute link are rendered by the base layout, so they
   are on every page (SIG-UI-044, SIG-UI-033).** `HowWeKnowThis.astro` renders the six
   required components from a `ProvenanceSummary` and calls `assertProvenanceComplete`
   (a module missing a component fails the build); it also carries the methodology /
   data-freshness / coverage-metrics links, which is how those pages end up **linked
   from every dossier** (SIG-UI-034) structurally rather than per-fixture.
   `DisputeLink.astro` is a plain no-JS GET to `/dispute/`, one click from any claim.

5. **The editorial gate is executable.** `checkRegisterConformance` is a conservative
   denylist of characterizing/motive/editorializing language (the mechanically-checkable
   core of the six rules); it is applied to **generated rationale templates** as well as
   hand-written copy at build (SIG-UI-046), mirroring the ADR-052 recommender-neutrality
   pattern. The three example cases (SIG-UI-045) are the spec's exact conformant copy.
   The hostile-reader review (SIG-UI-042) is data committed alongside the template
   version (`HOSTILE_READER_REVIEW`, keyed to the ruleset version, plus the prose record
   in `docs/governance/hostile-reader-review-dossier.md`); `assertReviewReleasable`
   throws at build unless there are two independent reviewers and every finding is
   dispositioned — so a template version with an open finding cannot render/release.

6. **The seven outline surfaces + the corrections log are asserted to exist across the
   built site** (P15.5 deliverable 6 / AC1) by an e2e manifest (`PHASE15_SURFACES`).

## Consequences

- The eighth surface (corrections) and the two per-page invariants close the outline's
  gaps; every page now carries provenance and a correction path, and every dossier
  links methodology/freshness/coverage without per-dossier wiring.
- All P15.5 pages ship **zero client JS** and stay within the ADR-049 performance
  budget; the WCAG 2.2 AA and OSI-licence gates hold on the new pages (they are added to
  the a11y sweep and auto-globbed by the perf gate).
- The coverage and editorial gates convert two "must not" requirements into build
  failures, so a future contributor cannot regress them by prose alone.

## Deviations

None. Consistent with ADR-049's zero-JS/static-first posture and ADR-038's
capture–recapture prohibition.

## Revisit trigger

When the live `tasks` queue, governance intake, and metrics APIs gain a DB-wired read
path (cf. RISK-P14-07/17), swap the committed fixtures for live reads — the view-model
shapes and the executable gates are unchanged. Any change to the register rules, the
disposition vocabulary, or the coverage-metric kinds is a spec amendment (SIG-ENG-003),
not an edit here.
