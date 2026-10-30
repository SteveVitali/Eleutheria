// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.23 (UXK14-3b, SIG-UI-083/086/151): the component-kit-B pure contracts —
// `sig.callout/1`, the absence chip's action vocabulary and the contested/
// unresolved marker levels — tested as data, independent of markup: closed
// vocabularies fail closed (SIG-ENG-042), every visible label comes from the
// lexicon or a batch-tracked string (SIG-UI-143, B-2), and the one-texture /
// no-colour-alone channels hold.
import { describe, it, expect } from "vitest";
import {
  ABSENCE_HELP_BATCH_ID,
  ABSENCE_HELP_LABEL,
  ABSENCE_KINDS,
  ABSENCE_KIND_META,
  CONTESTED_AGREEMENTS,
  contradictionRange,
} from "../../src/lib/epistemic";
import { CALLOUT_KINDS, calloutSpec } from "../../src/lib/callouts";
import { lexiconState } from "../../src/lib/lexicon";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SRC = fileURLToPath(new URL("../../src/", import.meta.url));
const readSrc = (rel: string) => readFileSync(`${SRC}${rel}`, "utf-8");

describe("the contested marker levels (SIG-UI-008, K14 §3.4)", () => {
  it("the marker renders exactly the two contested agreements", () => {
    expect(CONTESTED_AGREEMENTS).toEqual(["CONTESTED", "IRRECONCILABLE"]);
    for (const agreement of CONTESTED_AGREEMENTS) {
      const state = lexiconState("agreement", agreement);
      // Every marker level resolves a visible label and a glyph — the two
      // non-colour channels that tell the levels apart.
      expect(state.label.length).toBeGreaterThan(0);
      expect(state.symbol).toBe("≠");
    }
    // The levels name themselves differently in text.
    expect(lexiconState("agreement", "CONTESTED").label).toBe("Contested");
    expect(lexiconState("agreement", "IRRECONCILABLE").label).toBe("Unresolved");
  });

  it("the component distinguishes the levels by attribute and style hook", () => {
    const source = readSrc("components/ContestedMarker.astro");
    expect(source).toContain('data-agreement={agreement}');
    expect(source).toContain("sig-contested--unresolved");
    // J3: the marker can link to the both-sides surface — a plain href,
    // resolved through withBase() unless it is already an anchor.
    expect(source).toContain("withBase(target)");
  });
});

describe("the contradiction range (SIG-UI-009, K14 §4.6)", () => {
  it("computes the same min/max contract kit A's data layer declared", () => {
    const claims = [
      { claimId: "a", value: 38, source: "s1", tier: "W3", date: "d", documentUrl: "/" },
      { claimId: "b", value: 42, source: "s2", tier: "W6", date: "d", documentUrl: "/" },
    ];
    const range = contradictionRange(claims);
    expect(range.min).toBe(38);
    expect(range.max).toBe(42);
    expect(() => contradictionRange([])).toThrow();
  });

  it("the component labels every plotted point and names the agreement level", () => {
    const source = readSrc("components/ContradictionRange.astro");
    // "One labelled dot per claim" — the ordinal text rides each plotted point.
    expect(source).toContain("sig-range__point-label");
    expect(source).toContain("text-anchor");
    // The unresolved form is a named variant, never a different contract.
    expect(source).toContain("sig-range--unresolved");
    expect(source).toContain('data-agreement={agreement}');
    // The different-quantity note stays (§29.1).
    expect(source).toContain("differentQuantityNote");
  });
});

describe("the absence chip (SIG-UI-007, K14 §4.6, O4)", () => {
  it("carries all four kinds with symbol + label + meaning", () => {
    expect(ABSENCE_KINDS).toEqual([
      "NOT_RESEARCHED",
      "NO_EVIDENCE_FOUND",
      "EVIDENCE_OF_ABSENCE",
      "UNRESOLVED",
    ]);
    for (const kind of ABSENCE_KINDS) {
      const meta = ABSENCE_KIND_META[kind];
      // Symbol + label + plain meaning + taskability — the chip's four channels.
      expect(meta.symbol.length).toBeGreaterThan(0);
      expect(meta.label.length).toBeGreaterThan(0);
      expect(meta.meaning.length).toBeGreaterThan(0);
      expect(meta.taskable).toBe(true);
    }
  });

  it("'Help find it' is a batch-tracked sentence, never a mock task page (B-2)", () => {
    expect(ABSENCE_HELP_LABEL).toBe("Help find it ›");
    expect(ABSENCE_HELP_BATCH_ID).toBe("CK-61");
    const source = readSrc("components/AbsenceChip.astro");
    // The action renders the shared sentence under its batch id — and defaults
    // to the research queue, the honest "gap becomes work" surface.
    expect(source).toContain("data-copy={ABSENCE_HELP_BATCH_ID}");
    expect(source).toContain('withBase("research-queue/")');
    // Never the retired generated-task fixture route (P34.12 stands).
    expect(source).not.toContain("/task/new/");
  });
});

describe("sig.callout/1 — the closed callout vocabulary (K14 §4.6)", () => {
  it("declares exactly note · caution · known_issue", () => {
    expect(CALLOUT_KINDS).toEqual(["note", "caution", "known_issue"]);
  });

  it("every kind resolves a batch-tracked label", () => {
    const expected: Record<string, [string, string]> = {
      note: ["Note", "CK-62"],
      caution: ["Caution", "CK-63"],
      known_issue: ["Known issue", "CK-64"],
    };
    for (const kind of CALLOUT_KINDS) {
      const spec = calloutSpec(kind);
      expect(spec.kind).toBe(kind);
      expect([spec.label, spec.batchId]).toEqual(expected[kind]);
    }
  });

  it("fails closed on an unknown kind (SIG-ENG-042)", () => {
    expect(() => calloutSpec("warning")).toThrow(/unknown callout kind/);
    expect(() => calloutSpec("")).toThrow();
    expect(() => calloutSpec("NOTE")).toThrow();
  });
});

describe("the one provenance panel (SIG-UI-083, UXR-33)", () => {
  it("the shell mounts the one renderer; the panel rules ride the global sheet", () => {
    const shell = readSrc("components/ProvenancePanelShell.astro");
    expect(shell).toContain('from "./ProvenancePanel"');
    // The shell never re-implements the contract — it is markup-thin.
    expect(shell).not.toContain("data-provenance-panel");
    // The panel's rules live on the GLOBAL epistemic sheet — a dedicated
    // per-module stylesheet import resolves through the shared facade chunk
    // and lands an extra render-blocking <link> on pages that never mount
    // the panel (fix-arc 12: the leak regressed T1 LCP ~11 ms over the
    // ratified 1,500 ms bound). Neither module may import one.
    expect(shell).not.toContain('import "../styles/provenance.css"');
    const tsx = readSrc("components/ProvenancePanel.tsx");
    expect(tsx).not.toContain('import "../styles/provenance.css"');
    const css = readSrc("styles/epistemic.css");
    expect(css).toContain(".provenance-panel");
  });
});

describe("the neutral incompleteness banner (SIG-UI-012, K14 NEW-2)", () => {
  it("keeps the neutral styling — never the contested hue", () => {
    const css = readSrc("styles/epistemic.css");
    const banner = css.match(/\.sig-incompleteness \{([\s\S]*?)\}/);
    expect(banner).not.toBeNull();
    // The banner must not pull the reserved raspberry (K14 NEW-2 — a count
    // of gaps is not a disagreement).
    expect(banner![1]).not.toContain("epi-disagree");
  });
});
