import { expect, test } from "@playwright/test";

// P36.55 (VIZ-02, SIG-UI-069/123/129/132, SIG-WATCH-009): the ONE dossier
// template — every dossier renders the v2 composition: header strip, the
// locator + Figure 1 + Explore bar on At a glance, the network-figure slots
// typed until VIZ-01b, Where this comes from, Next decisions, Other public
// resources — with the print posture (brief page 1 + locator, map leads
// page 2). Asserted on a drawn dossier (oklahoma-city), a keyed
// sub-jurisdiction (oklahoma-city-4064000) and the typed-absence dossier
// (usa/vi).

test.describe("the one dossier template (SIG-UI-069)", () => {
  test("the drawn dossier renders every v2 block in order", async ({ page }) => {
    await page.goto("/dossier/oklahoma-city/");
    // Header strip — the K4 row fields. The flat worked dossier carries no
    // roll-up so its record count is an honest `not_recorded`, never a
    // fabricated number.
    await expect(page.getByTestId("dossier-header-strip")).toBeVisible();
    await expect(page.getByTestId("strip-records")).toBeVisible();
    // At a glance carries the locator + Figure 1 + Explore bar.
    await expect(page.getByTestId("dossier-locator")).toBeVisible();
    await expect(page.getByTestId("dossier-map-figure")).toBeVisible();
    await expect(page.getByTestId("fig1-canvas").locator("svg")).toBeVisible();
    await expect(page.getByTestId("fig1-caption")).toContainText("Not a census");
    // The explore bar's three links.
    await expect(page.getByTestId("dossier-explore-bar")).toBeVisible();
    await expect(page.getByTestId("explore-map")).toHaveAttribute("href", /\/map\//);
    await expect(page.getByTestId("explore-network")).toHaveAttribute("href", /\/explore\//);
    await expect(page.getByTestId("explore-search")).toHaveAttribute("href", /\/search\//);
    // The twelve sections still render in order.
    const ids = await page
      .getByTestId("dossier-section")
      .evaluateAll((els) => els.map((e) => e.getAttribute("data-section-id")));
    expect(ids).toEqual([
      "at_a_glance",
      "what_is_deployed",
      "cost_and_expiry",
      "who_else_can_see",
      "configuration_and_retention",
      "usage",
      "where_the_hardware_is",
      "policy",
      "accountability_events",
      "timeline",
      "what_we_dont_know",
      "how_we_know_this",
    ]);
    // The network-figure slots (P37.28 / VIZ-01b): emitted entries render —
    // the flat fixture dossier carries typed absences (no anchored entity).
    const slots = page.getByTestId("network-figure-slot");
    await expect(slots).toHaveCount(4);
    await expect(slots.first()).toHaveAttribute("data-figure", "fig-2");
    await expect(slots.first()).toContainText("Who runs and supplies it");
    // Next decisions — SIG-WATCH-009: items + the watch link + official portal.
    await expect(page.getByTestId("next-decisions")).toBeVisible();
    await expect(page.getByTestId("next-decision-item")).toHaveCount(2);
    await expect(page.getByTestId("agenda-portal")).toHaveAttribute("href", /civicclerk/);
    // The neutral Other public resources block (D3-Q4 [B-27]).
    await expect(page.getByTestId("other-public-resources")).toBeVisible();
    await expect(page.getByTestId("other-public-resources")).toContainText("SIG does not endorse");
  });

  test("a keyed sub-jurisdiction renders the same template", async ({ page }) => {
    await page.goto("/dossier/usa/ok/oklahoma-city-4064000/");
    await expect(page.getByTestId("dossier-header-strip")).toBeVisible();
    await expect(page.getByTestId("strip-records")).toContainText("391");
    await expect(page.getByTestId("dossier-map-figure")).toBeVisible();
    await expect(page.getByTestId("fig1-canvas").locator("svg")).toBeVisible();
    await expect(page.getByTestId("next-decisions")).toBeVisible();
    await expect(page.getByTestId("other-public-resources")).toBeVisible();
  });

  test("usa/ok draws the emitted access figure — toggles, table twin, links", async ({ page }) => {
    await page.goto("/dossier/usa/ok/");
    // P37.28 (SIG-UI-125/DV03): the drawn figure renders the kit's SVG,
    // the zero-JS `:has()` toggles, the H-2 table twin and the hand-offs.
    const fig = page.getByTestId("network-figure");
    await expect(fig).toHaveAttribute("id", "fig-access");
    await expect(fig.locator("svg")).toBeVisible();
    // The access-kind toggles hide each kind without JavaScript.
    await expect(page.getByTestId("network-toggles")).toBeVisible();
    await expect(fig.locator(".sig-fig-edge-acc-declared")).toBeVisible();
    await page.getByLabel("declared").uncheck();
    await expect(fig.locator(".sig-fig-edge-acc-declared")).toBeHidden();
    await page.getByLabel("declared").check();
    // The H-2 table twin is the figure's long description.
    const twin = page.getByTestId("network-table-twin");
    await expect(twin).toContainText("configured access to");
    await expect(twin).toContainText("undated");
    // Skip link, explorer hand-off and the full-table link resolve.
    await expect(page.getByTestId("network-explore-link")).toHaveAttribute(
      "href",
      /\/explore\/\?v=2&overview=access&jurisdiction=/,
    );
    await expect(page.getByTestId("network-table-link")).toHaveAttribute("href", /\/graphs\/access\//);
    // The H-4 degree-only sentence renders beside the figure.
    await expect(page.getByTestId("network-degree-facts")).toContainText(
      "Shared with 9 agencies — partners not named",
    );
    // The typed absences keep their named reasons (never a blank frame).
    const slots = page.getByTestId("network-figure-slot");
    await expect(slots.first()).toContainText("no recorded relationship of this kind");
    // A figure with no evidenced edge is never drawn (V-7).
    await expect(slots.first().locator("svg")).toHaveCount(0);
  });

  test("usa/vi renders the typed map absence — never a blank map", async ({ page }) => {
    await page.goto("/dossier/usa/vi/");
    const fig = page.getByTestId("dossier-map-figure");
    await expect(fig).toBeVisible();
    await expect(fig.locator("svg")).toHaveCount(0);
    await expect(fig).toContainText("No verified outline");
    // The country-level dossier carries the typed locator status.
    await expect(page.getByTestId("dossier-locator")).toBeVisible();
  });

  test("a top-level dossier carries the no-parent-context locator", async ({ page }) => {
    await page.goto("/dossier/usa/");
    await expect(page.getByTestId("locator-status")).toContainText("No parent context");
  });
});

test.describe("the print posture (SIG-UI-130)", () => {
  test("the council brief carries the locator; the map leads page 2", async ({ page }) => {
    await page.goto("/dossier/oklahoma-city/print/");
    // Page 1 is the brief; its locator is the place-inside-parent glyph.
    await expect(page.getByTestId("brief-locator").locator("path")).toHaveCount(2);
    // Page 2 leads with the map figure — the fixture's static SVG renders,
    // never a placeholder over a drawable figure (SIG-UI-130).
    const mapPage = page.locator('[data-page-kind="figures"]').first();
    await expect(mapPage.getByTestId("print-figure")).toHaveAttribute("data-figure-kind", "map");
    await expect(mapPage.getByTestId("print-figure-svg").locator("svg")).toBeVisible();
  });
});
