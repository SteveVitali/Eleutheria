// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.

/**
 * P36.64 (SIG-UI-137/138; K14 §6.1/6.2): the golden place, persona paths and
 * example questions are release-bound — an example is emitted only when its
 * contract holds, and a missing golden dossier is an honest omission.
 */
import { describe, expect, it } from "vitest";
import { exampleQuestions, goldenPlace, personaPaths } from "../../src/lib/onboarding";
import { getDossiers } from "../../src/lib/data";

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const RAWKEY_RE = /(iso3166|us\.census|geoid|jkey|agency:|jurisdiction:)/i;

describe("goldenPlace", () => {
  it("selects a joined dossier: >=3 sources + a recorded disagreement + a decision", () => {
    const g = goldenPlace();
    expect(g).not.toBeNull();
    expect(g!.sources.length).toBeGreaterThanOrEqual(3);
    expect(g!.disagreement).not.toBeNull();
    expect(g!.disagreement!.sides.length).toBeGreaterThanOrEqual(1);
    expect("date" in g!.decision || "absence" in g!.decision).toBe(true);
    expect(g!.href).toMatch(/^\/dossier\/.+\/$/);
    expect(g!.facts.length).toBeGreaterThanOrEqual(3);
  });

  it("nulls honestly when no joined dossier exists", () => {
    const thin = getDossiers().map((d) => ({ ...d, source_families: [] }));
    expect(goldenPlace(thin)).toBeNull();
  });
});

describe("personaPaths", () => {
  it("offers one 3–4-step path per co-primary persona", () => {
    const paths = personaPaths();
    expect(paths.map((p) => p.id)).toEqual(["advocate", "journalist", "organizer"]);
    for (const p of paths) {
      expect(p.steps.length).toBeGreaterThanOrEqual(3);
      expect(p.steps.length).toBeLessThanOrEqual(4);
      for (const s of p.steps) {
        expect(s.href).toMatch(/^\//);
        expect(s.label).not.toMatch(UUID_RE);
      }
    }
  });
});

describe("exampleQuestions", () => {
  it("emits only contract-satisfying examples, ≤ the limit", () => {
    const ex = exampleQuestions(3);
    expect(ex.length).toBeGreaterThan(0);
    expect(ex.length).toBeLessThanOrEqual(3);
    for (const e of ex) {
      expect(e.href).toMatch(/^\//);
      expect(e.question).not.toMatch(UUID_RE);
      expect(e.question).not.toMatch(RAWKEY_RE);
    }
    // The disagreement example lands on the joined dossier's deployed section.
    const disagree = ex.find((e) => e.template === "disagree");
    expect(disagree).toBeDefined();
    expect(disagree!.href).toContain("#sec-what_is_deployed");
  });

  it("drops the disagreement example when no contested figure exists", () => {
    const clean = getDossiers().map((d) => ({
      ...d,
      sections: d.sections.map((s) => ({
        ...s,
        figures: (s.figures ?? []).map((f) => ({ ...f, contested: false })),
      })),
    }));
    const ex = exampleQuestions(6, clean);
    expect(ex.find((e) => e.template === "disagree")).toBeUndefined();
    expect(ex.find((e) => e.template === "unknown")).toBeDefined();
  });
});
