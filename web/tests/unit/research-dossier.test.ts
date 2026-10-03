// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The web mirror of `sig.research-dossier/1` / `sig.dossier-portfolio/1`
// (P32.17, SIG-DOS-001/002): the fixture exercises all six states, the rubric
// constants mirror exports.research_dossier exactly, and the data seam serves
// the portfolio identically in fixtures mode.
import { describe, it, expect } from "vitest";
import {
  ANSWER_STATES,
  COMPLETE_TOTAL,
  COMPLETE_MAX,
  REQUIRED_MINIMUM,
  DOSSIER_PORTFOLIO_SCHEMA,
  RESEARCH_DOSSIER_SCHEMA,
  emptyPortfolio,
  researchDossierSlug,
  researchDossierPath,
  researchDossierJsonPath,
  rubricGateLine,
  stateLabel,
} from "../../src/lib/research-dossier";
import {
  RESEARCH_DOSSIER_FIXTURE,
  RESEARCH_PORTFOLIO_FIXTURE,
} from "../../src/lib/research-dossier-fixture";
import { getResearchDossierPortfolio } from "../../src/lib/data";

describe("the six-state answer vocabulary (SIG-DOS-001)", () => {
  it("is exactly the export contract's vocabulary", () => {
    expect([...ANSWER_STATES].sort()).toEqual(
      ["derived", "disputed", "not_applicable", "supported", "unknown", "withheld"].sort(),
    );
  });

  it("the fixture exercises every state across its twelve answers", () => {
    expect(RESEARCH_DOSSIER_FIXTURE.answers).toHaveLength(12);
    const states = new Set(RESEARCH_DOSSIER_FIXTURE.answers.map((a) => a.state));
    for (const s of ANSWER_STATES) expect(states.has(s)).toBe(true);
  });

  it("every answer carries a legal state and a 0–3 score", () => {
    for (const a of RESEARCH_DOSSIER_FIXTURE.answers) {
      expect(ANSWER_STATES).toContain(a.state);
      expect(a.score).toBeGreaterThanOrEqual(0);
      expect(a.score).toBeLessThanOrEqual(3);
    }
  });

  it("an unknown carries a documented search basis + a precise follow-up", () => {
    const unknown = RESEARCH_DOSSIER_FIXTURE.answers.find((a) => a.state === "unknown")!;
    expect(unknown.search_basis?.sources_searched.length).toBeGreaterThan(0);
    expect(unknown.search_basis?.searched_at).toBeTruthy();
    expect(unknown.follow_ups[0]?.closing_condition).toBeTruthy();
  });

  it("a withheld answer renders no assertion value", () => {
    const w = RESEARCH_DOSSIER_FIXTURE.answers.find((a) => a.state === "withheld")!;
    expect(w.assertions).toHaveLength(0);
    expect(JSON.stringify(w)).not.toContain("confidential");
  });
});

describe("the rubric gate (mirrors exports.research_dossier)", () => {
  it("the constants match the Python contract", () => {
    expect(COMPLETE_TOTAL).toBe(28);
    expect(COMPLETE_MAX).toBe(36);
    expect(REQUIRED_MINIMUM).toEqual({ q1: 2, q5: 2, q7: 2, q8: 2 });
  });

  it("the gate line names the threshold and the floors", () => {
    const line = rubricGateLine(RESEARCH_DOSSIER_FIXTURE);
    expect(line).toContain("26/36");
    expect(line).toContain("28/36");
    expect(line).toContain("q1");
  });
});

describe("the portfolio surface", () => {
  it("carries the right schema ids", () => {
    expect(RESEARCH_PORTFOLIO_FIXTURE.schema).toBe(DOSSIER_PORTFOLIO_SCHEMA);
    expect(RESEARCH_DOSSIER_FIXTURE.schema).toBe(RESEARCH_DOSSIER_SCHEMA);
    expect(RESEARCH_DOSSIER_FIXTURE.kind).toBe("research_dossier");
  });

  it("the data seam returns the portfolio in fixtures mode", () => {
    const p = getResearchDossierPortfolio();
    expect(p.dossiers).toHaveLength(1);
    expect(p.summary.dossier_count).toBe(1);
  });

  it("the empty portfolio is the honest-absence form", () => {
    const p = emptyPortfolio();
    expect(p.dossiers).toHaveLength(0);
    expect(p.summary.dossier_count).toBe(0);
  });

  it("routing helpers produce the canonical paths", () => {
    expect(researchDossierSlug(RESEARCH_DOSSIER_FIXTURE)).toBe("okc-alpr");
    expect(researchDossierPath("okc-alpr")).toBe("/research-dossier/okc-alpr/");
    expect(researchDossierJsonPath("okc-alpr")).toBe("/research-dossier/okc-alpr.json");
  });

  it("stateLabel covers every state", () => {
    for (const s of ANSWER_STATES) expect(stateLabel(s).length).toBeGreaterThan(0);
  });
});

describe("the fact-to-capture ledger + conflicting claims", () => {
  it("every rendered ledger row binds a claim digest to a capture digest", () => {
    for (const r of RESEARCH_DOSSIER_FIXTURE.ledger) {
      if (r.state === "rendered") {
        expect(r.claim_digest).toBeTruthy();
        expect(r.capture_digest).toBeTruthy();
      }
    }
  });

  it("a withheld row keeps only the digest — no locator, no source", () => {
    const w = RESEARCH_DOSSIER_FIXTURE.ledger.find((r) => r.state === "withheld")!;
    expect(w.fact).toBe("(withheld)");
    expect(w.source_url).toBeNull();
    expect(w.locator).toBeNull();
  });

  it("the disputed answer keeps both competing values marked", () => {
    const q3 = RESEARCH_DOSSIER_FIXTURE.answers.find((a) => a.question === "q3")!;
    expect(q3.state).toBe("disputed");
    const values = q3.assertions.map((x) => x.value).sort();
    expect(values).toEqual([190, 299]);
    expect(q3.assertions.every((x) => x.conflicting)).toBe(true);
  });
});
