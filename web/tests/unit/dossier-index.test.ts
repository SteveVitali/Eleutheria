// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P36.34 (K4 JUR-04, SIG-JUR-001…008/010/011): the grouped dossier index's
// model + the fixture corpus it renders — grouping order, conservation
// (JUR-007), index↔dossier parity (JUR-006 AT), sort/facet/A–Z coverage
// (JUR-011: ≤3 clicks by hierarchy or letter), and the country-derived
// publication regime (JUR-010).
import { describe, expect, it } from "vitest";
import {
  azGroups,
  facetIndex,
  facetValues,
  groupIndex,
  indexFigureSpecs,
  isKeyedIndexRow,
  publicationRegime,
  rowName,
  sortIndex,
  INDEX_FIELD_DEFINITIONS,
} from "../../src/lib/dossier-index";
import { GROUPED_FIXTURE_DOSSIERS, GROUPED_INDEX_FIXTURE } from "../../src/lib/dossier-grouped-fixture";
import { getDossierIndex } from "../../src/lib/data";
import { validateDossier } from "../../src/lib/dossier";

const rows = getDossierIndex();
const keyed = rows.filter(isKeyedIndexRow);
const groups = groupIndex(rows);
const bySlug = new Map(GROUPED_FIXTURE_DOSSIERS.map((d) => [d.slug, d]));

const flatten = (n: { children: unknown[] }) =>
  [n, ...n.children.flatMap((c) => flatten(c as typeof n))] as {
    row: (typeof rows)[number];
    children: unknown[];
  }[];

describe("groupIndex (SIG-JUR-006)", () => {
  it("puts the United States first, then other countries A–Z", () => {
    expect(groups.unitedStates?.row.jkey).toBe("iso3166-1:US");
    const names = groups.otherCountries.map((c) => c.row.display_name);
    expect(names).toEqual(["Canada", "France", "Germany"]);
    // Every keyed row lands inside a group — none orphaned.
    const inTree = (groups.unitedStates ? flatten(groups.unitedStates) : [])
      .concat(groups.otherCountries.flatMap(flatten));
    expect(inTree.length).toBe(keyed.length);
  });

  it("nests states, counties and places under their parents", () => {
    const ok = groups.unitedStates!.children.find((c) => c.row.jkey === "iso3166-2:US-OK")!;
    expect(ok.children.map((c) => c.row.jkey)).toContain("us.census.geoid.county:40109");
    const county = ok.children.find((c) => c.row.jkey === "us.census.geoid.county:40109")!;
    expect(county.children.map((c) => c.row.jkey)).toEqual(["us.census.geoid.place:4064000"]);
  });

  it("climbs a no-page registry parent (Norman under Cleveland County → Oklahoma)", () => {
    const ok = groups.unitedStates!.children.find((c) => c.row.jkey === "iso3166-2:US-OK")!;
    expect(ok.children.map((c) => c.row.jkey)).toContain("us.census.geoid.place:4055000");
    // The no-page county never appears as an index row.
    expect(keyed.some((r) => r.jkey === "us.census.geoid.county:40131")).toBe(false);
  });
});

describe("hierarchy conservation + index↔dossier parity (SIG-JUR-007/006)", () => {
  it("every parent's records equal Σ children + placed_only_here", () => {
    const byJkey = new Map(keyed.map((r) => [r.jkey, r]));
    // Registry children incl. no-page rows — from the fixture dossiers.
    for (const d of GROUPED_FIXTURE_DOSSIERS) {
      const kidSum = (d.children ?? []).reduce((s, c) => s + (c.records ?? 0), 0);
      expect(d.rollup!.records).toBe(kidSum + (d.rollup!.records_placed_only_here ?? 0));
      // Index row parity with the dossier JSON.
      const row = byJkey.get(d.jurisdiction_key)!;
      expect(row.records).toBe(d.rollup!.records);
      expect(row.children!.count).toBe((d.children ?? []).length);
    }
  });

  it("every index row has a dossier page and vice versa", () => {
    expect(keyed.map((r) => r.slug).sort()).toEqual(
      GROUPED_FIXTURE_DOSSIERS.map((d) => d.slug).sort(),
    );
    for (const d of GROUPED_FIXTURE_DOSSIERS) validateDossier(d);
  });
});

describe("sort / facet / A–Z (SIG-JUR-011)", () => {
  it("sorts each sibling group by the key without orphaning rows", () => {
    const g = groupIndex(rows);
    sortIndex(g.unitedStates, "records");
    const recs = g.unitedStates!.children.map((c) => c.row.records!);
    expect(recs).toEqual([...recs].sort((a, b) => b - a));
  });

  it("facets by level, single-source and evidence-type", () => {
    expect(facetIndex(rows, "level", "place").map((r) => r.jkey)).toEqual(
      expect.arrayContaining(["us.census.geoid.place:4064000", "us.census.geoid.place:4055000"]),
    );
    expect(facetIndex(rows, "single-source", "yes").map((r) => r.jkey)).toContain("us.census.geoid.place:4064000");
    expect(facetIndex(rows, "evidence-type", "non-site-evidence").map((r) => r.jkey)).toEqual(["us.census.geoid.place:4055000"]);
    for (const dim of ["level", "single-source", "evidence-type"] as const) {
      for (const v of facetValues(rows, dim)) {
        expect(facetIndex(rows, dim, v).length).toBeGreaterThan(0);
      }
    }
  });

  it("covers every row under exactly one letter", () => {
    const letters = azGroups(rows);
    const covered = [...letters.values()].flat().length;
    expect(covered).toBe(rows.length);
    expect(letters.get("o")!.map((r) => rowName(r))).toContain("Oklahoma City, Oklahoma, United States");
  });
});

describe("publication regime (SIG-JUR-010)", () => {
  it("derives the regime from the country key; no adapter → conservative", () => {
    expect(publicationRegime(keyed.find((r) => r.jkey === "us.census.geoid.place:4064000")!)!.profile).toBe("US-DEFAULT");
    const de = publicationRegime(keyed.find((r) => r.jkey === "iso3166-1:DE")!)!;
    expect(de.adapter).toBe(false);
    expect(de.profile).toBe("UNKNOWN");
    expect(publicationRegime(keyed.find((r) => r.jkey === "iso3166-1:FR")!)!.profile).toBe("FR-GDPR");
  });
});

describe("figure registry + named definitions", () => {
  it("registers a figure spec per rendered numeral", () => {
    const specs = indexFigureSpecs(keyed);
    expect(specs.map((s) => s.id)).toContain("r0-records");
    const ids = specs.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("every K4 §5.2 row field carries a named definition", () => {
    expect(INDEX_FIELD_DEFINITIONS.map((d) => d.id)).toEqual([
      "place", "records", "located", "sources", "evidence-types",
      "open-questions", "disagreements", "freshness", "children",
      "publication-regime",
    ]);
  });
});
