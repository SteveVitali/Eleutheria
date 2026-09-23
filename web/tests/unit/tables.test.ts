// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Build-time large-table UX (§15, SIG-UI-034/037): static-link sorting + grouping /
// summarisation, computed at build time so the table stays usable and zero-JS.
import { describe, it, expect } from "vitest";
import { sortRows, sortHref, summariseBy } from "../../src/lib/tables";
import type { SortColumn } from "../../src/lib/tables";

interface Row {
  name: string;
  status: string;
  count: number;
}

const ROWS: Row[] = [
  { name: "charlie", status: "ok", count: 5 },
  { name: "alpha", status: "degraded", count: 20 },
  { name: "bravo", status: "ok", count: 1 },
  { name: "delta", status: "failing", count: 20 },
];

const COLUMNS: SortColumn<Row>[] = [
  { key: "name", label: "Name", value: (r) => r.name },
  { key: "status", label: "Status", value: (r) => r.status },
  { key: "count", label: "Count", value: (r) => r.count, direction: "desc" },
];

const tiebreak = (r: Row) => r.name;

describe("sortRows (static-link sorting)", () => {
  it("sorts ascending by a string column and reports the active column", () => {
    const { rows, active } = sortRows(ROWS, COLUMNS, "name", tiebreak);
    expect(rows.map((r) => r.name)).toEqual(["alpha", "bravo", "charlie", "delta"]);
    expect(active.key).toBe("name");
  });

  it("sorts descending by a numeric column with a stable tiebreak", () => {
    const { rows } = sortRows(ROWS, COLUMNS, "count", tiebreak);
    // 20s first (desc); the two 20s broken by name ascending (stable, deterministic).
    expect(rows.map((r) => r.name)).toEqual(["alpha", "delta", "charlie", "bravo"]);
  });

  it("falls back to the first column for an unknown key", () => {
    const { active } = sortRows(ROWS, COLUMNS, "nonsense", tiebreak);
    expect(active.key).toBe("name");
  });

  it("falls back to the first column for an undefined key (the base route)", () => {
    const { active } = sortRows(ROWS, COLUMNS, undefined, tiebreak);
    expect(active.key).toBe("name");
  });

  it("never mutates the input array", () => {
    const before = ROWS.map((r) => r.name);
    sortRows(ROWS, COLUMNS, "count", tiebreak);
    expect(ROWS.map((r) => r.name)).toEqual(before);
  });
});

describe("sortHref (pre-rendered sort routes)", () => {
  it("maps the default key to the base path and others to a sub-route", () => {
    expect(sortHref("/data-freshness/", "source", "source")).toBe("/data-freshness/");
    expect(sortHref("/data-freshness/", "status", "source")).toBe("/data-freshness/status/");
    expect(sortHref("/data-freshness", "stale", "source")).toBe("/data-freshness/stale/");
  });
});

describe("summariseBy (grouping / summarisation)", () => {
  it("counts rows per group in descending count order", () => {
    const buckets = summariseBy(ROWS, (r) => r.status);
    expect(buckets).toEqual([
      { label: "ok", count: 2 },
      { label: "degraded", count: 1 },
      { label: "failing", count: 1 },
    ]);
  });

  it("returns an empty summary for no rows (no fabricated buckets)", () => {
    expect(summariseBy([] as Row[], (r) => r.status)).toEqual([]);
  });
});
