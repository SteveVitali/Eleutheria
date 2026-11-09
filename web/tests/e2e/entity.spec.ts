// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P36.42a (K2 GX-06a): the `/entity/` hub + the 06a entity page — SIG-UI-070's
// counts + ER disclosure, H-2 relationship rows, the A-10 typed states, and
// SIG-UI-122's edge → provenance in ≤ 2 actions.
import { expect, test } from "@playwright/test";

const HUB = "/entity/";
const AGENCY = "/entity/agency/acworth-police-department--4g2wm8q/";

test.describe("the Organizations hub (SIG-UI-070 / UXR-20)", () => {
  test("lists the published types with counts + the ER disclosure", async ({ page }) => {
    await page.goto(HUB);
    const rows = page.locator('[data-testid="entity-type-row"]');
    await expect(rows).toHaveCount(3);
    await expect(page.locator('[data-testid="entity-types"]')).toContainText(
      "SIG has not merged organisations across sources",
    );
    // Every row links its per-type A–Z list.
    await expect(page.locator('a[href="/entity/org/"]')).not.toHaveCount(0);
    // The A-10 typed review state is named on the hub, never a name.
    await expect(page.locator('[data-testid="entity-type-review"]').first()).toContainText(
      "not yet independently reviewed",
    );
  });

  test("the per-type A–Z list carries published rows + typed review rows", async ({ page }) => {
    await page.goto("/entity/org/");
    const list = page.locator('[data-testid="entity-list"] li');
    await expect(list).toHaveCount(1);
    await expect(list.first()).toContainText("Vigilant Solutions (LEARN)");
    const review = page.locator('[data-testid="entity-review-row"]');
    await expect(review).toHaveCount(1);
    await expect(review.first()).toContainText("not yet independently reviewed");
    // ER disclosure on the list too.
    await expect(page.locator("#er-disclosure")).toContainText("one agency can appear more than once");
  });
});

test.describe("the 06a entity page (SIG-UI-114/115/116/122)", () => {
  test("renders header, claims, relationship tables, downloads and cite", async ({ page }) => {
    await page.goto(AGENCY);
    await expect(page.locator("h1")).toContainText("Acworth Police Department");
    await expect(page.locator('[data-testid="entity-header"]')).toContainText(
      "Not yet independently reviewed",
    );
    // Label basis shown (SIG-UI-110).
    await expect(page.locator('[data-testid="label-basis"]')).toHaveText("source_name");
    // The withheld-relationships notice, verbatim (SIG-UI-080).
    await expect(page.locator('[data-testid="withheld-notice"]')).toHaveText(
      "some relationships are not shown pending publication review",
    );
    // Claim groups: four epistemic fields separate (SIG-UI-004).
    const group = page.locator('[data-testid="claim-group"]');
    await expect(group.locator('[data-testid="epistemic-fields"] li')).toHaveCount(4);
    // Relationship tables: both direction groups render with H-2 fields.
    const groups = page.locator('[data-testid="relation-group"]');
    await expect(groups).toHaveCount(2);
    await expect(page.locator('[data-relation="configured sharing partner"]')).toContainText(
      "configured access",
    );
    // Historical + undated marked (SIG-UI-116/088).
    await expect(
      page.locator('[data-testid="relation-row"][data-historical="true"]'),
    ).toHaveCount(1);
    await expect(
      page.locator('[data-testid="relation-row"][data-date-kind="undated"]'),
    ).toHaveCount(1);
    // The "more" posture names the true total.
    await expect(page.locator('[data-testid="relation-more"]')).toContainText("all 3");
    // Degree-only is a sentence, never a relation row (H-4 / SIG-UI-117,
    // D-K2-3 verbatim).
    await expect(page.locator('[data-testid="degree-fact"]')).toContainText("partners not named");
    // GX-07 closures: the outbound group renders the 2-hop path with its
    // labelled hop chain and per-hop evidence links (SIG-UI-025).
    const closures = page.locator('[data-testid="access-closure-outbound"]');
    await expect(closures).toHaveCount(1);
    const path = closures.locator('[data-testid="access-path"]');
    await expect(path).toHaveCount(1);
    await expect(path.locator('[data-testid="access-path-chain"]')).toContainText(
      "Multi-state LEARN lookup pool",
    );
    await expect(path).toContainText("2 hops");
    await expect(
      path.locator('a[href="#claim-clm-vig-lookup-1"]'),
    ).toHaveCount(1);
    // Downloads carry the JSON twin; cite names the SIG id.
    await expect(
      page.locator('a[href="/entity/agency/acworth-police-department--4g2wm8q/index.sig_graph.json"]'),
    ).not.toHaveCount(0);
    await expect(page.locator('[data-testid="cite-sig-id"]')).toContainText("sig:agency:");
    // Contract-B sections render typed states, never gaps (SIG-UI-086).
    await expect(page.locator('[data-testid="entity-contract-b"]')).toContainText(
      "Not shipped in this record wave",
    );
  });

  test("edge → provenance in one action, no JS needed (SIG-UI-122)", async ({ page }) => {
    await page.goto(AGENCY);
    // Every relationship row's evidence link resolves to exactly one panel anchor.
    const link = page.locator(
      '[data-testid="relation-row"] [data-testid="relation-evidence"] a[href="#claim-clm-apd-vigilant-1"]',
    );
    await expect(link).toHaveCount(1);
    await expect(page.locator("#claim-clm-apd-vigilant-1")).toHaveCount(1);
    await link.click();
    await expect(page).toHaveURL(/#claim-clm-apd-vigilant-1$/);
  });

  test("the JSON twin endpoint serves sig.entity-page/1 bytes", async ({ request }) => {
    const res = await request.get(`${AGENCY}index.sig_graph.json`);
    expect(res.status()).toBe(200);
    const doc = await res.json();
    expect(doc.schema).toBe("sig.entity-page/1");
    expect(doc.label).toBe("Acworth Police Department");
  });
});

test.describe("the 06b figure companions (SIG-UI-094/122/130)", () => {
  test("the ego figure renders with its legend, open-doc link + linked nodes", async ({ page, request }) => {
    await page.goto(AGENCY);
    const fig = page.locator('[data-testid="entity-figure-ego"]');
    await expect(fig.locator("img.sig-entity-figure__img")).toHaveCount(1);
    // The standalone document is the figure's own link target — its bytes
    // carry every node as an <a href> (K2 §4.2 row 7).
    await expect(page.locator('[data-testid="entity-figure-ego-open"]')).toHaveAttribute(
      "href",
      `${AGENCY}ego.svg`,
    );
    const svg = await (await request.get(`${AGENCY}ego.svg`)).text();
    expect(svg).toContain('<a href="/entity/org/vigilant-solutions-learn--7xk3mrt/"');
    expect(svg).toContain('<a href="/entity/agency/acworth-police-department--4g2wm8q/"');
    await expect(page.locator('[data-testid="entity-figure-ego-legend"] li').first()).toBeVisible();
    // The explorer named-absence is text, never a dead route.
    await expect(page.locator('[data-testid="ego-explorer"] a')).toHaveCount(0);
  });

  test("the timeline strip draws dated events; undated items list apart", async ({ page }) => {
    await page.goto(AGENCY);
    await expect(page.locator('[data-testid="entity-figure-timeline"] img')).toHaveCount(1);
    await expect(page.locator('[data-testid="timeline-undated"]')).toContainText("camera operator");
  });

  test("the map snippet draws the recorded place", async ({ page }) => {
    await page.goto(AGENCY);
    await expect(page.locator('[data-testid="entity-figure-map"] img')).toHaveCount(1);
    await expect(page.locator('[data-testid="entity-figure-map-caption"]')).toContainText("usa-ga");
  });

  test("the print page is T0: figures print, no script anywhere", async ({ page }) => {
    await page.goto(`${AGENCY}print/`);
    await expect(page.locator("script")).toHaveCount(0);
    await expect(page.locator('[data-testid="print-page"]')).toHaveCount(4);
    await expect(page.locator('[data-testid="print-figures"] img')).not.toHaveCount(0);
    await expect(page.locator('[data-testid="print-tables"] table')).not.toHaveCount(0);
  });
});
