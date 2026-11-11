# ADR-243 — `<sig-activate>`: the sixth kit element and the dossier's deferred K1 mount (P37.29)

- Date: 2026-11-10
- Status: accepted
- Ticket: P37.29 (K6 VIZ-04, manifest row 453 — on `r11/P37.29-in-place-map-on-dossiers`)
- Base: `r11/P37.28-dossier-network-figures`
- Requirement stamps: SIG-UI-127 (the owned row — no T2 preload; reserved-box
  reuse; the static figure kept for print; no browser history; `/map/`
  hand-offs), SIG-UI-130 (print keeps the figure — no control or canvas may
  print), SIG-UI-132 (the activated box draws the figure's own records —
  figure/map reconcile), SIG-UI-036/050/091 (cited — the enhancement
  contract), ADR-224 (the element-roster revisit trigger this ADR records),
  ADR-155/ADR-223 (cited — the page-type + CSP posture is unchanged)
- Supersedes: nothing

This ADR records the named revisit trigger ADR-224 authored ("a sixth
element roster lands — its own ADR records its admission") and the owned
decisions the in-place mount needed; the governing contracts (page types,
budgets, the T2 set, the workspace-state contract) are deliberately
unchanged.

## Context

K6 VIZ-04 admits the in-place Figure-1 activation on dossiers: on an
explicit reader action — a desktop pointer+width match only — the static
dossier map's reserved box upgrades into the existing K1 map app in
embedded mode. The open design questions were: (a) how a T1 page mounts T2
code without ever becoming a T2 surface or preloading it (SIG-UI-127),
(b) which bytes the activation may spend (the dossier is T1-budgeted, the
app is T2-map-sized), and (c) how the embedded mount honours "no workspace
URL writes" when the K1 workspace adapter's whole job is URL state.

## Decision

1. **The admission is the element, not the island.** `<sig-activate>`
   (`src/elements/sig-activate.ts` → `/_kit/sig-activate.js`, the sixth
   roster entry in `t1-module-entries.json`) is a ≈1.5 KiB framework-free
   custom element admitted page-locally beside the figure markup it
   upgrades — ADR-224's own mechanism, no new policy. It upgrades the
   complete zero-JS anchor (`<a class="sig-activate" href="/map/?v=2&…">`)
   to `<button aria-controls aria-expanded>` ONLY where
   `matchMedia("(min-width: 64rem) and (pointer: fine)")` matches; on
   touch/mobile the anchor navigates — the activation can never exist
   where K6 forbids it. Every injected node is `[data-enhancement]` (the
   SIG-UI-091 parity sweep subtracts it).
2. **T2 bytes are deferred, shared, and post-action only.** The K1 app is
   never a `<script>` on a dossier. `MapIsland` carries
   `loadDossierEmbed = () => import("./map/dossier-embed")`, which makes
   Vite emit `/_astro/dossier-embed.<hash>.js` — a lazy chunk that shares
   every common module (Preact, MapApp, the model, workspace-state) with
   the `/map/` island verbatim: the "same hashed chunks /map/ uses" K6
   §5.4 requires, HTTP-cached across pages. The `sigEnhancementKit` build
   hook resolves the emitted filename and writes the stable shim
   `/_kit/sig-map-embed.js` (`export * from "../_astro/<chunk>"`) plus the
   deferred stylesheet `/_kit/sig-map-embed.css` (MapLibre controls + the
   shared island chrome); `<sig-activate>` `import()`s the shim and
   link-injects the stylesheet only after the click. A mismatch in the
   chunk scan (zero or two hits) is a loud build failure, never a guessed
   module. The MapLibre renderer is still never bundled —
   `loadMaplibre(vendorBase)` reads the self-hosted `/map/vendor/` split
   at runtime, the same files the T2 surface reads.
3. **Per-dossier props travel as a fetched document, not inline state.**
   `/dossier/<slug>/map-embed.json` (schema `sig.dossier-map-embed/1`,
   emitted for exactly the dossiers whose Figure-1 drew located records)
   serialises the same `MapAppProps` contract `/map/` hands its island —
   the one-resolution rule — plus `embedded` context (`jkey`,
   `placeLabel`, `publicationId`, `fallbackAt`). The fixtures-mode
   `records` payload is the dossier's subtree-resolved sites rows (the
   figure's own scope — a parent dossier's payload includes its
   descendants' records, an unkeyed flat dossier's the rows its assets
   name), so the activated box draws the records the static figure counts
   (SIG-UI-132); the tile path carries the compartment archives + dict
   instead. The document is the post-action data the element fetches —
   no records JSON ever inflates a T1 document.
4. **Embedded mode is a prop, not a fork.** `MapApp` gains
   `embedded?: { jkey, placeLabel, publicationId, fallbackAt, onClose,
   onFailed }`. In embedded mode it renders the K6 §5.4 subset — no
   view-switch nav, no place search, no "My location"; the cooperative
   gestures flag; a filters row (technology · status · source — the
   records path's source facet filters over the record's contributing-
   source labels, `recordPasses`); the In-view list and selection panel
   below the canvas; the heading the focus lands on; and the three
   controls: "Open full map" (mints `/map/?v=2&…` from the live state,
   carrying the dossier's `jurisdiction=` facet), "Cite this view" (the
   `/s/<pub>/map/?v=2&…` snapshot, or the honest unbound note), and
   "Close interactive map". The mount overlays the figure's own reserved
   box; the SVG stays in the DOM (aria-hidden after the first drawn
   render) — it is the print rendition and the no-JS one.
5. **State lives in memory; the dossier's address bar is untouched.**
   `useMapWorkspace` gains `url: false`: the embedded adapter never reads
   `location.search` (a dossier URL carries no workspace params, so no
   phantom unapplied-facet receipts), never calls
   `pushState`/`replaceState`, and attaches no `popstate` listener. The
   seed is `frame=<jkey>` — the registry-bbox fold — never
   `jurisdiction=` as a *filter*: the payload already IS the scope, so no
   facet can hide a record the figure drew. An unkeyed dossier frames
   through the payload-bounds `fallbackAt`.
6. **The activated box is a T2-map box for budgets.** The page-type row
   is unchanged (the dossier stays T1 — the element itself is the only
   T1-budgeted code, well inside the 20 KiB T1 row). The post-click fetch
   is the K1 app's first load, so `budget.spec.ts` measures the
   activation leg against `t2Surfaces.map`'s `jsInitialBytes` and
   `firstViewMaxBytes` (the `map-embed` interaction's `budget: "map"`),
   never the T1 post-action ceilings and never an invented new ceiling.
   Activation latency is measured and attached, not gated — K6's ≤ 200 ms
   bound is the in-app selection→panel latency, not the mount.
7. **Failure is loud and leaves the figure.** A failed module import,
   props fetch, mount, WebGL init or runtime `data-failed` latch unmounts
   the app, restores the static figure, re-collapses the button and shows
   the batch-bound notice (SA-02: "The interactive map could not load;
   the figure and the places table show the same records.") — the honest
   equivalent, never a blank box. "Close interactive map" returns focus
   to the activation button.

## Consequences

- **The T2 set is unchanged.** Dossiers remain T1; `/map/`, `/explore/`,
  `/search/` remain the only T2 surfaces. The activated box is a
  progressive enhancement measured as a T2-map box, not a fourth T2
  surface — no ADR-155 amendment was needed because no route type, budget
  ceiling or surface name changed.
- **ADR-224's roster is now six.** `t1-module-entries.json` records
  `/_kit/sig-activate.js` verbatim; the `sig-map-embed.js` shim is a
  runtime-only re-export, never a module entry (no `<script>` names it).
- **Fixture-mode honesty.** The flat `oklahoma-city` dossier's records
  resolve to the keyed descendant dossier in the sites model, so its
  props payload is empty — the activated box shows the honest empty
  in-view while the static figure remains the complete equivalent. On the
  export path (tile archives) the dict + compartment sources carry every
  in-scope record and this fixture asymmetry does not exist.
- **The deferred chunk is a new published route for bytes, not for
  markup.** No link, script tag or preload names `/_kit/sig-map-embed.*`
  — the link-integrity sweep cannot flag it and it is fetched only by the
  element's post-click `import()`.

## Revisit trigger

A second element that mounts a lazy shared chunk needs the seam
generalised (the hook's chunk-name scan is `dossier-embed`-specific); a
dossier-scale where the subtree records payload threatens the
`firstViewMaxBytes` bound moves the payload to tile-only or a paged
form; touch-device activation of any kind is a new ADR, never this
one's relaxation; and if the K1 app gains a second embed context, the
`embedded` prop becomes a discriminated union.
