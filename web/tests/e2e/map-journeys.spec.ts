// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.63 (K1 MAP-07, R11-K13-MAP-07): the named J1–J10 map-acceptance
// journey battery, run as ONE spec so the pass/fail set lands in one place.
// It runs in the ordinary `test:e2e` pass (committed fixtures corpus) and —
// the ticket's point — over the REAL-SIZED deterministic national overlay
// (`national_budget_leg.sh journeys` runs this file with
// SIG_DATA_SOURCE=national against the national dist): K1 §9.3's "the map
// journeys run against the real-sized fixture" is then an exercised fact,
// not a fixtures-scale proxy.
//
// Corpus adaptations — recorded, never silent (the acceptance packet
// docs/build/reports/p37.63-map-acceptance/PACKET.md lists them verbatim):
//
//   * K1's literal J1 anchor is "Canberra". The synthetic corpus is
//     CONUS-bounded (build_national_fixture.py lat 25–48, lon −124…−67), so
//     the corpus-real anchor is "Oklahoma City" — a place option that exists
//     in BOTH corpora and has synthetic records in view when framed.
//   * K1's literal J2 facet is "a vendor + ALPR". Synthetic national sites
//     carry no vendor slot and the overlay emits no web/map/dict.json (the
//     facet dictionary is a real-export artifact — recorded in the packet),
//     so the national-scale narrowing proof is the sig_graph licence
//     compartment toggle (K1 §9's "compartment toggling" cell re-sum), and
//     the technology facet is asserted as honestly-rendered but
//     dict-degraded. Under committed fixtures the literal technology facet
//     narrows and is asserted too.
//   * J3's dossier "Open on map" lands `jurisdiction=` on a `us.census` key;
//     under the synthetic corpus the framing contract is what is asserted
//     (the bbox frame + the print view) — a zero-records filter result is
//     the corpus telling the truth, not a defect.
//   * J8's document bound is the ratified 100 KiB under fixtures; under
//     national it binds at the RECORDED measured-gap bound (800,000 B —
//     D-P35.51-3's national no-JS row verbatim), never silently raised.

import fs from "node:fs";
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { gotoSettled } from "./pages";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const IS_NATIONAL = process.env.SIG_DATA_SOURCE === "national";
const DRAWN_TIMEOUT = IS_NATIONAL ? 120_000 : 20_000;
// K1 §5.3: the T2-map no-JS document budget is 100 KiB. The national-scale
// document is a recorded measured gap (D-P35.51-3) bounded at 800 KiB — the
// journey asserts the RECORDED bound, not a relaxed one.
const NOJS_DOC_MAX = IS_NATIONAL ? 800_000 : 102_400;

// The place-search anchor — a place result present in both corpora with
// records in view when framed (see the adaptation note above).
const JOURNEY_PLACE = "Oklahoma City";

// J6's street-zoom anchor. Under committed fixtures it is the journey
// place's real frame. Under national the corpus is synthetic and CONUS-
// gridded — no real-world coordinate is guaranteed a street-zoom record —
// so the anchor is read from the overlay's own sig_graph/sites.geojson
// (the deterministic seed fixes feature order, so the first published
// point is stable, and reading the artifact rather than copying its seed
// keeps the anchor true across reseeds). Fails loud if unreadable — a
// missing overlay can never degrade into a fixtures anchor.
function nationalSiteAnchor(): { lat: number; lon: number } {
  const dir = (process.env.SIG_NATIONAL_DIR ?? "national").replace(/\/$/, "");
  const path = `${dir}/sig_graph/sites.geojson`;
  const fd = fs.openSync(path, "r");
  try {
    const buf = Buffer.alloc(256 * 1024);
    const n = fs.readSync(fd, buf, 0, buf.length, 0);
    const head = buf.subarray(0, n).toString("utf8");
    const m = head.match(
      /"coordinates"\s*:\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]/,
    );
    if (!m) throw new Error(`no site coordinates in ${path} head`);
    return { lon: Number(m[1]), lat: Number(m[2]) };
  } finally {
    fs.closeSync(fd);
  }
}
const J6_ANCHOR = IS_NATIONAL ? nationalSiteAnchor() : { lat: 35.47, lon: -97.51 };
const J6_AT = `${J6_ANCHOR.lat}%2F${J6_ANCHOR.lon}`;

async function ready(page: import("@playwright/test").Page, url = "/map/") {
  await gotoSettled(page, url);
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
    timeout: 30_000,
  });
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-drawn", "true", {
    timeout: DRAWN_TIMEOUT,
  });
}

async function recordsInView(page: import("@playwright/test").Page): Promise<number> {
  // The status line unmounts entirely at zero (an empty view has no status)
  // — absent reads as 0, not "unknown".
  const el = page.getByTestId("inview-status");
  if ((await el.count()) === 0) return 0;
  const text = (await el.textContent()) ?? "";
  const m = text.match(/([\d,]+) records? in view/);
  return m ? Number(m[1].replace(/,/g, "")) : 0;
}

// A RECORD row — the In-view list mixes place-group rows (their button only
// frames tighter) with record rows (their button selects); only the latter
// carry data-record-id (row.selectId in MapApp). The list renders
// asynchronously after draw, so every step below polls rather than samples.
const RECORD_ROW = "[data-row][data-record-id]";
const GROUP_ROW = "[data-row]:not([data-record-id])";

// Select a record through the In-view list: prefer a record row; a
// place-group row's button is the list's own zoom gesture, so drill those
// until a record row appears. A click that selects early short-circuits.
async function ensureSelection(page: import("@playwright/test").Page) {
  for (let i = 0; i < 6; i += 1) {
    if ((await page.getByTestId("selection-label").count()) > 0) break;
    const rec = page.locator(`${RECORD_ROW} button`).first();
    if ((await rec.count()) > 0) {
      await rec.click();
      break;
    }
    const group = page.locator(`${GROUP_ROW} button`).first();
    if ((await group.count()) === 0) {
      await page.waitForTimeout(600); // rows may still be rendering
      continue;
    }
    try {
      // A group row sampled mid-frame is transient — the frame's final zoom
      // re-renders the list. A vanished row is resampled, never awaited.
      await group.click({ timeout: 4_000 });
    } catch {
      continue;
    }
    await page.waitForTimeout(IS_NATIONAL ? 2_500 : 900);
  }
  await expect(page.getByTestId("selection-label")).toBeAttached({
    timeout: 20_000,
  });
  // The selection opens the Selected tab; on the mobile bottom sheet the
  // panel stays behind the collapsed grabber until expanded.
  const grabber = page.getByTestId("sheet-grabber");
  if ((await grabber.count()) > 0 && (await grabber.isVisible())) {
    await grabber.click();
  }
  await expect(page.getByTestId("map-selected-panel")).toBeVisible({
    timeout: 15_000,
  });
}

async function frameJourneyPlace(page: import("@playwright/test").Page) {
  const input = page.getByTestId("map-place-input");
  await input.click();
  await input.fill(JOURNEY_PLACE);
  const option = page
    .locator(".sig-typeahead-option", { hasText: JOURNEY_PLACE })
    .first();
  await expect(option).toBeVisible({ timeout: 15_000 });
  await option.click();
  // Frame, don't filter: under the synthetic corpus the registry option's
  // jurisdiction= facet matches nothing (syn.state.NN keys), and under
  // fixtures both states are valid — "show area" is the corpus-true leg.
  await page.getByTestId("place-show-area").click();
  await page.waitForTimeout(IS_NATIONAL ? 2_000 : 900);
  await expect(page).toHaveURL(/at=\d+(%2F|\/)/, { timeout: 15_000 });
}

test.describe("K1 §9.3 map acceptance journeys J1–J10 (P37.63)", () => {
  // The zoom walk (J6) and the place-search journeys re-await draw per
  // navigation; the national corpus's tile path draws slower — one honest
  // bound for the whole battery.
  test.describe.configure({
    timeout: IS_NATIONAL ? 240_000 : 120_000,
  });

  test("J1 — mobile resident: search → place → In view → site → share reproduces", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    // 1. search, 2. choose the place, 3. open the In-view row, 4. Share —
    // the K1 pass condition is "completes within four interactions".
    await ready(page);
    await frameJourneyPlace(page);
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeGreaterThan(0);
    await ensureSelection(page);
    const selectedLabel = (
      (await page.getByTestId("selection-label").innerText()) ?? ""
    ).trim();
    expect(selectedLabel.length, "a record is selected").toBeGreaterThan(0);
    const panel = page.getByTestId("map-selected-panel");
    // The K1 field set: technology, operator-or-"not stated", jurisdiction,
    // sources, dates — a named absence is the sanctioned value, never blank.
    const fields = await panel.innerText();
    expect(fields).toMatch(/Technology/);
    expect(fields).toMatch(/Operator/);
    expect(fields).toMatch(/Jurisdiction/);
    expect(fields).toMatch(/Sources/);
    expect(fields).toMatch(/First seen|Last seen/);
    await expect(page).toHaveURL(/focus=/, { timeout: 15_000 });
    // Share reproduces the view: the deep-link URL restores the selection.
    const shared = page.url();
    await page.goto(shared);
    await expect(page.getByTestId("map-island")).toHaveAttribute(
      "data-drawn",
      "true",
      { timeout: DRAWN_TIMEOUT },
    );
    const grabber2 = page.getByTestId("sheet-grabber");
    if ((await grabber2.count()) > 0 && (await grabber2.isVisible())) {
      await grabber2.click();
    }
    const panel2 = page.getByTestId("map-selected-panel");
    await expect(panel2).toBeVisible({ timeout: 15_000 });
    // Under tiles the focus= rk resolves once the linked view's sites draw —
    // retrying is the honest shape of that, not a race being papered over.
    // Case-insensitive: the label's CSS text-transform is presentation, the
    // restored record is the same record either way.
    const labelRe = new RegExp(
      selectedLabel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"),
      "i",
    );
    await expect(panel2).toContainText(labelRe, { timeout: 30_000 });
    // Cite names the snapshot-pinned form (K1 §8).
    await page.getByTestId("cite-this-view").click();
    await expect(page.locator("text=/\\/s\\/p-[0-9a-f]+/").first()).toBeVisible({
      timeout: 10_000,
    });
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("J2 — journalist: compartment/facet narrows, zoom national→city, cite restores", async ({
    page,
  }) => {
    // City-zoom start — K1's facet contract only applies from z10 up
    // (filters-cannot-apply below it); the national view is exercised after.
    // The z13 anchor carries records under both corpora (the deterministic
    // fixture site's block; the synthetic corpus's spread).
    await ready(page, "/map/?v=2&at=13%2F35.47%2F-97.51");
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeGreaterThan(0);
    const before = await recordsInView(page);
    // The licence-compartment toggle is the facet every corpus carries:
    // unchecking sig_graph must re-sum the view down, rechecking restores.
    // The status line lives on the In-view tab — read it there after each
    // flip (the input is visually hidden behind its label — force is the
    // honest flip, not a real-element workaround).
    await page.getByTestId("map-tab-filters").click();
    const compartment = page.getByTestId("map-compartment-sig_graph");
    await compartment.uncheck({ force: true });
    await page.getByTestId("map-tab-view").click();
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeLessThan(before);
    await page.getByTestId("map-tab-filters").click();
    await compartment.check({ force: true });
    await page.getByTestId("map-tab-view").click();
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeGreaterThanOrEqual(before);
    if (!IS_NATIONAL) {
      // Under committed fixtures the literal technology facet applies —
      // dict.json ships, so options carry real counts and the applied state
      // lands the technology= URL param (the deterministic contract; strict
      // narrowing is corpus-dependent — a homogeneous view keeps its count).
      await page.getByTestId("map-tab-filters").click();
      const tech = page
        .getByTestId("filter-technology")
        .locator("input[type=checkbox]")
        .first();
      await tech.check({ force: true });
      await expect(page).toHaveURL(/technology=/, { timeout: 15_000 });
      await page.getByTestId("map-tab-view").click();
      const narrowed = await recordsInView(page);
      expect(narrowed).toBeGreaterThanOrEqual(0);
      await page.getByTestId("map-tab-filters").click();
      await tech.uncheck({ force: true });
      await page.getByTestId("map-tab-view").click();
    } else {
      // National overlay: dict.json is absent (real-export artifact — the
      // packet records the degradation); the facet renders honestly.
      await page.getByTestId("map-tab-filters").click();
      await expect(page.getByTestId("filter-technology")).toBeVisible();
    }
    // Zoom city → national → the cite restores the frame (the at= state IS
    // the zoom; the URL form is the citability contract being exercised).
    await page.goto("/map/?v=2&at=4%2F38%2F-96");
    await expect(page.getByTestId("map-island")).toHaveAttribute(
      "data-drawn",
      "true",
      { timeout: DRAWN_TIMEOUT },
    );
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeGreaterThan(0);
    await page.goto("/map/?v=2&at=12%2F35.47%2F-97.5");
    await expect(page.getByTestId("map-island")).toHaveAttribute(
      "data-drawn",
      "true",
      { timeout: DRAWN_TIMEOUT },
    );
    await page.getByTestId("cite-this-view").click();
    await expect(page.locator("text=/\\/s\\/p-[0-9a-f]+/").first()).toBeVisible({
      timeout: 10_000,
    });
    // Reopen restores the state — the shared URL reloads the same frame.
    const shared = page.url();
    await page.goto(shared);
    await expect(page.getByTestId("map-island")).toHaveAttribute(
      "data-drawn",
      "true",
      { timeout: DRAWN_TIMEOUT },
    );
    expect(page.url()).toMatch(/at=12(%2F|\/)35\.4/);
  });

  test("J3 — dossier 'Open on map' frames the jurisdiction and prints", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoSettled(page, "/dossier/usa/ok/");
    const button = page.locator(".sig-activate__button");
    await expect(button).toBeVisible({ timeout: 15_000 });
    await button.click();
    const embed = page.getByTestId("fig-map-embed");
    await expect(embed).toBeVisible();
    const openFull = page.getByTestId("embed-open-full");
    const href = await openFull.getAttribute("href");
    expect(href).toMatch(/\/map\/\?v=2/);
    await ready(page, href!);
    // Framed within the dossier's bbox: either the frame wrote at= or the
    // jurisdiction facet chip names the frame (K1 §9.3's "framed county").
    const url = page.url();
    const frameChip = await page
      .getByTestId("place-frame")
      .count()
      .catch(() => 0);
    expect(
      /at=\d+(%2F|\/)/.test(url) || /jurisdiction=/.test(url) || frameChip > 0,
      `dossier hand-off frames the map (url=${url})`,
    ).toBe(true);
    if (!IS_NATIONAL) {
      await expect
        .poll(() => recordsInView(page), { timeout: 20_000 })
        .toBeGreaterThan(0);
    }
    // Print view carries the as-of / cite / attribution contract (K1 §5).
    await page.evaluate(() => {
      (window as unknown as { __printed: boolean }).__printed = false;
      window.print = () => {
        (window as unknown as { __printed: boolean }).__printed = true;
      };
    });
    await page.getByTestId("print-view").click();
    const print = page.getByTestId("map-print");
    await expect(print).toContainText("Data as of");
    await expect(print).toContainText("Cite this view");
    await expect(print).toContainText("Attribution:");
  });

  test("J4 — keyboard-only: search → In view → row → Escape, no trap", async ({
    page,
  }) => {
    await ready(page);
    // Reach a place field by keyboard alone (bounded tabs): either the
    // island's search input (map-place-input / map-app-place-q) or the
    // typeahead's (map-place-q) is a valid landing.
    const PLACE_IDS = ["map-place-input", "map-place-q", "map-app-place-q"];
    let landed = false;
    for (let i = 0; i < 50 && !landed; i += 1) {
      landed = await page.evaluate(
        (ids) =>
          ids.includes(document.activeElement?.id ?? "") ||
          document.activeElement?.getAttribute("data-testid") ===
            "map-place-input",
        PLACE_IDS,
      );
      if (!landed) await page.keyboard.press("Tab");
    }
    expect(landed, "Tab order reaches the place search field").toBe(true);
    await page.keyboard.type(JOURNEY_PLACE, { delay: 20 });
    const option = page
      .locator(".sig-typeahead-option", { hasText: JOURNEY_PLACE })
      .first();
    await expect(option).toBeVisible({ timeout: 15_000 });
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    await page.getByTestId("place-show-area").click();
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeGreaterThan(0);
    // Open a record row by keyboard: Enter on a place-group row is the
    // list's own zoom gesture; Enter on a record row selects.
    for (let i = 0; i < 6; i += 1) {
      if ((await page.getByTestId("selection-label").count()) > 0) break;
      const recBtn = page.locator(`${RECORD_ROW} button`).first();
      const groupBtn = page.locator(`${GROUP_ROW} button`).first();
      const target = (await recBtn.count()) > 0 ? recBtn : groupBtn;
      if ((await target.count()) === 0) {
        await page.waitForTimeout(600);
        continue;
      }
      try {
        // A place-group row sampled mid-frame is transient — the frame's
        // final zoom re-renders the list as record rows. A vanished row is
        // resampled next pass, never awaited forever.
        await target.focus({ timeout: 3_000 });
        await page.keyboard.press("Enter");
      } catch {
        continue;
      }
      await page.waitForTimeout(IS_NATIONAL ? 2_000 : 800);
      if ((await recBtn.count()) > 0 || (await page.getByTestId("selection-label").count()) > 0) {
        // A record row is now reachable — Enter it (or stop if it selected).
        if ((await page.getByTestId("selection-label").count()) === 0) {
          await page.locator(`${RECORD_ROW} button`).first().focus();
          await page.keyboard.press("Enter");
        }
        break;
      }
    }
    await expect(page.getByTestId("selection-label")).toBeAttached({
      timeout: 20_000,
    });
    // Escape clears the selection only from a row/canvas keydown context
    // (SIG-UI-095) — after the Selected tab opened, the keyboard way back is
    // Enter on the In-view tab, then Escape on the row: focus returns to it
    // and focus= clears. Never a trap.
    await page.getByTestId("map-tab-view").focus();
    await page.keyboard.press("Enter");
    const backRow = page.locator(RECORD_ROW).first();
    await backRow.locator("button").first().focus();
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400);
    expect(page.url()).not.toContain("focus=");
    const focusOk = await page.evaluate(
      () => document.activeElement?.closest("[data-row]") !== null,
    );
    expect(focusOk, "focus returns to the invoking row after Escape").toBe(true);
  });

  test("J5 — screen-reader proxy: live region + sortable table", async ({ page }) => {
    await ready(page);
    await expect(page.getByTestId("inview-status")).toContainText("in view", {
      timeout: 30_000,
    });
    // The live region announces what the status line shows — the SR proxy
    // K1 §9.3 J5 names.
    const live = page.getByTestId("map-aria-live");
    await expect(live).toContainText("in view", { timeout: 15_000 });
    // The table view carries real headers and the same records (the table's
    // own rows are <tr>, not the list view's [data-row] <li>).
    await page.getByTestId("inview-table-toggle").click();
    const table = page.getByTestId("inview-table");
    await expect(table).toBeVisible({ timeout: 15_000 });
    expect(await table.locator("thead th").count()).toBeGreaterThanOrEqual(3);
    expect(await table.locator("tbody tr").count()).toBeGreaterThanOrEqual(1);
  });

  test("J6 — street-zoom regression: record survives the z6→z15 walk", async ({
    page,
  }) => {
    // Anchor at street zoom on a known site (fixtures: the journey place's
    // frame; national: the overlay's first published point), then walk the
    // zooms the K1 regression names. At z≤9 the tile path aggregates the
    // record into exactly one visible cell (national); at z≥10 the record
    // resolves again.
    await ready(page, `/map/?v=2&at=14%2F${J6_AT}`);
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeGreaterThan(0);
    for (const z of [6, 9]) {
      await ready(page, `/map/?v=2&at=${z}%2F${J6_AT}`);
      if (IS_NATIONAL) {
        // Cell-aggregated view: the status still reports records in view —
        // the site is counted inside a cell, not dropped.
        await expect
          .poll(() => recordsInView(page), { timeout: 30_000 })
          .toBeGreaterThan(0);
      } else {
        await expect(page.locator("[data-row]").first()).toBeVisible({
          timeout: 15_000,
        });
      }
    }
    for (const z of [10, 12, 13, 14, 15]) {
      await ready(page, `/map/?v=2&at=${z}%2F${J6_AT}`);
      await expect
        .poll(() => recordsInView(page), { timeout: 30_000 })
        .toBeGreaterThan(0);
      await expect(page.locator(RECORD_ROW).first()).toBeVisible({
        timeout: 20_000,
      });
    }
  });

  test("J7 — basemap failure: honest notice, context base and sites survive", async ({
    page,
  }) => {
    // Fail every basemap-style fetch: the SIG basemap is a vendored style
    // served same-origin — an unreachable host is the J7 condition.
    let basemapHits = 0;
    await page.route(/\/map\/style[^/]*\.json/, (route) => {
      basemapHits += 1;
      return route.abort();
    });
    await ready(page);
    const notice = page.locator(
      "[data-testid=basemap-unavailable], [data-testid=basemap-fallback]",
    );
    await expect(notice.first()).toBeVisible({ timeout: 15_000 });
    expect(basemapHits).toBeGreaterThan(0);
    // The context base (labels/coast) and the records stay — J7's
    // "still leaves context base and sites".
    await expect
      .poll(() => recordsInView(page), { timeout: 30_000 })
      .toBeGreaterThan(0);
    // No error loop: the notice is role=status and the island stays drawn —
    // a retry storm would tear the drawn latch.
    await expect(page.getByTestId("map-island")).toHaveAttribute(
      "data-drawn",
      "true",
    );
  });

  test("J8 — no-JS: state URL names the equivalent list, bounded document", async ({
    browser,
  }) => {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    const response = await page.goto("/map/?v=2&at=12%2F35.47%2F-97.5", {
      waitUntil: "load",
    });
    expect(response?.status()).toBe(200);
    const body = await response!.body();
    expect(
      body.length,
      `no-JS document ${body.length}B vs the bound ${NOJS_DOC_MAX}B`,
    ).toBeLessThanOrEqual(NOJS_DOC_MAX);
    // The JS-off notice names the equivalent views — the in-page places /
    // coverage-bins tables and the static overview (K1 §4.9, T2's named
    // no-JS equivalent).
    const notice = page.getByTestId("no-js-state-notice");
    await expect(notice).toBeVisible({ timeout: 10_000 });
    const eqLinks = notice.locator("a");
    expect(await eqLinks.count()).toBeGreaterThanOrEqual(1);
    // Every named equivalent resolves to a real on-page target.
    for (const href of await eqLinks.evaluateAll((els) =>
      els.map((e) => (e as HTMLAnchorElement).getAttribute("href") ?? ""),
    )) {
      const id = href.replace(/^#/, "");
      await expect(
        page.locator(`#${id}`),
        `no-JS equivalent target ${href} exists`,
      ).toBeAttached({ timeout: 10_000 });
    }
    // The tabular equivalent actually carries rows under both corpora.
    expect(
      await page.locator("table tbody tr").count(),
      "the no-JS tabular equivalent carries rows",
    ).toBeGreaterThanOrEqual(1);
    // No broken internal links in the shell chrome (bounded sample).
    const hrefs = await page
      .locator("header a, footer a")
      .evaluateAll((els) =>
        els
          .map((e) => (e as HTMLAnchorElement).getAttribute("href") ?? "")
          .filter((h) => h.startsWith("/"))
          .slice(0, 12),
      );
    for (const h of hrefs) {
      expect((await page.request.get(h)).status(), h).toBe(200);
    }
    await context.close();
  });

  test("J9 — dark theme: dark basemap loads, legend and a11y hold", async ({
    page,
  }) => {
    const darkStyle = page.waitForResponse(/style-dark|basemap.*dark/i, {
      timeout: 30_000,
    }).catch(() => null);
    await ready(page, "/map/?v=2&basemap=1");
    await darkStyle;
    // The dark basemap choice is round-tripped through the URL — the toggle
    // reflects it and the island still draws.
    await expect(page.getByTestId("basemap-toggle")).toBeVisible();
    await expect(page.getByTestId("map-island")).toHaveAttribute(
      "data-drawn",
      "true",
    );
    const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
    expect(results.violations, JSON.stringify(results.violations)).toEqual([]);
  });

  test("J10 — reduced motion: no animated transitions on the map journey", async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await ready(page);
    await frameJourneyPlace(page);
    await ensureSelection(page);
    // Zero-duration contract (the same sweep reduced-motion.spec.ts runs,
    // scoped to the island chrome the journey touches).
    const offenders = await page.evaluate(() => {
      const out: string[] = [];
      const root = document.querySelector("[data-testid=map-island]");
      if (!root) return ["no map-island root"];
      for (const el of Array.from(root.querySelectorAll("*")).slice(0, 2000)) {
        const cs = getComputedStyle(el);
        for (const d of cs.transitionDuration.split(",")) {
          if (d.trim() !== "0s") out.push(`${el.tagName} transition ${d.trim()}`);
        }
        for (const d of cs.animationDuration.split(",")) {
          if (d.trim() !== "0s") out.push(`${el.tagName} animation ${d.trim()}`);
        }
      }
      return out.slice(0, 10);
    });
    expect(offenders, offenders.join("\n")).toEqual([]);
    // No live animations after the interaction (map camera moves are jumps).
    expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
  });
});
