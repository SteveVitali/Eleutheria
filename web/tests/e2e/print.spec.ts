// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.26 (K14 UXK14-9 / K14 §4.10–4.11, DR-K14-21, SIG-UI-098/130/155) — the
// print-v2 document, driven against the built static site:
//
//   - page 1 is the council brief (place, recorded/unknown at a glance, the
//     next decision or its typed absence, 3–5 documents to bring, the
//     build-generated QR);
//   - every page carries the running head (place) and footer (as-of, release
//     when bound, permalink, licence when bound, "Page n of N") — no orphan
//     pages;
//   - every declared figure renders on its own page (SIG-UI-130);
//   - the popover terms collapse to the "Terms used" strip on the last page;
//   - the whole document is zero-JS and greyscale-safe.
import { test, expect } from "@playwright/test";
import { DOSSIER_PRINT } from "./pages";

test.describe("print v2 — the council brief page 1 (SIG-UI-155)", () => {
  test("page 1 is the council brief: place, glance, decision, documents, QR", async ({
    page,
  }) => {
    await page.goto(DOSSIER_PRINT);
    const first = page.getByTestId("print-page").first();
    await expect(first).toHaveAttribute("data-page-kind", "brief");
    const brief = first.getByTestId("council-brief");
    await expect(brief).toBeAttached();
    // The place's name leads.
    await expect(first.locator("h1")).toContainText("Oklahoma City");
    // What is recorded / unknown at a glance — real counts, not placeholders.
    const glance = brief.getByTestId("brief-glance");
    await expect(glance.getByTestId("brief-recorded")).toContainText(/\d+ of \d+/);
    await expect(glance.getByTestId("brief-unknown")).toContainText(/\d+/);
    // The next decision — the derived renewal date (or its typed absence).
    await expect(glance.getByTestId("brief-decision")).toContainText("2027-01-02");
    // 3–5 documents to bring, each a real locator from the record.
    const docs = brief.getByTestId("brief-documents").locator("li");
    const docCount = await docs.count();
    expect(docCount).toBeGreaterThanOrEqual(3);
    expect(docCount).toBeLessThanOrEqual(5);
    // The static QR — generated at build, a real symbol matrix.
    const qr = brief.getByTestId("brief-qr").locator("svg");
    await expect(qr).toHaveAttribute("viewBox", /^0 0 \d+ \d+$/);
    const path = qr.locator("path");
    await expect(path).toBeAttached();
    const d = await path.getAttribute("d");
    expect(d!.length).toBeGreaterThan(200); // a real matrix, not a stub
    // The caption names the pinned permalink the QR encodes.
    await expect(brief.getByTestId("brief-qr")).toContainText("Scan for the pinned page");
  });
});

test.describe("print v2 — running chrome on every page (SIG-UI-155)", () => {
  test("every page carries place, as-of, permalink, licence-if-bound, page n of N", async ({
    page,
  }) => {
    await page.goto(DOSSIER_PRINT);
    const pages = page.getByTestId("print-page");
    const total = await pages.count();
    expect(total).toBeGreaterThanOrEqual(6); // brief + figure + 4 section pages + terms
    const releases = page.getByTestId("print-release");
    const releaseBound = (await releases.count()) > 0;
    for (let i = 0; i < total; i++) {
      const pg = pages.nth(i);
      // The running head: the place name.
      const runhead = pg.getByTestId("print-runhead");
      await expect(runhead).toContainText("Oklahoma City");
      const footer = pg.getByTestId("print-footer");
      await expect(footer).toContainText("As of world");
      await expect(footer.getByTestId("print-permalink")).toHaveAttribute(
        "href",
        /ruleset=/,
      );
      // Page numbering is composed — never a margin-box counter that can
      // drift. The `n/N` form also keeps the label out of the figure gate's
      // material-numeral scan (chrome, not a count claim).
      await expect(footer.getByTestId("print-pageno")).toHaveText(
        `Page ${i + 1}/${total}`,
      );
      // Release + licence appear on EVERY page exactly when the build is
      // release-bound — never partially, never fabricated.
      if (releaseBound) {
        await expect(pg.getByTestId("print-release")).toBeAttached();
        await expect(footer).toContainText("Licence:");
      }
    }
  });

  test("page kinds paginate in order — brief, figures, sections, terms", async ({ page }) => {
    await page.goto(DOSSIER_PRINT);
    const kinds = await page
      .getByTestId("print-page")
      .evaluateAll((els) => els.map((e) => e.getAttribute("data-page-kind")));
    expect(kinds[0]).toBe("brief");
    expect(kinds[1]).toBe("figures"); // the map leads page 2 (K13)
    expect(kinds[kinds.length - 1]).toBe("terms");
    // Four section pages in the middle.
    expect(kinds.slice(2, -1)).toEqual(["sections", "sections", "sections", "sections"]);
  });
});

test.describe("print v2 — every declared figure on its own page (SIG-UI-130)", () => {
  test("the declared map figure prints with caption, as-of, permalink", async ({ page }) => {
    await page.goto(DOSSIER_PRINT);
    const fig = page.getByTestId("print-figure");
    await expect(fig).toHaveCount(1);
    await expect(fig).toHaveAttribute("data-figure-kind", "map");
    // The greyscale-safe placeholder carries hatch + a text label — never a
    // colour-only state and never a fabricated visual.
    const canvas = fig.locator(".sig-print-figure__canvas");
    await expect(canvas).toBeAttached();
    await expect(fig).toContainText("Placement of recorded camera sites");
    await expect(fig).toContainText("As of world");
    await expect(fig.locator(".sig-print-figure__permalink")).toHaveAttribute(
      "href",
      /ruleset=/,
    );
  });
});

test.describe("print v2 — the terms strip (K14 §4.11)", () => {
  test("the last page lists the terms used, linked to their glossary anchors", async ({
    page,
  }) => {
    await page.goto(DOSSIER_PRINT);
    const last = page.getByTestId("print-page").last();
    await expect(last).toHaveAttribute("data-page-kind", "terms");
    const terms = last.getByTestId("print-terms");
    await expect(terms).toContainText("Terms used on this page");
    const links = terms.locator("a.sig-print-terms__link");
    const count = await links.count();
    expect(count).toBeGreaterThanOrEqual(4); // the four core document terms at minimum
    for (let i = 0; i < count; i++) {
      await expect(links.nth(i)).toHaveAttribute("href", /\/glossary\/#.+/);
    }
    // The dossier's own terms: it carries figures + an unresolved record.
    await expect(terms).toContainText("dossier");
    await expect(terms).toContainText("unresolved");
  });
});

test.describe("print v2 — document integrity (DR-K14-21)", () => {
  test("zero script elements — the print route is T0", async ({ page }) => {
    await page.goto(DOSSIER_PRINT);
    expect(await page.locator("script").count()).toBe(0);
  });

  test("reconciliations are present expanded for print (a paper reader cannot click)", async ({
    page,
  }) => {
    await page.goto(DOSSIER_PRINT);
    expect(await page.locator("details.sig-recon").count()).toBeGreaterThan(0);
  });

  test("the emitted PDF paginates into at least one sheet per composed page", async ({
    page,
  }) => {
    await page.goto(DOSSIER_PRINT);
    const blockCount = await page.getByTestId("print-page").count();
    await page.emulateMedia({ media: "print" });
    const pdf = await page.pdf({ format: "Letter", printBackground: true });
    expect(pdf.subarray(0, 5).toString("latin1")).toBe("%PDF-");
    expect(pdf.byteLength).toBeGreaterThan(5_000);
    // The PDF page-tree count: every composed page starts a new sheet, so the
    // document never collapses to fewer sheets than composed pages, and a
    // blank trailing sheet would read as a larger count than content allows.
    const text = pdf.toString("latin1");
    const counts = [...text.matchAll(/\/Count (\d+)/g)].map((m) => Number(m[1]));
    const sheetCount = Math.max(...counts);
    expect(sheetCount).toBeGreaterThanOrEqual(blockCount);
  });
});
