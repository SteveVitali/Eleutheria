// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.55 (K6 VIZ-02, SIG-UI-069/123/132): the dossier's map + locator figure
 * contract — the web-side reader of the `sig.dossier-visuals/1` build input
 * P36.54's export emits under `inputs/dossier-visuals/` (a RESTRICTED input —
 * on disk for the Astro build, never published, SIG-UI-134/DV12), plus the
 * `sig.locator-symbols/1` parent-context sheet every locator cites.
 *
 * One dossier's visuals doc carries:
 *   - `map`     — either the `sig.figure-geo-meta/1` metadata + the inline SVG
 *                 the one figure kit rendered, or `{status: "no_boundary"}`
 *                 typed absence (a registry key with no mintable outline);
 *   - `locator` — the place-inside-its-parent geometry (`child_d` + viewbox +
 *                 the parent's symbol id in the shared sheet), or a typed
 *                 `no_parent_context` / `no_boundary_geometry` status;
 *   - `networks`— the network-figure slots, `[]` until VIZ-01b lands the
 *                 content (the slots render typed empty states today).
 *
 * The published metadata twin — `figures[]` on `sig.dossier/2` (id + caption +
 * desc counts + links, NO geometry, K6 §9.2) — is typed here too so the page
 * can caption Figure 1 without touching restricted bytes in the twin itself.
 */

import { existsSync, readFileSync } from "node:fs";
import { dataSource, exportDir } from "./data";
import { DOSSIER_VISUALS_FIXTURE, LOCATOR_SYMBOLS_FIXTURE } from "./dossier-visuals-fixture";
import { assertInlineSvgSafe } from "./entity-figures";

/** The emitted document id (K6 §9.1). */
export const VISUALS_SCHEMA = "sig.dossier-visuals/1";
export const LOCATOR_SYMBOLS_SCHEMA = "sig.locator-symbols/1";
export const FIGURE_GEO_META_SCHEMA = "sig.figure-geo-meta/1";

// ---------------------------------------------------------------------------
// The sig.dossier-visuals/1 shape (restricted build input).
// ---------------------------------------------------------------------------

export interface VisualsRelease {
  label: string;
  publication_id: string | null;
  as_of_world: string;
}

export interface VisualsJurisdiction {
  jkey: string;
  slug_path: string;
  level: string;
  chain: string[];
  name: string;
}

export interface MapNotDrawn {
  declared_no_point: number;
  located_elsewhere: { jkey: string; records: number }[];
  conflicting: number;
  tier3: number;
}

export interface MapChildRow {
  jkey: string;
  coverage: string;
  drawn: boolean;
  href: string | null;
}

export interface MapMeta {
  schema: string;
  viewbox: [number, number];
  zoom: number;
  mode: "points" | "h3-areas" | string;
  h3_res: number | null;
  rule: string;
  cap_actions: string[];
  not_drawn: MapNotDrawn;
  desc: {
    records_drawn: number;
    areas_drawn: number;
    records_total: number;
    jurisdiction: string;
    release: string;
    publication_id: string | null;
  };
  compartments_drawn: string[];
  children: MapChildRow[];
  boundary_vintage: string;
  size_bytes: number;
  gzip_bytes: number;
}

/** A drawn map — the kit's metadata + the inline SVG bytes. */
export interface DrawnMap extends MapMeta {
  svg: string;
}

/** The typed absence — a registry key the pack mints no outline for. */
export interface NoBoundaryMap {
  status: "no_boundary";
  reason: string;
  records_total: number;
}

export type VisualsMap = DrawnMap | NoBoundaryMap;

export interface DrawnLocator {
  parent_symbol: string;
  parent_jkey: string;
  child_d: string;
  viewbox: [number, number];
}

export interface TypedLocator {
  status: "no_parent_context" | "no_boundary_geometry";
  parent_jkey: string | null;
}

export type VisualsLocator = DrawnLocator | TypedLocator;

/** The H-2 relationship-table row the kit's table twin carries verbatim. */
export interface NetworkEdgeRow {
  counterparty: string;
  href: string;
  relation: string;
  direction: string;
  access_kind: string;
  date: string;
  date_kind: string;
  currency: string;
  support: string;
  sources: number;
  evidence: string[];
}

/** One generated legend entry (lexicon-bound — only encodings present). */
export interface NetworkLegendRow {
  id?: string;
  label?: string;
  plain?: string;
  [k: string]: unknown;
}

/** The kit's `sig.figure-graph-meta/1` block a drawn figure carries. */
export interface NetworkFigureMeta {
  schema: string;
  viewbox: [number, number];
  narrow_viewbox: [number, number];
  mode: string;
  cap_actions: string[];
  legend: NetworkLegendRow[];
  table_columns: string[];
  table_rows: NetworkEdgeRow[];
  node_count: number;
  edge_count: number;
  desc: { anchors: number; counterparties: number; edges: number; [k: string]: unknown };
  size_bytes: number;
  gzip_bytes: number;
  [k: string]: unknown;
}

/** An H-4 degree-only fact — a partner COUNT, a sentence, never an edge. */
export interface NetworkDegreeFact {
  count: number | null;
  observed: string | null;
  sources: string[];
  claim_ids: string[];
}

/** A drawn network figure — the kit's wide + narrow SVGs plus metadata. */
export interface DrawnNetworkSlot {
  figure_id: string;
  slot?: string;
  family: string;
  overview: string;
  title: string;
  status: "drawn";
  svg: string;
  svg_narrow: string;
  meta: NetworkFigureMeta;
  anchors_drawn: number;
  counterparties_drawn: number;
  edges_drawn: number;
  cap_actions: string[];
  toggle_kinds: string[];
  table_rows_total: number;
  table_href: string;
  explore_href: string;
  anchor_attrs?: Record<string, string>;
  degree_facts: NetworkDegreeFact[];
  by_source: { source_id: string; value: number }[];
  [k: string]: unknown;
}

/** The typed absence — a figure with no evidenced edge is never drawn
 *  (K6 V-7); the emitted reason is a value, never a blank frame. */
export interface EmptyNetworkSlot {
  figure_id: string;
  slot?: string;
  family: string;
  overview: string;
  title: string;
  status: "country_no_figure" | "no_anchors" | "no_evidenced_edges" | "over_cap" | string;
  reason: string;
  anchors_total: number;
  edges_total: number;
  degree_facts?: NetworkDegreeFact[];
  table_href: string;
  explore_href: string;
  [k: string]: unknown;
}

/** A network-figure slot — drawn or typed-absent (P37.28, K6 VIZ-01b). */
export type NetworkSlot = DrawnNetworkSlot | EmptyNetworkSlot;

/** True when the slot carries a drawn figure (vs the typed absence). */
export function isDrawnNetwork(slot: NetworkSlot | undefined): slot is DrawnNetworkSlot {
  return slot?.status === "drawn" && typeof (slot as DrawnNetworkSlot).svg === "string";
}

export interface DossierVisualsDoc {
  schema: string;
  release: VisualsRelease;
  jurisdiction: VisualsJurisdiction;
  map: VisualsMap;
  locator: VisualsLocator;
  networks: NetworkSlot[];
  timeline_items: number;
}

/** The published `figures[]` twin row on `sig.dossier/2` (no geometry). */
export interface DossierFigureTwin {
  figure_id: string;
  kind: string;
  caption: string | null;
  caption_drafted: string;
  meta: MapMeta | null;
  links: { sites?: string; download?: string | null };
}

// ---------------------------------------------------------------------------
// Readers — fixtures → the committed corpus; export → the restricted input.
// ---------------------------------------------------------------------------

/** True when the map block drew a figure (vs the typed no_boundary absence). */
export function isDrawnMap(map: VisualsMap): map is DrawnMap {
  return (map as DrawnMap).svg !== undefined && (map as DrawnMap).schema === FIGURE_GEO_META_SCHEMA;
}

/** True when the locator carries drawable geometry. */
export function isDrawnLocator(locator: VisualsLocator): locator is DrawnLocator {
  return (locator as DrawnLocator).child_d !== undefined;
}

function validateDoc(parsed: unknown, path: string): DossierVisualsDoc {
  const doc = parsed as DossierVisualsDoc;
  if (doc?.schema !== VISUALS_SCHEMA) {
    throw new Error(`${path}: schema ${doc?.schema} — expected ${VISUALS_SCHEMA}`);
  }
  if (!doc.jurisdiction || !doc.map || !doc.locator) {
    throw new Error(`${path}: missing jurisdiction/map/locator blocks`);
  }
  if (isDrawnMap(doc.map)) {
    // Defence in depth at the inlining seam (SIG-UI-096): the page inlines
    // only bytes satisfying the one kit's no-script/no-handler contract.
    assertInlineSvgSafe(doc.map.svg, `${path}#map`);
  }
  for (const slot of doc.networks ?? []) {
    if (isDrawnNetwork(slot)) {
      assertInlineSvgSafe(slot.svg, `${path}#${slot.figure_id}`);
      assertInlineSvgSafe(slot.svg_narrow, `${path}#${slot.figure_id}-narrow`);
    }
  }
  return doc;
}

/**
 * One dossier's `sig.dossier-visuals/1` document — `null` when the build
 * carries none (an honest typed state on the page, never a hard failure):
 * fixtures mode serves the committed corpus; export mode reads the
 * restricted `inputs/dossier-visuals/<slug>.json` (never a published web
 * artifact — the visuals input itself stays unpublished, SIG-UI-134).
 */
export function getDossierVisuals(slug: string): DossierVisualsDoc | null {
  if (dataSource() !== "export") {
    const doc = DOSSIER_VISUALS_FIXTURE[slug];
    return doc ? validateDoc(doc, `fixture:${slug}`) : null;
  }
  const path = `${exportDir()}/inputs/dossier-visuals/${slug}.json`;
  if (!existsSync(path)) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(path, "utf-8"));
  } catch (cause) {
    throw new Error(`${path}: not valid JSON`, { cause });
  }
  return validateDoc(parsed, path);
}

// ---------------------------------------------------------------------------
// The locator-symbol sheet (sig.locator-symbols/1).
// ---------------------------------------------------------------------------

export interface LocatorSymbolRow {
  symbol: string;
  viewbox: [number, number];
}

export interface LocatorSymbols {
  /** jkey → {symbol id, viewbox} (the JSON index). */
  index: Record<string, LocatorSymbolRow>;
  /** symbol id → the parent-context path `d` (from the SVG sheet). */
  paths: Record<string, string>;
}

const SYMBOL_PATH_RE = /<symbol\s+id="([^"]+)"[^>]*>\s*<path\s+d="([^"]+)"[^>]*>/g;

/**
 * Parse the produced-work sheet — one `<symbol id>` → `<path d>` each —
 * fail-closed on a non-SVG document (SIG-ENG-042).
 */
export function parseLocatorSheet(svg: string, path: string): Record<string, string> {
  if (!svg.includes("<svg")) throw new Error(`${path}: not SVG bytes`);
  const out: Record<string, string> = {};
  for (const m of svg.matchAll(SYMBOL_PATH_RE)) out[m[1]!] = m[2]!;
  return out;
}

let _symbolsCache: LocatorSymbols | null = null;

/**
 * The shared parent-context glyph sheet every dossier locator cites. An
 * absent sheet yields `null` — the locator then renders its typed status
 * rather than a glyph with a missing parent (never a dead `<use>`).
 */
export function getLocatorSymbols(): LocatorSymbols | null {
  if (_symbolsCache) return _symbolsCache;
  if (dataSource() !== "export") {
    _symbolsCache = LOCATOR_SYMBOLS_FIXTURE;
    return _symbolsCache;
  }
  const dir = `${exportDir()}/web/figures`;
  const indexPath = `${dir}/locator-symbols.json`;
  const svgPath = `${dir}/locator-symbols.svg`;
  if (!existsSync(indexPath) || !existsSync(svgPath)) return null;
  const parsed = JSON.parse(readFileSync(indexPath, "utf-8")) as {
    schema?: string;
    symbols?: Record<string, LocatorSymbolRow>;
  };
  if (parsed.schema !== LOCATOR_SYMBOLS_SCHEMA) {
    throw new Error(`${indexPath}: schema ${parsed.schema} — expected ${LOCATOR_SYMBOLS_SCHEMA}`);
  }
  _symbolsCache = {
    index: parsed.symbols ?? {},
    paths: parseLocatorSheet(readFileSync(svgPath, "utf-8"), svgPath),
  };
  return _symbolsCache;
}

/** The drawable locator triple for one doc — `null` under every typed state. */
export function locatorGlyph(
  doc: DossierVisualsDoc,
  symbols: LocatorSymbols | null,
): { parentD: string; childD: string; viewbox: [number, number] } | null {
  if (!isDrawnLocator(doc.locator) || symbols === null) return null;
  const row = symbols.index[doc.locator.parent_jkey];
  const d = row ? symbols.paths[row.symbol] : undefined;
  if (!row || !d) return null;
  return { parentD: d, childD: doc.locator.child_d, viewbox: doc.locator.viewbox };
}

// ---------------------------------------------------------------------------
// SIG-UI-132 — figure counts reconcile.
// ---------------------------------------------------------------------------

/**
 * The fig-map twin row a dossier page cites — the dossier's own `figures[]`
 * row when the release minted one, else a row derived from the visuals doc's
 * own metadata (same caption template, same counts — K6 §5.1 verbatim).
 */
export function figMapTwin(
  dossier: { figures?: { figure_id: string; kind: string }[] },
  doc: DossierVisualsDoc | null,
): DossierFigureTwin | null {
  const own = dossier.figures?.find((f) => f.figure_id === "fig-map");
  if (own) return own as DossierFigureTwin;
  if (!doc || !isDrawnMap(doc.map)) return null;
  const m = doc.map;
  const elsewhere = m.not_drawn.located_elsewhere.reduce((n, r) => n + r.records, 0);
  return {
    figure_id: "fig-map",
    kind: "map",
    caption:
      `Where SIG's published records are in ${doc.jurisdiction.name}. ` +
      `${m.desc.records_drawn} of ${m.desc.records_total} published records drawn under ` +
      `the ${m.rule} rule (${m.mode}); ${m.not_drawn.declared_no_point} have no ` +
      `published point, ${elsewhere} declared here are located elsewhere, ` +
      `${m.not_drawn.conflicting} withheld as conflicting coordinates, ` +
      `${m.not_drawn.tier3} at precision tier 3. Not a census — counts show what ` +
      `the named sources publish. Where SIG has looked: rule pending — hollow ` +
      `areas rest on one source.`,
    caption_drafted: "agent-drafted (K6 §5.1 template, labelled — VIZ-02 binds the copy)",
    meta: m,
    links: {
      sites: `/dossier/${doc.jurisdiction.slug_path}/sites/`,
      download:
        doc.jurisdiction.level === "country" || doc.jurisdiction.level === "state_province"
          ? `/figures/dossier/${doc.jurisdiction.slug_path}.svg`
          : null,
    },
  };
}

/**
 * The not-drawn total a figure's caption counts: declared-without-point +
 * located-elsewhere + conflicting + tier-3 records.
 */
export function notDrawnTotal(nd: MapNotDrawn): number {
  return (
    nd.declared_no_point +
    nd.located_elsewhere.reduce((n, r) => n + r.records, 0) +
    nd.conflicting +
    nd.tier3
  );
}

/**
 * The reconciliation check the page + tests share: a drawn figure's
 * `records_drawn` plus its not-drawn counters MUST equal `desc.records_total`
 * — and that total MUST equal the dossier's published record figure for the
 * same framing and release (SIG-UI-132; K6's Σ table counts = figure rule).
 */
export function figureCountsReconcile(map: DrawnMap, dossierRecords: number | null): {
  drawn: number;
  total: number;
  dossierRecords: number | null;
  reconciles: boolean;
} {
  const drawn = map.desc.records_drawn;
  const total = map.desc.records_total;
  const accounted = drawn + notDrawnTotal(map.not_drawn) === total;
  const matches = dossierRecords === null || total === dossierRecords;
  return { drawn, total, dossierRecords, reconciles: accounted && matches };
}
