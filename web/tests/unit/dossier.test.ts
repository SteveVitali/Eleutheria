// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The §39.2 dossier content contract (SIG-UI-010..015), tested on the pure logic in
// isolation from the Astro render. Mirrors the superseded P06.1 renderer's contract
// tests (tests/exports/test_dossier.py), now over the production TypeScript surface.
import { describe, expect, it } from "vitest";
import {
  NO_RECORD_IN_SIG,
  SECTION_ACTION_BLOCKS,
  SECTION_IDS,
  dossierUnknowns,
  incompletenessBanner,
  nextDecisionDate,
  renderDossierJson,
  resolveTermination,
  rowDisplayValue,
  sectionIsEmpty,
  unresearchedFieldCount,
  validateDossier,
} from "../../src/lib/dossier";
import type { Dossier } from "../../src/lib/dossier";
import { OKC_DOSSIER } from "../../src/lib/dossier-fixture";

describe("the twelve sections in order (SIG-UI-010)", () => {
  it("is exactly the §39.2 order", () => {
    expect(SECTION_IDS).toEqual([
      "at_a_glance",
      "what_is_deployed",
      "cost_and_expiry",
      "who_else_can_see",
      "configuration_and_retention",
      "usage",
      "where_the_hardware_is",
      "policy",
      "accountability_events",
      "timeline",
      "what_we_dont_know",
      "how_we_know_this",
    ]);
  });

  it("the worked dossier validates, and a mis-ordered one is rejected", () => {
    expect(() => validateDossier(OKC_DOSSIER)).not.toThrow();
    const bad: Dossier = { ...OKC_DOSSIER, sections: [...OKC_DOSSIER.sections].reverse() };
    expect(() => validateDossier(bad)).toThrow(/SIG-UI-010/);
    expect(() => renderDossierJson(bad)).toThrow();
  });
});

describe("next_decision_date, not the expiry date (SIG-UI-014b)", () => {
  it("auto-renewal: expiry minus the notice window (the Appendix-D example)", () => {
    expect(nextDecisionDate({ auto_renews: true, notice_window_days: 90, expiry_date: "2027-04-02" })).toBe(
      "2027-01-02",
    );
  });

  it("no auto-renewal: the decision must be taken by the expiry itself", () => {
    expect(nextDecisionDate({ auto_renews: false, notice_window_days: 90, expiry_date: "2027-04-02" })).toBe(
      "2027-04-02",
    );
  });

  it("auto-renewal without a known notice window falls back to the expiry", () => {
    expect(nextDecisionDate({ auto_renews: true, notice_window_days: null, expiry_date: "2027-04-02" })).toBe(
      "2027-04-02",
    );
  });

  it("no expiry date yields no decision date", () => {
    expect(nextDecisionDate({ auto_renews: true, notice_window_days: 90, expiry_date: null })).toBeNull();
  });

  it("resolveTermination attaches the derived date to the raw inputs", () => {
    const t = resolveTermination(OKC_DOSSIER.termination);
    expect(t.next_decision_date).toBe("2027-01-02");
    expect(t.expiry_date).toBe("2027-04-02");
  });
});

describe("incompleteness banner (SIG-UI-012)", () => {
  it("names the count of EVERY unanswered field, broken down honestly, plus the absence rule (P34.11 / QW-7)", () => {
    const banner = incompletenessBanner(OKC_DOSSIER);
    const u = dossierUnknowns(OKC_DOSSIER);
    expect(u.total).toBeGreaterThan(0);
    expect(banner).toContain(`${u.total} field`);
    expect(banner).toContain("no recorded value");
    // The not-researched subset is named as such, never conflated with the
    // searched-but-empty or unresolved kinds.
    expect(banner).toContain(`${u.notResearched} not researched`);
    expect(banner).toContain("absence of a row is not evidence of absence");
  });

  it("counts DISTINCT NOT_RESEARCHED fields, not the other unknown kinds, deduped", () => {
    // NOT_RESEARCHED (subject, predicate) pairs in the fixture: unmapped_devices
    // (gap) and immigration_enforcement_config (row) = 2 distinct. sharing_partners
    // is UNRESOLVED (F-422: a contested sharing edge is recorded — 'not researched'
    // would contradict the record), and the NO_EVIDENCE_FOUND retention field
    // (SIG looked) must NOT be counted as unresearched either.
    expect(unresearchedFieldCount(OKC_DOSSIER)).toBe(2);
  });
});

describe("dossierUnknowns — every field the page cannot answer (P34.11 / QW-7)", () => {
  const u = dossierUnknowns(OKC_DOSSIER);

  it("counts every unknown kind, deduplicated by (subject, predicate)", () => {
    // 2 NOT_RESEARCHED (unmapped_devices, immigration_enforcement_config);
    // 1 NO_EVIDENCE_FOUND (retention_days — gap AND row, counted once);
    // 2 UNRESOLVED (sharing_partners — gap AND row, counted once; contracted_active_delta);
    // 2 bare UNKNOWNs (annual contract value, policy written retention — null
    // rows with no recorded absence kind: rendered 'unknown', never assigned one).
    expect(u.notResearched).toBe(2);
    expect(u.noEvidenceFound).toBe(1);
    expect(u.unresolved).toBe(2);
    expect(u.unknown).toBe(2);
    expect(u.total).toBe(7);
    expect(u.withheld).toBe(0);
  });

  it("the worked dossier has no empty sections; an empty one is detected and never assigned a kind", () => {
    expect(u.emptySections).toBe(0);
    const withEmpty = {
      ...OKC_DOSSIER,
      sections: OKC_DOSSIER.sections.map((s) =>
        s.section_id === "usage" ? { section_id: "usage" } : s,
      ),
    };
    const u2 = dossierUnknowns(withEmpty);
    expect(u2.emptySections).toBe(1);
    expect(sectionIsEmpty({ section_id: "usage" })).toBe(true);
    // The empty-section sentence asserts NO absence kind.
    expect(NO_RECORD_IN_SIG).toBe("No record in SIG.");
    expect(NO_RECORD_IN_SIG).not.toMatch(/not researched|no evidence|absent/i);
  });

  it("a bare-null action-block field is an unknown the banner counts", () => {
    const noVote = {
      ...OKC_DOSSIER,
      authorization: { ...OKC_DOSSIER.authorization, vote: null },
    };
    expect(dossierUnknowns(noVote).unknown).toBe(u.unknown + 1);
  });

  it("the rendered JSON carries the full unknown counts additively", () => {
    const js = renderDossierJson(OKC_DOSSIER);
    expect(js.unresearched_field_count).toBe(2);
    expect(js.unknown_field_count).toBe(7);
    expect(js.empty_section_count).toBe(0);
    expect(js.unknown_fields).toMatchObject({
      not_researched: 2,
      no_evidence_found: 1,
      unresolved: 2,
      unknown: 2,
    });
  });

  it("section/action-block placement is shared, so page and print cannot disagree", () => {
    expect(SECTION_ACTION_BLOCKS["cost_and_expiry"]).toBe("termination");
    expect(SECTION_ACTION_BLOCKS["accountability_events"]).toBe("authorization");
    expect(SECTION_ACTION_BLOCKS["policy"]).toBe("legal_regime");
  });
});

describe("what we don't know: summary + API (SIG-UI-011)", () => {
  const js = renderDossierJson(OKC_DOSSIER);

  it("appears at the summary top level AND as a section", () => {
    const gaps = js.what_we_dont_know as unknown[];
    expect(gaps.length).toBeGreaterThan(0);
    const sections = js.sections as Array<{ id: string }>;
    expect(sections.some((s) => s.id === "what_we_dont_know")).toBe(true);
    expect(sections.map((s) => s.id)).toEqual([...SECTION_IDS]);
  });

  it("carries the three action blocks with the derived decision date (SIG-UI-014a/b)", () => {
    expect(js.authorization).toMatchObject({ consent_agenda: true, public_comment: false });
    expect(js.termination_mechanics).toMatchObject({ next_decision_date: "2027-01-02" });
    expect(js.legal_regime).toHaveProperty("state_statute");
  });
});

describe("every material figure expands to its reconciliation (SIG-UI-014)", () => {
  const js = renderDossierJson(OKC_DOSSIER);
  const sections = js.sections as Array<{ id: string; figures: any[] }>;
  const deployed = sections.find((s) => s.id === "what_is_deployed")!;

  it("carries rule, winning + competing claims, each with tier/date/document link", () => {
    expect(deployed.figures.length).toBeGreaterThan(0);
    for (const fig of deployed.figures) {
      const rec = fig.reconciliation;
      expect(rec.rule).toBeTruthy();
      expect(rec.winning_present).toBe(true);
      for (const c of rec.claims) {
        expect(c.tier).toBeTruthy();
        expect(c.date).toBeTruthy();
        expect(c.document_url).toBeTruthy();
      }
      expect(rec.claims.some((c: { winning: boolean }) => c.winning)).toBe(true);
    }
  });
});

describe("unknown Appendix-B values are rendered, not omitted (SIG-UI-015)", () => {
  it("a null value renders as the literal 'unknown'", () => {
    expect(rowDisplayValue({ label: "x", value: null })).toBe("unknown");
    expect(rowDisplayValue({ label: "x", value: 30 })).toBe("30");
  });

  it("the rendered JSON keeps the null value and a 'unknown' display string", () => {
    const js = renderDossierJson(OKC_DOSSIER);
    const sections = js.sections as Array<{ id: string; rows: any[] }>;
    const cost = sections.find((s) => s.id === "cost_and_expiry")!;
    const annual = cost.rows.find((r) => r.label === "Contract value (annual)")!;
    expect(annual.value).toBeNull();
    expect(annual.display_value).toBe("unknown");
  });
});
