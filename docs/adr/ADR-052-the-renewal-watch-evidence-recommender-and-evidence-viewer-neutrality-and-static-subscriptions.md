# ADR-052: The renewal watch, evidence recommender, and evidence viewer — the neutrality guarantee and static per-jurisdiction subscriptions

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P15.4
- **Requirement ids:** SIG-UI-026, SIG-UI-027, SIG-UI-027a, SIG-UI-027b, SIG-UI-027c, SIG-UI-028, SIG-UI-029, SIG-UI-030, SIG-UI-008, SIG-UI-014b, SIG-EVID-009, SIG-EVID-010, SIG-RECON-045
- **Spec:** docs/2_canonical_design_spec.md §§39.5 (procurement and renewal watch), 39.5a (the evidence recommender), 39.6 (the evidence viewer); §29.7 (snapshot-diff), §17.5 (storage tiers)
- **Relates to:** ADR-049 (the no-JS archivable web shell), ADR-050 (the production local dossier — owns the `next_decision_date` derivation this ticket keys on), ADR-051 (the map/network surfaces P15.4 sits beside)

## Context

P15.4 lands the three remaining actionable-timing / evidence-inspection surfaces on
P15.1's epistemic visual language and no-JS/a11y/archivability baseline: the
procurement/renewal **watch** (§39.5), the evidence **recommender** (§39.5a), and the
evidence **viewer** (§39.6). Two tensions shape the design.

1. **Subscriptions in a zero-JS shell.** SIG-UI-027 requires iCal and RSS
   subscriptions by jurisdiction, but ADR-049 makes the shell zero-JS-by-default and
   archivable, with a Lighthouse budget of 0 script bytes on every page. A dynamic
   feed server is neither available (static-first, SIG-UI-036) nor permitted.

2. **The recommender is where SIG could quietly stop being a record.** A ranker for
   "the most useful evidence for an upcoming decision" is one design decision away
   from "the most *persuasive* evidence" — and SIG-UI-027b forbids exactly that. The
   neutrality guarantee is the property that keeps SIG a record rather than an
   advocacy instrument; it must be enforced, not merely intended.

## Decision

1. **Subscriptions are emitted as static files at build time.** `web/src/lib/watch.ts`
   is the single tested source of truth for the iCal (RFC 5545, with §3.1 octet-aware
   line folding) and RSS 2.0 serializers; Astro static endpoints
   (`watch/[jurisdiction].ics.ts`, `watch/[jurisdiction].xml.ts`) emit one feed per
   jurisdiction at build, mirroring the dossier's `.json.ts`. No feed server, no
   client JS. The DTSTAMP is the deterministic as-of date (never wall-clock), so a
   feed is byte-reproducible.

2. **Every alert keys on `next_decision_date`, not the expiry (SIG-UI-014b).** The
   watch does **not** recompute that date — it reuses P15.2's `resolveTermination` /
   `nextDecisionDate` verbatim (the ADR-050 wire contract), so the watch and the
   dossier can never disagree about when a decision falls. An expiry with auto-renewal
   and a notice window has a real deadline of expiry-minus-notice; that is what the
   VEVENT/RSS item is dated on.

3. **The recommender's neutrality is structural (SIG-UI-027b).** The `EvidenceArtifact`
   type carries only the six §39.5a-admissible inputs (directness `D`, currency `C`,
   open-contradiction/open-task flags, artifact type, `capture_status`) and none of the
   forbidden signals; `assertNeutralInputs` rejects any (untyped/JSON) artifact that
   smuggles a `persuasiveness`/`sentiment`/`predicted_vote`/… key in at runtime, from an
   explicit denylist; and the score is a pure function of the six axes with a per-axis
   breakdown the UI shows, so there is no path by which any other signal can enter the
   ranking. A D6 (non-probative) artifact is excluded from the ranking entirely (§10.5).
   Output is exportable as a plain-text citation list with belief-pinned permalinks and
   as-of dates (SIG-UI-027c), emitted at `watch/citations.txt`.

4. **The evidence viewer is pure, colour-free logic + a static page.**
   `web/src/lib/evidence-viewer.ts` resolves the locator to a character span and splits
   the document into before/highlighted/after (SIG-UI-028); `assertClaimView` enforces
   the SIG-UI-028 completeness contract (claim, extraction method + version, review
   status, conflicting claims, capture date + digest, acquisition method, full history)
   at build, so an incomplete view cannot render. Capture diffing is at the
   extracted-field level with both values and both dates (SIG-UI-029, SIG-RECON-045).
   For a `sealed` capture the type forbids document bytes and requires a `sealed_reason`
   (`assertCaptureTier`), and the page renders the metadata-only representation —
   existence, source, date, digest, supported fields — with the explanation of why the
   bytes are withheld (SIG-UI-030, SIG-EVID-009/010).

5. **Contested values carry the persistent marker at every appearance (SIG-UI-008).**
   The shared `ContestedMarker` component / `CONTESTED_MARKER` glyph travels to the
   watch list, the iCal/RSS feed text, the recommender entry, the citation-list export,
   and the conflicting-claims view — not only a detail view.

## Consequences

- The watch, recommender, and viewer ship as archivable zero-JS pages plus static
  feeds/exports; the a11y (axe WCAG 2.2 AA) and perf (0 script bytes, ≤150 KB) gates
  hold on every new page, verified in CI.
- Wiring to the live `/v1` API is a data-source swap, not a component change: the
  fixtures mirror the pipeline's field names (directness `D`, currency `C`,
  `storage_tier`/`capture_status`, extraction method + locator), and the surfaces
  read only those shapes (see RISK-P15-22).
- The neutrality guarantee is testable and enforced: `tests/unit/recommender.test.ts`
  asserts the forbidden inputs are absent from the type, rejected at runtime, and
  never contribute to a score.

## Alternatives considered

- **A dynamic feed/recommender service.** Rejected: it violates static-first
  (SIG-UI-036) and the zero-JS/perf gates, and there is no DB-wired read API yet.
- **Ranking with a learned "usefulness" signal.** Rejected outright: any signal that
  correlates with persuasion forfeits SIG-UI-027b. The ordinal, published,
  six-axis table is the faithful design — it ranks by *evidentiary* usefulness only.

## Revisit trigger

Revisit when the live `/v1` read API gains a DB-wired store: at that point the watch,
recommender, and viewer should read contracts, artifacts, captures, and claim history
from the API instead of the committed fixtures (the shapes already mirror the wire
contract, so this is a data-source swap). Also revisit if a persona study shows the
ordinal six-axis ranking mis-orders evidence in a way that matters — any new input
must be re-checked against the SIG-UI-027b neutrality bar before it is added, and the
denylist extended if a new forbidden signal is identified. Finally, revisit the
static-feed decision if an interactive/dynamic subscription surface is ever desired;
it would attach to the same tested serializers behind an explicit, greppable directive.
