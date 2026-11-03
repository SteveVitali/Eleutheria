// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.52 (R11-K13-DSRC-02; SIG-DSRC-001…006/008/009 owner; SIG-UI-039/040,
 * SIG-ENG-042 cited; K5 §4–§7, K13 §2.2) — the dossier-source explorer model.
 *
 * The `sig.dossier-sources/1` contribution artifact (P35.44 / DSRC-01 emits it
 * under `web/dossier_sources/<slug-path>.json`; one computation feeds BOTH
 * directions — this page and the `/sources/<id>/` `contributions[]` mirror, so
 * parity SIG-DSRC-008 holds by construction) renders:
 *
 *   - "Where this comes from" on every dossier (K5 §4.1) — the totals line, the
 *     top-5 contributing sources and the explorer link;
 *   - `/dossier/<path>/sources/` — the explorer (K5 §4.2): the contribution
 *     table, one `<details>` per source, the over-time chart + its `<table>`
 *     twin, the agree/disagree block, placement, downloads and cite;
 *   - the `index.json` JSON twin — the artifact served verbatim (SIG-DSRC-009);
 *   - pre-rendered GET sort routes `…/sources/sort/<key>/` — only for dossiers
 *     with > SORT_ROUTE_THRESHOLD sources (K5 §7); pagination at
 *     PAGE_SIZE rows/page for sets above it (K5-P6, K9 §6.1 precedent);
 *   - "Previously contributed" below the table (D-K5-3 = yes): withdrawn,
 *     disappeared and never-re-asserted sources with their dates and reason.
 *
 * Honest-absence vocabulary (K5-P4): `run_level_only`, `not_recorded`,
 * `not_evaluable`, `not_typed` — the page never shows 0 for "not measured".
 */

import type { ProvenanceSummary } from "./provenance";
import { dossierPath } from "./dossier";
import { artifactHref, type FigureSpec, type FigureTarget } from "./figures";

export const DOSSIER_SOURCES_SCHEMA = "sig.dossier-sources/1" as const;

// ---------------------------------------------------------------------------
// The artifact contract — the fields the render reads (the emitted document
// carries more; validators require only what is consumed).
// ---------------------------------------------------------------------------

export type AbsenceToken = { not_recorded?: string } & { not_evaluable?: string };

export interface SeenInstant {
  at: string | null;
  run_id?: string | null;
}
export type SeenField = SeenInstant | AbsenceToken;
export type LatestRun =
  | { run_id: string; finished_at: string | null; status: string | null }
  | AbsenceToken;

export interface SourceSeriesPoint {
  period: string;
  records_first_seen: number;
  claims_first_seen: number;
  claims_resighted: number;
}

export interface DossierSourceRow {
  source_id: string;
  name: string;
  publisher: string | null;
  publisher_type: string | null;
  lifecycle: string | null;
  source_page: string;
  runs_page: string;
  licence: {
    spdx: string | null;
    compartment: string | null;
    compartments?: string[];
    attribution: string | null;
  };
  records: number;
  records_placed: number;
  /** The source's records as a fraction of the dossier's (SIG-DSRC-002). */
  share: number;
  located_by_point: number;
  placed_by_declared: number;
  claims: number;
  claims_by_predicate: Record<string, number>;
  records_by_entity_type: Record<string, number>;
  records_by_technology: Record<string, number> | "not_typed";
  placement_checks: Record<string, number>;
  first_seen: SeenField;
  last_seen: SeenField;
  sightings: "per_run" | "run_level_only" | string;
  latest_run: LatestRun;
  freshness_state: string;
  not_reasserted_in_latest_complete_run: number | AbsenceToken;
  coordinate_conflicts_intra_source: number;
  declared_here_located_elsewhere: number;
  contradictions: string[];
  series: SourceSeriesPoint[];
  downloads: DossierDownloadFile[];
  known_issues: string[];
}

// ---------------------------------------------------------------------------
// P36.53 (DSRC-03 / K5 §6, SIG-DSRC-007): the per-dossier download entries —
// `by-dossier/<slug>/<compartment>/` slices materialised at country/admin-1
// (D-K5-1 "as recommended"; the unplaced sentinel materialises too) and the
// DuckDB/API recipe block every dossier carries (county/place readers slice
// the national files on the statements' placement columns — never a 4×
// materialisation).
// ---------------------------------------------------------------------------

export interface DossierDownloadFile {
  path: string;
  name: string;
  format: string;
  bytes: number;
  sha256: string;
  href: string;
  rows?: number;
}

export interface DossierDownloadCompartment {
  compartment: string;
  license: string;
  directory: string;
  files: DossierDownloadFile[];
}

export interface DossierDownloadRecipes {
  materialised: boolean;
  level: string | null;
  duckdb: {
    note: string;
    files: {
      compartment: string;
      statements: string | AbsenceToken;
      sites: string;
    }[];
  };
  api: { endpoint: string; note: string };
  note?: string;
}

export interface DossierSourcesFigure {
  figure_id: string;
  label: string;
  value: number;
  definition: string;
  artifact: string;
  pointer: string;
  by_source: { source_id: string; value: number }[];
  sum_rule: "sum" | "distinct" | string;
  sum_disclosure?: string;
  interval?: { lower: number; upper: number; declared_distance_m?: number };
  display?: string;
}

export interface DossierSourcesProvenance {
  artifact_count: number;
  tier_distribution: Record<string, number>;
  sources_with_published_claims: number;
  independent_lineages: number | AbsenceToken;
  date_range: { earliest: string; latest: string } | null;
  rules_applied: string[];
  human_review_status: string;
  scope?: string;
}

export interface DossierSourcesDoc {
  schema: string;
  release: { label: string; publication_id: string | null; as_of_world: string };
  jurisdiction: {
    jkey: string | null;
    slug_path: string;
    name: string;
    level: string | null;
    chain?: string[];
    boundary_vintage?: string | null;
    unplaced?: boolean;
  };
  definitions: Record<string, string>;
  totals: {
    records: number;
    records_placed: number;
    located_by_point: number;
    placed_by_declared: number;
    claims: number;
    sources: number;
    compartments: string[];
    first_seen_at: string | null;
    last_seen_at: string | null;
    claims_by_predicate: Record<string, number>;
    records_by_entity_type: Record<string, number>;
    records_by_technology: Record<string, number> | "not_typed";
    coordinate_conflicts_intra_source: number;
    declared_here_located_elsewhere: number;
    located_here_declared_elsewhere: number;
    contradictions_open: number;
    cross_source_colocated_candidates?: number | AbsenceToken;
  };
  provenance_summary: DossierSourcesProvenance;
  figures: DossierSourcesFigure[];
  sources: DossierSourceRow[];
  cross_source: {
    colocated_pairs: number | AbsenceToken;
    contradictions: { contradiction_id: string }[];
  };
  placement: {
    rules?: string;
    by_basis: Record<string, number>;
    declared_elsewhere_located_here: { jkey: string; records: number }[];
    declared_here_located_elsewhere: { jkey: string; records: number }[];
  };
  runs_file: string | null;
  downloads: DossierDownloadCompartment[];
  download_recipes?: DossierDownloadRecipes;
}

/** Fail-closed shape check — a malformed artifact fails the build (SIG-ENG-042). */
export function isDossierSourcesDoc(o: unknown, where = "artifact"): o is DossierSourcesDoc {
  if (o === null || typeof o !== "object") return false;
  const d = o as Record<string, unknown>;
  if (d.schema !== DOSSIER_SOURCES_SCHEMA) {
    throw new Error(`${where}: schema ${String(d.schema)} — expected ${DOSSIER_SOURCES_SCHEMA}`);
  }
  if (!Array.isArray(d.sources) || !Array.isArray(d.figures)) return false;
  const t = d.totals as Record<string, unknown> | undefined;
  const p = d.provenance_summary as Record<string, unknown> | undefined;
  const j = d.jurisdiction as Record<string, unknown> | undefined;
  return (
    typeof t?.records === "number" &&
    typeof t?.claims === "number" &&
    typeof t?.sources === "number" &&
    typeof p?.artifact_count === "number" &&
    typeof p?.sources_with_published_claims === "number" &&
    typeof j?.slug_path === "string" &&
    typeof j?.name === "string" &&
    d.sources.every(
      (s) =>
        s !== null &&
        typeof s === "object" &&
        typeof (s as Record<string, unknown>).source_id === "string" &&
        typeof (s as Record<string, unknown>).name === "string" &&
        typeof (s as Record<string, unknown>).records === "number" &&
        typeof (s as Record<string, unknown>).claims === "number" &&
        Array.isArray((s as Record<string, unknown>).series),
    )
  );
}

// ---------------------------------------------------------------------------
// The dossier-scope "How we know this" (SIG-DSRC-004 + K5 §5): the artifact's
// `provenance_summary` mapped onto the SIG-UI-044 six-component shape — the
// figures resolve INSIDE this artifact (`/provenance_summary/…`), never under
// `/surfaces/site` (a site-wide block renders labelled Site-wide instead).
// ---------------------------------------------------------------------------

/** Map `provenance_summary` onto the HWKT `ProvenanceSummary` contract. */
export function dossierSourcesProvenance(doc: DossierSourcesDoc): ProvenanceSummary {
  const p = doc.provenance_summary;
  return {
    artifact_count: p.artifact_count,
    tier_distribution: p.tier_distribution,
    source_independence_count: p.sources_with_published_claims,
    // K5 §5's honest label: the named predicate, never "independent sources".
    source_label: "Sources with published claims",
    date_range: p.date_range,
    rules_applied: p.rules_applied,
    human_review_status:
      p.human_review_status === "reviewed" || p.human_review_status === "partially_reviewed"
        ? p.human_review_status
        : "unreviewed",
  };
}

// ---------------------------------------------------------------------------
// Field accessors — the typed absences render as labels, never guesses.
// ---------------------------------------------------------------------------

/** The instant a "first/last seen" field carries, or `null` for an absence. */
export function seenAt(field: SeenField): string | null {
  return "at" in field ? field.at : null;
}
export function seenRun(field: SeenField): string | null {
  return "at" in field ? (field.run_id ?? null) : null;
}
/** The absence reason a `not_recorded`/`not_evaluable` field carries. */
export function absenceReason(field: unknown): string | null {
  if (field !== null && typeof field === "object") {
    const f = field as AbsenceToken;
    return f.not_recorded ?? f.not_evaluable ?? null;
  }
  return null;
}
/** `latest_run` fields — `null` when the artifact records none. */
export function latestRun(s: DossierSourceRow): {
  run_id: string;
  finished_at: string | null;
  status: string | null;
} | null {
  return "run_id" in s.latest_run ? s.latest_run : null;
}

// ---------------------------------------------------------------------------
// "Previously contributed" (D-K5-3 = yes): a source that no longer contributes
// shows below the contribution table with its dates and its reason.
// ---------------------------------------------------------------------------

const DISAPPEARED = /disappeared|withdrawn/i;

/** The reason a source sits in the "previously contributed" block, or null. */
export function previousContributionReason(s: DossierSourceRow): string | null {
  if (s.lifecycle === "withdrawn") return "withdrawn from the published record";
  if (s.lifecycle === "gated" || s.lifecycle === "refused") {
    return `not published — the ${s.lifecycle} gate closed after these records`;
  }
  if (DISAPPEARED.test(s.freshness_state)) return `upstream ${s.freshness_state}`;
  if (
    typeof s.not_reasserted_in_latest_complete_run === "number" &&
    s.claims > 0 &&
    s.not_reasserted_in_latest_complete_run === s.claims
  ) {
    return "not re-asserted in the latest complete run";
  }
  return null;
}

/** The currently-contributing sources (the sortable contribution table). */
export function contributingSources(doc: DossierSourcesDoc): DossierSourceRow[] {
  return doc.sources.filter((s) => previousContributionReason(s) === null);
}
/** The previously-contributing sources (D-K5-3's below-the-table block). */
export function previousContributors(doc: DossierSourcesDoc): DossierSourceRow[] {
  return doc.sources.filter((s) => previousContributionReason(s) !== null);
}

// ---------------------------------------------------------------------------
// Sort + pagination (K5 §4.2/§7 + K9 §6.1 precedent)
// ---------------------------------------------------------------------------

export type DsrcSortKey =
  | "records"
  | "first-seen"
  | "last-seen"
  | "freshness"
  | "conflicts"
  | "name";

export const DSRC_SORT_KEYS: readonly DsrcSortKey[] = [
  "records",
  "first-seen",
  "last-seen",
  "freshness",
  "conflicts",
  "name",
];

/** The sort-route threshold — sort routes mint only above it (K5 §4.2). */
export const SORT_ROUTE_THRESHOLD = 25;
/** Rows per table page (K5-P6: ≤50). */
export const DSRC_PAGE_SIZE = 50;

const FRESHNESS_ORDER = [
  "on_time",
  "late",
  "overdue",
  "last_run_failed",
  "never_run",
  "not_scheduled",
  "one_time_load",
  "not_applicable",
  "not_recorded",
];

const nameKey = (s: string): string => s.toLowerCase();

function rank(order: readonly string[], v: string): number {
  const i = order.indexOf(v);
  return i === -1 ? order.length : i;
}

/** The comparable a sort key reads — `null` = an absence token, sorted LAST
 *  in both directions (K9 C-3). */
export function sortValue(s: DossierSourceRow, key: DsrcSortKey): string | number | null {
  switch (key) {
    case "records":
      return s.records;
    case "first-seen":
      return seenAt(s.first_seen);
    case "last-seen":
      return seenAt(s.last_seen);
    case "freshness":
      return rank(FRESHNESS_ORDER, s.freshness_state);
    case "conflicts":
      return s.coordinate_conflicts_intra_source + s.contradictions.length;
    case "name":
      return nameKey(s.name);
  }
}

/** Sort the contribution rows — absences last in BOTH directions, ties on name. */
export function sortSources(
  rows: readonly DossierSourceRow[],
  key: DsrcSortKey,
): DossierSourceRow[] {
  return [...rows].sort((a, b) => {
    const va = sortValue(a, key);
    const vb = sortValue(b, key);
    if ((va === null) !== (vb === null)) return va === null ? 1 : -1;
    if (va !== null && vb !== null) {
      // First-seen/last-seen sort ascending by default is wrong for a
      // contribution view — the design orders every key descending except
      // name (K5 §7: sort routes, default by records).
      const cmp =
        typeof va === "number" && typeof vb === "number"
          ? vb - va // numbers: largest first (records, conflicts)
          : key === "name"
            ? String(va).localeCompare(String(vb))
            : String(vb).localeCompare(String(va)); // instants: newest first
      if (cmp !== 0) return cmp;
    }
    return nameKey(a.name).localeCompare(nameKey(b.name)) || a.source_id.localeCompare(b.source_id);
  });
}

/** Slice the sorted rows to `page` (1-based); throws outside 1..pages. */
export function paginateSources(
  rows: readonly DossierSourceRow[],
  page: number,
  size: number = DSRC_PAGE_SIZE,
): { rows: DossierSourceRow[]; page: number; pages: number; total: number; first: number; last: number } {
  const total = rows.length;
  const pages = Math.max(1, Math.ceil(total / size));
  if (page < 1 || page > pages) {
    throw new Error(`dossier-sources: page ${page} outside 1..${pages} (SIG-ENG-042)`);
  }
  const start = (page - 1) * size;
  const slice = rows.slice(start, start + size);
  return { rows: slice, page, pages, total, first: start + 1, last: start + slice.length };
}

// ---------------------------------------------------------------------------
// Routes (sans leading slash — render joins withBase())
// ---------------------------------------------------------------------------

/** `/dossier/<path>/sources/` — the explorer index (records sort, page 1). */
export function dossierSourcesPath(slug: string): string {
  return `dossier/${slug}/sources/`;
}
/** `/dossier/<path>/downloads/` — the per-dossier downloads page (P36.53). */
export function dossierDownloadsPath(slug: string): string {
  return `dossier/${slug}/downloads/`;
}
/** `/dossier/<path>/sources/index.json` — the JSON twin. */
export function dossierSourcesJsonPath(slug: string): string {
  return `dossier/${slug}/sources/index.json`;
}
/** A continuation page of the explorer index (`page/<n>/`). */
export function dossierSourcesPagePath(slug: string, page: number): string {
  return page <= 1
    ? dossierSourcesPath(slug)
    : `dossier/${slug}/sources/page/${page}/`;
}
/** A pre-rendered sort route (`…/sources/sort/<key>/`). */
export function dossierSourcesSortPath(slug: string, key: DsrcSortKey): string {
  return `dossier/${slug}/sources/sort/${key}/`;
}
/** A continuation page of a sort route (`…/sort/<key>/page/<n>/`). */
export function dossierSourcesSortPagePath(slug: string, key: DsrcSortKey, page: number): string {
  return page <= 1
    ? dossierSourcesSortPath(slug, key)
    : `dossier/${slug}/sources/sort/${key}/page/${page}/`;
}

// ---------------------------------------------------------------------------
// The over-time model (K5 §4.2 "Over time") — monthly `records_first_seen`
// per source, top 8 + an "other" bucket, the chart's table twin carries the
// same numbers (SIG-DSRC-006: the SVG is never the only carrier).
// ---------------------------------------------------------------------------

export interface OverTimeSeries {
  source_id: string;
  name: string;
  /** monthly values aligned to `OverTimeModel.periods` */
  values: number[];
}
export interface OverTimeModel {
  periods: string[];
  series: OverTimeSeries[];
  /** column totals per period — the chart's scale + the table's footer */
  totals: number[];
}

/** Sources the chart draws individually — the rest fold into "other". */
export const OVER_TIME_TOP = 8;

/** Compose the monthly first-seen-records series model. */
export function overTimeModel(doc: DossierSourcesDoc): OverTimeModel {
  const periods = Array.from(
    new Set(doc.sources.flatMap((s) => s.series.map((p) => p.period))),
  ).sort();
  const byTotal = [...doc.sources].sort((a, b) => {
    const ta = a.series.reduce((n, p) => n + p.records_first_seen, 0);
    const tb = b.series.reduce((n, p) => n + p.records_first_seen, 0);
    return tb - ta || nameKey(a.name).localeCompare(nameKey(b.name));
  });
  const top = byTotal.slice(0, OVER_TIME_TOP);
  const rest = byTotal.slice(OVER_TIME_TOP);
  const rowFor = (s: DossierSourceRow): OverTimeSeries => {
    const m = new Map(s.series.map((p) => [p.period, p.records_first_seen]));
    return {
      source_id: s.source_id,
      name: s.name,
      values: periods.map((p) => m.get(p) ?? 0),
    };
  };
  const series = top.map(rowFor);
  if (rest.length > 0) {
    series.push({
      source_id: "",
      name: `Other (${rest.length} source${rest.length === 1 ? "" : "s"})`,
      values: periods.map((p) =>
        rest.reduce((n, s) => n + (s.series.find((x) => x.period === p)?.records_first_seen ?? 0), 0),
      ),
    });
  }
  const totals = periods.map((_, i) => series.reduce((n, s) => n + s.values[i]!, 0));
  return { periods, series, totals };
}

// ---------------------------------------------------------------------------
// Routes-table helpers shared by page + print/block
// ---------------------------------------------------------------------------

/** The dossier's own page path (dossierPath's leading-slash-free form). */
export function dossierHref(slug: string): string {
  return dossierPath(slug).replace(/^\//, "");
}

// ---------------------------------------------------------------------------
// The figures[] entries the two surfaces register (UXR-34). Every material
// numeral is a contract figure over `web/dossier_sources/<slug>.json` —
// pointers resolve inside the artifact itself.
// ---------------------------------------------------------------------------

export function dsrcArtifact(slug: string): string {
  return `web/dossier_sources/${slug}.json`;
}

/** The HWKT pointerBase for a dossier-sources provenance block — a JSON
 * pointer inside `web/dossier_sources/<slug>.json`, never a route. */
export const DSRC_PROVENANCE_POINTER_BASE = "/provenance_summary";

const dsrcTargets = (slug: string): FigureTarget[] => [
  { kind: "rows", label: "artifact JSON", href: artifactHref(dsrcArtifact(slug)) },
  {
    kind: "breakdown",
    label: "per-source breakdown",
    href: `${dossierSourcesPath(slug)}#dsrc-table-heading`,
  },
  {
    kind: "provenance",
    label: "dossier provenance",
    href: `${dossierPath(slug).replace(/^\//, "")}#hwkt-heading`,
  },
];

/** The material figure specs the explorer + the dossier block share. */
export function dsrcFigureSpecs(doc: DossierSourcesDoc): FigureSpec[] {
  const slug = doc.jurisdiction.slug_path;
  const artifact = dsrcArtifact(slug);
  const href = artifactHref(artifact);
  const t = dsrcTargets(slug);
  const spec = (
    id: string,
    value: number | string,
    pointer: string,
    definition: string,
  ): FigureSpec => ({
    id,
    class: "dossier",
    value,
    artifact,
    pointer,
    definition,
    href,
    breakdown: `#fig-${id}`,
    targets: t,
  });
  return [
    spec("dsrc-records", doc.totals.records, "/totals/records", `${dossierSourcesPath(slug)}#dsrc-def-records`),
    spec("dsrc-claims", doc.totals.claims, "/totals/claims", `${dossierSourcesPath(slug)}#dsrc-def-claims`),
    spec("dsrc-sources", doc.totals.sources, "/totals/sources", `${dossierSourcesPath(slug)}#dsrc-def-sources`),
    spec("dsrc-records-placed", doc.totals.located_by_point, "/totals/located_by_point", `${dossierSourcesPath(slug)}#dsrc-def-located_by_point`),
    spec(
      "dsrc-conflicts",
      doc.totals.coordinate_conflicts_intra_source,
      "/totals/coordinate_conflicts_intra_source",
      `${dossierSourcesPath(slug)}#dsrc-def-coordinate_conflicts_intra_source`,
    ),
    spec(
      "dsrc-declared-elsewhere",
      doc.totals.declared_here_located_elsewhere,
      "/totals/declared_here_located_elsewhere",
      `${dossierSourcesPath(slug)}#dsrc-def-declared_here_located_elsewhere`,
    ),
    // The "Where this comes from" block's dated + derived figures (the
    // per-row table cells are row data inside the one table figure region).
    spec("dsrc-first-seen", doc.totals.first_seen_at ?? "not_recorded", "/totals/first_seen_at", `${dossierSourcesPath(slug)}#dsrc-def-first_seen`),
    spec("dsrc-last-seen", doc.totals.last_seen_at ?? "not_recorded", "/totals/last_seen_at", `${dossierSourcesPath(slug)}#dsrc-def-last_seen`),
    spec("dsrc-explore", doc.totals.sources, "/totals/sources", `${dossierSourcesPath(slug)}#dsrc-def-sources`),
    spec("dsrc-top-sources", doc.totals.sources, "/sources", `${dossierSourcesPath(slug)}#dsrc-def-records`),
    spec("dsrc-rest", Math.max(0, contributingSources(doc).length - 5), "/totals/sources", `${dossierSourcesPath(slug)}#dsrc-def-sources`),
  ];
}
