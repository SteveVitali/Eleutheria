// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The release catalog types (P32.13 / ADR-132 — SIG-FIND-001/002). Mirrors the
 * `sig.publication/1` catalog entry emitted into every activated release
 * (`releases/<publication_id>/catalog_entry.json`) and the registry catalog.
 */

export interface ReleaseCompartment {
  compartment: string;
  license: string;
  record_count: number;
  artifact_count?: number;
}

export interface ReleaseCatalogEntry {
  schema: string;
  publication_id: string;
  descriptor_sha256: string;
  manifest_sha256?: string;
  data_release_id: string;
  reproducibility: {
    as_of_world: string;
    as_of_belief: string;
    ruleset_version: string;
    resolver_version?: string;
    policy_version?: string;
  };
  compartments: ReleaseCompartment[];
  record_count: number;
  artifact_count?: number;
  completeness?: { state: string; failures?: string[] };
}

export interface ReleaseCatalog {
  schema: string;
  publications: ReleaseCatalogEntry[];
}
