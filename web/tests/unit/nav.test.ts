// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.18 (UXK14-2, SIG-UI-051/UXR-01) — the navigation model's unit contract:
// sections and items render ONLY against routes the release serves, the
// current section resolves by longest declared prefix, and a section that
// resolves to nothing is honestly absent (never a dead link).
import { describe, it, expect } from "vitest";
import {
  NAV_SECTIONS,
  navForRoutes,
  sectionForPath,
  pathInSection,
} from "../../src/lib/nav";

/** A release route set shaped like today's public surface. */
const PUBLIC_ROUTES = new Set([
  "",
  "dossier/",
  "dossier/unplaced/",
  "map/",
  "network/",
  "search/",
  "watch/",
  "sources/",
  "sources/identifier-changed/",
  "evidence/",
  "data/dictionary/",
  "data-freshness/",
  "status/",
  "glossary/",
  "methodology/",
  "editorial-standards/",
  "corrections/",
  "research-queue/",
  "dispute/",
  "style-guide/",
  "coverage-metrics/",
  "terms/",
]);

describe("navForRoutes — the route-aware six-section header (SIG-UI-051)", () => {
  it("offers at most six sections plus search", () => {
    const nav = navForRoutes(PUBLIC_ROUTES, "");
    expect(nav.length).toBeLessThanOrEqual(6);
  });

  it("omits a section whose routes the release does not serve — Organizations", () => {
    const nav = navForRoutes(PUBLIC_ROUTES, "");
    // No entity/organization hub is emitted today → the section is honestly
    // absent, never a dead link (UXR-01).
    expect(nav.find((s) => s.id === "organizations")).toBeUndefined();
    const labels = nav.map((s) => s.label);
    expect(labels).toEqual(["Places", "Explore", "Watch", "Sources & data", "About"]);
  });

  it("renders Organizations when a release serves the entity hub", () => {
    const withEntities = new Set([...PUBLIC_ROUTES, "entity/"]);
    const nav = navForRoutes(withEntities, "");
    const org = nav.find((s) => s.id === "organizations");
    expect(org).toBeDefined();
    expect(org!.landing).toBe("entity/");
  });

  it("drops every item whose route the release does not emit", () => {
    const nav = navForRoutes(PUBLIC_ROUTES, "");
    // /releases/ is internal and /disagreements/ is not emitted → neither
    // appears in a rendered menu.
    for (const section of nav) {
      for (const item of section.items) {
        expect(PUBLIC_ROUTES.has(item.route), `${item.label} → ${item.route}`).toBe(true);
      }
    }
    const sources = nav.find((s) => s.id === "sources-data")!;
    expect(sources.items.map((i) => i.label)).not.toContain("Releases & changes");
    const explore = nav.find((s) => s.id === "explore")!;
    expect(explore.items.map((i) => i.label)).not.toContain("Disagreements");
  });

  it("never renders a menu item that repeats the section's landing link", () => {
    const nav = navForRoutes(PUBLIC_ROUTES, "");
    for (const section of nav) {
      expect(section.items.map((i) => i.route)).not.toContain(section.landing);
    }
  });

  it("lands the label on the first rendered item when the declared landing is absent", () => {
    // About's landing is methodology/ — a release without it falls back to the
    // first item that resolves, never a dead link.
    const routes = new Set([...PUBLIC_ROUTES].filter((r) => r !== "methodology/"));
    const about = navForRoutes(routes, "").find((s) => s.id === "about")!;
    expect(routes.has(about.landing)).toBe(true);
    expect(about.landing).toBe("glossary/");
  });

  it("omits a section that resolves to nothing at all", () => {
    const nav = navForRoutes(new Set([""]), "");
    expect(nav).toEqual([]);
  });
});

describe("sectionForPath — the current-section marker (aria-current)", () => {
  it("marks the section the path sits inside", () => {
    expect(sectionForPath("dossier/oklahoma-city/")?.id).toBe("places");
    expect(sectionForPath("dossier/unplaced/")?.id).toBe("places");
    expect(sectionForPath("map/")?.id).toBe("explore");
    expect(sectionForPath("search/")?.id).toBe("explore");
    expect(sectionForPath("watch/")?.id).toBe("watch");
    expect(sectionForPath("sources/identifier-changed/")?.id).toBe("sources-data");
    expect(sectionForPath("data/dictionary/")?.id).toBe("sources-data");
    expect(sectionForPath("data-freshness/")?.id).toBe("sources-data");
    expect(sectionForPath("status/")?.id).toBe("sources-data");
    expect(sectionForPath("corrections/")?.id).toBe("about");
    expect(sectionForPath("glossary/")?.id).toBe("about");
    expect(sectionForPath("methodology/")?.id).toBe("about");
    expect(sectionForPath("dispute/")?.id).toBe("about");
  });

  it("marks nothing on the home page or an unclassified route", () => {
    expect(sectionForPath("")).toBeUndefined();
    expect(sectionForPath("404.html")).toBeUndefined();
  });

  it("a partial segment never marks a section — data-freshness/ is not data/", () => {
    // `data-freshness/` must not satisfy the `data/` prefix via bare string
    // prefixing; it is declared explicitly in the section's match list.
    expect(pathInSection("data-freshness/", NAV_SECTIONS[4]!)).toBe(true);
    const fake = { ...NAV_SECTIONS[4]!, match: ["data/"] };
    expect(pathInSection("data-freshness/", fake)).toBe(false);
  });
});

describe("aria-current wiring", () => {
  it("sets the section marker only on the current section", () => {
    const nav = navForRoutes(PUBLIC_ROUTES, "corrections/");
    const marked = nav.filter((s) => s.current);
    expect(marked.map((s) => s.id)).toEqual(["about"]);
  });

  it("marks the exact item when its route is the current page", () => {
    const nav = navForRoutes(PUBLIC_ROUTES, "glossary/");
    const about = nav.find((s) => s.id === "about")!;
    const glossary = about.items.find((i) => i.route === "glossary/")!;
    expect(glossary.current).toBe(true);
    for (const item of about.items) {
      if (item !== glossary) expect(item.current).toBe(false);
    }
  });
});
