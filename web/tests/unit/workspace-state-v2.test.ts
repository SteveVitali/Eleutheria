// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.21 unit tests — `sig.workspace-state/2` (SIG-UI-059, SIG-UI-060,
 * SIG-UI-093; K13 UXR-09/UXR-10; ADR-155/ADR-225):
 *
 * - registry completeness: every parameter the spec names is registered
 *   exactly once, with the scoping the table declares;
 * - the v2 round-trip: parse → serialise is byte-stable on canonical URLs
 *   and `v=2` + `view` are always minted;
 * - the v=1 compatibility clause (SIG-UI-093): every `v=1` link resolves
 *   identically — same v1 fields, same visible behaviour — while the link
 *   re-mints as `v=2`;
 * - canonicalisation with visible receipts: `bbox`/`frame` → `at`,
 *   `kind=site` → `type=record`, `US-OK` → `iso3166-2:US-OK`,
 *   `view=network` → `graph`, `location=any` → absent;
 * - refusal: an unregistered parameter is reported, never applied, never
 *   re-emitted;
 * - the surface × facet conformance harness: for every T2 surface, every
 *   registered parameter is either applied or named by the notice.
 */

import { describe, expect, it } from "vitest";
import {
  parseWorkspaceState,
  serializeWorkspaceState,
} from "../../src/lib/workspace-state";
import {
  APPLIED_PARAMS,
  bboxToViewport,
  canonicaliseWorkspaceState,
  checkSurfaceConformance,
  citeViewHref,
  conformanceReport,
  facetNoticeText,
  ISLAND_SURFACE,
  islandToViewValue,
  parseWorkspaceState2,
  PARAM_BY_NAME,
  serializeWorkspaceState2,
  surfaceForPath,
  SURFACE_PATHS,
  T2_ROBOTS_CONTENT,
  unappliedParams,
  V1_PARAM_NAMES,
  viewValueToIsland,
  WORKSPACE_PARAMS,
  WORKSPACE_STATE2_VERSION,
  WORKSPACE_SURFACES,
  workspaceHref2,
  type IslandWorkspaceState,
} from "../../src/lib/workspace-state/index";

// ------------------------------------------------------------ registry

describe("sig.workspace-state-registry/1", () => {
  it("registers every parameter SIG-UI-059 names, exactly once", () => {
    const names = WORKSPACE_PARAMS.map((p) => p.name);
    expect(new Set(names).size).toBe(names.length);
    // The §56.11/K13 §2.5 table, verbatim.
    expect(new Set(names)).toEqual(
      new Set([
        "release", "view", "q", "type", "kind", "jurisdiction", "frame",
        "bbox", "technology", "vendor", "operator", "source", "collection",
        "location", "status", "seen", "dated", "currency", "focus", "page",
        "sort", "dir", "cursor", "within",
        "at", "layers", "basemap",
        "overview", "hops", "edge", "expand", "path",
      ]),
    );
  });

  it("scopes map/graph parameters exactly as the table declares", () => {
    expect(PARAM_BY_NAME.get("at")!.scope).toBe("map");
    expect(PARAM_BY_NAME.get("layers")!.scope).toBe("map");
    expect(PARAM_BY_NAME.get("basemap")!.scope).toBe("map");
    for (const n of ["overview", "hops", "edge", "expand", "path"]) {
      expect(PARAM_BY_NAME.get(n)!.scope, n).toBe("graph");
    }
    expect(PARAM_BY_NAME.get("q")!.scope).toBe("common");
    expect(PARAM_BY_NAME.get("focus")!.scope).toBe("common");
  });

  it("marks the v1 parameter set (the names a v=1 link may carry)", () => {
    expect(new Set(V1_PARAM_NAMES)).toEqual(
      new Set([
        "release", "view", "q", "kind", "jurisdiction", "technology",
        "source", "collection", "location", "focus", "page",
      ]),
    );
  });

  it("declares the canonicalisation targets", () => {
    expect(PARAM_BY_NAME.get("bbox")!.canonicalisesTo).toBe("at");
    expect(PARAM_BY_NAME.get("frame")!.canonicalisesTo).toBe("at");
  });

  it("keeps the closed vocabularies closed", () => {
    expect(PARAM_BY_NAME.get("view")!.values).toEqual([
      "list", "map", "graph", "table", "search",
    ]);
    expect(PARAM_BY_NAME.get("status")!.values).toEqual([
      "corroborated", "single-source", "contested", "candidate",
    ]);
    expect(PARAM_BY_NAME.get("currency")!.values).toEqual([
      "current", "aging", "stale", "historical", "undated",
    ]);
    expect(PARAM_BY_NAME.get("location")!.values).toEqual([
      "public-point", "no-public-point",
    ]);
  });
});

// ------------------------------------------------------------ v2 parse

describe("parseWorkspaceState2 — v2 semantics", () => {
  it("parses a full canonical v2 link into every field", () => {
    const url =
      "?v=2&view=map&release=p-abc123&q=drone&type=record&kind=agency" +
      "&jurisdiction=iso3166-2:US-OK&technology=alu&vendor=axon&operator=okc-pd" +
      "&source=src-1&collection=sig-osm&location=public-point" +
      "&status=corroborated&status=contested&seen=2020..2024-03" +
      "&dated=2021-06..2024&currency=current&focus=sig-osm:site:1&page=2" +
      "&sort=name&dir=desc&cursor=g:c1&within=us-ok" +
      "&at=10/35.5/-97.5&layers=alpr&basemap=1";
    const { state, issues, notes, present } = parseWorkspaceState2(url);
    expect(issues).toEqual([]);
    expect(notes).toEqual([]);
    expect(state.view).toBe("map");
    expect(state.release).toBe("p-abc123");
    expect(state.q).toBe("drone");
    expect(state.type).toEqual(["record"]);
    expect(state.kind).toEqual(["agency"]);
    expect(state.jurisdiction).toEqual(["iso3166-2:US-OK"]);
    expect(state.technology).toEqual(["alu"]);
    expect(state.vendor).toEqual(["axon"]);
    expect(state.operator).toEqual(["okc-pd"]);
    expect(state.source).toEqual(["src-1"]);
    expect(state.collection).toEqual(["sig-osm"]);
    expect(state.location).toBe("public-point");
    expect(state.status).toEqual(["corroborated", "contested"]);
    expect(state.seen).toBe("2020..2024-03");
    expect(state.dated).toBe("2021-06..2024");
    expect(state.currency).toBe("current");
    expect(state.focus).toBe("sig-osm:site:1");
    expect(state.page).toBe(2);
    expect(state.sort).toBe("name");
    expect(state.dir).toBe("desc");
    expect(state.cursor).toBe("g:c1");
    expect(state.within).toBe("us-ok");
    expect(state.at).toEqual({ z: 10, lat: 35.5, lon: -97.5 });
    expect(state.layers).toEqual(["alpr"]);
    expect(state.basemap).toBe("1");
    expect(present).toContain("at");
  });

  it("parses the graph-scoped parameters", () => {
    const { state } = parseWorkspaceState2(
      "?v=2&view=graph&overview=ov-1&hops=2&edge=alpr&edge=cctv&expand=e1&expand=e2&path=a~b",
    );
    expect(state.overview).toBe("ov-1");
    expect(state.hops).toBe(2);
    expect(state.edge).toEqual(["alpr", "cctv"]);
    expect(state.expand).toEqual(["e1", "e2"]);
    expect(state.path).toBe("a~b");
  });

  it("round-trips byte-for-byte on the canonical (emitted) form", () => {
    // The canonical form is URLSearchParams-encoded; an input written with
    // unencoded separators decodes to the same state and re-emits the one
    // canonical spelling — parse → serialise → parse is the identity.
    const url =
      "?v=2&view=map&release=p-abc123&collection=sig-osm&focus=sig-osm:site:1" +
      "&at=10/35.47/-97.52&basemap=1";
    const first = parseWorkspaceState2(url);
    const emitted = serializeWorkspaceState2(first.state);
    const second = parseWorkspaceState2(`?${emitted}`);
    expect(second.state).toEqual(first.state);
    expect(serializeWorkspaceState2(second.state)).toBe(emitted);
    expect(emitted).toContain("at=10%2F35.47%2F-97.52");
    expect(emitted).toContain("focus=sig-osm%3Asite%3A1");
  });

  it("always mints v=2 and view on serialise (canonical emission)", () => {
    const emitted = serializeWorkspaceState2({
      ...parseWorkspaceState2("?v=2&view=graph&focus=x").state,
    });
    expect(emitted).toBe("v=2&view=graph&focus=x");
  });

  it("keeps repeated facet order", () => {
    const { state } = parseWorkspaceState2(
      "?v=2&view=list&technology=alv&technology=alu&collection=a&collection=b",
    );
    expect(state.technology).toEqual(["alv", "alu"]);
    expect(state.collection).toEqual(["a", "b"]);
  });

  it("collection bare marks the empty selection (never all)", () => {
    const bare = parseWorkspaceState2("?v=2&view=list&collection");
    expect(bare.state.collectionSpecified).toBe(true);
    expect(bare.state.collection).toEqual([]);
    const empty = parseWorkspaceState2("?v=2&view=list&collection=");
    expect(empty.state.collectionSpecified).toBe(true);
    expect(empty.state.collection).toEqual([]);
    expect(serializeWorkspaceState2(empty.state)).toContain("collection=");
  });
});

// ------------------------------------------------- v=1 compatibility

describe("sig.workspace-state/2 — v=1 identical resolution (SIG-UI-093)", () => {
  const V1_URL =
    "?v=1&view=map&release=p-abc123&collection=sig-osm&collection=sig-graph" +
    "&q=drone&kind=site&jurisdiction=US-OK&technology=alu&source=src-1" +
    "&location=public-point&focus=sig-osm:site:1&page=2";

  it("a v=1 link produces the same v1 field values the v1 parser produced", () => {
    const v1 = parseWorkspaceState(V1_URL);
    const v2 = parseWorkspaceState2(V1_URL);
    expect(v2.state.release).toBe(v1.state.release);
    expect(v2.state.collection).toEqual(v1.state.collection);
    expect(v2.state.collectionSpecified).toBe(v1.state.collectionSpecified);
    expect(v2.state.q).toBe(v1.state.q);
    // v1 `kind` semantics are preserved verbatim — record-type facets are
    // NOT re-read as v2 entity types (no `site` → `record` fold under v=1).
    expect(v2.state.kind).toEqual(v1.state.kind);
    expect(v2.state.jurisdiction).toEqual(v1.state.jurisdiction);
    expect(v2.state.technology).toEqual(v1.state.technology);
    expect(v2.state.source).toEqual(v1.state.source);
    expect(v2.state.location).toBe(v1.state.location);
    expect(v2.state.focus).toBe(v1.state.focus);
    expect(v2.state.page).toBe(v1.state.page);
  });

  it("keeps the v1 network view name resolving to the graph surface", () => {
    const { state } = parseWorkspaceState2("?v=1&view=network&focus=a:b:c");
    expect(state.view).toBe("graph");
    expect(viewValueToIsland(state.view)).toBe("network");
  });

  it("raises the v1 unknown-view issue for a v1-illegal view value", () => {
    const { issues } = parseWorkspaceState2("?v=1&view=graph");
    expect(issues.some((i) => i.includes('Unknown view "graph"'))).toBe(true);
  });

  it("keeps v1's unusable-page receipt", () => {
    for (const bad of ["0", "01", "1.5", "x"]) {
      const { state, issues } = parseWorkspaceState2(`?v=1&view=list&page=${bad}`);
      expect(state.page).toBe(1);
      expect(issues.some((i) => i.includes(`Unusable page "${bad}"`))).toBe(true);
    }
  });

  it("reports but does not interpret v2-only params on a v=1 link", () => {
    const { state, present, issues } = parseWorkspaceState2(
      "?v=1&view=map&sort=name&at=10/35/-97",
    );
    expect(present).toContain("sort");
    expect(present).toContain("at");
    expect(state.sort).toBeNull(); // v1 semantics: the extra is ignored
    expect(state.at).toBeNull();
    expect(issues).toEqual([]); // not an error — the surface notice names them
  });

  it("re-mints a v1 link as canonical v2", () => {
    const { state } = parseWorkspaceState2("?v=1&view=network&focus=a:b:c");
    expect(serializeWorkspaceState2(state)).toBe("v=2&view=graph&focus=a%3Ab%3Ac");
  });
});

// ------------------------------------------------------- canonicalise

describe("canonicalisation — every quiet rewrite is named", () => {
  it("folds bbox into at= and never re-emits it", () => {
    const { state, notes } = parseWorkspaceState2("?v=2&view=map&bbox=-98,34,-96,36");
    expect(state.at).not.toBeNull();
    const vp = bboxToViewport("-98,34,-96,36");
    expect(state.at).toEqual(vp);
    expect(notes.some((n) => n.includes("bbox") && n.includes("at="))).toBe(true);
    const emitted = serializeWorkspaceState2(state);
    expect(emitted).not.toContain("bbox");
    expect(emitted).toContain("at=");
  });

  it("lets an explicit at= win over a bbox", () => {
    const { state, notes } = parseWorkspaceState2(
      "?v=2&view=map&at=10/35/-97&bbox=-98,34,-96,36",
    );
    expect(state.at).toEqual({ z: 10, lat: 35, lon: -97 });
    expect(notes.some((n) => n.includes("bbox"))).toBe(true);
  });

  it("rounds at= coordinates to the published zoom precision", () => {
    expect(bboxToViewport("-97.9,35.4,-97.5,35.7")).toEqual(
      parseWorkspaceState2("?v=2&view=map&bbox=-97.9,35.4,-97.5,35.7").state.at,
    );
    const { state } = parseWorkspaceState2("?v=2&view=map&at=8/35.4679/-97.5164");
    expect(state.at).toEqual({ z: 8, lat: 35.47, lon: -97.52 });
  });

  it("keeps frame as a framing parameter (resolution needs the bounds table)", () => {
    const { state } = parseWorkspaceState2("?v=2&view=map&frame=iso3166-2:US-OK");
    expect(state.frame).toBe("iso3166-2:US-OK");
    expect(serializeWorkspaceState2(state)).toContain("frame=iso3166-2%3AUS-OK");
    const folded = canonicaliseWorkspaceState(state, {
      frameBounds: () => ({ z: 7, lat: 35.5, lon: -97.5 }),
    });
    expect(folded.state.at).toEqual({ z: 7, lat: 35.5, lon: -97.5 });
    expect(folded.state.frame).toBeNull();
    expect(folded.notes.some((n) => n.includes("frame"))).toBe(true);
  });

  it("normalises a legacy jurisdiction code with a visible note", () => {
    const { state, notes } = parseWorkspaceState2(
      "?v=2&view=list&jurisdiction=US-OK&jurisdiction=iso3166-2:US-CA",
    );
    expect(state.jurisdiction).toEqual(["iso3166-2:US-OK", "iso3166-2:US-CA"]);
    expect(notes.some((n) => n.includes("US-OK") && n.includes("iso3166-2:US-OK"))).toBe(true);
  });

  it("normalises kind=site to type=record with a visible note", () => {
    const { state, notes } = parseWorkspaceState2("?v=2&view=list&kind=site&kind=agency");
    expect(state.kind).toEqual(["agency"]);
    expect(state.type).toEqual(["record"]);
    expect(notes.some((n) => n.includes("kind=site"))).toBe(true);
  });

  it("normalises the v1 view name and location default word", () => {
    const v = parseWorkspaceState2("?v=2&view=network");
    expect(v.state.view).toBe("graph");
    expect(v.notes.some((n) => n.includes("network"))).toBe(true);
    const l = parseWorkspaceState2("?v=2&view=list&location=any");
    expect(l.state.location).toBeNull();
    expect(l.notes.some((n) => n.includes('"any"'))).toBe(true);
  });
});

// ------------------------------------------------------------ refusal

describe("refusal — an unregistered parameter is never silent", () => {
  it("reports, names and refuses an unregistered parameter", () => {
    const { issues, unregistered, state } = parseWorkspaceState2(
      "?v=2&view=list&bogus=1&release=p-x",
    );
    expect(unregistered).toEqual(["bogus"]);
    expect(issues.some((i) => i.includes('"bogus"') && i.includes("not in the"))).toBe(true);
    expect(serializeWorkspaceState2(state)).not.toContain("bogus");
    expect(state.release).toBe("p-x");
  });

  it("rejects a closed-vocabulary violation visibly", () => {
    const { issues, state } = parseWorkspaceState2("?v=2&view=list&status=bogus");
    expect(state.status).toEqual([]);
    expect(issues.some((i) => i.includes("status") && i.includes("bogus"))).toBe(true);
  });

  it("rejects a malformed range and viewport visibly", () => {
    const r = parseWorkspaceState2("?v=2&view=list&seen=2020-2024");
    expect(r.state.seen).toBeNull();
    expect(r.issues.some((i) => i.includes("seen"))).toBe(true);
    const a = parseWorkspaceState2("?v=2&view=map&at=x/y/z");
    expect(a.state.at).toBeNull();
    expect(a.issues.some((i) => i.includes("at"))).toBe(true);
  });
});

// -------------------------------------------------------- conformance

describe("surface × facet conformance (SIG-UI-060)", () => {
  it("every registered parameter is applied or noticed on every T2 surface", () => {
    for (const surface of WORKSPACE_SURFACES) {
      const report = conformanceReport(surface);
      expect(report.violations).toEqual([]);
      expect(report.applied.length + report.noticed.length).toBe(
        PARAM_BY_NAME.size,
      );
      for (const name of report.applied) {
        expect(APPLIED_PARAMS[surface]).toContain(name);
      }
    }
  });

  it("a probe URL on each surface partitions into applied + noticed", () => {
    const url =
      "?v=2&view=list&release=p-1&q=x&sort=name&at=1/2/3&hops=2&focus=a:b:c";
    const { present } = parseWorkspaceState2(url);
    const search = checkSurfaceConformance("search", present);
    expect(search.applied).toEqual(
      expect.arrayContaining(["release", "q", "view", "focus"]),
    );
    expect(search.noticed).toEqual(
      expect.arrayContaining(["sort", "at", "hops"]),
    );
    const graph = checkSurfaceConformance("graph", present);
    expect(graph.applied).toEqual(expect.arrayContaining(["release", "focus", "view"]));
    expect(graph.noticed).toEqual(expect.arrayContaining(["q", "sort", "at", "hops"]));
  });

  it("the notice names unapplied facets in the registry's words", () => {
    const { present } = parseWorkspaceState2("?v=2&view=list&sort=name&jurisdiction=US-OK");
    const unapplied = unappliedParams(present, "search");
    expect(unapplied).toContain("sort");
    const text = facetNoticeText(unapplied);
    expect(text).toContain("does not apply");
    expect(text).toContain("do not filter");
  });

  it("the notice never lists an applied parameter", () => {
    const { present } = parseWorkspaceState2("?v=2&view=list&q=x&release=p-1");
    expect(unappliedParams(present, "search")).toEqual([]);
  });
});

// ------------------------------------------------------------ surfaces

describe("surface/vocabulary mapping", () => {
  it("maps internal island views to surfaces and back", () => {
    expect(ISLAND_SURFACE.network).toBe("graph");
    expect(islandToViewValue("network")).toBe("graph");
    expect(viewValueToIsland("graph")).toBe("network");
    expect(viewValueToIsland("table")).toBe("list");
    expect(SURFACE_PATHS.graph).toBe("/network/");
  });

  it("resolves the surface for a path, including /s/<pub>/ prefixes", () => {
    expect(surfaceForPath("/map/")).toBe("map");
    expect(surfaceForPath("/network/")).toBe("graph");
    expect(surfaceForPath("/search/")).toBe("search");
    expect(surfaceForPath("/s/p-abc/map/")).toBe("map");
    expect(surfaceForPath("/dossier/x/")).toBeNull();
  });
});

// ------------------------------------------------------------- citing

describe("cite this view (K0 §4.5, J3 §8.1 interim)", () => {
  const state: IslandWorkspaceState = {
    ...parseWorkspaceState2("?v=2&view=list&collection=sig-osm&focus=a:b:c").state,
    view: "map",
  };

  it("mints the snapshot-pinned /s/<pub>/<surface>/?v=2&… form", () => {
    const href = citeViewHref("p-abc123", "map", state);
    expect(href.startsWith("/s/p-abc123/map/?v=2&")).toBe(true);
    expect(href).toContain("view=map");
    expect(href).toContain("collection=sig-osm");
    expect(href).toContain("focus=a%3Ab%3Ac");
  });

  it("mints the base form when no state is bound", () => {
    expect(citeViewHref("p-abc123", "search", null)).toBe(
      "/s/p-abc123/search/?v=2",
    );
  });

  it("the T2 robots policy is noindex,follow", () => {
    expect(T2_ROBOTS_CONTENT).toBe("noindex,follow");
  });

  it("workspaceHref2 emits v=2 links on the surface's own path", () => {
    const island: IslandWorkspaceState = {
      ...parseWorkspaceState2("?v=2&view=map&focus=a:b:c").state,
      view: "network",
    };
    const href = workspaceHref2(island);
    expect(href).toBe("/network/?v=2&view=graph&focus=a%3Ab%3Ac");
  });
});

// ----------------------------------------------------------- version

describe("version handling", () => {
  it("an unversioned link parses as v2", () => {
    const { state, issues } = parseWorkspaceState2("?view=map&focus=a:b:c");
    expect(state.view).toBe("map");
    expect(issues).toEqual([]);
  });

  it("an unrecognised version parses under v2 with a visible receipt", () => {
    const { state, issues } = parseWorkspaceState2("?v=9&view=list&focus=x");
    expect(state.focus).toBe("x");
    expect(issues.some((i) => i.includes('"9"'))).toBe(true);
  });

  it("serializeWorkspaceState always mints v=1 (the v1 module is untouched)", () => {
    expect(serializeWorkspaceState(parseWorkspaceState("?v=1&view=list&focus=x").state).get("v")).toBe("1");
    expect(WORKSPACE_STATE2_VERSION).toBe("2");
  });
});
