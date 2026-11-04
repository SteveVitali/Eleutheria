// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.65 (UXK14-11; K14 §6.3) — the per-page reading key's contract: the key
// lists ONLY the symbols the page's model carries (never a symbol the page
// lacks, never missing one it has), every label/meaning comes from the ONE
// lexicon, and every linked term resolves in the merged glossary (fail closed).
import { describe, it, expect } from "vitest";
import { dossierReadingKey } from "../../src/lib/reading-key";
import type { ReadingKeyItem } from "../../src/lib/reading-key";
import { glossaryTerm } from "../../src/lib/lexicon";
import { getDossiers } from "../../src/lib/data";
import type { Dossier, Figure } from "../../src/lib/dossier";

function baseDossier(overrides: Partial<Dossier>): Dossier {
  return {
    schema: "sig.dossier/2",
    jurisdiction: "Testville",
    subject_label: "Testville",
    slug: "testville",
    source_families: ["a", "b", "c"],
    gaps: [],
    sections: [],
    ...overrides,
  } as Dossier;
}

const figure = (over: Partial<Figure>): Figure =>
  ({
    key: "f1",
    label: "Devices",
    value: 42,
    support: "STRONGLY_SUPPORTED",
    evidenceCount: 2,
    contested: false,
    reconciliation: {
      rule: "R",
      winningClaimId: "c1",
      claims: [
        { claimId: "c1", value: 42, source: "s", tier: "W2", date: "2026-01-01", documentUrl: "https://x" },
      ],
    },
    ...over,
  }) as Figure;

describe("dossierReadingKey (K14 §6.3 — only the symbols present)", () => {
  it("is never empty on a figure-bearing dossier and always lists support", () => {
    const d = baseDossier({ sections: [{ section_id: "what_is_deployed", figures: [figure({})] }] });
    const ids = dossierReadingKey(d).map((i) => i.id);
    expect(ids).toContain("support");
  });

  it("lists contested only when a contested figure or the disagreement pair is present", () => {
    const none = baseDossier({ sections: [{ section_id: "s", figures: [figure({})] }] });
    expect(dossierReadingKey(none).map((i) => i.id)).not.toContain("contested");
    const contested = baseDossier({ sections: [{ section_id: "s", figures: [figure({ contested: true })] }] });
    expect(dossierReadingKey(contested).map((i) => i.id)).toContain("contested");
    const pair = baseDossier({
      sections: [{ section_id: "s", figures: [figure({})] }],
      disagreements: { declared_here_located_elsewhere: 1 },
    });
    expect(dossierReadingKey(pair).map((i) => i.id)).toContain("contested");
  });

  it("lists unresolved only when a figure has no winning claim", () => {
    const unres = baseDossier({
      sections: [{ section_id: "s", figures: [figure({ reconciliation: { rule: "R", winningClaimId: "gone", claims: [{ claimId: "c1", value: 42, source: "s", tier: "W2", date: "d", documentUrl: "u" }] } })] }],
    });
    expect(dossierReadingKey(unres).map((i) => i.id)).toContain("unresolved");
  });

  it("lists exactly the absence kinds the page carries — from gaps and absence rows", () => {
    const d = baseDossier({
      gaps: [{ kind: "NOT_RESEARCHED", label: "g", subject_id: "s", predicate_id: "p" }],
      sections: [
        { section_id: "s", rows: [{ label: "r", value: null, absence: "NO_EVIDENCE_FOUND" }] },
      ],
    });
    const ids = dossierReadingKey(d).map((i) => i.id);
    expect(ids).toContain("absence-not_researched");
    expect(ids).toContain("absence-no_evidence_found");
    expect(ids).not.toContain("absence-evidence_of_absence");
    expect(ids).not.toContain("absence-unresolved");
  });

  it("lists inferred and withheld only when the rows carry them", () => {
    const d = baseDossier({
      sections: [
        {
          section_id: "s",
          rows: [
            { label: "a", value: 1, inferred: true, layer: "L4" },
            { label: "b", value: null, withheld: true },
          ],
        },
      ],
    });
    const ids = dossierReadingKey(d).map((i) => i.id);
    expect(ids).toContain("inferred");
    expect(ids).toContain("withheld");
    const plain = baseDossier({ sections: [{ section_id: "s", rows: [{ label: "a", value: 1 }] }] });
    const pids = dossierReadingKey(plain).map((i) => i.id);
    expect(pids).not.toContain("inferred");
    expect(pids).not.toContain("withheld");
  });

  it("every item's term resolves in the glossary and every item is fully labelled", () => {
    const dossiers = getDossiers();
    for (const d of dossiers) {
      for (const item of dossierReadingKey(d) as ReadingKeyItem[]) {
        expect(item.label.length, item.id).toBeGreaterThan(0);
        expect(item.plain.length, item.id).toBeGreaterThan(0);
        if (item.term !== null) expect(() => glossaryTerm(item.term!), item.id).not.toThrow();
      }
    }
    expect(dossiers.length).toBeGreaterThan(0);
  });
});
