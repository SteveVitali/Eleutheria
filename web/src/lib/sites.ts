// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.36 (K1 MAP-05, UXR-18 / SIG-UI-068, SIG-UI-105) — the per-dossier sites
 * lists (`/dossier/<path>/sites/` + `/page/<n>/`) and the `/map/` places
 * table derived over them.
 *
 * The contract (K1 §5, K13's route table "sites files + placement"):
 *
 *   - one paginated list per canonical dossier with ≥ 1 located record —
 *     country, admin-1, county and place levels alike (D-K4-3 thresholds
 *     govern which dossiers exist at all);
 *   - a record resolves to the DEEPEST published dossier its placement key
 *     chain reaches: `us.census.geoid.place:4064000` →
 *     `usa/ok/oklahoma-city-4064000` when that page exists, else the nearest
 *     published ancestor (`usa/ok`, `usa`). A key no published ancestor
 *     claims is counted under `unresolved` — never guessed into a
 *     jurisdiction;
 *   - every resolved record appears on exactly ONE list — the row anchor
 *     `…/sites/…#<key>` is the interim site-record link target (UXR-18):
 *     until `/r/<pub>/` is publicly exposed (G2 ACT-24) a site link targets
 *     its row here and never 404s;
 *   - ≤ 100 rows per page, paginated BY PATH (`sites/page/<n>/`) so static
 *     hosting needs no query strings;
 *   - coordinates print only at the published precision — a tier-3 or
 *     no-point record shows its precision words, never a finer point the
 *     release does not publish;
 *   - the list is the cross-compartment reading view: rows group by licence
 *     compartment with a licence line per group, and the CSV download
 *     carries `#`-comment licence provenance lines (ADR-224's convention).
 *
 * This module is pure data + logic — no DOM, no rendering — so every rule is
 * unit-testable in isolation from the Astro pages.
 */

import {
  technologyLabel,
  type MapAsset,
  type SensitivityTier,
} from "./map";
import type { Dossier } from "./dossier";
import type { DossierIndexRow, JurisdictionKeyMapRow } from "./data";

// ---------------------------------------------------------------- constants //

/** K1 §5: ≤ 100 rows per site-list page. */
export const SITE_PAGE_SIZE = 100;

/** The honest cell a site-list column renders when the wire carries no value. */
export const NOT_STATED = "not stated";

// ------------------------------------------------------------------- model //

/** One sites-list row — the published facts a record may show, nothing more. */
export interface SiteRow {
  /** The record key — also the row's `#<key>` anchor (UXR-18). */
  id: string;
  label: string;
  technology: string;
  operator: string | null;
  /** Contributing source labels — `null` when the wire carries none. */
  sources: string[] | null;
  firstSeen: string | null;
  lastSeen: string | null;
  status: string | null;
  tier: SensitivityTier;
  precision: string;
  /** The published point — already suppressed to `null` when the tier or the
   * record publishes none, so a renderer can never leak a finer value. */
  lat: number | null;
  lon: number | null;
  compartment: string | null;
  licence: string | null;
  /** The dossier slug path this row resolved to. */
  dossierSlug: string;
  /** The contested-location flag — the places table's contested column. */
  contested: boolean;
}

/** One dossier's emitted sites list. */
export interface SiteList {
  slug: string;
  rows: SiteRow[];
  /** Rows with a publishable point (the "located" the MUST binds on). */
  located: number;
  /** Rows with no publishable point. */
  noPoint: number;
  contested: number;
  /** Distinct compartments present, first-seen order — the group order. */
  compartments: (string | null)[];
  pages: number;
}

/**
 * The resolved model: per-dossier lists plus the honestly-counted set that
 * resolved to no published dossier (a record is never silently dropped).
 */
export interface SitesModel {
  /** slug → list, in first-resolution order. */
  lists: Map<string, SiteList>;
  /** Resolved to no published dossier — counted, never listed. */
  unresolved: SiteRow[];
}

/**
 * The jurisdiction lookup the resolver walks — jkey → published slug path,
 * jkey → parent jkey. Built additively from every source the build carries:
 * the export's `sig.jurisdiction-key-map/1` rows, the keyed dossiers' own
 * `jurisdiction_key`/`chain` fields, and the `sig.dossier-index/2` rows'
 * `parent_jkey` links. No single source is required — a pre-keyed build
 * resolves through the dossiers alone, and `jurisdictionSlug` (the legacy
 * flat-slug fallback) maps whatever remains.
 */
export interface JurisdictionLookup {
  slugByJkey: Map<string, string>;
  parentByJkey: Map<string, string | null>;
}

/** Build the lookup from the data layer's three sources (all optional). */
export function buildJurisdictionLookup(
  dossiers: readonly Dossier[],
  indexRows: readonly DossierIndexRow[],
  keyMap: ReadonlyMap<string, JurisdictionKeyMapRow> | null,
): JurisdictionLookup {
  const slugByJkey = new Map<string, string>();
  const parentByJkey = new Map<string, string | null>();
  const put = (jkey: string | null | undefined, slug: string | null | undefined): void => {
    if (jkey && slug && !slugByJkey.has(jkey)) slugByJkey.set(jkey, slug);
  };
  const parent = (jkey: string | null | undefined, p: string | null | undefined): void => {
    if (jkey && !parentByJkey.has(jkey)) parentByJkey.set(jkey, p ?? null);
  };
  for (const d of dossiers) {
    put(d.jurisdiction_key, d.slug);
    // The root-first chain carries each ancestor's jkey (+ slug where the
    // ancestor has a page) — parent links for every element, keyed and not.
    const chain = d.chain ?? [];
    for (let i = 0; i < chain.length; i += 1) {
      const link = chain[i]!;
      put(link.jkey, link.slug_path ?? (i === chain.length - 1 ? d.slug : null));
      parent(link.jkey, i > 0 ? chain[i - 1]!.jkey : null);
    }
    if (d.jurisdiction_key && d.parent_jkey !== undefined) {
      parent(d.jurisdiction_key, d.parent_jkey ?? null);
    }
  }
  for (const r of indexRows) {
    put(r.jkey, r.slug_path ?? r.slug);
    parent(r.jkey, r.parent_jkey ?? null);
  }
  for (const [jkey, row] of keyMap ?? []) {
    put(jkey, row.slug_path);
    parent(jkey, row.parent_jkey ?? null);
  }
  return { slugByJkey, parentByJkey };
}

/**
 * The key a record resolves through (P36.36): the explicit `jurisdictionKey`
 * when the wire carries it, else `jurisdiction` when it is already a
 * `scheme:value` key (the keyed export's wire shape), else `null`.
 */
export function assetJurisdictionKey(asset: MapAsset): string | null {
  if (asset.jurisdictionKey) return asset.jurisdictionKey;
  return asset.jurisdiction.includes(":") ? asset.jurisdiction : null;
}

/**
 * Resolve a record to its deepest published dossier slug path — the key's own
 * page when published, else the nearest published ancestor, else `null`.
 */
export function resolveDossierSlug(
  asset: MapAsset,
  lookup: JurisdictionLookup,
): string | null {
  let jkey = assetJurisdictionKey(asset);
  const seen = new Set<string>();
  while (jkey !== null && !seen.has(jkey)) {
    seen.add(jkey);
    const slug = lookup.slugByJkey.get(jkey);
    if (slug) return slug;
    jkey = lookup.parentByJkey.get(jkey) ?? null;
  }
  return null;
}

/** Whether the record's published point may print (§19.4 — never finer). */
export function publishablePoint(asset: MapAsset): boolean {
  return asset.tier !== 3 && asset.lat !== null && asset.lon !== null;
}

/**
 * The `#<key>` fragment the row answers to (SIG-UI-068). The record id is
 * verbatim — an HTML5 `id` may carry `:` and every site link targets it.
 */
export function siteAnchor(id: string): string {
  return id;
}

/** Root-relative path fragments for `withBase()` (never a leading `/` — the
 * check:paths gate counts only literal sites). */
export function dossierSitesPath(slug: string): string {
  return `dossier/${slug}/sites/`;
}
export function dossierSitesPagePath(slug: string, page: number): string {
  return page <= 1 ? dossierSitesPath(slug) : `dossier/${slug}/sites/page/${page}/`;
}
export function dossierSitesCsvPath(slug: string): string {
  return `dossier/${slug}/sites/index.csv`;
}
export function dossierSitesHref(slug: string, id: string): string {
  return `${dossierSitesPath(slug)}#${siteAnchor(id)}`;
}

/** Shape a wire asset into its published row — the tier guard applied here so
 * no renderer can print a point the release does not publish. */
export function siteRowOf(asset: MapAsset, dossierSlug: string): SiteRow {
  const point = publishablePoint(asset);
  return {
    id: asset.id,
    label: asset.label,
    technology: technologyLabel(asset),
    operator: asset.operator ?? null,
    sources: asset.sources && asset.sources.length > 0 ? [...asset.sources] : null,
    firstSeen: asset.firstSeen ?? null,
    lastSeen: asset.lastSeen ?? null,
    status: asset.status ?? null,
    tier: asset.tier,
    precision: asset.precision,
    lat: point ? asset.lat : null,
    lon: point ? asset.lon : null,
    compartment: asset.compartment ?? null,
    licence: asset.licence ?? null,
    dossierSlug,
    contested: asset.locationAbsence === "UNRESOLVED" || asset.status === "contested",
  };
}

/** Derive the whole sites model over the map layer's assets. */
export function buildSitesModel(
  assets: readonly MapAsset[],
  lookup: JurisdictionLookup,
): SitesModel {
  const lists = new Map<string, SiteList>();
  const unresolved: SiteRow[] = [];
  const acc = new Map<string, SiteRow[]>();
  for (const asset of assets) {
    const slug = resolveDossierSlug(asset, lookup);
    if (slug === null) {
      unresolved.push(siteRowOf(asset, "(unresolved)"));
      continue;
    }
    const rows = acc.get(slug) ?? [];
    rows.push(siteRowOf(asset, slug));
    acc.set(slug, rows);
  }
  for (const [slug, rows] of acc) {
    const located = rows.filter((r) => r.lat !== null).length;
    lists.set(slug, {
      slug,
      rows,
      located,
      noPoint: rows.length - located,
      contested: rows.filter((r) => r.contested).length,
      compartments: [...new Set(rows.map((r) => r.compartment))],
      pages: Math.ceil(rows.length / SITE_PAGE_SIZE),
    });
  }
  return { lists, unresolved };
}

/**
 * The lists that MUST exist (SIG-UI-105): every dossier with ≥ 1 located
 * record gets a paginated list. Rows are sorted deterministically — label,
 * then id — so pagination is stable and byte-deterministic.
 */
export function emittedSiteLists(model: SitesModel): SiteList[] {
  return [...model.lists.values()]
    .filter((l) => l.located > 0)
    .map((l) => ({
      ...l,
      rows: [...l.rows].sort(
        (a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id),
      ),
    }))
    .sort((a, b) => a.slug.localeCompare(b.slug));
}

/** The page slice for `page` (1-based). `pages` is the honest total. */
export function sitePage(list: SiteList, page: number): { rows: SiteRow[]; first: number; last: number } {
  const start = (page - 1) * SITE_PAGE_SIZE;
  const rows = list.rows.slice(start, start + SITE_PAGE_SIZE);
  return { rows, first: rows.length ? start + 1 : 0, last: start + rows.length };
}

// ------------------------------------------------------------- the CSV //

/**
 * Escape one CSV cell — the RFC-4180 doubling rule; `#` comment lines are
 * emitted by `sitesCsv` itself, never inside a cell.
 */
export function csvCell(value: string | number | null): string {
  if (value === null) return "";
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * The "Download this view" CSV (K13 capstone O3) — the jurisdiction's FULL
 * list (never just the page slice), with ADR-224's `#`-comment licence
 * provenance lines leading so the rows are never read decontextualised from
 * their licence. Grouped by compartment exactly like the HTML list.
 */
export function sitesCsv(
  list: SiteList,
  meta: { dossierName: string; asOf: string; licence?: string | null },
): string {
  const lines: string[] = [
    `# SIG dossier sites list — ${meta.dossierName}`,
    `# route: /${dossierSitesPath(list.slug)} (interim site-record link target, UXR-18)`,
    `# data as of: ${meta.asOf}`,
    `# rows: ${list.rows.length} (${list.located} located, ${list.noPoint} with no published point)`,
    ...(meta.licence ? [`# licence: ${meta.licence}`] : []),
    "# compartments: rows group by licence compartment; each group's licence names its own terms",
  ];
  const header = [
    "record",
    "label",
    "technology",
    "operator",
    "sources",
    "first_seen",
    "last_seen",
    "status",
    "tier",
    "precision",
    "latitude",
    "longitude",
    "compartment",
    "licence",
  ];
  lines.push(header.join(","));
  for (const comp of list.compartments) {
    if (list.compartments.length > 1) {
      lines.push(`# compartment: ${comp ?? "unassigned"}`);
    }
    for (const r of list.rows.filter((row) => row.compartment === comp)) {
      lines.push(
        [
          csvCell(r.id),
          csvCell(r.label),
          csvCell(r.technology),
          csvCell(r.operator ?? NOT_STATED),
          csvCell(r.sources ? r.sources.join("; ") : NOT_STATED),
          csvCell(r.firstSeen ?? NOT_STATED),
          csvCell(r.lastSeen ?? NOT_STATED),
          csvCell(r.status ?? NOT_STATED),
          csvCell(r.tier),
          csvCell(r.precision),
          csvCell(r.lat),
          csvCell(r.lon),
          csvCell(r.compartment ?? NOT_STATED),
          csvCell(r.licence ?? NOT_STATED),
        ].join(","),
      );
    }
  }
  return `${lines.join("\n")}\n`;
}

// ------------------------------------------------- the /map/ places table //

/** One places-table row (K1 §5 item 4). */
export interface PlaceTableRow {
  slug: string;
  /** Display name (the dossier's own registry name, never a raw key). */
  name: string;
  /** The K4 registry level — country | state_province | county | municipality. */
  level: string | null;
  /** The country-level ancestor slug this row groups under. */
  countrySlug: string;
  countryName: string;
  located: number;
  noPoint: number;
  contested: number;
  /** Distinct source labels across rows — `null` when no row carries any. */
  sources: number | null;
  /** Rows with exactly one source / all rows — `null` when not computable. */
  singleSourceShare: number | null;
  /** True when the dossier's sites list is emitted (≥ 1 located row). */
  hasSitesList: boolean;
}

/** Grouped places-table section — one per country. */
export interface PlaceTableGroup {
  countrySlug: string;
  countryName: string;
  rows: PlaceTableRow[];
}

/**
 * Aggregate the places table over the sites model + the dossier registry.
 * Rows cover every dossier the model resolved records to; grouping follows
 * the dossier's root-first chain (the country-level ancestor, falling back
 * to the dossier itself for a flat row). K1's ≤ 70-row bound applies at the
 * caller (`placeTableGroups` is the full set; `PLACES_TABLE_MAX` bounds it).
 */
export const PLACES_TABLE_MAX = 70;

export interface PlaceTable {
  groups: PlaceTableGroup[];
  totalRows: number;
  /** Rows past PLACES_TABLE_MAX — the honest truncation count. */
  truncated: number;
  /** Records that resolved to no published dossier — counted, never hidden. */
  unresolvedRecords: number;
}

export function buildPlaceTable(
  model: SitesModel,
  dossiers: readonly Dossier[],
): PlaceTable {
  const bySlug = new Map(dossiers.map((d) => [d.slug, d]));
  const rows: PlaceTableRow[] = [];
  for (const list of model.lists.values()) {
    const d = bySlug.get(list.slug);
    const root = d?.chain?.[0];
    const allSourced = list.rows.every((r) => r.sources !== null);
    const sourceSet = new Set<string>();
    for (const r of list.rows) for (const s of r.sources ?? []) sourceSet.add(s);
    const singleSource = list.rows.filter((r) => r.sources?.length === 1).length;
    rows.push({
      slug: list.slug,
      name: d?.display_name ?? d?.name ?? d?.subject_label ?? list.slug,
      level: d?.level ?? null,
      countrySlug: root?.slug_path ?? list.slug,
      countryName: root?.name ?? d?.display_name ?? d?.name ?? list.slug,
      located: list.located,
      noPoint: list.noPoint,
      contested: list.contested,
      sources: allSourced && list.rows.length > 0 ? sourceSet.size : null,
      singleSourceShare:
        allSourced && list.rows.length > 0
          ? singleSource / list.rows.length
          : null,
      hasSitesList: list.located > 0,
    });
  }
  const levelOrder = (l: string | null): number =>
    l === "country" ? 0 : l === "state_province" ? 1 : l === "county" ? 2 : l === "municipality" ? 3 : 4;
  rows.sort(
    (a, b) =>
      a.countryName.localeCompare(b.countryName) ||
      levelOrder(a.level) - levelOrder(b.level) ||
      a.name.localeCompare(b.name) ||
      a.slug.localeCompare(b.slug),
  );
  const shown = rows.slice(0, PLACES_TABLE_MAX);
  const groups: PlaceTableGroup[] = [];
  for (const row of shown) {
    let g = groups[groups.length - 1];
    if (!g || g.countrySlug !== row.countrySlug) {
      g = { countrySlug: row.countrySlug, countryName: row.countryName, rows: [] };
      groups.push(g);
    }
    g.rows.push(row);
  }
  return {
    groups,
    totalRows: rows.length,
    truncated: Math.max(0, rows.length - PLACES_TABLE_MAX),
    unresolvedRecords: model.unresolved.length,
  };
}
