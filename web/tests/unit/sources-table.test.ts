// SPDX-License-Identifier: Apache-2.0
// P36.48 (UX9-3; SIG-TRANSP-001/028/033) — the sources table model fixtures.
// Every leg asserts an invariant, never a living record (OM-15).
import { describe, expect, it } from "vitest";
import {
  EXPORT_COLUMNS,
  FACET_DIMS,
  VIEWS,
  azIndex,
  facetRoutes,
  facetRows,
  freshnessVerdict,
  getTableRows,
  sortRoutesFor,
  sortTable,
  tableCsv,
  tableSchema,
  derivedStatus,
} from "../../src/lib/sources-table";
import { SOURCE_ROWS_DOC_FIXTURE } from "../../src/lib/source-counts";

const { rows } = getTableRows();

describe("the canonical row set (SIG-TRANSP-001)", () => {
  it("carries one row per registry row, sorted by name", () => {
    expect(rows.length).toBe(SOURCE_ROWS_DOC_FIXTURE.sources.length);
    const names = rows.map((r) => r.name);
    expect([...names].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))).toEqual(names);
  });

  it("every K9 §4.1 column is a value or a named absence token", () => {
    for (const r of rows) {
      expect(r.freshnessState).toBeTruthy();
      expect(r.lifecycle).toBeTruthy();
      expect(r.downloadToken).toBeTruthy();
      expect(typeof r.registryOnly).toBe("boolean");
    }
  });
});

describe("sorting (SIG-TRANSP-028, K9 C-3)", () => {
  it("absence tokens sort last in BOTH directions", () => {
    for (const key of Object.keys(rows.length ? { source: 1, publisher: 1, claims: 1 } : {})) {
      for (const dir of ["asc", "desc"] as const) {
        const sorted = sortTable(rows, key, dir);
        const absentIdx = sorted.findIndex(
          (r) => (key === "claims" ? r.publishedClaims : key === "publisher" ? r.publisher : r.name) == null ||
            (key === "publisher" && r.publisher === "publisher_not_recorded"),
        );
        const lastReal = sorted.map((r, i) => ({ r, i })).filter(({ r }) =>
          key === "claims" ? r.publishedClaims !== null : key === "publisher" ? r.publisher !== "publisher_not_recorded" : true,
        );
        if (absentIdx !== -1 && lastReal.length > 0) {
          expect(absentIdx).toBeGreaterThanOrEqual(lastReal[lastReal.length - 1]!.i);
        }
      }
    }
  });

  it("every sortable view column emits both directions", () => {
    for (const view of Object.keys(VIEWS) as (keyof typeof VIEWS)[]) {
      const routes = sortRoutesFor(view);
      expect(routes.length).toBe(VIEWS[view].columns.length * 2);
      expect(new Set(routes.map((r) => r.col)).size).toBe(VIEWS[view].columns.length);
    }
  });

  it("name sort ascends case-folded; desc reverses", () => {
    const asc = sortTable(rows, "source", "asc").map((r) => r.name);
    const desc = sortTable(rows, "source", "desc").map((r) => r.name);
    expect(desc).toEqual([...asc].reverse());
  });
});

describe("facets (K9 §6.1)", () => {
  it("every dim emits a route per observed value; row sets match the predicate", () => {
    const routes = facetRoutes(rows);
    expect(routes.length).toBeGreaterThan(0);
    for (const dim of FACET_DIMS) {
      for (const v of new Set(rows.flatMap((r) => dim.values(r)))) {
        const hit = routes.find((r) => r.dim === dim.key && r.value === v);
        expect(hit, `facet ${dim.key}=${v}`).toBeTruthy();
        const set = facetRows(rows, dim.key, v);
        expect(set.length).toBe(hit!.count);
        expect(set.every((r) => dim.values(r).includes(v))).toBe(true);
      }
    }
  });
});

describe("the freshness verdict (K9 §5.1)", () => {
  it("registry-only rows are not_applicable; one-time loads keep their state", () => {
    const gated = SOURCE_ROWS_DOC_FIXTURE.sources.find((r) => r.lifecycle_state === "gated")!;
    expect(freshnessVerdict(gated, null, null).state).toBe("not_applicable");
    const seed = SOURCE_ROWS_DOC_FIXTURE.sources.find((r) => r.cadence?.one_time_load === true)!;
    expect(freshnessVerdict(seed, null, null).state).toBe("one_time_load");
  });
});

describe("derived redistribution + downloads", () => {
  it("published rows are download_host_pending until UX9-4", () => {
    for (const r of rows) {
      if (r.lifecycle === "published") expect(r.downloadToken).toBe("download_host_pending");
      if (r.lifecycle === "gated") expect(derivedStatus(SOURCE_ROWS_DOC_FIXTURE.sources.find((s) => s.source_id === r.sourceId)!)).toBe("withheld_pending_rights_review");
    }
  });
});

describe("exports (SIG-TRANSP-033)", () => {
  it("the CSV header is the export column registry, one row per source", () => {
    const csv = tableCsv(rows, "2026-08-20");
    const lines = csv.split("\r\n").filter((l) => l && !l.startsWith("#"));
    expect(lines[0]).toBe(EXPORT_COLUMNS.map((c) => c.name).join(","));
    expect(lines.length - 1).toBe(rows.length);
  });

  it("the Table Schema names every export column exactly once", () => {
    const schema = tableSchema("2026-08-20") as { fields: { name: string }[]; primaryKey: string };
    expect(schema.fields.map((f) => f.name)).toEqual(EXPORT_COLUMNS.map((c) => c.name));
    expect(schema.primaryKey).toBe("source_id");
  });
});

describe("the A–Z jump list", () => {
  it("one anchor per initial letter of the name sort", () => {
    const idx = azIndex(rows);
    expect(idx.length).toBeGreaterThan(0);
    const letters = new Set(idx.map((e) => e.letter));
    expect(letters.size).toBe(idx.length);
    expect(idx.every((e) => e.anchorId.startsWith("az-"))).toBe(true);
  });
});
