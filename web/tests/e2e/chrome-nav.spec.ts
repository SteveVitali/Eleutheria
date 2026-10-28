// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.18 (UXK14-2 + the K13 IA; SIG-UI-051/145/150) — the shared chrome spec:
// the six-section route-aware header (aria-current; the mobile <details>
// menu), the header search GET that opens the K13 A1 journey, the page-header
// band (breadcrumbs, stamp, Cite disclosure), the footer strip inside the
// forty-word chrome budget, and the mobile H1-in-120px layout contract.
// Runs against the BUILT static site (astro preview).
import { test, expect } from "@playwright/test";
import { DISCOVERED_ROUTES } from "./pages";

const PUBLIC_ROUTES = new Set(
  DISCOVERED_ROUTES.filter((r) => !r.internal).map((r) => r.path),
);

test.describe("the six-section route-aware header (SIG-UI-051, UXR-01)", () => {
  test("the primary nav offers at most six sections plus the search entry", async ({
    page,
  }) => {
    await page.goto("/");
    const nav = page.locator("nav[aria-label='Primary']");
    await expect(nav).toBeVisible();
    const sections = nav.locator(".sig-nav__section");
    const count = await sections.count();
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThanOrEqual(6);
    // The search entry is a plain GET form — always present (P36.40's
    // typeahead upgrades it later; the chrome hosts the entry now).
    const form = page.locator("form[data-testid='site-search']");
    await expect(form).toBeVisible();
    await expect(form).toHaveAttribute("method", "get");
    await expect(form).toHaveAttribute("action", /\/search\/$/);
    await expect(form.locator("input[name='q']")).toHaveCount(1);
  });

  test("every rendered nav target resolves in this release — no dead links", async ({
    page,
    request,
  }) => {
    await page.goto("/");
    const hrefs = await page
      .locator("nav[aria-label='Primary'] a, nav[aria-label='Footer'] a")
      .evaluateAll((els) => els.map((el) => el.getAttribute("href")).filter(Boolean));
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      const res = await request.get(href!);
      expect(res.status(), `chrome link ${href} must resolve in this release`).toBe(200);
    }
    // The route the release does not serve is never offered: no entity hub is
    // emitted today, so the Organizations section is honestly absent; the
    // internal /releases/ route is never a chrome target.
    await expect(
      page.locator("nav[aria-label='Primary'] .sig-nav__section-link", { hasText: "Organizations" }),
    ).toHaveCount(0);
    expect(hrefs.some((h) => h === "/releases/" || h!.startsWith("/releases/"))).toBe(false);
    // And every target is a public route the build emitted (sitemap-side check).
    for (const href of hrefs) {
      expect(PUBLIC_ROUTES.has(href!), `chrome link ${href} is an emitted public route`).toBe(true);
    }
  });

  test("the current section carries aria-current on the page that sits in it", async ({
    page,
  }) => {
    const cases: { path: string; label: string }[] = [
      { path: "/dossier/oklahoma-city/", label: "Places" },
      { path: "/map/", label: "Explore" },
      { path: "/watch/", label: "Watch" },
      { path: "/status/", label: "Sources & data" },
      { path: "/corrections/", label: "About" },
      { path: "/glossary/", label: "About" },
    ];
    for (const { path, label } of cases) {
      await page.goto(path);
      const nav = page.locator("nav[aria-label='Primary']");
      const marked = nav.locator(".sig-nav__section-link[aria-current]");
      await expect(marked, `${path}: exactly one section is current`).toHaveCount(1);
      await expect(marked, `${path}: the current section is ${label}`).toHaveText(label);
    }
    // The home page belongs to no section — nothing is marked.
    await page.goto("/");
    await expect(
      page.locator("nav[aria-label='Primary'] .sig-nav__section-link[aria-current]"),
    ).toHaveCount(0);
  });

  test("the mobile <details> menu carries the same sections with no JavaScript", async ({
    page,
  }) => {
    // At a mobile width the desktop nav is hidden and the details menu is the
    // navigation — the disclosure itself is native HTML.
    await page.setViewportSize({ width: 375, height: 640 });
    await page.goto("/dossier/oklahoma-city/");
    const details = page.locator("[data-testid='mobile-nav']");
    await expect(details).toHaveCount(1);
    // The desktop sections and the mobile menu mirror one another.
    const primary = page.locator("nav[aria-label='Primary']");
    const desktopLabels = await primary
      .locator(".sig-nav__section-link")
      .evaluateAll((els) => els.map((el) => el.textContent?.trim()));
    const mobile = details.locator("nav[aria-label='Menu']");
    const mobileLabels = await mobile
      .locator(".sig-nav__section-link")
      .evaluateAll((els) => els.map((el) => el.textContent?.trim()));
    expect(mobileLabels).toEqual(desktopLabels);
    // aria-current survives in the mobile form too.
    await expect(mobile.locator(".sig-nav__section-link[aria-current]")).toHaveText("Places");
    // The disclosure is native: opening it reveals the menu without a script.
    await expect(mobile).not.toBeVisible();
    await details.locator("summary").click();
    await expect(mobile).toBeVisible();
    // K14 §5.3's compact bar: the search field steps aside for a link to
    // /search/ — same destination, no room for a field at this width.
    await expect(page.locator("form[data-testid='site-search']")).not.toBeVisible();
    const searchLink = page.locator("[data-testid='site-search-link']");
    await expect(searchLink).toBeVisible();
    await expect(searchLink).toHaveAttribute("href", "/search/");
  });
});

test.describe("the header search entry — K13 capstone A1's first click (SIG-UI-051)", () => {
  test("the header search is a plain GET to /search/ and the A1 route reaches the place dossier", async ({
    page,
  }) => {
    await page.goto("/");
    const input = page.locator("form[data-testid='site-search'] input[name='q']");
    await input.fill("Oklahoma City");
    await Promise.all([
      page.waitForURL(/\/search\/\?q=/),
      input.press("Enter"),
    ]);
    // A1's chrome slice: the type-in lands on the search surface (P36.40's
    // typeahead is the interactive upgrade), whose named no-JS equivalents
    // link the dossier index — the browse route to the named place.
    expect(page.url()).toContain("/search/");
    expect(page.url()).toContain("q=Oklahoma+City");
    await expect(page.locator("h1")).toContainText("Search");
    await page.locator("a[href='/dossier/']").first().click();
    await expect(page.locator("a[href='/dossier/oklahoma-city/']").first()).toBeVisible();
    await page.locator("a[href='/dossier/oklahoma-city/']").first().click();
    await page.waitForURL(/\/dossier\/oklahoma-city\//);
    await expect(page.locator("main h1")).toContainText(/Oklahoma City/);
  });
});

test.describe("the page-header band + breadcrumbs (SIG-UI-150)", () => {
  test("every full-chrome page renders the band with the release stamp and Cite disclosure", async ({
    page,
  }) => {
    for (const path of ["/", "/methodology/", "/map/"]) {
      await page.goto(path);
      const band = page.locator("[data-testid='page-header']");
      await expect(band).toBeVisible();
      await expect(band.locator("h1")).toHaveCount(1);
      await expect(band.locator("[data-testid='page-stamp']")).toContainText(/data as of/);
      await expect(band.locator("[data-testid='cite-details']")).toHaveCount(1);
    }
  });

  test("a record page carries breadcrumbs: Places > the place", async ({ page }) => {
    await page.goto("/dossier/oklahoma-city/");
    const crumbs = page.locator("[data-testid='dossier-breadcrumb']");
    await expect(crumbs).toBeVisible();
    const items = crumbs.locator("li");
    await expect(items).toHaveCount(2);
    await expect(items.nth(0).locator("a")).toHaveAttribute("href", "/dossier/");
    await expect(items.nth(0)).toContainText("Places");
    // The last crumb is the current page — unlinked, aria-current="page".
    const last = items.nth(1).locator("[aria-current='page']");
    await expect(last).toHaveCount(1);
    await expect(last).toContainText(/Oklahoma City/);
  });

  test("the band's Cite disclosure opens the citation affordance without JS mechanics", async ({
    page,
  }) => {
    await page.goto("/dossier/oklahoma-city/");
    await page.locator("[data-testid='cite-details'] > summary").click();
    await expect(page.getByTestId("citation")).toBeVisible();
    await expect(page.getByTestId("permalink")).toHaveAttribute("href", /as_of_world=/);
  });

  test("the dossier's band actions link the print and JSON forms", async ({ page }) => {
    await page.goto("/dossier/oklahoma-city/");
    const band = page.locator("[data-testid='page-header']");
    await expect(band.getByTestId("print-link")).toHaveAttribute("href", /\/dossier\/oklahoma-city\/print\/$/);
    await expect(band.getByTestId("api-link")).toHaveAttribute("href", /\/dossier\/oklahoma-city\.json$/);
  });

  test("a record page keeps the module one action away and page-specific (SIG-UI-145)", async ({
    page,
  }) => {
    // The disclosure stays closed on the dossier too — one action away is the
    // posture on every page; on a record page the module labels its actual
    // scope (page-specific when the release emits a per-dossier row — the
    // fixture dossier has none, so it honestly reads site-wide, P34.12).
    await page.goto("/dossier/oklahoma-city/");
    const details = page.locator("[data-testid='chrome-details']");
    await expect(details).not.toHaveAttribute("open", "");
    await expect(page.getByTestId("how-we-know-this")).not.toBeVisible();
    await details.locator("> summary").click();
    await expect(page.getByTestId("how-we-know-this")).toBeVisible();
    await expect(page.getByTestId("hwkt-scope")).toContainText(/Site-wide|dossier/i);
  });
});

test.describe("the footer strip — forty-word chrome (SIG-UI-145)", () => {
  test("the strip, disclosure and tagline render on every full-chrome page", async ({
    page,
  }) => {
    for (const path of ["/", "/dossier/oklahoma-city/", "/dispute/"]) {
      await page.goto(path);
      const strip = page.locator("[data-testid='footer-strip']");
      await expect(strip).toBeVisible();
      await expect(strip).toContainText("data as of");
      await expect(strip).toContainText("not yet human-reviewed");
      await expect(strip.locator("[data-testid='dispute-link']")).toBeVisible();
      await expect(page.locator("[data-testid='footer-tagline']")).toContainText(
        /not a census · not advocacy/i,
      );
      await expect(page.locator("nav[aria-label='Footer']")).toBeVisible();
    }
  });

  test("the shared provenance modules stay one action away in the disclosure", async ({
    page,
  }) => {
    await page.goto("/");
    // The module + release sentences exist in the static HTML but are not
    // visible by default — the strip's word budget holds because they are one
    // action away, never removed.
    const module = page.getByTestId("how-we-know-this");
    await expect(module).toHaveCount(1);
    await expect(module).not.toBeVisible();
    await page.locator("[data-testid='chrome-details'] > summary").click();
    await expect(module).toBeVisible();
    await expect(page.getByTestId("release-stamp")).toBeVisible();
    await expect(page.getByTestId("publication-basis")).toBeVisible();
  });

  test("visible-by-default chrome stays within the forty-word budget", async ({ page }) => {
    // Counts the SHARED chrome words — the footer (minus disclosure bodies)
    // plus the band's stamp/action/summary chrome — never page content or
    // navigation labels (SIG-UI-145).
    const count = async (path: string) => {
      await page.goto(path);
      return page.evaluate(() => {
        const clone = document.body.cloneNode(true) as HTMLElement;
        // Disclosure bodies are one action away — keep only the summary text.
        clone.querySelectorAll("details").forEach((d) => {
          [...d.children].forEach((c) => {
            if (c.tagName !== "SUMMARY") c.remove();
          });
        });
        const words = (el: Element | null): number =>
          (el?.textContent ?? "")
            .split(/\s+/)
            .filter((w) => /[\p{L}\p{N}]/u.test(w)).length;
        const footer = clone.querySelector("footer");
        const band = clone.querySelector("[data-testid='page-header']");
        // Page content inside the band is not chrome: the H1, lede and the
        // breadcrumb trail (nav labels) are excluded.
        band?.querySelector("h1")?.remove();
        band?.querySelector(".sig-page-header__lede")?.remove();
        band?.querySelector("[aria-label='Breadcrumb']")?.remove();
        return words(footer) + words(band);
      });
    };
    for (const path of ["/", "/dossier/oklahoma-city/", "/methodology/", "/dispute/"]) {
      const words = await count(path);
      expect(words, `${path}: shared chrome renders ${words} words — budget is 40`).toBeLessThanOrEqual(40);
    }
  });
});

test.describe("the shared layout grid (K14 §4.5)", () => {
  test("the mobile H1 starts within 120 px of the top at 320 px reflow", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 600 });
    for (const path of ["/", "/dossier/oklahoma-city/"]) {
      await page.goto(path);
      const box = await page.locator("main h1").boundingBox();
      expect(box, `${path}: h1 has a layout box`).not.toBeNull();
      expect(
        box!.y,
        `${path}: mobile H1 starts ${box!.y.toFixed(0)} px from the top — budget is 120`,
      ).toBeLessThanOrEqual(120);
    }
  });
});
