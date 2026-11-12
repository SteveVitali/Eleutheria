// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.72 — the 'My location' map-pan control (D-K1-7 [B-44] = yes; K1 §4.1/§4.2).
// The SIG-GOV-017 analysis it honours: docs/build/reports/p37.72-gov017-analysis.
// Pinned: the read happens ONLY on an explicit click; the position never
// reaches the network (the only write is the same zoom-rounded `at=` every
// pan writes); no marker, no 'cameras near you' list/count/alert/proximity
// copy; denial/unavailability is honest and leaves the map put.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { gotoSettled } from "./pages";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

// An Oklahoma City position — inside the fixtures' coverage.
const POS = { latitude: 35.4676, longitude: -97.5164 };

async function ready(page: import("@playwright/test").Page, url = "/map/") {
  await gotoSettled(page, url);
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-ready", "true", {
    timeout: 20_000,
  });
  await expect(page.getByTestId("map-island")).toHaveAttribute("data-drawn", "true", {
    timeout: 20_000,
  });
}

/** Counts getCurrentPosition calls so load-time silence is assertable. */
const GEO_SPY = () => {
  const geo = navigator.geolocation;
  if (!geo) return;
  const orig = geo.getCurrentPosition.bind(geo);
  (window as unknown as { __geoCalls: number }).__geoCalls = 0;
  geo.getCurrentPosition = ((s: PositionCallback, e?: PositionErrorCallback | null, o?: PositionOptions) => {
    (window as unknown as { __geoCalls: number }).__geoCalls += 1;
    return orig(s, e, o);
  }) as typeof geo.getCurrentPosition;
};

test.describe("my-location pan control (P37.72)", () => {
  test("geolocation is never requested on load — only on the explicit click", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["geolocation"]);
    await context.setGeolocation(POS);
    await page.addInitScript(GEO_SPY);
    await ready(page);
    const calls = () =>
      page.evaluate(() => (window as unknown as { __geoCalls: number }).__geoCalls);
    // The island hydrated and drew without touching geolocation.
    expect(await calls(), "no geolocation read before the click").toBe(0);
    await page.getByTestId("my-location").click();
    await expect.poll(calls, { timeout: 5_000 }).toBe(1);
  });

  test("the click pans to the position and the position never reaches the network", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["geolocation"]);
    await context.setGeolocation(POS);
    await ready(page);
    const requests: string[] = [];
    page.on("request", (r) => requests.push(r.url()));
    await page.getByTestId("my-location").click();
    // The same zoom-rounded `at=` every pan writes — wait for the SETTLED
    // viewport (the first moveend also writes the pre-pan `at=`).
    await expect(page).toHaveURL(/35\.4\d/, { timeout: 15_000 });
    const m = page.url().match(/at=(\d+)(?:%2F|\/)(-?[\d.]+)(?:%2F|\/)(-?[\d.]+)/);
    expect(m, "at= viewport token").not.toBeNull();
    const [, z, lat, lon] = m!;
    expect(Number(z)).toBeGreaterThanOrEqual(10);
    expect(Number(lat)).toBeCloseTo(POS.latitude, 1);
    expect(Number(lon)).toBeCloseTo(POS.longitude, 1);
    // Never a marker at the viewer — the control only pans.
    await expect(page.locator(".maplibregl-marker")).toHaveCount(0);
    // No request carries the position — full precision or rounded.
    await page.waitForTimeout(500);
    for (const u of requests) {
      expect(u, `position must never leave the browser: ${u}`).not.toMatch(
        /35\.4\d|-97\.5\d/,
      );
    }
    // No 'near you' / proximity copy anywhere on the surface.
    const body = await page.locator("body").innerText();
    expect(body).not.toMatch(/near you|nearby|around you|watching you/i);
    // The honest in-view line is viewport copy, unchanged.
    await expect(page.getByTestId("inview-status")).toContainText("in view", {
      timeout: 10_000,
    });
  });

  test("a denial shows the honest note and the map stays put", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: {
          getCurrentPosition: (
            _s: unknown,
            err?: (e: GeolocationPositionError) => void,
          ) =>
            err?.({
              code: 1,
              PERMISSION_DENIED: 1,
              POSITION_UNAVAILABLE: 2,
              TIMEOUT: 3,
              message: "denied",
            }),
          watchPosition: () => 0,
          clearWatch: () => undefined,
        },
      });
    });
    await ready(page);
    // The island's own first settled viewport write (refreshList's 300 ms
    // debounce after load → `at=` via replaceState, SIG-UI-103) can land
    // after `data-drawn` latches. Baseline only once it has, so the
    // comparison below isolates the denial path from the load-time write.
    await expect(page).toHaveURL(/[?&]at=\d+(%2F|\/)/, { timeout: 15_000 });
    const urlBefore = page.url();
    await page.getByTestId("my-location").click();
    const note = page.getByTestId("my-location-note");
    await expect(note).toContainText("map stays where it is", { timeout: 5_000 });
    await expect(note).toContainText("Nothing was read or sent");
    await expect(page.getByTestId("my-location")).toBeEnabled();
    expect(page.url(), "a failed read never rewrites the viewport").toBe(urlBefore);
  });

  test("the control passes axe WCAG 2.2 AA inside the map chrome", async ({ page }) => {
    await ready(page);
    const results = await new AxeBuilder({ page })
      .withTags(WCAG_TAGS)
      .include(".sig-map-app__controls")
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
