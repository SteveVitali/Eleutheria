// SPDX-License-Identifier: Apache-2.0
/** P37.24 (GX-08a) — the /graphs/ T1 pages: hub, overview, drill-down,
 * downloads, JS-off parity. */
import { expect, test } from "@playwright/test";

test.describe("/graphs/ overview pages", () => {
  test("hub lists every emitted overview", async ({ page }) => {
    await page.goto("/graphs/");
    const rows = page.getByTestId("graphs-index-row");
    await expect(rows).toHaveCount(4);
    await expect(page.getByRole("link", { name: "Supply" })).toBeVisible();
  });

  test("overview page: static figure + adjacency table with H-2 fields", async ({ page }) => {
    await page.goto("/graphs/supply/");
    await expect(page.getByTestId("graph-figure")).toBeVisible();
    const rows = page.getByTestId("graph-edge-row");
    await expect(rows.first()).toBeVisible();
    const first = rows.first();
    await expect(first).toContainText("sells to");
    // SIG-EXPORT-015 — date, currency, sources shown per edge.
    await expect(first).toContainText("2020-01-28");
    await expect(
      page.getByTestId("graph-edges").getByText(/Vigilant Solutions \(LEARN\)/),
    ).toBeVisible();
    // undated edges are visibly marked, never present-tense.
    await expect(page.getByText("undated").first()).toBeVisible();
  });

  test("per-place drill-down filters the overview", async ({ page }) => {
    await page.goto("/graphs/supply/usa/ok/");
    await expect(page.getByText(/Scoped to/)).toBeVisible();
    await expect(page.getByTestId("graph-edge-row").first()).toBeVisible();
  });

  test("download endpoints serve every named artifact", async ({ request }) => {
    for (const f of ["sig_graph.json", "edges.sig_graph.csv", "nodes.sig_graph.csv", "overview.sig_graph.svg"]) {
      const res = await request.get(`/graph/supply/${f}`);
      expect(res.status()).toBe(200);
    }
    const json = await (await request.get("/graph/supply/sig_graph.json")).json();
    expect(json.schema).toBe("sig.graph-overview/1");
  });

  test("JS off shows the same facts", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto("/graphs/supply/");
    await expect(page.getByTestId("graph-edge-row").first()).toBeVisible();
    await expect(
      page.getByTestId("graph-edges").getByText(/Vigilant Solutions \(LEARN\)/),
    ).toBeVisible();
    await ctx.close();
  });
});
