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
import {
  latestDecisionFor,
  namingDecisions,
  namingRecordConcurs,
  namingRecordPermits,
  replayNamingDecision,
  type OfficerNamingRecord,
} from "../../src/lib/officer-naming";
import { FR_DOSSIER, BE_DOSSIER } from "../../src/lib/dossier-jurisdiction-fixture";
import { OKC_DOSSIER } from "../../src/lib/dossier-fixture";

// A synthetic persisted two-reviewer concurrence for the test seam — the
// committed registry itself stays empty (no real naming act exists; ADR-163).
const ALL_PRONGS = {
  official_conduct: true,
  name_on_face_of_record: true,
  record_public_in_jurisdiction: true,
  claim_fails_without_name: true,
  proportionate: true,
};
const TWO_REVIEWERS = [
  { reviewer_id: "rev-a", agrees: true, rationale: "official conduct on the record" },
  { reviewer_id: "rev-b", agrees: true, rationale: "claim fails without the name" },
];
const CONCUR_RECORD: OfficerNamingRecord = {
  decision_id: "ond-test-concur",
  subject_id: "agency:okcpd",
  predicate_id: "approving_official",
  permitted: true,
  reason: "two independent reviewers concurred in writing",
  prongs: ALL_PRONGS,
  reviewers: TWO_REVIEWERS,
  recorded_at: "2026-10-14T00:00:00Z",
  recorded_by: "operator (recorded two-reviewer act)",
};

describe("jurisdiction-conditional publication (SIG-PUB-017)", () => {
  it("permits a public-employee name only where both jurisdictions permit", () => {
    expect(publicationPermitted("US", "US", { isPublicEmployeeName: true })).toBe(true);
    expect(publicationPermitted("FR", "FR", { isPublicEmployeeName: true })).toBe(false);
    expect(publicationPermitted("BE", "BE", { isPublicEmployeeName: true })).toBe(false);
    // One permissive + one restrictive jurisdiction → still withheld.
    expect(publicationPermitted("US", "FR", { isPublicEmployeeName: true })).toBe(false);
    expect(publicationPermitted("FR", "US", { isPublicEmployeeName: true })).toBe(false);
    // The map is aligned to the full jurisdictions.toml set (P35.28 drift fix).
    expect(publicationPermitted("UK", "UK", { isPublicEmployeeName: true })).toBe(true);
    expect(publicationPermitted("US-CA", "US-CA", { isPublicEmployeeName: true })).toBe(true);
    expect(publicationPermitted("EU", "EU", { isPublicEmployeeName: true })).toBe(false);
    expect(publicationPermitted("DE", "DE", { isPublicEmployeeName: true })).toBe(false);
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

describe("the persisted naming-decision record (SIG-PUB-007/008, P35.28)", () => {
  it("the committed registry parses as sig.officer-naming-decisions/1", () => {
    expect(Array.isArray(namingDecisions())).toBe(true);
  });

  it("replays the §43.4 test over the stored inputs — never trusts the bare flag", () => {
    expect(replayNamingDecision(CONCUR_RECORD)).toBe(true);
    expect(namingRecordConcurs(CONCUR_RECORD)).toBe(true);
    // A forged permit over non-concurring inputs is denied (fail-closed).
    expect(
      namingRecordConcurs({
        ...CONCUR_RECORD,
        reviewers: TWO_REVIEWERS.slice(0, 1), // one reviewer is not a concurrence
      }),
    ).toBe(false);
    expect(
      namingRecordConcurs({
        ...CONCUR_RECORD,
        reviewers: [
          TWO_REVIEWERS[0]!,
          { reviewer_id: "rev-b", agrees: false, rationale: "not proportionate" },
        ],
      }),
    ).toBe(false);
    // Stored deny over concurring inputs is inconsistent → still withhold.
    expect(namingRecordConcurs({ ...CONCUR_RECORD, permitted: false })).toBe(false);
    // Carve-outs deny regardless of the stored flag (SIG-PUB-009/010).
    expect(namingRecordConcurs({ ...CONCUR_RECORD, is_home_address: true })).toBe(false);
    expect(namingRecordConcurs({ ...CONCUR_RECORD, is_routine_audit_row: true })).toBe(
      false,
    );
  });

  it("latest-in-append-order governs; a non-concur supersedes a concur", () => {
    const deny: OfficerNamingRecord = {
      ...CONCUR_RECORD,
      decision_id: "ond-test-deny",
      permitted: false,
      reason: "reviewers did not concur",
      reviewers: [
        TWO_REVIEWERS[0]!,
        { reviewer_id: "rev-b", agrees: false, rationale: "no longer proportionate" },
      ],
      supersedes: "ond-test-concur",
    };
    expect(latestDecisionFor([CONCUR_RECORD, deny], "agency:okcpd", "approving_official"))
      .toBe(deny);
    expect(namingRecordPermits("agency:okcpd", "approving_official", [deny]).permitted).toBe(
      false,
    );
  });

  it("no record → default deny on every jurisdiction leg", () => {
    const verdict = namingRecordPermits("agency:okcpd", "approving_official", []);
    expect(verdict.permitted).toBe(false);
    expect(verdict.reason).toContain("default deny");
  });
});

describe("applyPublicationPolicy only ever withholds (Part VIII §0.7)", () => {
  it("withholds the US public-employee name while no concurrence is recorded", () => {
    // The committed registry is empty: even a jurisdiction-permitted name is
    // withheld — default deny (the gate never permits without a record).
    const gated = applyPublicationPolicy(OKC_DOSSIER, { namingDecisions: [] });
    const officer = gated.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
    expect(officer.value).toBeNull();
    expect(officer.note).toContain("default deny");
  });

  it("shows the US name only with a recorded two-reviewer concurrence", () => {
    const gated = applyPublicationPolicy(OKC_DOSSIER, {
      namingDecisions: [CONCUR_RECORD],
    });
    const officer = gated.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBeFalsy();
    expect(officer.value).toBe("Chief Wade Gourley");
    expect(officer.namingDecisionId).toBe("ond-test-concur");
  });

  it("withholds a recorded concur where the jurisdiction rule denies", () => {
    // FR-GDPR denies the jurisdiction leg even when a record concurs.
    const frRecord: OfficerNamingRecord = {
      ...CONCUR_RECORD,
      decision_id: "ond-test-fr",
      subject_id: "org:prefpol-paris",
      predicate_id: "signing_officer",
    };
    const gated = applyPublicationPolicy(FR_DOSSIER, { namingDecisions: [frRecord] });
    const officer = gated.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
    expect(officer.value).toBeNull();
    expect(officer.note).toContain("FR-GDPR");
    expect(officer.namingDecisionId).toBe("ond-test-fr");
  });

  it("withholds the FR public-employee name and clears its value", () => {
    const gated = applyPublicationPolicy(FR_DOSSIER, { namingDecisions: [] });
    const rows = gated.sections.find((s) => s.section_id === "accountability_events")!.rows!;
    const officer = rows.find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
    expect(officer.value).toBeNull();
    expect(officer.note).toContain("FR-GDPR");
  });

  it("withholds the BE public-employee name", () => {
    const gated = applyPublicationPolicy(BE_DOSSIER, { namingDecisions: [] });
    const officer = gated.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
  });

  it("withholds a single-reviewer record and a dissenting record (SIG-PUB-008)", () => {
    const single: OfficerNamingRecord = {
      ...CONCUR_RECORD,
      decision_id: "ond-test-single",
      reviewers: TWO_REVIEWERS.slice(0, 1),
      permitted: true,
    };
    // `single` is inconsistent (a stored permit over non-concurring inputs) —
    // the gate replays the inputs, never the flag.
    const gatedSingle = applyPublicationPolicy(OKC_DOSSIER, {
      namingDecisions: [single],
    });
    const officer = gatedSingle.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
    expect(officer.value).toBeNull();
  });

  it("withholds under an unknown jurisdiction even with a recorded concur", () => {
    const dossier = { ...OKC_DOSSIER, jurisdictionCode: "ZZ" };
    const gated = applyPublicationPolicy(dossier, { namingDecisions: [CONCUR_RECORD] });
    const officer = gated.sections
      .flatMap((s) => s.rows ?? [])
      .find((r) => r.isPublicEmployeeName)!;
    expect(officer.withheld).toBe(true);
    expect(officer.note).toContain("UNKNOWN");
  });
});
