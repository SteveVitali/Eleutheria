# ADR-225 — the `sig.workspace-state/2` registry, "cite this view", and the surface × facet conformance harness (P36.21)

- Date: 2026-10-28
- Status: accepted
- Ticket: P36.21 (UXR-09/UXR-10, manifest row 361 — on `r11/P36.21-workspace-state-cite-this-view-facets`)
- Base: `r11/P36.20-enhancement-kit-behaviour`
- Requirement stamps: SIG-UI-052, SIG-UI-059, SIG-UI-060, SIG-UI-093 (owned);
  SIG-UI-039 / SIG-UI-040 / SIG-ENG-042 (cited); K0 §4.5, K13 §2.5/§C-11,
  J3 §8.1; ADR-155 (page-type posture), ADR-134 (the /1 workspace contract
  this supersedes at the contract layer, never re-decided)
- Supersedes: nothing by amendment (no status line for ADR-155) —
  `sig.workspace-state/2` supersedes the `/1` CONTRACT per ADR-155's
  registered migration posture; this ADR records the implementation
  decisions that posture did not specify. The /1 module
  (`web/src/lib/workspace-state.ts`) stays for the /1 contract's own tests.

## Context

ADR-155 declared `sig.workspace-state/2` the T2 state contract and the
page-type registry already names it; K13's UXR-09/UXR-10 rows own the
parameter registry and the surface × facet conformance harness. The
implementation surface inherited `sig.workspace-state/1`: a hardcoded
parameter list, `view=network` as the explorer's name, no `at=`/facet
registry, no canonicalisation receipts, no "cite this view" minting, and no
uniform rule that an unapplied parameter is always visibly named. The
questions this row owned: where the registry lives, what a `v=1` link means
under `/2`, which rewrites are canonicalisations (each named visibly), how
the minted cite form coexists with `/s/<pub>/` not yet existing, and how a
STATIC document can honour "noindex,follow on parameterised T2 URLs" when a
build emits one head per route.

## Decision

1. **One registry module drives the whole contract.**
   `web/src/lib/workspace-state/registry.ts` is the single parameter table
   (`sig.workspace-state-registry/1`): name, scope (`common`/`map`/`graph`),
   value kind, `repeated`, closed `values`, `canonicalisesTo`, `sinceVersion`
   and the notice `label`. The parser, serialiser (registry emission order,
   defaults omitted — byte-stable round-trips), the surface × facet harness
   (`conformance.ts`), and the cite mint (`cite.ts`) all read that table; a
   parameter absent from it is refused — parsed out, reported in
   `unregistered`, named in `issues`, never re-emitted.

2. **`v=1` links resolve identically.** `sinceVersion: 1` marks the eleven
   parameters a `v=1` link may carry. Under a `v=1` input the parser keeps
   the v1 value semantics exactly — record-type `kind`, view name `network`,
   `location=any`, the first-`get`-wins rule, `collection=`/`collection` as
   the empty set, `page`'s canonical-integer rule — and merely REPORTS
   `/2`-only parameters (they land in `present`, so the conformance notice
   names them) without interpreting their values, which is what the /1
   contract did with extras. Links minted from this row are `v=2` — the
   migration is forward-emitting, never a redirect or a dropped field.

3. **Canonicalisations are parse-time folds with visible receipts.**
   `bbox=w,s,e,n` folds to `at=<z>/<lat>/<lon>` (centre; zoom
   `floor(log2(360/span))` clamped 0–14) and is never re-emitted;
   `kind=site` → `type=record` (K13 §C-11); `US-OK`-shaped codes →
   `iso3166-2:<code>`; `view=network` → `graph`; `location=any` → absent.
   Every fold appends a plain-language receipt to `notes`, rendered with the
   issues so no rewrite is silent. `at=` precision is deterministic and
   published: z≤5 → 1 dp, z≤10 → 2 dp, z≤14 → 3 dp, else 4 dp (§19.4's
   view-layer rounding — never finer than the zoom supports).

4. **`frame` is registered and round-trips; its fold waits for the jkey
   bounds table.** `frame=<jkey>` is framing-only (canonicalises to `at`),
   parsed and re-emitted verbatim; `canonicaliseWorkspaceState` folds it
   only when a `frameBounds` resolver is supplied (the map row owns the
   bounds table). An explicit `at=` always wins over `frame`/`bbox`.

5. **Conformance is a registry sweep, not a per-island convention.**
   `APPLIED_PARAMS[surface]` is the honesty mirror of what each island
   consumes today (search: `release q kind focus view`; map: `release
   collection focus view`; graph: `release focus view`). For every T2
   surface, every registered parameter is either in that applied set or in
   the notice set — the third option (silently dropped) does not exist, and
   the unit sweep asserts the partition covers the whole registry. Scoped
   params (`at`, `hops`, …) on a surface that cannot apply them are named
   by the same notice, never a hidden filter.

6. **"Cite this view" mints `/s/<pub>/<surface>/?v=2&…` — as text, until
   TX-13b.** The minted form is a snapshot route that does not resolve on
   this build, so the affordance shows it as copyable `<code>` with J3 §8.1's
   interim sentence and the page's named no-JS equivalent links — never a
   dead `<a>`. `citeViewHref()` is the single mint; when the snapshot rows
   land, the same string becomes the anchor href.

7. **T2 documents carry `noindex,follow` + the base canonical
   unconditionally, and the sitemap is registry-derived.** A static build
   emits one `<head>` per route — it cannot split parameterised from bare
   T2 URLs — so the directive is unconditional on the T2 document and the
   canonical link names the base surface. The sitemap generator classifies
   each emitted route through the page-type registry and lists T0/T1
   canonical routes only: the indexing surface and the registry can never
   drift apart, and T2's explore surfaces (which carry `noindex,follow`)
   can never leak into the indexable set.

8. **The islands keep their internal view ids; the wire emits registered
   values.** The islands' runtime vocabulary stays `{list, map, network}`
   (the `view-link-network` testids and switch labels are unchanged); the
   boundary translates `network` ↔ the registered `graph` view, and the
   registry's `SURFACE_PATHS` is the single place the graph surface's
   interim `/network/` route is named until GX-09a.

9. **`at=` is parsed and announced, not yet applied.** The map's viewport
   stays transient today (ADR-134's posture — the map state row owns
   writing `at=`); a link carrying `at` is honoured by the parse, folded
   into state, and visibly named unapplied by the conformance notice.

## Consequences

- Every T2 page now emits `noindex,follow` unconditionally. The T2 surfaces
  were never the canonical indexable content (records are) and the sitemap
  is now T0/T1-only by construction, so this narrows nothing a crawler
  could previously rely on; it is the recorded posture for the whole
  parameter space of a stateful route, not per-URL.
- `frame=` round-trips unresolved until the jkey bounds table exists; a
  link naming a frame the map cannot yet resolve stays honest (parsed,
  carried, announced) rather than silently dropped.
- The `/1` contract module remains for the /1 tests and the island-honesty
  sweep (`test_p34_15_island_honesty.py`); the islands and every newly
  minted link speak `/2`.
- The conformance partition (`APPLIED_PARAMS`) is the place a later row
  registers a newly-applied parameter — the unit sweep fails until the
  island and the table agree, so a parameter can never be claimed applied
  without being applied.

## Alternatives considered

- **Per-query-string `noindex` via `X-Robots-Tag` in nginx.** Rejected here —
  the deployment layer is outside this ticket's `web/` scope; the static
  document carries the unconditional directive and the sitemap is the
  indexable set. A later ops row MAY relax the document directive when the
  edge can express the parameter rule; the ADR records the page-type split.
- **Rewriting `view=network` links to `/explore/`.** Rejected — the rename
  is GX-09a's row; `/network/` remains the graph surface's route and the
  registry keeps the indirection in one place.
- **Making `frame` resolve now over a hand-rolled jkey table.** Rejected —
  the bounds table is data the map row owns; inventing fixture bounds here
  would fabricate geometry.
- **Dropping the v1 parser and re-interpreting v1 params under /2
  semantics.** Rejected — `kind` under /1 is record-type, under /2
  entity-type; re-reading would break SIG-UI-093's identical-resolution
  clause.
- **Emitting the cite mint as a live `<a href>` today.** Rejected —
  `/s/<pub>/` does not resolve on this build; a minted link that 404s is a
  dead link, which the honesty posture forbids. The minted form is copyable
  text until TX-13b.

## Revisit trigger

- TX-13b / the snapshot rows land `/s/<pub>/` — the cite affordance's
  interim text is replaced by the snapshot's own citation block and the
  minted form becomes a live link.
- The map-state row teaches the map to apply `at=`/`layers`/`basemap` (or
  the graph row its scoped params) — `APPLIED_PARAMS` moves and the
  conformance sweep's partition with it; a parameter that must remain
  unapplied needs a recorded reason, not silence.
- A jkey→bounds table lands — `canonicaliseWorkspaceState`'s `frameBounds`
  resolver is wired and `frame=` folds to `at=` at parse.
- A new T2 surface or a `view=` value lands — the registry's closed
  `WORKSPACE_SURFACES`/`view` vocabulary and the sitemap's T0/T1 rule move
  together (an ADR-155 amendment path).
- The deployment row gains a query-string-aware `X-Robots-Tag` — the
  unconditional T2 document directive is relaxed to the parameterised set
  per that row's record.
