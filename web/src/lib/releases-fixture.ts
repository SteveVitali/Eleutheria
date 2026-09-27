// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The fixtures-mode release catalog (P32.13): ONE demo activated publication
 * so the /releases/ index exercises the real rendering path in fixtures mode —
 * labelled demonstration data, never a claim of a live release.
 */
import type { ReleaseCatalog } from "./releases";

export const RELEASE_CATALOG_FIXTURE: ReleaseCatalog = {
  schema: "sig.publication-catalog/1",
  publications: [
    {
      schema: "sig.publication/1",
      publication_id: "p-0000000000000000000000000000000000000000000000000000000000000001",
      descriptor_sha256: "0".repeat(64),
      manifest_sha256: "1".repeat(64),
      data_release_id: "sig-2026-09-27-demo",
      reproducibility: {
        as_of_world: "2026-09-27",
        as_of_belief: "2026-09-27",
        ruleset_version: "p27.3/1.0.0",
        resolver_version: "0.0.0",
        policy_version: "publication-eligibility/1",
      },
      compartments: [
        { compartment: "sig_graph", license: "CC-BY-4.0", record_count: 4, artifact_count: 9 },
      ],
      record_count: 4,
      artifact_count: 12,
      completeness: { state: "complete" },
    },
  ],
};
