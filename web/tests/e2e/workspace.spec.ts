// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P32.15 (SIG-FIND-004, ADR-134): the shared `sig.workspace-state/1` contract —
// release / compartment / query / filters / focus / view in the versioned URL —
// proven end-to-end on the three investigation islands: deep links, reloads and
// Back/Forward restore the selected record and release; view switching carries
// compatible state; a record that leaves the filter scope clears with a visible
// announcement; unknown combinations fail visibly; compartment switching updates
// data and attribution; records without a public point remain navigable.
import { test, expect } from "@playwright/test";

test.describe("shared workspace state — deep links + restore (SIG-FIND-004)", () => {
  test("network: a deep-linked focus centres the ego view, and Back/Forward restores it", async ({
    page,
  }) => {
    // Deep link + reload restore the SELECTED record (focus= the node id).
    await page.goto("/network/?v=1&focus=agency:ocso&view=network");
    const island = page.getByTestId("network-island");
    await expect(island).toBeVisible();
    const ocso = page.getByTestId("graph-island-node").filter({ hasText: "Oklahoma County Sheriff" });
    await expect(ocso).toHaveAttribute("aria-pressed", "true");
    await page.reload();
    await expect(ocso).toHaveAttribute("aria-pressed", "true");

    // Selecting another node pushes a history entry; Back restores the deep link.
    const tulsa = page.getByTestId("graph-island-node").filter({ hasText: "Tulsa PD" });
    await tulsa.click();
    await expect(tulsa).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/focus=agency%3Atulsa|focus=agency:tulsa/);
    await page.goBack();
    await expect(ocso).toHaveAttribute("aria-pressed", "true");
    await page.goForward();
    await expect(tulsa).toHaveAttribute("aria-pressed", "true");
  });

  test("network: a focus that names no node stays navigable, never fabricated", async ({ page }) => {
    await page.goto("/network/?v=1&focus=ccby3:deployment:no-such&view=network");
    await expect(page.getByTestId("network-island")).toBeVisible();
    // The honest miss note + the default ego view still render.
    await expect(page.getByTestId("graph-focus-miss")).toBeVisible();
    await expect(page.getByTestId("graph-island-node").first()).toBeVisible();
    // And the released-record route is still offered (the demo release pins it).
    await expect(page.getByTestId("focus-record-link")).toBeVisible();
  });

  test("search: deep-linked q + focus restore the query and the selected record", async ({
    page,
  }) => {
    await page.goto("/search/?v=1&q=alpr&view=list");
    await expect(page.getByTestId("search-input")).toHaveValue("alpr");
    await expect(page.getByTestId("search-status")).toContainText("result");

    // Selecting a record opens the focus pane and writes focus= to the URL.
    const select = page.getByTestId("search-focus-item").first();
    await select.click();
    await expect(page.getByTestId("search-focus-pane")).toBeVisible();
    await expect(page.getByTestId("focus-record-link")).toBeVisible();
    const url = page.url();
    expect(url).toContain("focus=");

    // Reload restores the selection; the view links carry it to Map/Connections.
    await page.reload();
    await expect(page.getByTestId("search-focus-pane")).toBeVisible();
    const mapLink = page.getByTestId("view-link-map");
    const mapHref = await mapLink.getAttribute("href");
    expect(mapHref).toContain("/map/?");
    expect(mapHref).toContain("focus=");
    expect(mapHref).toContain("q=alpr");
    const netHref = await page.getByTestId("view-link-network").getAttribute("href");
    expect(netHref).toContain("/network/?");
    expect(netHref).toContain("focus=");
  });

  test("search: a query that removes the focused record clears it — announced, not silent", async ({
    page,
  }) => {
    await page.goto("/search/?v=1&view=list");
    await page.getByTestId("search-focus-item").first().click();
    await expect(page.getByTestId("search-focus-pane")).toBeVisible();
    // A query that excludes every listed site clears the selection (S4 §7).
    await page.getByTestId("search-input").fill("zzzzzznomatch");
    await expect(page.getByTestId("search-status")).toContainText("Selection cleared", {
      timeout: 5_000,
    });
    await expect(page.getByTestId("search-focus-pane")).toHaveCount(0);
  });

  test("search: the kind facet travels in the URL and narrows the groups", async ({ page }) => {
    await page.goto("/search/?v=1&kind=source&view=list");
    await expect(page.getByTestId("search-group-source")).toBeVisible();
    await expect(page.getByTestId("search-group-site")).toHaveCount(0);
    await expect(page.getByTestId("search-group-dossier")).toHaveCount(0);
    // Unchecking the last facet restores "all" — the canonical empty default.
    await page.getByTestId("search-kind-facets").getByRole("checkbox", { name: "Sources" }).click();
    await expect(page.getByTestId("search-group-site")).toBeVisible();
  });

  test("release pinning is restored and carried across views", async ({ page }) => {
    await page.goto("/search/?v=1&release=p-demo-release&view=list");
    await expect(page.getByTestId("workspace-release")).toContainText("p-demo-release");
    const mapHref = await page.getByTestId("view-link-map").getAttribute("href");
    expect(mapHref).toContain("release=p-demo-release");
  });

  test("unknown state values fail visibly rather than silently defaulting", async ({ page }) => {
    await page.goto("/network/?v=9&view=galaxy&page=x");
    await expect(page.getByTestId("workspace-issues")).toBeVisible();
    await expect(page.getByTestId("workspace-issues")).toContainText(/version "9"/);
  });
});

test.describe("map island — focus + compartment switch (SIG-FIND-004)", () => {
  test("a bare-id focus deep link centres and names the record", async ({ page }) => {
    await page.goto("/map/?v=1&focus=device:okc-001&view=map");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    const pane = page.getByTestId("map-focus-pane");
    await expect(pane).toBeVisible();
    await expect(pane).toContainText("Fixed ALPR — downtown corridor");
    // The view links preserve the selection.
    await expect(page.getByTestId("focus-network-link")).toBeVisible();
    await page.reload();
    await expect(page.getByTestId("map-focus-pane")).toBeVisible();
  });

  test("a record-key focus stays navigable even when the record cannot load here", async ({
    page,
  }) => {
    // The demo release pins a publication id but no /r/ tree is staged in the
    // fixture build — the pane states the honest miss AND links the canonical
    // released-record route (never a fabricated detail page).
    await page.goto("/map/?v=1&focus=sig_graph:deployment:missing&view=map");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    const pane = page.getByTestId("map-focus-pane");
    await expect(pane).toContainText("could not be loaded", { timeout: 10_000 });
    await expect(page.getByTestId("focus-record-link")).toHaveAttribute(
      "href",
      "/r/p-0000000000000000000000000000000000000000000000000000000000000001/c/sig_graph/entity/deployment/missing/",
    );
  });

  test("compartment switching updates the URL state and the attribution line", async ({
    page,
  }) => {
    await page.goto("/map/");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    const attribution = page.getByTestId("map-compartment-attribution");
    await expect(attribution).toContainText("All 1 licence compartment");
    await expect(attribution).toContainText("CC-BY-4.0");
    const toggle = page.getByTestId("map-compartment-sig_graph");
    await toggle.uncheck();
    await expect(attribution).toContainText("0 of 1 licence compartments");
    await expect(page).toHaveURL(/collection=/);
    // Forward/back restore the compartment selection.
    await toggle.check();
    await expect(attribution).toContainText("All 1 licence compartment");
    await page.goBack();
    await expect(attribution).toContainText("0 of 1 licence compartments");
  });

  test("the viewport is never written to the URL (S4 §8 transient state)", async ({ page }) => {
    await page.goto("/map/");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    // Pan/zoom through the MapLibre controls; z/lat/lon must stay out of the URL.
    await page.locator(".maplibregl-ctrl-zoom-in").click();
    expect(page.url()).not.toMatch(/[?&](z|lat|lon)=/);
  });
});

test.describe("keyboard operability (WCAG 2.2 AA)", () => {
  test("the network node buttons re-centre via keyboard alone", async ({ page }) => {
    await page.goto("/network/");
    const island = page.getByTestId("network-island");
    await expect(island).toBeVisible();
    // From the default ego centre (Oklahoma City PD) the first ring renders
    // the OKC Real-Time Crime Center — a real node button, keyboard-focusable.
    const target = page
      .getByTestId("graph-island-node")
      .filter({ hasText: "OKC Real-Time Crime Center" });
    await target.focus();
    await page.keyboard.press("Enter");
    await expect(target).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/focus=rtcc%3Aokc|focus=rtcc:okc/);
  });
});
