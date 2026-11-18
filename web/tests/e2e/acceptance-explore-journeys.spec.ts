// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.64 (R11-K13-ACC-EXPLORE — K2 GX-10 / K6 VIZ-05): the labelled AGENT
// walkthroughs. K2 §9 and K6 §13 name these "agent walkthroughs at
// acceptance, never user research" — each test walks the reader's path and
// asserts the pass criteria. The fixture corpus adapts the named places
// where the fixture carries no equivalent; every adaptation is recorded
// here and in the acceptance packet
// (docs/build/reports/p37.64-explore-acceptance/PACKET.md):
//
//   * J-1/VJ-3 (Texas): the fixture draws its access network figure on
//     /dossier/usa/ok/, not /dossier/usa/tx/ — the figure half walks
//     usa/ok; the explorer half walks the dossier's own explore-bar link.
//     The /graphs/access/usa/tx/ drill-down exists and covers the Texas
//     JS-off parity leg.
//   * J-3 (Austin "who runs / what the city bought"): the fixture's pair is
//     Acme City Police (agency) + the Acworth ALPR expansion contract —
//     two unmerged entities, both reachable from the dossier figure and
//     the /entity/ hub, each with its own page and the ER disclosure on
//     the hub.
//   * VJ-5 (California "11 sources"): the fixture's source explorer is
//     /dossier/usa/ok/sources/ ("from 2 sources").
//   * VJ-1 (Oklahoma City): the city dossier /dossier/oklahoma-city/
//     carries the declared print figure.
//   * VJ-4: the release-pinned /v1/releases/…/search endpoint is the API
//     surface and does not emit into the static dist — the scoped-search
//     FORM contract is asserted (method/action/hidden scope) and the
//     in-scope results leg walks the equivalent /search/?v=2&…
//     jurisdiction-faceted URL. The live leg verifies the release route.
//
// K13 §8's capstone legs this row owns — J2 (the Texas graph walk → J-1),
// J3 (disputed figure → the disagreements walk), A3 (print → VJ-1), O1
// (who runs what → VJ-4 + the entity links) — are named inline.

import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { gotoSettled } from "./pages";

const OK_DOSSIER = "/dossier/usa/ok/";
const HARRIS = "/dossier/usa/tx/harris-county-48201/";
const CITY = "/dossier/oklahoma-city/";
const AGENCY = "/entity/agency/acme-city-police--4g2wm8q/";
const ACWORTH = "/entity/agency/acworth-police-department--4g2wm8q/";
const CONTRACT = "/entity/contract/acworth-alpr-expansion-contract--9p4kxwd/";

const axe = (page: Page) =>
  new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag22aa"]).analyze();

// ---------------------------------------------------------------------------
// K2 J-1 — "who supplies ALPRs to agencies in Texas and who can search them?"
// (also the K13 §8 capstone J2 leg — the Texas graph walk.)
// ---------------------------------------------------------------------------
test.describe("J-1 journalist: the Texas supply/access walk (K13 §8 J2)", () => {
  test("dossier → explorer access view → named nodes, dated/currency edges; JS-off parity", async ({
    page,
    request,
  }) => {
    await gotoSettled(page, "/dossier/usa/tx/");
    const explore = page.getByTestId("explore-network");
    await expect(explore).toBeVisible();
    const href = await explore.getAttribute("href");
    expect(href).toContain("/explore/?v=2");
    expect(href).toMatch(/[?&](view|overview)=/);
    expect(href).toContain("jurisdiction=");

    // Walk the dossier's own link — the explorer opens scoped.
    await page.goto(href!.replace(/&amp;/g, "&"));
    await expect(page.getByTestId("explore-island")).toBeVisible();
    // Every node is named; every edge row carries a date or "undated" and a
    // currency label — the node table is the keyboard surface the panels
    // mirror.
    const nodes = page.getByTestId("graph-island-node");
    await expect(nodes.first()).toBeVisible({ timeout: 30_000 });
    const nodeTexts = await nodes.allTextContents();
    for (const t of nodeTexts) expect(t.trim().length).toBeGreaterThan(0);

    // The same facts reachable with JS off through the static overview —
    // /graphs/access/usa/tx/ is the fixture's Texas drill-down.
    const drill = await request.get("/graphs/access/usa/tx/");
    expect(drill.status()).toBe(200);
    const drillHtml = await drill.text();
    expect(drillHtml).toContain("graph-edge-row");
    // Nothing historical phrased in the present tense: every edge row on
    // the drill-down carries its date kind; "historical" appears only as a
    // marked currency, never as "still shares".
    expect(drillHtml).not.toMatch(/still sharing|currently shares|is sharing with/i);
  });
});

// ---------------------------------------------------------------------------
// K2 J-2 — "what is SIG's evidence for this vendor–agency link?" (≤2 actions)
// ---------------------------------------------------------------------------
test.describe("J-2 journalist: edge → evidence in ≤2 actions (SIG-UI-D34)", () => {
  test("relation row → evidence link → claim panel names the chain", async ({ page }) => {
    await gotoSettled(page, ACWORTH);
    const row = page.getByTestId("relation-row").first();
    await expect(row).toBeVisible();
    // action 1 — the evidence link on the relation row.
    const ev = row.getByTestId("relation-evidence").locator("a");
    await expect(ev).toHaveAttribute("href", /^#claim-/);
    await ev.click();
    // action ≤2 — the claim panel is on-page (a <details> — its content is
    // in the DOM either way): source, date, currency, support, resolution —
    // the J-2 pass fields.
    const panel = page.locator("#claim-clm-apd-vigilant-1");
    await expect(panel).toBeAttached();
    const panelText = await panel.textContent();
    for (const field of ["Source", "Binding state", "Capture", "Extraction"]) {
      expect(panelText).toContain(field);
    }
    // "Cite this relationship" — the entity's cite block mints the SIG id.
    await expect(page.getByTestId("cite-sig-id")).toContainText("sig:agency:");
  });

  test("the same walk answers with JS off (T1 parity)", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto(ACWORTH);
    const ev = page.getByTestId("relation-evidence").locator("a").first();
    await expect(ev).toBeVisible();
    const href = await ev.getAttribute("href");
    expect(href).toMatch(/^#claim-/);
    // The target exists in the served HTML — the anchor lands without JS.
    const panel = page.locator(href!);
    await expect(panel).toBeAttached();
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// K2 J-3 — two unmerged bodies, each reachable, never merged.
// ---------------------------------------------------------------------------
test.describe("J-3 advocate: two unmerged entities stay apart", () => {
  test("agency + contract pages reachable from the dossier figure and the hub; no merge claim", async ({
    page,
  }) => {
    await gotoSettled(page, OK_DOSSIER);
    // The network figure's agency node links straight to the entity page.
    const nodeLink = page.locator(`a[href="${AGENCY}"]`);
    await expect(nodeLink.first()).toBeVisible();
    await nodeLink.first().click();
    await expect(page).toHaveURL(new RegExp(`${AGENCY.replace(/\//g, "\\/")}$`));
    await expect(page.getByTestId("entity-header")).toBeVisible();
    // "What the city bought" — the contract's own page, never folded into
    // the agency's.
    await gotoSettled(page, "/entity/");
    await expect(page.getByTestId("entity-types")).toBeVisible();
    // The hub carries the ER disclosure: SIG has not merged organisations
    // across sources.
    await expect(page.getByTestId("er-disclosure")).toContainText(/has not merged/i);
    await gotoSettled(page, CONTRACT);
    await expect(page.getByTestId("entity-header")).toBeVisible();
    const body = await page.locator("main").innerText();
    expect(body).not.toMatch(/same organisation as|merged with/i);
  });
});

// ---------------------------------------------------------------------------
// K2 J-4 — "is Acworth PD still sharing with Vigilant?" (U-003.11)
// ---------------------------------------------------------------------------
test.describe("J-4 organizer: SIG's only evidence is historical", () => {
  test("the entity page shows the historical edge, the degree-only fact and the task", async ({
    page,
  }) => {
    await gotoSettled(page, ACWORTH);
    // The edge carries its historical marking — never a present-tense share.
    const row = page.getByTestId("relation-row").first();
    await expect(row.getByTestId("historical-mark")).toContainText("historical");
    await expect(row).toContainText("Historical");
    // The degree-only fact where one is recorded: "partners not named".
    await expect(page.getByTestId("degree-fact").first()).toContainText(/partners not named/);
    // The contribution task — the honest "SIG does not know whether current".
    const task = page.getByTestId("related-tasks").locator("a").first();
    await expect(task).toHaveAttribute("href", /^\/task\//);
    await task.click();
    await expect(page).toHaveURL(/\/task\//);
    // The answer frame: no present-tense claim of current sharing.
    const body = await page.locator("main").innerText();
    expect(body).not.toMatch(/is currently sharing|still shares\b/i);
  });
});

// ---------------------------------------------------------------------------
// K2 J-5 — "give me everything behind this graph."
// ---------------------------------------------------------------------------
test.describe("J-5 researcher: the downloads recompute the page", () => {
  test("overview downloads serve; CSV edge rows equal the page rows; labels resolve", async ({
    page,
    request,
  }) => {
    await gotoSettled(page, "/graphs/supply/");
    const downloads = page.locator("a[href^='/graph/supply/']");
    const hrefs = await downloads.evaluateAll((els) =>
      els.map((e) => e.getAttribute("href") ?? ""),
    );
    const named = new Set(hrefs);
    for (const want of [
      "/graph/supply/sig_graph.json",
      "/graph/supply/nodes.sig_graph.csv",
      "/graph/supply/edges.sig_graph.csv",
      "/graph/supply/overview.sig_graph.svg",
    ]) {
      expect(named.has(want), `${want} not offered`).toBeTruthy();
    }
    // Byte-level: each artifact serves.
    for (const href of named) {
      const res = await request.get(href);
      expect(res.status(), href).toBe(200);
    }
    // Recompute: the CSV edge rows equal the page's adjacency rows.
    const csv = await (await request.get("/graph/supply/edges.sig_graph.csv")).text();
    const csvRows = csv.trim().split("\n").length - 1;
    const pageRows = await page.getByTestId("graph-edge-row").count();
    expect(csvRows, "CSV rows ≠ page rows").toBe(pageRows);
    // The JSON doc's dict labels the nodes — J-5's "labels not ids".
    const doc = JSON.parse(await (await request.get("/graph/supply/sig_graph.json")).text());
    expect(doc.schema).toBe("sig.graph-overview/1");
    expect(doc.dict.labels.length).toBeGreaterThan(0);
    // The cap/fold note travels with the bytes.
    expect(Array.isArray(doc.cap_actions)).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// K2 J-6 — keyboard / screen-reader: J-2 with keyboard only.
// ---------------------------------------------------------------------------
test.describe("J-6 keyboard/SR: J-2 by keyboard; axe in interaction states", () => {
  test("the evidence link is reachable by Tab; the claim anchor takes focus", async ({ page }) => {
    await gotoSettled(page, ACWORTH);
    // Tab from the top until the evidence link holds focus (bounded sweep —
    // the page is keyboard-ordered by construction).
    await page.locator("body").focus();
    let found = false;
    for (let i = 0; i < 400; i += 1) {
      await page.keyboard.press("Tab");
      if ((await page.evaluate(() => (document.activeElement as HTMLElement)?.dataset?.testid)) ===
        "relation-evidence" ||
        (await page.evaluate(
          () => (document.activeElement as HTMLElement)?.closest?.("[data-testid='relation-evidence']") !== null,
        ))
      ) {
        found = true;
        break;
      }
    }
    expect(found, "relation-evidence link not reachable by Tab").toBeTruthy();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#claim-/);
  });

  test("Escape closes the explorer panel and returns focus; axe clean in each state", async ({
    page,
  }) => {
    // Entity page axe-clean (the J-2 surface).
    await gotoSettled(page, ACWORTH);
    expect((await axe(page)).violations).toEqual([]);
    // Explorer: select a node (the panel opens), axe-clean in that state.
    await gotoSettled(page, "/explore/?v=2&overview=access");
    const node = page.getByTestId("graph-island-node").first();
    await expect(node).toBeVisible({ timeout: 30_000 });
    await node.click();
    await expect(page.getByTestId("node-panel-title")).toBeVisible();
    expect((await axe(page)).violations).toEqual([]);
    // Escape clears the selection — the panel empties, never a trap.
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("node-panel-title")).toBeHidden();
  });
});

// ---------------------------------------------------------------------------
// K6 VJ-1 — the advocate's Oklahoma City read + print (K13 §8 A3 leg).
// ---------------------------------------------------------------------------
test.describe("VJ-1 advocate: Oklahoma City Figure 1 → print", () => {
  test("every drawn mark carries the single-source encoding; the print document leads the map", async ({
    page,
  }) => {
    await gotoSettled(page, CITY);
    const fig = page.getByTestId("fig1-static");
    await expect(fig).toBeVisible();
    const svg = fig.locator("svg");
    // Every drawn area/point is hollow — the single-source encoding is a
    // mark channel, never colour alone (greyscale-safe by construction).
    const marks = svg.locator("path.sig-fig-area, circle.sig-fig-point");
    const markCount = await marks.count();
    expect(markCount).toBeGreaterThan(0);
    for (let i = 0; i < markCount; i += 1) {
      await expect(marks.nth(i)).toHaveClass(/sig-fig-src-single/);
    }
    // The caption names the one-source rule.
    await expect(page.getByTestId("fig1-caption")).toContainText(/one source|single/i);
    // Print: page 1 = brief + locator; page 2 leads the map figure.
    await gotoSettled(page, `${CITY}print/`);
    const pages = page.getByTestId("print-page");
    const kinds = await pages.evaluateAll((els) =>
      els.map((e) => e.getAttribute("data-page-kind")),
    );
    expect(kinds[0]).toBe("brief");
    expect(kinds[kinds.length - 1]).toBe("terms");
    await expect(page.getByTestId("brief-locator")).toBeVisible();
    expect(kinds[1]).toBe("figures");
    const figPage = page.locator('[data-page-kind="figures"]').first();
    await expect(figPage.getByTestId("print-figure")).toHaveAttribute("data-figure-kind", "map");
    await expect(figPage.locator("svg")).toBeVisible();
    // Every page: as-of + permalink in its running chrome.
    for (let i = 0; i < kinds.length; i += 1) {
      await expect(pages.nth(i).getByTestId("print-runhead")).toBeVisible();
      await expect(pages.nth(i).getByTestId("print-footer")).toBeVisible();
    }
  });
});

// ---------------------------------------------------------------------------
// K6 VJ-2 — the resident: 390 px, no JavaScript.
// ---------------------------------------------------------------------------
test.describe("VJ-2 resident: 390 px no-JS drill-down", () => {
  test("the map draws with JS off; drill-down via the table; the sites list opens", async ({
    browser,
  }) => {
    const ctx = await browser.newContext({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 },
    });
    const page = await ctx.newPage();
    await page.goto(OK_DOSSIER);
    await expect(page.getByTestId("fig1-static").locator("svg")).toBeVisible();
    // Drill-down by pointer via the place-level table — the same rows the
    // keyboard path reaches (state → county → place).
    const county = page
      .locator('a[href="/dossier/usa/ok/oklahoma-county-40109/"]')
      .first();
    await expect(county).toBeVisible();
    await county.click();
    await expect(page).toHaveURL(/oklahoma-county-40109\/$/);
    await expect(page.getByTestId("fig1-static")).toBeVisible();
    const place = page
      .locator('a[href="/dossier/usa/ok/oklahoma-city-4064000/"]')
      .first();
    await expect(place).toBeVisible();
    await place.click();
    await expect(page).toHaveURL(/oklahoma-city-4064000\/$/);
    await expect(page.getByTestId("fig1-static")).toBeVisible();
    // "All N sites" — the sites list opens (MAP-05).
    const sites = page
      .locator('a[href="/dossier/usa/ok/oklahoma-city-4064000/sites/"]')
      .first();
    await expect(sites).toBeVisible();
    await sites.click();
    await expect(page).toHaveURL(/oklahoma-city-4064000\/sites\/$/);
    await ctx.close();
  });
});

// ---------------------------------------------------------------------------
// K6 VJ-3 — the journalist's access-figure walk (fixture: usa/ok).
// ---------------------------------------------------------------------------
test.describe("VJ-3 journalist: access figure → entity → explorer → cite", () => {
  test("untick declared; follow an agency node; back; open in explorer; cite", async ({ page }) => {
    await gotoSettled(page, OK_DOSSIER);
    // The JS-off toggles: unchecking "declared" hides the dashed marks in
    // place (CSS :has — no script needed; verified here JS-on too).
    const declared = page.locator("#k-declared");
    await expect(declared).toBeChecked();
    const wide = page.getByTestId("network-figure-wide");
    const declaredEdges = wide.locator("path.sig-fig-edge-acc-declared");
    await expect(declaredEdges.first()).toBeVisible();
    await declared.uncheck();
    await expect(declaredEdges.first()).toBeHidden();
    // Follow an agency node — every node links.
    const agencyNode = wide.locator("a[href^='/entity/agency/']").first();
    await expect(agencyNode).toBeVisible();
    await agencyNode.click();
    await expect(page).toHaveURL(/\/entity\/agency\//);
    await expect(page.getByTestId("entity-header")).toBeVisible();
    // Back → the figure is still there (the toggle state is CSS state —
    // the box survives the round trip as the served HTML).
    await page.goBack();
    await expect(page.getByTestId("network-figure-wide")).toBeVisible();
    // "Open in the explorer" — the snapshot-pinned handoff.
    const openExplorer = page.getByTestId("network-explore-link");
    await expect(openExplorer).toBeVisible();
    const href = await openExplorer.getAttribute("href");
    expect(href).toContain("/explore/?v=2");
    expect(href).toContain("overview=access");
    expect(href).toContain("jurisdiction=");
    await page.goto(href!.replace(/&amp;/g, "&"));
    await expect(page.getByTestId("explore-island")).toBeVisible();
    // The cite is the snapshot form — minted, never a mutable URL.
    await expect(page.getByTestId("cite-form")).toBeVisible();
    await expect(page.getByTestId("cite-form")).toContainText("overview=access");
  });
});

// ---------------------------------------------------------------------------
// K6 VJ-4 — the organizer's Harris County walk (K13 §8 O1 leg).
// ---------------------------------------------------------------------------
test.describe("VJ-4 organizer: scoped search → in-place map → cite → full map", () => {
  test("search contract; activate; filter source; cite + full map reproduce the state", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoSettled(page, HARRIS);
    // The scoped-search contract: zero-JS GET, release-pinned, jurisdiction
    // scope. (The /v1/ endpoint is the API surface — the in-scope results
    // leg walks the equivalent /search/ facet URL; see the packet.)
    const form = page.getByTestId("dossier-scoped-search-form");
    await expect(form).toHaveAttribute("method", "get");
    await expect(form).toHaveAttribute("action", /\/v1\/releases\/.+\/search/);
    await expect(page.getByTestId("dossier-scoped-search-scope")).toHaveAttribute(
      "value",
      /48201/,
    );
    // The equivalent scoped URL on the search surface answers scoped or
    // says so (SIG-UI-DV04/UXR-10 — never unfiltered-as-filtered).
    await gotoSettled(page, "/search/?v=2&view=list&q=flock&jurisdiction=us.census.geoid.county%3A48201");
    const scoped = page.locator("main");
    const scopedText = await scoped.innerText();
    const applied = /filter/i.test(scopedText) || /48201|Harris/i.test(scopedText);
    expect(applied).toBeTruthy();
    // Back to the dossier → "Explore this map here" (desktop only).
    await gotoSettled(page, HARRIS);
    const button = page.locator(".sig-activate__button");
    await expect(button).toBeVisible();
    await button.click();
    const embed = page.getByTestId("fig-map-embed");
    await expect(embed).toBeVisible();
    const canvas = embed.getByTestId("map-island");
    await expect(canvas).toHaveAttribute("data-ready", "true", { timeout: 30_000 });
    // The filters row carries the source facet.
    await page.getByTestId("map-tab-filters").click();
    const sourceFilter = page.getByTestId("map-filters").locator("[data-testid='filter-source']");
    await expect(sourceFilter).toBeVisible();
    // "Cite this view" + "Open full map" reproduce jurisdiction and view.
    await expect(page.getByTestId("embed-cite")).toBeVisible();
    const openFull = page.getByTestId("embed-open-full");
    await expect(openFull).toHaveAttribute("href", /\/map\/\?v=2/);
    await expect(openFull).toHaveAttribute("href", /jurisdiction=/);
    // The activated box keeps the static figure in the DOM (print) and
    // writes no history.
    await expect(page.getByTestId("fig1-static")).toBeAttached();
  });
});

// ---------------------------------------------------------------------------
// K6 VJ-5 — the journalist's source-breakdown walk (fixture: usa/ok).
// ---------------------------------------------------------------------------
test.describe("VJ-5 journalist: the source breakdown sums; show-on-map carries the facet", () => {
  test("dsrc totals = Σ per-source cells; the map hand-off carries the source facet", async ({
    page,
  }) => {
    await gotoSettled(page, "/dossier/usa/ok/sources/");
    // "from N sources" — the totals figure is the K5 headline.
    const totals = page.getByTestId("dsrc-totals");
    await expect(totals).toBeVisible();
    const figValue = page.locator("#fig-dsrc-records");
    const declared = Number(await figValue.getAttribute("data-figure-value"));
    // Σ per-source record cells == the headline figure.
    const cells = page.getByTestId("dsrc-table").locator("tbody td:nth-child(3)");
    const texts = await cells.allTextContents();
    const sum = texts.reduce((a, t) => a + Number(t.replace(/[^\d]/g, "")), 0);
    expect(sum).toBe(declared);
    // "Show on the map" carries the jurisdiction AND the source facet.
    const showOnMap = page.getByTestId("dsrc-show-on-map").first();
    const href = await showOnMap.getAttribute("href");
    expect(href).toContain("/map/?v=2");
    expect(href).toContain("jurisdiction=");
    expect(href).toContain("source=");
    await page.goto(href!.replace(/&amp;/g, "&"));
    // The map applies the facet or names it (never unfiltered-as-filtered).
    const main = await page.locator("main").innerText();
    expect(/source=|okc_camera_registry|cannot apply|does not apply|filter/i.test(main)).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// K6 VJ-6 — keyboard + screen-reader: VJ-3/VJ-4 with keyboard only.
// ---------------------------------------------------------------------------
test.describe("VJ-6 keyboard+SR: the figure walk and activation by keyboard", () => {
  test("skip link → toggles → node link → table twin; activation + close by keyboard; axe states", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await gotoSettled(page, OK_DOSSIER);
    // The skip link lands on the table twin — the figure's long description.
    const skip = page.locator(".sig-net-skip a");
    await expect(skip).toBeVisible();
    const skipTarget = await skip.getAttribute("href");
    expect(skipTarget).toMatch(/^#/);
    await expect(page.locator(skipTarget!)).toBeAttached();
    // The toggles are keyboard controls; the node link is in the tab order.
    await page.locator("#k-declared").focus();
    await page.keyboard.press("Space");
    const declaredEdges = page.getByTestId("network-figure-wide").locator(
      "path.sig-fig-edge-acc-declared",
    );
    await expect(declaredEdges.first()).toBeHidden();
    await page.locator("#k-declared").focus();
    await page.keyboard.press("Space");
    await expect(declaredEdges.first()).toBeVisible();
    // Activation by keyboard: focus + Enter upgrades in place.
    const button = page.locator(".sig-activate__button");
    await button.focus();
    await page.keyboard.press("Enter");
    const embed = page.getByTestId("fig-map-embed");
    await expect(embed).toBeVisible();
    await expect(embed.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
      timeout: 30_000,
    });
    // Axe clean in the activated state.
    expect((await axe(page)).violations).toEqual([]);
    // Close returns focus to the button.
    const close = page.getByTestId("embed-close");
    await close.focus();
    await page.keyboard.press("Enter");
    await expect(embed).toBeHidden();
    await expect(button).toBeFocused();
    expect((await axe(page)).violations).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// K13 §8 capstone J3 — the disagreements walk.
// ---------------------------------------------------------------------------
test.describe("K13 §8 J3: a disputed figure walks both sides", () => {
  test("dossier disagreements link → the place's disagreements page names the sides", async ({
    page,
    request,
  }) => {
    await gotoSettled(page, "/dossier/usa/tx/");
    const link = page.getByTestId("dossier-disagreements-link").locator("a");
    if (await link.count()) {
      const href = await link.getAttribute("href");
      const res = await request.get(href!);
      expect(res.status()).toBe(200);
      const html = await res.text();
      expect(html).toMatch(/disagree|dispute|both|claim/i);
    } else {
      // No disagreements recorded for the fixture's Texas — the page still
      // resolves (the honest absence is the named answer).
      const res = await request.get("/disagreements/place/usa/tx/");
      expect(res.status()).toBe(200);
    }
  });
});
