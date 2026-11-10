// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.29 (K6 VIZ-04, SIG-UI-127/132): the per-dossier embed-props document —
 * the build-side half of the in-place activation. The doc serialises the
 * SAME island-prop contract `/map/` hands MapIsland; the embedded context
 * carries the dossier's jkey (the `frame=` seed + the "Open full map"
 * facet) and the unkeyed fallback framing. The records payload is the
 * figure's own scope — the dossier's subtree-resolved sites rows, never a
 * fabricated set — so the activated box draws the same records the static
 * figure counts (SIG-UI-132's reconcile).
 */
import { describe, expect, it } from "vitest";
import {
  buildMapEmbedDoc,
  embedDossierSlugs,
  MAP_EMBED_SCHEMA,
  mapEmbedPropsHref,
} from "../../src/lib/map-embed";
import { getDossierVisuals, isDrawnMap } from "../../src/lib/dossier-visuals";

describe("dossier map-embed props document (VIZ-04)", () => {
  it("emits a doc only for dossiers whose Figure-1 drew located records", () => {
    const slugs = embedDossierSlugs();
    expect(slugs.length).toBeGreaterThan(0);
    for (const slug of slugs) {
      const doc = getDossierVisuals(slug);
      expect(doc, slug).not.toBeNull();
      expect(isDrawnMap(doc!.map), slug).toBe(true);
      expect(doc!.map.desc.records_drawn, slug).toBeGreaterThan(0);
    }
  });

  it("serialises the map island's prop contract plus the embed context", () => {
    const slug = embedDossierSlugs().find((s) => buildMapEmbedDoc(s).embedded.jkey) ??
      embedDossierSlugs()[0];
    const doc = buildMapEmbedDoc(slug);
    expect(doc.schema).toBe(MAP_EMBED_SCHEMA);
    // The MapAppProps surface — the same fields the island consumes.
    for (const key of [
      "tiles",
      "records",
      "pointCount",
      "attribution",
      "citationHref",
      "release",
      "compartments",
      "styles",
      "vendorBase",
      "dictHref",
      "asOf",
      "unplotted",
      "jurisdictionHrefs",
      "jurisdictionFrames",
      "shardRoot",
    ]) {
      expect(doc, key).toHaveProperty(key);
    }
    expect(doc.styles.light).toContain("map/style-light.json");
    expect(doc.vendorBase).toContain("map/vendor/");
    expect(doc.embedded.placeLabel.length).toBeGreaterThan(0);
  });

  it("scopes the records payload to the dossier's subtree — every row located", () => {
    for (const slug of embedDossierSlugs()) {
      const doc = buildMapEmbedDoc(slug);
      for (const r of doc.records) {
        expect(r.lat, `${slug}:${r.id}`).not.toBeNull();
        expect(r.lon, `${slug}:${r.id}`).not.toBeNull();
        expect(r.id.length, `${slug}:${r.id}`).toBeGreaterThan(0);
      }
      // pointCount is the drawn-record count; unplotted the honest
      // no-published-point remainder of the scope's rows.
      expect(doc.pointCount).toBe(doc.records.length);
      expect(doc.unplotted).toBeGreaterThanOrEqual(0);
    }
  });

  it("a keyed dossier's subtree scope includes descendants' records", () => {
    // usa/ok's figure covers its keyed children — the payload must carry
    // the descendant lists' rows, not just the parent list's own.
    const ok = buildMapEmbedDoc("usa/ok");
    const child = buildMapEmbedDoc("usa/ok/oklahoma-city-4064000");
    expect(ok.records.length).toBeGreaterThanOrEqual(child.records.length);
    const childIds = new Set(child.records.map((r) => r.id));
    for (const id of childIds) {
      expect(
        ok.records.some((r) => r.id === id),
        `usa/ok payload missing descendant record ${id}`,
      ).toBe(true);
    }
  });

  it("the embed context: frame seed via jkey; fallbackAt only when unkeyed", () => {
    const keyed = buildMapEmbedDoc("usa/ok");
    expect(keyed.embedded.jkey).toBe("iso3166-2:US-OK");
    expect(keyed.embedded.fallbackAt).toBeNull();
    expect(keyed.jurisdictionFrames["iso3166-2:US-OK"]).toBeDefined();
    for (const slug of embedDossierSlugs()) {
      const doc = buildMapEmbedDoc(slug);
      if (doc.embedded.jkey === null && doc.records.length > 0) {
        expect(doc.embedded.fallbackAt, slug).not.toBeNull();
      }
    }
  });

  it("the props route mints the dossier's own map-embed.json", () => {
    expect(mapEmbedPropsHref("usa/ok")).toBe("dossier/usa/ok/map-embed.json");
    expect(mapEmbedPropsHref("oklahoma-city")).toBe(
      "dossier/oklahoma-city/map-embed.json",
    );
  });
});
