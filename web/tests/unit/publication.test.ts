// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { describe, expect, it } from "vitest";
import {
  adapterFor,
  adapterPublicationPermitted,
  publicationPermitted,
} from "../../src/lib/publication";
import { applyPublicationPolicy } from "../../src/lib/dossier";
import { FR_DOSSIER, BE_DOSSIER } from "../../src/lib/dossier-jurisdiction-fixture";
import { OKC_DOSSIER } from "../../src/lib/dossier-fixture";

describe("jurisdiction-conditional publication (SIG-PUB-017)", () => {
  it("publishes a public-employee name only where both jurisdictions permit", () => {
    expect(publicationPermitted("US", "US", { isPublicEmployeeName: true })).toBe(true);
    expect(publicationPermitted("FR", "FR", { isPublicEmployeeName: true })).toBe(false);
    expect(publicationPermitted("BE", "BE", { isPublicEmployeeName: true })).toBe(false);
    // One permissive + one restrictive jurisdiction → still withheld.
    expect(publicationPermitted("US", "FR", { isPublicEmployeeName: true })).toBe(false);
    expect(publicationPermitted("FR", "US", { isPublicEmployeeName: true })).toBe(false);
  });

  it("never gates non-employee-name material", () => {
    expect(publicationPermitted("FR", "FR", { isPublicEmployeeName: false })).toBe(true);
  });

  it("defaults an unknown jurisdiction to no-publish (conservative)", () => {
    expect(publicationPermitted("ZZ", "ZZ", { isPublicEmployeeName: true })).toBe(false);
  });

  it("routes through the adapter using its own code as the subject jurisdiction", () => {
    expect(
      adapterPublicationPermitted(adapterFor("US"), "US", { isPublicEmployeeName: true }),
    ).toBe(true);
    expect(
      adapterPublicationPermitted(adapterFor("FR"), "FR", { isPublicEmployeeName: true }),
    ).toBe(false);
  });
});

describe("applyPublicationPolicy only ever withholds (Part VIII §0.7)", () => {
  it("withholds the FR public-employee name and clears its value", () => {
    const gated = applyPublicationPolicy(FR_DOSSIER);
    const rows = gated.sections.find((s) => s.section_id === "accountability_events")!.rows!;
    const officer = rows.find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
    expect(officer.value).toBeNull();
    expect(officer.note).toContain("FR-GDPR");
  });

  it("withholds the BE public-employee name", () => {
    const gated = applyPublicationPolicy(BE_DOSSIER);
    const officer = gated.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
  });

  it("leaves the US public-employee name published (existing behaviour unchanged)", () => {
    const gated = applyPublicationPolicy(OKC_DOSSIER);
    const officer = gated.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBeFalsy();
    expect(officer.value).toBe("Chief Wade Gourley");
  });
});
