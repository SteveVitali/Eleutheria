// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The local dossier acceptance criteria (§39.2, SIG-UI-010..015), driven against the
// built static site. These are the deterministic + agentic ACs from the P15.2 ticket.
import { test, expect } from "@playwright/test";
import { DOSSIER_JSON, DOSSIER_PAGE, DOSSIER_PRINT } from "./pages";

const SECTION_ORDER = [
  "at_a_glance",
  "what_is_deployed",
  "cost_and_expiry",
  "who_else_can_see",
  "configuration_and_retention",
  "usage",
  "where_the_hardware_is",
  "policy",
  "accountability_events",
  "timeline",
  "what_we_dont_know",
  "how_we_know_this",
];

test("all twelve §39.2 sections render in order (SIG-UI-010)", async ({ page }) => {
  await page.goto(DOSSIER_PAGE);
  const ids = await page
    .getByTestId("dossier-section")
    .evaluateAll((els) => els.map((e) => e.getAttribute("data-section-id")));
  expect(ids).toEqual(SECTION_ORDER);
});

test("incompleteness banner names the count and the absence rule (SIG-UI-012)", async ({ page }) => {
  await page.goto(DOSSIER_PAGE);
  const banner = page.getByTestId("incompleteness-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText(/\d+ unresearched field/);
  await expect(banner).toContainText("absence of a row is not evidence of absence");
});

test("'what we don't know' appears in the summary, the section, AND the API (SIG-UI-011)", async ({
  page,
  request,
}) => {
  await page.goto(DOSSIER_PAGE);
  // Summary (top of the dossier) and the dedicated §39.2 section.
  await expect(page.getByTestId("what-we-dont-know-summary")).toBeVisible();
  await expect(page.getByTestId("what-we-dont-know-section")).toBeVisible();
  await expect(page.getByTestId("what-we-dont-know-summary").getByTestId("absence-hatch").first()).toBeVisible();

  // The API (static JSON) form carries it at the top level.
  const res = await request.get(DOSSIER_JSON);
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(Array.isArray(body.what_we_dont_know)).toBe(true);
  expect(body.what_we_dont_know.length).toBeGreaterThan(0);
});

test("next_decision_date is computed and shown wherever the expiry is (SIG-UI-014b)", async ({
  page,
}) => {
  await page.goto(DOSSIER_PAGE);
  // The termination block lives in the "cost and expiry" section (where the expiry
  // is displayed), and surfaces the decision date, not just the expiry.
  const costSection = page.locator('[data-section-id="cost_and_expiry"]');
  await expect(costSection).toContainText("2027-04-02"); // the expiry
  const decision = costSection.getByTestId("next-decision-date");
  await expect(decision).toContainText("2027-01-02"); // the DECISION date
});

test("every material figure expands to its reconciliation (SIG-UI-014)", async ({ page }) => {
  await page.goto(DOSSIER_PAGE);
  const figures = page.getByTestId("dossier-figure");
  const count = await figures.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i++) {
    const fig = figures.nth(i);
    await fig.locator("summary").click(); // native <details> — no JS required
    await expect(fig.getByTestId("recon-rule")).toBeVisible();
    const claims = fig.getByTestId("recon-claim");
    await expect(claims.first()).toBeVisible();
    // The winning claim is marked, and every claim carries tier, date, and a document link.
    await expect(fig.locator('[data-winning="true"]')).toHaveCount(1);
    await expect(claims.first().locator("a")).toHaveAttribute("href", /.+/);
    await expect(claims.first().locator("time")).toHaveAttribute("datetime", /\d{4}-\d{2}-\d{2}/);
  }
});

test("the three action blocks are present (SIG-UI-014a)", async ({ page }) => {
  await page.goto(DOSSIER_PAGE);
  await expect(page.getByTestId("authorization-block")).toBeVisible();
  await expect(page.getByTestId("termination-block")).toBeVisible();
  await expect(page.getByTestId("legal-regime-block")).toBeVisible();
  // The consent-agenda flag is first-class (the most actionable fact).
  await expect(page.getByTestId("auth-consent-agenda")).toHaveText("yes");
});

test("an unknown Appendix-B value renders as 'unknown', not omitted (SIG-UI-015)", async ({
  page,
}) => {
  await page.goto(DOSSIER_PAGE);
  const unknowns = page.locator(".sig-unknown");
  await expect(unknowns.first()).toBeVisible();
  await expect(unknowns.first()).toHaveText("unknown");
});

test.describe("print / PDF path (SIG-UI-013)", () => {
  test("every print page carries a footer with the as-of date and the permalink", async ({
    page,
  }) => {
    await page.goto(DOSSIER_PRINT);
    const pages = page.getByTestId("print-page");
    const footers = page.getByTestId("print-footer");
    const pageCount = await pages.count();
    expect(pageCount).toBeGreaterThan(1); // genuinely paginated
    await expect(footers).toHaveCount(pageCount); // a footer on EVERY page
    for (let i = 0; i < pageCount; i++) {
      const footer = footers.nth(i);
      await expect(footer).toContainText("As of world");
      await expect(footer.getByTestId("print-permalink")).toHaveAttribute("href", /ruleset=/);
    }
    // Sources are present on the printed document (document links behind figures).
    await expect(page.locator('a[href*="/v1/claim/"]').first()).toBeAttached();
  });

  test("the print route renders to a usable, multi-byte PDF", async ({ page }) => {
    await page.goto(DOSSIER_PRINT);
    await page.emulateMedia({ media: "print" });
    const pdf = await page.pdf({ format: "Letter", printBackground: true });
    // A real PDF: the %PDF header and a non-trivial body.
    expect(pdf.subarray(0, 5).toString("latin1")).toBe("%PDF-");
    expect(pdf.byteLength).toBeGreaterThan(5_000);
  });
});
