// SPDX-License-Identifier: Apache-2.0
// P36.36 (K1 MAP-05, UXR-18, SIG-UI-068/105): the no-JS sites lists.
import { test, expect } from "@playwright/test";

const OKC = "/dossier/usa/ok/oklahoma-city-4064000/sites/";
const HARRIS = "/dossier/usa/tx/harris-county-48201/sites/";

test("the sites list renders without JS — rows, anchors, compartment groups", async ({ page, request }) => {
  await page.goto(OKC);
  const rows = page.getByTestId("site-row");
  expect(await rows.count()).toBeGreaterThan(0);
  // The row anchor is the record key verbatim (UXR-18's interim target).
  const first = rows.first();
  const id = await first.getAttribute("id");
  expect(id).toBeTruthy();
  await expect(first.getByTestId("site-anchor")).toHaveAttribute("href", `#${id}`);
  // Compartment grouping carries a licence line per group.
  await expect(page.getByTestId("sites-licence-line").first()).toContainText("Licence:");
  // Coordinates print only at the published precision — a tier-3 row shows its
  // precision words, never a point.
  const t3 = page.locator("[data-testid='site-row'][data-tier='3']").first();
  await expect(t3.getByTestId("site-no-coords")).toContainText("jurisdiction only");
  // The CSV download exists and names the licence in a comment line.
  const csv = page.getByTestId("sites-csv");
  await expect(csv).toBeVisible();
  const href = (await csv.getAttribute("href"))!;
  const resp = await request.get(href);
  expect(resp.ok()).toBeTruthy();
  const text = await resp.text();
  expect(text).toContain("# SIG dossier sites list");
  expect(text).toContain("device:okc-001");
});

test("pagination by path — page 2 exists and links back", async ({ page }) => {
  await page.goto(HARRIS);
  await expect(page.getByTestId("sites-pager")).toContainText("Page 1 of 2");
  await page.getByRole("link", { name: "Next page" }).click();
  await expect(page).toHaveURL(/\/sites\/page\/2\/$/);
  await expect(page.getByTestId("sites-pager")).toContainText("Page 2 of 2");
  await page.getByRole("link", { name: "Previous page" }).click();
  await expect(page).toHaveURL(new RegExp(HARRIS.replace(/\//g, "\\/") + "$"));
});

test("every map link resolves — the link crawl (K1 J8)", async ({ request }) => {
  const seeds = ["/map/", OKC, HARRIS, `${HARRIS}page/2/`, "/dossier/"];
  const seen = new Set<string>();
  const queue = [...seeds];
  let checked = 0;
  const bad: string[] = [];
  while (queue.length > 0 && checked < 400) {
    const path = queue.shift()!;
    if (seen.has(path)) continue;
    seen.add(path);
    const res = await request.get(path);
    if (!res.ok()) { bad.push(`${path} → ${res.status()}`); continue; }
    checked += 1;
    const html = await res.text();
    for (const m of html.matchAll(/href="(\/[^"#]*)#?[^"]*"/g)) {
      const href = m[1]!;
      // Namespaces that are not emitted static routes by design — the API
      // (`/v1/`), the artifact/release/record trees (`/artifact/`,
      // `/releases/`, `/r/` — the record tree's public exposure is G2's row).
      const NON_STATIC = /^\/(v1|artifact|releases|r)\//;
      if (!seen.has(href) && href.startsWith("/") && !NON_STATIC.test(href)) queue.push(href);
    }
  }
  expect(bad, `broken internal links: ${bad.join(", ")}`).toEqual([]);
  expect(checked).toBeGreaterThan(seeds.length - 1);
});
