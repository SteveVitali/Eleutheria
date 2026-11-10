// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.42b (K2 GX-06a 06b): emit the fixture entity's figure spec docs and
 * render them through the figure kit — the SAME seam a release export
 * takes (K13 C-07: compositions stay with the page owner, layouts stay in
 * the kit).
 *
 *   npm run fixture:entity-figures
 *
 * = esbuild bundle this file → node writes the `sig.figure-kit-*` spec
 * docs under `web/src/fixtures/entity-figures/<url_type>/<key>/` →
 * `uv run sig-exports figure ego|chart|map --in <spec> --out <svg>
 * --meta <meta>` renders the committed SVG bytes the fixtures-mode build
 * serves. Invented honest data only: the map outline is an invented ring
 * standing in for a real boundary (the same posture as the index sprite's
 * invented outlines).
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";

import { ENTITY_PAGE_FIXTURES } from "../src/lib/entity-page-fixtures";
import { mergeEntityTwins } from "../src/lib/entity-pages";
import { entityEgoSpec, entityMapSpec, entityTimeline } from "../src/lib/entity-figures";

function repoRoot(): string {
  let dir = fileURLToPath(new URL(".", import.meta.url));
  for (;;) {
    if (existsSync(join(dir, "uv.lock"))) return dir;
    const parent = join(dir, "..");
    if (parent === dir) throw new Error("repoRoot: walked above the bundle without finding uv.lock");
    dir = parent;
  }
}
const REPO_ROOT = repoRoot();

/** The fixture place outlines — invented honest rings, documented in each
 *  spec's `boundary_vintage` (never a real boundary presented as real). */
const FIXTURE_PLACES: Record<
  string,
  { name: string; slugPath: string; level: string; chain: string[]; outline: [number, number][][] }
> = {
  "usa-ga": {
    name: "Georgia, United States",
    slugPath: "usa/ga",
    level: "state_province",
    chain: ["usa"],
    outline: [
      [
        [-85.61, 35.0],
        [-80.84, 35.0],
        [-80.76, 32.03],
        [-81.05, 30.72],
        [-82.22, 30.39],
        [-85.61, 30.98],
        [-85.61, 35.0],
      ],
    ],
  },
};

const verbs = ["ego", "timeline", "map"] as const;
let emitted = 0;

for (const [routeKey, twin] of Object.entries(ENTITY_PAGE_FIXTURES)) {
  const merged = mergeEntityTwins([twin]);
  const dir = join(REPO_ROOT, "web", "src", "fixtures", "entity-figures", routeKey);
  mkdirSync(dir, { recursive: true });

  const specs: Record<(typeof verbs)[number], unknown | null> = {
    ego: entityEgoSpec(merged),
    timeline: entityTimeline(merged).spec,
    map: twin.place_jkey
      ? entityMapSpec(merged, {
          outline: FIXTURE_PLACES[twin.place_jkey]?.outline ?? [],
          name: FIXTURE_PLACES[twin.place_jkey]?.name ?? twin.place_jkey,
          slugPath: FIXTURE_PLACES[twin.place_jkey]?.slugPath ?? twin.place_jkey,
          level: FIXTURE_PLACES[twin.place_jkey]?.level ?? "unknown",
          chain: FIXTURE_PLACES[twin.place_jkey]?.chain ?? [],
          boundaryVintage: "fixture-invented-outlines (P36.42b)",
        })
      : null,
  };

  for (const kind of verbs) {
    const spec = specs[kind];
    const specPath = `${dir}/${kind}.spec.json`;
    if (spec === null) continue;
    writeFileSync(specPath, JSON.stringify(spec, null, 2) + "\n", "utf-8");
    const verb = kind === "map" ? "map" : kind === "ego" ? "ego" : "chart";
    execFileSync(
      "uv",
      [
        "run",
        "sig-exports",
        "figure",
        verb,
        "--in",
        specPath,
        "--out",
        `${dir}/${kind}.svg`,
        "--meta",
        `${dir}/${kind}.meta.json`,
      ],
      { cwd: REPO_ROOT, stdio: "inherit" },
    );
    emitted += 1;
  }
}

console.log(`emit-entity-figures: ${emitted} figure artifacts rendered`);
