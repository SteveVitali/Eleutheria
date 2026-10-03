// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The /evidence/ interim artifact list (P34.20, K8 NEW-6 / SIG-EVUI-D05+D08).
 *
 * Until claims are bound to publishable document views, the evidence index
 * lists what the release actually carries: the published evidence artifacts
 * from `evidence.json`, grouped by their source. Every row names a human
 * title and a plain-language type; a synthetic capture is labelled a run
 * record — honest that SIG did not store the document — and an upstream
 * URL (emitted only where the export's effective-rights gate allows it,
 * S-6) is labelled as the source's own link recorded as a claim, never
 * presented as a capture SIG holds.
 *
 * Pure data + logic — the page supplies the markup; the copy constants are
 * the batch-tracked public sentences for this section.
 */
import type { EvidenceArtifact } from "./recommender";

/** The section heading on /evidence/ (batch-tracked copy). */
export const ARTIFACTS_HEADING = "Published artifacts";

/** The section's one-line framing (batch-tracked copy). */
export const ARTIFACTS_INTRO =
  "The artifacts this release carries, grouped by source. A run record is a build-time record, not a stored document.";

/** The honest label a synthetic capture carries (batch-tracked copy; SIG-EVUI-D04). */
export const RUN_RECORD_LABEL = "run record — SIG did not store this document";

/**
 * The label an upstream document link carries (batch-tracked copy; K8 NEW-9):
 * the source's own URL, recorded as a claim — never presented as a capture.
 */
export const UPSTREAM_LINK_LABEL = "the source's own link (recorded as a claim)";

/** The note when a release carries no artifacts at all (batch-tracked copy). */
export const ARTIFACTS_EMPTY =
  "No published artifacts in this release — the list appears once the export carries them.";

/** One group in the by-source artifact list. */
export interface ArtifactGroup {
  /** The artifact `source` id (stable key). */
  sourceId: string;
  /** The display name — the registry `source_name` when the export carried it, else the id. */
  sourceName: string;
  artifacts: EvidenceArtifact[];
}

/**
 * Group the published artifacts by source, ordered by display name, with the
 * artifacts inside each group ordered by title. The registry `source_name`
 * wins over the raw id only when the export emitted it — never a fabricated
 * name.
 */
export function artifactsBySource(artifacts: EvidenceArtifact[]): ArtifactGroup[] {
  const groups = new Map<string, ArtifactGroup>();
  for (const artifact of artifacts) {
    const existing = groups.get(artifact.source);
    if (existing) {
      if (artifact.source_name) existing.sourceName = artifact.source_name;
      existing.artifacts.push(artifact);
    } else {
      groups.set(artifact.source, {
        sourceId: artifact.source,
        sourceName: artifact.source_name ?? artifact.source,
        artifacts: [artifact],
      });
    }
  }
  const out = [...groups.values()];
  for (const group of out) {
    group.artifacts.sort((a, b) => a.title.localeCompare(b.title));
  }
  out.sort(
    (a, b) => a.sourceName.localeCompare(b.sourceName) || a.sourceId.localeCompare(b.sourceId),
  );
  return out;
}

/** The plain-language artifact-type label (`meeting_minutes` → "meeting minutes"). */
export function artifactTypeLabel(artifactType: string): string {
  return artifactType.replace(/_/g, " ");
}

/** True when the artifact's latest capture is a synthetic placeholder — a run record. */
export function isRunRecord(artifact: EvidenceArtifact): boolean {
  return artifact.capture_classification === "synthetic";
}
