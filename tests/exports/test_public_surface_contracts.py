# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Guards the frozen per-page data contracts artifact (P27.1, LAUNCH.1, deliverable 3).

The contract is a committed JSON-schema doc that MUST cover all ten public surfaces and MUST point
each surface at a real ``web/src/lib`` source-of-truth interface, so a future drift is caught here.
"""

from __future__ import annotations

import json
import re

from support import REPO_ROOT

SCHEMA = REPO_ROOT / "docs" / "build" / "reports" / "public_surface_contracts.schema.json"

TEN_SURFACES = {
    "dossier_index",
    "jurisdiction_dossier",
    "map_layer",
    "network",
    "data_freshness",
    "coverage",
    "watch",
    "evidence",
    "corrections",
    "research_queue",
}


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_schema_is_valid_json_and_draft_2020_12() -> None:
    doc = _schema()
    assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert doc["type"] == "object"


def test_covers_all_ten_public_surfaces() -> None:
    doc = _schema()
    assert set(doc["properties"]) == TEN_SURFACES
    assert set(doc["required"]) == TEN_SURFACES


def test_every_surface_names_a_real_web_interface() -> None:
    doc = _schema()
    for name, surface in doc["properties"].items():
        assert "x_source" in surface, name
        # Extract the web/src/lib/*.ts files referenced and assert they exist.
        files = re.findall(r"web/src/lib/[\w./-]+\.ts", surface["x_source"])
        assert files, name
        for rel in files:
            assert (REPO_ROOT / rel).exists(), f"{name}: missing {rel}"


def test_coverage_metric_forbids_a_population_total() -> None:
    # The "never a bare total" invariant is baked into the frozen contract (SIG-METRIC-010).
    defs = _schema()["$defs"]["CoverageMetric"]
    assert defs["properties"]["is_population_total"] == {
        "const": False,
        "description": defs["properties"]["is_population_total"]["description"],
    }
    assert "denominator" in defs["required"]


def test_map_asset_supports_null_point_for_sensitive_tiers() -> None:
    # Coordinate reduction (§19.4/§43.3): a tier-3/mobile/unknown asset publishes no point.
    props = _schema()["$defs"]["MapAsset"]["properties"]
    assert props["lat"]["type"] == ["number", "null"]
    assert props["tier"]["enum"] == [0, 1, 2, 3]


def test_network_edge_keeps_the_three_access_kinds_distinct() -> None:
    enum = _schema()["$defs"]["NetworkEdge"]["properties"]["access_kind"]["enum"]
    assert enum == ["configured_access", "observed_use", "declared_policy"]
