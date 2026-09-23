// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * Build-time large-table UX (§15, SIG-UI-034/037): sorting via STATIC links and
 * grouping / summarisation, all computed at build time so a national-scale table
 * (freshness's ~210 sources, the map's tabular equivalent over tens of thousands of
 * sites) stays usable and inside the zero-JS a11y/perf budget.
 *
 * The shell ships no client JavaScript (SIG-UI-036/037), so a "sortable" table cannot
 * re-sort in the browser. Instead each sort order is a distinct, pre-rendered static
 * page reached by a plain GET link: `sortRows` computes the order at build time and
 * `SORT_LINKS`-style column descriptors drive the header links. This keeps sorting
 * archivable and screen-reader-navigable — the ordering is in the HTML, not in a
 * script a reader must run.
 *
 * Pure data + logic (no markup, no colour) so the ordering + summarisation rules are
 * unit-testable independently of any page (mirrors `epistemic.ts` / `empty.ts`).
 */

/** A column that a static table can be sorted by. */
export interface SortColumn<T> {
  /** The URL-safe sort key (also the static route segment, e.g. `/data-freshness/status/`). */
  key: string;
  /** The human header label. */
  label: string;
  /** Pull the comparable value from a row. */
  value: (row: T) => string | number;
  /** Sort direction; `desc` is natural for counts ("most stale first"). Default `asc`. */
  direction?: "asc" | "desc";
}

/** A stable comparator: compares by the column, then by a stable tiebreak key. */
function compare<T>(col: SortColumn<T>, tiebreak: (row: T) => string) {
  const dir = col.direction === "desc" ? -1 : 1;
  return (a: T, b: T): number => {
    const va = col.value(a);
    const vb = col.value(b);
    let primary: number;
    if (typeof va === "number" && typeof vb === "number") {
      primary = va - vb;
    } else {
      primary = String(va).localeCompare(String(vb));
    }
    if (primary !== 0) return dir * primary;
    // Stable, direction-independent tiebreak so a re-sort is deterministic.
    return tiebreak(a).localeCompare(tiebreak(b));
  };
}

/**
 * Sort `rows` by the named column (a copy; never mutates the input). An unknown key
 * falls back to the first column, so a stray route segment renders a sane default
 * rather than an error. `tiebreak` keeps ties in a deterministic order.
 */
export function sortRows<T>(
  rows: readonly T[],
  columns: readonly SortColumn<T>[],
  key: string | undefined,
  tiebreak: (row: T) => string,
): { rows: T[]; active: SortColumn<T> } {
  const active = columns.find((c) => c.key === key) ?? columns[0];
  return { rows: [...rows].sort(compare(active, tiebreak)), active };
}

/** The static-route path for a sort key under a base path (undefined key = the base). */
export function sortHref(basePath: string, key: string, defaultKey: string): string {
  const base = basePath.endsWith("/") ? basePath : `${basePath}/`;
  return key === defaultKey ? base : `${base}${key}/`;
}

/** One group in a build-time summary: the group label and how many rows fall in it. */
export interface SummaryBucket {
  label: string;
  count: number;
}

/**
 * Summarise rows into counts per group, in descending count order (largest group
 * first), with a stable label tiebreak. This is the honest "grouping / summarisation"
 * band a large table carries so a reader sees the shape (e.g. "180 ok · 20 degraded ·
 * 10 failing") before the rows — never a fabricated total, only counts of what is
 * present.
 */
export function summariseBy<T>(rows: readonly T[], group: (row: T) => string): SummaryBucket[] {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const label = group(row);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}
