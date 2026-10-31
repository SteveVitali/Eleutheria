// SPDX-License-Identifier: Apache-2.0
import { describe, it, expect } from "vitest";
import {
  buildJurisdictionLookup, buildSitesModel, emittedSiteLists, sitePage,
  sitesCsv, siteAnchor, dossierSitesPagePath, publishablePoint,
  resolveDossierSlug, buildPlaceTable, SITE_PAGE_SIZE,
} from "../../src/lib/sites";
import type { MapAsset } from "../../src/lib/map";
import { MAP_ASSETS } from "../../src/lib/map-network-fixture";
import { getDossiers, getDossierIndex, getJurisdictionKeyMap } from "../../src/lib/data";

const asset = (id: string, jkey: string | null, tier = 0, lat: number | null = 1, lon: number | null = 1): MapAsset => ({
  id, label: id, jurisdiction: jkey ?? "X", jurisdictionKey: jkey, tier: tier as 0,
  lat, lon, precision: "p", sources: ["s"], status: "single source",
  compartment: "c", licence: "L",
});

const dossiers = getDossiers();
const lookup = buildJurisdictionLookup(dossiers, getDossierIndex(), getJurisdictionKeyMap());

describe("P36.36 sites model", () => {
  it("resolves a place key to its deepest dossier", () => {
    expect(resolveDossierSlug(asset("a", "us.census.geoid.place:4064000"), lookup)).toBe("usa/ok/oklahoma-city-4064000");
    expect(resolveDossierSlug(asset("b", "us.census.geoid.county:48201"), lookup)).toBe("usa/tx/harris-county-48201");
    expect(resolveDossierSlug(asset("c", "iso3166-2:US-OK"), lookup)).toBe("usa/ok");
    expect(resolveDossierSlug(asset("d", "iso3166-1:FR"), lookup)).toBe("fra");
    expect(resolveDossierSlug(asset("e", "us.census.geoid.place:9999999"), lookup)).toBeNull();
  });
  it("tier-3 and no-point records never print a point", () => {
    expect(publishablePoint(asset("t", "x", 3, 1, 1))).toBe(false);
    expect(publishablePoint(asset("u", "x", 0, null, null))).toBe(false);
  });
  it("emits lists only where ≥ 1 located record, ≤ SITE_PAGE_SIZE rows per page", () => {
    const model = buildSitesModel(MAP_ASSETS, lookup);
    const lists = emittedSiteLists(model);
    expect(lists.length).toBeGreaterThan(0);
    for (const l of lists) {
      expect(l.located).toBeGreaterThan(0);
      for (let p = 1; p <= l.pages; p += 1) expect(sitePage(l, p).rows.length).toBeLessThanOrEqual(SITE_PAGE_SIZE);
    }
    const harris = lists.find((l) => l.slug === "usa/tx/harris-county-48201")!;
    expect(harris.pages).toBe(2); // the 122-row fixture block paginates
    expect(sitePage(harris, 2).rows.length).toBe(harris.rows.length - SITE_PAGE_SIZE);
    // Every row anchor is the record key verbatim.
    expect(siteAnchor("device:okc-001")).toBe("device:okc-001");
    expect(dossierSitesPagePath("usa/ok", 2)).toBe("dossier/usa/ok/sites/page/2/");
  });
  it("CSV carries licence comment lines + every row, not the page slice", () => {
    const model = buildSitesModel(MAP_ASSETS, lookup);
    const harris = emittedSiteLists(model).find((l) => l.slug === "usa/tx/harris-county-48201")!;
    const csv = sitesCsv(harris, { dossierName: "Harris County", asOf: "2026-09-30", licence: "CC-BY-4.0" });
    expect(csv.startsWith("# SIG dossier sites list")).toBe(true);
    expect(csv).toContain("# licence:");
    expect(csv.split("\n").filter((l) => l.startsWith("device:")).length).toBe(harris.rows.length);
  });
  it("the places table groups by country and reconciles the lists", () => {
    const model = buildSitesModel(MAP_ASSETS, lookup);
    const table = buildPlaceTable(model, dossiers);
    expect(table.totalRows).toBe(model.lists.size);
    const names = table.groups.map((g) => g.countryName);
    expect(names).toContain("United States");
    const okc = table.groups.flatMap((g) => g.rows).find((r) => r.slug === "usa/ok/oklahoma-city-4064000")!;
    expect(okc.hasSitesList).toBe(true);
    expect(okc.singleSourceShare).not.toBeNull();
    const fr = table.groups.flatMap((g) => g.rows).find((r) => r.slug === "fra")!;
    expect(fr.countryName).toBe("France");
  });
});
