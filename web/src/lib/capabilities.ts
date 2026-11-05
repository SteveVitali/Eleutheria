// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.64 (UXK14-6 / DR-K14-05 → SIG-UI-139; K14 §2.2; CP-9) — the capability
 * table: the ONE registry every capability statement on home and About reads.
 *
 * A capability is a verb the release demonstrates, never an aspiration: each
 * row carries a metric measured over the release's own data (dossiers,
 * contested figures, evidence artifacts, tracked decisions, an activated
 * release). A row whose metric is 0 renders its "being built" state — the
 * capability is named, never promised (K14 NEW-11 / SIG-ENG-042). A verb is
 * never removed silently: a release that cannot show it shows the honest
 * state instead.
 */

import { withBase } from "./paths";
import {
  getDossierIndex,
  getEvidence,
  getLatestReleaseTarget,
  getWatchV2,
} from "./data";
import { getDossiers } from "./data";

export type CapabilityId = "find" | "trace" | "compare" | "follow" | "take";

export interface CapabilityMetrics {
  /** Published dossier pages in this release (the Find metric). */
  dossiers: number;
  /**
   * Published evidence artifacts (the Trace metric — every figure's pointer
   * resolves into the release's evidence/manifest bytes, and the artifact
   * count is what the chain ends on).
   */
  evidenceArtifacts: number;
  /**
   * Material dossier figures whose values are contested (the Compare metric —
   * a published disagreement the reader can open, never a count of
   * disagreements that might exist).
   */
  contestedFigures: number;
  /** Tracked decisions on the watch (the Follow metric — K14's "the watch is empty" test). */
  trackedDecisions: number;
  /**
   * Whether an activated release is bound — the pinned-citation / downloads
   * half of Take (G3). 1 or 0, never a higher invented count.
   */
  activatedRelease: number;
}

export interface Capability {
  id: CapabilityId;
  /** The verb label — "Find". */
  verb: string;
  /** The plain promise — rendered only when `live` (a copy-batch row). */
  promise: string;
  /** The surface the verb links to when live; `null` keeps the row unlinked. */
  href: string;
  /** The metric value the row is bound to. */
  metric: number;
  /** `metric > 0` — the release demonstrates the capability. */
  live: boolean;
  /** The honest state rendered when the metric is 0 — "{label} — being built". */
  beingBuilt: string;
}

/** The five K14 §2.2 verbs, in design order. */
const CAPABILITY_DEFS: readonly {
  id: CapabilityId;
  verb: string;
  promise: string;
  href: string;
  metric: (m: CapabilityMetrics) => number;
  beingBuilt: string;
}[] = [
  {
    id: "find",
    verb: "Find",
    promise: "Look up a state, county or city and see what the record holds.", // copy: CP-01
    href: withBase("dossier/"),
    metric: (m) => m.dossiers,
    beingBuilt: "Place lookup — being built", // copy: CB-01
  },
  {
    id: "trace",
    verb: "Trace",
    promise: "Follow any figure to the sources and rows behind it.", // copy: CP-02
    href: withBase("evidence/"),
    metric: (m) => m.evidenceArtifacts,
    beingBuilt: "Figure tracing — being built", // copy: CB-02
  },
  {
    id: "compare",
    verb: "Compare",
    promise: "See where sources agree, disagree, or say nothing.", // copy: CP-03
    href: withBase("coverage-metrics/"),
    metric: (m) => m.contestedFigures,
    beingBuilt: "Source disagreements — being built", // copy: CB-03
  },
  {
    id: "follow",
    verb: "Follow",
    promise: "Know what is up for a decision, and subscribe.", // copy: CP-04
    href: withBase("watch/"),
    metric: (m) => m.trackedDecisions,
    // K14 §2.2's verbatim being-built state for the empty watch.
    beingBuilt: "Decision tracking — being built", // copy: CB-04
  },
  {
    id: "take",
    verb: "Take",
    promise: "Cite a pinned page, print a council brief, download the data.", // copy: CP-05
    href: withBase("data/"),
    metric: (m) => m.activatedRelease,
    beingBuilt: "Pinned citations — being built", // copy: CB-05
  },
];

/** The capability table for one release metric set — every row, live or "being built". */
export function capabilityTable(metrics: CapabilityMetrics): Capability[] {
  return CAPABILITY_DEFS.map((def) => {
    const metric = def.metric(metrics);
    return {
      id: def.id,
      verb: def.verb,
      promise: def.promise,
      href: def.href,
      metric,
      live: metric > 0,
      beingBuilt: def.beingBuilt,
    };
  });
}

/**
 * The metric set measured over this release's data layer — the single seam
 * (ADR-066) both pages read. In fixtures mode the committed corpus stands in
 * for the release bytes; under `SIG_DATA_SOURCE=export` the same fields come
 * from the emitted artifacts.
 */
export function releaseCapabilityMetrics(): CapabilityMetrics {
  const dossiers = getDossiers();
  const contestedFigures = dossiers.reduce(
    (n, d) =>
      n +
      d.sections.reduce(
        (k, s) => k + (s.figures ?? []).filter((f) => f.contested === true).length,
        0,
      ),
    0,
  );
  return {
    dossiers: getDossierIndex().length,
    evidenceArtifacts: getEvidence().artifacts.length,
    contestedFigures,
    trackedDecisions: getWatchV2().items.length,
    activatedRelease: getLatestReleaseTarget() === null ? 0 : 1,
  };
}
