// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.20 (UXK0-4, SIG-UI-091, SIG-ENG-042) — the enhancement kit's pure-model
// unit contract: the table model's sort/filter/facet/CSV/URL-state halves,
// the cite formatters, the typeahead shard + match model, and the T1 module
// allow-list's shape (every recorded entry names a real emitted element).
import { describe, it, expect } from "vitest";
import { readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  compareCells,
  defaultState,
  facetValues,
  numericCell,
  paramsToState,
  rowMatchesFacets,
  rowMatchesQuery,
  sortOrder,
  stateToParams,
  toCsv,
  visibleRowOrder,
  type TableModel,
} from "../../src/elements/table-model";
import {
  CITE_FORMATS,
  formatCite,
  formatDateUS,
  type CiteFields,
} from "../../src/elements/cite-formats";
import {
  isShard,
  matchEntries,
  shardKey,
  type TypeaheadShard,
} from "../../src/elements/typeahead-model";
import t1ModuleEntries from "../e2e/t1-module-entries.json" with { type: "json" };

const MODEL: TableModel = {
  columns: [
    { index: 0, id: "name", label: "Name" },
    { index: 1, id: "rows", label: "Rows" },
    { index: 2, id: "licence", label: "Licence" },
  ],
  rows: [
    {
      cells: ["bravo", "10", "CC0-1.0"],
      facets: { licence: ["CC0-1.0"], credit: ["ok"] },
      licences: ["CC0-1.0"],
    },
    {
      cells: ["alpha", "2", "ODbL-1.0"],
      facets: { licence: ["ODbL-1.0"], credit: ["ok"] },
      licences: ["ODbL-1.0"],
      compartment: "osm",
    },
    {
      cells: ["charlie", "—", "CC-BY-4.0"],
      facets: { licence: ["CC-BY-4.0"], credit: ["under-correction"] },
      licences: ["CC-BY-4.0"],
    },
  ],
};

describe("table-model sorting", () => {
  it("orders numeric columns numerically, not lexically", () => {
    const state = { ...defaultState(), sort: "rows", dir: "asc" as const };
    const order = sortOrder(MODEL, state).map(
      (i) => MODEL.rows[i].cells[0],
    );
    // The absence cell always sorts last, in either direction.
    expect(order).toEqual(["alpha", "bravo", "charlie"]);
    const desc = sortOrder(MODEL, { ...state, dir: "desc" });
    expect(desc.map((i) => MODEL.rows[i].cells[0])).toEqual([
      "bravo",
      "alpha",
      "charlie",
    ]);
  });

  it("sorts text case-insensitively and keeps server order when unsorted", () => {
    const byName = sortOrder(MODEL, {
      ...defaultState(),
      sort: "name",
      dir: "asc",
    });
    expect(byName.map((i) => MODEL.rows[i].cells[0])).toEqual([
      "alpha",
      "bravo",
      "charlie",
    ]);
    expect(sortOrder(MODEL, defaultState())).toEqual([0, 1, 2]);
  });

  it("reads numeric cells only when the whole cell is a number", () => {
    expect(numericCell("8,088")).toBe(8088);
    expect(numericCell("12.5%")).toBe(12.5);
    expect(numericCell("ODbL-1.0")).toBeNull();
    expect(numericCell("")).toBeNull();
    expect(compareCells("—", "zzz")).toBeGreaterThan(0);
  });
});

describe("table-model filtering + facets", () => {
  it("text-matches across cells, case-insensitively", () => {
    expect(rowMatchesQuery(MODEL.rows[0], "BRAVO")).toBe(true);
    expect(rowMatchesQuery(MODEL.rows[0], "odbl")).toBe(false);
    expect(rowMatchesQuery(MODEL.rows[0], "")).toBe(true);
  });

  it("ANDs dimensions and ORs values within one dimension", () => {
    const row = MODEL.rows[1];
    expect(rowMatchesFacets(row, { licence: ["ODbL-1.0"] })).toBe(true);
    expect(
      rowMatchesFacets(row, { licence: ["ODbL-1.0", "CC0-1.0"] }),
    ).toBe(true);
    expect(rowMatchesFacets(row, { licence: ["CC0-1.0"] })).toBe(false);
    expect(
      rowMatchesFacets(row, {
        licence: ["ODbL-1.0"],
        credit: ["under-correction"],
      }),
    ).toBe(false);
  });

  it("counts facet values over the full row set", () => {
    const v = facetValues(MODEL.rows, "licence");
    expect(v.get("CC0-1.0")).toBe(1);
    expect(v.get("ODbL-1.0")).toBe(1);
    expect(facetValues(MODEL.rows, "credit").get("ok")).toBe(2);
  });

  it("visibleRowOrder composes query + facets + sort", () => {
    const state = {
      ...defaultState(),
      q: "c",
      facets: { credit: ["ok"] },
    };
    // "c" matches bravo? no — cells: bravo/10/CC0-1.0 → "c" matches CC0 → yes;
    // alpha/2/ODbL → "c" matches "ODbL-1.0"? no. charlie hidden by facet.
    const order = visibleRowOrder(MODEL, state);
    expect(order.map((i) => MODEL.rows[i].cells[0])).toEqual(["bravo"]);
  });
});

describe("table-model URL state", () => {
  const dims = ["licence", "credit"];

  it("round-trips a non-default state", () => {
    const state = {
      q: "osm",
      sort: "rows" as const,
      dir: "desc" as const,
      facets: { licence: ["ODbL-1.0"], credit: ["ok"] },
      hidden: ["licence"],
    };
    const params = `?${stateToParams(state).toString()}`;
    expect(paramsToState(params, MODEL, dims)).toEqual(state);
  });

  it("encodes only non-default keys", () => {
    expect(stateToParams(defaultState()).toString()).toBe("");
    expect(stateToParams({ ...defaultState(), q: "x" }).toString()).toBe("q=x");
  });

  it("drops fabricated parameters the model does not support", () => {
    const state = paramsToState(
      "?sort=bogus&dir=sideways&licence=nope,cC0-1.0&credit=ok&cols=name,zzz&other=x",
      MODEL,
      dims,
    );
    expect(state.sort).toBeNull();
    expect(state.facets.credit).toEqual(["ok"]);
    expect(state.facets.licence).toEqual([]); // "nope" invalid; "cC0-1.0" case-sensitive → dropped
    expect(state.hidden).toEqual(["name"]);
  });
});

describe("table-model CSV export", () => {
  it("carries licence provenance lines for the visible rows, compartment-named", () => {
    const csv = toCsv(MODEL, [0, 1], ["name", "licence"], "test view");
    const lines = csv.split("\n");
    expect(lines).toContain("# licence: CC0-1.0");
    expect(lines).toContain("# licence (osm compartment): ODbL-1.0");
    // The excluded row's licence never travels with the view.
    expect(lines.some((l) => l.includes("CC-BY-4.0"))).toBe(false);
    expect(lines).toContain("Name,Licence");
    expect(lines).toContain("bravo,CC0-1.0");
    expect(lines).toContain("alpha,ODbL-1.0");
    expect(csv.endsWith("\n")).toBe(true);
  });

  it("escapes commas, quotes and collapses whitespace", () => {
    const model: TableModel = {
      columns: [{ index: 0, id: "a", label: "A, B" }],
      rows: [{ cells: ['say "hi"'], facets: {}, licences: [] }],
    };
    const csv = toCsv(model, [0], ["a"], "v");
    expect(csv).toContain('"A, B"');
    expect(csv).toContain('"say ""hi"""');
  });
});

describe("cite-formats", () => {
  const fields: CiteFields = {
    title: "Sources and licences",
    release: "2026.08-abc1234",
    asOfWorld: "2026-08-20",
    asOfBelief: "2026-08-21",
    ruleset: "resolver-ruleset-2026.07",
    url: "https://surveillancegraph.org/s/rel-x/sources/",
    plain: "Cite: Sources and licences, SIG release 2026.08-abc1234 …",
  };

  it("offers plain, APA, Chicago and legal", () => {
    expect(CITE_FORMATS.map((f) => f.id)).toEqual([
      "plain",
      "apa",
      "chicago",
      "legal",
    ]);
  });

  it("plain returns the verbatim block text unchanged", () => {
    expect(formatCite(fields, "plain")).toBe(fields.plain);
  });

  it("APA restates author, year, title and URL", () => {
    const apa = formatCite(fields, "apa");
    expect(apa).toBe(
      "Surveillance Infrastructure Graph. (2026). Sources and licences. https://surveillancegraph.org/s/rel-x/sources/",
    );
    // The unreleased build carries no release → a retrieval date is honest.
    expect(formatCite({ ...fields, release: "" }, "apa")).toContain(
      "Retrieved August 21, 2026,",
    );
  });

  it("Chicago and legal restate the same fields", () => {
    expect(formatCite(fields, "chicago")).toBe(
      'Surveillance Infrastructure Graph. "Sources and licences." ' +
        "Data as of August 20, 2026. Accessed August 21, 2026. " +
        "https://surveillancegraph.org/s/rel-x/sources/.",
    );
    expect(formatCite(fields, "legal")).toBe(
      "Surveillance Infrastructure Graph, Sources and licences, " +
        "https://surveillancegraph.org/s/rel-x/sources/ (data as of August 20, 2026)",
    );
  });

  it("formatDateUS renders ISO dates and passes through non-ISO", () => {
    expect(formatDateUS("2026-01-03")).toBe("January 3, 2026");
    expect(formatDateUS("n.d.")).toBe("n.d.");
  });
});

describe("typeahead-model", () => {
  it("derives the shard key from the first alnum run, lowercased", () => {
    expect(shardKey("Austin")).toBe("au");
    expect(shardKey("  Methodology")).toBe("me");
    expect(shardKey("3rd")).toBe("3r");
    expect(shardKey("x")).toBe("xx");
    expect(shardKey("—")).toBeNull();
  });

  it("validates the shard contract fail-closed", () => {
    const good: TypeaheadShard = {
      schema: "sig.typeahead-shard/1",
      key: "me",
      entries: [{ label: "Methodology", href: "/methodology/" }],
    };
    expect(isShard(good)).toBe(true);
    expect(isShard({ ...good, schema: "other/1" })).toBe(false);
    expect(isShard({ ...good, key: "ME!" })).toBe(false);
    expect(isShard({ ...good, entries: [{ label: "x" }] })).toBe(false);
    expect(isShard(null)).toBe(false);
  });

  it("ranks word-prefix above substring and keeps shard order within a class", () => {
    const entries = [
      { label: "Mental health registry", href: "/a/" },
      { label: "Methodology", href: "/m/" },
      { label: "Enmeshment report", href: "/e/" },
      { label: "memoranda", href: "/x/" },
    ];
    const out = matchEntries(entries, "me");
    // Mental/methodology/memoranda all carry a word starting "me" (class 0,
    // shard order); enmeshment is a substring-only match (class 1).
    expect(out.map((e) => e.label)).toEqual([
      "Mental health registry",
      "Methodology",
      "memoranda",
      "Enmeshment report",
    ]);
    expect(matchEntries(entries, "")).toEqual([]);
    expect(matchEntries(entries, "zzz")).toEqual([]);
  });
});

describe("the T1 module-entry allow-list", () => {
  it("declares sig.t1-module-entries/1 with unique /_kit/ entries", () => {
    expect(t1ModuleEntries.schema).toBe("sig.t1-module-entries/1");
    const entries: string[] = t1ModuleEntries.entries;
    expect(new Set(entries).size).toBe(entries.length);
    for (const entry of entries) {
      expect(entry).toMatch(/^\/_kit\/sig-[\w-]+\.js$/);
    }
  });

  it("names exactly the element modules under src/elements/", () => {
    const dir = fileURLToPath(new URL("../../src/elements", import.meta.url));
    const emitted = readdirSync(dir)
      .filter((f) => /^sig-[\w-]+\.ts$/.test(f))
      .map((f) => `/_kit/${f.replace(/\.ts$/, ".js")}`)
      .sort();
    expect([...t1ModuleEntries.entries].sort()).toEqual(emitted);
  });
});
