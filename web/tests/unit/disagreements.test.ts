// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.38 (R11-K13-CX-01, SIG-UI-071) — the disagreements-browser derivation:
 * three typed kinds kept apart, counts from the release artifacts, both
 * sides of a recorded contradiction with sources and dates, and the typed
 * absences (a doc-named record no statement cites; a place with nothing
 * recorded). Asserts the model over the committed fixtures — never a living
 * record (OM-15).
 */
import { describe, expect, it } from "vitest";
import {
  buildContradictions,
  disagreementAnchor,
  disagreementPlacePath,
  disagreementsIndex,
  jkeyPlaceMap,
  placeDisagreementPage,
} from "../../src/lib/disagreements";
import {
  getDossierSourcesMap,
  getEntityLabelRows,
  getEvidence,
  getStatementIndex,
} from "../../src/lib/data";
import { getSourcePageIds } from "../../src/lib/source-page";

const DOCS = getDossierSourcesMap();
const STATEMENTS = getStatementIndex();
const VIEWS = getEvidence().claimViews;
const SOURCE_PAGES = new Set(getSourcePageIds());
const LABELS = getEntityLabelRows();

const CONTRADICTION_ID = "contra:device-count-42-38";

describe("buildContradictions — recorded contradictions, both sides", () => {
  const records = buildContradictions(STATEMENTS, DOCS, VIEWS, SOURCE_PAGES, LABELS);

  it("groups the claims citing one contradiction id", () => {
    const rec = records.find((c) => c.contradiction_id === CONTRADICTION_ID);
    expect(rec).toBeDefined();
    // Both sides resolve: the contract claim and the portal claim.
    const claims = rec!.sides.map((s) => s.claim_id);
    expect(claims).toContain("active-device-count");
    expect(claims).toContain("portal-device-count");
  });

  it("carries each side's source and dates — never a bare id", () => {
    const rec = records.find((c) => c.contradiction_id === CONTRADICTION_ID)!;
    for (const side of rec.sides) {
      expect(side.statement_published).toBe(true);
      expect(side.source_id).not.toBeNull();
      expect(side.observed_at).not.toBeNull();
    }
    // Published claim labels render (the claim view joins by id).
    const portal = rec.sides.find((s) => s.claim_id === "portal-device-count")!;
    expect(portal.label).toBe("Portal-reported device count = 38");
    expect(portal.claim_href).toBe("evidence/claim/portal-device-count/");
  });

  it("places a doc-named record on its dossiers' place pages", () => {
    const rec = records.find((c) => c.contradiction_id === CONTRADICTION_ID)!;
    expect(rec.place_slugs).toContain("usa");
    expect(rec.place_slugs).toContain("usa/ok");
    expect(rec.place_slugs).toContain("oklahoma-city");
  });

  it("keeps an id-only doc record even with no citing statement", () => {
    // A doc naming an id no statement cites still lists — typed absence,
    // never dropped (the record exists).
    const docs2 = new Map(DOCS);
    const ghost = structuredClone(DOCS.get("usa")!);
    ghost.cross_source.contradictions.push({ contradiction_id: "contra:ghost" });
    docs2.set("usa", ghost);
    const rs = buildContradictions(STATEMENTS, docs2, VIEWS, SOURCE_PAGES, LABELS);
    const g = rs.find((c) => c.contradiction_id === "contra:ghost")!;
    expect(g.sides).toEqual([]);
    expect(g.place_slugs).toEqual(["usa"]);
  });
});

describe("disagreementsIndex — the hub model", () => {
  const index = disagreementsIndex(STATEMENTS, DOCS, VIEWS, SOURCE_PAGES, LABELS);

  it("counts contradictions once (deduplicated across places)", () => {
    expect(index.contradictions.map((c) => c.contradiction_id)).toEqual([CONTRADICTION_ID]);
  });

  it("keeps the three kinds apart — coordinate conflicts never merge into contradictions", () => {
    const slugs = index.coordinate_places.map((p) => p.slug);
    expect(slugs).toContain("usa");
    expect(slugs).toContain("usa/ok");
    // A coordinate-conflict row is a source count, never a contradiction record.
    for (const p of index.coordinate_places) expect(p.records).toBeGreaterThan(0);
  });

  it("lists declared-vs-located places in both directions", () => {
    const ok = index.declared_located_places.find((p) => p.slug === "usa/ok")!;
    expect(ok.declared_here).toBe(12);
    const harris = index.declared_located_places.find(
      (p) => p.slug === "usa/tx/harris-county-48201",
    )!;
    expect(harris.located_here).toBe(12);
  });
});

describe("placeDisagreementPage — one dossier's three kinds", () => {
  const contradictions = buildContradictions(STATEMENTS, DOCS, VIEWS, SOURCE_PAGES, LABELS);
  const dossierSlugs = new Set(["usa/ok", "oklahoma-city"]);

  it("usa/ok carries all three kinds", () => {
    const page = placeDisagreementPage("usa/ok", DOCS.get("usa/ok")!, contradictions, DOCS, dossierSlugs);
    expect(page.contradictions.map((c) => c.contradiction_id)).toEqual([CONTRADICTION_ID]);
    expect(page.coordinate_conflicts.total).toBe(3);
    expect(page.coordinate_conflicts.sources.map((s) => s.source_id)).toEqual(["demo_permitted_portal"]);
    expect(page.declared_located.declared_here_located_elsewhere).toBe(12);
  });

  it("resolves counterpart jkeys to names and place links — both sides visible", () => {
    const page = placeDisagreementPage("usa/ok", DOCS.get("usa/ok")!, contradictions, DOCS, dossierSlugs);
    const cp = page.declared_located.located_elsewhere[0]!;
    expect(cp.records).toBe(12);
    expect(cp.slug).toBe("usa/tx/harris-county-48201");
    const harris = placeDisagreementPage(
      "usa/tx/harris-county-48201", DOCS.get("usa/tx/harris-county-48201")!, contradictions, DOCS, dossierSlugs,
    );
    expect(harris.declared_located.declared_elsewhere[0]!.slug).toBe("usa/ok");
  });

  it("usa/tx renders the three typed absences — zero of each kind", () => {
    const page = placeDisagreementPage("usa/tx", DOCS.get("usa/tx")!, contradictions, DOCS, dossierSlugs);
    expect(page.contradictions).toEqual([]);
    expect(page.coordinate_conflicts.total).toBe(0);
    expect(page.declared_located.declared_here_located_elsewhere).toBe(0);
    expect(page.declared_located.located_here_declared_elsewhere).toBe(0);
  });
});

describe("routes + anchors", () => {
  it("builds place paths and stable anchors", () => {
    expect(disagreementPlacePath("usa/ok")).toBe("disagreements/place/usa/ok/");
    expect(disagreementAnchor(CONTRADICTION_ID)).toBe("con-contra-device-count-42-38");
  });

  it("maps docs' jkeys to place names", () => {
    const places = jkeyPlaceMap(DOCS);
    expect(places.get("iso3166-2:US-OK")!.slug).toBe("usa/ok");
  });
});
