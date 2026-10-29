// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P36.14 / SIG-RECON-052 (§30.4): the L4 inference marker contract on the web
// side — the typed field pair, the marker's non-colour channels, and the
// epistemic class it styles — plus the design-token guard for its ink.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { CONTESTED_MARKER, INFERRED_MARKER, isInferredRecord } from "../../src/lib/epistemic";
import { renderDossierJson } from "../../src/lib/dossier";
import { DOSSIERS } from "../../src/lib/dossier-fixture";

const CSS_PATH = fileURLToPath(new URL("../../src/styles/epistemic.css", import.meta.url));
const css = readFileSync(CSS_PATH, "utf8");

describe("the L4 inference marker (SIG-RECON-052)", () => {
  it("the marker predicate requires BOTH fields — a half-marker is unmarked", () => {
    expect(isInferredRecord({ inferred: true, layer: "L4" })).toBe(true);
    expect(isInferredRecord({ inferred: true })).toBe(false);
    expect(isInferredRecord({ layer: "L4" })).toBe(false);
    expect(isInferredRecord({ inferred: false, layer: "L4" })).toBe(false);
    expect(isInferredRecord({})).toBe(false);
    expect(isInferredRecord(null)).toBe(false);
    expect(isInferredRecord(undefined)).toBe(false);
  });

  it("carries a non-colour channel — glyph AND text label (SIG-UI-005)", () => {
    expect(INFERRED_MARKER.glyph).toBe("◈");
    expect(INFERRED_MARKER.label).toBe("Inferred");
    expect(INFERRED_MARKER.label).not.toBe(CONTESTED_MARKER.label);
    expect(INFERRED_MARKER.glyph).not.toBe(CONTESTED_MARKER.glyph);
    expect(INFERRED_MARKER.meaning.length).toBeGreaterThan(0);
    expect(INFERRED_MARKER.cssClass).toBe("sig-inferred");
  });

  it("the epistemic class exists in epistemic.css and its token is non-green", () => {
    expect(css).toContain(".sig-inferred");
    expect(css).toContain("--sig-epi-inferred-ink");
    const m = /--sig-epi-inferred-ink:\s*hsl\(\s*([\d.]+)deg/.exec(css);
    expect(m, "inferred ink token must be hsl()").not.toBeNull();
    const hue = Number(m![1]);
    expect(hue < 75 || hue > 165, `${hue}deg must be outside the green band`).toBe(true);
  });

  it("the fixture dossier carries a marked row and the JSON twin emits it", () => {
    const okc = DOSSIERS.find((d) => d.slug === "oklahoma-city")!;
    const marked = okc.sections.flatMap((s) => s.rows ?? []).filter((r) => isInferredRecord(r));
    expect(marked.length).toBeGreaterThan(0);
    const json = renderDossierJson(okc);
    const rows = (json["sections"] as { rows?: Record<string, unknown>[] }[]).flatMap(
      (s) => s.rows ?? [],
    );
    const jsonMarked = rows.filter((r) => r["inferred"] === true && r["layer"] === "L4");
    expect(jsonMarked.length).toBeGreaterThan(0);
  });

  it("an unmarked row emits no marker fields — removing the flag fails the contract", () => {
    const okc = DOSSIERS.find((d) => d.slug === "oklahoma-city")!;
    const json = renderDossierJson(okc);
    const rows = (json["sections"] as { rows?: Record<string, unknown>[] }[]).flatMap(
      (s) => s.rows ?? [],
    );
    // Every observed row carries NEITHER field — the marker is never implied.
    const unmarked = rows.filter((r) => r["inferred"] !== true);
    expect(unmarked.length).toBeGreaterThan(0);
    for (const r of unmarked) {
      expect(r["layer"]).toBeUndefined();
      expect(isInferredRecord(r as { inferred?: boolean; layer?: string })).toBe(false);
    }
  });
});
