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
}

// ------------------------------------------------------------ tile props //

/** The §3.3 tile-property row (sig.map-tiles/2) the `sites` layer carries. */
export interface TileSiteProps {
  rk?: string;
  lb?: string;
  tc?: number;
  op?: string;
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

/** Whether a record passes the active facets (technology/status/seen). */
export function recordPasses(rec: MapRecord, facets: MapFacets): boolean {
  if (facets.technology.length > 0 && !facets.technology.includes(rec.technology)) {
    return false;
  }
  if (facets.status.length > 0 && (rec.status === null || !facets.status.includes(rec.status))) {
    return false;
  }
  if (facets.seen && !seenOverlaps(rec, facets.seen)) return false;
  return true;
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
