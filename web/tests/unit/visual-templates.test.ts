// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  VISUAL_TEMPLATE_GROUPS,
  claimedComponents,
  selectRepresentative,
} from "../visual/templates";

// P37.60 (SIG-UI-152, DR-K14-18): the visual-regression contract's static
// half — the template registry must be well-formed (unique ids, no component
// claimed twice, every group non-empty) and every committed baseline must
// cite its authorising ticket in tests/visual/baselines.json ("a baseline
// change MUST cite its ticket"). The manifest-derived halves (every emitted
// component claimed, every group resolving a representative) live in
// tests/visual/visual.spec.ts where dist/page-types.json is readable.

const VISUAL_DIR = fileURLToPath(new URL("../visual", import.meta.url));
const SNAPSHOT_DIR = join(VISUAL_DIR, "visual.spec.ts-snapshots");
const LEDGER = JSON.parse(readFileSync(join(VISUAL_DIR, "baselines.json"), "utf8")) as {
  schema: string;
  baselines: Record<string, { ticket?: string; note?: string; pending?: boolean }>;
};

const CELLS = ["light-1440", "light-390", "light-320", "dark-1440", "dark-390", "dark-320"];

describe("visual template registry (SIG-UI-152)", () => {
  it("has unique group ids", () => {
    const ids = VISUAL_TEMPLATE_GROUPS.map((g) => g.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("claims every component coherently — no empty group, shared modules discriminated", () => {
    for (const g of VISUAL_TEMPLATE_GROUPS) {
      expect(g.components.length, `group ${g.id} claims no components`).toBeGreaterThan(0);
      expect(g.id, `group id ${g.id} must be filename-safe`).toMatch(/^[a-z0-9-]+$/);
    }
    // A page module MAY legitimately back several groups (one module → three
    // dossier depths) — but every group sharing a module must carry a
    // `prefer` discriminator or the representatives collide and the extra
    // "template" shots the same page twice.
    const claims = claimedComponents();
    const undifferentiated = [...claims.entries()].flatMap(([c, holders]) =>
      holders.length > 1
        ? holders
            .map((id) => VISUAL_TEMPLATE_GROUPS.find((g) => g.id === id)!)
            .filter((g) => g.prefer === undefined)
            .map((g) => `${g.id} shares ${c} with no prefer discriminator`)
        : [],
    );
    expect(undifferentiated).toEqual([]);
  });

  it("covers the six required cells per group (light/dark × 1440/390/320)", () => {
    // The matrix lives in playwright.visual.config.ts; this test pins the
    // cell names the snapshots are filed under so a project rename cannot
    // silently orphan the committed baselines.
    const config = readFileSync(
      fileURLToPath(new URL("../../playwright.visual.config.ts", import.meta.url)),
      "utf8",
    );
    for (const cell of CELLS) {
      const [theme, vp] = cell.split("-");
      expect(config, `config lost the ${theme} theme`).toContain(`"${theme}"`);
      expect(config, `config lost the ${vp} viewport`).toContain(`"${vp}"`);
      expect(config).toContain("`${theme}-${vp}`");
    }
    expect(config).toContain('colorScheme: theme');
    expect(config).toContain("maxDiffPixelRatio: 0.01");
  });

  it("picks a deterministic representative per group", () => {
    const routes = [
      { path: "/b/", component: "alpha.astro" },
      { path: "/a/", component: "alpha.astro" },
      { path: "/z/", component: "beta.astro" },
    ];
    const g = {
      id: "t",
      title: "t",
      components: ["alpha.astro"],
      prefer: /^\/b\//,
    } as const;
    // prefer wins even when lexicographically later.
    expect(selectRepresentative(g, routes).path).toBe("/b/");
    // Without prefer the sorted head wins — order-independent.
    expect(selectRepresentative({ ...g, prefer: undefined }, routes).path).toBe("/a/");
    // A group whose components emitted nothing resolves null, never a guess.
    expect(
      selectRepresentative({ ...g, components: ["gamma.astro"] }, routes).path,
    ).toBeNull();
  });
});

describe("baseline provenance ledger (a baseline change MUST cite its ticket)", () => {
  const pngs = existsSync(SNAPSHOT_DIR)
    ? readdirSync(SNAPSHOT_DIR).filter((f) => f.endsWith(".png")).sort()
    : [];

  it("is the sig.visual-baselines/1 schema", () => {
    expect(LEDGER.schema).toBe("sig.visual-baselines/1");
  });

  it("every committed snapshot is cited, every citation is a real ticket id", () => {
    const missing = pngs.filter((p) => LEDGER.baselines[p] === undefined);
    expect(
      missing,
      "snapshot(s) without a baselines.json row — add the row citing the ticket that authorised the baseline",
    ).toEqual([]);
    for (const [name, row] of Object.entries(LEDGER.baselines)) {
      expect(row.ticket, `${name}: baseline row carries no ticket`).toMatch(/^P\d+\.\d+[a-z]?$/);
      expect(
        row.pending === true || pngs.includes(name),
        `${name}: ledger row names no committed snapshot — mark it 'pending' or shoot the baseline`,
      ).toBe(true);
    }
  });

  it("snapshot filenames are <group>--<theme>-<viewport>.png over known groups and cells", () => {
    const groupIds = new Set(VISUAL_TEMPLATE_GROUPS.map((g) => g.id));
    for (const p of pngs) {
      const m = p.match(/^([a-z0-9-]+)--(light|dark)-(?:1440|390|320)\.png$/);
      expect(m, `${p}: not a <group>--<cell>.png name`).not.toBeNull();
      expect(groupIds.has(m![1]!), `${p}: no template group named ${m![1]}`).toBe(true);
    }
  });
});
