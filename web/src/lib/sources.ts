// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interim sources-and-licences table (P34.17 / R1.8-as-reassigned: P34.19's
 * disclosure ships on this page instead of a withdrawal, and wrong per-source
 * credits are replaced by notice N-4 until P34.21b's attribution re-export).
 *
 * The table is derived at build time from the export's own compartment rows —
 * `sites.jsonl` `_rights` per row — so the licence and credit shown are exactly
 * what the download bytes carry, never a hand-maintained list. Fixtures mode
 * ships a small demonstration set.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolveSourceId, resolveTextIds } from "./alias";

export interface SourceLicenceRow {
  sourceId: string;
  /** The licence(s) the source's rows are filed under (from `_rights.license`). */
  licenses: string[];
  /** The compartment(s) the source's rows land in. */
  compartments: string[];
  /** Row count across the export. */
  rows: number;
  /** Whether the licence terms require attribution. */
  attributionRequired: boolean;
  /** The credit string the rows carry, if any. */
  attribution: string | null;
  /** The source's own terms URL, when the rows record one. */
  termsUrl: string | null;
  /**
   * True when the credit is WRONG or absent where the licence requires it —
   * the page then renders notice N-4 ("Attribution for this source is being
   * corrected…") in place of the credit until P34.21b's re-export fixes it.
   * Covers the recorded classes (F-387/F-405): required-but-empty credit and
   * the misattribution to "DeFlock community map" on rows that are not DeFlock's.
   */
  creditUnderCorrection: boolean;
}

interface RightsBlock {
  source_id?: unknown;
  license?: unknown;
  attribution?: unknown;
  attribution_required?: unknown;
  terms_url?: unknown;
}

interface SiteRow {
  source_id?: unknown;
  _rights?: RightsBlock;
}

/**
 * Handle-bearing source ids (the `camreg_<handle>` set P34.18 re-keys, C3
 * NEW-2) appear here as the source's true registered identifier — a table row
 * is data, not a page whose URL or title embeds the handle (R1.11's scope is
 * page routes, which this build does not emit for source ids at all).
 */

/**
 * Aggregate the export's compartment `sites.jsonl` rows into one row per source
 * id. `exportDir` is the national export root; absent in fixtures mode.
 */
export function sourceLicenceTable(exportDir: string): SourceLicenceRow[] {
  const agg = new Map<string, SourceLicenceRow & { licenseSet: Set<string>; compSet: Set<string>; attrSet: Set<string>; termsSet: Set<string> }>();
  for (const entry of readdirSync(exportDir)) {
    const path = `${exportDir}/${entry}/sites.jsonl`;
    if (!existsSync(path)) continue;
    for (const line of readFileSync(path, "utf-8").split("\n")) {
      const t = line.trim();
      if (!t) continue;
      const row = JSON.parse(t) as SiteRow;
      // P34.18 / ADR-178: already-published export bytes may still carry a
      // retired id until P34.21b's re-export — resolve so the rendered table
      // can never repeat a handle.
      const rawSid = typeof row.source_id === "string" ? row.source_id : null;
      const sid = rawSid === null ? null : resolveSourceId(rawSid);
      if (!sid) continue;
      const rights = row._rights ?? {};
      let a = agg.get(sid);
      if (!a) {
        a = {
          sourceId: sid,
          licenses: [],
          compartments: [],
          rows: 0,
          attributionRequired: false,
          attribution: null,
          termsUrl: null,
          creditUnderCorrection: false,
          licenseSet: new Set(),
          compSet: new Set(),
          attrSet: new Set(),
          termsSet: new Set(),
        };
        agg.set(sid, a);
      }
      a.rows += 1;
      a.compSet.add(entry);
      if (typeof rights.license === "string") a.licenseSet.add(rights.license);
      if (rights.attribution_required === true) a.attributionRequired = true;
      if (typeof rights.attribution === "string" && rights.attribution.trim()) {
        a.attrSet.add(resolveTextIds(rights.attribution.trim()));
      }
      if (typeof rights.terms_url === "string") a.termsSet.add(resolveTextIds(rights.terms_url));
    }
  }
  const rows: SourceLicenceRow[] = [];
  for (const a of agg.values()) {
    const attribution = a.attrSet.size ? [...a.attrSet].sort().join("; ") : null;
    // F-387: "DeFlock community map" is the recorded mis-credit — it stands on
    // rows whose source is not a DeFlock feed; flag the credit, keep the source.
    const deflockMiscredit =
      attribution !== null &&
      attribution.toLowerCase().includes("deflock") &&
      !a.sourceId.toLowerCase().includes("deflock");
    rows.push({
      sourceId: a.sourceId,
      licenses: [...a.licenseSet].sort(),
      compartments: [...a.compSet].sort(),
      rows: a.rows,
      attributionRequired: a.attributionRequired,
      attribution,
      termsUrl: a.termsSet.size ? [...a.termsSet].sort()[0]! : null,
      creditUnderCorrection: (a.attributionRequired && !attribution) || deflockMiscredit,
    });
  }
  return rows.sort((x, y) => x.sourceId.localeCompare(y.sourceId));
}

/** The small fixtures-mode demonstration set (clearly demo data, §3.1). */
export const SOURCES_FIXTURE: SourceLicenceRow[] = [
  {
    sourceId: "demo-municipal-portal",
    licenses: ["CC0-1.0"],
    compartments: ["portal"],
    rows: 38,
    attributionRequired: false,
    attribution: "Demo municipal portal (demonstration entry)",
    termsUrl: "https://example.invalid/demo-portal",
    creditUnderCorrection: false,
  },
  {
    sourceId: "demo-records-request",
    licenses: ["CC-BY-4.0"],
    compartments: ["public_record"],
    rows: 3,
    attributionRequired: true,
    attribution: null,
    termsUrl: null,
    creditUnderCorrection: true,
  },
];
