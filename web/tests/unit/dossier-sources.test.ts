// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.52 (DSRC-02): the dossier-sources model — sort, pagination, threshold,
// previously-contributed, run_level_only, parity, the chart model + twin,
// and the regex pins. Tests assert invariants, never a living record.

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import {
  DOSSIER_SOURCES_SCHEMA,
  DSRC_PAGE_SIZE,
  DSRC_SORT_KEYS,
  SORT_ROUTE_THRESHOLD,
  contributingSources,
  dossierDownloadsPath,
  dossierSourcesJsonPath,
  dossierSourcesPagePath,
  dossierSourcesPath,
  dossierSourcesProvenance,
  dossierSourcesSortPagePath,
  dsrcArtifact,
  dsrcFigureSpecs,
  isDossierSourcesDoc,
  overTimeModel,
  paginateSources,
  previousContributors,
  previousContributionReason,
  sortSources,
  seenAt,
} from "../../src/lib/dossier-sources";
import { DOSSIER_SOURCES_FIXTURE } from "../../src/lib/dossier-sources-fixture";
import { isManifestArtifact } from "../../src/lib/figures";
import { assertProvenanceComplete } from "../../src/lib/provenance";

const usa = DOSSIER_SOURCES_FIXTURE["usa"]!;
const ok = DOSSIER_SOURCES_FIXTURE["usa/ok"]!;

describe("sig.dossier-sources/1 fixture corpus", () => {
  it("every fixture doc validates against the contract", () => {
    for (const [slug, doc] of Object.entries(DOSSIER_SOURCES_FIXTURE)) {
      expect(isDossierSourcesDoc(doc, slug), slug).toBe(true);
      expect(doc.schema).toBe(DOSSIER_SOURCES_SCHEMA);
      expect(doc.jurisdiction.slug_path).toBe(slug);
    }
  });

  it("per-source counts reconcile to the dossier totals (SIG-DSRC-001 sum rule)", () => {
    for (const doc of Object.values(DOSSIER_SOURCES_FIXTURE)) {
      expect(doc.sources.reduce((n, s) => n + s.records, 0)).toBe(doc.totals.records);
      expect(doc.sources.reduce((n, s) => n + s.claims, 0)).toBe(doc.totals.claims);
      expect(doc.totals.sources).toBe(doc.sources.length);
      for (const f of doc.figures) {
        if (f.sum_rule === "sum") {
          expect(
            f.by_source.reduce((n, b) => n + b.value, 0),
            `${doc.jurisdiction.slug_path}:${f.figure_id}`,
          ).toBe(f.value);
        }
      }
    }
  });

  it("usa carries > SORT_ROUTE_THRESHOLD sources — sort routes mint only there", () => {
    expect(usa.sources.length).toBeGreaterThan(SORT_ROUTE_THRESHOLD);
    for (const [slug, doc] of Object.entries(DOSSIER_SOURCES_FIXTURE)) {
      if (slug !== "usa") expect(doc.sources.length).toBeLessThanOrEqual(SORT_ROUTE_THRESHOLD);
    }
  });

  it("SIG-DSRC-008 parity: okc_camera_registry shows the same 38 records the source page claims", () => {
    const okc = DOSSIER_SOURCES_FIXTURE["usa/ok/oklahoma-city-4064000"]!;
    const row = okc.sources.find((s) => s.source_id === "okc_camera_registry")!;
    expect(row.records).toBe(38);
  });
});

describe("sort + pagination (K9 §6.1 precedent)", () => {
  it("default sort orders by records desc, ties on name", () => {
    const s = sortSources(ok.sources, "records");
    expect(s[0]!.source_id).toBe("okc_camera_registry");
    for (let i = 1; i < s.length; i += 1) {
      expect(s[i]!.records).toBeLessThanOrEqual(s[i - 1]!.records);
    }
  });

  it("absence cells sort LAST in every direction (run_level_only has no last_seen)", () => {
    const s = sortSources(ok.sources, "last-seen");
    const absentIdx = s.findIndex((x) => x.sightings === "run_level_only");
    expect(absentIdx).toBe(s.length - 1);
    const fs = sortSources(ok.sources, "first-seen");
    expect(fs.length).toBe(ok.sources.length);
  });

  it("paginateSources bounds pages and throws outside", () => {
    const p1 = paginateSources(usa.sources, 1);
    expect(p1.rows.length).toBe(DSRC_PAGE_SIZE >= usa.sources.length ? usa.sources.length : DSRC_PAGE_SIZE);
    expect(() => paginateSources(usa.sources, 99)).toThrow(/outside 1\.\./);
  });

  it("route helpers mint the right paths", () => {
    expect(dossierSourcesPath("usa/ok")).toBe("dossier/usa/ok/sources/");
    expect(dossierSourcesJsonPath("usa/ok")).toBe("dossier/usa/ok/sources/index.json");
    expect(dossierSourcesPagePath("usa/ok", 2)).toBe("dossier/usa/ok/sources/page/2/");
    expect(dossierSourcesSortPagePath("usa/ok", "name", 1)).toBe("dossier/usa/ok/sources/sort/name/");
    expect(DSRC_SORT_KEYS).toContain("first-seen");
  });
});

describe("honest-absence vocabulary (K5-P4)", () => {
  it("run_level_only rows carry no last_seen instant and a named reason", () => {
    const rlo = ok.sources.find((s) => s.sightings === "run_level_only")!;
    expect(seenAt(rlo.last_seen)).toBeNull();
    expect(typeof rlo.not_reasserted_in_latest_complete_run).toBe("object");
  });

  it("withdrawn / disappeared / never-re-asserted sources are 'previously contributed' (D-K5-3)", () => {
    const prev = previousContributors(usa);
    const ids = prev.map((s) => s.source_id);
    expect(ids).toContain("demo_state_registry_03"); // lifecycle withdrawn
    expect(ids).toContain("demo_state_registry_04"); // freshness disappeared
    for (const s of prev) {
      expect(previousContributionReason(s)).toBeTruthy();
    }
    expect(contributingSources(usa).length).toBe(usa.sources.length - prev.length);
  });
});

describe("provenance + figures (SIG-DSRC-004)", () => {
  it("the dossier-scope summary satisfies the six-component contract", () => {
    const p = dossierSourcesProvenance(ok);
    assertProvenanceComplete(p);
    expect(p.source_label).toBe("Sources with published claims");
    expect(p.source_independence_count).toBe(ok.provenance_summary.sources_with_published_claims);
  });

  it("figure specs resolve inside the artifact — never under /surfaces/site", () => {
    const specs = dsrcFigureSpecs(ok);
    const artifact = dsrcArtifact(ok.jurisdiction.slug_path);
    expect(isManifestArtifact(artifact)).toBe(true);
    for (const f of specs) {
      expect(f.artifact).toBe(artifact);
      expect(f.pointer.startsWith("/")).toBe(true);
      expect(f.breakdown).toBe(`#fig-${f.id}`);
    }
  });
});

describe("the over-time model + chart twin", () => {
  it("composes monthly series, top 8 + other, totals reconcile", () => {
    const m = overTimeModel(usa);
    expect(m.periods.length).toBeGreaterThan(0);
    expect(m.series.length).toBeLessThanOrEqual(9);
    for (let i = 0; i < m.periods.length; i += 1) {
      expect(m.series.reduce((n, s) => n + s.values[i]!, 0)).toBe(m.totals[i]);
    }
    const grand = usa.sources.reduce(
      (n, s) => n + s.series.reduce((x, p) => x + p.records_first_seen, 0),
      0,
    );
    expect(m.totals.reduce((a, b) => a + b, 0)).toBe(grand);
  });
});

describe("check-figures regex pin", () => {
  it("pins DOSSIER_SOURCES_RE byte-identical between lib + build check", () => {
    const lib = readFileSync("src/lib/figures.ts", "utf-8");
    const chk = readFileSync("scripts/check-figures.mjs", "utf-8");
    const libM = /DOSSIER_SOURCES_RE = (\/.+\/[gimsuy]*)/.exec(lib);
    const chkM = /DOSSIER_SOURCES_RE = (\/.+\/[gimsuy]*)/.exec(chk);
    expect(libM).not.toBeNull();
    expect(chkM).not.toBeNull();
    expect(chkM![1]).toBe(libM![1]);
    expect(isManifestArtifact("web/dossier_sources/usa/ok.json")).toBe(true);
    expect(isManifestArtifact("web/dossier_sources/usa/ok.runs.jsonl.gz")).toBe(false);
  });
});

// P36.53 (DSRC-03): the downloads model — path helper, materialised entries,
// and the county/place recipe block over the committed fixture corpus.
describe("per-dossier downloads (P36.53)", () => {
  it("dossierDownloadsPath names the T1 route", () => {
    expect(dossierDownloadsPath("usa/ok")).toBe("dossier/usa/ok/downloads/");
  });
  it("materialised dossiers carry per-compartment slice entries", () => {
    const usa = DOSSIER_SOURCES_FIXTURE["usa"];
    expect(usa.downloads.length).toBeGreaterThan(0);
    for (const g of usa.downloads) {
      expect(g.directory.startsWith(`by-dossier/usa/`)).toBe(true);
      const names = g.files.map((f) => f.name);
      expect(names).toContain("ATTRIBUTION.txt");
      expect(names).toContain("LICENCE.txt");
      for (const f of g.files) {
        expect(f.sha256).toHaveLength(64);
        expect(f.href).toContain("files.surveillancegraph.org");
      }
    }
    expect(usa.download_recipes?.materialised).toBe(true);
  });
  it("county/place dossiers are not materialised — the recipe block carries them", () => {
    const harris = DOSSIER_SOURCES_FIXTURE["usa/tx/harris-county-48201"];
    expect(harris.downloads).toHaveLength(0);
    const r = harris.download_recipes;
    expect(r?.materialised).toBe(false);
    expect(r?.duckdb.files[0]?.sites).toContain("jurisdiction_chain");
    expect(r?.api.endpoint).toContain("jurisdiction=us.census.geoid.county:48201");
  });
  it("source rows carry the by-source slice links", () => {
    const ok = DOSSIER_SOURCES_FIXTURE["usa/ok"];
    expect(ok.sources[0].downloads.length).toBeGreaterThan(0);
    expect(ok.sources[0].downloads[0].path.startsWith("by-source/")).toBe(true);
  });
});
