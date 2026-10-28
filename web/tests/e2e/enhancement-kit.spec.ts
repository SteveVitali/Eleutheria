// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.20 (UXK0-4, SIG-UI-091, ADR-155/ADR-224) — the T1 enhancement kit's
// behavioural sweep: every element upgrades complete server-rendered markup,
// adds only `[data-enhancement]` chrome, keeps URL state shareable, and —
// the K0 failure rule — a module that never loads leaves the page whole.
// The kit ships as the allow-listed `/_kit/sig-*.js` entries
// (t1-module-entries.json) under the strict CSP's `script-src 'self'`.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const SOURCES = "/sources/";
const HARNESS = "/enhancement-kit/";

test.describe("<sig-table> on the sources table", () => {
  test("text filtering hides non-matching rows and writes the q param", async ({
    page,
  }) => {
    await page.goto(SOURCES);
    const table = page.locator("sig-table");
    const all = page.getByTestId("source-row");
    const total = await all.count();
    expect(total).toBeGreaterThan(1);

    await table.getByRole("searchbox", { name: /filter rows/i }).fill("portal");
    const visible = page.locator('[data-testid="source-row"]:visible');
    await expect(visible).toHaveCount(1);
    await expect(visible).toContainText("demo-municipal-portal");
    // Hidden rows stay in the DOM (filtered, never removed) — the parity sweep
    // still sees the same text.
    expect(await all.count()).toBe(total);
    await expect(table.locator(".sig-kit-status")).toContainText(
      `Showing 1 of ${total} rows`,
    );
    expect(page.url()).toContain("q=portal");
  });

  test("column sorting reorders rows and reports aria-sort", async ({ page }) => {
    await page.goto(SOURCES);
    const firstCell = () =>
      page.locator('[data-testid="source-row"] td').first();
    await expect(firstCell()).toContainText("demo-municipal-portal");
    const sort = page.getByRole("button", { name: /^Source/ });
    await sort.click();
    await expect(firstCell()).toContainText("demo-municipal-portal");
    await expect(
      page.locator('th[aria-sort="ascending"]'),
    ).toContainText("Source");
    expect(page.url()).toContain("sort=source");
    await sort.click();
    await expect(firstCell()).toContainText("demo-records-request");
    await expect(
      page.locator('th[aria-sort="descending"]'),
    ).toContainText("Source");
    expect(page.url()).toContain("dir=desc");
  });

  test("facet chips narrow the view; the column chooser hides columns", async ({
    page,
  }) => {
    await page.goto(SOURCES);
    const table = page.locator("sig-table");
    const creditMenu = table.locator("details", {
      hasText: "Filter by credit",
    });
    await creditMenu.locator("summary").click();
    await creditMenu
      .locator(".sig-kit-chip", { hasText: "under-correction" })
      .click();
    const visible = page.locator('[data-testid="source-row"]:visible');
    await expect(visible).toHaveCount(1);
    await expect(visible).toContainText("demo-records-request");
    expect(page.url()).toContain("credit=under-correction");

    const colMenu = table.locator("details", { hasText: "Columns" });
    await colMenu.locator("summary").click();
    await colMenu.locator(".sig-kit-chip", { hasText: "Terms" }).click();
    await expect(page.locator("th", { hasText: "Terms" })).toBeHidden();
    expect(page.url()).toContain("cols=terms");
  });

  test("URL state restores the view on load", async ({ page }) => {
    await page.goto(`${SOURCES}?q=records`);
    const visible = page.locator('[data-testid="source-row"]:visible');
    await expect(visible).toHaveCount(1);
    await expect(visible).toContainText("demo-records-request");
    await expect(
      page.locator("sig-table").getByRole("searchbox"),
    ).toHaveValue("records");
  });

  test("Download this view emits CSV with per-licence provenance lines", async ({
    page,
  }) => {
    await page.goto(SOURCES);
    const table = page.locator("sig-table");
    await table.getByRole("searchbox", { name: /filter rows/i }).fill("portal");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      table
        .getByRole("button", { name: /download this view/i })
        .click(),
    ]);
    const path = await download.path();
    const { readFileSync } = await import("node:fs");
    const csv = readFileSync(path!, "utf-8");
    expect(csv).toContain("# licence: CC0-1.0");
    // The filtered-out row's licence never travels with the view.
    expect(csv).not.toContain("CC-BY-4.0");
    expect(csv).toContain("Source,Licence,Rows,Credit,Terms");
    expect(csv).toContain("demo-municipal-portal");
    expect(csv).not.toContain("demo-records-request");
  });
});

test.describe("<sig-cite>, <sig-copy>, <sig-details> — the shared cite trio", () => {
  test("the cite disclosure restates the citation in named formats", async ({
    page,
  }) => {
    await page.goto(SOURCES);
    await page.locator("summary", { hasText: "Cite" }).click();
    const cite = page.locator("sig-cite");
    const out = cite.locator(".sig-cite__formatted");
    // The plain format is the block's own rendered citation verbatim.
    const plain = await page
      .getByTestId("citation-text")
      .textContent();
    await expect(out).toHaveText(plain!.trim());
    await cite.getByRole("combobox", { name: "Format" }).selectOption("apa");
    await expect(out).toContainText(
      "Surveillance Infrastructure Graph. (",
    );
    await expect(out).toContainText("Sources and licences");
    await cite.getByRole("combobox", { name: "Format" }).selectOption("chicago");
    await expect(out).toContainText('"Sources and licences."');
    await cite.getByRole("combobox", { name: "Format" }).selectOption("legal");
    await expect(out).toContainText("data as of");
  });

  test("a fragment naming the disclosure opens it; print opens it too", async ({
    page,
  }) => {
    await page.goto(`${SOURCES}#cite-details`);
    const details = page.locator("#cite-details");
    await expect(details).toHaveJSProperty("open", true);

    // A closed disclosure expands for print and restores afterwards.
    await page.goto(SOURCES);
    await expect(details).toHaveJSProperty("open", false);
    await page.evaluate(() => window.dispatchEvent(new Event("beforeprint")));
    await expect(details).toHaveJSProperty("open", true);
    await page.evaluate(() => window.dispatchEvent(new Event("afterprint")));
    await expect(details).toHaveJSProperty("open", false);
  });

  test("the copy affordances report success without touching source text", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.goto(SOURCES);
    await page.locator("summary", { hasText: "Cite" }).click();
    const cite = page.locator("sig-cite");
    await cite.getByRole("button", { name: "Copy citation" }).click();
    await expect(
      cite.locator(".sig-kit-bar .sig-kit-status"),
    ).toContainText("Copied");

    const permalink = await page
      .getByTestId("permalink")
      .first()
      .getAttribute("href");
    await page.getByRole("button", { name: "Copy link" }).first().click();
    const clip = await page.evaluate(() => navigator.clipboard.readText());
    expect(clip).toBe(permalink);
  });
});

test.describe("<sig-typeahead> over static shards", () => {
  test("keystrokes fetch the named shard and render options; Enter navigates", async ({
    page,
  }) => {
    const shardRequests: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/enhancement-kit/shards/")) {
        shardRequests.push(r.url());
      }
    });
    await page.goto(HARNESS);
    const input = page.getByTestId("kit-typeahead-input");
    const typeahead = page.locator("sig-typeahead");
    await input.fill("me");
    const list = typeahead.getByRole("listbox");
    await expect(list).toBeVisible();
    const options = list.getByRole("option");
    await expect(options.first()).toContainText("Methodology");
    // One fetch per shard key, cached — the second keystroke reuses it.
    await input.fill("met");
    await expect(options.first()).toBeVisible();
    expect(
      shardRequests.filter((u) => u.endsWith("/me.json")).length,
    ).toBeLessThanOrEqual(1);

    await input.press("ArrowDown");
    await expect(input).toHaveAttribute("aria-expanded", "true");
    const active = await input.getAttribute("aria-activedescendant");
    expect(active).toBeTruthy();
    await input.press("Enter");
    await page.waitForURL("**/methodology/**");
  });

  test("Escape closes; a plain Enter still submits the GET form", async ({
    page,
  }) => {
    await page.goto(HARNESS);
    const input = page.getByTestId("kit-typeahead-input");
    await input.fill("so");
    await expect(page.getByRole("listbox")).toBeVisible();
    await input.press("Escape");
    await expect(page.getByRole("listbox")).toBeHidden();
    // An unmatched query leaves the no-JS path intact: Enter submits the form.
    await input.fill("zz");
    await input.press("Enter");
    await page.waitForURL("**/search/?q=zz**");
  });

  test("the combobox + open listbox pass the WCAG 2.2 AA sweep", async ({
    page,
  }) => {
    await page.goto(HARNESS);
    await page.getByTestId("kit-typeahead-input").fill("me");
    await expect(
      page.locator("sig-typeahead").getByRole("option").first(),
    ).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(WCAG_TAGS)
      .analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });
});

test.describe("the K0 failure rule — module absent, markup unchanged", () => {
  test("blocking every /_kit/ module leaves the page complete and inert", async ({
    page,
  }) => {
    await page.route("**/_kit/**", (route) => route.abort());
    await page.goto(SOURCES);
    // Every row still renders; the toolbar never exists.
    await expect(page.getByTestId("source-row").first()).toBeVisible();
    await expect(page.locator(".sig-kit-bar")).toHaveCount(0);
    // The native disclosure still works — it was complete before the upgrade.
    await page.locator("summary", { hasText: "Cite" }).click();
    await expect(page.getByTestId("citation-text")).toBeVisible();
    await expect(page.locator(".sig-cite__formatted")).toHaveCount(0);
  });
});
