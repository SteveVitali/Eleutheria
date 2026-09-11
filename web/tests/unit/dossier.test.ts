// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The §39.2 dossier content contract (SIG-UI-010..015), tested on the pure logic in
// isolation from the Astro render. Mirrors the superseded P06.1 renderer's contract
// tests (tests/exports/test_dossier.py), now over the production TypeScript surface.
import { describe, expect, it } from "vitest";
import {
  SECTION_IDS,
  incompletenessBanner,
  nextDecisionDate,
  renderDossierJson,
  resolveTermination,
  rowDisplayValue,
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
  it("names the count of unresearched fields and the absence rule", () => {
    const banner = incompletenessBanner(OKC_DOSSIER);
    const n = unresearchedFieldCount(OKC_DOSSIER);
    expect(n).toBeGreaterThan(0);
    expect(banner).toContain(`${n} unresearched field`);
    expect(banner).toContain("absence of a row is not evidence of absence");
  });

  it("counts DISTINCT NOT_RESEARCHED fields, not 'no evidence found', deduped", () => {
    // NOT_RESEARCHED (subject, predicate) pairs in the fixture: sharing_partners
    // (a gap AND a row — counted once), unmapped_devices (gap), and
    // immigration_enforcement_config (row) = 3 distinct. The NO_EVIDENCE_FOUND
    // retention field (SIG looked) must NOT be counted as unresearched.
    expect(unresearchedFieldCount(OKC_DOSSIER)).toBe(3);
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
