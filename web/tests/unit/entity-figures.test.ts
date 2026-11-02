// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project.
// P36.42b (K2 GX-06a 06b): the entity-figure composition — spec docs derive
// verbatim from the merged twin, undated is never drawn as dated, the
// committed fixture specs match regeneration, and the inline-safety guard
// refuses banned markup before it can reach a page.
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  ENTITY_PAGE_TWIN_FIXTURE,
  type EntityRelationItem,
} from "../../src/lib/entity-page";
import { mergeEntityTwins } from "../../src/lib/entity-pages";
import {
  assertInlineSvgSafe,
  entityEgoSpec,
  entityMapSpec,
  entityTimeline,
  figureAccessKind,
  figureCurrency,
} from "../../src/lib/entity-figures";

const MERGED = mergeEntityTwins([ENTITY_PAGE_TWIN_FIXTURE]);
const FIG_DIR = fileURLToPath(
  new URL(
    "../../src/fixtures/entity-figures/agency/acworth-police-department--4g2wm8q/",
    import.meta.url,
  ),
);

describe("field mappings", () => {
  it("maps the three access kinds one-to-one, never merged", () => {
    expect(figureAccessKind("configured_access")).toBe("configured");
    expect(figureAccessKind("observed_use")).toBe("observed");
    expect(figureAccessKind("declared_policy")).toBe("declared");
    expect(figureAccessKind(null)).toBeNull();
  });
  it("maps currency words; UNDATED never reads current or historical", () => {
    expect(figureCurrency("CURRENT")).toBe("current");
    expect(figureCurrency("HISTORICAL")).toBe("historical");
    expect(figureCurrency("UNDATED")).toBe("aging");
    expect(figureCurrency(null)).toBe("aging");
  });
});

describe("entityEgoSpec", () => {
  const spec = entityEgoSpec(MERGED)!;
  it("centres the entity and links every node", () => {
    expect(spec.schema).toBe("sig.figure-kit-graph/1");
    expect(spec.kind).toBe("ego");
    const centre = spec.nodes.find((n) => n.side === "centre")!;
    expect(centre.label).toBe("Acworth Police Department");
    for (const n of spec.nodes) expect(n.href.startsWith("/")).toBe(true);
  });
  it("a page-less counterparty links this entity's page — never a dead route", () => {
    const site = spec.nodes.find((n) => n.label === "surveillance camera in usa-ga")!;
    expect(site.href).toBe("/entity/agency/acworth-police-department--4g2wm8q/");
  });
  it("edges carry the H-2 fields verbatim — kinds never merged, undated marked", () => {
    const share = spec.edges.find((e) => e.relation === "configured sharing partner")!;
    expect(share.access_kind).toBe("configured");
    expect(share.date).toBe("2020-01-28");
    expect(share.currency).toBe("historical");
    const cam = spec.edges.find((e) => e.relation === "camera operator")!;
    expect(cam.date_kind).toBe("undated");
    expect(cam.date).toBeUndefined();
    expect(cam.direction).toBe("inbound");
    expect(cam.source).not.toBe("centre"); // inbound edge: site → entity
  });
  it("every neighbour declares group fields — group, never silently prune", () => {
    for (const n of spec.nodes.filter((n) => n.side === "neighbour")) {
      expect(n.group_key).toBeTruthy();
      expect(n.group_label).toBeTruthy();
      expect(n.group_href).toBeTruthy();
    }
  });
  it("returns null when the record carries no edges", () => {
    const empty = mergeEntityTwins([
      { ...ENTITY_PAGE_TWIN_FIXTURE, relations: [] },
    ]);
    expect(entityEgoSpec(empty)).toBeNull();
  });
});

describe("entityTimeline", () => {
  const tl = entityTimeline(MERGED);
  it("dated events compose from observed dates only", () => {
    expect(tl.spec).not.toBeNull();
    expect(tl.dated.length).toBeGreaterThan(0);
    for (const e of tl.dated) expect(e.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
  it("undated items are listed, never placed on the axis", () => {
    expect(tl.undated.length).toBeGreaterThan(0);
    expect(tl.spec!.events.every((e) => e.date)).toBe(true);
    expect(tl.undated.some((u) => u.label.includes("camera operator"))).toBe(true);
  });
  it("a record with no dated facts composes no spec but keeps its list", () => {
    const undatedOnly = mergeEntityTwins([
      {
        ...ENTITY_PAGE_TWIN_FIXTURE,
        claims: [],
        access: { closures: [], degree_only: [] },
        relations: [
          {
            ...ENTITY_PAGE_TWIN_FIXTURE.relations[1]!,
            items: ENTITY_PAGE_TWIN_FIXTURE.relations[1]!.items.map(
              (i): EntityRelationItem => ({ ...i }),
            ),
          },
        ],
      },
    ]);
    const t2 = entityTimeline(undatedOnly);
    expect(t2.spec).toBeNull();
    expect(t2.undated.length).toBeGreaterThan(0);
  });
});

describe("entityMapSpec", () => {
  it("renders only when the twin records a place", () => {
    const opts = {
      outline: [[[0, 0], [1, 0], [1, 1], [0, 0]]] as [number, number][][],
      name: "Georgia, United States",
      slugPath: "usa/ga",
      level: "state_province",
      chain: ["usa"],
      boundaryVintage: "fixture-invented-outlines",
    };
    const spec = entityMapSpec(MERGED, opts)!;
    expect(spec.schema).toBe("sig.figure-kit-geo/1");
    expect(spec.jurisdiction.jkey).toBe("usa-ga");
    const noPlace = mergeEntityTwins([{ ...ENTITY_PAGE_TWIN_FIXTURE, place_jkey: null }]);
    expect(entityMapSpec(noPlace, opts)).toBeNull();
  });
});

describe("committed fixture artifacts", () => {
  it("the committed specs match regeneration from the fixture twin", () => {
    for (const [kind, spec] of [
      ["ego", entityEgoSpec(MERGED)],
      ["timeline", entityTimeline(MERGED).spec],
    ] as const) {
      const committed = JSON.parse(readFileSync(`${FIG_DIR}${kind}.spec.json`, "utf-8"));
      expect(committed).toEqual(JSON.parse(JSON.stringify(spec)));
    }
  });
  it("the committed SVGs pass the inline-safety contract", () => {
    for (const kind of ["ego", "timeline", "map"]) {
      const svg = readFileSync(`${FIG_DIR}${kind}.svg`, "utf-8");
      expect(() => assertInlineSvgSafe(svg, `fixture ${kind}`)).not.toThrow();
    }
  });
});

describe("assertInlineSvgSafe", () => {
  it("refuses scripts, handlers, styles, data-* and external refs", () => {
    const base = '<svg xmlns="http://www.w3.org/2000/svg"></svg>';
    for (const bad of [
      "<svg><script>1</script></svg>",
      '<svg><a onload="x()"/></svg>',
      '<svg><a href="javascript:x()"/></svg>',
      '<svg><a href="https://evil.example/"/></svg>',
      '<svg><rect style="fill:red"/></svg>',
      '<svg><rect data-count="3"/></svg>',
      "<svg><style>.x{}</style></svg>",
      "not svg at all",
    ]) {
      expect(() => assertInlineSvgSafe(bad, "test")).toThrow();
    }
    expect(assertInlineSvgSafe(base, "test")).toBe(base);
  });
});
