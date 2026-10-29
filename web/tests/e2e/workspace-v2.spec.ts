// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.21 (SIG-UI-052/059/060/093; K13 UXR-09/UXR-10, K0 §4.5; ADR-155/225):
// the `sig.workspace-state/2` surface behaviour — v2 deep links restore, the
// canonicalisations (bbox→at, kind=site→type=record, legacy jkeys,
// view=network→graph) are visible receipts, unregistered parameters are
// refused loudly, "cite this view" names the snapshot-pinned form, every T2
// document carries noindex,follow + the base canonical, and Back/Forward
// restores v2 state.
import { test, expect } from "@playwright/test";

const T2 = [
  { path: "/map/", surface: "map" },
  { path: "/network/", surface: "graph" },
  { path: "/search/", surface: "search" },
] as const;

test.describe("T2 indexing posture + cite this view (K13 §2.5, K0 §4.5)", () => {
  for (const { path, surface } of T2) {
    test(`${path} carries noindex,follow, the base canonical and the cite affordance`, async ({
      page,
    }) => {
      await page.goto(`${path}?v=2&focus=x`);
      // A static build emits one head per route — the directive is on the
      // document, so the parameter-space of a T2 surface is never the
      // indexable copy; the canonical stays the base surface.
      await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
        "content",
        "noindex,follow",
      );
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
        "href",
        `https://surveillancegraph.org${path}`,
      );
      const cite = page.getByTestId("cite-this-view");
      await expect(cite).toBeVisible();
      await expect(cite).toContainText(`/s/p-`);
      // The minted form is the snapshot-pinned v2 URL (J3 §8.1 interim —
      // shown as text until TX-13b's snapshots exist, never a dead link).
      await expect(cite).toContainText(`/${surface === "graph" ? "network" : surface}/`);
      await expect(cite).toContainText("v=2");
    });
  }
});

test.describe("v2 deep links (SIG-UI-093)", () => {
  test("a v2 focus deep link on the map centres and names the record", async ({
    page,
  }) => {
    await page.goto("/map/?v=2&view=map&focus=device:okc-001");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("map-focus-pane")).toBeVisible();
    await expect(page.getByTestId("map-focus-pane")).toContainText(
      "Fixed ALPR — downtown corridor",
    );
  });

  test("a v2 compartment selection deep link restores on the map", async ({ page }) => {
    await page.goto("/map/?v=2&view=map&collection=");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("map-compartment-attribution")).toContainText(
      "0 of 1 licence compartments",
    );
  });

  test("Back/Forward restores v2 state (SIG-UI-093)", async ({ page }) => {
    await page.goto("/search/?v=2&view=list");
    await page.getByTestId("search-focus-item").first().click();
    await expect(page.getByTestId("search-focus-pane")).toBeVisible();
    expect(page.url()).toContain("focus=");
    await page.goBack();
    await expect(page.getByTestId("search-focus-pane")).toHaveCount(0);
    await page.goForward();
    await expect(page.getByTestId("search-focus-pane")).toBeVisible();
  });

  test("view links mint the canonical v2 form (network → graph)", async ({ page }) => {
    await page.goto("/map/?v=2&view=map");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    const netHref = await page.getByTestId("view-link-network").getAttribute("href");
    expect(netHref).toContain("/network/?");
    expect(netHref).toContain("v=2");
    expect(netHref).toContain("view=graph");
  });
});

test.describe("canonicalisation receipts (K13 §2.5/C-11)", () => {
  test("bbox canonicalises to at= with a visible receipt", async ({ page }) => {
    await page.goto("/map/?v=2&view=map&bbox=-98,34,-96,36");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("workspace-issues")).toContainText(
      /bbox.*at=\d+\//,
    );
    // The map does not apply a bounding box today — the conformance notice
    // names the parameter the address carried.
    await expect(page.getByTestId("facet-not-applied")).toContainText("bounding box");
  });

  test("a legacy jurisdiction code normalises with a visible note", async ({
    page,
  }) => {
    await page.goto("/search/?v=2&view=list&jurisdiction=US-OK");
    await expect(page.getByTestId("workspace-issues")).toContainText(
      "iso3166-2:US-OK",
    );
    await expect(page.getByTestId("facet-not-applied")).toContainText(
      "jurisdiction filter",
    );
  });

  test("kind=site resolves as type=record with a visible note", async ({ page }) => {
    await page.goto("/search/?v=2&view=list&kind=site");
    await expect(page.getByTestId("workspace-issues")).toContainText(
      /kind=site.*type=record/,
    );
    // `kind` is applied (with the fold receipt); `type` is derived, never
    // received, so the conformance notice has nothing unapplied to name.
    await expect(page.getByTestId("facet-not-applied")).toHaveCount(0);
  });

  test("the v1 view name network resolves as graph with a visible note", async ({
    page,
  }) => {
    await page.goto("/network/?v=2&view=network");
    await expect(page.getByTestId("workspace-issues")).toContainText(
      'the v1 view "network"',
    );
    // The surface still works — the graph island renders.
    await expect(page.getByTestId("network-island")).toBeVisible();
  });
});

test.describe("refusal + surface mismatch (SIG-UI-059)", () => {
  test("an unregistered parameter is refused loudly", async ({ page }) => {
    await page.goto("/search/?v=2&view=list&bogus=1&focus=fixture:probe");
    await expect(page.getByTestId("workspace-issues")).toContainText('"bogus"');
    await expect(page.getByTestId("workspace-issues")).toContainText(
      /not in the sig\.workspace-state\/2 registry/,
    );
  });

  test("a view naming a different surface is a visible receipt", async ({ page }) => {
    await page.goto("/map/?v=2&view=list");
    await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("workspace-issues")).toContainText(
      'names the "list" view',
    );
  });

  test("an unapplied registered parameter is named on every surface", async ({
    page,
  }) => {
    // `sort` parses (registered) but no surface applies it — the notice names
    // it on each T2 surface rather than silently dropping it.
    for (const { path } of T2) {
      await page.goto(`${path}?v=2&sort=name`);
      await expect(page.getByTestId("facet-not-applied")).toContainText(
        "sort key",
      );
    }
  });
});
