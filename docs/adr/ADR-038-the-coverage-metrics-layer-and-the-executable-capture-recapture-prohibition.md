# ADR-038: The coverage-metrics layer, its home in `inference`, and the executable capture–recapture prohibition

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P09.1
- **Requirement ids:** SIG-METRIC-001, SIG-METRIC-002, SIG-METRIC-002a, SIG-METRIC-003, SIG-METRIC-004, SIG-METRIC-005, SIG-METRIC-006, SIG-METRIC-007, SIG-METRIC-008, SIG-METRIC-008a, SIG-METRIC-008b, SIG-METRIC-009, SIG-METRIC-010, SIG-TIME-010, SIG-TIME-011, SIG-TIME-012
- **Spec:** docs/2_canonical_design_spec.md §9.5 (the four epistemic states), §32 (coverage record §32.1, published denominators §32.2, provenance completeness §32.3, freshness §32.4, completeness estimation and the capture–recapture prohibition §32.5)

## Context

P09.1 makes negative space queryable rather than editorial (§32): the `CoverageRecord`
with `sources_searched[]`, a denominator on every published aggregate, the four
absence kinds rendered distinguishably, freshness computed relative to predicate
volatility, and completeness estimates that either publish their violated assumptions
or are omitted — with capture–recapture prohibited outright. Several structural
questions had to be settled against existing precedent.

1. **Where does the coverage-metrics layer live?** §47 names no dedicated `metrics/`
   package; §32 is described (line 276) as "the derived metrics that summarize"
   the claim spine, and §47 gives `inference/` as the home for "L4 derivations".
2. **One absence model, or a new one?** P02.3 already shipped `db.absence` — the four
   §9.5 states (`AbsenceState`), the state↔`coverage_record.absence_kind` mapping, and
   `render_absence` (SIG-TIME-011/012). The `coverage_record` table
   (`db/deploy/graph_annotations.sql`) already encodes the full §32.1 shape, including
   the `sources_searched` CHECK.
3. **One freshness notion, or a new one?** The resolver already derives currency
   `C1..C4` from predicate volatility + half-life (`reconcile.weight.currency`, §28.3).
4. **How is a MUST NOT (capture–recapture, §32.5) made verifiable?** A prohibition that
   lives only in prose is not gated by CI.

## Decision

1. **Put the coverage-metrics layer in `inference/`** — the §47 home for derived
   metrics — as four focused, pure-Python value-object modules: `inference.coverage`
   (`CoverageRecord` + discovery-probe negatives), `inference.denominators`
   (`PublishedAggregate`, per-jurisdiction coverage, provenance completeness),
   `inference.freshness` (volatility-relative freshness + the per-source surface), and
   `inference.completeness` (the prohibition + the publishable-completeness guardrails).
   `inference` depends on `sig-db` and `sig-reconcile` (workspace) so it reuses the
   existing models rather than forking them.

2. **Reuse and extend `db.absence`; do not re-encode the states.** The runtime
   `CoverageRecord` aligns field-for-field with `graph_annotations.coverage_record`
   and delegates rendering to `db.absence`. `db.absence` gained only the fourth
   coverage kind that was missing a rendering — `not_applicable` — via
   `render_coverage_kind` and an `ABSENCE_KINDS` vocabulary; `AbsenceRendering.state`
   became `AbsenceState | None` because `not_applicable` carries no §9.5 epistemic
   state (it is not a kind of "unknown"). This is additive and back-compat: no
   existing caller reads `.state`, and the three previously-modelled kinds are
   unchanged.

3. **Freshness is currency (§28.3), not absolute days.** `inference.freshness`
   delegates to `reconcile.weight.currency` over the predicate registry's volatility
   class and half-life, so the *same* age yields C1 (fresh) for an IMMUTABLE
   contract date and C4 (historical) for a FAST active count — exactly the §32.4
   example (SIG-METRIC-006). There is no second, divergent staleness threshold.

4. **Make the prohibitions executable refusals.** `capture_recapture_population` and
   `multi_list_log_linear_population` are functions that *always raise*
   `ProhibitedEstimateError` (SIG-METRIC-008/008a) — the ban is a test, not a
   convention. Publishable figures must be a `CompletenessStatement` with one of the
   four §32.5 methods and a **named** denominator; `assert_no_population_total`
   rejects a bare number or a "reality"/"total" denominator (SIG-METRIC-009/010).
   The single legitimate exception — records-derived survey recall (SIG-METRIC-008b) —
   is `RecordsDerivedRecall`, which enforces pre-registration, a window shorter than
   the predicate half-life, and publication as method-recall in a named jurisdiction
   (never extrapolated, never a population total). Likewise
   `assert_denominated` refuses a bare count so "every published aggregate carries a
   denominator" (SIG-METRIC-003) is a type error, not a review-time hope.

5. **Model in pure Python aligned to the DDL; no live Postgres persistence and no HTTP
   here.** This continues the ADR-031/036/037 precedent. Persisting coverage records
   and serving them over the read-API envelope + coverage statement is P14.1; the
   methodology/freshness/coverage web pages are P15.5. This ticket owns the *shapes,
   validation, and rendering* those consumers read.

## Consequences

Negative space is now a set of queryable, denominated, freshness-aware value objects
with a single owner of the `CoverageRecord` shape, the four-kind ↔ §9.5-state mapping,
the published-denominator contract, and the capture–recapture ban. The ban and the
denominator contract are mechanically gated: a bare count, an implied population total,
or an attempted capture–recapture estimate fails a test. Because freshness reuses the
resolver's currency derivation, there is exactly one definition of "stale" in the
system. `db.absence.AbsenceRendering.state` is now `Optional`; this is a widening and
no caller depended on its non-`None`-ness.

## Alternatives considered

- **A new top-level `metrics/` package** (rejected: §47 does not name one, and adding a
  workspace member for §32 alone is heavier than the derived-metrics remit of
  `inference/`; an ADR would be required to deviate from the frozen layout for no gain).
- **Re-encoding the four states inside `inference`** (rejected: `db.absence` already
  owns them and is imported by the records/procurement connectors and registry-ingest;
  a second copy would drift).
- **A capture–recapture function that returns a wide-interval estimate with a caveat**
  (rejected outright: §32.5 says "not with a caveat, not with a wide interval"; the
  estimator's known failure mode is *understating* what SIG exists to document).
- **Persisting coverage records to Postgres now** (rejected: forks the pure-Python
  precedent and pre-empts the P14.1 read-API surface).

## Revisit trigger

Revisit when P14.1 lands the read-API envelope + coverage statement (the `public_view`
/ `as_json` projections are wired to endpoints and the `coverage_record` table is
written for real), when P15.5 renders the methodology/freshness/coverage pages
(the "distinguishable in the **UI**" half of SIG-TIME-012 is exercised in a browser),
or if the §28.3 currency thresholds or the predicate registry's volatility classes
change (freshness follows them). Also revisit if a records-derived recall exercise is
actually run (SIG-METRIC-008b), so its pre-registration and window are checked against
this object.
