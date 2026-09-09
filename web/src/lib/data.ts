// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The web data layer (P21.4, deliverable 2; ADR-066).
 *
 * The shell is static-first (SIG-UI-036): it reads its data at BUILD time, never
 * from a live API in the browser, so nothing here ships to the client — the
 * zero-JS budget is unchanged. This module is the single seam through which the
 * pages get their data, so the source can be swapped without touching a page:
 *
 *   - `SIG_DATA_SOURCE=fixtures` (the DEFAULT, so CI is unchanged) — the committed
 *     typed fixtures (`web/src/lib/*-fixture.ts`), exactly as before.
 *   - `SIG_DATA_SOURCE=export` — the output of `sig-exports build --jurisdiction
 *     <j>` (JSON/Parquet-derived JSON + a PMTiles path), read from the export
 *     directory at build time. This is how the composed stack builds the static
 *     site *from the exports* (§38.1: "a hand-built export is a different dataset
 *     wearing the same name" — the site and the export agree by construction).
 *
 * `export` mode fails LOUD if the export directory / a required artifact is absent
 * (never a silent fall-back to fixtures — that would fabricate green). The export
 * carries the same `/v1` dossier contract the fixtures do, so the page code is
 * identical in both modes.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { DOSSIERS } from "./dossier-fixture";
import { JURISDICTION_DOSSIERS } from "./dossier-jurisdiction-fixture";
import type { Dossier } from "./dossier";
import { LEVERAGE_METRIC_FIXTURE, type LeverageMetric } from "./leverage-fixture";

export type DataSource = "fixtures" | "export";

/** The active data source (build-time env; defaults to `fixtures` so CI is unchanged). */
export function dataSource(): DataSource {
  return process.env.SIG_DATA_SOURCE === "export" ? "export" : "fixtures";
}

/** The repository root, resolved from this module's URL (web/src/lib/data.ts → root). */
function repoRoot(): string {
  return fileURLToPath(new URL("../../../", import.meta.url));
}

/**
 * The export directory `sig-exports build --jurisdiction <j> --out <dir>` wrote.
 * `SIG_EXPORT_DIR` overrides; the default is the OKC output path the composed run
 * (`docs/build/tools/run_okc.sh`) uses.
 */
export function exportDir(): string {
  return process.env.SIG_EXPORT_DIR ?? `${repoRoot()}exports/out/okc`;
}

/**
 * The dossiers the site renders. In `fixtures` mode this is the committed fixture
 * set; in `export` mode it is `<exportDir>/web/dossiers.json` — the web-shaped
 * dossier bundle the jurisdiction export emits (the same `Dossier` contract).
 */
export function getDossiers(): Dossier[] {
  if (dataSource() === "fixtures") return DOSSIERS;
  const path = `${exportDir()}/web/dossiers.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the export dossier bundle is missing: ${path}. ` +
        `Run \`sig-exports build --jurisdiction <j> --out <dir>\` first ` +
        `(see docs/build/tools/run_okc.sh).`,
      { cause },
    );
  }
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed)) {
    throw new Error(`${path}: expected a JSON array of dossiers, got ${typeof parsed}`);
  }
  // The export carries the real jurisdiction (OKC). The FR/BE dossiers are the
  // SIG-PUB-017 publication-adapter *demonstrations* the shell ships regardless of
  // data source (they show the jurisdiction-conditional withholding, not export
  // data), so they render in both modes and the e2e/a11y surface is identical.
  return [...(parsed as Dossier[]), ...JURISDICTION_DOSSIERS];
}

/**
 * The §7 contribution-back leverage metric (P21.7, SIG-CONTRIB-016e): the count of
 * SIG-originated operator-attribution suggestions accepted upstream, read from the
 * public OSM changeset feed via the declared hashtag.
 *
 *   - `fixtures` mode — the committed sample (`leverage-fixture.ts`).
 *   - `export` mode — `<exportDir>/web/leverage.json`, produced by
 *     `sig-tasks osm-feed pull --out <dir>` (`tasks.osm_feed.leverage_metric_json`).
 *
 * `export` mode fails LOUD if the artifact is missing — never a silent fall-back to
 * fixtures (that would fabricate the metric). The record carries only the hashtag,
 * the accepted count, and the attributed changeset ids — no OSM user data
 * (Part VIII §0.7).
 */
export function getLeverageMetric(): LeverageMetric {
  if (dataSource() === "fixtures") return LEVERAGE_METRIC_FIXTURE;
  const path = `${exportDir()}/web/leverage.json`;
  let raw: string;
  try {
    raw = readFileSync(path, "utf-8");
  } catch (cause) {
    throw new Error(
      `SIG_DATA_SOURCE=export but the leverage metric artifact is missing: ${path}. ` +
        `Run \`sig-tasks osm-feed pull --out <dir>\` first (P21.7).`,
      { cause },
    );
  }
  const parsed = JSON.parse(raw) as Partial<LeverageMetric>;
  if (
    typeof parsed.hashtag !== "string" ||
    typeof parsed.accepted_operator_attributions !== "number" ||
    !Array.isArray(parsed.attributed_changeset_ids)
  ) {
    throw new Error(`${path}: not a valid leverage metric record`);
  }
  return parsed as LeverageMetric;
}
