# ADR-134 — One versioned workspace-state contract (`sig.workspace-state/1`) shared by the three investigation islands, bounded navigation everywhere, evidence-bearing network edges, measured per-island budgets (P32.15)

- Date: 2026-10-04
- Status: accepted (engineering; **offline tooling only** — nothing is deployed or published; public exposure stays with GATE-G3)
- Ticket: P32.15 (Round 10 / S4, row 175; requirements SIG-FIND-004, SIG-FIND-005)
- Base: the P32.14 chain tip `devin/p32-14-full-corpus-release-search` (PR #170, stacked on P32.13 / PR #169)

## Context

P32.13/P32.14 gave the public surface release namespaces, specific record
routes and a full-corpus released search — but each of the three opted-in
investigation islands (`/search/`, `/map/`, `/network/`) still owned its own
local state. A query typed in List did not survive a hop to Map; a selected
record could not be deep-linked across views; the map/network focus was
in-memory only; and the static fallbacks could not name the shared state at
all. S4's research requires ONE canonical, versioned, shareable query state
(`release`, query, repeated permitted facets, `collection`, `focus`,
`view`) honoured by all three views and by the equivalent static links —
explicitly **not** a general SPA router and not a second source of truth.

Two further gaps the same ticket closes:

- **Unbounded surfaces.** The map's no-JS tabular equivalent rendered every
  unlocated asset; the network list rendered every hop without a stated
  bound; the graph island had no node/edge cap. S4 requires complete,
  bounded navigation: pagination that provably ends, named denominators, a
  focused record/evidence pane, and a bounded ego network (target ~50
  nodes / ~100 edges) that expands one ring at a time.
- **Undifferentiated edges.** The §12.2 access edges
  (`configured_access`, `observed_use`, `declared_policy`) rendered as
  styled lines but carried no supporting-claim detail, so "configured
  access" could not be told apart from "observed use" at the claim level
  and no edge could cite its evidence.

## Decision

**One pure, versioned URL-state module — `sig.workspace-state/1` in
`web/src/lib/workspace-state.ts` — is the single contract every island and
every view-switch link serializes/parses; a thin React adapter
(`web/src/islands/workspace.ts`) is the only DOM/history-aware piece.**

### 1. The canonical state (`web/src/lib/workspace-state.ts`)

Emits `v` + `view` always; omits every field at its default so links stay
short and stable:

```
v=1&release=p-<sha256>&collection=<c>&collection=<c2>&q=<text>
    &kind=<k>&jurisdiction=<j>&technology=<t>&source=<s>
    &location=any|public-point|no-public-point&focus=<id>&view=<v>&page=<n>
```

- `collection` is REPEATED; absent = all compartments; a bare
  `collection=` (present, no values) is an explicitly-empty "none"
  selection (`collectionSpecified`) — `0 of N compartments` is a real,
  linkable state, never a silent default.
- `focus` names the selected record — a self-describing
  `sig.published-record/1` `record_key` (`<comp>:<type>:<id>`) where it
  resolves, or an island node/asset id where the fixture data uses those.
  `recordRoutes(publication, key)` derives `/r/<pub>/c/<comp>/entity/…`
  routes from the key itself — no id→compartment index needed.
- `location` reuses the P32.14 index vocabulary verbatim — never a second
  filter vocabulary.
- `page` is 1-based and resets on any query/filter change.

Parse is tolerant-with-receipts: an unsupported `v`, unknown `view`,
unknown `location` or unusable `page` each fall back **and** report an
`issues` note the islands render visibly (`data-testid="workspace-issues"`).
Unknown extra parameters are ignored — other surfaces own their own query
strings.

**Focus scoping.** `clearFocusOutOfScope` implements the S4 rule: a
selection that no longer exists in the new scope is dropped **and** the
caller announces it (`role="status"`), never silently. Each island decides
scope for its own view — a `record_key` the map cannot place yields the
honest "not in this view" pane with the released-record link, not a
fabricated point.

**Not carried** (S4 §8): the map viewport (`z`/`lat`/`lon`) stays
transient in memory — an explicit share-view encoding is a separate
decision; no localStorage research history, accounts or analytics.

### 2. The React adapter (`web/src/islands/workspace.ts`)

`useWorkspaceState(view, {release})` parses `location.search` once at
mount (deep links/reloads), mirrors committed state into `history`
(`push` for navigations Back can undo, `replace` for in-flight text),
and re-parses on `popstate` so Back/Forward restores state exactly. It is
the *only* history-aware code — no router, no global store, no second
source of truth; the URL and the static tables remain authoritative.

### 3. The three islands consume the same state

- `SearchIsland` — `q`/`kind`/`jurisdiction`/`location`/`focus`/`page` all
  read from and write to the URL; a query that drops the focused record
  clears it **with the announced "selection cleared" note**.
- `MapIsland` — `focus` centres and names the record (bare asset id or
  `record_key`); an unplaceable/unloadable focus renders the honest "not
  in this view" pane plus the released-record link; the licence-compartment
  checkboxes drive `collection`/`collectionSpecified`, recompute the
  attribution line and show `0 of N` for an explicit empty; tile layers
  follow the selection without dropping the no-basemap/PMTiles contract.
- `NetworkIsland` — `focus` is the ego centre; a focus naming no node
  renders the default centre plus a visible miss note and the released-record
  link where one resolves; the node buttons re-centre via keyboard alone.
- Each island renders the same `List · Map · Connections` view switch the
  static `ViewSwitch.astro` component emits, with the LIVE state in the
  hrefs — the static and island switches never disagree on the contract.

### 4. Bounded navigation (`web/src/lib/network.ts`, `map.ts`, pages)

- `boundedEgoNetwork` caps the island graph at `EGO_NODE_LIMIT = 50` /
  `EGO_EDGE_LIMIT = 100`, counts the true totals, marks `truncated`, and
  the island states the bound ("showing X of N") while expansion stays one
  ring at a time by node selection.
- The map's no-JS tabular equivalent is now *complete but bounded*: the
  located table paginates in `TABLE_PAGE = 100` rows of the full fixture
  list with previous/next links; unlocated records remain reachable as
  bounded `JurisdictionIndicator` rows grouped by jurisdiction — never
  dropped.
- `network.astro`/`map.astro`/`search.astro` emit the `ViewSwitch`, the
  named-denominator lines ("N of M", release id), per-record links to the
  released routes where they exist, and edge supporting claims in the
  no-JS lists.

### 5. Evidence-bearing edges (`exports/src/exports/spine_export.py`, `network.ts`)

`NetworkEdge.evidence: string[] | null` lists the backing claim ids
(additive — the public-surface schema allows it). The export stamps the
representative supporting claim ids on both the materialized-edge and the
shaped-fallback path, so an edge detail can name its claims. The three
access kinds stay distinct end-to-end — `configured_access`, `observed_use`
and `declared_policy` are never merged, and each rendered edge names its
kind, count and claim ids.

### 6. Measured per-island budgets (`island-budgets.json`, `budget.spec.ts`, `lighthouserc.json`, `p32.15-island-budgets.md`)

`web/scripts/measure-island-budgets.mjs` walks each island page's emitted
assets (module entries + transitive chunks + the MapLibre worker +
stylesheets) over the built `dist/` and writes
`docs/build/reports/p32.15-island-budgets.md`. The measured baselines and
their hard ceilings live in `web/tests/e2e/island-budgets.json`; the
Playwright `budget.spec.ts` measures the same assets on the wire (gzip,
incl. the worker) and fails past the ceilings; `lighthouserc.json` gains a
per-island assertMatrix block so the Lighthouse gate enforces the same
ceilings. The zero-JS pages' script-size-0/≤150 KiB contract is unchanged
and still asserted.

## Alternatives considered

- **A shared SPA router / client navigation.** Rejected — the ticket and
  ADR-097 keep the three islands as progressive enhancement over static
  routes; a router would become a second source of truth and break the
  zero-JS baseline.
- **`focus` carrying a view-specific id only.** Rejected — a
  `record_key` is self-describing (`compartment:type:id`), so a deep link
  needs no index lookup and the miss path can still link the released
  record.
- **Encoding empty-compartment as a sentinel value.** Rejected — a bare
  `collection=` is the honest URL encoding of "none selected"; inventing a
  `none` compartment id would collide with real ids and confuse the
  absent=all default.

## Consequences

- Deep link / reload / Back / Forward restore release, query, facets,
  compartment selection and focus across all three views; unlocated and
  unplaceable records stay navigable via the honest panes and the released
  record links.
- The shared contract is a single file both the unit suite and every
  island exercise — no three divergent serializations.
- Islands stay bounded by construction (ego caps, paginated static tables)
  and every bound states its denominator.
- Edges name their claims; the three access kinds stay distinct and
  separately attributed.
- The per-island budgets are *measured* (map ≈ 1.79 MB raw script-family
  incl. the 507 KB worker, ≈ 0.50 MB gzip; network/search ≈ 230 KB raw,
  ≈ 73 KB gzip) with ~10–25% headroom ceilings — a regression fails the
  Playwright wire test and the Lighthouse matrix.
- `collectionSpecified` is the one backward-compatible schema refinement:
  a bare `collection=` is new in `sig.workspace-state/1`; older links
  without it keep the absent=all default.

## Revisit trigger

Revisit when (a) a requirement asks to share the map viewport or any other
transient state — needs an explicit `v=2` encoding decision, never a
silent `z/lat/lon` leak; (b) a fourth investigation view or a cross-view
selection model appears — the contract's `WORKSPACE_VIEWS`/`view` enum
extends deliberately, not by convention; (c) an edge's claim list needs
full pagination or a richer evidence payload — bump the additive field
into its own document; or (d) an island legitimately needs >2× the
measured budget — raise the ceilings only with a fresh measured report and
a named reason, never silently.
