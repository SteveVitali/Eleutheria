// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.37 (K1 MAP-03a app shell) — the pure model half of the `/map/` T2 app:
 * the record shape the selection panel reads (SIG-UI-101), the in-view list
 * model (SIG-UI-102), the filter/facet model with counts and the cannot-apply
 * rule (SIG-UI-104), and the tile-feature → panel projection. Everything here
 * is DOM-free so the same logic is unit-tested without a browser and the
 * fixtures path and the tile path share it.
 *
 * P37.18 (K1 MAP-03b) extends the same pure half: the `sig.map-dict/1`
 * document model and the tile-path filters (`sig.map-tiles/2` props —
 * `tc`/`vd`/`oe`/`sr`/`f`/`l`/`st`), the browser-side `cells` summation
 * (K1 §3.2 — marginal facet props `t_<code>`/`v_<slot>`/`s1`, never a joint
 * slice the tiles do not carry), the zoom-honesty rule applied to DRAWN data
 * (a filter that cannot apply greys the drawn set with a note — C-03, no
 * hatch), the in-view table model + CSV download (K1 §4.6), and the mobile
 * bottom-sheet snap model (K1 §4.1).
 *
 * Copy rules (UXR-13 / SIG-UI-063): observation-level rows are "records" —
 * never "sites" or "cameras" in app copy. Links follow UXR-18 / SIG-UI-068:
 * a record link targets the dossier sites-list anchor until `/r/<pub>/` is
 * public, and a link is emitted ONLY when it resolves — never a 404.
 */

import { NATIONAL_ZOOM_MAX } from "../../lib/map";

// ---------------------------------------------------------------- records //

/** The epistemic status the tile contract encodes (`st`, sig.map-tiles/2 §3.3). */
export type SiteStatus = "corroborated" | "single-source" | "contested" | "candidate";

/** `st` code ↔ status (sig.map-tiles/2: 0 corroborated · 1 single · 2 contested · 3 provisional/candidate). */
export const STATUS_BY_CODE: readonly SiteStatus[] = [
  "corroborated",
  "single-source",
  "contested",
  "candidate",
];
export const STATUS_CODE: Record<SiteStatus, number> = {
  corroborated: 0,
  "single-source": 1,
  contested: 2,
  candidate: 3,
};
export const STATUS_TEXT: Record<SiteStatus, string> = {
  corroborated: "Corroborated",
  "single-source": "One source",
  contested: "Contested",
  candidate: "Candidate",
};

/** Normalise any wire status word ("single source", "corroborated", …) to a code. */
export function statusCode(raw: string | null | undefined): SiteStatus | null {
  if (!raw) return null;
  const s = raw.toLowerCase().trim();
  if (s === "corroborated") return "corroborated";
  if (s === "single source" || s === "single-source" || s === "one source") return "single-source";
  if (s === "contested" || s === "unresolved") return "contested";
  if (s === "candidate" || s === "provisional") return "candidate";
  return null;
}

/** A link that is emitted ONLY when it resolves (UXR-18 — never a 404). */
export interface NamedLink {
  label: string;
  href: string | null;
}

/**
 * One located record the app can select and list — the fixtures-mode payload
 * (bounded to the located set) and the shape the tile path projects into.
 * Every field is already published at the record's tier; nothing finer rides
 * the wire (§19.4).
 */
export interface MapRecord {
  /** The record key (`rk` in tiles; the sites-list `#<key>` anchor id). */
  id: string;
  /** The derived label — never a raw identifier (SIG-UI-053/101). */
  label: string;
  /** Technology facet text (the slug or dict label; "unclassified" is a state). */
  technology: string;
  /** Operator display text; null renders the "not stated" wording. */
  operator: string | null;
  /** Contributing sources with their resolvable links (null → text only). */
  sources: NamedLink[];
  /** The record's licence line (per-compartment attribution, §42.3). */
  licence: string | null;
  /** The placed jurisdiction (linked to its dossier when it resolves). */
  jurisdiction: NamedLink;
  firstSeen: string | null;
  lastSeen: string | null;
  status: SiteStatus | null;
  /** The precision/point text at the published tier (SIG-UI-101's "precision"). */
  precision: string;
  tier: number;
  lat: number;
  lon: number;
  /** The licence compartment the record draws under. */
  compartment: string | null;
  /** The interim record link — the dossier sites-list anchor (never 404). */
  recordHref: string | null;
  /** The site-list (cross-compartment reading view) link for the record's dossier. */
  listHref: string | null;
  /**
   * P37.19 (MAP-04): the record's canonical jurisdiction key and its
   * root-first ancestor chain (self last) — the `jurisdiction=` facet
   * matches a record when a facet key sits in this chain (the place itself
   * and its descendants, `jurisdiction_chain` semantics). `null`/absent
   * means unkeyed — a facet never guesses it in.
   */
  jkey?: string | null;
  chain?: string[];
}

// ------------------------------------------------------------ tile props //

/** The §3.3 tile-property row (sig.map-tiles/2) the `sites` layer carries. */
export interface TileSiteProps {
  rk?: string;
  lb?: string;
  tc?: number;
  /** P37.17: vendor slot (dict `vendor_slots[]`); 0 = unknown. */
  vd?: number;
  op?: string;
  /** P37.17: operator entity key when resolved (the `operator=` wire value). */
  oe?: string;
  sr?: number;
  j?: string;
  f?: number;
  l?: number;
  st?: number;
  tr?: number;
  pm?: number;
  co?: number;
}

/** `yyyymm` int → "YYYY-MM" display text (empty when absent/implausible). */
export function monthText(v: number | null | undefined): string | null {
  if (v === null || v === undefined || !Number.isFinite(v)) return null;
  const y = Math.floor(v / 100);
  const m = v % 100;
  if (y < 1900 || y > 2200 || m < 1 || m > 12) return null;
  return `${y}-${String(m).padStart(2, "0")}`;
}

// --------------------------------------------------------- selection pane //

/** The SIG-UI-101 selection panel rows — every field a text value + link. */
export interface SelectionPanelModel {
  id: string;
  label: string;
  technology: string;
  operatorText: string;
  jurisdiction: NamedLink;
  sources: NamedLink[];
  licenceText: string | null;
  firstSeen: string | null;
  lastSeen: string | null;
  precision: string;
  statusText: string;
  /** Interim record link (the sites-list anchor) — null when unresolvable. */
  recordHref: string | null;
  /** The jurisdiction's sites list (the "Show on list" target). */
  listHref: string | null;
  /** The released-record page when a release is pinned (the /r/ twin). */
  recordPageHref: string | null;
  /** The dispute route carrying the record key. */
  disputeHref: string | null;
  /** Where the selection was resolved (in view = true; honest "not in view" = false). */
  located: boolean;
}

/** "Operator not stated by any source" — K1 §4.5's verbatim honest wording. */
export const OPERATOR_NOT_STATED = "Operator not stated by any source";

/**
 * Project a MapRecord (fixtures path) into the panel model. Links come from
 * the record itself — `recordHref` is only set when the anchor exists.
 */
export function selectionFromRecord(
  rec: MapRecord,
  extras: { recordPageHref?: string | null; disputeHref?: string | null } = {},
): SelectionPanelModel {
  return {
    id: rec.id,
    label: rec.label,
    technology: rec.technology,
    operatorText: rec.operator ?? OPERATOR_NOT_STATED,
    jurisdiction: rec.jurisdiction,
    sources: rec.sources,
    licenceText: rec.licence,
    firstSeen: rec.firstSeen,
    lastSeen: rec.lastSeen,
    precision: rec.precision,
    statusText: rec.status ? STATUS_TEXT[rec.status] : "Not recorded",
    recordHref: rec.recordHref,
    listHref: rec.listHref,
    recordPageHref: extras.recordPageHref ?? null,
    disputeHref: extras.disputeHref ?? null,
    located: true,
  };
}

/**
 * Project raw tile props into the panel model (tile path). Only what the
 * archive publishes may show — a field the tile does not carry renders the
 * honest "not stated" state, never a guessed value (SIG-ENG-042).
 */
export function selectionFromTileProps(
  p: TileSiteProps,
  ctx: {
    jurisdictionLink?: NamedLink | null;
    technologyLabel?: (code: number) => string | null;
    sourceLabel?: (index: number) => NamedLink | null;
    recordHref?: (rk: string) => string | null;
    recordPageHref?: string | null;
    disputeHref?: string | null;
  },
): SelectionPanelModel {
  const rk = String(p.rk ?? "");
  const tech =
    typeof p.tc === "number" && p.tc > 0
      ? (ctx.technologyLabel?.(p.tc) ?? `Technology code ${p.tc}`)
      : "Unclassified";
  const status = typeof p.st === "number" ? (STATUS_BY_CODE[p.st] ?? null) : null;
  const precision =
    typeof p.pm === "number" && p.pm > 0
      ? `Location truncated to ~${p.pm} m`
      : p.tr === 2
        ? "Location published as an area"
        : "Location as published";
  const sourceLink =
    typeof p.sr === "number" ? (ctx.sourceLabel?.(p.sr) ?? null) : null;
  return {
    id: rk,
    label: String(p.lb ?? rk),
    technology: tech,
    operatorText: p.op ?? OPERATOR_NOT_STATED,
    jurisdiction: ctx.jurisdictionLink ?? { label: String(p.j ?? ""), href: null },
    sources: sourceLink ? [sourceLink] : [],
    licenceText: null,
    firstSeen: monthText(p.f),
    lastSeen: monthText(p.l),
    precision,
    statusText: status ? STATUS_TEXT[status] : "Not recorded",
    recordHref: rk ? (ctx.recordHref?.(rk) ?? null) : null,
    listHref: null,
    recordPageHref: ctx.recordPageHref ?? null,
    disputeHref: ctx.disputeHref ?? null,
    located: true,
  };
}

// --------------------------------------------------------------- filters //

/** The facet values the app tracks. `collection` rides the compartment set. */
export interface MapFacets {
  technology: string[];
  status: SiteStatus[];
  /** `YYYY-MM..YYYY-MM` month range (the wire `seen=` form), or null. */
  seen: { from: string; to: string } | null;
}

export const EMPTY_FACETS: MapFacets = { technology: [], status: [], seen: null };

const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

/** Parse the wire `seen=` range to the app's facet shape (null = unparseable/absent). */
export function parseSeenRange(raw: string | null): { from: string; to: string } | null {
  if (!raw) return null;
  const m = /^(\d{4}(?:-(?:0[1-9]|1[0-2]))?)\.\.(\d{4}(?:-(?:0[1-9]|1[0-2]))?)$/.exec(raw);
  if (!m) return null;
  const norm = (v: string) => (v.length === 4 ? `${v}-01` : v);
  const from = norm(m[1]!);
  const to = m[2]!.length === 4 ? `${m[2]}-12` : m[2]!;
  return MONTH_RE.test(from) && MONTH_RE.test(to) ? { from, to } : null;
}

/** The wire `seen=` value for a facet (null facet → null). */
export function seenRangeWire(seen: MapFacets["seen"]): string | null {
  return seen ? `${seen.from}..${seen.to}` : null;
}

/** A record's months overlap the [from,to] month range (inclusive). */
export function seenOverlaps(
  rec: { firstSeen: string | null; lastSeen: string | null },
  seen: { from: string; to: string },
): boolean {
  const f = rec.firstSeen?.slice(0, 7) ?? null;
  const l = rec.lastSeen?.slice(0, 7) ?? null;
  if (f === null && l === null) return false;
  if (f !== null && f > seen.to) return false;
  if (l !== null && l < seen.from) return false;
  return true;
}

/** Whether a record passes the active facets (technology/status/seen/jurisdiction). */
export function recordPasses(rec: MapRecord, facets: MapFacets): boolean {
  if (facets.technology.length > 0 && !facets.technology.includes(rec.technology)) {
    return false;
  }
  if (facets.status.length > 0 && (rec.status === null || !facets.status.includes(rec.status))) {
    return false;
  }
  if (facets.seen && !seenOverlaps(rec, facets.seen)) return false;
  const jur = (facets as MapFacetsV2).jurisdiction;
  if (jur !== undefined && jur.length > 0 && !jkeyWithin(rec.jkey ?? null, rec.chain, jur)) {
    return false;
  }
  return true;
}

/**
 * P37.19 (MAP-04, C-11): the `jurisdiction=` facet matches descendants —
 * a record/site passes when its own jkey's ancestor chain (self included)
 * contains a selected key. An unkeyed record or an unknown chain matches
 * only when the record's own key IS the selected one — never a guessed
 * ancestry.
 */
export function jkeyWithin(
  jkey: string | null | undefined,
  chain: readonly string[] | undefined,
  selected: readonly string[],
): boolean {
  if (selected.length === 0) return true;
  if (!jkey) return false;
  const ancestry = chain && chain.length > 0 ? chain : [jkey];
  return selected.some((s) => ancestry.includes(s));
}

/**
 * The cannot-apply rule (SIG-UI-104, K1 §4.3 verbatim): a facet that cannot
 * apply at the current zoom greys its cells with a note and NO hatch — the
 * map never shows unfiltered counts as if filtered. `seen` aggregates over
 * cells below the sites band, so it can only apply once individual records
 * are drawn (z ≥ 10).
 */
export function facetCannotApply(name: keyof MapFacets | "collection", zoom: number): string | null {
  if (name === "seen" && zoom <= NATIONAL_ZOOM_MAX) {
    return `Seen-date filtering applies from zoom ${NATIONAL_ZOOM_MAX + 1}`;
  }
  return null;
}

/** The count each active facet contributes — in-view matches vs total in view. */
export interface FacetCounts {
  /** option value → records in view matching it (before that facet's own filter). */
  perOption: Map<string, number>;
  /** records passing every other facet — the option's effective count. */
  totalInView: number;
}

/** Distinct option values for a facet over the in-view records (stable order). */
export function facetOptions(records: readonly MapRecord[], pick: (r: MapRecord) => string | null): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const r of records) {
    const v = pick(r);
    if (v !== null && !seen.has(v)) {
      seen.add(v);
      out.push(v);
    }
  }
  return out.sort((a, b) => a.localeCompare(b));
}

/** Count records matching each option (a record counts once per option it holds). */
export function facetOptionCounts(
  records: readonly MapRecord[],
  pick: (r: MapRecord) => string | null,
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const r of records) {
    const v = pick(r);
    if (v !== null) counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  return counts;
}

// ------------------------------------------------------------- in-view //

/** One row of the synchronized "in view" list (SIG-UI-102). */
export interface InViewRow {
  id: string;
  label: string;
  meta: string;
  /** The record id this row selects (sites rows), or null (place rows). */
  selectId: string | null;
  /** The place frame action (place rows): centre + zoom to fit. */
  frame?: { lat: number; lon: number; zoom: number };
  /** Dossier / sites-list links where they resolve. */
  dossierHref?: string | null;
  listHref?: string | null;
  distanceKm: number;
  /** P37.18: the published point when the row carries one (hover highlight). */
  lat?: number;
  lon?: number;
  /** P37.18: structured fields the sortable table view + CSV read. */
  technology?: string;
  operator?: string;
  statusText?: string;
  sourceText?: string | null;
  licence?: string | null;
  compartment?: string | null;
  /** P37.18: a place row's registry bbox (`fitBounds` when present). */
  bbox?: [number, number, number, number];
}

/** The cap K1 sets on the list (≤ 50 rows). */
export const IN_VIEW_MAX = 50;

/** km between two coordinates (equirectangular — list ordering only). */
export function distanceKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLon = ((b.lon - a.lon) * Math.PI) / 180;
  const meanLat = (((a.lat + b.lat) / 2) * Math.PI) / 180;
  const x = dLon * Math.cos(meanLat);
  return Math.sqrt(x * x + dLat * dLat) * 6371;
}

/** Whether a record sits inside the current bounds. */
export function inBounds(
  rec: { lat: number; lon: number },
  b: { w: number; s: number; e: number; n: number },
): boolean {
  return rec.lat >= b.s && rec.lat <= b.n && rec.lon >= b.w && rec.lon <= b.e;
}

/**
 * The sites-from-z10 list: records in bounds passing the facets, sorted by
 * distance from centre, capped at IN_VIEW_MAX.
 */
export function siteRowsInView(
  records: readonly MapRecord[],
  facets: MapFacets,
  bounds: { w: number; s: number; e: number; n: number },
  centre: { lat: number; lon: number },
): { rows: InViewRow[]; matching: number } {
  const matching = records.filter((r) => inBounds(r, bounds) && recordPasses(r, facets));
  const rows = matching
    .map((r) => ({
      id: r.id,
      label: r.label,
      meta: `${r.technology} · ${r.operator ?? "not stated"} · ${r.status ? STATUS_TEXT[r.status] : "not recorded"}`,
      selectId: r.id,
      dossierHref: r.jurisdiction.href,
      listHref: r.recordHref,
      distanceKm: distanceKm(r, centre),
      lat: r.lat,
      lon: r.lon,
      technology: r.technology,
      operator: r.operator ?? "not stated",
      statusText: r.status ? STATUS_TEXT[r.status] : "not recorded",
      sourceText: r.sources[0]?.label ?? null,
      licence: r.licence,
      compartment: r.compartment,
    }))
    .sort((a, b) => a.distanceKm - b.distanceKm || a.id.localeCompare(b.id))
    .slice(0, IN_VIEW_MAX);
  return { rows, matching: matching.length };
}

/**
 * The places-below-z10 list: jurisdiction groups of the in-bounds records,
 * each with its count, a "Show" frame and the dossier/sites-list links.
 */
export function placeRowsInView(
  records: readonly MapRecord[],
  facets: MapFacets,
  bounds: { w: number; s: number; e: number; n: number },
): { rows: InViewRow[]; matching: number } {
  const groups = new Map<string, { label: string; href: string | null; list: string | null; recs: MapRecord[] }>();
  let matching = 0;
  for (const r of records) {
    if (!inBounds(r, bounds) || !recordPasses(r, facets)) continue;
    matching += 1;
    const key = r.jurisdiction.label;
    const g = groups.get(key) ?? { label: key, href: r.jurisdiction.href, list: r.listHref, recs: [] };
    g.recs.push(r);
    groups.set(key, g);
  }
  const rows = [...groups.values()]
    .map((g) => {
      const lat = g.recs.reduce((a, r) => a + r.lat, 0) / g.recs.length;
      const lon = g.recs.reduce((a, r) => a + r.lon, 0) / g.recs.length;
      return {
        id: g.label,
        label: `${g.label} — ${g.recs.length} record${g.recs.length === 1 ? "" : "s"}`,
        meta: `${g.recs.length} record${g.recs.length === 1 ? "" : "s"} in view`,
        selectId: null,
        frame: { lat, lon, zoom: NATIONAL_ZOOM_MAX + 1 },
        dossierHref: g.href,
        listHref: g.list,
        distanceKm: 0,
      };
    })
    .sort((a, b) => a.label.localeCompare(b.label))
    .slice(0, IN_VIEW_MAX);
  return { rows, matching };
}

// ============================================================ P37.18 (MAP-03b)

/** The `sig.map-dict/1` document (P37.17) — the indices tile props resolve through. */
export interface MapDictSource {
  index: number;
  id: string;
  name: string;
  publisher?: string | null;
  licence?: string | null;
  compartment?: string | null;
  url?: string;
}
export interface MapDictTech {
  code: number;
  slug: string;
  label: string;
}
export interface MapDictVendor {
  slot: number;
  key: string;
  label: string;
}
export interface MapDictJurisdiction {
  name?: string;
  level?: string;
  chain?: string[];
  /** `[w, s, e, n]` degrees, or null. */
  bbox?: number[] | null;
}
export interface MapDict {
  schema: string;
  contract?: string;
  sources: MapDictSource[];
  technologies: MapDictTech[];
  vendor_slots: MapDictVendor[];
  jurisdictions: Record<string, MapDictJurisdiction>;
  unplotted: Record<string, number>;
  totals: {
    slice_rows?: number;
    by_technology?: Record<string, number>;
    by_vendor_slot?: Record<string, number>;
    unplotted_rows?: number;
  };
}

export function isMapDict(o: unknown): o is MapDict {
  const d = o as Partial<MapDict> | null;
  return (
    d !== null &&
    typeof d === "object" &&
    d.schema === "sig.map-dict/1" &&
    Array.isArray(d.sources) &&
    Array.isArray(d.technologies) &&
    typeof d.jurisdictions === "object" &&
    d.jurisdictions !== null
  );
}

/** The lookups the tile-path filters resolve through. */
export interface FacetDict {
  techCodeBySlug: Map<string, number>;
  techSlugByCode: Map<number, string>;
  vendorSlotByKey: Map<string, number>;
  vendorBySlot: Map<number, MapDictVendor>;
  sourceByIndex: Map<number, MapDictSource>;
  sourceIndexById: Map<string, number>;
  jurisdictions: Record<string, MapDictJurisdiction>;
}

export function buildFacetDict(dict: MapDict | null): FacetDict {
  const techCodeBySlug = new Map<string, number>();
  const techSlugByCode = new Map<number, string>();
  for (const t of dict?.technologies ?? []) {
    techCodeBySlug.set(t.slug, t.code);
    techSlugByCode.set(t.code, t.slug);
  }
  const vendorSlotByKey = new Map<string, number>();
  const vendorBySlot = new Map<number, MapDictVendor>();
  for (const v of dict?.vendor_slots ?? []) {
    vendorSlotByKey.set(v.key, v.slot);
    vendorBySlot.set(v.slot, v);
  }
  const sourceByIndex = new Map<number, MapDictSource>();
  const sourceIndexById = new Map<string, number>();
  for (const s of dict?.sources ?? []) {
    sourceByIndex.set(s.index, s);
    sourceIndexById.set(s.id, s.index);
  }
  return {
    techCodeBySlug,
    techSlugByCode,
    vendorSlotByKey,
    vendorBySlot,
    sourceByIndex,
    sourceIndexById,
    jurisdictions: dict?.jurisdictions ?? {},
  };
}

export const EMPTY_FACET_DICT: FacetDict = buildFacetDict(null);

/** The `cells` layer props (z0–9 aggregation, sig.map-tiles/2 §3.3). */
export interface TileCellProps {
  h3?: string;
  n?: number;
  ns?: number;
  jp?: string;
  s1?: number;
  sx?: number;
  [key: string]: unknown;
}

// -------------------------------------------------------- facet extension //

/** MAP-03b's added facet dims (vendor/operator/source — wire values are the
 * entity keys / source ids of sig.workspace-state/2); P37.19 adds the
 * descendants-inclusive `jurisdiction` facet (C-11: a filter, distinct
 * from `frame=`'s framing-only state). */
export interface MapFacetsV2 extends MapFacets {
  vendor: string[];
  operator: string[];
  source: string[];
  jurisdiction: string[];
}

/** Whether a `sites`-layer feature passes every active facet (tile path). */
export function tileSitePasses(
  p: TileSiteProps & { vd?: number; oe?: string },
  f: MapFacetsV2,
  d: FacetDict,
): boolean {
  if (f.technology.length > 0) {
    const code = typeof p.tc === "number" ? p.tc : 0;
    if (!f.technology.some((slug) => d.techCodeBySlug.get(slug) === code)) return false;
  }
  if (f.status.length > 0) {
    const st = typeof p.st === "number" ? (STATUS_BY_CODE[p.st] ?? null) : null;
    if (st === null || !f.status.includes(st)) return false;
  }
  if (f.vendor.length > 0) {
    const slot = typeof p.vd === "number" ? p.vd : 0;
    if (!f.vendor.some((k) => d.vendorSlotByKey.get(k) === slot)) return false;
  }
  if (f.operator.length > 0) {
    if (typeof p.oe !== "string" || !f.operator.includes(p.oe)) return false;
  }
  if (f.source.length > 0) {
    const idx = typeof p.sr === "number" ? p.sr : -1;
    if (!f.source.some((id) => d.sourceIndexById.get(id) === idx)) return false;
  }
  if (f.seen) {
    const fInt = typeof p.f === "number" ? p.f : null;
    const lInt = typeof p.l === "number" ? p.l : null;
    const from = Number(f.seen.from.replace("-", ""));
    const to = Number(f.seen.to.replace("-", ""));
    if (fInt === null && lInt === null) return false;
    if (fInt !== null && fInt > to) return false;
    if (lInt !== null && lInt < from) return false;
  }
  if (f.jurisdiction.length > 0) {
    const j = typeof p.j === "string" && p.j !== "" ? p.j : null;
    const chain = j ? (d.jurisdictions[j]?.chain ?? [j]) : undefined;
    if (!jkeyWithin(j, chain, f.jurisdiction)) return false;
  }
  return true;
}

/**
 * The MapLibre filter-expression fragment the active facets contribute for
 * the `sites` layers (AND-ed with each status layer's base filter). `null`
 * means no facet narrows the drawn set.
 */
export function tileFacetExpr(f: MapFacetsV2, d: FacetDict): unknown[] | null {
  const parts: unknown[] = [];
  if (f.technology.length > 0) {
    const codes = f.technology
      .map((s) => d.techCodeBySlug.get(s))
      .filter((c): c is number => c !== undefined);
    if (codes.length === 0) return ["==", 1, 0];
    parts.push(["in", ["get", "tc"], ["literal", codes]]);
  }
  if (f.vendor.length > 0) {
    const slots = f.vendor
      .map((k) => d.vendorSlotByKey.get(k))
      .filter((c): c is number => c !== undefined);
    if (slots.length === 0) return ["==", 1, 0];
    parts.push(["in", ["get", "vd"], ["literal", slots]]);
  }
  if (f.operator.length > 0) {
    parts.push(["in", ["get", "oe"], ["literal", f.operator]]);
  }
  if (f.source.length > 0) {
    const idxs = f.source
      .map((id) => d.sourceIndexById.get(id))
      .filter((c): c is number => c !== undefined);
    if (idxs.length === 0) return ["==", 1, 0];
    parts.push(["in", ["get", "sr"], ["literal", idxs]]);
  }
  if (f.seen) {
    const from = Number(f.seen.from.replace("-", ""));
    const to = Number(f.seen.to.replace("-", ""));
    // seen = (f <= to) AND (l >= from OR l absent means open-ended→kept?)
    // An absent `f`/`l` is honest absence — it cannot satisfy a date facet.
    parts.push([
      "all",
      ["has", "f"],
      ["<=", ["get", "f"], to],
      ["all", ["has", "l"], [">=", ["get", "l"], from]],
    ]);
  }
  if (f.jurisdiction.length > 0) {
    // Descendants-inclusive (C-11): the drawn feature's `j` must sit in the
    // selected subtree — expanded over the dictionary's chains. An empty
    // expansion honestly matches nothing rather than everything.
    const allowed = jurisdictionSubtreeKeys(f.jurisdiction, d);
    if (allowed.length === 0) return ["==", 1, 0];
    parts.push(["in", ["get", "j"], ["literal", allowed]]);
  }
  if (parts.length === 0) return null;
  return parts.length === 1 ? (parts[0] as unknown[]) : ["all", ...parts];
}

/** Every dict jkey inside any selected `jurisdiction=` subtree (self + descendants). */
export function jurisdictionSubtreeKeys(
  selected: readonly string[],
  d: FacetDict,
): string[] {
  if (selected.length === 0) return [];
  const out = new Set<string>(selected);
  for (const [jkey, j] of Object.entries(d.jurisdictions)) {
    const chain = Array.isArray(j.chain) && j.chain.length > 0 ? j.chain : [jkey];
    if (selected.some((s) => chain.includes(s))) out.add(jkey);
  }
  return [...out].sort();
}

// --------------------------------------------------------- zoom honesty //

/**
 * Which `cells` prop a single active facet dimension slices by (K1 §3.2 —
 * the cells carry MARGINAL counts `t_<code>` / `v_<slot>` / `s1`; a joint
 * slice the tiles do not carry is honestly "cannot apply"). Returns
 * `{kind:"n"}` (no facet narrows), `{kind:"props", keys}` (sum these props)
 * or `{kind:"cannot"}` (active facets the cells cannot honour).
 */
export type CellSlice =
  | { kind: "n" }
  | { kind: "props"; keys: string[]; label: string }
  | { kind: "cannot"; dims: string[] };

export function cellSlice(f: MapFacetsV2, d: FacetDict): CellSlice {
  const cannot: string[] = [];
  const sliceable: { dim: string; keys: string[] }[] = [];
  if (f.technology.length > 0) {
    sliceable.push({
      dim: "technology",
      keys: f.technology
        .map((s) => d.techCodeBySlug.get(s))
        .filter((c): c is number => c !== undefined)
        .map((c) => `t_${c}`),
    });
  }
  if (f.vendor.length > 0) {
    sliceable.push({
      dim: "vendor",
      keys: f.vendor
        .map((k) => d.vendorSlotByKey.get(k))
        .filter((c): c is number => c !== undefined)
        .map((c) => `v_${c}`),
    });
  }
  if (f.status.length > 0) {
    // Cells carry s1 (single-source) + sx (everything else) — only the pure
    // single-source selection slices honestly.
    if (f.status.length === 1 && f.status[0] === "single-source") {
      sliceable.push({ dim: "status", keys: ["s1"] });
    } else {
      cannot.push("status");
    }
  }
  if (f.seen) cannot.push("seen");
  if (f.operator.length > 0) cannot.push("operator");
  if (f.source.length > 0) cannot.push("source");
  // A cell's `jp` is a plurality key — the count cells cannot slice a
  // jurisdiction subtree honestly, so the facet cannot apply below z10.
  if (f.jurisdiction.length > 0) cannot.push("jurisdiction");
  if (cannot.length > 0) return { kind: "cannot", dims: cannot };
  if (sliceable.length > 1) {
    return { kind: "cannot", dims: sliceable.map((s) => s.dim) };
  }
  if (sliceable.length === 1) {
    const s = sliceable[0];
    return s.keys.length === 0
      ? { kind: "cannot", dims: [s.dim] }
      : { kind: "props", keys: s.keys, label: s.dim };
  }
  return { kind: "n" };
}

/** The value one cell contributes under the slice (deduped per (comp, h3)). */
export function cellSliceValue(p: TileCellProps, slice: CellSlice): number {
  if (slice.kind === "cannot") return typeof p.n === "number" ? p.n : 0;
  if (slice.kind === "n") return typeof p.n === "number" ? p.n : 0;
  let sum = 0;
  for (const k of slice.keys) {
    const v = p[k];
    if (typeof v === "number") sum += v;
  }
  return sum;
}

/**
 * The drawn-set honesty rule (SIG-UI-104, C-03): the dims whose ACTIVE
 * selection cannot apply at this zoom/mode, each with the note to show.
 * When non-empty, the drawn layers desaturate (grey, NO hatch) and the
 * matching facets are dropped from `effectiveFacets` — the map and the list
 * then show the same honestly-unfiltered set.
 */
export function cannotApplyNotes(
  f: MapFacetsV2,
  zoom: number,
  tileMode: boolean,
): { dim: string; note: string }[] {
  const out: { dim: string; note: string }[] = [];
  const atCellsBand = zoom <= NATIONAL_ZOOM_MAX;
  if (f.seen && atCellsBand) {
    out.push({
      dim: "seen",
      note: `Seen-date filtering applies from zoom ${NATIONAL_ZOOM_MAX + 1} — the map is showing every record, not a filtered set.`,
    });
  }
  if (tileMode && atCellsBand) {
    if (f.operator.length > 0) {
      out.push({
        dim: "operator",
        note: `Operator filtering applies from zoom ${NATIONAL_ZOOM_MAX + 1} — the map is showing every record, not a filtered set.`,
      });
    }
    if (f.source.length > 0) {
      out.push({
        dim: "source",
        note: `Source filtering applies from zoom ${NATIONAL_ZOOM_MAX + 1} — the map is showing every record, not a filtered set.`,
      });
    }
    if (f.jurisdiction.length > 0) {
      out.push({
        dim: "jurisdiction",
        note: `Place filtering applies from zoom ${NATIONAL_ZOOM_MAX + 1} — the count cells cannot slice a place subtree, so the map is showing every record in the area, not a filtered set.`,
      });
    }
    if (
      f.status.length > 0 &&
      !(f.status.length === 1 && f.status[0] === "single-source")
    ) {
      out.push({
        dim: "status",
        note: `This status selection can't slice the count cells — it applies from zoom ${NATIONAL_ZOOM_MAX + 1}.`,
      });
    }
    const joint =
      (f.technology.length > 0 ? 1 : 0) +
      (f.vendor.length > 0 ? 1 : 0) +
      (f.status.length === 1 && f.status[0] === "single-source" ? 1 : 0);
    if (joint > 1) {
      out.push({
        dim: "joint",
        note: `Combined facets can't slice the count cells — they apply together from zoom ${NATIONAL_ZOOM_MAX + 1}.`,
      });
    }
  }
  return out;
}

/** The facet set that may HONESTLY narrow the drawn set at this zoom. */
export function effectiveFacets(
  f: MapFacetsV2,
  zoom: number,
  tileMode: boolean,
): MapFacetsV2 {
  const blocked = new Set(cannotApplyNotes(f, zoom, tileMode).map((n) => n.dim));
  const out: MapFacetsV2 = { ...f };
  if (blocked.has("seen")) out.seen = null;
  if (blocked.has("operator")) out.operator = [];
  if (blocked.has("source")) out.source = [];
  if (blocked.has("status")) out.status = [];
  if (blocked.has("jurisdiction")) out.jurisdiction = [];
  if (blocked.has("joint")) {
    out.technology = [];
    out.vendor = [];
  }
  return out;
}

// ------------------------------------------------- tile-path in-view rows //

/** One drawn site feature the viewport holds (deduped by `rk`). */
export interface TileSiteFeature {
  props: TileSiteProps & { vd?: number; oe?: string };
  lat: number;
  lon: number;
  compartment: string;
}

/** Dedupe rendered/source features by `rk`, keeping the first seen. */
export function dedupeTileSites(
  features: { props: TileSiteFeature["props"]; lat: number; lon: number; compartment: string }[],
): TileSiteFeature[] {
  const seen = new Set<string>();
  const out: TileSiteFeature[] = [];
  for (const f of features) {
    const rk = String(f.props.rk ?? "");
    if (rk === "" || seen.has(rk)) continue;
    seen.add(rk);
    out.push(f);
  }
  return out;
}

/** The z≥10 tile-path list: passing records sorted by distance, capped at 50. */
export function tileSiteRowsInView(
  sites: readonly TileSiteFeature[],
  facets: MapFacetsV2,
  dict: FacetDict,
  centre: { lat: number; lon: number },
  hrefs: {
    jurisdictionHref?: (jkey: string) => string | null;
    recordPageHref?: (rk: string) => string | null;
  } = {},
): { rows: InViewRow[]; matching: number; passing: TileSiteFeature[] } {
  const passing = sites.filter((f) => tileSitePasses(f.props, facets, dict));
  const rows: InViewRow[] = passing
    .map((f) => {
      const p = f.props;
      const rk = String(p.rk ?? "");
      const st = typeof p.st === "number" ? (STATUS_BY_CODE[p.st] ?? null) : null;
      const tech =
        typeof p.tc === "number" && p.tc > 0
          ? (dict.techSlugByCode.get(p.tc) ?? `code ${p.tc}`)
          : "unclassified";
      const src = typeof p.sr === "number" ? dict.sourceByIndex.get(p.sr) : undefined;
      return {
        id: rk,
        label: String(p.lb ?? rk),
        meta: `${tech} · ${p.op ?? "not stated"} · ${st ? STATUS_TEXT[st] : "not recorded"}`,
        selectId: rk,
        dossierHref:
          typeof p.j === "string" ? (hrefs.jurisdictionHref?.(p.j) ?? null) : null,
        listHref: rk ? (hrefs.recordPageHref?.(rk) ?? null) : null,
        distanceKm: distanceKm({ lat: f.lat, lon: f.lon }, centre),
        lat: f.lat,
        lon: f.lon,
        technology: tech,
        operator: p.op ?? "not stated",
        statusText: st ? STATUS_TEXT[st] : "not recorded",
        sourceText: src?.name ?? null,
        licence: src?.licence ?? null,
        compartment: src?.compartment ?? f.compartment,
      };
    })
    .sort((a, b) => a.distanceKm - b.distanceKm || a.id.localeCompare(b.id))
    .slice(0, IN_VIEW_MAX);
  return { rows, matching: passing.length, passing };
}

/**
 * The z≤9 tile-path "Places in view": dedupe the drawn `cells` by
 * `(compartment, h3)`, apply the single-dim slice, then group by the cell's
 * plurality jurisdiction `jp` with its count + single-source share.
 */
export function tilePlaceRowsInView(
  cells: { props: TileCellProps; compartment: string }[],
  slice: CellSlice,
  dict: FacetDict,
  hrefs: { jurisdictionHref?: (jkey: string) => string | null } = {},
): { rows: InViewRow[]; matching: number } {
  const seen = new Set<string>();
  const groups = new Map<
    string,
    { count: number; single: number; total: number; lat: number; lon: number }
  >();
  for (const c of cells) {
    const h3 = String(c.props.h3 ?? "");
    if (h3 === "") continue;
    const key = `${c.compartment}|${h3}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const jp = String(c.props.jp ?? "unplaced");
    const g = groups.get(jp) ?? { count: 0, single: 0, total: 0, lat: 0, lon: 0 };
    g.count += cellSliceValue(c.props, slice);
    g.single += typeof c.props.s1 === "number" ? c.props.s1 : 0;
    g.total += typeof c.props.n === "number" ? c.props.n : 0;
    groups.set(jp, g);
  }
  let matching = 0;
  const rows: InViewRow[] = [];
  for (const [jp, g] of groups) {
    matching += g.count;
    const jdoc = dict.jurisdictions[jp];
    const name = jdoc?.name ?? jp;
    const singleShare = g.total > 0 ? Math.round((g.single / g.total) * 100) : null;
    const bbox =
      Array.isArray(jdoc?.bbox) && jdoc.bbox.length === 4
        ? (jdoc.bbox as [number, number, number, number])
        : null;
    rows.push({
      id: jp,
      label: `${name} — ${g.count} record${g.count === 1 ? "" : "s"}`,
      meta:
        `${g.count} record${g.count === 1 ? "" : "s"} in view` +
        (singleShare !== null ? ` · 1 source: ${singleShare}%` : ""),
      selectId: null,
      frame: bbox
        ? { lat: (bbox[1] + bbox[3]) / 2, lon: (bbox[0] + bbox[2]) / 2, zoom: NATIONAL_ZOOM_MAX + 1 }
        : undefined,
      bbox: bbox ?? undefined,
      dossierHref: hrefs.jurisdictionHref?.(jp) ?? null,
      listHref: null,
      distanceKm: 0,
    });
  }
  rows.sort((a, b) => a.label.localeCompare(b.label));
  return { rows: rows.slice(0, IN_VIEW_MAX), matching };
}

// ------------------------------------------------------- table + download //

/** Sortable keys for the in-view table (the screen-reader table view, J5). */
export type InViewSort = "label" | "technology" | "status" | "distance";

export function sortInViewRows(
  rows: readonly InViewRow[],
  key: InViewSort,
  dir: "asc" | "desc",
): InViewRow[] {
  const d = dir === "desc" ? -1 : 1;
  const by = (r: InViewRow): string | number =>
    key === "distance" ? r.distanceKm
    : key === "technology" ? (r.technology ?? r.meta)
    : key === "status" ? (r.statusText ?? r.meta)
    : r.label;
  return [...rows].sort((a, b) => {
    const av = by(a);
    const bv = by(b);
    const cmp =
      typeof av === "number" && typeof bv === "number"
        ? av - bv
        : String(av).localeCompare(String(bv));
    return cmp === 0 ? a.id.localeCompare(b.id) : d * cmp;
  });
}

/** "Filters (N)" — the active facet-dimension count the peek line carries. */
export function activeFacetCount(f: MapFacetsV2): number {
  return (
    (f.technology.length > 0 ? 1 : 0) +
    (f.status.length > 0 ? 1 : 0) +
    (f.seen ? 1 : 0) +
    (f.vendor.length > 0 ? 1 : 0) +
    (f.operator.length > 0 ? 1 : 0) +
    (f.source.length > 0 ? 1 : 0) +
    (f.jurisdiction.length > 0 ? 1 : 0)
  );
}

/** The mobile sheet's peek line (K1 §4.1): "137 records in view · Filters (2)". */
export function sheetPeekText(count: number, activeFacets: number): string {
  const recs = `${count} record${count === 1 ? "" : "s"} in view`;
  return activeFacets > 0 ? `${recs} · Filters (${activeFacets})` : recs;
}

// --------------------------------------------- 'My location' pan (P37.72) //
// D-K1-7 [B-44] = yes · K1 §4.1/§4.2. The control ONLY pans the map: a
// one-shot browser geolocation read after an explicit click; the position
// never leaves the browser, is never sent to SIG, draws no marker, and
// produces no 'cameras near you' list/count/alert/proximity notice of any
// kind. The written SIG-GOV-017 analysis this pins lives at
// docs/build/reports/p37.72-gov017-analysis/PACKET.md.

/** The zoom floor the pan applies — the site band opens above the national cells (z10). */
export const MY_LOCATION_MIN_ZOOM = 10;

/**
 * The frame the click produces: centre on the position; raise zoom only up
 * to the site-band floor — a pan plus a floor, never a zoom-out and never a
 * fit. The caller's moveend path writes the same zoom-rounded `at=` every
 * pan writes; nothing person-keyed is computed or stored.
 */
export function myLocationTarget(
  lon: number,
  lat: number,
  currentZoom: number,
): { center: [number, number]; zoom: number } {
  return { center: [lon, lat], zoom: Math.max(currentZoom, MY_LOCATION_MIN_ZOOM) };
}

/** The honest failure kinds the click can produce. */
export type GeoFailure = "unsupported" | "denied" | "unavailable" | "timeout";

/**
 * The failure note — honest copy that leaves the map where it is and never
 * nags, never promises, and never keys anything to the viewer ("near you"
 * wording is contract-banned).
 */
export function geoFailureNote(kind: GeoFailure): string {
  switch (kind) {
    case "unsupported":
      return "This browser offers no geolocation — the map stays where it is.";
    case "denied":
      return "Location permission was not granted — the map stays where it is. Nothing was read or sent.";
    case "timeout":
      return "The position request timed out — the map stays where it is.";
    default:
      return "Your position could not be determined — the map stays where it is.";
  }
}

// ------------------------------------------------- MAP-04 place framing //

/** A `[w,s,e,n]` bounds box in degrees (registry/dict shape). */
export type BoundsBox = [number, number, number, number];

/**
 * The map viewport a bounds box resolves to — the same deterministic fold
 * `bbox=` applies in `sig.workspace-state/2` (centre + span-derived zoom
 * clamped to the public tile range). `frame=<jkey>` folds through this —
 * the jkey→bounds table the state module deferred to this row.
 */
export function boundsViewport(
  b: BoundsBox,
): { z: number; lat: number; lon: number } {
  const [w, s, e, n] = b;
  const span = Math.max(e - w, n - s);
  const z = Math.max(0, Math.min(14, Math.floor(Math.log2(360 / Math.max(span, 1e-9)))));
  const d = z <= 5 ? 1 : z <= 10 ? 2 : z <= 14 ? 3 : 4;
  const r = (v: number) => Math.round(v * 10 ** d) / 10 ** d;
  return { z, lat: r((s + n) / 2), lon: r((w + e) / 2) };
}

/** Merge several jkey bounds into one fitBounds box (null when none carry one). */
export function unionBounds(boxes: readonly (BoundsBox | null | undefined)[]): BoundsBox | null {
  const real = boxes.filter((b): b is BoundsBox => Array.isArray(b) && b.length === 4);
  if (real.length === 0) return null;
  return [
    Math.min(...real.map((b) => b[0])),
    Math.min(...real.map((b) => b[1])),
    Math.max(...real.map((b) => b[2])),
    Math.max(...real.map((b) => b[3])),
  ];
}
