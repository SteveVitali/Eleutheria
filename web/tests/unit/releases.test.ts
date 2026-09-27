// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import { getReleaseCatalog } from "../../src/lib/data";
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
