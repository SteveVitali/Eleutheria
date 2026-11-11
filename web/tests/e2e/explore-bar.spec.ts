// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.57 (VIZ-03, SIG-UI-055/126; cites SIG-UI-059/060): the explore bar and
// scoped-search placement — the three links minted as canonical
// `sig.workspace-state/2` carrying the dossier's jurisdiction key; the
// unapplied-facet notice on every target that cannot apply a received facet
// (NEW-1/UXR-10); and K5 §5.5's "Show on the map" control on the sources
// explorer rows. Fixture-verified over the committed corpus; the capstone
// journey O1 legs this row owns walk the Harris County dossier.
import { test, expect } from "@playwright/test";

const OK_JKEY_ENC = "iso3166-2%3AUS-OK";
const OKC_JKEY = "us.census.geoid.place:4064000";
const OKC_JKEY_ENC = "us.census.geoid.place%3A4064000";

test.describe("the dossier explore bar (SIG-UI-126)", () => {
  test("the three links carry sig.workspace-state/2 + the dossier's jkey", async ({
    page,
  }) => {
    await page.goto("/dossier/usa/ok/");
    await expect(page.getByTestId("dossier-explore-bar")).toBeVisible();
    const map = await page.getByTestId("explore-map").getAttribute("href");
    expect(map).toContain("/map/?v=2");
    expect(map).toContain("view=map");
    expect(map).toContain(`jurisdiction=${OK_JKEY_ENC}`);
    const graph = await page.getByTestId("explore-network").getAttribute("href");
    expect(graph).toContain("/explore/?v=2");
    expect(graph).toContain("view=graph");
    expect(graph).toContain(`jurisdiction=${OK_JKEY_ENC}`);
    const search = await page.getByTestId("explore-search").getAttribute("href");
    expect(search).toContain("/search/?v=2");
    expect(search).toContain("view=list");
    expect(search).toContain(`jurisdiction=${OK_JKEY_ENC}`);
  });

  test("a facet the target cannot apply is visibly named — on every explore link target (SIG-UI-060)", async ({
    page,
  }) => {
    // NEW-1/UXR-10: the links carry the jurisdiction facet; a surface that
    // cannot apply it says so visibly rather than showing unfiltered results
    // as filtered. P37.27 (GX-09b): the explorer APPLIES jurisdiction now —
    // its leg asserts the applied-filter disclosure (SIG-UI-060's other half);
    // map and search still land on the not-applied notice.
    await page.goto(`/map/?v=2&view=map&jurisdiction=${OK_JKEY_ENC}`);
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("facet-not-applied")).toContainText(
      "jurisdiction filter",
    );
    await page.goto(`/explore/?v=2&view=graph&jurisdiction=${OK_JKEY_ENC}`);
    await expect(page.getByTestId("explore-island")).toBeVisible();
    await expect(page.getByTestId("active-filters")).toContainText("filter");
    await page.goto(`/search/?v=2&view=list&jurisdiction=${OK_JKEY_ENC}`);
    await expect(page.getByTestId("facet-not-applied")).toContainText(
      "jurisdiction filter",
    );
  });

  test("a surface honouring the received parameter shows no unapplied notice", async ({
    page,
  }) => {
    // Notice honesty, the other half: `q` IS applied by the search surface —
    // no facet-not-applied may appear.
    await page.goto("/search/?v=2&view=list&q=flock");
    await expect(page.getByTestId("facet-not-applied")).toHaveCount(0);
  });
});

test.describe("'Show on the map' (K5 §5.5)", () => {
  test("each contributing source row carries the scoped map link + the records list", async ({
    page,
  }) => {
    await page.goto("/dossier/usa/ok/oklahoma-city-4064000/sources/");
    // One control cell per contributing row — every fixture row here has
    // point-located records, so every cell carries both links.
    const cells = page.getByTestId("dsrc-showmap-cell");
    expect(await cells.count()).toBe(2);
    const row = page.locator('tr[data-source-id="okc_camera_registry"]');
    const mapHref = await row
      .getByTestId("dsrc-show-on-map")
      .getAttribute("href");
    expect(mapHref).toContain("/map/?v=2");
    expect(mapHref).toContain("view=map");
    expect(mapHref).toContain(`jurisdiction=${OKC_JKEY_ENC}`);
    expect(mapHref).toContain("source=okc_camera_registry");
    const listHref = await row
      .getByTestId("dsrc-source-records")
      .getAttribute("href");
    // The no-JS list is the release-pinned federated route (K3 SRCH-04):
    // type=record + the scope facets + format=html.
    expect(listHref).toContain("/v1/releases/");
    expect(listHref).toContain("/search?");
    expect(listHref).toContain("type=record");
    expect(listHref).toContain("format=html");
    expect(listHref).toContain(`jurisdiction=${OKC_JKEY_ENC}`);
    expect(listHref).toContain("source=okc_camera_registry");
  });

  test("the map link's target names the facets it cannot apply", async ({
    page,
  }) => {
    await page.goto(
      `/map/?v=2&view=map&jurisdiction=${OKC_JKEY_ENC}&source=okc_camera_registry`,
    );
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    const notice = page.getByTestId("facet-not-applied");
    await expect(notice).toContainText("jurisdiction filter");
    await expect(notice).toContainText("source filter");
  });
});

test.describe("capstone journey O1 legs (K13 §8)", () => {
  test("the county dossier's explore + scoped-search + per-source map controls scope to its jkey", async ({
    page,
  }) => {
    // O1: "Who runs what in my county or city?" — the legs this row owns:
    // the sideways explore links, the scoped search form, and the per-source
    // "Show on the map" controls all scope to the county's canonical key.
    await page.goto("/dossier/usa/tx/harris-county-48201/");
    await expect(page.getByTestId("dossier-explore-bar")).toBeVisible();
    const search = await page.getByTestId("explore-search").getAttribute("href");
    expect(search).toContain(
      "jurisdiction=us.census.geoid.county%3A48201",
    );
    await expect(
      page.getByTestId("dossier-scoped-search-scope"),
    ).toHaveAttribute("value", "us.census.geoid.county:48201");
    await page.goto("/dossier/usa/tx/harris-county-48201/sources/");
    const row = page.locator('tr[data-source-id="demo_state_registry_01"]');
    await expect(row.getByTestId("dsrc-show-on-map")).toBeVisible();
    const mapHref = await row
      .getByTestId("dsrc-show-on-map")
      .getAttribute("href");
    expect(mapHref).toContain(
      "jurisdiction=us.census.geoid.county%3A48201",
    );
  });
});
