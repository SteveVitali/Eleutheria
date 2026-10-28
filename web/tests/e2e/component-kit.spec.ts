// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.22 (UXK14-3a, SIG-UI-054/083/084/086/151) — the component-kit-A harness
// sweep over the internal `/component-kit/` fixture page: every visual-layer
// component renders complete server HTML — the stat row's numerals live
// inside <Figure> regions (SIG-UI-084), the six card kinds render the one
// card contract, the table shell carries sortable/numeric semantics, and the
// chips/badges speak the shared lexicon, never a raw enum (SIG-UI-143).
// Runs in the "chromium" project; the no-JS twin is component-kit.nojs.spec.ts.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const HARNESS = "/component-kit/";

test("the stat row renders every numeral inside a <Figure> contract region", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const row = page.getByTestId("kit-stat-row");
  await expect(row.getByTestId("kit-stat-jurisdictions")).toBeVisible();
  await expect(row.getByTestId("kit-stat-sources")).toBeVisible();

  const stat = row.getByTestId("kit-stat-sources");
  // The numeral is grouped (SIG-UI-148) and sits inside a figure region that
  // carries the artifact + pointer contract (SIG-UI-084).
  await expect(stat).toContainText("64,212");
  const figure = stat.getByTestId("kit-stat-sources-figure");
  await expect(figure).toHaveAttribute("data-figure-id", "site-records");
  await expect(figure).toHaveAttribute("data-artifact", /counts\.json$/);
  await expect(figure).toHaveAttribute("data-pointer", "/attributes/site_records/count");
  // A stat names its denominator — never a bare count (§32.5, SIG-METRIC-010).
  await expect(stat.getByTestId("kit-stat-sources-denominator")).toContainText(
    "registry rows",
  );
  // The figure's evidence is reachable — the artifact link is on the figure.
  await expect(figure.locator("a[href*='counts.json']")).toHaveCount(1);
});

test("all six card kinds render the one contract, and the empty card is a typed state", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const grid = page.getByTestId("kit-card-grid");
  for (const kind of ["place", "organization", "source", "task", "persona", "example"]) {
    const card = grid.locator(`[data-card-kind="${kind}"]`).first();
    await expect(card, `${kind} card`).toBeVisible();
    // A non-empty card is a doorway: a titled link, never a dead card.
    const link = card.getByTestId("card-link");
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", /^\//);
  }

  // The persona card carries its linked start-here steps (K14 §6.1).
  const steps = grid
    .locator('[data-card-kind="persona"]')
    .getByTestId("card-steps")
    .locator("a");
  expect(await steps.count()).toBeGreaterThanOrEqual(3);
  expect(await steps.count()).toBeLessThanOrEqual(4);

  // The example card names its question (K14 §6.2).
  await expect(grid.locator('[data-card-kind="example"]')).toContainText(
    "Who can query this camera network?",
  );

  // The empty card renders the typed five-part state — never a dead card.
  const empty = grid.locator('[data-card-kind="place"]').last();
  const state = empty.getByTestId("empty-state");
  await expect(state).toBeVisible();
  await expect(state).toHaveAttribute("data-surface", "dossierIndex");
  await expect(state).toHaveAttribute("data-cause-class", "true");
  await expect(state).toHaveAttribute("data-cause", "not_published");
  // An absence cause keeps the single absence hatch.
  await expect(state).toHaveAttribute("data-hatch", "true");
  for (const part of ["state", "missing", "nearby", "action", "change"]) {
    await expect(
      state.getByTestId(`empty-state-${part}`),
      `empty card part ${part}`,
    ).toBeVisible();
  }
  // The affordance is a plain GET link.
  await expect(state.getByTestId("empty-state-cta")).toHaveAttribute("href", /^\//);
});

test("the table shell carries caption, scope, aria-sort and numeric columns at each density", async ({
  page,
}) => {
  await page.goto(HARNESS);
  for (const density of ["compact", "default", "roomy"]) {
    const table = page.getByTestId(`kit-table-${density}`).locator("table");
    await expect(table, `${density} table`).toHaveAttribute("data-density", density);
    await expect(table).toHaveClass(/sig-table/);
    await expect(table.locator("th[scope='col']").first()).toBeVisible();
    await expect(table.locator("td.sig-table__num").first()).toBeVisible();
  }
  // Sortable headers are plain GET links; aria-sort sits on the sorted column only.
  const def = page.getByTestId("kit-table-default");
  await expect(def.locator("caption")).toContainText("Fixture sources by row count");
  await expect(def.locator('th[aria-sort="ascending"]')).toContainText("Source");
  const sortLinks = def.locator("th a.sig-table__sortlink");
  expect(await sortLinks.count()).toBeGreaterThanOrEqual(2);
  await expect(sortLinks.first()).toHaveAttribute("href", /^\//);
});

test("the support chip carries glyph + lexicon label + evidence count with a native popover", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const chips = page.getByTestId("support-chip");
  await expect(chips).toHaveCount(2);
  const strong = chips.first();
  // Text + glyph, never colour alone (SIG-UI-003/005); the ⓘ is a real button
  // driving a UA-native popover (no JavaScript anywhere).
  await expect(strong.locator(".sig-chip__def")).toHaveAttribute(
    "popovertarget",
    "sc-fixture-strong",
  );
  await expect(strong.locator("span[popover]")).toHaveAttribute("id", "sc-fixture-strong");
  await expect(strong).toContainText("4");
});

test("the four epistemic chips are four independent fields — never fused", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const chips = page.getByTestId("field-chips");
  await expect(chips).toHaveAttribute("data-fused", "false");
  await expect(chips.locator("[data-field]")).toHaveCount(4);
  for (const field of ["resolution_status", "support", "agreement", "currency"]) {
    const chip = chips.locator(`[data-field="${field}"]`);
    await expect(chip).toBeVisible();
    // A chip names its field and carries the machine value on data-value.
    expect(await chip.getAttribute("data-value")).toBeTruthy();
  }
  // The support chip carries the four-step glyph + a text step equivalent.
  const support = chips.locator('[data-field="support"]');
  await expect(support.locator(".sig-chip__glyph")).toHaveAttribute(
    "data-filled-steps",
    "3",
  );
});

test("the status chips and neutral badges speak the lexicon, never a raw enum", async ({
  page,
}) => {
  await page.goto(HARNESS);
  for (const kind of [
    "provisional",
    "historical",
    "not_reviewed",
    "superseded",
    "withdrawn",
  ]) {
    const chip = page.getByTestId(`status-chip-${kind}`).first();
    await expect(chip, kind).toBeVisible();
    await expect(chip).toHaveAttribute("data-status", kind);
  }
  await expect(page.getByTestId("status-chip-historical").first()).toContainText(
    "since 2025-11",
  );

  for (const kind of ["directness", "access_kind", "licence", "mirror"]) {
    const badges = page.getByTestId(`badge-${kind}`);
    expect(await badges.count(), `${kind} badges`).toBeGreaterThanOrEqual(1);
    for (const badge of await badges.all()) {
      const value = await badge.getAttribute("data-value");
      expect(value, "badge data-value").toBeTruthy();
      // SIG-UI-143: the VISIBLE value word is a lexicon label / verbatim id,
      // never the re-cased enum — enum-shaped tokens stay on data-value.
      const text = (await badge.textContent()) ?? "";
      if (kind === "access_kind" || kind === "directness") {
        expect(text).not.toContain(`${value}`);
      }
    }
  }
  // Every §10.5 class and §12.2 kind is mounted — the closed vocabularies render.
  const block = page.getByTestId("kit-badge-block");
  expect(await block.getByTestId("badge-directness").count()).toBe(6);
  expect(await block.getByTestId("badge-access_kind").count()).toBe(3);
  expect(await block.getByTestId("badge-mirror").count()).toBe(3);
});

test("a figure reaches its evidence in at most two actions (SIG-UI-054)", async ({
  page,
  request,
}) => {
  // On the fixture dossier the <Figure> contract emits a visible "source"
  // link straight to the manifest-listed artifact — action one is the click,
  // and the artifact route itself carries the claim's evidence pointer, so
  // evidence is never more than two actions away.
  await page.goto("/dossier/oklahoma-city/");
  const figures = page.locator("main [data-figure-id]");
  const count = await figures.count();
  expect(count, "the dossier mounts figures").toBeGreaterThanOrEqual(1);
  for (let i = 0; i < count; i++) {
    const fig = figures.nth(i);
    const source = fig.locator('a[data-figure-link="source"]').first();
    await expect(source, `figure ${i} source link`).toBeVisible();
    const href = await source.getAttribute("href");
    expect(href, `figure ${i} source href`).toMatch(/^\//);
    const res = await request.get(href!);
    expect(res.status(), `figure ${i} evidence route ${href} resolves`).toBe(200);
  }
});

test("the harness is complete server HTML — no scripts, WCAG 2.2 AA clean", async ({
  page,
}) => {
  await page.goto(HARNESS);
  // The kit is the visual layer only: zero client JavaScript ships with it.
  await expect(page.locator("main script")).toHaveCount(0);
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
});
