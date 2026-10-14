// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// Runs in the "no-js" Playwright project (JavaScript DISABLED). The reviewed
// research dossier (P32.17, SIG-DOS-001/002) must be fully readable without
// JavaScript: all twelve answers with their six-state vocabulary, qualifiers,
// original + capture dates, capture citations, the same-scope conflict marker,
// search bases, follow-ups, the ledger, the checklist and the rubric — all in
// the static HTML.
import { test, expect } from "@playwright/test";
import { RESEARCH_INDEX, RESEARCH_PAGE, RESEARCH_JSON } from "./pages";

test("the research-dossier index lists the portfolio without JS (SIG-DOS-001)", async ({ page }) => {
  await page.goto(RESEARCH_INDEX);
  await expect(page.getByTestId("research-dossier-item")).toHaveCount(1);
  await expect(page.getByTestId("research-dossier-item").first()).toContainText("rubric");
});

test("all twelve answers render with a state, without JS (SIG-DOS-001)", async ({ page }) => {
  await page.goto(RESEARCH_PAGE);
  await expect(page.getByTestId("research-answer")).toHaveCount(12);
  // every one of the six states is exercised and visible
  for (const state of ["supported", "disputed", "derived", "unknown", "withheld", "not_applicable"]) {
    await expect(page.locator(`[data-state="${state}"]`).first()).toBeVisible();
  }
});

test("a same-scope conflict keeps both competing values visible, without JS (SIG-DOS-001)", async ({
  page,
}) => {
  await page.goto(RESEARCH_PAGE);
  const q3 = page.locator('[data-question="q3"]');
  await expect(q3.locator('[data-state="disputed"]')).toBeVisible();
  const rows = q3.getByTestId("answer-assertion");
  await expect(rows).toHaveCount(2);
  await expect(rows.first()).toContainText("190");
  await expect(rows.nth(1)).toContainText("299");
  await expect(q3).toContainText("≠"); // the conflict marker survives
  await expect(q3).toContainText("count_scope=city_limits"); // the qualifier survives
});

test("qualifiers, original dates, and capture citations are in the HTML (SIG-DOS-001)", async ({
  page,
}) => {
  await page.goto(RESEARCH_PAGE);
  const body = await page.content();
  // P34.22b / B4 G1 R4: the stand-in posture is rendered, never a fabricated
  // retrieval date — assertions cite the fixture's authoring commit instead.
  expect(body).toContain("stand-in"); // the capture-kind label
  expect(body).toContain("committed 2026-10-04"); // the fixture's real authoring day
  expect(body).not.toContain("retrieved 2026-"); // no fabricated capture date
  expect(body).toContain("valid 2026-07-01"); // the document's own date
  expect(body).toContain("cap-okc-usage-2026".slice(0, 16)); // the capture digest citation
});

test("an unknown answer carries its search basis + follow-up, without JS (SIG-DOS-002)", async ({
  page,
}) => {
  await page.goto(RESEARCH_PAGE);
  const q10 = page.locator('[data-question="q10"]');
  await expect(q10.getByTestId("answer-search-basis")).toContainText("searched_not_found");
  await expect(q10.getByTestId("answer-follow-up")).toContainText("closes when");
});

test("withheld and not-applicable answers show their declared basis, without JS", async ({
  page,
}) => {
  await page.goto(RESEARCH_PAGE);
  const q8 = page.locator('[data-question="q8"]');
  await expect(q8.getByTestId("answer-declared")).toContainText("withheld");
  const q4 = page.locator('[data-question="q4"]');
  await expect(q4.getByTestId("answer-declared")).toContainText("not applicable");
});

test("the ledger, checklist, and rubric render without JS (SIG-DOS-002)", async ({ page }) => {
  await page.goto(RESEARCH_PAGE);
  await expect(page.getByTestId("research-ledger")).toContainText("(withheld)");
  await expect(page.getByTestId("research-checklist")).toContainText("independent_semantic_review");
  await expect(page.getByTestId("rubric-score")).toHaveText("26/36");
  await expect(page.getByTestId("rubric-blocking")).toContainText("below 28");
});

test("the inventory overview marks itself as distinct from the research dossier", async ({
  page,
}) => {
  await page.goto("/dossier/oklahoma-city/");
  await expect(page.getByTestId("dossier-kind")).toContainText("Inventory overview");
});

test("the research dossier JSON endpoint emits the contract, without JS", async ({ page }) => {
  const resp = await page.goto(RESEARCH_JSON);
  expect(resp?.status()).toBe(200);
  const body = JSON.parse((await resp?.text()) ?? "{}");
  expect(body.schema).toBe("sig.research-dossier/1");
  expect(body.answers).toHaveLength(12);
  // P34.35: the wire record carries the disclosure fields
  expect(body.review_label).toBe("independent review not yet run");
  expect(body.licence.artifact).toBe("CC-BY-4.0");
  expect(body.permalink).toBe("https://surveillancegraph.org/research-dossier/okc-alpr/");
  expect(body.evidence_posture.has_non_live).toBe(true);
  expect(body.evidence_posture.stand_in_facts.length).toBeGreaterThan(0);
});

test("a non-live dossier discloses its evidence posture above the fold, without JS", async ({
  page,
}) => {
  // P34.35 (DR-C4-03): a page resting on stand-in/transcription bytes says so
  // before the answers — the disclosure precedes every answer section.
  await page.goto(RESEARCH_PAGE);
  const disclosure = page.getByTestId("non-live-disclosure");
  await expect(disclosure).toBeVisible();
  await expect(disclosure).toContainText("non-live evidence");
  await expect(disclosure).toContainText("stand-in");
  await expect(disclosure).toContainText("committed transcription");
  const firstAnswer = page.getByTestId("research-answer").first();
  const dBox = await disclosure.boundingBox();
  const aBox = await firstAnswer.boundingBox();
  expect(dBox!.y).toBeLessThan(aBox!.y); // above the fold, before every answer
});

test("every rendered assertion names how its bytes were obtained, without JS", async ({ page }) => {
  // P34.35 (DR-C4-03): the per-assertion acquisition label — live capture,
  // committed transcription or stand-in — never inferred from a URL.
  await page.goto(RESEARCH_PAGE);
  const labels = page.getByTestId("assertion-acquisition");
  const n = await labels.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    await expect(labels.nth(i)).toContainText(/live capture|committed transcription|stand-in/);
  }
  const body = await page.content();
  expect(body).toContain("committed transcription"); // the transcription-bound row
  expect(body).toContain("stand-in");
});

test("the review wording derives from the recorded status — never 'reviewed' on not_run", async ({
  page,
}) => {
  // P34.35 (F-153 / DR-C4-04): the fixture's review_status is not_run, so no
  // rendered string may read as if a human check ran.
  await page.goto(RESEARCH_PAGE);
  await expect(page.getByTestId("review-label")).toContainText("independent review not yet run");
  const body = await page.content();
  expect(body).not.toContain("Reviewed research dossier");
  expect(body).toContain("recorded status not_run");
});

test("licence, permalink and the as-of pair are carried on the page, without JS", async ({
  page,
}) => {
  // P34.35 (C4 NEW-22/NEW-23): every page carries its licence, a permalink and
  // a per-page as-of — the print footer carries the same triple on each page.
  await page.goto(RESEARCH_PAGE);
  const licence = page.getByTestId("dossier-licence");
  await expect(licence).toBeVisible();
  await expect(licence).toContainText("Licence CC-BY-4.0");
  await expect(licence).toContainText("as-of world 2026-10-04, belief 2026-10-04");
  const permalink = page.getByTestId("dossier-permalink");
  await expect(permalink).toHaveAttribute(
    "href",
    "https://surveillancegraph.org/research-dossier/okc-alpr/",
  );
});

test("the index labels each dossier's review state from its record, without JS", async ({
  page,
}) => {
  await page.goto(RESEARCH_INDEX);
  const item = page.getByTestId("research-dossier-item").first();
  await expect(item).toContainText("independent review not yet run");
  await expect(item).not.toContainText("reviewed packet");
});
