// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.65 withBase() unit tests (G3 NEW-6/GT-11; K13 R-8/UXR-25; SIG-REL-008
 * `Also:`). `joinBase` carries the join semantics so every base posture is
 * exercisable; `withBase` is asserted against `BASE` as an invariant — under
 * the repo's current no-`base` config it returns the path unchanged, and it
 * must track `import.meta.env.BASE_URL` the moment P36.66 configures one.
 */

import { describe, expect, it } from "vitest";
import { BASE, joinBase, withBase } from "../../src/lib/paths";

describe("joinBase — root base returns the path unchanged", () => {
  it.each(["/", ""])("base %j", (base) => {
    expect(joinBase(base, "/dossier/oklahoma-city/")).toBe("/dossier/oklahoma-city/");
    expect(joinBase(base, "dossier/oklahoma-city/")).toBe("/dossier/oklahoma-city/");
    expect(joinBase(base, "/")).toBe("/");
    expect(joinBase(base, "")).toBe("/");
  });
});

describe("joinBase — configured base joins with exactly one slash", () => {
  it.each(["/s/p-abc123", "/s/p-abc123/", "s/p-abc123"])("base %j", (base) => {
    expect(joinBase(base, "/dossier/oklahoma-city/")).toBe(
      "/s/p-abc123/dossier/oklahoma-city/",
    );
    expect(joinBase(base, "dossier/oklahoma-city/")).toBe(
      "/s/p-abc123/dossier/oklahoma-city/",
    );
    expect(joinBase(base, "/")).toBe("/s/p-abc123/");
    expect(joinBase(base, "")).toBe("/s/p-abc123/");
  });

  it("never emits a double slash at the join", () => {
    expect(joinBase("/s/p-1/", "/map/")).toBe("/s/p-1/map/");
    expect(joinBase("/s/p-1", "map/")).toBe("/s/p-1/map/");
    expect(joinBase("/s/p-1/", "//map/")).toBe("/s/p-1/map/");
    expect(joinBase("/", "/")).not.toContain("//");
    expect(joinBase("/s/p-1", "/")).toBe("/s/p-1/");
  });

  it("collapses extra leading slashes — no protocol-relative escape", () => {
    expect(joinBase("/", "//evil.example/x")).toBe("/evil.example/x");
    expect(joinBase("/s/p-1/", "///dossier/")).toBe("/s/p-1/dossier/");
  });

  it("keeps query strings and fragments", () => {
    expect(joinBase("/s/p-1/", "/search/?q=flock#r1")).toBe("/s/p-1/search/?q=flock#r1");
  });

  it("roots a base that lacks a leading slash rather than emit a relative URL", () => {
    expect(joinBase("s/p-1", "/map/")).toBe("/s/p-1/map/");
  });
});

describe("withBase — reads the configured base", () => {
  it("equals joinBase(BASE, path) — the invariant the snapshot depends on", () => {
    for (const p of ["/dossier/", "/map/", "/", "", "research-queue/"]) {
      expect(withBase(p)).toBe(joinBase(BASE, p));
    }
  });

  it("under the repo's current no-base config, returns the path unchanged", () => {
    // GT-11 recorded no `base` in astro.config.mjs; BASE is therefore "/".
    // This test fails loudly the day a base is configured — deliberately:
    // whoever sets `base` must come here and re-assert the snapshot shape.
    expect(BASE).toBe("/");
    expect(withBase("/dossier/oklahoma-city/")).toBe("/dossier/oklahoma-city/");
    expect(withBase("/")).toBe("/");
  });

  it("never emits a double slash", () => {
    for (const p of ["/", "//x", "/dossier/", "map/"]) {
      expect(withBase(p)).not.toMatch(/\/\//);
    }
  });
});

// --------------------------------------------------------------------- //
// P36.66a (SIG-UI-075 / SIG-REL-008): the sweep helpers — rootPath() for the
// declared outside-the-base namespaces and dataHref() for artifact-data paths.
// --------------------------------------------------------------------- //

import { rootPath, dataHref, OUTSIDE_BASE_PREFIXES } from "../../src/lib/paths";

describe("rootPath — the declared outside-the-base join (P36.66a)", () => {
  it("joins at the deploy root, never under the configured base", () => {
    expect(rootPath("r/p-abc/c/graph/")).toBe("/r/p-abc/c/graph/");
    expect(rootPath("/releases/p-abc/")).toBe("/releases/p-abc/");
    expect(rootPath("v1/releases/x/search")).toBe("/v1/releases/x/search");
  });
  it("normalises slashes exactly like joinBase", () => {
    expect(rootPath("//evil")).toBe("/evil");
    expect(rootPath("")).toBe("/");
  });
});

describe("dataHref — artifact-data paths (P36.66a)", () => {
  it("in-site paths re-base like any other link", () => {
    expect(dataHref("/map/")).toBe(withBase("/map/"));
    expect(dataHref("map/")).toBe("map/");
  });
  it("declared exception namespaces pass through raw", () => {
    for (const p of OUTSIDE_BASE_PREFIXES) {
      expect(dataHref(`${p}x/`)).toBe(`${p}x/`);
    }
    expect(dataHref("/v1/claim/contract")).toBe("/v1/claim/contract");
    expect(dataHref("/r/p-x/c/g/")).toBe("/r/p-x/c/g/");
  });
  it("external + fragment + relative values are untouched", () => {
    expect(dataHref("https://x.example/a")).toBe("https://x.example/a");
    expect(dataHref("#frag")).toBe("#frag");
    expect(dataHref("rel/path")).toBe("rel/path");
  });
});
