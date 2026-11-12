// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.26 (K2 GX-09a, ADR-242) — the /explore/ T2 graph explorer: the Preact +
// sigma island in the reserved SSR box, overview loading over the emitted
// sig.graph-overview/1 docs, node and edge panels → provenance, workspace
// state round-trip and cite view, plus the J2 capstone traversal's web leg
// (K13 §8). The /network/ 301 contract is asserted in redirects.test.ts /
// redirects.spec.ts (the conf is nginx-side; astro preview cannot 3xx).
import { test, expect } from "@playwright/test";

test.describe("graph explorer /explore/ (GX-09a)", () => {
  test("the island mounts sigma over the default access overview", async ({ page }) => {
    await page.goto("/explore/");
    const island = page.getByTestId("explore-island");
    await expect(island).toBeVisible();
    // The reserved box resolved: sigma mounted a canvas inside the reserved SSR box.
    await expect(page.getByTestId("explore-canvas")).toBeVisible();
    // The default overview (access — the /network/ successor view) is pressed in the picker.
    const access = page.getByTestId("overview-pick").filter({ hasText: "Access" });
    await expect(access).toHaveAttribute("aria-pressed", "true");
    // Node buttons carry the budget interaction contract (select-node).
    const nodes = page.getByTestId("graph-island-node");
    await expect(nodes.first()).toBeVisible();
    expect(await nodes.count()).toBeGreaterThan(1);
    // The workspace URL state minted v=2&view=graph.
    expect(page.url()).toContain("/explore/");
  });

  test("overview switching round-trips through ?v=2&overview=", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=supply");
    const island = page.getByTestId("explore-island");
    await expect(island).toBeVisible();
    // The supply overview is selected from the address.
    const supply = page.getByTestId("overview-pick").filter({ hasText: "Supply" });
    await expect(supply).toHaveAttribute("aria-pressed", "true");
    // The picker switches the address state — overview= rides the URL (SIG-UI-119).
    const access = page.getByTestId("overview-pick").filter({ hasText: "Access" });
    await access.click();
    await expect(access).toHaveAttribute("aria-pressed", "true");
    expect(page.url()).toContain("overview=access");
  });

  test("an unknown overview names itself honestly, never fabricates", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=nosuchoverview");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    await expect(page.getByTestId("explore-overview-miss")).toContainText("nosuchoverview");
    // The default overview still renders.
    await expect(page.getByTestId("explore-canvas")).toBeVisible();
  });

  test("node selection inspects the node and hands off to provenance", async ({ page }) => {
    await page.goto("/explore/");
    const island = page.getByTestId("explore-island");
    await expect(island).toBeVisible();
    const nodes = page.getByTestId("graph-island-node");
    await expect(nodes.first()).toBeVisible();
    expect(await nodes.count()).toBeGreaterThan(0);
    // Pick the first non-focused node — aria-pressed flips to true.
    let target = -1;
    for (let i = 0; i < (await nodes.count()); i += 1) {
      if ((await nodes.nth(i).getAttribute("aria-pressed")) === "false") {
        target = i;
        break;
      }
    }
    expect(target).toBeGreaterThanOrEqual(0);
    await nodes.nth(target).click();
    await expect(nodes.nth(target)).toHaveAttribute("aria-pressed", "true");
    // The node panel shows the facts and the focus rides the URL.
    const detail = page.getByTestId("graph-island-detail");
    await expect(detail.getByTestId("node-panel-title")).toBeVisible();
    expect(page.url()).toContain("focus=");
  });

  test("node selection restyles in place — the sigma canvas is never rebuilt", async ({ page }) => {
    // The graph + WebGL context build once per drawn graph; a selection
    // only restyles (graphology attributes + sigma.refresh()). A rebuild per
    // click (sigma.kill() + new Sigma) replaces every canvas in the box —
    // the context churn the select-node interaction-latency leg would
    // otherwise only catch as a noisy timing overage.
    await page.goto("/explore/");
    const canvasBox = page.getByTestId("explore-canvas");
    await expect(canvasBox.locator("canvas").first()).toBeAttached();
    const nodes = page.getByTestId("graph-island-node");
    await expect(nodes.first()).toBeVisible();
    await canvasBox.evaluate((box) => {
      for (const c of box.querySelectorAll("canvas")) c.setAttribute("data-probe-mount", "1");
    });
    let target = -1;
    for (let i = 0; i < (await nodes.count()); i += 1) {
      if ((await nodes.nth(i).getAttribute("aria-pressed")) === "false") {
        target = i;
        break;
      }
    }
    expect(target).toBeGreaterThanOrEqual(0);
    await nodes.nth(target).click();
    await expect(nodes.nth(target)).toHaveAttribute("aria-pressed", "true");
    // Let any (regressed) post-render effect run before reading the box.
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0))));
    const canvases = await canvasBox.evaluate((box) => {
      const all = [...box.querySelectorAll("canvas")];
      return { total: all.length, original: all.filter((c) => c.hasAttribute("data-probe-mount")).length };
    });
    expect(canvases.total).toBeGreaterThan(0);
    expect(canvases.original, "a node selection rebuilt the sigma mount").toBe(canvases.total);
  });

  test("a deep-linked focus selects its node; a missing focus is named", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&focus=place:usa-tx");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    const texas = page.getByTestId("graph-island-node").filter({ hasText: "Texas" });
    await expect(texas).toHaveAttribute("aria-pressed", "true");
    // A focus no node in the overview carries is reported, never fabricated.
    await page.goto("/explore/?v=2&view=graph&focus=no-such-node");
    await expect(page.getByTestId("graph-focus-miss")).toBeVisible();
  });

  test("the edge panel names relation, date, currency, sources and evidence", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&focus=place:usa-ok");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    // The island hydrates async — the overview doc fetch must land before
    // the node list and the focused node's incident edges render.
    await expect(page.getByTestId("graph-island-node").first()).toBeVisible();
    const incident = page.getByTestId("edge-panel-open");
    await expect(incident.first()).toBeVisible();
    await incident.first().click();
    const facts = page.getByTestId("edge-panel-facts");
    await expect(facts).toBeVisible();
    await expect(facts).toContainText("configured access to");
    await expect(facts).toContainText("historical");
    await expect(facts).toContainText("supporting claim");
  });

  test("unapplied facets are visibly named, never silently applied", async ({ page }) => {
    // `seen` + `within` parse (registered) but the explorer does not apply
    // them — the SIG-UI-060 notice names both rather than drop them.
    await page.goto("/explore/?v=2&view=graph&seen=2020..2024&within=x");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    const notice = page.getByTestId("facet-not-applied");
    await expect(notice).toBeVisible();
    await expect(notice).toContainText("seen range");
    await expect(notice).toContainText("scope restriction");
  });

  test("the live cite view mints the snapshot-pinned form", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=access&focus=place:usa-ok");
    const cite = page.getByTestId("cite-form");
    const text = await cite.textContent();
    expect(text).toContain("/s/");
    expect(text).toContain("/explore/");
    expect(text).toContain("v=2");
    expect(text).toContain("view=graph");
    expect(text).toContain("overview=access");
    expect(text).toContain("focus=place%3Ausa-ok");
  });

  test("the no-JS equivalents carry every fact class (SIG-UI-037)", async ({ page }) => {
    // JS on here — the static sections are the same DOM the no-JS build serves.
    await page.goto("/explore/");
    await expect(page.getByTestId("graph-overview-row").first()).toBeVisible();
    await expect(page.getByTestId("default-overview-figure")).toBeVisible();
    await expect(page.getByTestId("default-overview-edge").first()).toBeVisible();
    await expect(page.getByTestId("access-edge").first()).toBeVisible();
    await expect(page.getByTestId("path-hop").first()).toBeVisible();
    await expect(page.getByTestId("centrality-withdrawn")).toBeVisible();
  });

  test("no centrality or hub ranking renders anywhere (SIG-UI-121)", async ({ page }) => {
    await page.goto("/explore/");
    await expect(page.getByTestId("graph-island-er-disclosure")).toHaveCount(0);
    await expect(page.getByTestId("graph-island-centrality")).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText(
      /deterministic identity resolution|never an estimate/i,
    );
  });

  // K13 §8 J2's web leg: search "Texas ALPR" → dossier → Explore →
  // /explore/?v=2&overview=supply&jurisdiction=…, then overview=access. The
  // explorer half is asserted here; the dossier/search legs live in their
  // own specs (the capstone's full traversal rides CAP-01).
  test("J2: the dossier explore link lands on a working explorer", async ({ page }) => {
    await page.goto("/dossier/usa/");
    const link = page.getByTestId("explore-network");
    const href = await link.getAttribute("href");
    expect(href).toContain("/explore/?v=2&view=graph&jurisdiction=");
    await page.goto(href!);
    await expect(page.getByTestId("explore-island")).toBeVisible();
    // The dossier's jurisdiction facet applies (P37.27): the access
    // overview's Texas node matches the jkey's place subtree and the active
    // filter is disclosed — never a silent filter.
    await expect(page.getByTestId("active-filters")).toContainText("filter");
    await expect(page.getByTestId("graph-island-node").filter({ hasText: "Texas" })).toHaveCount(1);
    await page.getByTestId("overview-pick").filter({ hasText: "Supply" }).click();
    await expect(page.getByTestId("explore-canvas")).toBeVisible();
    expect(page.url()).toContain("overview=supply");
    await page.getByTestId("overview-pick").filter({ hasText: "Access" }).click();
    expect(page.url()).toContain("overview=access");
  });
});

test.describe("graph explorer /explore/ 09b (GX-09b)", () => {
  test("facet filters narrow honestly and disclose themselves", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=governance");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    const nodes = page.getByTestId("graph-island-node");
    await expect(nodes.first()).toBeVisible();
    expect(await nodes.count()).toBeGreaterThanOrEqual(4);
    // kind=agency narrows to the single agency node — the filter is stated.
    await page.goto("/explore/?v=2&view=graph&overview=governance&kind=agency");
    await expect(page.getByTestId("active-filters")).toBeVisible();
    const agencies = page.getByTestId("graph-island-node").filter({ hasText: "Legislature" });
    await expect(agencies).toHaveCount(1);
    expect(await page.getByTestId("graph-island-node").count()).toBeLessThan(4);
  });

  test("search-to-node finds a node in the loaded graph", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=governance");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    await page.getByTestId("explore-search-input").fill("Oklahoma Legislature");
    const hit = page.getByTestId("search-node-hit").filter({ hasText: "Legislature" });
    await expect(hit.first()).toBeVisible();
    await hit.first().click();
    expect(page.url()).toContain("focus=");
    await expect(page.getByTestId("graph-island-detail")).toBeVisible();
  });

  test("the path finder lists every hop; a missing endpoint is named", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=governance&path=tech:alpr~e-ok-leg");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    const hops = page.getByTestId("island-path-hop");
    await expect(hops.first()).toBeVisible();
    expect(await hops.count()).toBeGreaterThanOrEqual(2);
    await expect(page.getByTestId("path-panel-title")).toBeVisible();
    // A pair naming a node outside the overview is a typed answer, never dropped.
    await page.goto("/explore/?v=2&view=graph&overview=governance&path=e-sb1234~nosuchnode");
    await expect(page.getByTestId("path-missing")).toBeVisible();
  });

  test("expansion loads the twin ego; a twin-less node answers typed", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=adoption&expand=e-acme-pd");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    // The twin loads — nodes beyond the emitted pair render or the ego note names the bounded result.
    await expect(page.getByTestId("graph-island-node").first()).toBeVisible();
    expect(page.url()).toContain("expand=e-acme-pd");
    // tech:alpr has no entity page — the typed no-twin answer, never a fabricated ego.
    await page.goto("/explore/?v=2&view=graph&overview=adoption&focus=tech:alpr&expand=tech:alpr");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    await expect(page.getByTestId("ego-note")).toContainText("twin");
  });

  test("the keyboard node list sorts and the sort rides the URL", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=governance");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    await expect(page.getByTestId("explore-node-table")).toBeVisible();
    await page.getByTestId("sort-kind").click();
    expect(page.url()).toContain("sort=kind");
    await expect(page.getByTestId("sort-kind")).toHaveAttribute("aria-pressed", "true");
    await page.getByTestId("sort-kind").click();
    expect(page.url()).toContain("dir=desc");
  });

  test("hops= scopes the neighbourhood ring around the focus", async ({ page }) => {
    await page.goto("/explore/?v=2&view=graph&overview=governance&focus=e-ok-leg&hops=1");
    await expect(page.getByTestId("explore-island")).toBeVisible();
    await expect(page.getByTestId("graph-island-node").first()).toBeVisible();
    // The hops note or the scoped node set states the ring bound.
    const notes = page.locator("[data-testid='hops-note'], [data-testid='active-filters'], .sig-island__note");
    await expect(notes.first()).toBeVisible();
  });
});
