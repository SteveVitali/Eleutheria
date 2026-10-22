#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// P35.51 (SIG-UI-041, K0 §4.12 item 5, ADR-155): render `web/lighthouserc.json`
// — and the export-leg twin `web/lighthouserc.export.json` — from the page-type
// registry's discovery output (`dist/page-types.json`) and the committed budget
// table (`tests/e2e/page-budgets.json`, sig.page-budgets/1). The committed files
// are GENERATED artifacts: regenerate with `node scripts/gen-lhci.mjs` and never
// hand-edit — `node scripts/gen-lhci.mjs --verify` fails when they drift and is
// wired into `npm run check` after `build` (K0's "the committed file is in
// sync" test). Assertions are errors per page type; a recorded measured_gap
// keeps its ratified ceiling as a warn while the regression bound is the error
// gate — the law is never smoothed.
//
//   node scripts/gen-lhci.mjs            regenerate both files
//   node scripts/gen-lhci.mjs --verify   exit 1 when a committed file drifts
//
// URL coverage (K0 NEW-3): at least one route per type, including /releases/,
// a research dossier, an entity-shaped page, /sources/, a print page and a T0
// record — selected deterministically from the discovered manifest so the
// collect set can never silently drop a type.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const BUDGETS_PATH = join(WEB, "tests", "e2e", "page-budgets.json");
const MANIFEST_PATH = join(WEB, "dist", "page-types.json");
const RC_PATH = join(WEB, "lighthouserc.json");
const RC_EXPORT_PATH = join(WEB, "lighthouserc.export.json");
const RC_NATIONAL_PATH = join(WEB, "lighthouserc.national.json");

const budgets = JSON.parse(readFileSync(BUDGETS_PATH, "utf-8"));
if (budgets.schema !== "sig.page-budgets/1") {
  throw new Error(`${BUDGETS_PATH}: expected schema sig.page-budgets/1, got ${budgets.schema}`);
}

// --------------------------------------------------------------------------
// URL selection — deterministic over the discovered manifest.
// --------------------------------------------------------------------------

function loadManifestRoutes() {
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(MANIFEST_PATH, "utf-8"));
  } catch (cause) {
    throw new Error(
      `${MANIFEST_PATH} missing — the generator selects URLs from the discovered ` +
        "routes; run `SIG_BUILD_INTERNAL=1 npm run build` first (`check` orders it " +
        "before `check:lhci`).",
      { cause },
    );
  }
  if (parsed.schema !== "sig.page-types-manifest/1") {
    throw new Error(`${MANIFEST_PATH}: schema ${parsed.schema} — rebuild dist`);
  }
  // The canonical manifest is the INTERNAL build's: the contract's named
  // routes (/releases/, a research dossier, /curate/**) exist only on the
  // SIG_BUILD_INTERNAL surface, so a publishable manifest would silently drop
  // them from the collect set. Fail loud instead of emitting a thin config.
  if (!parsed.routes.some((r) => r.internal)) {
    throw new Error(
      `${MANIFEST_PATH}: no internal routes — the committed configs are generated ` +
        "from the SIG_BUILD_INTERNAL manifest; rebuild with `SIG_BUILD_INTERNAL=1 npm run build`.",
    );
  }
  return parsed.routes;
}

/**
 * Pick the collect set from discovered routes — ≥ 1 per type, the named
 * contract routes preferred, deterministic (manifest order is already sorted).
 */
export function selectUrls(routes) {
  const byPath = new Map(routes.map((r) => [r.path, r]));
  const has = (p) => byPath.has(p);
  const first = (pred) => routes.find(pred)?.path ?? null;
  const urls = [];

  const add = (p) => {
    if (p && !urls.includes(p)) urls.push(p);
  };

  // T0: a record page (the dispute-record surface) plus a print page.
  add(has("/dispute/") ? "/dispute/" : first((r) => r.type === "T0" && !/\/40\d/.test(r.path)));
  add(first((r) => r.type === "T0" && r.path.endsWith("/print/")));

  // T1: the contract's named representatives.
  add(has("/") ? "/" : null);
  add(has("/sources/") ? "/sources/" : null);
  add(has("/releases/") ? "/releases/" : null);
  add(
    first((r) => r.type === "T1" && /^\/research-dossier\/[^/]+\/$/.test(r.path)) ??
      (has("/research-dossier/") ? "/research-dossier/" : null),
  );
  add(
    // An entity page where the surface emits one (GX-06a's /entity/* is not
    // yet emitted — the jurisdiction dossier is today's entity-shaped T1).
    first((r) => r.type === "T1" && r.path.startsWith("/entity/")) ??
      (has("/dossier/oklahoma-city/")
        ? "/dossier/oklahoma-city/"
        : first(
            (r) =>
              r.type === "T1" &&
              /^\/dossier\/[^/]+\/$/.test(r.path) &&
              !r.path.includes("unplaced"),
          )),
  );
  add(has("/coverage-metrics/") ? "/coverage-metrics/" : null);
  add(has("/data-freshness/") ? "/data-freshness/" : null);

  // T2: EVERY discovered T2 route — a surface never escapes measurement.
  for (const r of routes.filter((r) => r.type === "T2")) add(r.path);

  // T3: the curation surface (ADR-068 — a11y asserted, perf advisory).
  add(has("/curate/") ? "/curate/" : first((r) => r.type === "T3"));

  return urls;
}

// The export leg's declared URL set — same representative coverage plus the
// routes only that build carries: the seeded-spine dossier /dossier/ok/, its
// print view, and the mounted archive record (mount-record in
// scripts/ci/export_mode_leg.sh — publication/entity ids are content-derived,
// the alias is the stable collect URL). The leg fails loudly if a URL 404s.
const EXPORT_URLS = [
  "/index.html",
  "/dossier/ok/index.html",
  "/dossier/ok/print/index.html",
  "/sources/index.html",
  "/coverage-metrics/index.html",
  "/data-freshness/index.html",
  "/curate/index.html",
  "/map/index.html",
  "/network/index.html",
  "/search/index.html",
  "/releases/index.html",
  "/research-dossier/index.html",
  "/r/_fixture-record/index.html",
];

// --------------------------------------------------------------------------
// Assertion matrix — one block per budget row, assertions as errors per type.
// --------------------------------------------------------------------------

const COMMON_OFF = {
  "unminified-css": "off",
  "uses-long-cache-ttl": "off",
  "csp-xss": "off",
};

/** Budget metric → the Lighthouse audit that asserts it. Interaction latency
 * and the wire-byte totals are the spec's gate, not lhci's — they never map. */
const METRIC_AUDITS = {
  jsInitialBytes: "resource-summary:script:size",
  documentMaxBytes: "resource-summary:document:size",
  lcpMs: "largest-contentful-paint",
  cls: "cumulative-layout-shift",
  tbtMs: "total-blocking-time",
};

/** The measured_gaps row that binds for (route, metric, source), preferring a
 * source-scoped row over the unscoped one — the same precedence as
 * page-budget-check.ts (`find(scoped) ?? find(unscoped)`). */
function findGap(route, metric, source) {
  const matching = (budgets.measured_gaps ?? []).filter(
    (g) =>
      g.route === route &&
      g.metric === metric &&
      (g.data_source === undefined || g.data_source === source),
  );
  return (
    matching.find((g) => g.data_source === source) ??
    matching.find((g) => g.data_source === undefined) ??
    null
  );
}

/** The per-metric audit assertions for a budget row (errors, verbatim numbers).
 * `source` scopes measured_gaps the way page-budget-check.ts does — a
 * `"national"`-scoped gap is emitted only in the national twin. assertMatrix
 * accepts exactly ONE `[level, options]` tuple per audit, so a recorded
 * measured_gap asserts its regression bound here at error while the sibling
 * warn block (gapWarnAssertions below) re-asserts the ratified ceiling —
 * the law is never smoothed. */
function assertionsFor(row, route, source = "fixtures") {
  const a = {};
  const byteAudit = (audit, metric, ceiling) => {
    if (ceiling === null || ceiling === undefined) return;
    const g = findGap(route, metric, source);
    a[audit] = ["error", { maxNumericValue: g ? g.regression_bound : ceiling }];
  };
  for (const [metric, audit] of Object.entries(METRIC_AUDITS)) {
    byteAudit(audit, metric, row[metric]);
  }
  if (row.lighthousePerformance !== null) {
    a["categories:performance"] = ["error", { minScore: row.lighthousePerformance }];
  }
  if (row.lighthouseAccessibility !== null) {
    a["categories:accessibility"] = ["error", { minScore: row.lighthouseAccessibility }];
  }
  Object.assign(a, COMMON_OFF);
  return a;
}

/** The warn-level sibling assertions: for every metric on this route with a
 * recorded measured_gap, the ratified §4.3 ceiling asserted at warn. Returns
 * null when the route has no gaps that map to a Lighthouse audit (e.g. a
 * latency-only gap stays the spec's gate entirely). */
function gapWarnAssertions(row, route, source = "fixtures") {
  const a = {};
  for (const [metric, audit] of Object.entries(METRIC_AUDITS)) {
    const g = findGap(route, metric, source);
    if (g && row[metric] !== null && row[metric] !== undefined) {
      a[audit] = ["warn", { maxNumericValue: g.ratified_ceiling }];
    }
  }
  return Object.keys(a).length ? a : null;
}

/**
 * The wire byte table's total-transfer ceiling is measured exactly by
 * budget.spec.ts (which excludes tile/data fetches the way the table words
 * it); Lighthouse's resource-summary:total counts data fetches too, so the
 * generated matrix asserts script + document + the lab metrics here and the
 * total stays the spec's gate — recorded, never double-counted.
 */
function assertMatrix(source = "fixtures") {
  const blocks = [];
  const T0 = budgets.types.T0;
  const T1 = budgets.types.T1;
  const T3 = budgets.types.T3;

  blocks.push({
    "//": "T0 record & print — zero executable JS, document ≤ 150 KiB, perf ≥ 0.95, a11y 1.0, LCP ≤ 1.5 s, CLS ≤ 0.02, TBT 0 (K0 §4.3 verbatim).",
    matchingUrlPattern:
      ".*/(dispute|print|r|intake)/.*|.*/40[0-9](/|\\.html)|^/r/.*",
    assertions: assertionsFor(T0, null, source),
  });
  blocks.push({
    "//": "T1 content — script ≤ 20 KiB, document ≤ 150 KiB, perf ≥ 0.95, a11y 1.0, LCP ≤ 1.5 s, CLS ≤ 0.02, TBT ≤ 50 ms (K0 §4.3 verbatim). Excludes the T0/T2/T3 blocks.",
    matchingUrlPattern:
      "^(?:(?!/curate/|/map/|/network/|/explore/|/search/|/dispute/|/print/|/r/|/intake/|/40[0-9]).)*$",
    assertions: assertionsFor(T1, null, source),
  });
  const surfaceBlocks = (note, pattern, row, route) => {
    blocks.push({
      "//": note,
      matchingUrlPattern: pattern,
      assertions: assertionsFor(row, route, source),
    });
    const warn = gapWarnAssertions(row, route, source);
    if (warn) {
      blocks.push({
        "//": `WARN TWIN of the block above — assertMatrix allows one tuple per audit, so the ratified §4.3 ceilings this route's measured_gaps record report at warn here while the block above keeps the regression bounds as the error gate.`,
        warnTwin: true,
        matchingUrlPattern: pattern,
        assertions: warn,
      });
    }
  };

  surfaceBlocks(
    "T2 map — script ≤ 360 KiB (ratified; the recorded measured gap bounds today's ≈ 497 KB at its regression bound as error, the ratified ceiling as warn — D-P35.51-1), document ≤ 100 KiB, perf ≥ 0.75, a11y 1.0, LCP ≤ 2.5 s, CLS ≤ 0.05, TBT ≤ 350 ms.",
    ".*/map/.*",
    budgets.t2Surfaces.map,
    "/map/",
  );
  surfaceBlocks(
    "T2 graph (/network/ today, /explore/ when it lands) — script ≤ 120 KiB, document ≤ 100 KiB, perf ≥ 0.90, a11y 1.0, LCP ≤ 2.0 s, CLS ≤ 0.05, TBT ≤ 200 ms.",
    ".*/(network|explore)/.*",
    budgets.t2Surfaces.graph,
    "/network/",
  );
  surfaceBlocks(
    "T2 search — script ≤ 60 KiB (ratified; the recorded measured gap bounds today's ≈ 72 KB React runtime at 80 KiB error — D-P35.51-2), document ≤ 100 KiB, perf ≥ 0.95, a11y 1.0, LCP ≤ 1.5 s, CLS ≤ 0.02, TBT ≤ 100 ms.",
    ".*/search/.*",
    budgets.t2Surfaces.search,
    "/search/",
  );
  blocks.push({
    "//": "T3 curation (/curate/**, ADR-068 unchanged) — a11y 1.0 enforced; performance advisory only; no byte budgets.",
    matchingUrlPattern: ".*/curate/.*",
    assertions: {
      ...assertionsFor(T3, null, source),
      // ADR-068's advisory floor, carried verbatim from the hand file.
      "categories:performance": ["warn", { minScore: 0.7 }],
    },
  });
  return blocks;
}

// --------------------------------------------------------------------------
// The rendered documents.
// --------------------------------------------------------------------------

function renderConfig(urls, note, source = "fixtures") {
  return (
    JSON.stringify(
      {
        "//": note,
        ci: {
          collect: {
            staticDistDir: "./dist",
            numberOfRuns: 3,
            "//runs":
              "P34.2 / ADR-191: three sampled runs per URL, asserted on the median — the single-run sampling flake (LH-PERF-1) red-marked green work; budgets and thresholds unchanged.",
            "//url":
              "GENERATED by web/scripts/gen-lhci.mjs from dist/page-types.json + tests/e2e/page-budgets.json — at least one route per page type (K0 NEW-3), never hand-edited.",
            url: urls,
            settings: { throttlingMethod: "simulate" },
          },
          assert: { assertMatrix: assertMatrix(source) },
          upload: { target: "filesystem", outputDir: "./.lighthouseci" },
        },
      },
      null,
      2,
    ) + "\n"
  );
}

const BASE_NOTE =
  "SPDX-License-Identifier: Apache-2.0 — GENERATED by web/scripts/gen-lhci.mjs from the page-type manifest + tests/e2e/page-budgets.json (sig.page-budgets/1, K0 §4.3 ratified numbers verbatim; SIG-UI-041, ADR-155). Never hand-edit — run `node scripts/gen-lhci.mjs`; `npm run check:lhci` fails on drift. Per-type budgets: T0 zero-JS record/print, T1 ≤ 20 KiB content, T2 map ≤ 360/graph ≤ 120/search ≤ 60 KiB, T3 curation a11y-only (ADR-068). Recorded measured gaps (page-budgets.json measured_gaps) assert their ratified ceilings as warn and the regression bound as error — the law is never smoothed.";
const EXPORT_NOTE =
  "SPDX-License-Identifier: Apache-2.0 — GENERATED by web/scripts/gen-lhci.mjs — the export-mode twin of lighthouserc.json (P34.34b / DR-C4-13): the same generated assertMatrix (a unit test fails if the matrices drift) over the from-spine export build's declared route set, incl. the mounted archive record /r/_fixture-record/.";
const NATIONAL_NOTE =
  "SPDX-License-Identifier: Apache-2.0 — GENERATED by web/scripts/gen-lhci.mjs — the national-fixture twin of lighthouserc.json (P35.51, SIG-FIND-005): the same assertMatrix rendered with the national-scoped measured_gaps applied (the real-scale document/total overages the fixture build never hits). The national leg (scripts/ci/national_budget_leg.sh) runs lhci against the SIG_DATA_SOURCE=national build with THIS config.";

// --------------------------------------------------------------------------

function main() {
  const verify = process.argv.includes("--verify");

function writeOrVerify(path, content) {
  let current = null;
  try {
    current = readFileSync(path, "utf-8");
  } catch {
    current = null;
  }
  if (verify) {
    if (current !== content) {
      console.error(
        `${path} is out of sync with the generator — run \`node scripts/gen-lhci.mjs\` and commit the result.`,
      );
      process.exitCode = 1;
    } else {
      console.log(`${path}: in sync ✓`);
    }
    return;
  }
  if (current === content) {
    console.log(`${path}: already in sync`);
    return;
  }
  writeFileSync(path, content, "utf-8");
  console.log(`${path}: regenerated`);
}

  const routes = loadManifestRoutes();
  const urls = selectUrls(routes).map((p) => (p === "/" ? "/index.html" : `${p}index.html`));
  writeOrVerify(RC_PATH, renderConfig(urls, BASE_NOTE));
  writeOrVerify(RC_EXPORT_PATH, renderConfig(EXPORT_URLS, EXPORT_NOTE));
  // The national twin: the same collect set (the national build emits the same
  // routes), with national-scoped measured_gaps applied (P35.51 SIG-FIND-005).
  writeOrVerify(RC_NATIONAL_PATH, renderConfig(urls, NATIONAL_NOTE, "national"));

  if (verify && process.exitCode === undefined) {
    console.log("generated lighthouserc files are in sync");
  }
}

// Imported by the unit tests (the pure selectUrls/render surface) — the CLI
// work only runs when the file is executed directly.
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main();
}
