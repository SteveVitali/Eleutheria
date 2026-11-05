// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.69 (UX10-3b): the source page-B sub-routes — runs, captures,
// changes, versions, entities, dossiers — render zero-JS, carry the JSON
// twins, embed entity ids for the page_index withdrawal seam, and never
// emit a sub-route for a registry-only source (S-11).
import { test, expect } from "@playwright/test";

const SRC = "okc_camera_registry";

test.describe("source page B", () => {
  test("the index links the page-B sections and the JSON twin", async ({ page }) => {
    await page.goto(`/sources/${SRC}/`);
    await expect(page.getByTestId("source-subnav")).toBeVisible();
    await expect(page.getByTestId("page-b-sections")).toBeVisible();
    await expect(page.getByTestId("pageb-runs")).toContainText("recorded executions");
    await expect(page.getByTestId("pageb-captures")).toContainText("recorded captures");
    await expect(page.locator('link[rel="alternate"][type="application/json"]')).toHaveAttribute(
      "href",
      /\/sources\/okc_camera_registry\/index\.json$/,
    );
  });

  test("runs: one <details> per execution, host+count robots disclosure", async ({ page }) => {
    await page.goto(`/sources/${SRC}/runs/`);
    await expect(page.locator("#runs-heading")).toContainText("Runs");
    const rows = page.getByTestId("run-row");
    await expect(rows).toHaveCount(3);
    await expect(page.getByTestId("executions-total")).toContainText("3");
    // D-J3-2 = yes: robots disclose host + count, never per-URL detail.
    await expect(page.getByTestId("run-robots").first()).toContainText(":");
    // JSON twin resolves.
    const res = await page.request.get(`/sources/${SRC}/runs/index.json`);
    expect(res.ok()).toBeTruthy();
    const doc = await res.json();
    expect(doc.schema).toBe("sig.source-runs/1");
    expect(doc.execution_count).toBe(3);
  });

  test("captures: the file-action table renders every lane cell", async ({ page }) => {
    await page.goto(`/sources/${SRC}/captures/`);
    await expect(page.getByTestId("captures-total")).toContainText("6");
    const actions = await page.getByTestId("capture-action").allTextContents();
    const joined = actions.join("|");
    expect(joined).toContain("Download original");
    expect(joined).toContain("SIG did not retain these bytes");
    expect(joined).toContain("run record");
    // no dead download href — the raw archive is unpublished.
    for (const a of actions) expect(a).not.toContain("download_host_pending");
    // The Part VIII redacted cell is per-source (the source row's
    // part_viii_class governs every capture): okc_council_minutes carries
    // P8-5, so its raw-ok + retained capture renders the redacted cell.
    await page.goto("/sources/okc_council_minutes/captures/");
    const p8Actions = await page.getByTestId("capture-action").allTextContents();
    expect(p8Actions.join("|")).toContain("Download redacted copy");
  });

  test("captures/changes lists only record-set changes", async ({ page }) => {
    await page.goto(`/sources/${SRC}/captures/changes/`);
    await expect(page.locator("#captures-heading")).toContainText("Capture changes");
    const rows = page.getByTestId("capture-row");
    expect(await rows.count()).toBe(1);
    await expect(rows.first()).toContainText("records changed");
  });

  test("versions: the index renders extract + manifest-only + absent states", async ({ page }) => {
    await page.goto(`/sources/${SRC}/versions/`);
    await expect(page.locator("#versions-heading")).toContainText("Versions and downloads");
    const states = await page.getByTestId("version-state").allTextContents();
    expect(states.join("|")).toContain("manifest only");
    expect(states.join("|")).toContain("extract absent");
    expect(states.join("|")).toContain("extract");
    const res = await page.request.get(`/sources/${SRC}/versions/index.json`);
    const doc = await res.json();
    expect(doc.schema).toBe("sig.source-versions/1");
    expect(doc.entry_count).toBe(3);
  });

  test("entities: capped browse with data-entity-id rows", async ({ page }) => {
    await page.goto(`/sources/${SRC}/entities/`);
    await expect(page.locator("#entities-heading")).toContainText("Published entities");
    const rows = page.getByTestId("entity-row");
    expect(await rows.count()).toBe(3);
    expect(await rows.first().getAttribute("data-entity-id")).toBe("device:okc-001");
  });

  test("entities cap: the 1050-row source states the 1000 cap and paginates", async ({ page }) => {
    await page.goto(`/sources/demo_seed_load/entities/`);
    // K14 §3.6: grouping starts at five digits — 4-digit counts stay ungrouped.
    await expect(page.getByTestId("entities-total")).toContainText("1050");
    await expect(page.getByTestId("entities-total")).toContainText("1000");
    await expect(page.getByTestId("entity-row")).toHaveCount(100);
    await expect(page.getByTestId("pager-next")).toBeVisible();
    await page.goto(`/sources/demo_seed_load/entities/page/10/`);
    await expect(page.getByTestId("entity-row")).toHaveCount(100);
  });

  test("runs pagination at 100 per page", async ({ page }) => {
    await page.goto(`/sources/demo_ingested_feed/captures/`);
    await expect(page.getByTestId("capture-row")).toHaveCount(100);
    await page.goto(`/sources/demo_ingested_feed/captures/page/3/`);
    await expect(page.getByTestId("capture-row")).toHaveCount(30);
    await page.goto(`/sources/demo_ingested_feed/captures/changes/`);
    const changes = await page.getByTestId("capture-row").count();
    expect(changes).toBe(100);
    await page.goto(`/sources/demo_ingested_feed/captures/changes/page/2/`);
    expect(await page.getByTestId("capture-row").count()).toBe(15);
  });

  test("dossier contribution table carries the shared rows + basis", async ({ page }) => {
    await page.goto(`/sources/${SRC}/dossiers/`);
    await expect(page.locator("#dossiers-heading")).toContainText("Dossier contribution");
    await expect(page.getByTestId("contribution-basis")).toContainText("declared by the source");
    const res = await page.request.get(`/sources/${SRC}/dossiers/index.json`);
    const doc = await res.json();
    expect(doc.contributions.length).toBe(1);
  });

  test("registry-only sources emit no page-B sub-routes (S-11)", async ({ page }) => {
    for (const sub of ["runs/", "captures/", "versions/", "entities/", "dossiers/"]) {
      const res = await page.request.get(`/sources/demo_gated_registry/${sub}`);
      expect(res.status(), sub).toBe(404);
    }
  });

  test("the sig.source-page/2 twin serves the page model", async ({ page }) => {
    const res = await page.request.get(`/sources/${SRC}/index.json`);
    const doc = await res.json();
    expect(doc.schema).toBe("sig.source-page/2");
    expect(doc.registry_only).toBe(false);
    expect(doc.links.runs).toBeTruthy();
    expect(doc.latest_executions.length).toBe(3);
  });
});
