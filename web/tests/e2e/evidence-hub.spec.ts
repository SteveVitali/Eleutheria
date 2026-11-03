// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.60 (K8 EV-02 / SIG-EVUI-001,002,003,005,010): the evidence hub's e2e
// legs — the artifact page's §4.2 blocks, the facet routes, the capture diff,
// the moved-stub fallback, the JSON twins and the honest run-record labels.
import { expect, test } from "@playwright/test";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const CONTRACT_HANDLE = "E-usa-ok-oklahoma-city-contract-executed-okcpd-flock-kq2p";
const NEWS_HANDLE = "E-usa-ok-oklahoma-city-news-local-newspaper-report-1aja";
const PORTAL_HANDLE = "E-usa-ok-oklahoma-city-portal-eyes-on-flock-portal-8hqv";

test.describe("artifact pages (§4.2)", () => {
  test("the artifact page renders every block, fields as values or named absences", async ({
    page,
  }) => {
    await page.goto(`/evidence/artifact/${CONTRACT_HANDLE}/`);
    await expect(page.getByTestId("artifact-page")).toBeVisible();
    await expect(page.getByTestId("artifact-page")).toHaveAttribute(
      "data-artifact-id",
      "contract:okcpd-alpr",
    );
    await expect(page.getByTestId("artifact-lane")).toContainText("raw-ok");
    // The upstream block: a real URL on the raw-ok artifact.
    await expect(page.getByTestId("artifact-upstream").locator("a")).toHaveAttribute(
      "href",
      "https://records.example.gov/okcpd/alpr-contract.pdf",
    );
    // The capture history shows its classification per row (SIG-EVUI-003).
    await expect(page.getByTestId("capture-row")).toHaveCount(1);
    await expect(page.getByTestId("capture-classification").first()).toContainText("actual");
    // Claims supported: the active-device-count statement binds to this artifact.
    await expect(page.getByTestId("artifact-claim").first()).toContainText("active-device-count");
    // The JSON twin exists.
    await expect(page.getByTestId("artifact-json-twin")).toHaveAttribute(
      "href",
      `/evidence/artifact/${CONTRACT_HANDLE}.json`,
    );
  });

  test("a synthetic artifact is labelled a run record — never a stored document", async ({
    page,
  }) => {
    await page.goto(`/evidence/artifact/${NEWS_HANDLE}/`);
    await expect(page.getByTestId("run-record-label")).toHaveText(
      "run record — SIG did not store this document",
    );
    // The synthetic capture row carries the run-record classification.
    await expect(page.getByTestId("capture-row").first()).toHaveAttribute(
      "data-classification",
      "synthetic",
    );
    await expect(page.getByTestId("capture-classification").first()).toContainText("run record");
    // No download-original href on a withheld-byte capture (SIG-EVUI-003).
    await expect(page.getByTestId("view-original").first()).toContainText("View at source");
    await expect(page.getByTestId("view-original-note")).toContainText(
      "SIG did not retain these bytes",
    );
    await expect(page.locator("a[data-testid='view-original']")).toHaveCount(0);
  });

  test("the capture diff compares two real captures of the same artifact (§4.4, SIG-EVUI-005)", async ({
    page,
  }) => {
    await page.goto(`/evidence/artifact/${PORTAL_HANDLE}/`);
    await expect(page.getByTestId("capture-row")).toHaveCount(2);
    await page.getByTestId("diff-link").first().click();
    await expect(page.getByTestId("capture-diff")).toBeVisible();
    // active_device_count changed between the June and August captures.
    const rows = page.getByTestId("diff-field");
    await expect(rows).toHaveCount(3);
    await expect(page.locator('[data-testid="diff-field"][data-field="active_device_count"]')).toHaveAttribute(
      "data-changed",
      "true",
    );
    await expect(page.locator('[data-testid="diff-field"][data-field="retention_days"]')).toHaveAttribute(
      "data-changed",
      "false",
    );
  });
});

test.describe("the retired claim address (K13 §2.5)", () => {
  test("/evidence/<id>/ answers a moved stub pointing at the canonical claim route", async () => {
    // The browser follows the stub's zero-second meta refresh; the static HTML
    // itself is the assertion — the fallback that answers where the include
    // cannot run (K4 §8.2's moved-stub pattern).
    const html = readFileSync(
      join(process.cwd(), "dist/evidence/active-device-count/index.html"),
      "utf-8",
    );
    expect(html).toContain("evidence-moved-stub");
    expect(html).toContain('href="/evidence/claim/active-device-count/"');
    expect(html).toContain('http-equiv="refresh"');
    // The JUR-05 generator's 301 rule exists in redirects.conf.
    const conf = readFileSync(join(process.cwd(), "dist/redirects.conf"), "utf-8");
    expect(conf).toContain("location = /evidence/active-device-count/ { return 301 /evidence/claim/active-device-count/$is_args$args; }");
  });

  test("the canonical claim page answers at /evidence/claim/<id>/", async ({ page }) => {
    const res = await page.goto("/evidence/claim/active-device-count/");
    expect(res?.status()).toBe(200);
    await expect(page.getByTestId("evidence-view")).toBeVisible();
  });
});

test.describe("facets + JSON twins", () => {
  test("facet pages list the filtered artifacts", async ({ page }) => {
    await page.goto("/evidence/state/legacy_synthetic/");
    await expect(page.getByTestId("evidence-artifact-row")).toHaveCount(2);
    await page.goto("/evidence/lane/raw-ok/");
    await expect(page.getByTestId("evidence-artifact-row")).toHaveCount(2);
    await page.goto("/evidence/type/contract/");
    await expect(page.getByTestId("evidence-artifact-row")).toHaveCount(1);
    await page.goto("/evidence/place/unplaced/");
    await expect(page.getByTestId("evidence-artifact-row")).toHaveCount(4);
  });

  test("the source facet links back to the emitted source page", async ({ page }) => {
    await page.goto("/evidence/source/okc-council-minutes/");
    await expect(page.getByTestId("evidence-artifact-row")).toHaveCount(1);
    await expect(page.getByTestId("source-page-link")).toHaveAttribute(
      "href",
      "/sources/okc_council_minutes/",
    );
  });

  test("the JSON twins carry the same facts the pages render", async ({ request }) => {
    const idx = await (await request.get("/evidence/index.json")).json();
    expect(idx.schema).toBe("sig.evidence-index/1");
    expect(idx.artifacts).toHaveLength(8);
    expect(idx.rollup.run_records).toBe(2);
    const art = await (
      await request.get(`/evidence/artifact/${CONTRACT_HANDLE}.json`)
    ).json();
    expect(art.schema).toBe("sig.evidence-artifact-page/1");
    expect(art.artifact_id).toBe("contract:okcpd-alpr");
    expect(art.lane).toBe("raw-ok");
    expect(art.claims_supported.map((c: { claim_id: string }) => c.claim_id)).toContain(
      "active-device-count",
    );
    const claim = await (await request.get("/evidence/claim/active-device-count.json")).json();
    expect(claim.schema).toBe("sig.evidence-claim-view/1");
    expect(claim.claim_id).toBe("active-device-count");
  });

  test("the watch item page links into artifact + claim pages", async ({ page }) => {
    await page.goto("/watch/item/W-us-ok-oklahoma-city-4064000-renewal-c100-ab12/");
    await expect(page.getByTestId("evidence-artifact-link").first()).toBeVisible();
  });
});

test.describe("handles (SIG-EVUI-010)", () => {
  test("the emitted artifact handles are unique and ≤64 chars", () => {
    const dir = join(process.cwd(), "dist/evidence/artifact");
    const handles = readdirSync(dir).filter(
      (e) => e.startsWith("E-") && statSync(join(dir, e)).isDirectory(),
    );
    expect(handles.length).toBe(8);
    for (const h of handles) {
      expect(h.length).toBeLessThanOrEqual(64);
      expect(h).toMatch(/^E-[a-z0-9-]+$/);
    }
  });
});
