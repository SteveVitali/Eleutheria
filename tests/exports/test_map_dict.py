# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.17 (MAP-01b): the ``sig.map-tiles/2`` full property emit,
``sig.map-dict/1`` dictionary and the real declared-scope coverage rule
(D-K1-4 = yes)."""

from __future__ import annotations

import json

from exports import map_dict as MD
from exports import tiles as T

_SLICE_GEOJSON = json.dumps(
    {
        "type": "FeatureCollection",
        "features": [
            # one record seen by two registry sources at the SAME point →
            # merged; corroborated (st=0, UXR-14 registry-source proxy).
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-97.5, 35.5]},
                "properties": {
                    "entity_id": "e1",
                    "entity_type": "deployment",
                    "sensitivity_tier": 0,
                    "label": "OKC pole cam",
                    "technology": "alpr-fixed",
                    "source_id": "src-a",
                    "jurisdiction_key": "us.census.geoid.place:4055000",
                    "first_seen": 202401,
                    "last_seen": 202503,
                    "operator_label": "Oklahoma City PD",
                    "vendor_key": "flock",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-97.5, 35.5]},
                "properties": {
                    "entity_id": "e1",
                    "entity_type": "deployment",
                    "sensitivity_tier": 0,
                    "label": "OKC pole cam",
                    "technology": "alpr-fixed",
                    "source_id": "src-b",
                    "jurisdiction_key": "us.census.geoid.place:4055000",
                    "first_seen": 202402,
                    "last_seen": 202506,
                },
            },
            # a second record, single source, conflicting point → contested.
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-97.5, 35.5]},
                "properties": {
                    "entity_id": "e2",
                    "entity_type": "deployment",
                    "sensitivity_tier": 0,
                    "source_id": "src-a",
                    "point_status": "conflicted",
                },
            },
        ],
    }
).encode()


def test_v2_emit_merges_record_slices_and_stamps_the_full_property_set() -> None:
    doc = json.loads(T.map_tile_geojson(_SLICE_GEOJSON, "sig_graph"))
    sites = [f for f in doc["features"] if f["tippecanoe"]["layer"] == "sites"]
    # e1's two same-point slices merge to ONE feature; e2 keeps its own —
    # a record is drawn once per published position, never stacked.
    rks = sorted(f["properties"]["rk"] for f in sites)
    assert rks == ["sig_graph:deployment:e1", "sig_graph:deployment:e2"]
    p1 = next(f["properties"] for f in sites if f["properties"]["rk"].endswith(":e1"))
    # the full §3.3 vocabulary, contract keys only
    assert set(p1) <= T.ALLOWED_SITE_KEYS
    assert p1["lb"] == "OKC pole cam"
    assert p1["j"] == "us.census.geoid.place:4055000"
    assert p1["st"] == 0  # two registry sources → corroborated (UXR-14 proxy)
    assert p1["f"] == 202401 and p1["l"] == 202506  # merged min/max
    assert p1["op"] == "Oklahoma City PD"
    assert p1["co"] == 2  # two distinct records share the exact coordinate
    p2 = next(f["properties"] for f in sites if f["properties"]["rk"].endswith(":e2"))
    assert p2["st"] == 2  # open contradiction on location → contested
    # cells: n counts merged records; facet counts ride beside it
    cells = [f["properties"] for f in doc["features"] if f["tippecanoe"]["layer"] == "cells"]
    assert all(c["n"] == c["s1"] + c["sx"] for c in cells)
    band9 = [c for c in cells if c["n"] >= 2]
    assert band9 and all(c["ns"] == 2 for c in band9)  # src-a + src-b


def test_v2_emit_indexes_through_the_dictionary() -> None:
    doc = json.loads(
        T.map_tile_geojson(
            _SLICE_GEOJSON,
            "sig_graph",
            source_index={("src-a", "sig_graph"): 0, ("src-b", "sig_graph"): 1},
            tech_codes={"alpr-fixed": 3},
            vendor_slots={"flock": 2},
        )
    )
    p1 = next(
        f["properties"]
        for f in doc["features"]
        if f["tippecanoe"]["layer"] == "sites" and f["properties"]["rk"].endswith(":e1")
    )
    assert p1["sr"] == 0 and p1["tc"] == 3 and p1["vd"] == 2


def test_map_dict_builds_sources_technologies_and_unplotted() -> None:
    rows = [
        {
            "source_id": "src-a",
            "_compartment": "sig_graph",
            "spdx": "CC-BY-4.0",
            "technology": "alpr-fixed",
            "vendor_key": "flock",
            "vendor_label": "Flock Safety",
            "jurisdiction_key": "us.census.geoid.place:4055000",
            "geometry": {"type": "Point", "coordinates": [-97.5, 35.5]},
            "tier": 0,
        },
        {
            "source_id": "src-b",
            "_compartment": "sig_graph",
            "spdx": "ODbL-1.0",
            "jurisdiction_key": "us.census.geoid.place:4055000",
            "geometry": None,
            "tier": 3,
        },
    ]
    doc, source_index = MD.build_map_dict(
        rows,
        release={"label": "p-test", "as_of_world": "2026-01-01"},
        source_names={"src-a": "Source A", "src-b": "Source B"},
        registry_sources={
            "src-a": {"name": "Source A", "publisher_type": "gov-open-data"},
            "src-b": {"name": "Source B", "publisher_type": "crowdsourced"},
        },
        tech_codes={"alpr-fixed": 1},
        vendor_slots={"flock": 1},
        vendor_labels={"flock": "Flock Safety"},
        jurisdictions={
            "us.census.geoid.place:4055000": {
                "name": "Oklahoma City",
                "level": "municipality",
                "bbox": [-98.0, 35.0, -97.0, 36.0],
            }
        },
        ancestor_chains={"us.census.geoid.place:4055000": ("iso3166-1:US", "iso3166-2:US-OK")},
    )
    assert doc["schema"] == "sig.map-dict/1"
    assert doc["corroboration_legend"] == MD.CORROBORATION_LEGEND
    assert len(doc["sources"]) == 2
    assert source_index[("src-b", "sig_graph")] == 1
    assert doc["sources"][1]["url"] == "/sources/src-b/"
    assert doc["jurisdictions"]["us.census.geoid.place:4055000"]["chain"] == [
        "iso3166-1:US",
        "iso3166-2:US-OK",
        "us.census.geoid.place:4055000",
    ]
    # tier-3 / no-point rows count in the per-jurisdiction unplotted table
    assert doc["unplotted"] == {"us.census.geoid.place:4055000": 1}
    assert doc["vendor_slots"] == [{"slot": 1, "key": "flock", "label": "Flock Safety"}]


def test_declared_scope_coverage_counts_scoped_sources_only() -> None:
    doc = MD.coverage_doc(
        {
            "us.census.geoid.county:40109": {
                "sources": ["dot_511_ok", "osm_overpass"],
                "technologies": ["alpr-fixed"],
            }
        },
        release={"label": "p-test"},
        scopes={"dot_511_ok": "iso3166-2:US-OK", "dot_511_tx": "iso3166-2:US-TX"},
        global_sources={"osm_overpass"},
        ancestors={"us.census.geoid.county:40109": ("iso3166-1:US", "iso3166-2:US-OK")},
        all_jkeys=["iso3166-2:US-OK", "us.census.geoid.county:40109", "us.census.geoid.county:48201"],
    )
    rows = doc["jurisdictions"]
    # the declared OK scope covers the state AND its descendants
    assert rows["us.census.geoid.county:40109"]["coverage"] == "covered"
    assert rows["us.census.geoid.county:40109"]["sources"] == ["dot_511_ok"]
    # the crowdsourced global is listed honestly, never counted
    assert rows["us.census.geoid.county:40109"]["global_sources_not_counted"] == ["osm_overpass"]
    # a jurisdiction no scoped source declares is not covered (D-K1-4)
    assert rows["us.census.geoid.county:48201"]["coverage"] == "not_covered"
    assert doc["rule_version"] == "declared-scope@1"
    assert doc["pending"] is False


def test_vendor_slot_map_top_eight_plus_other() -> None:
    counts = {f"v{i}": 100 - i for i in range(12)}
    slots = MD.vendor_slot_map(counts)
    assert slots["v0"] == 1 and slots["v7"] == 8
    assert slots["v8"] == 9 and slots["v11"] == 9  # beyond top-8 → "other"


def test_technology_codes_skip_retired_slugs(tmp_path) -> None:
    vocab = tmp_path / "technology.yaml"
    vocab.write_text(
        "domains:\n- slug: surveillance-vehicle\n"
        "  technologies:\n  - slug: alpr-fixed\n  - slug: alpr-old\n    status: retired\n"
        "  - slug: cctv-fixed\n",
        encoding="utf-8",
    )
    codes = MD.technology_codes(vocab)
    # active slugs code in file order; retired never takes a slot
    assert "alpr-old" not in codes
    assert codes["alpr-fixed"] == 1 and codes["cctv-fixed"] == 2
