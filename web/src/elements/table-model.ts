// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4 / SIG-UI-091) — the pure model half of `<sig-table>`.
 *
 * Everything here is DOM-free so the behaviour the element wires onto
 * server-rendered markup is unit-tested without a browser: column typing,
 * absence-last sorting, text filtering, multi-facet matching, URL-state
 * encode/decode, and the CSV view export with its per-licence provenance
 * lines (every downloaded view restates the licences its rows carry).
 */

export interface TableColumn {
  /** Position in the row's cell array (the `td`/`th` index). */
  index: number;
  /** Stable id for URL state — `data-col` on the `th`, else `c<index>`. */
  id: string;
  /** Header text as rendered. */
  label: string;
}

export interface TableRowModel {
  /** Cell text as rendered, one entry per column. */
  cells: string[];
  /** Facet dimension → the values this row carries (`data-facet-<dim>`). */
  facets: Record<string, string[]>;
  /** Licence ids the row's data is filed under (`data-licence`, `|`-joined). */
  licences: string[];
  /** Optional compartment name (`data-compartment`) for licence lines. */
  compartment?: string;
}

export interface TableModel {
  columns: TableColumn[];
  rows: TableRowModel[];
}

export interface TableState {
  /** Free-text filter (matches any cell). */
  q: string;
  /** Sort column id — `null` = server order. */
  sort: string | null;
  dir: "asc" | "desc";
  /** Facet dimension → selected values (empty = unfiltered on that dim). */
  facets: Record<string, string[]>;
  /** Hidden column ids. */
  hidden: string[];
}

export function defaultState(): TableState {
  return { q: "", sort: null, dir: "asc", facets: {}, hidden: [] };
}

/** The rendered absence marker — an em dash or an empty cell. */
export function isAbsence(text: string): boolean {
  const t = text.trim();
  return t === "" || t === "—" || t === "–";
}

/**
 * Numeric reading of a cell, or `null` when it carries any non-numeric
 * letters — "8,088" → 8088, "ODbL-1.0" → null (the letters make it text).
 */
export function numericCell(text: string): number | null {
  const t = text.trim().replace(/[,\s]/g, "");
  if (t === "" || !/^-?\d+(\.\d+)?%?$/.test(t)) return null;
  const n = Number(t.replace(/%$/, ""));
  return Number.isFinite(n) ? n : null;
}

/**
 * Cell comparison with the K9 ordering: numeric when both sides read as
 * numbers, else a locale-insensitive text compare; absence always sorts
 * last in BOTH directions so a missing fact never floats to the top.
 */
export function compareCells(a: string, b: string): number {
  const aAbsent = isAbsence(a);
  const bAbsent = isAbsence(b);
  if (aAbsent && bAbsent) return 0;
  if (aAbsent) return 1;
  if (bAbsent) return -1;
  const na = numericCell(a);
  const nb = numericCell(b);
  if (na !== null && nb !== null) return na - nb;
  return a.localeCompare(b, undefined, { sensitivity: "base", numeric: true });
}

/** Stable sort of row INDEXES (the DOM nodes stay put; visibility toggles). */
export function sortOrder(model: TableModel, state: TableState): number[] {
  const order = model.rows.map((_, i) => i);
  if (state.sort === null) return order;
  const col = model.columns.find((c) => c.id === state.sort);
  if (!col) return order;
  const dir = state.dir === "desc" ? -1 : 1;
  return order
    .map((i) => i)
    .sort((x, y) => {
      const a = model.rows[x].cells[col.index] ?? "";
      const b = model.rows[y].cells[col.index] ?? "";
      const aAbs = isAbsence(a);
      const bAbs = isAbsence(b);
      // Absence sorts last in BOTH directions — direction applies only to
      // rows that carry a value.
      if (aAbs && bAbs) return x - y;
      if (aAbs) return 1;
      if (bAbs) return -1;
      const cmp = compareCells(a, b);
      return cmp === 0 ? x - y : dir * cmp;
    });
}

/** Case-insensitive substring match over any cell. */
export function rowMatchesQuery(row: TableRowModel, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (needle === "") return true;
  return row.cells.some((cell) => cell.toLowerCase().includes(needle));
}

/**
 * AND across dimensions, OR within one: a row stays visible when, for every
 * dimension with a non-empty selection, it carries at least one selected
 * value. A dimension the row does not declare filters it out when selected.
 */
export function rowMatchesFacets(
  row: TableRowModel,
  selected: Record<string, string[]>,
): boolean {
  for (const [dim, values] of Object.entries(selected)) {
    if (values.length === 0) continue;
    const have = row.facets[dim] ?? [];
    if (!values.some((v) => have.includes(v))) return false;
  }
  return true;
}

/** The distinct facet values a dimension offers, with their row counts. */
export function facetValues(
  rows: TableRowModel[],
  dim: string,
): Map<string, number> {
  const out = new Map<string, number>();
  for (const row of rows) {
    for (const v of row.facets[dim] ?? []) out.set(v, (out.get(v) ?? 0) + 1);
  }
  return new Map([...out.entries()].sort((a, b) => a[0].localeCompare(b[0])));
}

/** The rows matching the filter + facets, in sort order (row indexes). */
export function visibleRowOrder(model: TableModel, state: TableState): number[] {
  return sortOrder(model, state).filter(
    (i) =>
      rowMatchesQuery(model.rows[i], state.q) &&
      rowMatchesFacets(model.rows[i], state.facets),
  );
}

/** Encode the state as URL parameters (only non-default keys are written). */
export function stateToParams(state: TableState): URLSearchParams {
  const p = new URLSearchParams();
  if (state.q !== "") p.set("q", state.q);
  if (state.sort !== null) {
    p.set("sort", state.sort);
    p.set("dir", state.dir);
  }
  for (const [dim, values] of Object.entries(state.facets)) {
    if (values.length > 0) p.set(dim, values.join(","));
  }
  if (state.hidden.length > 0) p.set("cols", state.hidden.join(","));
  return p;
}

/**
 * Decode URL parameters into a state, validated against the model: unknown
 * sort columns, facet dimensions, facet values, and hidden columns are
 * dropped rather than applied — a fabricated parameter can never invent a
 * view the markup does not support.
 */
export function paramsToState(
  search: string,
  model: TableModel,
  facetDims: string[],
): TableState {
  const state = defaultState();
  const p = new URLSearchParams(search);
  const q = p.get("q");
  if (q !== null) state.q = q;
  const sort = p.get("sort");
  if (sort !== null && model.columns.some((c) => c.id === sort)) {
    state.sort = sort;
    state.dir = p.get("dir") === "desc" ? "desc" : "asc";
  }
  for (const dim of facetDims) {
    const raw = p.get(dim);
    if (raw === null) continue;
    const valid = new Set(facetValues(model.rows, dim).keys());
    state.facets[dim] = raw.split(",").filter((v) => valid.has(v));
  }
  const cols = p.get("cols");
  if (cols !== null) {
    const valid = new Set(model.columns.map((c) => c.id));
    state.hidden = cols.split(",").filter((v) => valid.has(v));
  }
  return state;
}

function csvCell(text: string): string {
  const t = text.replace(/\s+/g, " ").trim();
  return /[",\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
}

/**
 * The "download this view" export: CSV over the currently visible rows and
 * columns, prefixed by `#`-comment provenance lines so the file never
 * travels without the licences its rows are filed under — one line per
 * distinct licence, compartment-named when the row declares one.
 */
export function toCsv(
  model: TableModel,
  rowOrder: number[],
  columnIds: string[],
  viewLabel: string,
): string {
  const cols = columnIds
    .map((id) => model.columns.find((c) => c.id === id))
    .filter((c): c is TableColumn => c !== undefined);
  const lines: string[] = [
    "# sig-table export — downloaded view",
    `# view: ${viewLabel}`,
    `# rows: ${rowOrder.length} of ${model.rows.length}`,
  ];
  const licences = new Map<string, string>(); // key -> comment text
  for (const i of rowOrder) {
    const row = model.rows[i];
    for (const licence of row.licences) {
      const key = `${row.compartment ?? ""}:${licence}`;
      licences.set(
        key,
        row.compartment
          ? `# licence (${row.compartment} compartment): ${licence}`
          : `# licence: ${licence}`,
      );
    }
  }
  for (const line of [...licences.values()].sort()) lines.push(line);
  lines.push(cols.map((c) => csvCell(c.label)).join(","));
  for (const i of rowOrder) {
    lines.push(
      cols.map((c) => csvCell(model.rows[i].cells[c.index] ?? "")).join(","),
    );
  }
  return lines.join("\n") + "\n";
}
