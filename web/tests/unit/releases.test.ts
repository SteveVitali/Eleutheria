// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  getEntityCompartments,
  getReleaseCatalog,
  getReleaseSearchTargets,
} from "../../src/lib/data";
import { RELEASE_CATALOG_FIXTURE } from "../../src/lib/releases-fixture";

describe("release catalog (P32.13, SIG-FIND-001/002)", () => {
  it("fixtures mode returns the demo catalog (exercises the real render path)", () => {
    const catalog = getReleaseCatalog();
    expect(catalog.schema).toBe("sig.publication-catalog/1");
    expect(catalog.publications.length).toBe(1);
    const e = catalog.publications[0];
    expect(e.publication_id).toMatch(/^p-[0-9a-f]{64}$/);
    expect(e.reproducibility.as_of_world).toBeTruthy();
    expect(e.compartments[0].license).toBe("CC-BY-4.0");
    expect(e.completeness?.state).toBe("complete");
  });

  it("the fixture is the committed demo — never a live-release claim", () => {
    expect(RELEASE_CATALOG_FIXTURE.publications[0].data_release_id).toContain("demo");
  });
});

describe("released-corpus search targets (P32.14, SIG-FIND-003)", () => {
  it("one GET target per activated compartment, pinned to the namespace", () => {
    const targets = getReleaseSearchTargets();
    expect(targets.length).toBe(1);
    const t = targets[0];
    expect(t.publicationId).toMatch(/^p-[0-9a-f]{64}$/);
    expect(t.landingHref).toBe(`/releases/${t.publicationId}/`);
    const c = t.compartments[0];
    expect(c.compartment).toBe("sig_graph");
    // The form posts to the release search route under the pinned namespace —
    // never a current-only or unversioned search path.
    expect(c.searchHref).toBe(
      `/v1/releases/${t.publicationId}/compartments/sig_graph/search`,
    );
    expect(c.overviewHref).toBe(`/r/${t.publicationId}/c/sig_graph/`);
  });

  it("SIG_RELEASE_SEARCH_BASE overrides only the route origin", () => {
    const prev = process.env.SIG_RELEASE_SEARCH_BASE;
    process.env.SIG_RELEASE_SEARCH_BASE = "https://api.example.test/";
    try {
      const c = getReleaseSearchTargets()[0].compartments[0];
      expect(c.searchHref.startsWith("https://api.example.test/v1/releases/")).toBe(
        true,
      );
      expect(c.overviewHref.startsWith("/r/")).toBe(true);
    } finally {
      if (prev === undefined) delete process.env.SIG_RELEASE_SEARCH_BASE;
      else process.env.SIG_RELEASE_SEARCH_BASE = prev;
    }
  });

  it("fixtures mode maps no entity compartments (demo ≠ a real namespace)", () => {
    expect(getEntityCompartments().size).toBe(0);
  });
});
