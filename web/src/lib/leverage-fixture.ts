// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The §7 contribution-back leverage metric (P21.7, SIG-CONTRIB-016e).
 *
 * "Count of SIG-originated operator-attribution suggestions accepted upstream" —
 * read from the public OSM changeset feed by filtering on the declared changeset
 * hashtag (`tasks.contribution.CHANGESET_HASHTAG`). The record carries ONLY the
 * hashtag, the accepted count, and the attributed changeset ids — never any OSM user
 * data (Part VIII §0.7). This committed fixture mirrors the shape
 * `tasks.osm_feed.leverage_metric_json` emits; `export` mode reads the real one.
 */
export interface LeverageMetric {
  /** The declared changeset hashtag the metric keys on. */
  hashtag: string;
  /** Count of accepted (upstream, not reverted) hashtag-bearing changesets. */
  accepted_operator_attributions: number;
  /** The public changeset ids attributed (accepted or later reverted). */
  attributed_changeset_ids: string[];
}

/**
 * The fixtures-mode sample. It matches the committed replay fixtures
 * (`tests/tasks/fixtures/osm_changesets_*.xml`): three accepted attributions plus
 * one still-open changeset that is attributed but not yet counted as accepted.
 */
export const LEVERAGE_METRIC_FIXTURE: LeverageMetric = {
  hashtag: "#sig_operator_attribution",
  accepted_operator_attributions: 3,
  attributed_changeset_ids: ["140000001", "140000002", "140000004", "140000005"],
};
