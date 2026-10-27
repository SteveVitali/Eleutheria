// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.17 — the generated /glossary/ page and the <Term>/<InBrief> consumers
// (SIG-UI-061/133/143, K14 §2.5). T1: complete server HTML, no runtime JS.
import { test, expect } from "@playwright/test";

test.describe("the generated glossary (K14 §2.5)", () => {
  test("is classified T1 in the emitted page-types manifest", async ({ page }) => {
    await page.goto("/glossary/");
    const manifest = await page.evaluate(async () => {
      const res = await fetch("/page-types.json");
      return res.json();
    });
    const entry = manifest.routes?.find?.(
      (r: { path: string; type?: string }) => r.path === "/glossary/"
    );
    expect(entry).toBeTruthy();
    expect(entry.type).toBe("T1");
  });

  test("carries Appendix E terms verbatim plus the site terms", async ({ page }) => {
    await page.goto("/glossary/");
    const entries = page.getByTestId("glossary-entry");
    // ~30 Appendix E rows + the site/state terms — a small count means the
    // merge silently dropped a source (SIG-ENG-042).
    expect(await entries.count()).toBeGreaterThan(40);
    // spec-sourced entries are flagged and carry the spec's words verbatim —
    // either pure `spec` rows or `merged` rows that folded Appendix E wording
    // into a lexicon/site term.
    expect(
      await page
        .locator(
          "[data-testid='glossary-entry'][data-glossary-source='spec'], " +
            "[data-testid='glossary-entry'][data-glossary-source='merged']",
        )
        .count(),
    ).toBeGreaterThanOrEqual(16);
    // The Dossier entry carries the Appendix E definition verbatim.
    const dossier = page.locator("#dossier");
    await expect(dossier).toBeVisible();
    await expect(page.locator("#dossier + dd")).toContainText("per-jurisdiction");
    // A site term resolves too.
    await expect(page.locator("#possible-duplicate")).toBeVisible();
    await expect(page.locator("#possible-duplicate + dd")).toContainText("not merged");
  });

  test("renders the lexicon states and the one-meaning legend", async ({ page }) => {
    await page.goto("/glossary/");
    const states = page.getByTestId("glossary-states");
    expect(await states.count()).toBeGreaterThanOrEqual(8);
    // The K14 short labels — the same words AbsenceHatch renders.
    await expect(page.locator("main")).toContainText("None found");
    await expect(page.locator("main")).toContainText("Stated absent");
    await expect(page.locator("main")).toContainText("possible duplicate");
    // The interim corroboration line travels verbatim (SIG-UI-064).
    await expect(page.locator("main")).toContainText(
      "2+ source records; republications not yet collapsed",
    );
    // Candidate vs Provisional stays distinct (SIG-UI-062).
    const legend = page.getByTestId("glossary-legend");
    await expect(legend).toContainText("Candidate");
    await expect(legend).toContainText("Provisional");
  });

  test("spec references live inside disclosures, never in prose (DR-K14-07)", async ({ page }) => {
    await page.goto("/glossary/");
    const refs = page.getByTestId("spec-refs");
    expect(await refs.count()).toBeGreaterThan(20);
    await expect(refs.first().locator("summary")).toHaveText("Spec references");
  });

  test("ships no script and opens the In brief orientation", async ({ page }) => {
    await page.goto("/glossary/");
    expect(await page.locator("main script").count()).toBe(0);
    await expect(page.getByTestId("in-brief")).toBeVisible();
    await expect(page.getByTestId("in-brief")).toContainText("one vocabulary");
  });
});

test.describe("<Term> on a content page (K14 §2.5)", () => {
  test("renders the glossary link, the popover button and the popover", async ({ page }) => {
    await page.goto("/methodology/");
    const term = page.locator(".sig-term[data-term='claim']");
    await expect(term).toBeVisible();
    const link = term.locator(".sig-term__link");
    await expect(link).toHaveAttribute("href", "/glossary/#claim");
    const button = term.locator("button.sig-term__def");
    await expect(button).toHaveAttribute("popovertarget", "td-claim");
    await expect(button).toHaveAttribute("aria-label", "Definition of claim");
    const popover = page.locator("span#td-claim[popover]");
    await expect(popover).toHaveCount(1);
    await expect(popover).toHaveText(/substance of the graph/);
  });

  test("the term link lands on the glossary anchor", async ({ page }) => {
    await page.goto("/glossary/#claim");
    const target = page.locator("#claim");
    await expect(target).toBeVisible();
    await expect(page.locator("main")).toContainText("An assertion with a subject");
  });

  test("the methodology In brief box links the precise section", async ({ page }) => {
    await page.goto("/methodology/");
    const box = page.getByTestId("in-brief");
    await expect(box).toBeVisible();
    const body = await box.locator(".sig-inbrief__body").textContent();
    expect(body!.trim().split(/\s+/).length).toBeLessThanOrEqual(80);
    await expect(box.locator("a")).toHaveAttribute("href", "#evidence-tiers");
  });
});
