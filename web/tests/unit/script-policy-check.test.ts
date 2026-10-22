// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P35.50 script-policy check tests (K0 §4.12 item 2, SIG-ENG-042 — the check
 * is itself proven, never assumed). An injected `<script>` on a T0 fixture
 * MUST fail; an un-allow-listed module entry on T1 must fail; a foreign src
 * on T2 must fail; the universal bans fire on every type.
 */

import { describe, expect, it } from "vitest";
import {
  scriptsOf,
  scriptViolations,
  universalViolations,
} from "../e2e/script-policy-check";

const BOOTSTRAP = new Set(["aaaabbbb"]);
const T1_ENTRIES = new Set<string>();

const inline = (body: string) => `<script>${body}</script>`;
const moduleSrc = (src: string) => `<script type="module" src="${src}"></script>`;

describe("scriptsOf", () => {
  it("extracts inline and src'd scripts with their type", () => {
    const html = `<p>x</p>${inline("body")}${moduleSrc("/_astro/x.js")}<script type="application/ld+json">{"a":1}</script>`;
    const s = scriptsOf(html);
    expect(s).toHaveLength(3);
    expect(s[0]!.inline).toBe(true);
    expect(s[1]!.src).toBe("/_astro/x.js");
    expect(s[2]!.type).toBe("application/ld+json");
  });
});

describe("scriptViolations — injected fixtures must fail", () => {
  it("an injected <script> on a T0 fixture is a violation", () => {
    const [s] = scriptsOf(inline("alert(1)"));
    expect(scriptViolations("T0", s!, BOOTSTRAP, T1_ENTRIES).join(" ")).toContain(
      "no <script> element",
    );
  });

  it("an inline ld+json block is a violation on every type (D-J3-7 linked files only)", () => {
    const [s] = scriptsOf(`<script type="application/ld+json">{}</script>`);
    for (const t of ["T0", "T1", "T2"] as const) {
      expect(scriptViolations(t, s!, BOOTSTRAP, T1_ENTRIES).join(" ")).toContain("ld+json");
    }
  });

  it("a non-allow-listed module entry on T1 fails; an allow-listed one passes", () => {
    const [s] = scriptsOf(moduleSrc("/_astro/sig-table.js"));
    expect(scriptViolations("T1", s!, BOOTSTRAP, T1_ENTRIES).length).toBeGreaterThan(0);
    const allowed = new Set(["/_astro/sig-table.js"]);
    expect(scriptViolations("T1", s!, BOOTSTRAP, allowed)).toEqual([]);
  });

  it("an unrecorded inline script on T1/T2 fails; the recorded bootstrap passes", () => {
    const [unknown] = scriptsOf(inline("var x=1"));
    expect(scriptViolations("T1", unknown!, BOOTSTRAP, T1_ENTRIES).length).toBeGreaterThan(0);
    expect(scriptViolations("T2", unknown!, BOOTSTRAP, T1_ENTRIES).length).toBeGreaterThan(0);
    // sha256("bootstrap") — recorded as aaaabbbb is NOT its digest; use a real one.
    const body = "x";
    const digest = require("node:crypto").createHash("sha256").update(body).digest("hex");
    const [rec] = scriptsOf(inline(body));
    expect(scriptViolations("T2", rec!, new Set([digest]), T1_ENTRIES)).toEqual([]);
  });

  it("a foreign or unhashed src on T2 fails; a /_astro/ asset passes", () => {
    const [ext] = scriptsOf(moduleSrc("https://cdn.example/x.js"));
    const [rel] = scriptsOf(moduleSrc("/static/x.js"));
    const [ok] = scriptsOf(moduleSrc("/_astro/island.abc123.js"));
    expect(scriptViolations("T2", ext!, BOOTSTRAP, T1_ENTRIES).length).toBeGreaterThan(0);
    expect(scriptViolations("T2", rel!, BOOTSTRAP, T1_ENTRIES).length).toBeGreaterThan(0);
    expect(scriptViolations("T2", ok!, BOOTSTRAP, T1_ENTRIES)).toEqual([]);
  });

  it("a classic (non-module) src'd script fails on T1/T2", () => {
    const [s] = scriptsOf(`<script src="/_astro/x.js"></script>`);
    expect(scriptViolations("T2", s!, BOOTSTRAP, T1_ENTRIES).join(" ")).toContain("non-module");
  });
});

describe("universalViolations", () => {
  it("catches on*= handlers and javascript: URLs", () => {
    const v = universalViolations(`<a href="javascript:void(0)" onclick="x()">y</a>`);
    expect(v.onHandlers.length).toBe(1);
    expect(v.jsUrls.length).toBe(1);
    expect(universalViolations(`<a href="/dossier/">y</a>`)).toEqual({
      onHandlers: [],
      jsUrls: [],
    });
  });
});
