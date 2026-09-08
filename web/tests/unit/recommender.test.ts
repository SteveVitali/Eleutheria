// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The §39.5a evidence recommender, tested on the pure logic (SIG-UI-027a/b/c). The
// load-bearing test is the neutrality guarantee (SIG-UI-027b): the ranking uses only
// directness, recency, and dispute status — never persuasiveness/sentiment/vote.
import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_RANKING_INPUTS,
  assertNeutralInputs,
  citationList,
  citationListText,
  recommendEvidence,
  scoreArtifact,
  scoreBreakdown,
} from "../../src/lib/recommender";
import type { EvidenceArtifact } from "../../src/lib/recommender";
import { DECISION_POINT, EVIDENCE_ARTIFACTS } from "../../src/lib/watch-evidence-fixture";
import { CONTESTED_MARKER } from "../../src/lib/epistemic";

const rank = () => recommendEvidence(EVIDENCE_ARTIFACTS, DECISION_POINT);
const idOrder = () => rank().map((r) => r.artifact.artifact_id);

describe("ranks by the §39.5a admissible inputs only (SIG-UI-027a)", () => {
  it("excludes a D6 (non-probative) artifact entirely (§10.5)", () => {
    expect(idOrder()).not.toContain("brochure:flock-marketing");
  });

  it("ranks a D1 contract above a D3 minutes record (directness)", () => {
    const order = idOrder();
    expect(order.indexOf("contract:okcpd-alpr")).toBeLessThan(order.indexOf("minutes:council-2025-03-25"));
  });

  it("ranks a retrievable capture above an otherwise-comparable link-rotted one", () => {
    const order = idOrder();
    // The August portal snapshot (retrievable, D2, C1, contested) beats the rotted D2/C4 one.
    expect(order.indexOf("snapshot:portal-2026-08")).toBeLessThan(order.indexOf("portal:rotted-2025"));
  });

  it("a fresher artifact ranks up when the other axes match", () => {
    const base: EvidenceArtifact = {
      artifact_id: "z-stale",
      subject_id: "s",
      title: "t",
      source: "x",
      artifact_type: "contract",
      directness: "D1",
      currency: "C4",
      touches_open_contradiction: false,
      answers_open_task: false,
      capture_status: "retrievable",
      permalink: "p",
      as_of: "2020-01-01",
    };
    const fresh: EvidenceArtifact = { ...base, artifact_id: "a-fresh", currency: "C1" };
    expect(scoreArtifact(fresh, DECISION_POINT)).toBeGreaterThan(scoreArtifact(base, DECISION_POINT));
  });

  it("an open contradiction and an open task each boost the score", () => {
    const base: EvidenceArtifact = {
      artifact_id: "b",
      subject_id: "s",
      title: "t",
      source: "x",
      artifact_type: "invoice",
      directness: "D3",
      currency: "C2",
      touches_open_contradiction: false,
      answers_open_task: false,
      capture_status: "retrievable",
      permalink: "p",
      as_of: "2026-01-01",
    };
    expect(scoreArtifact({ ...base, touches_open_contradiction: true }, DECISION_POINT)).toBeGreaterThan(
      scoreArtifact(base, DECISION_POINT),
    );
    expect(scoreArtifact({ ...base, answers_open_task: true }, DECISION_POINT)).toBeGreaterThan(
      scoreArtifact(base, DECISION_POINT),
    );
  });

  it("a contract + its amendment rank first for a renewal (artifact-type relevance)", () => {
    const order = idOrder();
    expect(order[0]).toBe("contract:okcpd-alpr"); // highest overall
    expect(order.slice(0, 3)).toContain("amendment:okcpd-alpr-1");
  });
});

describe("the neutrality guarantee (SIG-UI-027b)", () => {
  it("no admissible ranking artifact carries a forbidden signal", () => {
    for (const a of EVIDENCE_ARTIFACTS) {
      for (const key of Object.keys(a)) {
        expect(FORBIDDEN_RANKING_INPUTS as readonly string[]).not.toContain(key);
      }
    }
  });

  it("the score breakdown contains ONLY the six admissible axes", () => {
    const b = scoreBreakdown(EVIDENCE_ARTIFACTS[0]!, DECISION_POINT);
    expect(Object.keys(b).sort()).toEqual(
      ["artifact_type", "capture_status", "currency", "directness", "open_contradiction", "open_task"].sort(),
    );
  });

  it("rejects an artifact that smuggles in persuasiveness/sentiment/vote-effect", () => {
    for (const forbidden of ["persuasiveness", "sentiment", "predicted_vote"]) {
      const doctored = { ...EVIDENCE_ARTIFACTS[0]!, [forbidden]: 0.9 } as unknown as Record<string, unknown>;
      expect(() => assertNeutralInputs(doctored)).toThrow(/SIG-UI-027b/);
    }
  });

  it("recommendEvidence runs every artifact through the neutrality guard", () => {
    const poisoned = [
      { ...EVIDENCE_ARTIFACTS[0]!, sentiment: 1 } as unknown as EvidenceArtifact,
    ];
    expect(() => recommendEvidence(poisoned, DECISION_POINT)).toThrow(/SIG-UI-027b/);
  });
});

describe("exportable citation list with permalinks + as-of dates (SIG-UI-027c)", () => {
  it("every citation entry carries a permalink and an as-of date, in rank order", () => {
    const entries = citationList(rank());
    expect(entries.length).toBe(idOrder().length);
    for (const e of entries) {
      expect(e.permalink).toMatch(/^https?:\/\//);
      expect(e.as_of).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
    expect(entries.map((e) => e.artifact_id)).toEqual(idOrder());
  });

  it("the text export lists permalinks + as-of dates and marks contested artifacts (SIG-UI-008)", () => {
    const text = citationListText(rank(), DECISION_POINT);
    expect(text).toContain("As of 2026-07-01");
    expect(text).toContain("https://sig.example/evidence/");
    expect(text).toContain("directness, recency, and dispute status only");
    // The contested contract artifact carries the persistent marker in the export.
    expect(text).toContain(CONTESTED_MARKER.glyph);
  });
});
