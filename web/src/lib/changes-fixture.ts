// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.40 (R11-K13-CHG-01, SIG-UI-072): the fixtures-mode changes document —
 * a demonstration `sig.release-changes/1` diff (a demo second release
 * against a demo first), exercising the real rendering + feed paths in
 * fixtures mode. Labelled demonstration data, never a claim of a live
 * release — the same posture RELEASE_CATALOG_FIXTURE takes.
 *
 * The demo events cover every class the surface separates: record
 * added/removed/changed under real fixture slug paths and source ids
 * (`usa/ok/…`, `okc_camera_registry`), a `source_withdrawn` removal (the
 * world-changed class), a `claim_anchors` change (the CONF-03a disclosed
 * re-mint noise) and all four source-lifecycle kinds.
 */

import type { ReleaseChangesDoc } from "./changes";

const PREV_PUB = "p-" + "0".repeat(63) + "1";
const CUR_PUB = "p-" + "0".repeat(63) + "2";

export const CHANGES_FIXTURE: ReleaseChangesDoc = {
  index: {
    schema: "sig.release-changes/1",
    release: {
      label: "sig-2026-10-15.1",
      publication_id: CUR_PUB,
      as_of_world: "2026-10-15",
      as_of_belief: "2026-10-15",
    },
    previous: {
      label: "sig-2026-09-27.1",
      publication_id: PREV_PUB,
      as_of_world: "2026-09-27",
      as_of_belief: "2026-09-27",
    },
    baseline: false,
    compared_fields: [
      "claim_anchors",
      "coverage",
      "dedup",
      "inferred",
      "label",
      "layer",
      "jurisdiction",
      "location",
      "review",
      "technology",
    ],
    excluded_fields: ["schema", "source_refs", "claim_statements", "evidence_refs"],
    compartments: {
      sig_graph: { added: 2, removed: 2, changed: 2, records: 7, previous_records: 6 },
    },
    totals: { added: 2, removed: 2, changed: 2, records: 7, previous_records: 6 },
    versions: { ruleset_version: { previous: "p27.3/1.0.0", current: "p27.3/1.0.1" } },
    sources_state: "evaluated",
    disclosures: [
      "Sources and confidence are never compared per record — the changed-columns set is declared in compared_fields (J3 §8.4).",
      "Claim ids are not yet identity-stable across releases (SIG-CONF-003 unlanded): a claim_anchors diff may reflect claim re-minting, not a world change.",
      "Demonstration fixture — not a live release's diff.",
    ],
    files: [],
  },
  sources: {
    schema: "sig.release-source-changes/1",
    state: "evaluated",
    added: [
      { source_id: "demo_permitted_portal", name: "Demo permitted portal", lifecycle_state: "published" },
    ],
    retired: [
      { source_id: "demo_gated_registry", name: "Demo gated registry", lifecycle_state: "withdrawn" },
    ],
    newly_failing: [
      {
        source_id: "okc_council_minutes",
        name: "OKC council minutes",
        previous_lifecycle_state: "published",
        lifecycle_state: "gated",
      },
    ],
    lane_changed: [
      { source_id: "demo_seed_load", previous_lane: "raw-ok", lane: "raw-review" },
    ],
  },
  feed: {
    schema: "sig.release-changes-feed/1",
    release: {
      label: "sig-2026-10-15.1",
      publication_id: CUR_PUB,
      as_of_world: "2026-10-15",
      as_of_belief: "2026-10-15",
    },
    previous: {
      label: "sig-2026-09-27.1",
      publication_id: PREV_PUB,
      as_of_world: "2026-09-27",
      as_of_belief: "2026-09-27",
    },
    baseline: false,
    events: [
      {
        artifact_id: "sig_graph:deployment:ent-src_a-3",
        field: "record",
        change_type: "added",
        old_value: null,
        new_value: { label: "Renamed site 3", entity_id: "ent-src_a-3" },
        old_date: "2026-09-27",
        new_date: "2026-10-15",
        compartment: "sig_graph",
        entity_type: "deployment",
        entity_id: "ent-src_a-3",
        label: "Renamed site 3",
        jurisdiction: "usa/ok/oklahoma-city-4064000",
        source_ids: ["okc_camera_registry"],
      },
      {
        artifact_id: "sig_graph:deployment:ent-src_a-4",
        field: "record",
        change_type: "added",
        old_value: null,
        new_value: { label: "Demo Norman site", entity_id: "ent-src_a-4" },
        old_date: "2026-09-27",
        new_date: "2026-10-15",
        compartment: "sig_graph",
        entity_type: "deployment",
        entity_id: "ent-src_a-4",
        label: "Demo Norman site",
        jurisdiction: "usa/ok/norman-city-4055000",
        source_ids: ["okc_camera_registry", "demo_permitted_portal"],
      },
      {
        artifact_id: "sig_graph:deployment:ent-src_a-0",
        field: "label",
        change_type: "changed",
        old_value: null,
        new_value: null,
        old_date: "2026-09-27",
        new_date: "2026-10-15",
        compartment: "sig_graph",
        entity_type: "deployment",
        entity_id: "ent-src_a-0",
        label: "Renamed site 0",
        jurisdiction: "usa/ok/oklahoma-city-4064000",
        source_ids: ["okc_camera_registry"],
      },
      {
        artifact_id: "sig_graph:deployment:ent-src_a-0",
        field: "claim_anchors",
        change_type: "changed",
        old_value: null,
        new_value: null,
        old_date: "2026-09-27",
        new_date: "2026-10-15",
        compartment: "sig_graph",
        entity_type: "deployment",
        entity_id: "ent-src_a-0",
        label: "Renamed site 0",
        jurisdiction: "usa/ok/oklahoma-city-4064000",
        source_ids: ["okc_camera_registry"],
      },
      {
        artifact_id: "sig_graph:deployment:ent-src_a-1",
        field: "record",
        change_type: "removed",
        old_value: { label: "Retired site 1", entity_id: "ent-src_a-1" },
        new_value: null,
        old_date: "2026-09-27",
        new_date: "2026-10-15",
        reason: "source_withdrawn",
        compartment: "sig_graph",
        entity_type: "deployment",
        entity_id: "ent-src_a-1",
        label: "Retired site 1",
        jurisdiction: "usa/ok/oklahoma-county-40109",
        source_ids: ["demo_gated_registry"],
      },
      {
        artifact_id: "sig_graph:deployment:ent-src_a-2",
        field: "record",
        change_type: "removed",
        old_value: { label: "Re-keyed site 2", entity_id: "ent-src_a-2" },
        new_value: null,
        old_date: "2026-09-27",
        new_date: "2026-10-15",
        reason: "superseded",
        compartment: "sig_graph",
        entity_type: "deployment",
        entity_id: "ent-src_a-2",
        label: "Re-keyed site 2",
        jurisdiction: "usa/tx/harris-county-48201",
        source_ids: ["okc_camera_registry"],
      },
    ],
    event_count: 6,
    truncated: false,
    disclosures: [
      "Sources and confidence are never compared per record — the changed-columns set is declared in compared_fields (J3 §8.4).",
      "Claim ids are not yet identity-stable across releases (SIG-CONF-003 unlanded): a claim_anchors diff may reflect claim re-minting, not a world change.",
      "Demonstration fixture — not a live release's diff.",
    ],
  },
};
