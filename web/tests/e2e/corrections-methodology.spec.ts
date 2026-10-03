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

  test("every task card carries a UNIQUE id and every jurisdiction filter anchor resolves (P34.12 / RQ-00)", async ({
    page,
  }) => {
    await page.goto("/research-queue/");
    // No duplicate DOM ids across the whole page (the pre-P34.12 cards all shared
    // their jurisdiction's id).
    const dupes = await page.evaluate(() => {
      const counts = new Map<string, number>();
      for (const el of Array.from(document.querySelectorAll("[id]"))) {
        const id = el.getAttribute("id")!;
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
      return Array.from(counts).filter(([, n]) => n > 1).map(([id]) => id);
    });
    expect(dupes).toEqual([]);
    // Every filter link names an element that exists — and it is a task card's.
    const filters = page.getByTestId("jurisdiction-filter");
    const hrefs = await filters.locator("a").evaluateAll((els) =>
      els.map((e) => e.getAttribute("href")),
    );
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(href).toMatch(/^#/);
      const target = page.locator(href!);
      await expect(target).toHaveCount(1);
      await expect(target).toHaveAttribute("data-testid", "task-card");
    }
    // A card id derives from the task, not the jurisdiction: two cards in one
    // jurisdiction (the fixture's two Oklahoma City tasks) carry distinct ids.
    const okcCards = page.locator("[data-testid='task-card'][data-jurisdiction='Oklahoma City']");
    const okcIds = await okcCards.evaluateAll((els) => els.map((e) => e.getAttribute("id")));
    expect(new Set(okcIds).size).toBe(okcIds.length);
    expect(okcIds.every((id) => id?.startsWith("task-"))).toBe(true);
  });

  test("the provenance module names the page it describes (P34.12 / C3 NEW-13)", async ({ page }) => {
    await page.goto("/research-queue/");
    const scope = page.getByTestId("hwkt-scope");
    await expect(scope).toContainText("research queue");
    await expect(scope).toContainText("not the whole record");
    // A page-scoped module names its own page too — never anonymous "this page".
    await page.goto("/corrections/");
    await expect(page.getByTestId("hwkt-scope")).toContainText("corrections log");
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

  test("the log states its own start date, never implying it ran forever (P34.11 / QW-14)", async ({
    page,
  }) => {
    await page.goto("/corrections/");
    const start = page.getByTestId("log-start");
    await expect(start).toBeVisible();
    await expect(start.locator("time")).toHaveAttribute("datetime", /\d{4}-\d{2}-\d{2}/);
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

  test("publishes the WV-08 handling order and no identity requirement except legal demand", async ({ page }) => {
    // P34.17 / R1.2 (WV-05 + WV-08): the published order — privacy-harm and
    // safety reports first, then factual corrections, then everything else —
    // with NO response-time promise, and no "anonymous" claim (e-mail senders
    // disclose their address). The legal-demand category still notes standing.
    await page.goto("/dispute/");
    const note = page.getByTestId("priority-note");
    await expect(note).toContainText("privacy-harm and safety reports first");
    await expect(note).toContainText("then factual corrections");
    await expect(page.getByTestId("priority-note")).not.toContainText("minute");
    await expect(page.locator("body")).not.toContainText("anonymous");
    await expect(page.locator("body")).not.toContainText("one click");
    const prioritized = page.locator("[data-testid='dispute-category'][data-priority-band='0']");
    await expect(prioritized).toHaveCount(2);
    const needsId = page.locator("[data-testid='dispute-category'][data-requires-identity='true']");
    await expect(needsId).toHaveCount(1);
    await expect(needsId).toHaveAttribute("data-category", "legal_demand");
    // The intake channel is e-mail — the publish build injects the operator's
    // address (SIG_DISPUTE_EMAIL); a publishable tree must never carry "unset".
    await expect(page.getByTestId("intake-channel")).toHaveAttribute("data-intake-email", /^(set|unset)$/);
    await expect(page.getByTestId("intake-channel")).toContainText("e-mail");
  });

  test("refusal is a published, exercisable outcome (SIG-GOV-004)", async ({ page }) => {
    await page.goto("/dispute/");
    await expect(page.getByTestId("refusal-outcome")).toBeVisible();
  });

  test("the receiver is honestly described as not operating (P32.16)", async ({
    page,
  }) => {
    await page.goto("/dispute/");
    const notice = page.getByTestId("intake-availability");
    // The page must never advertise an unstaffed/unapproved receiver — the
    // flip is a later reviewed change gated on D-R10-PUBLISH-1 + staffing.
    await expect(notice).toHaveAttribute("data-operational", "false");
    // P34.17: notice string N-2 ("Not operating yet.") states the truth.
    await expect(notice).toContainText("Not operating yet");
    // It must also never present a fake submission path.
    await expect(page.locator("form")).toHaveCount(0);
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

  test("coverage surfaces the resolved-site framing + contradictions off the materialized graph (P28.5)", async ({
    page,
  }) => {
    await page.goto("/coverage-metrics/");
    // The map's observation-level framing is replaced by "N resolved sites (from M
    // observation-level records; dedup ratio …)" (ADR-101/ADR-105) — N = post-ER clusters of the
    // same physical device, a counted quantity carrying its named denominator, never a
    // total. It rides the frozen CoverageMetric contract, so it renders on the coverage page.
    const resolved = page.locator('[data-metric-id="resolved_sites"]');
    await expect(resolved).toContainText("resolved sites");
    await expect(resolved).toContainText("observation-level records");
    await expect(resolved).toContainText("dedup ratio");
    await expect(resolved.getByTestId("coverage-denominator")).toContainText("observation-level sites");
    // Contradictions stay recorded (§3.1): the materialized §31 contradiction object is
    // surfaced as an honest counted quantity (both evidence sides retained). P34.11
    // (K12b NEW-17): the label no longer claims a browsable contradiction surface —
    // the metric says what exists (a count) and names what does not (a browser).
    const contradictions = page.locator('[data-metric-id="contradictions_visible"]');
    await expect(contradictions).toContainText("recorded contradictions");
    await expect(contradictions).toContainText("does not publish a contradiction browser");
    await expect(contradictions.getByTestId("coverage-denominator")).toContainText("both evidence sides retained");
  });

  test("methodology states the capture–recapture prohibition (SIG-METRIC-008)", async ({ page }) => {
    await page.goto("/methodology/");
    await expect(page.getByTestId("no-capture-recapture")).toContainText("capture–recapture");
  });

  test("methodology surfaces the resolution eval honestly, with the PROVISIONAL disclosure (P28.4)", async ({
    page,
  }) => {
    await page.goto("/methodology/");
    // SIG measures its own method: the holdout metrics render.
    const metrics = page.getByTestId("resolution-eval-metric");
    await expect(metrics.first()).toBeVisible();
    await expect(page.getByTestId("resolution-eval")).toContainText("0.714"); // Cohen's κ
    await expect(page.getByTestId("resolution-eval")).toContainText("0.976"); // B-cubed F1
    // P34.17 / R1.4: the disclosure is honest development evidence — no person
    // labelled the sets — never a "human-verified" claim or a P/R/F1 1.000 row.
    await expect(page.getByTestId("resolution-eval-provisional")).toContainText("Development evidence only");
    await expect(page.getByTestId("resolution-eval")).not.toContainText("human-verified");
    await expect(page.getByTestId("resolution-eval")).not.toContainText("R 1.000");
    // P30.2b (ADR-105): the unit is defined — a resolved site is a cluster of records of the
    // same physical device, N of M; a value decision is never counted as one.
    const definition = page.getByTestId("resolved-site-definition");
    await expect(definition).toContainText("same physical device");
    await expect(definition).toContainText("N resolved sites from M observation-level");
    await expect(definition).toContainText("is never counted as a resolved site");
    // …and the camera-site rules' measured holdout precision + the missed κ bar are published.
    await expect(page.getByTestId("resolution-eval")).toContainText("0.986"); // tier 3g
    await expect(page.getByTestId("resolution-eval")).toContainText("suggester only");
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

  test("the hostile-reader review is recorded truthfully as not yet performed (SIG-UI-042, WV-04)", async ({ page }) => {
    // P34.17 / ADR-179: the fabricated two-reviewer "Releasable" record is gone;
    // the page states the review was never performed (notice N-1) and no review
    // card or findings render.
    await page.goto("/editorial-standards/");
    await expect(page.getByTestId("review-status")).toContainText("Not yet performed.");
    await expect(page.getByTestId("review-finding")).toHaveCount(0);
    await expect(page.getByTestId("review-reviewers")).toHaveCount(0);
    // The fabricated claims stay gone: no "Releasable" status anywhere.
    await expect(page.locator("body")).not.toContainText("Releasable");
    await expect(page.locator("body")).not.toContainText("Reviewer A");
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
