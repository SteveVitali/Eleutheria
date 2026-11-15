// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.61 (R11-K13-ENH-01, C-19/C-20, ADR-224/ADR-249) — the T1 kit rollout:
// `<sig-table>` over the existing table AND list surfaces on /sources/**,
// the dossier sources explorers, /dossier/, /watch/, /evidence/ and
// /research-queue/ — never a new island. This spec exercises the rollout's
// own contract: list mode, the toolbar "Sort by" menu where headers carry
// server sort links, param prefixes on multi-mount pages, URL state, the
// licence-aware CSV, and the K0 failure leg.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const HARNESS = "/enhancement-kit/";

const sortMenuButton = (
  scope: import("@playwright/test").Locator,
  name: string | RegExp,
) =>
  scope
    .locator("details", { hasText: "Sort by" })
    .getByRole("button", { name });

test.describe("<sig-table> list mode (harness fixtures)", () => {
  test("filters, facets, sorts and writes `lst.` namespaced params", async ({
    page,
  }) => {
    await page.goto(HARNESS);
    const mount = page.locator("sig-table:has([data-testid='kit-list'])");
    const items = page.getByTestId("kit-list-item");
    expect(await items.count()).toBe(3);

    // Free-text filter → hidden items stay in the DOM; status uses "items".
    await mount.getByRole("searchbox", { name: /filter items/i }).fill("amber");
    await expect(page.locator("[data-testid='kit-list-item']:visible")).toHaveCount(1);
    expect(await items.count()).toBe(3);
    await expect(mount.locator(".sig-kit-status")).toContainText("Showing 1 of 3 items");
    expect(page.url()).toContain("lst.q=amber");

    // Facet chips come from data-facet-* on the li rows.
    await mount.getByRole("searchbox", { name: /filter items/i }).fill("");
    const kindMenu = mount.locator("details", { hasText: "Filter by kind" });
    await kindMenu.locator("summary").click();
    await kindMenu.locator(".sig-kit-chip", { hasText: "beta" }).click();
    await expect(page.locator("[data-testid='kit-list-item']:visible")).toHaveCount(1);
    expect(page.url()).toContain("lst.kind=beta");
    // The other mount's params are untouched.
    expect(page.url()).not.toMatch(/[?&]kind=beta/);
  });

  test("the Sort by menu orders items by declared keys, both directions", async ({
    page,
  }) => {
    await page.goto(HARNESS);
    const mount = page.locator("sig-table:has([data-testid='kit-list'])");
    const menu = mount.locator("details", { hasText: "Sort by" });
    await menu.locator("summary").click();
    await menu.getByRole("button", { name: /^Weight/ }).click();
    await expect(
      page.locator("[data-testid='kit-list-item']").first(),
    ).toContainText("Bridle loop"); // weight 3 is smallest
    expect(page.url()).toContain("lst.sort=weight");
    await menu.getByRole("button", { name: /^Weight/ }).click();
    await expect(
      page.locator("[data-testid='kit-list-item']").first(),
    ).toContainText("Amber gate"); // desc → 9 first
    expect(page.url()).toContain("lst.dir=desc");
  });

  test("list URL state restores on load", async ({ page }) => {
    await page.goto(`${HARNESS}?lst.sort=weight&lst.dir=desc`);
    await expect(page.locator("[data-testid='kit-list-item']").first()).toContainText(
      "Amber gate",
    );
  });

  test("the linked-header table sorts through the toolbar menu — never a nested control", async ({
    page,
  }) => {
    await page.goto(HARNESS);
    const mount = page.locator("sig-table:has([data-testid='kit-linked-table'])");
    const table = page.getByTestId("kit-linked-table");
    // The header anchors stay plain anchors — no button was wrapped around
    // them and none was injected beside them.
    expect(await table.locator("thead th button").count()).toBe(0);
    expect(await table.locator("thead th a").count()).toBe(2);
    const menu = mount.locator("details", { hasText: "Sort by" });
    await menu.locator("summary").click();
    await menu.getByRole("button", { name: /^Rows/ }).click();
    // absence-last: "731" sorts before "3,172"? — municipal-open-data's 731
    // is the smallest number, numeric comparison over the rendered text.
    await expect(table.locator("tbody tr td").first()).toContainText(
      "municipal-open-data",
    );
    expect(page.url()).toContain("lnk.sort=rows");
    await menu.getByRole("button", { name: /^Name/ }).click();
    await expect(table.locator("tbody tr td").first()).toContainText(
      "atlas-of-surveillance",
    );
  });
});

test.describe("the rollout surfaces", () => {
  test("/dossier/ — the grouped index filters, facets and sorts in place (JUR-04)", async ({
    page,
  }) => {
    await page.goto("/dossier/");
    const mount = page.locator("sig-table:has(ul.sig-dossier-index)");
    const items = page.getByTestId("dossier-index-item");
    const total = await items.count();
    expect(total).toBeGreaterThan(3);

    // A nonsense term hides every item (they stay in the DOM), a real one
    // narrows — proving the filter without depending on fixture names.
    await mount.getByRole("searchbox", { name: /filter items/i }).fill("zzzz");
    await expect(
      page.locator("[data-testid='dossier-index-item']:visible"),
    ).toHaveCount(0);
    expect(await items.count()).toBe(total);
    expect(page.url()).toContain("q=zzzz");
    await mount.getByRole("searchbox", { name: /filter items/i }).fill("");
    const visible = page.locator("[data-testid='dossier-index-item']:visible");
    await expect(visible).toHaveCount(total);

    // A facet chip narrows across all three group sections at once — pick
    // the minority value (not every row carries it).
    const menu = mount.locator("details", { hasText: "Filter by level" });
    await menu.locator("summary").click();
    const chip = menu.locator(".sig-kit-chip", { hasText: /country \(/ });
    const chipLabel = (await chip.textContent())!.trim();
    const chipCount = Number(chipLabel.match(/\((\d+)\)$/)![1]);
    await chip.click();
    await expect(visible).toHaveCount(chipCount);
    expect(chipCount).toBeLessThan(total);
    await expect(mount.locator(".sig-kit-status")).toContainText(
      `Showing ${chipCount} of ${total} items`,
    );
    expect(page.url()).toContain("level=country");
    await menu.locator(".sig-kit-chip", { hasText: /country \(/ }).click();

    // Sort by records desc puts a top-level jurisdiction first in each group.
    const sortMenu = mount.locator("details", { hasText: "Sort by" });
    await sortMenu.locator("summary").click();
    await sortMenuButton(mount, /^Records/).click();
    await sortMenuButton(mount, /^Records/).click(); // asc → desc
    expect(page.url()).toContain("sort=records");
    expect(page.url()).toContain("dir=desc");
  });

  test("/watch/ — the watch list filters and facets in place (WX-04)", async ({
    page,
  }) => {
    await page.goto("/watch/");
    const mount = page.locator("sig-table:has(ol.sig-watch-list)");
    const items = page.getByTestId("watch-item");
    const total = await items.count();
    expect(total).toBeGreaterThan(2);

    await mount.getByRole("searchbox", { name: /filter items/i }).fill("zzzz");
    await expect(mount.locator(".sig-kit-status")).toContainText(
      `Showing 0 of ${total} items`,
    );
    // A code that occurs in exactly one item's title narrows to it — the
    // term is derived from the rendered rows, never a living-record guess.
    const texts = await items.allTextContents();
    const codes = texts.map(
      (t) => t.match(/\b(?:JAG|HSGP|CB|HB|C|R|N)-\d+\b/)?.[0],
    );
    const term = codes.find(
      (c, i) => c && codes.indexOf(c) === codes.lastIndexOf(c),
    );
    expect(term, "a uniquely-coded watch item must exist on page 1").toBeTruthy();
    await mount.getByRole("searchbox", { name: /filter items/i }).fill(term!);
    await expect(page.locator("[data-testid='watch-item']:visible")).toHaveCount(1);
    await mount.getByRole("searchbox", { name: /filter items/i }).fill("");

    // Facet chips derive from the rows' own data-facet-* values — the
    // first kind chip narrows the list to exactly its labelled count.
    const menu = mount.locator("details", { hasText: "Filter by kind" });
    await menu.locator("summary").click();
    const chip = menu.locator(".sig-kit-chip").first();
    const chipCount = Number(
      (await chip.textContent())!.trim().match(/\((\d+)\)$/)![1],
    );
    await chip.click();
    await expect(page.locator("[data-testid='watch-item']:visible")).toHaveCount(
      chipCount,
    );
  });

  test("/evidence/ — the artifact rows filter and facet in place (EV-02)", async ({
    page,
  }) => {
    await page.goto("/evidence/");
    const mount = page.locator("sig-table:has(ul.sig-artifact-rows)");
    const rows = page.getByTestId("evidence-artifact-row");
    expect(await rows.count()).toBe(8);

    // Facet chips derive from data-facet-* on the li rows.
    const menu = mount.locator("details", { hasText: "Filter by state" });
    await menu.locator("summary").click();
    const chips = menu.locator(".sig-kit-chip");
    expect(await chips.count()).toBeGreaterThan(0);
    const chip = menu.locator(".sig-kit-chip", { hasText: "legacy_synthetic" });
    await chip.click();
    await expect(page.locator("[data-testid='evidence-artifact-row']:visible")).toHaveCount(2);
    expect(page.url()).toContain("ev.state=legacy_synthetic");
    // A second mount on the same page would need its own prefix — the bare
    // state param stays unset.
    expect(page.url()).not.toContain("?state=legacy");
  });

  test("/research-queue/ — task cards and campaign rows share namespaced params (RQ-03)", async ({
    page,
  }) => {
    await page.goto("/research-queue/");
    const queueMount = page.locator("sig-table:has(ol.sig-queue)");
    const cards = page.getByTestId("task-card");
    const total = await cards.count();
    expect(total).toBeGreaterThan(0);

    await queueMount.getByRole("searchbox", { name: /filter items/i }).fill("zzzz");
    await expect(queueMount.locator(".sig-kit-status")).toContainText(
      `Showing 0 of ${total} items`,
    );
    expect(page.url()).toContain("rq.q=zzzz");
    // The campaign mount's params stay namespaced and independent.
    const campMount = page.locator("sig-table:has(ol.sig-campaigns)");
    if (await campMount.count()) {
      expect(page.url()).not.toContain("cmp.q=");
    }
  });

  test("/sources/ — the main table's linked headers get the toolbar sort menu (UX9-3e)", async ({
    page,
  }) => {
    await page.goto("/sources/");
    const mount = page.locator("sig-table:has([data-testid='source-table-row'])");
    const table = page.getByTestId("sources-table-grid");
    const rows = page.getByTestId("source-table-row");
    const total = await rows.count();
    expect(total).toBeGreaterThan(1);

    // Interactive headers keep their anchors — no button nests inside them.
    expect(await table.locator("thead th button").count()).toBe(0);
    const menu = mount.locator("details", { hasText: "Sort by" });
    await menu.locator("summary").click();
    await menu.getByRole("button", { name: /^Published claims/ }).click();
    expect(page.url()).toContain("src.sort=claims");

    // Filtering writes the prefixed param; the licences mount's bare q is
    // untouched by the interaction.
    await mount.getByRole("searchbox", { name: /filter rows/i }).fill("okc");
    const visible = page.locator("[data-testid='source-table-row']:visible");
    const n = await visible.count();
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThan(total);
    expect(page.url()).toContain("src.q=okc");

    // Facet chips on the main table come from the row's own data-facet-*.
    const menu2 = mount.locator("details", { hasText: "Filter by status" });
    await menu2.locator("summary").click();
    expect(await menu2.locator(".sig-kit-chip").count()).toBeGreaterThan(0);
  });

  test("the dossier sources explorer sorts + facets in place (DSRC-05)", async ({
    page,
  }) => {
    await page.goto("/dossier/usa/sources/");
    const mount = page.locator("sig-table:has([data-testid='dsrc-table'])");
    const table = page.getByTestId("dsrc-table");
    const rows = table.locator("tbody tr");
    const total = await rows.count();
    expect(total).toBeGreaterThan(20);

    // Plain text headers → per-header sort buttons with aria-sort.
    const sort = table.getByRole("button", { name: /^Records/ });
    await sort.click();
    await expect(table.locator('th[aria-sort="ascending"]')).toContainText("Records");
    expect(page.url()).toContain("dsrc.sort=records");

    // A facet chip narrows the view.
    const menu = mount.locator("details", { hasText: "Filter by publisher-type" });
    await menu.locator("summary").click();
    const chip = menu.locator(".sig-kit-chip").first();
    const chipText = await chip.textContent();
    await chip.click();
    const visible = table.locator("tbody tr:visible");
    const n = await visible.count();
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThan(total);
    expect(page.url()).toContain("dsrc.publisher-type=");

    // Download this view → CSV with the licence preamble.
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      mount.getByRole("button", { name: /download this view/i }).click(),
    ]);
    const path = await download.path();
    const { readFileSync } = await import("node:fs");
    const csv = readFileSync(path!, "utf-8");
    expect(csv).toContain("# sig-table export — downloaded view");
    expect(csv.split("\n").filter((l) => l.startsWith("# licence")).length).toBeGreaterThan(0);
    expect(chipText).toBeTruthy();
  });

  test("a /sources/<id>/ changelog table filters in place (UX10-4)", async ({ page }) => {
    await page.goto("/sources/okc_camera_registry/changelog/");
    const mount = page.locator("sig-table:has([data-testid='changelog-table'])");
    const rows = page.getByTestId("changelog-event");
    const total = await rows.count();
    expect(total).toBeGreaterThan(5);

    const menu = mount.locator("details", { hasText: "Filter by kind" });
    await menu.locator("summary").click();
    const chip = menu.locator(".sig-kit-chip").first();
    await chip.click();
    const n = await page.locator("[data-testid='changelog-event']:visible").count();
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThan(total);
    expect(page.url()).toContain("kind=");
  });
});

test.describe("a11y + the K0 failure rule", () => {
  test("the enhanced /dossier/ index passes the WCAG 2.2 AA sweep", async ({ page }) => {
    await page.goto("/dossier/");
    await expect(page.locator("sig-table .sig-kit-bar").first()).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("the enhanced /research-queue/ page passes the WCAG 2.2 AA sweep", async ({
    page,
  }) => {
    await page.goto("/research-queue/");
    await expect(page.locator("sig-table .sig-kit-bar").first()).toBeVisible();
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("blocking /_kit/ leaves every rollout surface complete and inert", async ({
    page,
  }) => {
    await page.route("**/_kit/**", (route) => route.abort());
    await page.goto("/dossier/");
    await expect(page.getByTestId("dossier-index-item").first()).toBeVisible();
    await page.goto("/watch/");
    await expect(page.getByTestId("watch-item").first()).toBeVisible();
    await page.goto("/research-queue/");
    await expect(page.getByTestId("task-card").first()).toBeVisible();
    await page.goto("/evidence/");
    await expect(page.getByTestId("evidence-artifact-row").first()).toBeVisible();
    await page.goto("/dossier/usa/sources/");
    await expect(page.getByTestId("dsrc-table")).toBeVisible();
    await page.goto("/sources/");
    await expect(page.getByTestId("source-table-row").first()).toBeVisible();
    expect(await page.locator(".sig-kit-bar").count()).toBe(0);
  });
});
