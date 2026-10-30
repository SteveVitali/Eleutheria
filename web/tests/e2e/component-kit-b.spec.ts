// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.23 (UXK14-3b, SIG-UI-083/086/151 + capstone journeys J3/O4) — the
// component-kit-B harness sweep over the internal `/component-kit/` fixture
// page: the contested marker distinguishes its two levels and links to the
// both-sides surface, the range labels one dot per claim, the absence chip
// carries the four kinds plus "Help find it", the one provenance panel
// renders inside its shell, callouts keep the closed vocabulary, the
// incompleteness banner stays neutral, all eight typed empty causes render
// five parts, and the branded error states carry the recovery trio — all
// complete server HTML, no JavaScript. Runs in the "chromium" project; the
// no-JS twin is component-kit-b.nojs.spec.ts.

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const HARNESS = "/component-kit/";

test("the contested marker names both levels and links to the both-sides surface (J3)", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const markers = page.getByTestId("contested-marker");
  await expect(markers.filter({ hasText: "Contested" }).first()).toBeVisible();
  await expect(markers.filter({ hasText: "Unresolved" }).first()).toBeVisible();
  // The levels carry their machine values.
  await expect(markers.filter({ hasText: "Contested" }).first()).toHaveAttribute(
    "data-agreement",
    "CONTESTED",
  );
  await expect(markers.filter({ hasText: "Unresolved" }).first()).toHaveAttribute(
    "data-agreement",
    "IRRECONCILABLE",
  );
  // Both sides one click away — the linked markers resolve to an in-page anchor.
  const linked = page.locator("a[data-testid='contested-marker']");
  expect(await linked.count()).toBeGreaterThanOrEqual(2);
  await expect(linked.first()).toHaveAttribute("href", "#kit-b-range");
});

test("the contradiction range labels one dot per claim and keeps the different-quantity note", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const ranges = page.getByTestId("contradiction-range");
  await expect(ranges).toHaveCount(2);

  const contested = ranges.first();
  await expect(contested).toHaveAttribute("data-agreement", "CONTESTED");
  await expect(contested.locator("figcaption")).toContainText("Contested range");
  // One labelled point per claim — three claims, three ordinal labels.
  await expect(contested.locator(".sig-range__point")).toHaveCount(3);
  await expect(contested.locator(".sig-range__point-label")).toHaveCount(3);
  // The different-quantity note keeps the honesty caveat visible (§29.1).
  await expect(contested.getByTestId("different-quantity-note")).toContainText(
    "different quantity",
    { ignoreCase: true },
  );
  // The claims list is the equivalent — every claim names source + tier + date.
  await expect(contested.getByTestId("competing-claim")).toHaveCount(3);

  const unresolved = ranges.nth(1);
  await expect(unresolved).toHaveAttribute("data-agreement", "IRRECONCILABLE");
  await expect(unresolved.locator("figcaption")).toContainText("Unresolved range");
  await expect(unresolved).toHaveClass(/sig-range--unresolved/);
});

test("the absence chip carries the four kinds plus the 'Help find it' action (O4)", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const block = page.getByTestId("kit-absence-chips");
  const chips = block.getByTestId("absence-chip");
  await expect(chips).toHaveCount(4);
  const expected: [string, string][] = [
    ["NOT_RESEARCHED", "Not researched"],
    ["NO_EVIDENCE_FOUND", "None found"],
    ["EVIDENCE_OF_ABSENCE", "Stated absent"],
    ["UNRESOLVED", "Unresolved"],
  ];
  for (let i = 0; i < expected.length; i++) {
    const [kind, label] = expected[i]!;
    const chip = chips.nth(i);
    await expect(chip).toHaveAttribute("data-absence-kind", kind);
    // The kind symbol rides the hatch next to the lexicon label.
    await expect(chip.locator(".sig-absence-hatch__symbol")).toBeVisible();
    await expect(chip).toContainText(label);
    // The meaning popover is UA-native — a real button + a named popover id.
    await expect(chip.locator(".sig-absence-chip__def")).toHaveAttribute(
      "popovertarget",
      `ac-harness-${kind.toLowerCase()}`,
    );
    // The affordance is a plain GET link under its copy-batch id.
    const help = chip.locator(".sig-absence-chip__help");
    await expect(help).toHaveText("Help find it ›");
    await expect(help).toHaveAttribute("data-copy", "CK-61");
    await expect(help).toHaveAttribute("href", "/research-queue/");
  }
  // The O4 seam: where a real task page exists, the chip links straight to it.
  const tasked = page.locator(
    "[data-testid='absence-chip']:has(span[popover][id='ac-harness-tasked'])",
  );
  await expect(tasked.locator(".sig-absence-chip__help")).toHaveAttribute(
    "href",
    "/task/example-task-handle/",
  );
});

test("the provenance panel renders the one contract inside its shell — full and absent", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const panels = page.getByTestId("kit-provenance").locator("[data-provenance-panel]");
  await expect(panels).toHaveCount(2);
  const full = panels.first();
  await expect(full).toHaveAttribute("data-binding-state", "document_only");
  // The anchor contract — #claim-<id> resolves to the panel itself.
  await expect(full).toHaveAttribute("id", "claim-fixture-claim-panel");
  // Fields read label + value — the verbatim binding-state wording is verbatim.
  await expect(full).toContainText("Binding state");
  const absent = panels.nth(1);
  await expect(absent).toHaveAttribute("data-binding-state", "not_recorded");
  await expect(absent).toContainText("not_recorded");
});

test("callouts keep the closed kind vocabulary with batch-tracked labels", async ({ page }) => {
  await page.goto(HARNESS);
  const block = page.getByTestId("kit-callouts");
  const kinds: [string, string, string][] = [
    ["note", "callout-note", "CK-62"],
    ["caution", "callout-caution", "CK-63"],
    ["known_issue", "callout-known-issue", "CK-64"],
  ];
  for (const [kind, testid, batch] of kinds) {
    const callout = block.getByTestId(testid);
    await expect(callout).toBeVisible();
    await expect(callout).toHaveAttribute("data-callout-kind", kind);
    await expect(callout.locator(".sig-callout__title")).toHaveAttribute(
      "data-copy",
      batch,
    );
  }
});

test("the incompleteness banner renders the dossier's honest count, neutrally", async ({ page }) => {
  await page.goto(HARNESS);
  const banner = page.getByTestId("kit-incomplete").getByTestId("incompleteness-banner");
  await expect(banner).toBeVisible();
  // The absence rule rides every banner (SIG-UI-012).
  await expect(banner).toContainText("absence of a row is not evidence of absence");
  // The count is data, not a decorative zero.
  expect(Number(await banner.getAttribute("data-unknown"))).toBeGreaterThan(0);
});

test("all eight typed empty causes render five parts — hatch only for real absence", async ({
  page,
}) => {
  await page.goto(HARNESS);
  // The absence-cause mounts keep the hatch (not_researched, not_reviewed,
  // none_recorded across the three surface fixtures).
  const absenceBlock = page.getByTestId("kit-empty-absence");
  for (const cause of ["not_researched", "not_reviewed", "none_recorded"]) {
    const state = absenceBlock.locator(`[data-cause="${cause}"]`);
    await expect(state, cause).toBeVisible();
    await expect(state).toHaveAttribute("data-hatch", "true");
    for (const part of ["state", "missing", "nearby", "action", "change"]) {
      await expect(state.getByTestId(`empty-state-${part}`)).toBeVisible();
    }
  }
  // The non-absence kinds render the same five parts and no hatch.
  const nonAbsenceBlock = page.getByTestId("kit-empty-non-absence");
  for (const cause of ["filtered_none", "not_redistributable", "degraded"]) {
    const state = nonAbsenceBlock.locator(`[data-cause="${cause}"]`);
    await expect(state, cause).toBeVisible();
    await expect(state).toHaveAttribute("data-hatch", "false");
    await expect(state.locator(".sig-empty__hatch")).toHaveCount(0);
    for (const part of ["state", "missing", "nearby", "action", "change"]) {
      await expect(state.getByTestId(`empty-state-${part}`)).toBeVisible();
    }
  }
});

test("the branded error states carry five parts and the recovery trio — never a hatch", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const block = page.getByTestId("kit-error-states");
  const kinds = ["not_found", "refused", "removed", "server_error"];
  await expect(block.locator("[data-testid='error-state']")).toHaveCount(4);
  for (const kind of kinds) {
    const state = block.locator(`[data-error-kind="${kind}"]`);
    await expect(state, kind).toBeVisible();
    // The recovery trio — search, home and status links on every error page
    // (SIG-UI-151); an error is never an absence, so no hatch element exists.
    const recovery = state.getByTestId("error-recovery").locator("a");
    await expect(recovery).toHaveCount(2);
    await expect(state.locator(".sig-error__action a")).toHaveText("Go to the home page");
    await expect(state.locator(".sig-empty__hatch")).toHaveCount(0);
  }
});

test("the kit-B harness section is complete server HTML — no scripts, WCAG 2.2 AA clean", async ({
  page,
}) => {
  await page.goto(HARNESS);
  await expect(page.locator("main script")).toHaveCount(0);
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
});
