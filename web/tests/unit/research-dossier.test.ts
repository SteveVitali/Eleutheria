// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The web mirror of `sig.research-dossier/1` / `sig.dossier-portfolio/1`
// (P32.17, SIG-DOS-001/002): the fixture exercises all six states, the rubric
// constants mirror exports.research_dossier exactly, and the data seam serves
// the portfolio identically in fixtures mode.
import { describe, it, expect } from "vitest";
import {
  ACQUISITION_LABELS,
  ANSWER_STATES,
  COMPLETE_TOTAL,
  COMPLETE_MAX,
  REQUIRED_MINIMUM,
  DOSSIER_PORTFOLIO_SCHEMA,
  RESEARCH_DOSSIER_SCHEMA,
  acquisitionLabel,
  assertNoFutureDisplayDates,
  derivedAcquisition,
  dossierLicenceText,
  dossierPermalink,
  emptyPortfolio,
  evidencePosture,
  researchDossierSlug,
  researchDossierPath,
  researchDossierJsonPath,
  reviewLabel,
  rubricGateLine,
  stateLabel,
  type ResearchAssertion,
  type ResearchDossier,
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

// --------------------------------------------------------------------------- //
// P34.35 — acquisition labels, review label, true dates, licence/permalink
// --------------------------------------------------------------------------- //

describe("the acquisition vocabulary (P34.35, DR-C4-03)", () => {
  it("the three display labels mirror the export contract", () => {
    expect(ACQUISITION_LABELS.live_capture).toBe("live capture");
    expect(ACQUISITION_LABELS.committed_transcription).toBe("committed transcription");
    expect(ACQUISITION_LABELS.stand_in).toBe("stand-in");
  });

  it("every fixture assertion carries a legal acquisition label", () => {
    for (const a of RESEARCH_DOSSIER_FIXTURE.answers) {
      for (const x of a.assertions) {
        expect(Object.values(ACQUISITION_LABELS)).toContain(acquisitionLabel(x));
      }
    }
    // the fixture exercises stand-in AND committed transcription honestly
    const all = RESEARCH_DOSSIER_FIXTURE.answers.flatMap((a) => a.assertions);
    const acq = new Set(all.map((x) => x.acquisition));
    expect(acq.has("stand_in")).toBe(true);
    expect(acq.has("committed_transcription")).toBe(true);
  });

  it("derives the label from the evidence record, never the URL", () => {
    const live: ResearchAssertion = {
      predicate: "p", value: 1, scope: {}, qualifiers: [],
      source_url: "https://example/doc", retrieved_date: "2026-10-01",
      access_mode: "document", capture_method: "html_text",
    };
    const transcription: ResearchAssertion = {
      predicate: "p", value: 1, scope: {}, qualifiers: [],
      capture_kind: "fixture_replay",
      access_mode: "committed_fixture", capture_method: "fixture_transcription",
    };
    const standIn: ResearchAssertion = {
      predicate: "p", value: 1, scope: {}, qualifiers: [],
      capture_kind: "stand-in", committed_at: "2026-09-27",
    };
    expect(acquisitionLabel(live)).toBe("live capture");
    expect(acquisitionLabel(transcription)).toBe("committed transcription");
    expect(acquisitionLabel(standIn)).toBe("stand-in");
    // fail-closed: no retrieval stamp and no marker → stand-in, never a capture
    expect(derivedAcquisition({})).toBe("stand_in");
  });

  it("a fixture dossier mixing the three postures discloses non-live evidence", () => {
    const mixed = structuredClone(RESEARCH_DOSSIER_FIXTURE);
    mixed.answers[0].assertions.push({
      predicate: "vendor", value: "Flock Safety", scope: {}, qualifiers: [],
      acquisition: "live_capture", retrieved_date: "2026-10-01", access_mode: "document",
    });
    const posture = evidencePosture(mixed);
    expect(posture.has).toBe(true);
    expect(posture.questions).toContain("q1");
  });

  it("a dossier resting only on live captures needs no disclosure", () => {
    const liveOnly = structuredClone(RESEARCH_DOSSIER_FIXTURE) as ResearchDossier;
    delete liveOnly.evidence_posture;
    for (const a of liveOnly.answers) {
      for (const x of a.assertions) {
        const rec = x as unknown as Record<string, unknown>;
        delete rec.acquisition;
        delete rec.extraction_method;
        x.capture_kind = "document";
        x.access_mode = "document";
        x.capture_method = "html_text";
        x.retrieved_date = "2026-10-01";
      }
    }
    const posture = evidencePosture(liveOnly);
    expect(posture.has).toBe(false);
    expect(posture.counts.stand_in ?? 0).toBe(0);
  });
});

describe("the review label (P34.35, F-153, DR-C4-04)", () => {
  it("derives from the recorded review_status — only completed may say 'reviewed'", () => {
    expect(reviewLabel("completed")).toBe("independently reviewed");
    expect(reviewLabel("pending")).toBe("independent review pending");
    expect(reviewLabel("not_run")).toBe("independent review not yet run");
    expect(reviewLabel("not_run")).not.toContain("reviewed");
    expect(reviewLabel("pending")).not.toContain("reviewed");
    // an unrecognised status echoes honestly, never claims a check
    expect(reviewLabel("bogus")).not.toContain("reviewed");
  });

  it("the fixture carries the derived label for its not_run record", () => {
    expect(RESEARCH_DOSSIER_FIXTURE.review_status).toBe("not_run");
    expect(RESEARCH_DOSSIER_FIXTURE.review_label).toBe("independent review not yet run");
  });
});

describe("licence, permalink, as-of (P34.35, C4 NEW-22/NEW-23)", () => {
  it("the dossier carries all three", () => {
    expect(RESEARCH_DOSSIER_FIXTURE.licence?.artifact).toBe("CC-BY-4.0");
    expect(dossierLicenceText(RESEARCH_DOSSIER_FIXTURE)).toContain("CC-BY-4.0");
    expect(RESEARCH_DOSSIER_FIXTURE.permalink).toBe(
      "https://surveillancegraph.org/research-dossier/okc-alpr/",
    );
    expect(dossierPermalink(RESEARCH_DOSSIER_FIXTURE)).toContain("/research-dossier/okc-alpr/");
    expect(RESEARCH_DOSSIER_FIXTURE.as_of.world).toBeTruthy();
    expect(RESEARCH_DOSSIER_FIXTURE.as_of.belief).toBeTruthy();
  });

  it("evidence_posture records which facts rest on stand-ins (F-16)", () => {
    const posture = RESEARCH_DOSSIER_FIXTURE.evidence_posture!;
    expect(posture.has_non_live).toBe(true);
    expect(posture.stand_in_facts.length).toBeGreaterThan(0);
    expect(posture.questions_with_non_live).toContain("q1");
  });
});

describe("the build-time date guard (P34.35, DR-C4-15)", () => {
  it("passes the honest fixture", () => {
    expect(() => assertNoFutureDisplayDates(RESEARCH_DOSSIER_FIXTURE)).not.toThrow();
  });

  it("a planted future displayed date fails the build", () => {
    const d = structuredClone(RESEARCH_DOSSIER_FIXTURE);
    d.answers[0].assertions[0].committed_at = "2999-01-01";
    expect(() => assertNoFutureDisplayDates(d)).toThrow(/build time|build clock/);
    const d2 = structuredClone(RESEARCH_DOSSIER_FIXTURE);
    d2.as_of.world = "2999-12-31";
    expect(() => assertNoFutureDisplayDates(d2)).toThrow();
    const d3 = structuredClone(RESEARCH_DOSSIER_FIXTURE);
    d3.search_log[0].searched_at = "2999-01-01";
    expect(() => assertNoFutureDisplayDates(d3)).toThrow();
    const d4 = structuredClone(RESEARCH_DOSSIER_FIXTURE);
    (d4.review as Record<string, unknown>).completed_at = "2999-01-01";
    expect(() => assertNoFutureDisplayDates(d4)).toThrow();
  });

  it("stated document dates are exempt — a future valid_from is a real-world claim", () => {
    const d = structuredClone(RESEARCH_DOSSIER_FIXTURE);
    d.answers[0].assertions[0].valid_from = "2999-01-01";
    expect(() => assertNoFutureDisplayDates(d)).not.toThrow();
  });
});
