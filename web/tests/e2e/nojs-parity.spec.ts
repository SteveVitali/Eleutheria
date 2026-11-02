// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.50 (UXK0-1, K0 §4.12 item 3, ADR-155, SIG-UI-037/050): the no-JS parity
// spec, iterated over the DISCOVERED routes. Two contracts:
//
//   T1 — the text of `main` with JavaScript OFF equals the text with JS ON,
//        minus `[data-enhancement]` subtrees. An enhancement element may add
//        behaviour chrome; it may never add or withhold a fact.
//   T2 — the registry's named no-JS equivalents exist and resolve with JS off,
//        and a stateful `sig.workspace-state/1` URL opened with JS off shows
//        the notice naming what the URL encodes and where the records live.
//
// The spec runs in the chromium project and creates its own JavaScript-OFF
// contexts — the same test needs both engine postures, which neither project
// offers alone.

import { test, expect, type Browser, type Page } from "@playwright/test";
import { gotoSettled, T1_PAGES, T2_PAGES } from "./pages";
import { classifyRoute } from "../../src/lib/page-types";

/** Rendered `main` text with every `[data-enhancement]` subtree removed. */
async function mainText(page: Page): Promise<string> {
  return page.evaluate(() => {
    const main = document.querySelector("main");
    if (main === null) return "<no main>";
    const clone = main.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("[data-enhancement]").forEach((el) => el.remove());
    return (clone.textContent ?? "").replace(/\s+/g, " ").trim();
  });
}

async function noJsPage(browser: Browser, path: string): Promise<Page> {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await gotoSettled(page, path);
  return page;
}

test.describe("T1 parity: main text JS-off == JS-on minus [data-enhancement]", () => {
  for (const path of T1_PAGES) {
    test(`${path}`, async ({ page, browser }) => {
      await gotoSettled(page, path);
      const jsOn = await mainText(page);
      const jsOffPage = await noJsPage(browser, path);
      const jsOff = await mainText(jsOffPage);
      expect(jsOff, `${path}: JS-off main text must equal JS-on minus [data-enhancement]`).toBe(
        jsOn,
      );
      await jsOffPage.context().close();
    });
  }

  test("the parity rule tolerates ONLY [data-enhancement] additions", async ({ page, browser }) => {
    // Mechanism proof on a real T1 route: an injected data-enhancement subtree
    // is the ONLY tolerated JS-on/off difference; an unmarked difference is caught.
    const path = T1_PAGES[0]!;
    await page.goto(path);
    const jsOff = await mainText(await noJsPage(browser, path));

    await page.evaluate(() => {
      const el = document.createElement("p");
      el.setAttribute("data-enhancement", "");
      el.textContent = "ENHANCEMENT-ONLY TEXT";
      document.querySelector("main")!.appendChild(el);
    });
    expect(await mainText(page)).toBe(jsOff);

    await page.evaluate(() => {
      const el = document.createElement("p");
      el.textContent = "UNMARKED-DIFFERENCE TEXT";
      document.querySelector("main")!.appendChild(el);
    });
    expect(await mainText(page)).not.toBe(jsOff);
  });
});

test.describe("T2: named no-JS equivalents resolve with JS off", () => {
  for (const path of T2_PAGES) {
    test(`${path}`, async ({ browser }) => {
      const classification = classifyRoute(path);
      expect(classification.ok && classification.entry.type === "T2").toBe(true);
      const testIds = classification.ok ? (classification.entry.noJsEquivalent.testIds ?? []) : [];
      expect(testIds.length, `${path} names no no-JS equivalent testIds`).toBeGreaterThan(0);
      const page = await noJsPage(browser, path);
      for (const testId of testIds) {
        await expect(
          page.getByTestId(testId).first(),
          `${path}: the no-JS equivalent '${testId}' must resolve with JS off`,
        ).toBeVisible();
      }
      await page.context().close();
    });
  }
});

test.describe("T2: a stateful URL with JS off shows the named notice", () => {
  for (const path of T2_PAGES) {
    test(`${path}?v=1&focus=… shows the notice`, async ({ browser }) => {
      const page = await noJsPage(browser, `${path}?v=1&focus=fixture%3Aprobe`);
      const notice = page.getByTestId("no-js-state-notice");
      await expect(notice, `${path}: the stateful-URL notice must be present`).toBeVisible();
      // The notice says what the URL encodes and names the static equivalent.
      await expect(notice).toContainText("view state");
      await expect(notice.locator("a").first()).toBeVisible();
      await page.context().close();
    });

    test(`${path} (base URL) keeps the notice inert under JS`, async ({ page }) => {
      // With JS ON the <noscript> notice never renders.
      await page.goto(path);
      await expect(page.getByTestId("no-js-state-notice")).toHaveCount(0);
    });
  }
});
