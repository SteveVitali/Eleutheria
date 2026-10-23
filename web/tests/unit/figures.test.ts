// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.37 (R11-K13-TX-09, SIG-TRANSP-013, J3 §5.4, UXR-34): the figure contract
// unit tests — the spec validation, the manifest-artifact gate, the
// link-or-named-absence target rule, and the bare-numeral pattern the build
// check enforces. The pattern lives in TWO files that must never drift:
// src/lib/dossier-figures.ts detects numerals a page should wrap;
// scripts/check-figures.mjs fails the build on the ones it missed.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  artifactHref,
  classTargets,
  defineFigures,
  isManifestArtifact,
  type FigureSpec,
} from "../../src/lib/figures";
import {
  dossierFigureSpecs,
  firstNumeral,
  MATERIAL_NUMERAL_PATTERN,
  textHasMaterialNumeral,
} from "../../src/lib/dossier-figures";
import { getDossierArtifactRef, getDossiers } from "../../src/lib/data";

const CHECK_FIGURES = fileURLToPath(new URL("../../scripts/check-figures.mjs", import.meta.url));

function baseSpec(overrides: Partial<FigureSpec> = {}): FigureSpec {
  return {
    id: "total",
    class: "headline",
    value: 42,
    artifact: "web/coverage.json",
    pointer: "/metrics/0/value",
    definition: "#coverage-metrics-heading",
    href: "artifact/web/coverage.json",
    breakdown: "#fig-total",
    targets: [{ kind: "record list", label: "record list", absent: "not published" }],
    ...overrides,
  };
}

describe("MATERIAL_NUMERAL_PATTERN — pinned byte-identical to the build check", () => {
  it("matches the MATERIAL_NUMERAL_RE source in scripts/check-figures.mjs", () => {
    const src = readFileSync(CHECK_FIGURES, "utf-8");
    const m = /MATERIAL_NUMERAL_RE = new RegExp\(\s*("(?:[^"\\]|\\.)*")/.exec(src);
    expect(m, "check-figures.mjs must declare MATERIAL_NUMERAL_RE").not.toBeNull();
    expect(JSON.parse(m![1])).toBe(MATERIAL_NUMERAL_PATTERN);
  });

  it("flags plain counts, comma-grouped counts and counts in prose", () => {
    expect(firstNumeral("147 devices")).toBe("147");
    expect(firstNumeral("all ≈8,088 currently public rows")).toBe("8,088");
    expect(firstNumeral("1,234,567 rows")).toBe("1,234,567");
    expect(textHasMaterialNumeral("Unresolved — not 'currently shares with 147'")).toBe(true);
  });

  it("a trailing prose comma is NOT part of the numeral (HTTP 429, 503 or 504)", () => {
    const re = new RegExp(MATERIAL_NUMERAL_PATTERN, "g");
    const tokens = [...("An HTTP 429, 503 or 504 answer".matchAll(re))].map((m) => m[0]);
    expect(tokens).toEqual(["429", "503", "504"]);
  });

  it("ignores identifiers — citations, versions, dates, sections, ratios", () => {
    expect(textHasMaterialNumeral("per RFC 9309. Under a recorded")).toBe(false);
    expect(textHasMaterialNumeral("osm/1.0.0")).toBe(false);
    expect(textHasMaterialNumeral("2026-08-20")).toBe(false);
    expect(textHasMaterialNumeral("(§12.2, SIG-TIME-005)")).toBe(false);
    expect(textHasMaterialNumeral("95% lower bound")).toBe(false);
    expect(textHasMaterialNumeral("score 0.714")).toBe(true); // a decimal IS material
  });
});

describe("defineFigures — the page registry contract (UXR-34, J3 §5.4)", () => {
  it("accepts a well-formed spec against the committed artifact list", () => {
    expect(() => defineFigures("test", [baseSpec()])).not.toThrow();
  });

  it("fails the build on a duplicate figure id", () => {
    expect(() => defineFigures("test", [baseSpec(), baseSpec()])).toThrow(/duplicate id "total"/);
  });

  it("fails the build on a non-manifest-listed artifact", () => {
    expect(() =>
      defineFigures("test", [baseSpec({ artifact: "web/not-a-real-artifact.json" })]),
    ).toThrow(/not a manifest-listed artifact path/);
  });

  it("honours the export-manifest override (the listed argument)", () => {
    expect(() =>
      defineFigures("test", [baseSpec({ artifact: "web/x.json" })], ["web/x.json"]),
    ).not.toThrow();
  });

  it("admits compartment row streams by pattern", () => {
    expect(isManifestArtifact("odbl/statements.jsonl")).toBe(true);
    expect(isManifestArtifact("cc_by/record_claims.jsonl")).toBe(true);
    expect(isManifestArtifact("statements.jsonl")).toBe(false);
  });

  it("admits P35.45 per-dossier artifacts by pattern — index excluded", () => {
    expect(isManifestArtifact("web/dossiers/usa.json")).toBe(true);
    expect(isManifestArtifact("web/dossiers/usa/ca.json")).toBe(true);
    expect(isManifestArtifact("web/dossiers/usa/ca/verdin-county-06037.json")).toBe(true);
    // The index document carries no dossier record — never a figure target.
    expect(isManifestArtifact("web/dossiers/index.json")).toBe(true); // listed path
    expect(isManifestArtifact("web/dossier_sources/usa.json")).toBe(false);
    expect(isManifestArtifact("web/dossiers.json")).toBe(true); // the v1 monolith
  });

  it("pins PER_DOSSIER_RE byte-identical to the build check's copy", () => {
    const src = readFileSync(CHECK_FIGURES, "utf-8");
    const m = /PER_DOSSIER_RE = (\/.+\/[gimsuy]*)/.exec(src);
    expect(m, "check-figures.mjs must declare PER_DOSSIER_RE").not.toBeNull();
    expect(m![1]).toBe("/^web\\/dossiers\\/[a-z0-9-]+(\\/[a-z0-9-]+)*\\.json$/");
  });

  it("rejects a pointer that is not a JSON pointer", () => {
    expect(() => defineFigures("test", [baseSpec({ pointer: "metrics/0" })])).toThrow(
      /not a JSON pointer/,
    );
  });

  it("rejects a non-slug id", () => {
    expect(() => defineFigures("test", [baseSpec({ id: "Total_Count" })])).toThrow(
      /lowercase slug/,
    );
  });

  it("enforces the link-or-named-absence rule — never both, never neither", () => {
    const both = baseSpec({
      targets: [{ kind: "k", label: "l", href: "/x/", absent: "missing" }],
    });
    expect(() => defineFigures("test", [both])).toThrow(/exactly one of href/);
    const neither = baseSpec({ targets: [{ kind: "k", label: "l" }] });
    expect(() => defineFigures("test", [neither])).toThrow(/exactly one of href/);
  });

  it("requires a visible source link and a breakdown target", () => {
    expect(() => defineFigures("test", [baseSpec({ href: "" })])).toThrow(/source link/);
    expect(() => defineFigures("test", [baseSpec({ breakdown: "" })])).toThrow(/breakdown/);
  });
});

describe("the served artifact route stays contained (SIG-UI-020 snapshot rule)", () => {
  it("artifactHref emits a relative path — the base join owns the prefix", () => {
    expect(artifactHref("web/coverage.json")).toBe("artifact/web/coverage.json");
    expect(artifactHref("web/coverage.json").startsWith("/")).toBe(false);
  });

  it("every class resolves a target set without dead links", () => {
    for (const cls of ["headline", "dossier", "per_source", "freshness", "contradiction"] as const) {
      const targets = classTargets(cls, { sourceId: "src-x" });
      for (const t of targets) {
        expect(t.kind.trim()).not.toBe("");
        expect(t.href === undefined || t.absent === undefined).toBe(true);
      }
    }
  });
});

describe("dossierFigureSpecs — the dossier registry over fixture dossiers", () => {
  const dossiers = getDossiers();

  it("every fixture dossier resolves an artifact ref and a valid registry", () => {
    expect(dossiers.length).toBeGreaterThan(0);
    for (const d of dossiers) {
      const ref = getDossierArtifactRef(d.slug);
      expect(ref, `dossier ${d.slug} has no artifact ref`).not.toBeNull();
      const specs = dossierFigureSpecs(d, "page", {
        ref,
        recordList: null,
        provenanceHref: "#hwkt-heading",
        artifactHref: artifactHref(ref!.artifact),
      });
      // The registry validates and the ids are unique (defineFigures throws otherwise).
      const validated = defineFigures(`test/${d.slug}`, specs);
      expect(validated.length).toBeGreaterThan(0);
      // Pointers name positions inside the artifact record, never the render index.
      for (const s of validated) {
        expect(s.pointer.startsWith(`/${ref!.index}`)).toBe(true);
        expect(s.artifact).toBe(ref!.artifact);
      }
      // The print variant re-runs the same registry without id collisions.
      const printSpecs = dossierFigureSpecs(d, "print", {
        ref,
        recordList: null,
        provenanceHref: null,
        artifactHref: artifactHref(ref!.artifact),
      });
      expect(() => defineFigures(`test/${d.slug}/print`, printSpecs)).not.toThrow();
    }
  });

  it("covers a numeral carried only in a row NOTE (the 'shares with 147' case)", () => {
    const okc = dossiers.find((d) => d.slug === "oklahoma-city");
    expect(okc).not.toBeUndefined();
    const ref = getDossierArtifactRef(okc!.slug)!;
    const specs = dossierFigureSpecs(okc!, "page", {
      ref,
      recordList: null,
      provenanceHref: "#hwkt-heading",
      artifactHref: artifactHref(ref.artifact),
    });
    // At least one row's spec is driven by the note numeral, not the value.
    const noteDriven = specs.find((s) => s.id.startsWith("row-") && s.value === "147");
    expect(noteDriven, "the '147' note numeral must be registered as a figure").not.toBeUndefined();
  });
});
