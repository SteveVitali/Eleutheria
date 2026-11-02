# ADR-157 — one static figure kit: the geography half (`exports.figures`), Web Mercator, `static-12px@1`, the CSP-safe serializer (P36.27)

- Date: 2026-10-29
- Status: accepted
- Ticket: P36.27 (R11-K13-FIG-01a, manifest row 367 — on
  `r11/P36.27-static-figure-kit-geography`)
- Base: `r11/P36.26-print-v2`
- Requirement stamps: SIG-UI-066 (one static figure kit), SIG-UI-094 (static
  SVG for every visualisation), SIG-UI-123 (dossier at-a-glance map),
  SIG-UI-124 (static-map binning), SIG-UI-131 (figure accessibility),
  SIG-UI-134 (figures leak no data) — owned; SIG-UI-039 / SIG-UI-040 /
  SIG-ENG-042 (cited); K6 §5.1, K13 §7 W1 (C-07), K14 §4 (the figure
  conventions); ADR-223 (the standalone-SVG response policy this renders
  for), ADR-155 (page-type posture the emitting surfaces keep)
- Supersedes: nothing — this records the first owned decision on the shared
  static figure kit (K6 NEW-3); the graph/chart/legend half lands under
  P36.28 (FIG-01b) as an extension of this package, never a second kit.

## Context

The K6 dossier-map spec (§5.1) and K13's W1 wave both call for *one* static
figure kit every build-time map figure shares — the dossier at-a-glance map,
the locator, the index sprite and the no-JS overview — so the
visualisation code cannot fork per surface (K13 C-07, SIG-UI-066). Before
this row every map-figure concern lived in consumer code: the map tile
builder knew H3 binning, the dossier renderer would have owned outlines,
and nothing pinned the projection, the binning rule or the SVG safety
contract to one vocabulary. The questions the row owned: where the kit
lives (a `web/`-adjacent Python package or an `exports/` module), which
projection and fit it uses, how K6's `static-12px@1` rule and the published
-precision ceilings compose, what the emitted SVG may carry, and how the
standalone-download variant styles itself under P36.19's dedicated response
policy.

## Decision

1. **One Python package in the export stage:**
   `exports/src/exports/figures/`. The build-time map figure is an export
   artifact — it rides the release pipeline the dossier and the download
   tree already ride (evidence-first, deterministic, licence-compartmented),
   so the kit lives beside `dossier.py` and `map_tiles.py`, not in `web/`'s
   TypeScript-only boundary (SIG-ENG-010). The input is a plain-data
   `sig.figure-kit-geo/1` document (release stamp, jurisdiction identity,
   outlines, children, records with *published* geometry and tiers only);
   the output is `MapFigureResult` — deterministic SVG bytes plus a
   `sig.figure-geo-meta/1` description (mode, rule, zoom, `cap_actions`,
   `not_drawn`, children table rows, compartments drawn). The `sig-exports
   figure map|locator|sprite` verbs expose it as a plain CLI
   (SIG-ENG-013); a malformed spec or an unmeetable contract refuses, never
   emits silently (SIG-ENG-042).
2. **Web Mercator everywhere; the framing zoom restates scale in the tile
   vocabulary.** `figures/projection.py` projects EPSG:3857 and fits the
   jurisdiction-plus-children bounds into K6's 720×≤520 box with 8 px
   padding, height derived from the fitted aspect (a ceiling, never a
   crop). The *framing zoom* — the number `static-12px@1` reads — is
   `log2(scale_px_per_mercator_metre · MERCATOR_WORLD_M / 512)`: the zoom at
   which a 512-px-tile world reproduces the figure's pixel-per-metre scale,
   the same vocabulary MAP-07's interactive bands speak so the static view
   is never a weaker rendition (K0 I-3). The one documented exception is
   the US country frame (K1's Albers + AK/HI/PR insets) — a composite the
   page composes out of locator-scale frames, never a second projection
   inside the kit.
3. **Douglas–Peucker in view units, with the 1.0-px perimeter floor.**
   `figures/simplify.py` simplifies deterministic D–P *after* the frame
   transform so the same published outline simplifies identically at any
   emitted scale (visvalingam-whyatt was the alternative; D–P is
   documented, stable and cheap — K6's own reading). An outline whose
   view-space perimeter collapses under 1.0 px is not drawn — the K6 V-4
   honesty floor: the figure never renders finer than a pixel.
4. **`static-12px@1` is one rule with a precision ceiling, not a family of
   heuristics.** `figures/binning.py`: draw tier-0 published points when
   the framing zoom is ≥ 10 *and* the drawable count ≤ 1,000; otherwise
   draw H3 areas at the finest published resolution whose average cell
   *diameter* (2·`average_hexagon_edge_length`) still reads ≥ 12 px at the
   figure width — where "finest" is capped per record cohort by the
   published-precision table (tier 0 unconstrained; tier 1 ≈ 1 km, tier 2
   ≈ 5 km, tier 3 never drawn). A published-state map cannot bin a
   request-time grid; it bins release bytes. MAP-07's interactive binning
   keeps the same numerical contract — zoom threshold, count cap, 12-px
   cell floor, precision ceiling — so parity is a rule, not a hope.
5. **The SVG contract is closed: serializer + post-hoc safety check.**
   `figures/serialize.py` emits a fixed element vocabulary through one
   formatter (`%.2f` coordinates, ordered attributes, trailing newline —
   byte-deterministic), refuses banned attributes (`on*`, `style`,
   `data-*`), bans every `href` that is not a fragment or a root-relative
   path, and `assert_svg_safe` re-scans the finished bytes for
   `<script>`, event handlers, `javascript:`/`data:`/external references
   and `data-*` attributes (SIG-UI-134 — no per-area numerals or record ids
   ever reach the bytes; the check:figures metadata lives on the page
   wrapper). Accessible by construction: `role="img"` +
   `aria-labelledby` into `<title>`/`<desc>`; the drill-down links are
   pointer affordances (`aria-hidden`, `tabindex="-1"`) whose accessible
   twin is the places table the metadata emits (SIG-UI-131).
6. **The lexicon is the vocabulary; the standalone file carries the same
   literals.** `figures/lexicon.py` reads `web/src/lib/lexicon.json`
   (`sig.lexicon/1`) as plain JSON — the corroboration fill channel
   (hollow = one source, filled = 2+), the `≠` contested mark, the amber
   provisional dash, the absence hatch — and the class vocabulary is a
   fixed `FIGURE_CLASSES` set the serializer gates on. On-page, the
   `sig-fig-*` classes draw their colour from `web/src/styles/epistemic.css`
   `var(--sig-*)` rules; the standalone download inlines *the same* literal
   values through `figures/tokens.py` — the Python mirror of
   `design-tokens.ts`, drift-pinned byte-equal against `tokens.css` in the
   unit suite — under `@media (prefers-color-scheme: dark)` for the dark
   set. That style block is the one emission P36.19's dedicated policy
   (`default-src 'none'; style-src 'unsafe-inline'`) exists to permit.
7. **Every omission is counted.** `not_drawn` records the four honest
   categories verbatim from K6 V-3: `declared_no_point`,
   `located_elsewhere` (keyed by the jkey the published point actually sits
   in), `conflicting`, `tier3` — emitted in the `<desc>` text and the
   metadata, so a figure always says what it left out (SIG-UI-020).
8. **The size-cap ladder is explicit.** A figure over its declared gzip cap
   retries with child outlines simplified at 1.0 px chord, then at one
   coarser H3 resolution; `cap_actions` records which rung produced the
   emitted bytes, and a figure still over cap fails with `FigureSizeError`
   rather than shipping past its budget (K6 §5.1's ≤30 KiB-gzip inline
   figure rule).

## Consequences

- Every build-time map figure now has one implementation to audit, one
  vocabulary to test, and one serializer to trust — the dossier renderer,
  the locator, the index sprite and the no-JS overview all reduce to
  spec-document → `build_*` → deterministic bytes.
- The interactive layer owes only *parity of numbers* (thresholds, caps,
  ceilings), not code — two implementations, one contract, checked by the
  shared constants.
- The figure kit never sees finer-than-published geometry: the exporter
  hands it the already tier-transformed coordinate, so the privacy posture
  is structural, not a lint.
- P36.28 (FIG-01b — graphs, charts, legends) extends this package with the
  non-map emitters; it inherits the serializer, the lexicon binding, the
  token mirror and the standalone wrapper rather than forking them.

## Alternatives considered

- **A `web/` TypeScript kit.** Rejected: SIG-ENG-010 confines TypeScript to
  `web/` and the export pipeline is Python; the figure is a release
  artifact — build it where the release is built. The web side owns the
  *page* concerns (the `.sig-fig-*` stylesheet rules, the wrapper chrome),
  not geometry.
- **Turf/EPSG-native geography in web.** Rejected for the same reason plus
  determinism: the kit must run inside `sig-exports`, and a JS geometry
  dependency would fork the vocabulary.
- **Visvalingam–Whyatt simplification.** Rejected (K6's own note): D–P is
  the documented, stable, cheap choice; the quality difference does not
  justify a second algorithm at this scale.
- **Per-record `<title>` tooltips.** Rejected outright — SIG-UI-134:
  per-area numerals and per-record ids are exactly the leak the figure
  contract forbids; counts and the table twin carry the information.

## Revisit trigger

- **P36.28 (FIG-01b) lands** — if the chart/legend emitters cannot share
  the serializer, the lexicon binding or the token mirror without
  weakening a rule, the split is re-recorded here or in a superseding ADR.
- **MAP-07's interactive binning lands** — the shared numerical contract
  (`DENSITY_LEVELS`/thresholds, count cap, precision ceiling) is asserted
  in one place; any divergence is a bug to fix, or this decision is
  revisited with the reason.
- **K1's `coverage_by_jurisdiction` rule lands (D-K1-4)** — the
  `rule_pending` child coverage state resolves to real `covered`/
  `not_covered` values and the interim class disappears.
- **A figure needs a non-Mercator projection** — a national-inset
  composition that cannot be page-composed, or a polar/extent frame the
  Mercator bound cannot hold, reopens decision 2.
- **The published-precision vocabulary changes** — a new tier, or a
  per-record precision finer than the table's floors, moves the res-cap
  table and the tier guards with it (new ADR for the semantic change).
- **The standalone policy changes** — if P36.19's dedicated response row
  tightens or loosens `style-src`, the standalone wrapper's one permitted
  relaxation is re-examined against it.
