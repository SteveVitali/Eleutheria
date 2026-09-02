# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The six downstream application classes as design targets (§38.4, SIG-EXPORT-010/011)."""

from __future__ import annotations

import pytest

from exports import downstream as DS

# The capabilities a full release + the surrounding surfaces (P14.1 API, procurement
# feed) provide. Assembled from the export bundle plus the other tickets' surfaces.
FULL_CAPABILITIES = {
    "parquet",
    "geojson",
    "pmtiles",
    "csv",
    "jsonl",
    "crosswalk",
    "odbl_asset_layer",
    "zenodo_doi",
    "json_api",
    "evidence_links",
    "belief_pinned_permalinks",
    "jurisdiction_slice",
    "procurement_feed",
    "ical_rss",
    "edge_list",
}


def test_there_are_exactly_six_classes() -> None:
    assert len(DS.DOWNSTREAM_CLASSES) == 6


def test_full_portfolio_serves_every_class() -> None:
    DS.assert_all_served(FULL_CAPABILITIES)
    assert all(c.served for c in DS.validate(FULL_CAPABILITIES))


def test_missing_capability_is_reported_as_a_design_defect() -> None:
    # SIG-EXPORT-010: a class with no serving artifact is an export-design defect.
    caps = FULL_CAPABILITIES - {"pmtiles"}
    unserved = DS.defects(caps)
    assert any(c.application_class.key == "route_privacy" for c in unserved)
    with pytest.raises(DS.DownstreamDesignDefect):
        DS.assert_all_served(caps)


def test_route_privacy_and_researcher_artifacts_must_be_separate() -> None:
    # SIG-EXPORT-011: the device-alone layer and the joined graph are separate files.
    DS.assert_separate_serving_artifacts(
        ["osm_physical/devices.pmtiles"], ["sig_graph/claims.parquet"]
    )
    with pytest.raises(DS.DownstreamDesignDefect):
        DS.assert_separate_serving_artifacts(
            ["shared/everything.parquet"], ["shared/everything.parquet"]
        )
