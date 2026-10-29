// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.20 (UXK0-4, SIG-UI-091) — the no-JS half of the enhancement kit's
// contract: every upgraded surface is COMPLETE without the module. The
// server-rendered markup carries every row, every fact and every fallback —
// the elements only add `[data-enhancement]` chrome, which simply never
// exists here. Runs in the "no-js" project (JavaScript disabled).

import { test, expect } from "@playwright/test";

const SOURCES = "/sources/";
const HARNESS = "/enhancement-kit/";

test("the sources table renders every row and fact without JS", async ({
  page,
}) => {
  await page.goto(SOURCES);
  const rows = page.getByTestId("source-row");
  await expect(rows).toHaveCount(2);
  for (const row of await rows.all()) {
    await expect(row).toBeVisible();
  }
  await expect(rows.first()).toContainText("demo-municipal-portal");
  // No enhancement chrome exists — nothing injected, nothing hidden.
  await expect(page.locator("[data-enhancement]")).toHaveCount(0);
  await expect(page.locator(".sig-kit-bar")).toHaveCount(0);
  // Every column header is plain server text — no sort buttons without the
  // element module.
  await expect(page.locator("sig-table th button")).toHaveCount(0);
});

test("the cite block's verbatim sentence and link work without JS", async ({
  page,
}) => {
  await page.goto(SOURCES);
  // The native disclosure opens on click — no module needed.
  await page.locator("summary", { hasText: "Cite" }).click();
  await expect(page.getByTestId("citation-text")).toBeVisible();
  await expect(page.getByTestId("permalink").first()).toBeVisible();
  await expect(page.locator(".sig-cite__formatted")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Copy link" }),
  ).toHaveCount(0);
});

test("the harness typeahead is a plain GET form without JS", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const form = page.getByTestId("kit-typeahead-form");
  await expect(form).toHaveAttribute("action", "/search/");
  const input = page.getByTestId("kit-typeahead-input");
  await expect(input).toBeVisible();
  // Plain input semantics — the combobox upgrade never ran.
  await expect(input).not.toHaveAttribute("role", "combobox");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await input.fill("method");
  await input.press("Enter");
  await page.waitForURL("**/search/?q=method**");
});

test("the harness table and disclosure are complete without JS", async ({
  page,
}) => {
  await page.goto(HARNESS);
  const rows = page.getByTestId("kit-row");
  await expect(rows).toHaveCount(4);
  for (const row of await rows.all()) {
    await expect(row).toBeVisible();
  }
  // A fragment still lands; the disclosure stays operable by click alone.
  await page.locator("#harness-details summary").click();
  await expect(page.locator("#harness-details")).toHaveJSProperty(
    "open",
    true,
  );
});
