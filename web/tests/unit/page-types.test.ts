// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.50 page-type registry unit tests (UXK0-1, K0 §4.2, ADR-155, SIG-UI-041).
 * The registry is fail-closed machinery, so these tests pin the invariants the
 * build hook and the sweeps rely on: every registry example classifies to its
 * own row, overlap resolves most-specific-wins (never first-match), a tie
 * between two different entries is an error, an unmatched route is an error,
 * and `classifyDist` turns an injected unclassified html file into a build
 * error — the mechanism `astro:build:done` raises on.
 */

import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  buildManifest,
  chromeOf,
  classifyDist,
  classifyRoute,
  discoverBuiltRoutes,
  htmlFileToRoute,
  PAGE_TYPE_REGISTRY,
  parsePattern,
  type PageTypeEntry,
} from "../../src/lib/page-types";

function classified(path: string): { type: string; pattern: string } {
  const r = classifyRoute(path);
  if (!r.ok) throw new Error(`expected ${path} to classify, got ${r.kind}`);
  return { type: r.entry.type, pattern: r.pattern };
}

describe("registry shape", () => {
  it("every entry carries the UXR-02 fields", () => {
    for (const entry of PAGE_TYPE_REGISTRY) {
      expect(entry.patterns.length).toBeGreaterThan(0);
      expect(["T0", "T1", "T2", "T3"]).toContain(entry.type);
      expect(entry.owner).toMatch(/^P\d/);
      expect(entry.contract.length).toBeGreaterThan(0);
      expect(entry.noJsEquivalent.kind).toMatch(/^(self|sections|none)$/);
      expect(entry.examples.length).toBeGreaterThan(0);
    }
  });

  it("every pattern parses — a malformed pattern is a build error at parse", () => {
    for (const entry of PAGE_TYPE_REGISTRY) {
      for (const p of entry.patterns) expect(() => parsePattern(p)).not.toThrow();
    }
    expect(() => parsePattern("dossier/**")).toThrow(/root-relative/);
    expect(() => parsePattern("/a/**/b/**")).toThrow(/two \*\*/);
    expect(() => parsePattern("/a/b*c/")).toThrow(/partial wildcard/);
  });

  it("every declared example classifies to the entry that declares it", () => {
    for (const entry of PAGE_TYPE_REGISTRY) {
      for (const example of entry.examples) {
        const r = classifyRoute(example);
        expect(r.ok, `example ${example} of ${entry.patterns} must classify`).toBe(true);
        if (r.ok) {
          expect(
            r.entry,
            `${example} resolved to ${r.entry.patterns.join("|")}, not ${entry.patterns.join("|")}`,
          ).toBe(entry);
          expect(r.entry.type).toBe(entry.type);
        }
      }
    }
  });
});

describe("type ordering — most-specific wins, never first-match", () => {
  it("print pages are T0 under every prefix (leaf literal beats rest)", () => {
    expect(classified("/dossier/oklahoma-city/print/").type).toBe("T0");
    expect(classified("/dossier/paris-alpr/print/").type).toBe("T0");
    expect(classified("/s/p-abc123/dossier/x/print/").type).toBe("T0");
  });

  it("snapshot T2 surfaces stay T2 inside the T1 umbrella", () => {
    expect(classified("/s/p-abc123/map/").type).toBe("T2");
    expect(classified("/s/p-abc123/search/").type).toBe("T2");
    expect(classified("/s/p-abc123/dossier/x/").type).toBe("T1");
  });

  it("/network/ classifies as the T2 surface it currently is", () => {
    expect(classified("/network/").type).toBe("T2");
    expect(classified("/map/").type).toBe("T2");
    expect(classified("/search/").type).toBe("T2");
    expect(classified("/explore/").type).toBe("T2");
  });

  it("tombstones and the terms forwarder classify", () => {
    expect(classified("/404.html").type).toBe("T0");
    expect(classified("/403/").type).toBe("T0");
    expect(classified("/403.html").type).toBe("T0");
    expect(classified("/410/").type).toBe("T0");
    expect(classified("/410.html").type).toBe("T0");
    expect(classified("/terms/").type).toBe("T1");
  });

  it("curate is T3 internal; injected T1 surfaces carry the internal flag", () => {
    const curate = classifyRoute("/curate/submit/");
    expect(curate.ok && curate.entry.internal).toBe(true);
    expect(classified("/curate/er_match:agency:a~agency:b/").type).toBe("T3");
    const rd = classifyRoute("/research-dossier/okc-alpr/");
    expect(rd.ok && rd.entry.type === "T1" && rd.entry.internal).toBe(true);
  });

  it("release data listings are T0 while /releases/ itself is T1", () => {
    expect(classified("/releases/").type).toBe("T1");
    expect(classified("/releases/p-abc123/data/x/").type).toBe("T0");
  });
});

describe("fail closed", () => {
  it("an unmatched route is unclassified, not silently T-something", () => {
    const r = classifyRoute("/made-up-namespace/");
    expect(r.ok).toBe(false);
    expect(r.ok ? "" : r.kind).toBe("unclassified");
  });

  it("a genuine tie between two different entries is doubly-classified", () => {
    const a: PageTypeEntry = {
      patterns: ["/x/**"],
      type: "T1",
      owner: "P1.1",
      contract: "none",
      noJsEquivalent: { kind: "self", description: "t" },
      examples: [],
    };
    const b: PageTypeEntry = {
      patterns: ["/x/**"],
      type: "T0",
      owner: "P1.2",
      contract: "none",
      noJsEquivalent: { kind: "self", description: "t" },
      examples: [],
    };
    const r = classifyRoute("/x/y/", [a, b]);
    expect(r.ok).toBe(false);
    expect(r.ok ? "" : r.kind).toBe("ambiguous");
  });

  it("a strictly-more-specific pattern beats a same-position wildcard (no tie)", () => {
    const exact: PageTypeEntry = {
      patterns: ["/x/y/"],
      type: "T0",
      owner: "P1.1",
      contract: "none",
      noJsEquivalent: { kind: "self", description: "t" },
      examples: [],
    };
    const rest: PageTypeEntry = {
      patterns: ["/x/**"],
      type: "T1",
      owner: "P1.2",
      contract: "none",
      noJsEquivalent: { kind: "self", description: "t" },
      examples: [],
    };
    const r = classifyRoute("/x/y/", [rest, exact]);
    expect(r.ok && r.entry === exact).toBe(true);
  });
});

describe("dist discovery + manifest", () => {
  function fixture(files: Record<string, string>): string {
    const dir = mkdtempSync(join(tmpdir(), "sig-pagetypes-"));
    for (const [rel, body] of Object.entries(files)) {
      const full = join(dir, rel);
      mkdirSync(join(full, ".."), { recursive: true });
      writeFileSync(full, body);
    }
    return dir;
  }

  it("maps dist html files to route paths", () => {
    expect(htmlFileToRoute(join("x", "index.html"))).toBe("/x/");
    expect(htmlFileToRoute("404.html")).toBe("/404.html");
    expect(htmlFileToRoute("index.html")).toBe("/");
  });

  it("discovers every built html route and classifies it", () => {
    const dir = fixture({
      "index.html": '<html data-sig-chrome="full"></html>',
      "map/index.html": '<html data-sig-chrome="full"></html>',
      "dossier/x/index.html": '<html data-sig-chrome="full"></html>',
      "dossier/x/print/index.html": '<html data-sig-chrome="print"></html>',
      "404.html": '<html data-sig-chrome="minimal"></html>',
      "curate/index.html": '<html data-sig-chrome="curate"></html>',
    });
    expect(discoverBuiltRoutes(dir)).toEqual([
      "/404.html",
      "/curate/",
      "/dossier/x/",
      "/dossier/x/print/",
      "/map/",
    ].concat(["/"]).sort());
    const { routes, errors } = classifyDist(dir);
    expect(errors).toEqual([]);
    const byPath = Object.fromEntries(routes.map((r) => [r.path, r]));
    expect(byPath["/map/"]?.type).toBe("T2");
    expect(byPath["/dossier/x/print/"]?.type).toBe("T0");
    expect(byPath["/dossier/x/print/"]?.chrome).toBe("print");
    expect(byPath["/404.html"]?.type).toBe("T0");
    expect(byPath["/curate/"]?.internal).toBe(true);
    const manifest = buildManifest(routes);
    expect(manifest.schema).toBe("sig.page-types-manifest/1");
    expect(manifest.routes.map((r) => r.path)).toEqual(
      [...manifest.routes.map((r) => r.path)].sort(),
    );
  });

  it("an injected unclassified html file is a build error (the hook's mechanism)", () => {
    const dir = fixture({
      "index.html": "<html></html>",
      "sneaky/index.html": "<html></html>",
    });
    const { errors } = classifyDist(dir);
    expect(errors).toHaveLength(1);
    expect(errors[0]).toContain("/sneaky/");
    expect(errors[0]).toContain("page-types.ts");
  });

  it("chromeOf records the layout marker", () => {
    expect(chromeOf('<html data-sig-chrome="minimal">')).toBe("minimal");
    expect(chromeOf("<html>")).toBe("unmarked");
  });
});
