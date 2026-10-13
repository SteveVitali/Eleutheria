// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The /evidence/ interim artifact list (P34.20, K8 NEW-6 / SIG-EVUI-D05+D08):
// the published artifacts from evidence.json grouped by source, run-record
// honesty on synthetic captures, and the S-6-labelled upstream link — tested
// independently of any markup.
import { describe, it, expect } from "vitest";
import {
  artifactTypeLabel,
  artifactsBySource,
  isRunRecord,
} from "../../src/lib/evidence-artifacts";
import type { EvidenceArtifact } from "../../src/lib/recommender";

function artifact(over: Partial<EvidenceArtifact>): EvidenceArtifact {
  return {
    artifact_id: "a",
    subject_id: "s",
    title: "t",
    source: "src",
    artifact_type: "news_article",
    directness: "D1",
    currency: "C1",
    touches_open_contradiction: false,
    answers_open_task: false,
    capture_status: "retrievable",
    permalink: "",
    as_of: "2026-09-27",
    ...over,
  };
}

describe("artifactsBySource (K8 NEW-6)", () => {
  it("groups by source, ordered by display name, artifacts by title — losing no rows", () => {
    const rows = [
      artifact({ artifact_id: "1", source: "src_b", source_name: "Beta", title: "Zeta" }),
      artifact({ artifact_id: "2", source: "src_a", source_name: "Alpha", title: "Mid" }),
      artifact({ artifact_id: "3", source: "src_b", source_name: "Beta", title: "Alpha" }),
      artifact({ artifact_id: "4", source: "src_c", title: "Solo" }), // no source_name → id
    ];
    const groups = artifactsBySource(rows);
    // every input row lands exactly once (the count AC)
    expect(groups.reduce((n, g) => n + g.artifacts.length, 0)).toBe(rows.length);
    expect(groups.map((g) => g.sourceName)).toEqual(["Alpha", "Beta", "src_c"]);
    const beta = groups.find((g) => g.sourceId === "src_b")!;
    expect(beta.artifacts.map((a) => a.title)).toEqual(["Alpha", "Zeta"]);
  });

  it("prefers the registry source_name, falling back to the id — never fabricating", () => {
    const groups = artifactsBySource([
      artifact({ artifact_id: "1", source: "src_x", source_name: "Registry Name" }),
      artifact({ artifact_id: "2", source: "src_y" }),
    ]);
    expect(groups.find((g) => g.sourceId === "src_x")!.sourceName).toBe("Registry Name");
    expect(groups.find((g) => g.sourceId === "src_y")!.sourceName).toBe("src_y");
  });
});

describe("honest labels (SIG-EVUI-D04, K8 NEW-9)", () => {
  it("only a synthetic capture classification is a run record", () => {
    expect(isRunRecord(artifact({ capture_classification: "synthetic" }))).toBe(true);
    expect(isRunRecord(artifact({ capture_classification: "actual" }))).toBe(false);
    expect(isRunRecord(artifact({ capture_classification: "legacy" }))).toBe(false);
    expect(isRunRecord(artifact({}))).toBe(false);
  });

  it("the artifact type renders as a plain-language label", () => {
    expect(artifactTypeLabel("meeting_minutes")).toBe("meeting minutes");
    expect(artifactTypeLabel("contract")).toBe("contract");
    expect(artifactTypeLabel("news_article")).toBe("news article");
  });
});
