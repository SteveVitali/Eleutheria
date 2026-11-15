# ADR-249 — `<sig-table>` list mode, `param-prefix` namespacing, and the toolbar "Sort by" menu for the T1 rollout (P37.61)

- Date: 2026-11-15
- Status: accepted
- Ticket: P37.61 (R11-K13-ENH-01, manifest row 489 — on `r11/P37.61-t1-table-filter`)
- Base: `r11/P37.60-visual-regression-gallery`
- Requirement stamps: SIG-UI-091 (the owned row — the kit contract), ADR-224
  (element admission + page-local `<script>` admission is unchanged),
  ADR-155/ADR-223 (cited — page types, budgets and the CSP posture are
  unchanged)
- Supersedes: nothing

P37.61 merges the K9 UX9-3e sources-table ideas, K5 DSRC-05's sort and
filter, K4 JUR-04's enhanced index filter and the K7/K8/K11 "enhanced
island" ideas **as T1 kit uses** (C-19/C-20) — `<sig-table>` on
`/sources/**`, the dossier sources explorers, `/dossier/`, `/watch/`,
`/evidence/` and `/research-queue/`. The surfaces named by the ticket are
a mix of real `<table>`s (`SourcesTable`, `dsrc-table`, the
`/sources/[id]` subpage tables) and server-rendered **lists** (`ol`/`ul`
rows: the grouped dossier index, watch items, evidence artifact rows,
queue task and campaign cards). Three owned decisions follow.

## Context

- The enhancement kit's whole premise is that the *same* element upgrades
  *complete* server markup — a second element per surface shape would
  fork the roster ADR-224 froze at six.
- `/sources/` already mounted `<sig-table>` on the licences table with
  the bare params (`q`, `sort`, `dir`, facet dims, `cols`). Adding a
  second mount (the main K9 table) on the same page collides on those
  names; `/research-queue/` mounts task cards beside campaign rows;
  `/sources/<id>/` mounts three tables.
- The K9 sources table's headers already carry interactive GET sort links
  (`aria-sort` honours the pre-rendered sort routes) — the kit's
  P36.20-era header-button upgrade would nest a `<button>` inside an
  `<a>` (an axe `nested-interactive` violation) if applied verbatim.
- Chart brushing stays deferred (C-20); nothing here touches it.

## Decision

1. **One element, two markup shapes — never a second roster entry.**
   `<sig-table>` gains a *list mode*: when the element contains no
   `<table>`, it builds its row model from every top-level `ol`/`ul`
   inside the element (a `ol`/`ul` nested inside a list item stays part
   of that item). Each direct `<li>` is a row whose cells are the
   element-declared `sort` attribute's `data-sort-<key>` values plus a
   trailing full-text cell labelled by `item-label` (default "Item").
   Filtering, multi-facet chips (`data-facet-*`), the licence-aware CSV
   (`data-licence`/`data-compartment`), `hidden` row filtering and URL
   state are byte-identical to table mode — the DOM-free `table-model`
   is unchanged. Sorting surfaces as a toolbar `<details>` "Sort by"
   menu; the status noun switches to "items"; the column chooser stays
   table-only.
2. **`param-prefix` namespaces URL state per mount.** When present, every
   controlled parameter (`q`, `sort`, `dir`, `cols`, each facet dim) is
   read and written as `<prefix><name>` (`src.q`, `iss.sort`,
   `dsrc.publisher-type`, …). Multi-mount pages assign a prefix per mount
   (`src.`/`iss.`/`tgt.`/`rob.`/`cmp.`/`dsrc.`/`ev.`/`rq.`); the
   licences table keeps its bare-param contract from P36.48 (existing
   shared URLs keep working). Decode-side, only prefixed keys are read —
   a fabricated bare param can never steer another mount.
3. **Interactive headers get the toolbar sort menu; `aria-sort` stays
   honest.** When a header cell contains an anchor/control (the server
   sort links), the kit renders its sort affordance as the same toolbar
   "Sort by" menu instead of wrapping the header text in a `<button>` —
   a control never nests inside an anchor. And when no client-side sort
   is active (`state.sort === null`) the element no longer strips
   `aria-sort` — the server-rendered sort state on a pre-rendered sort
   route stays truthful until the reader actually re-sorts.

Markup-side, rows restate their own rendered fields as `data-facet-*` /
`data-sort-*` / `data-licence` — the same vocabulary the GET facet/sort
routes mint (`indexRowFacet`/`indexRowSortValue` are exported from
`dossier-index` for exactly this); a facet that does not exist as a route
is still an honest page-local filter, never a dead link. Where the facet
*value* is an identifier rather than display text (the queue's place
slug carries the GEOID — `usa-ok-oklahoma-city-4064000`), the row may
carry a positional `data-facet-label-<dim>` so the chip shows the human
name the row already renders while the slug stays the URL/filter key —
the K14 NEW-8 no-ungrouped-digits sweep would otherwise read the raw
identifier as page text.

Admission stays page-local (ADR-224): each mount emits
`<script src="/_kit/sig-table.js" type="module">` beside its markup —
usually through the new `KitTable.astro` mount component — and
`t1-module-entries.json` is unchanged in membership (the same six
entries; `recorded_by`/`comment` note the rollout).

## Consequences

- Every named surface gets in-page filter/facet/sort/CSV with zero new
  JavaScript bytes — the rollout rides the one already-budgeted module.
- URL state on multi-mount pages is per-view and shareable; bare params
  on single-mount pages stay short and stable.
- The K9 per-column GET sort routes remain the no-JS path and are
  unchanged; the menu is additive convenience on JS.
- Lists keep their list semantics (an `<ol>`'s numbering follows its DOM
  order — sorting visibly renumbers, which is the honest rendering).

## Revisit trigger

- If a T1 surface needs a column-visibility control in list mode or a
  seventh element shape (e.g. card grids with per-cell fields), revisit
  whether the row model should become a declared `data-cell-*` mapping —
  and whether that belongs in `<sig-table>` at all versus a new roster
  entry (which needs its own ADR under ADR-224's revisit clause).
