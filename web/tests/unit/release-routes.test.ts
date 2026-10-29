// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.18 (UXK14-2, SIG-UI-051/UXR-01) — the release route manifest's unit
// contract: the set names every public route a page file emits plus the
// declared data probes, and never names an internal route (`/releases/`,
// `/curate/**`, `/visual-language/`) or an emitted route the navigation may
// not target (dynamic record paths). Against the fixtures build this is the
// same surface `ops/public_routes.toml` allow-lists.
import { describe, it, expect } from "vitest";
import { releaseRoutes } from "../../src/lib/release-routes";

describe("releaseRoutes — the served-route manifest (SIG-UI-051)", () => {
  const routes = releaseRoutes();

  it("names every static public page route", () => {
    for (const route of [
      "",
      "dossier/",
      "map/",
      "network/",
      "search/",
      "watch/",
      "sources/",
      "sources/identifier-changed/",
      "evidence/",
      "data/dictionary/",
      "status/",
      "glossary/",
      "methodology/",
      "editorial-standards/",
      "corrections/",
      "research-queue/",
      "dispute/",
      "style-guide/",
      "coverage-metrics/",
      "data-collection/",
      "terms/",
    ]) {
      expect(routes.has(route), `release serves ${route || "/"}`).toBe(true);
    }
  });

  it("resolves the declared data-dependent probes", () => {
    // The fixtures build emits the unplaced report and the freshness sort
    // index — both must be offered to chrome.
    expect(routes.has("dossier/unplaced/")).toBe(true);
    expect(routes.has("data-freshness/")).toBe(true);
  });

  it("never names an internal route — internal surfaces are not public", () => {
    // `/releases/`, `/curate/**`, `/research-dossier/**`, `/visual-language/`,
    // `/contribution-back/` live under src/internal/ — a publishable build
    // does not emit them, so the manifest must never offer them to chrome.
    for (const internal of [
      "releases/",
      "visual-language/",
      "contribution-back/",
      "research-dossier/",
      "curate/",
    ]) {
      expect(routes.has(internal), `${internal} is not a public route`).toBe(false);
    }
  });

  it("does not invent dynamic record routes or non-page endpoints", () => {
    // Dynamic emitters ([...path], [id], catch-alls) never stand in for nav
    // targets — their emitted routes are data-dependent.
    expect(routes.has("dossier/oklahoma-city/")).toBe(false);
    expect(routes.has("dossier/oklahoma-city/print/")).toBe(false);
    // Machine endpoints are not nav targets either.
    for (const route of routes) {
      expect(route.endsWith(".json")).toBe(false);
      expect(route.endsWith(".ics")).toBe(false);
      expect(route.endsWith(".xml")).toBe(false);
      expect(route.endsWith(".txt")).toBe(false);
    }
  });

  it("is stable and non-vacuous (SIG-ENG-042 — an empty manifest fails loudly)", () => {
    expect(routes.size).toBeGreaterThanOrEqual(20);
    // Calling it twice returns the same set of routes.
    expect([...releaseRoutes()].sort()).toEqual([...routes].sort());
  });
});
