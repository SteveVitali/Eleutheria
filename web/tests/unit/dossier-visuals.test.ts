import { describe, expect, it } from "vitest";
import {
  DOSSIER_VISUALS_FIXTURE,
  LOCATOR_SYMBOLS_FIXTURE,
} from "../../src/lib/dossier-visuals-fixture";
import {
  figureCountsReconcile,
  figMapTwin,
  getDossierVisuals,
  getLocatorSymbols,
  isDrawnLocator,
  isDrawnMap,
  locatorGlyph,
  notDrawnTotal,
  parseLocatorSheet,
} from "../../src/lib/dossier-visuals";
import { getDossiers } from "../../src/lib/data";
import type { Dossier } from "../../src/lib/dossier";

// P36.55 (VIZ-02, SIG-UI-123/132): the dossier-visuals reader contract —
// every dossier resolves its `sig.dossier-visuals/1` doc, the typed states
// stay typed, the locator glyph resolves against the shared sheet, and the
// figure counts reconcile with the dossier's own record figure.

const dossiers = getDossiers();

describe("getDossierVisuals — every dossier's visuals doc", () => {
  it("every fixture dossier resolves its sig.dossier-visuals/1 doc", () => {
    for (const d of dossiers) {
      const doc = getDossierVisuals(d.slug);
      expect(doc, `${d.slug}`).not.toBeNull();
      expect(doc!.schema).toBe("sig.dossier-visuals/1");
    }
  });

  it("an absent slug resolves null — an honest typed state, never a throw", () => {
    expect(getDossierVisuals("no-such-dossier")).toBeNull();
  });

  it("usa/vi exercises the typed no_boundary map (SIG-UI-123)", () => {
    const doc = getDossierVisuals("usa/vi")!;
    expect(isDrawnMap(doc.map)).toBe(false);
    expect((doc.map as { status: string }).status).toBe("no_boundary");
    expect((doc.map as { records_total: number }).records_total).toBe(66);
  });

  it("country dossiers carry the typed no_parent_context locator", () => {
    for (const slug of ["usa", "can", "fra", "deu"]) {
      const doc = getDossierVisuals(slug)!;
      expect(isDrawnLocator(doc.locator), slug).toBe(false);
      expect((doc.locator as { status: string }).status).toBe("no_parent_context");
    }
  });
});

describe("figureCountsReconcile — SIG-UI-132", () => {
  it("drawn + not-drawn = total = the dossier's record figure, per dossier", () => {
    for (const d of dossiers) {
      const doc = getDossierVisuals(d.slug)!;
      if (!isDrawnMap(doc.map)) continue;
      const rollup = d.rollup?.records ?? null;
      const recon = figureCountsReconcile(doc.map, rollup);
      expect(
        recon.reconciles,
        `${d.slug}: drawn ${recon.drawn} + not-drawn ${notDrawnTotal(doc.map.not_drawn)} ` +
          `!= total ${recon.total} (dossier records ${recon.dossierRecords})`,
      ).toBe(true);
    }
  });

  it("flags a mismatch honestly rather than smoothing it over", () => {
    const doc = getDossierVisuals("usa")!;
    if (!isDrawnMap(doc.map)) throw new Error("usa map must draw");
    expect(figureCountsReconcile(doc.map, 999999).reconciles).toBe(false);
  });
});

describe("the locator glyph + symbol sheet", () => {
  it("resolves parent + child paths for a sub-jurisdiction", () => {
    const doc = getDossierVisuals("usa/ok/oklahoma-city-4064000")!;
    const glyph = locatorGlyph(doc, LOCATOR_SYMBOLS_FIXTURE);
    expect(glyph).not.toBeNull();
    expect(glyph!.parentD).toMatch(/^M /);
    expect(glyph!.childD).toMatch(/^M /);
  });

  it("returns null under a missing sheet — never a dead use", () => {
    const doc = getDossierVisuals("usa/ok")!;
    expect(locatorGlyph(doc, null)).toBeNull();
  });

  it("parses the produced-work sheet, fail-closed on non-SVG", () => {
    const svg =
      '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">' +
      '<symbol id="loc-a" viewBox="0 0 10 10"><path d="M 0 0 L 1 1 Z" class="sig-fig-child"/></symbol>' +
      "</svg>";
    expect(parseLocatorSheet(svg, "t")).toEqual({ "loc-a": "M 0 0 L 1 1 Z" });
    expect(() => parseLocatorSheet("not svg", "t")).toThrow(/not SVG/);
  });

  it("the shared sheet reader resolves in fixtures mode", () => {
    expect(getLocatorSymbols()).not.toBeNull();
  });
});

describe("figMapTwin — the published figures[] row", () => {
  it("derives a twin from a drawn doc when the dossier carries none", () => {
    const doc = getDossierVisuals("usa")!;
    const twin = figMapTwin({} as Dossier, doc);
    expect(twin).not.toBeNull();
    expect(twin!.figure_id).toBe("fig-map");
    expect(twin!.caption).toContain("Not a census");
    expect(twin!.caption_drafted).toContain("agent-drafted");
  });

  it("returns null under a typed map state — no caption over a missing figure", () => {
    const doc = getDossierVisuals("usa/vi")!;
    expect(figMapTwin({} as Dossier, doc)).toBeNull();
  });

  it("every fixture dossier carries its twin via getDossiers", () => {
    for (const d of dossiers) {
      const doc = getDossierVisuals(d.slug)!;
      if (!isDrawnMap(doc.map)) continue;
      const twin = d.figures?.find((f) => f.figure_id === "fig-map");
      expect(twin, d.slug).toBeTruthy();
    }
  });
});
