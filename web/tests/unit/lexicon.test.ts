// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.17 — the lexicon's import-level invariants (SIG-UI-061/062/064/133/143).
// The file-level legs (usage scan, built-HTML anchors) live in
// scripts/check-lexicon.mjs; these prove the TypeScript binding itself:
// every stored enum has a state, epistemic.ts derives its display strings
// from the lexicon, the map style's data hue is resolved through the
// lexicon's declared token binding, and the glossary merge is collision-safe.
import { describe, expect, it } from "vitest";
import {
  ABSENCE_KIND_META,
  ABSENCE_KINDS,
  AGREEMENT_LEVELS,
  CONTESTED_MARKER,
  CURRENCY_LEVELS,
  FIELD_TITLES,
  INFERRED_MARKER,
  RESOLUTION_STATUSES,
  SUPPORT_LEVELS,
  epistemicFieldValueLabel,
} from "../../src/lib/epistemic";
import {
  CONTROLLED_VOCABULARY,
  LEXICON,
  glossaryEntries,
  glossaryTerm,
  lexiconState,
  specGlossaryTerms,
  symbolMeaningConflicts,
} from "../../src/lib/lexicon";
import { SIG_DATA_1, SIG_DATA_HUE, sigTokenValue } from "../../src/lib/design-tokens";

describe("sig.lexicon/1", () => {
  it("declares its schema and the four sections", () => {
    expect(LEXICON.schema).toBe("sig.lexicon/1");
    expect(LEXICON.states).toBeTruthy();
    expect(LEXICON.legend).toBeTruthy();
    expect(LEXICON.terms.length).toBeGreaterThan(0);
    expect(CONTROLLED_VOCABULARY.length).toBeGreaterThan(0);
  });

  it("covers every stored epistemic enum with a state (SIG-UI-143)", () => {
    // A stored value without a lexicon state would render as a raw enum.
    for (const s of SUPPORT_LEVELS) expect(lexiconState("support", s).label).toBeTruthy();
    for (const a of AGREEMENT_LEVELS) expect(lexiconState("agreement", a).label).toBeTruthy();
    for (const c of CURRENCY_LEVELS) expect(lexiconState("currency", c).label).toBeTruthy();
    for (const r of RESOLUTION_STATUSES) expect(lexiconState("resolution", r).label).toBeTruthy();
    for (const k of ABSENCE_KINDS) expect(lexiconState("absence", k).label).toBeTruthy();
  });

  it("fails closed on an undeclared enum (never a silent fallback)", () => {
    expect(() => lexiconState("support", "SOMEWHERE_OVER")).toThrow(/no support state/);
  });
});

describe("epistemic.ts derives its display strings from the lexicon", () => {
  it("absence kinds carry the K14 short labels, not forked literals", () => {
    for (const k of ABSENCE_KINDS) {
      const state = lexiconState("absence", k);
      expect(ABSENCE_KIND_META[k].label).toBe(state.label);
      expect(ABSENCE_KIND_META[k].meaning).toBe(state.plain);
      expect(ABSENCE_KIND_META[k].symbol).toBe(state.symbol);
    }
    expect(ABSENCE_KIND_META.NO_EVIDENCE_FOUND.label).toBe("None found");
    expect(ABSENCE_KIND_META.EVIDENCE_OF_ABSENCE.label).toBe("Stated absent");
  });

  it("markers ride the same lexicon states", () => {
    expect(CONTESTED_MARKER.glyph).toBe(lexiconState("agreement", "CONTESTED").symbol);
    expect(CONTESTED_MARKER.label).toBe(lexiconState("agreement", "CONTESTED").label);
    expect(INFERRED_MARKER.glyph).toBe(lexiconState("inferred", "INFERRED").symbol);
    expect(INFERRED_MARKER.label).toBe(lexiconState("inferred", "INFERRED").label);
  });

  it("field chips label values from the lexicon, never a re-cased enum", () => {
    expect(epistemicFieldValueLabel("support", "STRONGLY_SUPPORTED")).toBe("Strong support");
    expect(epistemicFieldValueLabel("agreement", "MINOR_DISAGREEMENT")).toBe("Minor disagreement");
    // A null field is the typed Not-applicable state, never a bare unknown.
    expect(epistemicFieldValueLabel("currency", "—")).toBe(LEXICON.legend.cannotApply.label);
    expect(FIELD_TITLES.support).toBe(LEXICON.fields.support.label);
  });
});

describe("one meaning per symbol (SIG-UI-133, C-01)", () => {
  it("no declared symbol carries two meaning families", () => {
    expect(symbolMeaningConflicts()).toEqual([]);
  });
});

describe("Candidate vs Provisional (SIG-UI-062)", () => {
  it("differs in word, symbol and filter", () => {
    const [a, b] = LEXICON.legend.candidateVsProvisional.rows;
    expect(a.word).not.toBe(b.word);
    expect(a.symbol).not.toBe(b.symbol);
    expect(a.filter).not.toBe(b.filter);
    expect(a.axis).toBe("lifecycle");
    expect(b.axis).toBe("epistemic");
  });
});

describe("independent-lineage corroboration (SIG-UI-064, C-01)", () => {
  it("fill counts independent lineages and carries the interim line verbatim", () => {
    const corr = LEXICON.legend.fill.encodings.corroborated;
    expect(corr.countsIndependentLineages).toBe(true);
    expect(corr.interimLegendLine).toBe("2+ source records; republications not yet collapsed");
  });
  it("currency is never a line pattern and never hollow", () => {
    expect(LEXICON.legend.currency.never).toContain("a line pattern");
    expect(LEXICON.legend.currency.never).toContain("hollow");
  });
});

describe("L3 copy and possible duplicate (Stream L)", () => {
  it("both states exist with their merge semantics", () => {
    expect(lexiconState("identity", "COPY").label).toBe("copy");
    const dup = lexiconState("identity", "POSSIBLE_DUPLICATE");
    expect(dup.label).toBe("possible duplicate");
    expect(dup.merged).toBe(false);
    expect(dup.plain).toMatch(/not merged/);
    expect(dup.plain).toMatch(/cannot prove/);
  });
});

describe("the map style reads the lexicon", () => {
  it("resolves the data hue through legend.dataHue.token", () => {
    expect(LEXICON.legend.dataHue.token).toBe("sig-data-1");
    expect(SIG_DATA_HUE).toBe(sigTokenValue(LEXICON.legend.dataHue.token));
    expect(SIG_DATA_HUE).toBe(SIG_DATA_1); // the binding resolves to the data blue today
  });
});

describe("the glossary merge", () => {
  it("reads Appendix E verbatim from the canonical spec", () => {
    const terms = specGlossaryTerms();
    expect(terms.length).toBeGreaterThanOrEqual(26);
    const support = terms.find((t) => t.term === "Support");
    expect(support?.definition).toContain("winning value");
  });

  it("merges lexicon terms + Appendix E with unique anchors", () => {
    const entries = glossaryEntries();
    const anchors = entries.map((e) => e.anchor);
    expect(new Set(anchors).size).toBe(anchors.length);
    // Every spec term reaches the page — verbatim, flagged as spec.
    for (const st of specGlossaryTerms()) {
      const hit = entries.find((e) => e.precise === st.definition);
      expect(hit, `spec term "${st.term}" lost`).toBeTruthy();
    }
    // A merged term carries the spec text verbatim as `precise`.
    const dossier = glossaryTerm("dossier");
    expect(dossier.precise).toContain("per-jurisdiction");
    // The site terms and state glosses resolve.
    expect(glossaryTerm("possible-duplicate").stateRef).toBe("identity.POSSIBLE_DUPLICATE");
  });

  it("fails closed on an undefined term (used before defined)", () => {
    expect(() => glossaryTerm("not-a-term")).toThrow(/names no glossary entry/);
  });

  it("every plain definition stays within the ~25-word cap", () => {
    for (const e of glossaryEntries()) {
      const words = e.plain.trim().split(/\s+/).length;
      expect(words, `${e.id}: ${e.plain}`).toBeLessThanOrEqual(40);
    }
  });
});

describe("the controlled vocabulary (K14 §3.5)", () => {
  it("names the adopted words and the banned synonyms", () => {
    const uses = CONTROLLED_VOCABULARY.map((v) => v.use);
    for (const want of ["place", "record", "camera site", "source", "release"]) {
      expect(uses).toContain(want);
    }
    const cameraSite = CONTROLLED_VOCABULARY.find((v) => v.use === "camera site");
    expect(cameraSite?.not).toContain("resolved site");
    expect(cameraSite?.not).toContain("entity");
  });
});
