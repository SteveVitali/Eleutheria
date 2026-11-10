// SPDX-License-Identifier: Apache-2.0
// P36.57 (VIZ-03, SIG-UI-055/126; cites SIG-UI-059/060): the explore-bar and
// "Show on the map" link minter — canonical `sig.workspace-state/2` on every
// emitted URL, the facet set the dossier owns, and byte-stable round-trips.
import { describe, expect, it } from "vitest";
import {
  exploreLinks,
  showOnMapHref,
  sourceRecordsHref,
} from "../../src/lib/explore-links";
import {
  checkSurfaceConformance,
  parseWorkspaceState2,
  surfaceForPath,
} from "../../src/lib/workspace-state/index";

const JKEY = "iso3166-2:US-OK";
const COUNTY = "us.census.geoid.county:48201";

/** Split "path?query" — the helpers always emit a query string. */
function split(href: string): { path: string; query: string } {
  const i = href.indexOf("?");
  expect(i).toBeGreaterThan(0);
  return { path: href.slice(0, i), query: href.slice(i + 1) };
}

describe("exploreLinks — the dossier explore bar (SIG-UI-126)", () => {
  it("mints canonical v=2 links on the three T2 surfaces", () => {
    const links = exploreLinks(JKEY);
    expect(links.map).toBe(
      "/map/?v=2&view=map&jurisdiction=iso3166-2%3AUS-OK",
    );
    expect(links.graph).toBe(
      "/explore/?v=2&view=graph&jurisdiction=iso3166-2%3AUS-OK",
    );
    expect(links.search).toBe(
      "/search/?v=2&view=list&jurisdiction=iso3166-2%3AUS-OK",
    );
  });

  it("every emitted link parses clean and carries the dossier's jkey", () => {
    for (const [surface, href] of Object.entries(exploreLinks(JKEY))) {
      const { path, query } = split(href);
      const parsed = parseWorkspaceState2(query);
      expect(parsed.issues).toEqual([]);
      expect(parsed.unregistered).toEqual([]);
      expect(parsed.state.jurisdiction).toEqual([JKEY]);
      expect(surfaceForPath(path)).toBe(surface);
      // The conformance harness partitions every received parameter — the
      // facets are registered, so they are applied or visibly named, never
      // silently dropped (SIG-UI-060).
      const conf = checkSurfaceConformance(
        surface as "map" | "graph" | "search",
        parsed.present,
      );
      expect(conf.violations).toEqual([]);
      expect([...conf.applied, ...conf.noticed].sort()).toEqual(
        [...parsed.present].sort(),
      );
    }
  });

  it("an unkeyed dossier emits the links without the facet — never a guess", () => {
    const links = exploreLinks(null);
    for (const href of Object.values(links)) {
      expect(href).not.toContain("jurisdiction");
      const { query } = split(href);
      const parsed = parseWorkspaceState2(query);
      expect(parsed.state.jurisdiction).toEqual([]);
    }
    expect(links.map).toBe("/map/?v=2&view=map");
    expect(links.graph).toBe("/explore/?v=2&view=graph");
    expect(links.search).toBe("/search/?v=2&view=list");
  });
});

describe("showOnMapHref — K5 §5.5's per-source control", () => {
  it("scopes the map to jurisdiction + source under v=2", () => {
    expect(showOnMapHref(COUNTY, "demo_state_registry_01")).toBe(
      "/map/?v=2&view=map&jurisdiction=us.census.geoid.county%3A48201&source=demo_state_registry_01",
    );
  });

  it("drops only the missing facet when the dossier is unkeyed", () => {
    const href = showOnMapHref(null, "demo_seed_load");
    expect(href).toBe("/map/?v=2&view=map&source=demo_seed_load");
    expect(href).not.toContain("jurisdiction");
  });
});

describe("sourceRecordsHref — the no-JS records list (K3 SRCH-04)", () => {
  const action = "/v1/releases/p-test/search";
  it("emits type=record + format=html + the scope facets", () => {
    const href = sourceRecordsHref(action, COUNTY, "okc_camera_registry");
    expect(href.startsWith(`${action}?`)).toBe(true);
    const params = new URLSearchParams(href.slice(href.indexOf("?") + 1));
    expect(params.get("type")).toBe("record");
    expect(params.get("format")).toBe("html");
    expect(params.get("jurisdiction")).toBe(COUNTY);
    expect(params.get("source")).toBe("okc_camera_registry");
  });

  it("an unkeyed dossier scopes by source alone", () => {
    const href = sourceRecordsHref(action, null, "demo_seed_load");
    const params = new URLSearchParams(href.slice(href.indexOf("?") + 1));
    expect(params.get("jurisdiction")).toBeNull();
    expect(params.get("source")).toBe("demo_seed_load");
  });
});
