// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P36.34 repair (JUR-04 / ADR-155): `/search/index.json` — the quick-filter
// island's dossier rows ride a fetched `sig.search-index/1` document, never
// the serialized island props (the one unbounded list stays out of the T2
// document bytes). The shared mapping emits one SearchItem per index row —
// keyed grouped rows and the flat demos alike — so a regression that drops
// the dossiers from the filter fails here.
import { describe, expect, it } from "vitest";
import { dossierSearchItems, SEARCH_INDEX_SCHEMA } from "../../src/lib/search-index";
import { getDossierIndex } from "../../src/lib/data";

const items = dossierSearchItems();
const rows = getDossierIndex();

describe("dossierSearchItems — the fetched quick-filter index (sig.search-index/1)", () => {
  it("names the emitted document's schema", () => {
    expect(SEARCH_INDEX_SCHEMA).toBe("sig.search-index/1");
  });

  it("emits one dossier item per index row — keyed corpus + flat demos", () => {
    expect(items).toHaveLength(rows.length);
    expect(rows.length).toBeGreaterThan(0);
    for (const item of items) {
      expect(item.kind).toBe("dossier");
      expect(item.label.length).toBeGreaterThan(0);
      expect(item.sublabel.length).toBeGreaterThan(0);
    }
  });

  it("links every item through its /dossier/<slug>/ page (JUR-011 reachability)", () => {
    const slugs = new Set(rows.map((d) => d.slug));
    for (const item of items) {
      const m = /^\/dossier\/(.+)\/$/.exec(item.href);
      expect(m, `${item.href} is a dossier path`).not.toBeNull();
      expect(slugs.has(m![1]!)).toBe(true);
    }
  });

  it("carries the grouped corpus — a name typed into the filter finds a keyed dossier (F-105)", () => {
    const usa = items.find((i) => i.href === "/dossier/usa/");
    expect(usa, "the keyed United States row is listed").toBeDefined();
    expect(usa!.label.toLowerCase()).toContain("united states");
    const flat = items.find((i) => i.href === "/dossier/oklahoma-city/");
    expect(flat, "the flat worked example is still listed").toBeDefined();
  });
});
