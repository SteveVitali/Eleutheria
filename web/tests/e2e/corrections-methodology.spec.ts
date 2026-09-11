// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { test, expect } from "@playwright/test";
import { PHASE15_SURFACES, SHELL_PAGES } from "./pages";

test.describe("research queue (§39.7, SIG-UI-031)", () => {
  test("each task card states closing condition, evidence sought, assignee class, effort", async ({ page }) => {
    await page.goto("/research-queue/");
    const card = page.getByTestId("task-card").first();
    await expect(card.getByTestId("closing-condition")).not.toBeEmpty();
    await expect(card.getByTestId("evidence-sought")).not.toBeEmpty();
    await expect(card.getByTestId("assignee-class")).not.toBeEmpty();
    await expect(card.getByTestId("effort-estimate")).not.toBeEmpty();
  });

  test("supports geographic filtering (§33.5)", async ({ page }) => {
    await page.goto("/research-queue/");
    const filters = page.getByTestId("jurisdiction-filter");
    await expect(filters.first()).toBeVisible();
    const jurisdictions = await filters.evaluateAll((els) => els.map((e) => e.getAttribute("data-jurisdiction")));
    expect(jurisdictions).toContain("Oklahoma City");
    expect(jurisdictions).toContain("Tulsa");
  });

  test("claiming grants priority, never exclusivity (SIG-TASK-010/011)", async ({ page }) => {
    await page.goto("/research-queue/");
    const claimed = page.locator("[data-testid='task-card'][data-claimed='true']").first();
    await expect(claimed).toBeVisible();
    // Every card states that any contributor may still work it.
    const anyone = page.getByTestId("anyone-may-work");
    await expect(anyone.first()).toContainText("priority, not exclusivity");
  });

  test("exposes the full disposition vocabulary incl. searched-found-nothing (SIG-TASK-008/009)", async ({ page }) => {
    await page.goto("/research-queue/");
    const searchTask = page.locator("[data-testid='task-card'][data-assignee='field_mapper']").first();
    await expect(
      searchTask.locator("[data-testid='disposition'][data-searched-found-nothing='true']"),
    ).toHaveCount(1);
  });

  test("has no volume leaderboard (SIG-TASK-012)", async ({ page }) => {
    await page.goto("/research-queue/");
    await expect(page.getByTestId("no-leaderboard-note")).toBeVisible();
  });
});

test.describe("public corrections log (§39.8, SIG-UI-032)", () => {
  test("lists every correction with what/when/why/who", async ({ page }) => {
    await page.goto("/corrections/");
    const first = page.getByTestId("correction").first();
    await expect(first.getByTestId("what-changed")).not.toBeEmpty();
    await expect(first.getByTestId("when")).not.toBeEmpty();
    await expect(first.getByTestId("why")).not.toBeEmpty();
    await expect(first.getByTestId("reported-by")).not.toBeEmpty();
  });

  test("preserves history: the prior value stays citable (SIG-GOV-005)", async ({ page }) => {
    await page.goto("/corrections/");
    const link = page.getByTestId("prior-permalink").first();
    const href = await link.getAttribute("href");
    expect(href).toContain("as_of_belief=");
    expect(href).toContain("ruleset=");
  });

  test("transparency report counts outcomes including refusals (SIG-GOV-011)", async ({ page }) => {
    await page.goto("/corrections/");
    await expect(page.getByTestId("transparency-by-category")).toBeVisible();
    await expect(page.getByTestId("outcome-count-refused")).toContainText("refused");
  });
});

test.describe("dispute/correction submission path (SIG-UI-033, §45)", () => {
  test("is one click from every page and reachable at /dispute/", async ({ page }) => {
    for (const path of ["/", "/dossier/oklahoma-city/", "/watch/"]) {
      await page.goto(path);
      const link = page.getByTestId("dispute-link").first();
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute("href", /\/dispute\//);
    }
  });

  test("prioritizes privacy/safety above all and needs no identity except legal demand", async ({ page }) => {
    await page.goto("/dispute/");
    await expect(page.getByTestId("priority-note")).toContainText("before all others");
    const prioritized = page.locator("[data-testid='dispute-category'][data-priority-band='0']");
    await expect(prioritized).toHaveCount(2);
    const needsId = page.locator("[data-testid='dispute-category'][data-requires-identity='true']");
    await expect(needsId).toHaveCount(1);
    await expect(needsId).toHaveAttribute("data-category", "legal_demand");
  });

  test("refusal is a published, exercisable outcome (SIG-GOV-004)", async ({ page }) => {
    await page.goto("/dispute/");
    await expect(page.getByTestId("refusal-outcome")).toBeVisible();
  });
});

test.describe("methodology, data-freshness, coverage-metrics (SIG-UI-034, §32.4/32.5)", () => {
  test("all three pages are public and linked from every dossier", async ({ page }) => {
    // Linked from the dossier via the "How we know this" module the base layout renders.
    await page.goto("/dossier/oklahoma-city/");
    await expect(page.getByTestId("methodology-link")).toHaveAttribute("href", "/methodology/");
    await expect(page.getByTestId("data-freshness-link")).toHaveAttribute("href", "/data-freshness/");
    await expect(page.getByTestId("coverage-metrics-link")).toHaveAttribute("href", "/coverage-metrics/");
  });

  test("data-freshness shows per-source run/change/status/stale counts (SIG-METRIC-007)", async ({ page }) => {
    await page.goto("/data-freshness/");
    const row = page.getByTestId("freshness-row").first();
    await expect(row.getByTestId("freshness-status")).not.toBeEmpty();
    await expect(row.getByTestId("stale-count")).not.toBeEmpty();
  });

  test("coverage metrics name denominators and never claim a total (SIG-METRIC-009/010)", async ({ page }) => {
    await page.goto("/coverage-metrics/");
    await expect(page.getByText("never publishes a total")).toBeVisible();
    await expect(page.getByTestId("no-total-note")).toContainText("capture–recapture");
    const metric = page.getByTestId("coverage-metric").first();
    await expect(metric.getByTestId("coverage-denominator")).not.toBeEmpty();
    await expect(metric.getByTestId("population-note")).not.toBeEmpty();
  });

  test("methodology states the capture–recapture prohibition (SIG-METRIC-008)", async ({ page }) => {
    await page.goto("/methodology/");
    await expect(page.getByTestId("no-capture-recapture")).toContainText("capture–recapture");
  });
});

test.describe("editorial standards (§41, SIG-UI-042/043/045/046)", () => {
  test("the three example cases render as specified (SIG-UI-045)", async ({ page }) => {
    await page.goto("/editorial-standards/");
    const cases = page.getByTestId("editorial-case");
    await expect(cases).toHaveCount(3);
    await expect(page.locator("[data-testid='editorial-case'][data-case-id='pending_lawsuit']")).toContainText(
      "has not been adjudicated",
    );
    await expect(
      page.locator("[data-testid='editorial-case'][data-case-id='cancellation_hardware_remaining']"),
    ).toContainText("not a record of surveillance being removed");
  });

  test("the hostile-reader review is recorded and every finding dispositioned (SIG-UI-042)", async ({ page }) => {
    await page.goto("/editorial-standards/");
    await expect(page.getByTestId("review-reviewers")).toContainText(";"); // two reviewers
    await expect(page.getByTestId("release-status")).toHaveAttribute("data-releasable", "true");
    await expect(page.getByTestId("release-status")).toHaveAttribute("data-open-findings", "0");
    const findings = page.getByTestId("review-finding");
    await expect(findings.first()).toBeVisible();
    // No finding is left open.
    await expect(page.locator("[data-testid='review-finding'][data-disposition='open']")).toHaveCount(0);
  });

  test("the style guide codifies the six register rules; generated text is bound (SIG-UI-043/046)", async ({ page }) => {
    await page.goto("/style-guide/");
    await expect(page.getByTestId("register-rule")).toHaveCount(6);
    // Every generated rationale template shown is conformant.
    const generated = page.getByTestId("generated-rationale");
    await expect(generated.first()).toBeVisible();
    await expect(page.locator("[data-testid='generated-rationale'][data-conformant='false']")).toHaveCount(0);
  });
});

test.describe("'How we know this' module on every page (SIG-UI-044)", () => {
  for (const path of SHELL_PAGES) {
    test(`all six components present on ${path}`, async ({ page }) => {
      await page.goto(path);
      const module = page.getByTestId("how-we-know-this");
      await expect(module).toBeVisible();
      for (const component of [
        "artifact_count",
        "tier_distribution",
        "source_independence_count",
        "date_range",
        "rules_applied",
        "human_review_status",
      ]) {
        await expect(module.locator(`[data-component='${component}']`)).toHaveCount(1);
      }
    });
  }
});

test.describe("seven outline surfaces + the corrections log exist (P15.5 AC1)", () => {
  for (const [surface, path] of Object.entries(PHASE15_SURFACES)) {
    test(`surface "${surface}" exists at ${path}`, async ({ page }) => {
      const res = await page.goto(path);
      expect(res?.status()).toBeLessThan(400);
      await expect(page.locator("h1")).toBeVisible();
    });
  }

  test("the recommender lives on /watch/ and the viewer at /evidence/*", async ({ page }) => {
    await page.goto("/watch/");
    await expect(page.getByTestId("recommended-artifact").first()).toBeVisible();
    await page.goto("/evidence/active-device-count/");
    await expect(page.getByTestId("highlighted-span")).toBeVisible();
  });
});
