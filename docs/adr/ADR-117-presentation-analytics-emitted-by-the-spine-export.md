# ADR-117 — Presentation analytics emitted by the spine export (the design's ADR-R9-ANALYTICS)

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.14 (`docs/tickets/P31.14__presentation-analytics-from-export.md`)
  — Round 9 `SURFACE.1`. Closes deferral **D-P27.5-1**; advances (does not close) **D-P30.3-3**
  (its public-surface half is owed to P31.16).
- **Date:** 2026-10-03
- **Related:** ADR-090 (`--from-spine` export), ADR-092 (materialized reads with shaping fallback),
  ADR-101 (the materialized graph as the network surface's source), ADR-106 (share-alike
  compartments publish separately; §6 the DEMO-constant removal), spec §19.4 (coordinate
  reduction), §19.5 (H3 bins), §10.6 (the W ordinal), §32.5 (named denominators — never a total),
  §39.5/§39.5a (the renewal watch and its decision date, SIG-UI-014b), §40 (the map),
  SIG-UI-018/019/022/023/044; deferral **D-P30.3-3** (OPEN — the public half); backlog home
  **BL-056**.

## Context

Since P27.5 the national site's presentation analytics lived in `web/presentation/` — an
**optional, demo-guarded overlay** the fixture-export harness wrote so the export-mode test suite
could exercise the map's density bins, the network's centrality/focus, the watch's tracked
decision point, the per-surface "How we know this" summaries (with their W-tier distribution),
and the research-queue metadata. A real `--from-spine` export emitted none of them: P30.3
(ADR-106 §6) deliberately made those getters read the overlay or show an honest empty state,
and `ops/publish.py` refuses a `web/presentation/` tree in a public build — so a national build
could never reach a DEMO constant, but also showed no density, no centrality, no focus, no
decision point, and `untiered` provenance. D-P27.5-1 had recorded exactly this open question —
*are these analytics export-emitted or presentation-only?*

The spec's answer is the first: the map renders density bins (§40, SIG-UI-019), the network
renders centrality statistics with an ego-focus (SIG-UI-022/023), the recommender ranks for a
tracked decision point (§39.5a), and "How we know this" carries W1–W3 evidence tiers (§15). None
of those are optional decoration — they are surfaces, so the export must emit them like the nine
P27.1 surfaces, with the same licence separation, determinism, named denominators, and
fail-loud reads.

## Decision

1. **The artifact family.** The spine export now emits a new family —
   `web/analytics/<name>.json`, never the demo-guarded `web/presentation/` — for the five
   analytics the surfaces render: `density_bins`, `centrality` (statistics + the focus rule),
   `decision_point`, `provenance` (the three per-surface summaries), `queue_meta`. Every file
   carries the same envelope: `schema` (a `sig/analytics-<name>/1` id), `as_of`, a **named
   denominator** ("2 published observation-level site records with a releasable tier-0 point" —
   never a bare total, §32.5), `is_population_total: false`, and `source_compartments` naming
   the compartments its inputs draw on. Producers are a pure function of one shaped snapshot +
   supplementary reads (`exports/src/exports/analytics.py`); the same `claim_weights` snapshot
   rows feed both the provenance tiers and the centrality source compartments.

2. **Density bins — H3 over tier-0 points only.** `density_bins.json` bins the published sites'
   **tier-0** points into H3 cells at resolution 3 (the coarse national view the map renders at
   ≤ zoom 6, SIG-GEO-011; the `h3` library — `h3-pg` is not on the images). Sites at tier ≥ 1
   (coordinate-reduced per §19.4 before any aggregation) and licence-refused subjects never pad
   a cell, and the denominator says so. Each bin carries `h3`, `jurisdiction`, `deviceCount`,
   and `coverage` — coverage = the number of **distinct named sources** contributing to the cell
   (≥3 high, 2 partial, 1 low) so low coverage is never rendered as low density (SIG-UI-018);
   a cell exists only where a point falls — never a searched-empty claim.

3. **Centrality + focus — degree over the typed access edges.** `centrality.json` computes
   **undirected degree** over the SAME typed access edges (`configured_access`,
   `observed_use`, `declared_policy`) `web/network.json` emits — materialized `relationship`
   edges when present, the compute-on-read shaping envelope as the honest fallback (ADR-092),
   de-duplicated per undirected pair — with the measure named in the file. The focus entity is
   the highest-degree node, ties resolving to the lexically smallest id (deterministic). Each
   statistic carries `er_quality: null` **with the inline disclosure saying why** (SIG-UI-023):
   the typed edge endpoints are spine entities minted by deterministic identity resolution, so
   the figure does not rest on the probabilistic camera-site ER eval — the honest statement,
   never invented precision-recall numbers.

4. **The decision point — derived, not stored.** `decision_point.json` derives the single tracked
   decision the recommender ranks for as the earliest derivable `next_decision_date` across the
   renewal watch, using the identical rule the web renders (`resolveTermination`/
   `nextDecisionDate`, SIG-UI-014b: expiry − notice window for an auto-renewing contract, else
   the expiry itself; never a stored field that could drift from the dossier's derivation).
   `null` when no watch item carries a derivable date — the honest "none tracked", never a
   fabricated urgency.

5. **Provenance + queue metadata — the real §10.6 tiers.** `provenance.json` carries the three
   per-surface `ProvenanceSummary` blocks the pages render (site / corrections / research_queue).
   The site tier distribution is computed over the publishable claims with
   `reconcile.weight.weight_class` — the §10.6 ordinal table (R base, D/I/C downgrades, D6
   excluded, C derived per predicate half-life at `as_of`, §28.3) — never an invented score.
   A claim that cannot be honestly weighted (D6, a missing axis, an unknown predicate registry
   row) counts as `untiered`, never silently assigned a weight. `human_review_status` is
   `partially_reviewed` only when the camera-site review materialization recorded verdicts.
   `queue_meta.json` carries `queue_as_of` + `jurisdiction_claims` — `[]` on the current spine,
   whose denominator names the honest gap: jurisdiction claims are community-curation state the
   claim spine does not carry.

6. **Licence separation — labelled like `web/map.json`.** Each analytics file is labelled with
   the `AND` of the licences its inputs draw on, the same way the map surface is labelled
   (ADR-106): a SIG-derivable CC-BY file lands in `web`; any other label — a single ODbL label
   or a compound `A AND B` — files in `web_mixed`, an unregistered (restricted) partition, a
   *build input of the produced-work website*, never a public download. `assert_separated` is
   re-proven over the emitted set (`assert_analytics_separated`): one licence label per
   compartment, two labels in one compartment refused loudly. The rendered site reads the raw
   export before partitioning, so a restricted analytic still renders; only its downloadable
   byte stays private.

7. **The web seam — fail loud, never demo.** `web/src/lib/data.ts` reads the family through a
   new `readAnalytics` that validates the envelope and **throws on a missing or malformed
   artifact** — the same fail-loud posture as the nine P27.1 surface getters — so no DEMO
   constant and no silent empty state can reach an export build. Fixtures mode still serves the
   committed constants; the fixture-export harness emits the same envelopes under
   `web/analytics/`. The one remaining `web/presentation/` read is
   `jurisdiction_dossiers` — the deliberately-demo SIG-PUB-017 dossiers — and `ops/publish.py`
   continues to refuse the whole `web/presentation/` tree in a public build.

## Consequences

- A `--from-spine` export now emits every presentation analytic the national surfaces render;
  P31.16's re-export + republish + public-surface verification is the remaining half of
  D-P30.3-3 (the honest-empty-state pages stop being empty on a populated spine).
- The map's national density view is honest: coverage ≠ density, tier-0 only,
  coordinate-reduced, H3-binned at a coarse national resolution. Zoom-aware/finer binning is
  P31.15 tile work.
- `h3` is a new exports dependency (`pyproject.toml`, `uv.lock`, `pylock.toml`).
- `CentralityStatistic.er_quality` widens to `ErQuality | null`; `assertErDisclosures` still
  requires the inline disclosure — a null `er_quality` is admissible only with the statement
  that the measure does not rest on a probabilistic ER eval.
- An analytics artifact missing from an export bundle fails the web build loudly (exit 1),
  proven by unit tests; a removed file can never degrade to demo or empty output.

## Alternatives considered

- **Keep `web/presentation/` and have the export write it.** Rejected: the name is the demo
  guard P30.3 erected — a real analytic must never share a directory the publish guard refuses;
  a new family makes the provenance of every byte unambiguous.
- **Compute the analytics at build time in the web layer** (data.ts deriving bins/centrality
  from the surface JSONs). Rejected: the ticket resolves D-P27.5-1 as *export-emitted* —
  presentation-side derivation would re-create exactly the non-deterministic, licence-blind
  compute-on-read the compartments exist to gate; the web layer stays a renderer.
- **Publish a mixed-licence analytic anyway** (single public file). Rejected: a compound SPDX
  label cannot sit in a registered single-licence compartment — ODbL is never merged with
  CC-BY (4.4(a)); the rendered produced-work site shows the analytic while the byte stays
  restricted, the same posture `web/map.json` already takes.
- **A W-tier count stored on claims.** Rejected: `C` (and therefore `W`) is deliberately
  *derived* (SIG-EPIS-020, §28.3) — storing it would freeze a belief the ordinal composition
  must recompute at `as_of`; the producer derives it per predicate half-life like the
  reconciler does.

## Revisit trigger

Revisit when any of: (a) P31.16 re-exports and republishes — verify the national bundle renders
every analytic on the live surfaces and re-close D-P30.3-3's public half; (b) the map gains
zoom-dependent density (P31.15) — the res-3 national bins need zoom-tier companions or a
vector-tile source rather than a second JSON; (c) a second centrality measure is needed
(betweenness/PageRank over the typed edges) — add a `statistics` metric, not a new file shape;
(d) the spine gains a real `contract_watch` table — `decision_point` should read it without a
fallback and its denominator must count it; (e) a licence regime with no registered compartment
feeds a bin — `_compartments_for_licences` names it but places nothing; decide whether the file
needs a per-licence split; (f) the §10.6 table or the predicate registry's half-lives change —
the provenance distribution recomputes, and stale pinned test counts must be re-derived.
