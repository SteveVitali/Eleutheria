// SPDX-License-Identifier: Apache-2.0
// P36.35 (JUR-05 / SIG-UI-058, SIG-JUR-009) — the migration stub surfaces:
// every historical slug answers with its stub kind, the moved stub carries
// the zero-JS refresh to its successor, and the /id/ fallback pages resolve
// through the same seam the generated include reads.
import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

test.describe("JUR-05 migration stubs", () => {
  test("the split page names both successor paths honestly", async ({ page }) => {
    await page.goto("/dossier/id/");
    const stub = page.getByTestId("dossier-stub");
    await expect(stub).toBeVisible();
    await expect(page.getByTestId("dossier-stub-note")).toContainText("Idaho");
  });

  test("the correction page is served in place (never a rename)", async ({ page }) => {
    await page.goto("/dossier/bd/");
    await expect(page.getByTestId("dossier-stub")).toContainText("corrected");
    await expect(page.getByTestId("dossier-stub-note")).toContainText("Singapore");
  });

  test("the moved stub carries a 0-second meta refresh to its successor", async ({ page }) => {
    const html = readFileSync(join(process.cwd(), "dist/dossier/unresolved/index.html"), "utf-8");
    expect(html).toContain('http-equiv="refresh"');
    expect(html).toContain("dossier/unplaced/");
    expect(html).toContain('name="robots" content="noindex"');
  });

  test("the corrections log carries the migration entries (D-K4-8)", async ({ page }) => {
    await page.goto("/corrections/");
    await expect(page.locator('[data-correction-id="migration-merged-places"]')).toBeVisible();
    await expect(page.locator('[data-correction-id="migration-mislabelled-records"]')).toBeVisible();
    await expect(page.locator('[data-correction-id="migration-replaced-unresolved"]')).toBeVisible();
  });

  test("/id/ fallback pages resolve per status — never a 404, never a dead link", async ({ page }) => {
    await page.goto("/id/agency/agency:okcpd/");
    await expect(page.getByTestId("id-stub")).toBeVisible();
    await page.goto("/id/agency/agency:okcpd-field-operations/");
    await expect(page.getByTestId("id-stub")).toHaveAttribute("data-status", "split");
    await page.goto("/id/atlas/atlas:okc-fairgrounds-cameras/");
    await expect(page.getByTestId("id-stub")).toHaveAttribute("data-status", "withdrawn");
  });

  test("the generated include exists and is the one mechanism", async ({ page }) => {
    const conf = readFileSync(join(process.cwd(), "dist/redirects.conf"), "utf-8");
    expect(conf).toContain("sig.redirects-conf/1");
    expect(conf).toContain("location = /dossier/unresolved/");
    expect(conf).toContain("location /task/new/ { return 410; }");
  });
});
