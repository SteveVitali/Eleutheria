// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.56 (K3 SRCH-06 / SIG-UI-128): the scoped-search forms — "Search within
// <place>" on every dossier (`jurisdiction=<jkey>`, descendants carried by
// the contract parameter per SIG-UI-059) and "Search this source" on source
// pages (`source=<id>`). Both are zero-JS GET forms pinned to the release's
// federated route; the `<sig-typeahead>` wrapper only upgrades the field —
// the scope attribute narrows its suggestions.
import { test, expect } from "@playwright/test";

test.describe("dossier scoped search (SIG-UI-128)", () => {
  test("a keyed dossier carries the zero-JS GET form with jurisdiction=<jkey>", async ({
    page,
  }) => {
    await page.goto("/dossier/usa/ok/");
    const section = page.getByTestId("dossier-scoped-search");
    await expect(section).toBeVisible();
    const form = page.getByTestId("dossier-scoped-search-form");
    await expect(form).toHaveAttribute("method", "get");
    const action = await form.getAttribute("action");
    expect(action).toContain("/v1/releases/");
    expect(action).toContain("/search");
    // The contract parameters: format=html + jurisdiction=<the dossier's key>.
    await expect(form.locator("input[name='format']")).toHaveAttribute(
      "value",
      "html",
    );
    await expect(
      page.getByTestId("dossier-scoped-search-scope"),
    ).toHaveAttribute("name", "jurisdiction");
    await expect(
      page.getByTestId("dossier-scoped-search-scope"),
    ).toHaveAttribute("value", "iso3166-2:US-OK");
    await expect(form.locator("input[name='q']")).toBeVisible();
    await expect(form.locator("button[type='submit']")).toContainText(
      "Search within Oklahoma",
    );
    // The typeahead scope attribute narrows suggestions to the subtree.
    await expect(
      page.getByTestId("dossier-scoped-search-typeahead"),
    ).toHaveAttribute("scope", "jurisdiction:iso3166-2:US-OK");
  });

  test("a descendant scope narrows the suggestions to the subtree", async ({
    page,
  }) => {
    await page.goto("/dossier/usa/");
    const input = page.locator(
      "[data-testid='dossier-scoped-search-typeahead'] input[name='q']",
    );
    await input.fill("ok");
    const list = page.locator(
      "[data-testid='dossier-scoped-search-typeahead'] [role='listbox']",
    );
    // The element upgrades the field only when JS runs; a scoped query that
    // finds in-scope places opens the listbox and every option is a place
    // inside the subtree (the filter itself is unit-pinned).
    await expect(list).toBeVisible({ timeout: 10000 });
    const texts = await list.getByRole("option").allTextContents();
    expect(texts.length).toBeGreaterThan(0);
    // A subtree place appears — "Oklahoma" itself — never just the
    // out-of-scope registry/research entries that also key under "ok".
    expect(texts.some((t) => t.startsWith("Oklahoma"))).toBe(true);
    // An out-of-scope sibling (Texas, sources, the OKC research dossier)
    // is never suggested under a jurisdiction scope.
    expect(texts.some((t) => t.startsWith("Texas"))).toBe(false);
  });

  test("a county dossier scopes to the county key", async ({ page }) => {
    await page.goto("/dossier/usa/ok/oklahoma-county-40109/");
    await expect(
      page.getByTestId("dossier-scoped-search-scope"),
    ).toHaveAttribute("value", "us.census.geoid.county:40109");
  });
});

test.describe("source scoped search", () => {
  test("a source page carries 'Search this source' with source=<id>", async ({
    page,
  }) => {
    await page.goto("/sources/okc_camera_registry/");
    const form = page.getByTestId("source-scoped-search-form");
    await expect(form).toBeVisible();
    const action = await form.getAttribute("action");
    expect(action).toContain("/v1/releases/");
    await expect(
      page.getByTestId("source-scoped-search-scope"),
    ).toHaveAttribute("name", "source");
    await expect(
      page.getByTestId("source-scoped-search-scope"),
    ).toHaveAttribute("value", "okc_camera_registry");
    await expect(
      page.getByTestId("source-scoped-search-typeahead"),
    ).toHaveAttribute("scope", "source:okc_camera_registry");
  });
});
