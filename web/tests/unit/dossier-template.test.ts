import { describe, expect, it } from "vitest";
import {
  decisionsForDossier,
  NETWORK_SLOT_SECTIONS,
  templatePlan,
} from "../../src/lib/dossier-template";
import { DOSSIERS } from "../../src/lib/dossier-fixture";
import { SECTION_IDS } from "../../src/lib/dossier";
import type { Dossier } from "../../src/lib/dossier";

// P36.55 (VIZ-02, SIG-UI-069): the one-template composition contract — the
// twelve §39.2 sections in SIG-UI-010 order with the v2 blocks anchored
// where SIG-UI-069 names them; the network-slot map; the watch matching.

const dossier = (id: string): Dossier => {
  const d = DOSSIERS.find((x) => x.slug === id);
  if (!d) throw new Error(`no fixture dossier ${id}`);
  return d;
};

describe("templatePlan — the one dossier template (SIG-UI-069)", () => {
  for (const d of DOSSIERS) {
    it(`keeps the twelve §39.2 sections in order on ${d.slug}`, () => {
      const plan = templatePlan(d);
      const ids = plan
        .filter((u) => u.kind === "section")
        .map((u) => (u as { section: { section_id: string } }).section.section_id);
      expect(ids).toEqual([...SECTION_IDS]);
    });

    it(`anchors the v2 blocks at their SIG-UI-069 positions on ${d.slug}`, () => {
      const plan = templatePlan(d);
      const seq = plan.map((u) => (u.kind === "section" ? `sec:${u.section.section_id}` : u.kind));
      expect(seq[0]).toBe("header-strip");
      expect(seq[seq.length - 1]).toBe("rollup");
      // WTCF directly after where_the_hardware_is.
      expect(seq.indexOf("where-this-comes-from")).toBe(
        seq.indexOf("sec:where_the_hardware_is") + 1,
      );
      // Next decisions between timeline and what_we_dont_know.
      expect(seq.indexOf("next-decisions")).toBeGreaterThan(seq.indexOf("sec:timeline"));
      expect(seq.indexOf("next-decisions")).toBeLessThan(
        seq.indexOf("sec:what_we_dont_know"),
      );
      // Other public resources between what_we_dont_know and how_we_know_this.
      expect(seq.indexOf("other-public-resources")).toBe(
        seq.indexOf("sec:what_we_dont_know") + 1,
      );
      expect(seq.indexOf("other-public-resources")).toBe(
        seq.indexOf("sec:how_we_know_this") - 1,
      );
    });
  }

  it("every section and block appears exactly once", () => {
    const plan = templatePlan(dossier("oklahoma-city"));
    const kinds = plan.map((u) => u.kind);
    for (const k of ["header-strip", "where-this-comes-from", "next-decisions", "other-public-resources", "rollup"]) {
      expect(kinds.filter((x) => x === k)).toHaveLength(1);
    }
  });
});

describe("NETWORK_SLOT_SECTIONS — the Figs 2–5 anchors (typed until VIZ-01b)", () => {
  it("sits one slot on each of deployed/cost/access/policy (K6 §4.1)", () => {
    expect(Object.keys(NETWORK_SLOT_SECTIONS)).toEqual([
      "what_is_deployed",
      "cost_and_expiry",
      "who_else_can_see",
      "policy",
    ]);
    expect(NETWORK_SLOT_SECTIONS.what_is_deployed!.figure).toBe("fig-2");
    expect(NETWORK_SLOT_SECTIONS.cost_and_expiry!.figure).toBe("fig-3");
    expect(NETWORK_SLOT_SECTIONS.who_else_can_see!.figure).toBe("fig-4");
    expect(NETWORK_SLOT_SECTIONS.policy!.figure).toBe("fig-5");
  });
});

describe("decisionsForDossier — the place's watch items (SIG-WATCH-009)", () => {
  it("matches a dossier on its display name", () => {
    const items = [
      { jurisdiction: "Oklahoma City" },
      { jurisdiction: "Tulsa" },
      { jurisdiction: "Oklahoma City" },
    ];
    const d = dossier("oklahoma-city");
    expect(decisionsForDossier(items, d)).toHaveLength(2);
  });

  it("matches a keyed dossier on its name", () => {
    const items = [{ jurisdiction: "Harris County" }, { jurisdiction: "Travis County" }];
    const d = dossier("usa/tx/harris-county-48201");
    expect(decisionsForDossier(items, d)).toHaveLength(1);
  });
});
