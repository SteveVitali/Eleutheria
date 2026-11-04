// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.48 (R11-K13-UX9-3; SIG-TRANSP-001/028/033 owner; SIG-TRANSP-027/037,
 * SIG-UI-039/040/058 cited; K9 §4–§8) — the sources table model.
 *
 * One canonical row set — the release's `sig.source-row/1` rows
 * (`transparency/sources.json`, P35.40) enriched with the freshness verdict
 * (`transparency/freshness.jsonl`, P35.41), the per-source
 * `sig.execution-record/1` feed (P36.46) and the registry-only enrichment
 * fields the page model carries (P36.47) — feeds every surface this row
 * ships:
 *
 *   - three pre-rendered views — Overview `/sources/`, Runs & freshness
 *     `/sources/runs/`, Rights & downloads `/sources/rights/` (K9 §4.2);
 *   - asc/desc sort routes `…/sort/<col>/<asc|desc>/` — plain GET links,
 *     absence tokens sort last in BOTH directions, ties break on name
 *     (K9 §6.1, C-3);
 *   - single-dimension facet routes `/sources/by/<dim>/<value>/` — no
 *     facet × sort or facet × facet product (bounded route count);
 *   - the A–Z jump list (in-page anchors — one un-paginated page per view);
 *   - `sources.csv` / the served `sources.json` + the generated Table
 *     Schema — every column is a registry entry, so the schema can never
 *     drift from the table (SIG-TRANSP-033);
 *   - the shared row contract both clocks render (K9 C-12): the Runs &
 *     freshness cells are the `RunsRow` shape — the status lane maps its
 *     `sig.status-lane/1` row onto the same cells, adding only the
 *     status-clock "Next run (day)".
 *
 * Every cell is a value or a named absence token (J3 T-5); a gated,
 * refused or withdrawn row renders its S-11 registry-only fields and
 * never a run/capture detail (D-J3-11).
 */

import {
  SOURCE_ROWS_DOC_FIXTURE,
  isSourceRowsDoc,
  type LifecycleState,
  type SourceRow,
  type SourceRowsDoc,
} from "./source-counts";
import {
  SOURCE_PAGE_EXTRAS_FIXTURE,
  SOURCE_EXECUTIONS_FIXTURE,
  SOURCE_FRESHNESS_FIXTURE,
  isExecutionRecord,
  isRegistryOnly,
  type ExecutionRecord,
  type SourceFreshness,
} from "./source-page";
import { AS_OF } from "./fixtures";
import { dataSource, exportDir, getDownloadListing } from "./data";
import type { DownloadFile } from "./downloads";
import { existsSync, readFileSync } from "node:fs";

export const SOURCES_TABLE_SCHEMA = "sig.sources-table/1";
export const TABLESCHEMA_PROFILE = "https://datapackage.org/profiles/2.0/tableschema.json";

// ---------------------------------------------------------------------------
// The normalized row — one per registry row, every cell a value or a named
// absence token.
// ---------------------------------------------------------------------------

/** The redistribution pair K9 §4.1 col 6 carries (derived + raw lane). */
export type DerivedStatus = "published" | "withheld_pending_rights_review" | "not_published";

export interface TableRow {
  sourceId: string;
  name: string;
  publisher: string;
  publisherType: string;
  /** Technology classes — `null` renders `not_typed` (the registry field
   *  is not emitted yet; K9 col 3's named absence). */
  classes: string[] | null;
  /** Declared geography (free text today — PKG-06a's structured keys are
   *  not emitted; country/subdivision stay `unresolved`). */
  geography: string | null;
  country: string;
  subdivision: string;
  licenceSpdx: string | null;
  licenceAttribution: string | null;
  /** Upstream terms URL when recorded. */
  termsUrl: string | null;
  homepage: string | null;
  homepageHost: string | null;
  derivedStatus: DerivedStatus;
  lane: string;
  laneBasis: string | null;
  lifecycle: LifecycleState;
  flags: string[];
  lastRun: string | null;
  /** The row's own token when no run is recorded (`never_run`,
   *  `not_recorded (…)`). */
  lastRunToken: string | null;
  upstreamChange: { value: string | null; basis: string } | null;
  sigChange: { value: string | null; basis: string } | null;
  cadenceRule: string | null;
  cadenceBasis: string | null;
  freshnessState: string;
  freshnessEvaluatedAt: string | null;
  runRecordMissing: boolean;
  volatilityDominant: string | null;
  staleness: { evaluable: number; notEvaluable: number } | null;
  publishedClaims: number | null;
  publishedSites: boolean;
  /** Executions recorded; `null` → `none_recorded`. */
  runsTotal: number | null;
  runsByOutcome: Record<string, number>;
  failedRecent: number | null;
  openIssue: boolean;
  /** The K9 col-16 download cell (P36.68 / UX9-4): the latest derived
   *  extract resolved from the release's `sig.download-listing/1` —
   *  the `sites.csv.gz` when present, else the `statements.jsonl.gz`
   *  slice every published source carries (K9 C-8). `null` → the row's
   *  named absence token stands in `downloadToken`. */
  download: { href: string; bytes: number; name: string; format: string; fileIndex: number } | null;
  /** The cell's named-absence token: `downloadable` when `download` is
   *  wired, `extract_not_emitted` for a published row with no slice in the
   *  listing, `withheld`/`not_published` per state. */
  downloadToken: string;
  registryOnly: boolean;
}

/** The status clock's one extra cell — day granularity only (J3 §14 R-6). */
export interface RunsRow extends TableRow {
  nextRunDay?: string;
}

// ---------------------------------------------------------------------------
// The data seam — fixtures | export (fail closed, never fabricate).
// ---------------------------------------------------------------------------

function exportSourcesDoc(): SourceRowsDoc | null {
  const path = `${exportDir()}/transparency/sources.json`;
  if (!existsSync(path)) return null;
  const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
  if (!isSourceRowsDoc(parsed)) {
    throw new Error(`${path}: not a valid sig.source-row/1 document`);
  }
  return parsed;
}

function sourcesDoc(): SourceRowsDoc {
  if (dataSource() === "export") {
    const doc = exportSourcesDoc();
    if (doc === null) {
      throw new Error(
        "SIG_DATA_SOURCE=export but transparency/sources.json is missing — a stale export fails loud (SIG-ENG-042)",
      );
    }
    return doc;
  }
  return SOURCE_ROWS_DOC_FIXTURE;
}

function exportExecutions(sourceId: string): ExecutionRecord[] | null {
  const path = `${exportDir()}/transparency/sources/${sourceId}/executions.jsonl`;
  if (!existsSync(path)) return null;
  const rows = readFileSync(path, "utf-8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => JSON.parse(l) as unknown);
  for (const r of rows) {
    if (!isExecutionRecord(r)) {
      throw new Error(`${path}: a row is not a valid sig.execution-record/1`);
    }
  }
  return rows as ExecutionRecord[];
}

function exportFreshnessMap(): Map<string, SourceFreshness> {
  const map = new Map<string, SourceFreshness>();
  const path = `${exportDir()}/transparency/freshness.jsonl`;
  if (!existsSync(path)) return map;
  for (const line of readFileSync(path, "utf-8").split("\n")) {
    const t = line.trim();
    if (!t) continue;
    const o = JSON.parse(t) as SourceFreshness;
    if (o && typeof o.source_id === "string") map.set(o.source_id, o);
  }
  return map;
}

// ---------------------------------------------------------------------------
// Derivations — verdict, derived status, execution summary. Pure over the
// emitted artifacts.
// ---------------------------------------------------------------------------

const SUCCESS_OUTCOMES = new Set(["ok", "partial", "quota_reached"]);

/** The K9 §5.1 freshness verdict — the shared artifact's state when the
 *  release carries one, else the bounded derivation over the same inputs
 *  the function consumes (cadence + executions); registry-only rows are
 *  `not_applicable`. Never a verdict without its basis. */
export function freshnessVerdict(
  row: SourceRow,
  freshness: SourceFreshness | null,
  executions: readonly ExecutionRecord[] | null,
): { state: string; evaluatedAt: string | null; runRecordMissing: boolean } {
  if (isRegistryOnlyShape(row)) {
    return { state: "not_applicable", evaluatedAt: freshness?.evaluated_at ?? null, runRecordMissing: false };
  }
  if (row.cadence?.one_time_load === true || (row.status_flags ?? []).includes("one_time_load")) {
    return {
      state: "one_time_load",
      evaluatedAt: freshness?.evaluated_at ?? null,
      runRecordMissing: freshness?.run_record_missing ?? false,
    };
  }
  if (freshness !== null) {
    return {
      state: freshness.freshness_state,
      evaluatedAt: freshness.evaluated_at,
      runRecordMissing: freshness.run_record_missing,
    };
  }
  if (executions && executions.length > 0) {
    const latest = [...executions].sort((a, b) =>
      String(b.finished_at ?? b.started_at ?? "").localeCompare(String(a.finished_at ?? a.started_at ?? "")),
    )[0]!;
    if (!SUCCESS_OUTCOMES.has(latest.outcome) && latest.quota_reached !== true) {
      return { state: "last_run_failed", evaluatedAt: null, runRecordMissing: false };
    }
    return { state: "on_time", evaluatedAt: null, runRecordMissing: false };
  }
  if (row.cadence?.scheduled === true) {
    return { state: "never_run", evaluatedAt: null, runRecordMissing: false };
  }
  if (row.cadence?.scheduled === false) {
    return { state: "not_scheduled", evaluatedAt: null, runRecordMissing: false };
  }
  return { state: "not_recorded", evaluatedAt: null, runRecordMissing: false };
}

function isRegistryOnlyShape(row: SourceRow): boolean {
  return isRegistryOnly(row as Parameters<typeof isRegistryOnly>[0]);
}

/** The volatility chip's dominant class (K9 §5.2) — largest bucket of the
 *  emitted distribution, or `null` when nothing was evaluated. */
export function volatilityDominant(
  volatility: Record<string, number> | null | undefined,
): string | null {
  if (!volatility) return null;
  const entries = Object.entries(volatility).filter(([, n]) => typeof n === "number" && n > 0);
  if (entries.length === 0) return null;
  entries.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return entries[0]![0];
}

/** K9 §4.1 col 6 derived status — published / withheld pending rights
 *  review / not published (registry-only rows are withheld or not
 *  published; the refused/withdrawn states are never "withheld"). */
export function derivedStatus(row: SourceRow): DerivedStatus {
  if (row.lifecycle_state === "published") return "published";
  if (row.lifecycle_state === "gated") return "withheld_pending_rights_review";
  return "not_published";
}

/** The K9 col-16 download cell (P36.68 / UX9-4): the latest derived
 *  extract from the `sig.download-listing/1` — `sites.csv.gz` when the
 *  source contributes site rows, else the always-present
 *  `statements.jsonl.gz` slice (K9 C-8). `null` names the honest absence. */
export function downloadFile(
  row: SourceRow,
  sliceFiles: readonly (DownloadFile & { fileIndex: number })[] | null,
): { href: string; bytes: number; name: string; format: string; fileIndex: number } | null {
  if (row.lifecycle_state !== "published" || !sliceFiles || sliceFiles.length === 0) return null;
  const pick =
    sliceFiles.find((f) => f.name === "sites.csv.gz") ??
    sliceFiles.find((f) => f.name === "statements.jsonl.gz") ??
    null;
  return pick
    ? { href: pick.href, bytes: pick.byte_size, name: pick.name, format: pick.format, fileIndex: pick.fileIndex }
    : null;
}

/** The cell's named-absence token per state — `download_host_pending`
 *  retired with UX9-4: a published row now reads `downloadable` when the
 *  listing carries its slice, `extract_not_emitted` when it does not. */
export function downloadToken(row: SourceRow, file: { href: string } | null): string {
  if (row.lifecycle_state === "published") return file ? "downloadable" : "extract_not_emitted";
  if (row.lifecycle_state === "gated" || row.lifecycle_state === "refused") return "withheld";
  return "not_published";
}

/** Executions summarised for the Runs & freshness columns — outcome split
 *  and the failures inside the 90-day window before the as-of (K9 col 15). */
export function executionSummary(
  executions: readonly ExecutionRecord[] | null,
  asOf: string,
): { total: number | null; byOutcome: Record<string, number>; failedRecent: number | null } {
  if (executions === null) return { total: null, byOutcome: {}, failedRecent: null };
  const byOutcome: Record<string, number> = {};
  let failedRecent = 0;
  const cutoff = Date.parse(asOf) - 90 * 86_400_000;
  for (const e of executions) {
    byOutcome[e.outcome] = (byOutcome[e.outcome] ?? 0) + 1;
    const at = Date.parse(String(e.finished_at ?? e.started_at ?? ""));
    if (!SUCCESS_OUTCOMES.has(e.outcome) && e.quota_reached !== true && Number.isFinite(at) && at >= cutoff) {
      failedRecent += 1;
    }
  }
  return { total: executions.length, byOutcome, failedRecent };
}

/** Compose one table row — `extras` carries the fields the artifacts do
 *  not emit yet (technology classes, declared geography); each falls back
 *  to its named absence, never a guess. */
export function composeRow(
  row: SourceRow,
  extras: { technology_classes: string[] | null; geography: string | null } | null,
  freshness: SourceFreshness | null,
  executions: readonly ExecutionRecord[] | null,
  asOf: string,
  sliceFiles: readonly (DownloadFile & { fileIndex: number })[] | null = null,
): TableRow {
  const verdict = freshnessVerdict(row, freshness, executions);
  const exec = executionSummary(executions, asOf);
  const lastRun = typeof row.last_successful_run === "string" && /^\d{4}-\d{2}-\d{2}T/.test(row.last_successful_run)
    ? row.last_successful_run
    : null;
  return {
    sourceId: row.source_id,
    name: row.name ?? row.source_id,
    publisher: row.publisher ?? "publisher_not_recorded",
    publisherType: row.publisher_type ?? "not_recorded",
    classes: extras?.technology_classes ?? null,
    geography: extras?.geography ?? null,
    country: "unresolved",
    subdivision: "unresolved",
    licenceSpdx: row.licence?.spdx ?? null,
    licenceAttribution: row.licence?.attribution ?? null,
    termsUrl: row.ground_truth?.terms_url && !row.ground_truth.terms_url.startsWith("no_upstream")
      ? row.ground_truth.terms_url
      : null,
    homepage: row.ground_truth?.homepage ?? row.homepage_url ?? null,
    homepageHost: row.ground_truth?.homepage_host ?? null,
    derivedStatus: derivedStatus(row),
    lane: row.lane ?? "unknown",
    laneBasis: row.lane_basis ?? null,
    lifecycle: row.lifecycle_state,
    flags: [...(row.status_flags ?? [])],
    lastRun,
    lastRunToken:
      typeof row.last_successful_run === "string" && lastRun === null
        ? row.last_successful_run
        : null,
    upstreamChange: row.last_upstream_change ?? null,
    sigChange: row.last_sig_records_change ?? null,
    cadenceRule: row.cadence?.rule ?? null,
    cadenceBasis: row.cadence?.basis ?? null,
    freshnessState: verdict.state,
    freshnessEvaluatedAt: verdict.evaluatedAt,
    runRecordMissing: verdict.runRecordMissing || (row.status_flags ?? []).includes("run_record_missing"),
    volatilityDominant: volatilityDominant(freshness?.volatility),
    staleness: freshness?.staleness
      ? { evaluable: freshness.staleness.evaluable ?? 0, notEvaluable: freshness.staleness.not_evaluable ?? 0 }
      : null,
    publishedClaims: typeof row.published_claims === "number" ? row.published_claims : null,
    publishedSites: row.published_sites === true,
    runsTotal: exec.total,
    runsByOutcome: exec.byOutcome,
    failedRecent: exec.failedRecent,
    openIssue: (row.status_flags ?? []).includes("open_issue"),
    download: downloadFile(row, sliceFiles),
    downloadToken: downloadToken(row, downloadFile(row, sliceFiles)),
    registryOnly: isRegistryOnlyShape(row),
  };
}

/** The whole table — every registry row, the canonical order (name
 *  case-folded, source_id tiebreak) the default sort renders. */
/** source_id → its `by-source/<id>/` slice files in the release listing
 *  (P36.68 / UX9-4 — the K9 col-16 download cell's data). */
function sliceFilesBySource(): Map<string, (DownloadFile & { fileIndex: number })[]> {
  const map = new Map<string, (DownloadFile & { fileIndex: number })[]>();
  getDownloadListing().files.forEach((f, fileIndex) => {
    if (f.kind !== "source-slice" || !f.source_id) return;
    const list = map.get(f.source_id) ?? [];
    list.push({ ...f, fileIndex });
    map.set(f.source_id, list);
  });
  return map;
}

export function getTableRows(): { rows: TableRow[]; asOf: string; rowIndex: Map<string, number> } {
  const doc = sourcesDoc();
  const freshnessMap =
    dataSource() === "export" ? exportFreshnessMap() : new Map(Object.entries(SOURCE_FRESHNESS_FIXTURE));
  const slices = sliceFilesBySource();
  const rows = doc.sources.map((raw) => {
    const extras =
      dataSource() === "export" ? null : (SOURCE_PAGE_EXTRAS_FIXTURE[raw.source_id] ?? null);
    const executions =
      dataSource() === "export"
        ? exportExecutions(raw.source_id)
        : (SOURCE_EXECUTIONS_FIXTURE[raw.source_id] ?? null);
    return composeRow(raw, extras, freshnessMap.get(raw.source_id) ?? null, executions, doc.as_of, slices.get(raw.source_id) ?? null);
  });
  rows.sort((a, b) => nameKey(a.name).localeCompare(nameKey(b.name)) || a.sourceId.localeCompare(b.sourceId));
  const rowIndex = new Map(doc.sources.map((r, i) => [r.source_id, i]));
  return { rows, asOf: doc.as_of, rowIndex };
}

// ---------------------------------------------------------------------------
// Views, sorts, facets, the A–Z list.
// ---------------------------------------------------------------------------

export type TableView = "overview" | "runs" | "rights";

export const VIEWS: Record<TableView, { routeBase: string; label: string; columns: readonly string[] }> = {
  overview: {
    routeBase: "sources/",
    label: "Overview",
    columns: ["source", "publisher", "class", "geography", "status", "freshness", "claims", "download"],
  },
  runs: {
    routeBase: "sources/runs/",
    label: "Runs & freshness",
    columns: ["source", "status", "last_run", "upstream", "sig_change", "cadence", "freshness", "runs", "errors"],
  },
  rights: {
    routeBase: "sources/rights/",
    label: "Rights & downloads",
    columns: ["source", "publisher", "licence", "redistribution", "download", "ground_truth"],
  },
};

function nameKey(name: string): string {
  return name.toLocaleLowerCase();
}

const LANE_ORDER = ["raw-ok", "derived-only", "link-only", "restricted", "unknown"];
const STATE_ORDER: LifecycleState[] = [
  "published",
  "ingested_not_published",
  "permitted_not_ingested",
  "gated",
  "refused",
  "withdrawn",
];
const VERDICT_ORDER = [
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

function rank(order: readonly string[], v: string | null): number {
  const i = v === null ? -1 : order.indexOf(v);
  return i === -1 ? order.length : i;
}

/** `null` means the cell's value is an absence token — it sorts LAST in
 *  both directions (K9 C-3). */
function absentLast(v: string | number | null): { absent: boolean; v: string | number } {
  return v === null ? { absent: true, v: "" } : { absent: false, v };
}

const timeVal = (c: { value: string | null } | null): string | null => c?.value ?? null;

/** One sortable column — the sort keys are the route segments. */
export interface SortSpec {
  key: string;
  /** The comparable, `null` for an absence-token cell. */
  value: (row: TableRow) => string | number | null;
}

export const SORT_SPECS: Record<string, SortSpec> = {
  source: { key: "source", value: (r) => nameKey(r.name) },
  publisher: { key: "publisher", value: (r) => (r.publisher === "publisher_not_recorded" ? null : nameKey(r.publisher)) },
  class: { key: "class", value: (r) => (r.classes && r.classes.length > 0 ? nameKey(r.classes[0]!) : null) },
  geography: { key: "geography", value: (r) => (r.geography === null ? null : nameKey(r.geography)) },
  status: { key: "status", value: (r) => rank(STATE_ORDER, r.lifecycle) },
  freshness: { key: "freshness", value: (r) => rank(VERDICT_ORDER, r.freshnessState) },
  claims: { key: "claims", value: (r) => r.publishedClaims },
  download: { key: "download", value: (r) => r.download?.bytes ?? null },
  last_run: { key: "last_run", value: (r) => r.lastRun },
  upstream: { key: "upstream", value: (r) => timeVal(r.upstreamChange) },
  sig_change: { key: "sig_change", value: (r) => timeVal(r.sigChange) },
  cadence: { key: "cadence", value: (r) => r.cadenceRule },
  runs: { key: "runs", value: (r) => r.runsTotal },
  errors: { key: "errors", value: (r) => (r.failedRecent === null ? null : r.failedRecent * 1000 + (r.openIssue ? 1 : 0)) },
  licence: { key: "licence", value: (r) => r.licenceSpdx },
  redistribution: { key: "redistribution", value: (r) => rank(LANE_ORDER, r.lane) },
  ground_truth: { key: "ground_truth", value: (r) => r.homepageHost },
};

/** The sortable columns of one view (every column that has a sort spec). */
export function sortableColumns(view: TableView): SortSpec[] {
  return VIEWS[view].columns.map((c) => SORT_SPECS[c]!).filter(Boolean);
}

export type SortDir = "asc" | "desc";

/** Sort rows by a column — absences last in BOTH directions, ties on name. */
export function sortTable(rows: readonly TableRow[], key: string, dir: SortDir): TableRow[] {
  const spec = SORT_SPECS[key];
  if (!spec) return [...rows];
  const sign = dir === "desc" ? -1 : 1;
  return [...rows].sort((a, b) => {
    const va = absentLast(spec.value(a));
    const vb = absentLast(spec.value(b));
    if (va.absent !== vb.absent) return va.absent ? 1 : -1;
    if (!va.absent) {
      const cmp =
        typeof va.v === "number" && typeof vb.v === "number"
          ? va.v - vb.v
          : String(va.v).localeCompare(String(vb.v));
      if (cmp !== 0) return sign * cmp;
    }
    return nameKey(a.name).localeCompare(nameKey(b.name)) || a.sourceId.localeCompare(b.sourceId);
  });
}

/** The sort-route path for a view + column + direction (sans leading slash). */
export function sortRoute(view: TableView, key: string, dir: SortDir): string {
  return `${VIEWS[view].routeBase}sort/${key}/${dir}/`;
}

// ---------------------------------------------------------------------------
// Pagination (K9 §6.1's fallback): a build check — the ADR-155 T1 document
// budget, measured by the export-mode budgets leg — found the full row set
// over the 150 KiB ceiling, so every table route paginates its sorted row
// set at SOURCES_TABLE_PAGE_SIZE rows with sort preserved across pages.
// Page 1 is the route itself; `page/<n>/` carries the continuations. The
// fixtures corpus fits one page, so no continuation routes emit there.
// ---------------------------------------------------------------------------

/** Rows per table page — sized so the heaviest view's document stays under
 *  the ratified T1 `documentMaxBytes` with headroom (the row byte weight is
 *  dominated by the per-cell <Figure> evidence, which the defining standard
 *  requires; never smoothed, measured by the budgets leg every run). */
export const SOURCES_TABLE_PAGE_SIZE = 30;

/** Slice `rows` (already in the route's sort order) to page `page` (1-based). */
export function paginateRows<T>(
  rows: readonly T[],
  page: number,
  size: number = SOURCES_TABLE_PAGE_SIZE,
): { rows: T[]; page: number; pages: number; total: number } {
  const total = rows.length;
  const pages = Math.max(1, Math.ceil(total / size));
  if (page < 1 || page > pages) {
    throw new Error(`sources-table: page ${page} outside 1..${pages} (SIG-ENG-042)`);
  }
  const start = (page - 1) * size;
  return { rows: rows.slice(start, start + size), page, pages, total };
}

/** The continuation page numbers a row set emits — `2..pages` (page 1 is
 *  the base route; an empty list means the set fits one page and no
 *  `page/<n>/` route emits). */
export function pageNumbers(total: number, size: number = SOURCES_TABLE_PAGE_SIZE): number[] {
  const pages = Math.ceil(total / size);
  return Array.from({ length: Math.max(0, pages - 1) }, (_, i) => i + 2);
}

/** The continuation route for a base path — page 1 is the base itself. */
export function pageRoute(base: string, page: number): string {
  return page <= 1 ? base : `${base}page/${page}/`;
}

/** Every sort route a view emits (the getStaticPaths contract). */
export function sortRoutesFor(view: TableView): { col: string; dir: SortDir }[] {
  const out: { col: string; dir: SortDir }[] = [];
  for (const c of sortableColumns(view)) {
    for (const dir of ["asc", "desc"] as const) out.push({ col: c.key, dir });
  }
  return out;
}

// ---------------------------------------------------------------------------
// Facets — one dimension per page, values over the rendered vocabulary
// (including the named-absence tokens — a facet over an absence is a real
// set, never a fabricated value).
// ---------------------------------------------------------------------------

export interface FacetDim {
  key: string;
  label: string;
  /** Every value the row maps to (a row may map to several — e.g. classes). */
  values: (row: TableRow) => string[];
}

export const FACET_DIMS: readonly FacetDim[] = [
  { key: "status", label: "lifecycle state", values: (r) => [r.lifecycle] },
  { key: "class", label: "technology class", values: (r) => r.classes ?? ["not_typed"] },
  { key: "publisher-type", label: "publisher type", values: (r) => [r.publisherType] },
  { key: "country", label: "country", values: (r) => [r.country] },
  { key: "subdivision", label: "subdivision", values: (r) => [r.subdivision] },
  { key: "licence", label: "upstream licence", values: (r) => [r.licenceSpdx ?? "rights_not_reviewed"] },
  { key: "lane", label: "raw-bytes lane", values: (r) => [r.lane] },
  {
    key: "cadence",
    label: "declared cadence",
    values: (r) => [
      r.cadenceRule ?? "not_recorded",
      ...(r.cadenceRule === "not_scheduled" ? [] : []),
    ],
  },
  { key: "freshness", label: "freshness verdict", values: (r) => [r.freshnessState] },
  { key: "volatility", label: "dominant volatility", values: (r) => [r.volatilityDominant ?? "not_evaluable"] },
  {
    key: "downloadable",
    label: "downloadable",
    values: (r) => [r.download ? "yes" : r.downloadToken],
  },
  { key: "has-issues", label: "open issues", values: (r) => [r.openIssue ? "yes" : "no"] },
];

export function facetDim(key: string): FacetDim | null {
  return FACET_DIMS.find((d) => d.key === key) ?? null;
}

/** One facet value → its row set (counts drive the facet menu). */
export interface FacetValue {
  dim: string;
  value: string;
  count: number;
}

/** Every facet route this build emits — dim × observed value (ordered). */
export function facetRoutes(rows: readonly TableRow[]): { dim: string; value: string; count: number }[] {
  const out: { dim: string; value: string; count: number }[] = [];
  for (const dim of FACET_DIMS) {
    const counts = new Map<string, number>();
    for (const row of rows) {
      for (const v of dim.values(row)) counts.set(v, (counts.get(v) ?? 0) + 1);
    }
    for (const [value, count] of [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      out.push({ dim: dim.key, value, count });
    }
  }
  return out;
}

/** The facet menu — per dim, the value list with counts + route paths. */
export function facetMenu(rows: readonly TableRow[]): { dim: FacetDim; values: { value: string; count: number }[] }[] {
  return FACET_DIMS.map((dim) => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      for (const v of dim.values(row)) counts.set(v, (counts.get(v) ?? 0) + 1);
    }
    return {
      dim,
      values: [...counts.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([value, count]) => ({ value, count })),
    };
  });
}

export function facetRows(rows: readonly TableRow[], dimKey: string, value: string): TableRow[] {
  const dim = facetDim(dimKey);
  if (!dim) return [];
  return rows.filter((r) => dim.values(r).includes(value));
}

/** The route segment for a facet value — slugified (multi-word values
 *  like `camera registry` carry no space into the emitted path, so the
 *  canonical/og:url needs no percent-encoding). */
export function facetValueSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function facetRoute(dim: string, value: string): string {
  return `sources/by/${dim}/${facetValueSlug(value)}/`;
}

// ---------------------------------------------------------------------------
// The A–Z jump list — in-page anchors on the name sort (letters key the
// FIRST row of each initial letter). Under pagination (K9 §6.1's fallback)
// a letter's anchor lives on the name-sorted page that row lands on, so each
// entry carries its `page` and the nav links across the continuation routes.
// ---------------------------------------------------------------------------

export function azIndex(rows: readonly TableRow[]): { letter: string; anchorId: string }[] {
  return azPaged(rows).map(({ letter, anchorId }) => ({ letter, anchorId }));
}

/** The A–Z index with each letter's name-sorted page (1-based) — the nav
 *  links to `pageRoute(base, letter.page)#anchorId`. */
export function azPaged(
  rows: readonly TableRow[],
  size: number = SOURCES_TABLE_PAGE_SIZE,
): { letter: string; anchorId: string; page: number }[] {
  const seen = new Set<string>();
  const out: { letter: string; anchorId: string; page: number }[] = [];
  const nameSorted = sortTable(rows, "source", "asc");
  nameSorted.forEach((r, pos) => {
    const letter = (nameKey(r.name)[0] ?? "#").toLocaleUpperCase();
    const key = /[A-Z]/.test(letter) ? letter : "#";
    if (seen.has(key)) return;
    seen.add(key);
    out.push({
      letter: key,
      anchorId: `az-${key === "#" ? "other" : key}`,
      page: Math.floor(pos / size) + 1,
    });
  });
  return out;
}

/** The anchor id a row carries when it opens its letter (else `null`). */
export function azAnchorFor(row: TableRow, index: readonly { letter: string; anchorId: string }[], nameSorted: readonly TableRow[]): string | null {
  const pos = nameSorted.indexOf(row);
  if (pos === -1) return null;
  const letter = (nameKey(row.name)[0] ?? "#").toLocaleUpperCase();
  const key = /[A-Z]/.test(letter) ? letter : "#";
  const first = index.find((e) => e.letter === key);
  if (!first) return null;
  return first.anchorId && pos === nameSorted.findIndex((r) => {
    const l = (nameKey(r.name)[0] ?? "#").toLocaleUpperCase();
    return (/[A-Z]/.test(l) ? l : "#") === key;
  })
    ? first.anchorId
    : null;
}

// ---------------------------------------------------------------------------
// `sources.csv` + the served rows JSON + the generated Table Schema — one
// column registry drives all three (SIG-TRANSP-033; the schema can never
// drift from the table it describes).
// ---------------------------------------------------------------------------

/** One column of the flat export — the Table Schema's field list. */
export interface ExportColumn {
  name: string;
  title: string;
  type: "string" | "number" | "boolean" | "array";
  /** The cell value (absence tokens are explicit strings, never null). */
  cell: (row: TableRow) => string | number | boolean;
}

const chg = (c: { value: string | null; basis: string } | null, absent: string): string =>
  c === null ? absent : c.value ?? c.basis;

export const EXPORT_COLUMNS: readonly ExportColumn[] = [
  { name: "source_id", title: "Source id", type: "string", cell: (r) => r.sourceId },
  { name: "name", title: "Source", type: "string", cell: (r) => r.name },
  { name: "publisher", title: "Publisher", type: "string", cell: (r) => r.publisher },
  { name: "publisher_type", title: "Publisher type", type: "string", cell: (r) => r.publisherType },
  { name: "technology_classes", title: "Technology classes", type: "array", cell: (r) => (r.classes ?? ["not_typed"]).join("|") },
  { name: "geography", title: "Declared geography", type: "string", cell: (r) => r.geography ?? "unresolved" },
  { name: "country", title: "Country", type: "string", cell: (r) => r.country },
  { name: "subdivision", title: "Subdivision", type: "string", cell: (r) => r.subdivision },
  { name: "licence_spdx", title: "Upstream licence (SPDX)", type: "string", cell: (r) => r.licenceSpdx ?? "rights_not_reviewed" },
  { name: "derived_status", title: "Derived redistribution", type: "string", cell: (r) => r.derivedStatus },
  { name: "raw_lane", title: "Raw-bytes lane", type: "string", cell: (r) => r.lane },
  { name: "lifecycle_state", title: "Lifecycle state", type: "string", cell: (r) => r.lifecycle },
  { name: "status_flags", title: "Status flags", type: "array", cell: (r) => r.flags.join("|") },
  { name: "last_successful_run", title: "Last successful run", type: "string", cell: (r) => r.lastRun ?? (r.lastRunToken ?? "not_recorded") },
  { name: "last_upstream_change", title: "Last upstream change", type: "string", cell: (r) => chg(r.upstreamChange, "not_recorded") },
  { name: "last_sig_records_change", title: "Last change in SIG records", type: "string", cell: (r) => chg(r.sigChange, "not_recorded") },
  { name: "cadence", title: "Declared cadence", type: "string", cell: (r) => r.cadenceRule ?? "not_recorded" },
  { name: "freshness_verdict", title: "Freshness verdict", type: "string", cell: (r) => r.freshnessState },
  { name: "freshness_evaluated_at", title: "Verdict evaluated at", type: "string", cell: (r) => r.freshnessEvaluatedAt ?? "not_recorded" },
  { name: "volatility_dominant", title: "Dominant volatility", type: "string", cell: (r) => r.volatilityDominant ?? "not_evaluable" },
  { name: "staleness_evaluable", title: "Staleness evaluable", type: "number", cell: (r) => r.staleness?.evaluable ?? -1 },
  { name: "staleness_not_evaluable", title: "Staleness not evaluable", type: "number", cell: (r) => r.staleness?.notEvaluable ?? -1 },
  { name: "published_claims", title: "Published claims", type: "number", cell: (r) => r.publishedClaims ?? -1 },
  { name: "published_sites", title: "Published sites", type: "boolean", cell: (r) => r.publishedSites },
  { name: "executions_total", title: "Executions recorded", type: "number", cell: (r) => r.runsTotal ?? -1 },
  { name: "failed_90d", title: "Failed executions, trailing 90d", type: "number", cell: (r) => r.failedRecent ?? -1 },
  { name: "open_issue", title: "Open issue", type: "boolean", cell: (r) => r.openIssue },
  { name: "download", title: "Download", type: "string", cell: (r) => r.download?.href ?? r.downloadToken },
  { name: "homepage", title: "Ground-truth homepage", type: "string", cell: (r) => r.homepage ?? "no_upstream_url_recorded" },
  { name: "homepage_host", title: "Ground-truth host", type: "string", cell: (r) => r.homepageHost ?? "not_recorded" },
  { name: "terms_url", title: "Ground-truth terms", type: "string", cell: (r) => r.termsUrl ?? "terms_not_captured" },
];

function csvEscape(v: string | number | boolean): string {
  const s = String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** `sources.csv` — RFC 4180, UTF-8, `#` provenance comment lines first
 *  (the same rows the pages render; the served JSON stays the structured
 *  `sig.source-row/1` doc). */
export function tableCsv(rows: readonly TableRow[], asOf: string): string {
  const lines = [
    "# sig.sources-table/1 — the sources table (SIG-TRANSP-001/028/033)",
    `# rows: registry rows of the release source index; as_of: ${asOf}`,
    "# licences: upstream licence per row (licence_spdx); SIG's rows are facts",
    "# published under each row's recorded basis — see /sources/ for the",
    "# counting definitions and the terms disclosures.",
    EXPORT_COLUMNS.map((c) => csvEscape(c.name)).join(","),
    ...rows.map((r) => EXPORT_COLUMNS.map((c) => csvEscape(c.cell(r))).join(",")),
  ];
  return `${lines.join("\r\n")}\r\n`;
}

/** `sources.schema.json` — the generated Table Schema: every column is a
 *  registry entry, so a column added to the table arrives documented or
 *  the schema build fails (J3 §6.5). */
export function tableSchema(asOf: string): Record<string, unknown> {
  return {
    $schema: TABLESCHEMA_PROFILE,
    schema: SOURCES_TABLE_SCHEMA,
    title: "SIG sources table",
    description:
      "One row per source-registry row of the release — the sig.source-row/1 universe the /sources/ views render (K9 §4.1 columns, flattened). Absence tokens are explicit strings; numeric absences are -1 with the token carried in the sibling *_token column where the view shows one.",
    as_of: asOf,
    fields: EXPORT_COLUMNS.map((c) => ({
      name: c.name,
      title: c.title,
      type: c.type === "array" ? "string" : c.type,
      ...(c.type === "array" ? { description: "pipe-separated list" } : {}),
    })),
    primaryKey: "source_id",
  };
}

/** The table's JSON twin — the rendered rows themselves (structured). */
export function tableJson(rows: readonly TableRow[], asOf: string): Record<string, unknown> {
  return { schema: SOURCES_TABLE_SCHEMA, as_of: asOf, rows };
}

export { AS_OF as TABLE_AS_OF };
