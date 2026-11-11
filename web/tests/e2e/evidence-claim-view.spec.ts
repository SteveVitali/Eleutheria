// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P37.37 (K8 EV-03 / SIG-EVUI-004/005/009): the claim viewer v2 + the real
// capture diff — the published generation cap + overflow disclosure on
// /evidence/, the lane-aware panes (the raw-ok `download` pane + the D-K8-1
// excerpt), and the typed absence where a second capture isn't recorded.
import { expect, test } from "@playwright/test";

const CONTRACT_HANDLE = "E-usa-ok-oklahoma-city-contract-executed-okcpd-flock-kq2p";
const PORTAL_HANDLE = "E-usa-ok-oklahoma-city-portal-eyes-on-flock-portal-8hqv";

test.describe("claim-view generation cap disclosure (SIG-EVUI-009)", () => {
  test("/evidence/ states the cap, the emitted and the eligible counts", async ({ page }) => {
    await page.goto("/evidence/");
    const cap = page.getByTestId("claim-view-cap");
    await expect(cap).toBeVisible();
    await expect(cap).toContainText("cap of 20,000");
    await expect(page.getByTestId("claim-view-emitted")).toHaveText("5");
    await expect(page.getByTestId("claim-view-eligible")).toHaveText("5");
    // No overflow in the fixture set — the disclosure renders only when nonzero.
    await expect(page.getByTestId("claim-view-overflow")).toHaveCount(0);
  });
});

test.describe("the lane-aware claim-view panes (SIG-EVUI-004)", () => {
  test("the raw-ok download pane shows the locator, digest, excerpt and download link", async ({
    page,
  }) => {
    await page.goto("/evidence/claim/contract-renewal-term/");
    await expect(page.getByTestId("download-pane")).toBeVisible();
    // The locator always; the D-K8-1 excerpt where terms permit (raw-ok publishes bytes).
    await expect(page.getByTestId("download-pane")).toContainText("renewal clause");
    await expect(page.getByTestId("claim-excerpt")).toContainText("one-year terms");
    await expect(page.getByTestId("download-original")).toHaveAttribute(
      "href",
      "https://files.example.org/raw/sha256:ab12cd34ef56ab12",
    );
    await expect(page.getByTestId("capture-digest")).toContainText("sha256:");
  });

  test("the derived-only locator pane shows the locator without bytes", async ({ page }) => {
    await page.goto("/evidence/claim/portal-device-count/");
    await expect(page.getByTestId("locator-only-pane")).toBeVisible();
    await expect(page.getByTestId("locator-only-pane")).toContainText("JSON pointer");
    await expect(page.getByTestId("document-text")).toHaveCount(0);
  });
});

test.describe("the real-capture diff (SIG-EVUI-005, amends SIG-UI-029)", () => {
  test("a two-capture artifact links the field-by-field diff over real captures", async ({
    page,
  }) => {
    await page.goto(`/evidence/artifact/${PORTAL_HANDLE}/`);
    await expect(page.getByTestId("diff-link").first()).toBeVisible();
    await expect(page.getByTestId("diff-absence")).toHaveCount(0);
    const res = await page.goto(
      `/evidence/artifact/${PORTAL_HANDLE}/diff/capture:okcpd-portal-2026-06..capture:okcpd-portal-2026-08/`,
    );
    expect(res?.status()).toBe(200);
    await expect(page.getByTestId("artifact-capture-diff")).toBeVisible();
    // Real recorded values only — the fixture pair's own fields.
    await expect(page.getByTestId("diff-field").first()).toBeVisible();
  });

  test("a single-capture artifact states the typed absence — never a fabricated pair", async ({
    page,
  }) => {
    await page.goto(`/evidence/artifact/${CONTRACT_HANDLE}/`);
    await expect(page.getByTestId("diff-absence")).toContainText("Only one capture");
    await expect(page.getByTestId("diff-link")).toHaveCount(0);
  });
});
