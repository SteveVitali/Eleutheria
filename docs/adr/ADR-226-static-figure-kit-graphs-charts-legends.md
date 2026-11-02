# ADR-226 — the static figure kit's graph/chart/legend half: in-repo deterministic layouts, generated legends, table twins (P36.28)

- Date: 2026-10-29
- Status: accepted
- Ticket: P36.28 (R11-K13-FIG-01b, manifest row 368 — on
  `r11/P36.28-static-figure-kit-graphs-charts-legends`)
- Base: `r11/P36.27-static-figure-kit-geography`
- Requirement stamps: SIG-UI-125 (dossier network figure) — owned;
  SIG-UI-061 (the legend lexicon the legends are generated from),
  SIG-UI-066 (the one-kit decision this row completes), SIG-UI-131
  (figure accessibility), SIG-UI-133 (one meaning per symbol),
  SIG-UI-134 (figures leak no data), SIG-UI-039 / SIG-UI-040 /
  SIG-ENG-042 (cited); K6 §6.2/§6.3 (graph caps, honest grouping,
  compound edge paths), K13 §7 W1 (C-07, FIG-01b), K14 §4 (the figure
  conventions, UXK14-8 absorbed); the K5 'chart component' audit
  absorption (DSRC-02's chart component is this package's `chart.py`);
  ADR-157 (the kit this row extends), ADR-223 (the standalone-SVG
  response policy), ADR-155 (page-type posture)
- Extends: ADR-157 — ADR-157 §"the graph/chart/legend half lands under
  P36.28 (FIG-01b) as an extension of this package, never a second kit"
  is discharged here; nothing in ADR-157 is superseded.
- Supersedes: nothing.

## Context

ADR-157 placed the whole build-time figure kit in
`exports/src/exports/figures/` and landed the geography half. This row
lands the other half (K13 W1 FIG-01b): the dossier bipartite network
and the entity radial ego layouts, the bar/strip/stacked-bar/timeline
chart emitters, the generated legend, the table twins, the wide/narrow
variants and the print rules. The questions the row owned:

1. **Which layout engine draws graphs?** K2 §6.3 pins the answer in
   advance: "positions precomputed at build (deterministic seed; a
   BSD-licensed Python layout, **not** the `igraph` package present in
   `pylock.toml`, which is GPL-2.0-or-later)". The ticket restates it:
   a BSD/OSI-compatible overview-layout wrapper; the GPL igraph wheel
   is never a dependency. The sub-question — vendor a BSD package or
   implement the two needed layouts in-repo — was genuinely open: the
   spec names no package.
2. **How do the caps degrade honestly?** K6 §6.2 caps a drawn figure
   (an overview never exceeds its node bound; a dossier network draws
   at most ~20 anchors × ~30 counterparties in the measured shapes).
   Silently pruning nodes would violate the defining standard — a
   figure that drops evidence reads as a figure that has none.
3. **Where does the legend's vocabulary live?** SIG-UI-061 (landed by
   P36.17) already makes `web/src/lib/lexicon.json` the single legend
   lexicon; a legend that invents a term or lists a symbol the figure
   does not use breaks both SIG-UI-131 and SIG-UI-133.
4. **How does a static figure carry its data?** The K0/K14 posture is
   HTML-first with colour never the only channel (SIG-UI-005): every
   visual needs an accessible, machine-readable twin.

## Decision

1. **The layouts are implemented in-repo, in `exports/src/exports/figures/layout.py`,
   with no third-party dependency at all.** The two layouts the
   overview/figure surface needs — the deterministic two-column
   bipartite (anchors left, counterparties right; a narrow variant
   stacks anchors above counterparties) and the deterministic radial
   ego (entity centred, neighbours placed on a circle grouped by
   relation sector) — are small, closed-form placements: ordering is
   fully specified by `(group ordinal, label, id)`, there is no
   iterative solver, no force simulation and no seed to manage, so
   output is byte-identical for identical input *by construction*, not
   by pinning a PRNG. This satisfies K2 §6.3's licence pin strictly:
   the repo's own Apache-2.0 code is OSI-compatible, introduces zero
   new dependency surface for the licence scanner, and `igraph` is
   never imported by the figure kit (asserted in tests). If a later
   surface needs a real overview layout over thousands of nodes (K2
   §6.3's `sig.graph-overview/1`), this ADR's wrapper posture still
   applies — a BSD-licensed package may be adopted then; the wrapper
   boundary (`layout.py` returns plain `pos` dicts) keeps that swap
   local.
2. **Caps degrade by grouping, never by silent pruning — and refuse
   when they cannot group honestly.** `graph_model.py` carries the
   `sig.figure-kit-graph/1` input contract plus the caps
   (`NODE_CAP = 60`, `SIDE_CAP = 20` per column, `EGO_CAP = 20`
   neighbours). A spec may declare `group_by` on a node set; nodes
   sharing a group key collapse into one drawn group node whose label
   and `members` are listed in the table twin and whose edges union the
   members' edges (counts preserved in `GroupedNode.member_ids` and the
   metadata's `group_actions`). Nodes without a `group_by` are drawn
   individually. If the drawn count still exceeds a cap the build
   **refuses** — exit 4, no partial SVG — rather than dropping a node
   (SIG-ENG-042). There is no ranking: grouping keys are declared in
   the spec (a dossier's own notion — `country`, `kind`, …), and
   ordering inside every column/sector is the plain lexical order, so
   no figure can read as "more important".
3. **Legends are generated from `lexicon.json` and list only the
   symbols the figure drew.** `legend.py` takes the encoding tokens a
   builder actually emitted (`fill:singleSource`, `line:configured`,
   `kind:agency`, `marker:contested`, `currency:muted`, `series:<n>`,
   `absence:<state>`), resolves each through the shared lexicon — the
   same binding P36.17's `lexicon.ts`/`check-lexicon.mjs` enforce — and
   returns ordered entries carrying the lexicon's own `interimLegendLine`
   wording, never a hand-written string. A token with no lexicon
   binding fails the build. A figure that draws no contested mark
   lists no contested row. Channel ordering follows the lexicon's
   declared encodings, so the legend order is itself deterministic.
4. **Every figure emits an accessible table twin beside its SVG.** The
   twin ships as the `table_columns`/`table_rows` payload in the
   result's `sig.figure-kit-meta/1` metadata — stable columns, one row
   per drawn element carrying link, label, relation, access kind,
   currency, date and `sources`/`claim_ids` provenance fields — which
   the embedding surface renders as real HTML `<table>` markup (the
   tabular no-JS equivalent ADR-155 already requires), never as an SVG
   picture of a table and never as `data-*` attributes. The SVG itself
   carries `role="img"`, `<title>`, a `<desc>` that names every drawn
   node/edge state, and `aria-labelledby`; per-node links are
   root-relative `<a href="/…">` only — the serializer's CSP contract
   (no `data-*`, no `on*`, no external refs) holds for graphs exactly
   as it held for maps; K6 §6.3's compound-path-per-edge-class rule is
   met by drawing each access-kind class as one `<path>` of joined
   segments.
5. **Wide and narrow variants are two results of one build, and print
   rules keep a figure whole.** `StaticFigureResult` carries `svg` +
   `svg_narrow` (720 px and 360 px viewports; narrow truncates visible
   labels at 14 chars with the full label retained in `<title>`). The
   epistemic stylesheet's `@media print` block forces every `.sig-fig*`
   figure `break-inside: avoid` and swaps fills/strokes to a
   greyscale-safe posture that keeps hatches, dashes and the `≠`
   marker readable — colour is never the only channel (K14 §4).

## Consequences

- The kit is one package still: graph/chart emitters reuse
  `serialize.py`'s closed vocabulary, `lexicon.py`'s binding,
  `tokens.py`'s mirror and `standalone.py`'s one permitted `<style>`
  block — the ADR-157 "never a second kit" clause holds.
- `sig-exports figure` gains `network|ego|chart` verbs and a
  `--out-narrow` flag; `map|locator|sprite` are unchanged.
- The spec-facing inputs are plain-data documents
  (`sig.figure-kit-graph/1`, `sig.figure-kit-chart/1`); no figure reads
  the claim spine, the release tree or `web/`'s TypeScript — the
  release/export boundary is untouched.
- The K5 'chart component' audit absorption (the row's contract) is
  recorded: DSRC-02's charts are this package's `chart.py` emitters —
  bar, strip, stacked-bar and timeline only; any other kind (pie,
  scatter, …) refuses with a named error, so the audited surface is a
  closed vocabulary.
- No new runtime dependency was added; the licence scanner's frozen
  expected-strong-copyleft set is unchanged (`igraph` remains an
  existing declared dev-side wheel, never imported here).

## Revisit trigger

- **A real overview layout lands** — K2 §6.3's `sig.graph-overview/1`
  over thousands of nodes needs an iterative layout; a BSD-licensed
  package adopted for it goes through this ADR's wrapper boundary and a
  new ADR records the dependency.
- **A figure needs a layout these two cannot express** — a DAG, a
  geographic-pin graph or a chord/arc form reopens decision 1.
- **A cap needs a different degradation** — e.g. a spec that can
  honestly *sample* (a documented subset with a stated rule) rather
  than group would amend decision 2; silent pruning stays forbidden.
- **The lexicon gains a channel these emitters cannot express** — a
  new legend channel (a texture family, a second marker) extends
  `legend.py`'s encoding grammar; one-meaning-per-symbol stands.
- **The print posture changes** — a different greyscale rule or a
  split-figures accommodation amends decision 5.
