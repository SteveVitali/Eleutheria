# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.map-tiles/2`` verifier (P35.52, ADR-156, K1-map §9.2): the six
contract checks over a built export directory — conservation, renderer parity,
precision/tier, size, metadata, and the report it lands at
``reports/tiles_verify.json``."""

from __future__ import annotations

import json
from pathlib import Path

from exports.manifest import canonical_json, tiles_index_document
from exports.tile_verify import TILES_VERIFY_SCHEMA, decode_mvt_tile, verify_export_tiles
from exports.tiles import (
    build_pmtiles,
    render_compartment_sites_pmtiles,
    tiles_index_entry,
    zxy_to_tileid,
)

_COMPARTMENT = "sig_graph"
_LICENCE = "CC-BY-4.0"
_ATTRIBUTION = "© The SIG project — CC-BY-4.0"

_FEATURES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.5164, 35.4676]},
            "properties": {
                "entity_id": "a1",
                "entity_type": "deployment",
                "sensitivity_tier": 0,
                "jurisdiction": "iso3166-2:US-OK",
                "source_ids": ["src-1"],
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.5164, 35.4676]},
            "properties": {
                "entity_id": "a2",
                "entity_type": "deployment",
                "sensitivity_tier": 0,
                "jurisdiction": "iso3166-2:US-OK",
                "source_ids": ["src-2"],
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-96.34, 43.55]},
            "properties": {
                "entity_id": "b1",
                "entity_type": "deployment",
                "sensitivity_tier": 1,
                "jurisdiction": "iso3166-2:US-ND",
                "source_ids": ["src-1"],
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-96.75, 46.88]},
            "properties": {
                "entity_id": "c1",
                "entity_type": "deployment",
                "sensitivity_tier": 2,
                "jurisdiction": "iso3166-2:US-ND",
                "source_ids": ["src-3"],
            },
        },
    ],
}
_GEOJSON = json.dumps(_FEATURES).encode()


def _export_dir(tmp_path: Path, geojson: bytes = _GEOJSON) -> Path:
    """A minimal built export: source geojson + archive + index + manifest."""
    root = tmp_path / "export"
    (root / _COMPARTMENT).mkdir(parents=True)
    (root / _COMPARTMENT / "sites.geojson").write_bytes(geojson)
    (root / "web" / "tiles").mkdir(parents=True)
    rendered = render_compartment_sites_pmtiles(_COMPARTMENT, geojson, _LICENCE)
    tile_path = f"web/tiles/{_COMPARTMENT}-sites.{rendered.sha256[:8]}.pmtiles"
    (root / tile_path).write_bytes(rendered.data)
    index = tiles_index_document(
        [
            tiles_index_entry(
                compartment=_COMPARTMENT,
                path=tile_path,
                license_id=_LICENCE,
                attribution=_ATTRIBUTION,
                rendered=rendered,
                source=f"{_COMPARTMENT}/sites.geojson",
            )
        ]
    )
    (root / "web" / "tiles" / "index.json").write_bytes(canonical_json(index))
    manifest = {
        "schema": "sig.export-manifest/1",
        "artifacts": [
            {
                "path": tile_path,
                "license": _LICENCE,
                "compartment": _COMPARTMENT,
                "sha256": rendered.sha256,
                "bytes": len(rendered.data),
            }
        ],
    }
    (root / "manifest.json").write_bytes(canonical_json(manifest))
    return root


def test_verify_passes_a_correct_export(tmp_path: Path) -> None:
    report = verify_export_tiles(_export_dir(tmp_path))
    assert report["schema"] == TILES_VERIFY_SCHEMA
    assert report["verdict"] == "pass", json.dumps(report["archives"], indent=2)[:2000]
    assert report["checks"] == {
        "conservation": "pass",
        "parity": "pass",
        "precision_tier": "pass",
        "size": "pass",
        "metadata": "pass",
    }
    archive = report["archives"][0]
    # measured numbers, not asserted constants: Σn per z≤9 band == 4 located
    detail = archive["checks"]["conservation"]["detail"]
    assert detail["z0"]["sum_n"] == 4 == detail["z0"]["expected"]
    assert detail["z10"]["rk"] == 2  # only tier-0 pair at z10
    assert detail["z12"]["rk"] == 4
    # shipped renderer is pure-python locally → parity is honestly vacuous
    assert archive["checks"]["parity"]["detail"]["vacuous"] is True


def test_verify_fails_when_index_is_missing(tmp_path: Path) -> None:
    report = verify_export_tiles(tmp_path)
    assert report["verdict"] == "fail"
    assert "index.json" in report["error"]


def test_verify_fails_when_a_site_is_dropped(tmp_path: Path) -> None:
    """A tampered archive (one feature removed) breaks conservation loudly."""
    root = _export_dir(tmp_path)
    # rebuild the archive WITHOUT one feature — conservation must flag it
    trimmed = json.loads(_GEOJSON)
    trimmed["features"] = trimmed["features"][:-1]
    rendered = render_compartment_sites_pmtiles(
        _COMPARTMENT, json.dumps(trimmed).encode(), _LICENCE
    )
    index = json.loads((root / "web/tiles/index.json").read_bytes())
    entry = index["archives"][0]
    tile_path = entry["path"]
    # overwrite the archive bytes but keep the index entry (path + sha now stale:
    # integrity fails first — drop the file under a NEW hash-named path instead
    # so conservation itself is what trips).
    new_path = f"web/tiles/{_COMPARTMENT}-sites.{rendered.sha256[:8]}.pmtiles"
    (root / tile_path).unlink()
    (root / new_path).write_bytes(rendered.data)
    entry["path"] = new_path
    entry["sha256"] = rendered.sha256
    (root / "web/tiles/index.json").write_bytes(canonical_json(index))
    report = verify_export_tiles(root)
    assert report["verdict"] == "fail"
    assert report["checks"]["conservation"] == "fail"


def test_verify_fails_on_a_foreign_property(tmp_path: Path) -> None:
    """A tile feature carrying a non-§3.3 tag (e.g. a claim id) fails check 3."""
    root = _export_dir(tmp_path)
    # hand-build an archive whose sites layer carries an extra `claim_id` tag
    from exports.tiles import map_tile_geojson, render_pmtiles

    emit = json.loads(map_tile_geojson(_GEOJSON, _COMPARTMENT))
    for f in emit["features"]:
        if f["tippecanoe"]["layer"] == "sites":
            f["properties"]["claim_ids"] = "claim:secret"
    data = render_pmtiles(emit, layer_name="sites", license_id=_LICENCE, attribution=_ATTRIBUTION)
    index = json.loads((root / "web/tiles/index.json").read_bytes())
    entry = index["archives"][0]
    import hashlib

    new_path = f"web/tiles/{_COMPARTMENT}-sites.{hashlib.sha256(data).hexdigest()[:8]}.pmtiles"
    (root / entry["path"]).unlink()
    (root / new_path).write_bytes(data)
    entry["path"] = new_path
    entry["sha256"] = hashlib.sha256(data).hexdigest()
    (root / "web/tiles/index.json").write_bytes(canonical_json(index))
    report = verify_export_tiles(root)
    assert report["verdict"] == "fail"
    assert report["checks"]["precision_tier"] == "fail"


def test_verify_fails_on_a_metadata_mismatch(tmp_path: Path) -> None:
    root = _export_dir(tmp_path)
    index = json.loads((root / "web/tiles/index.json").read_bytes())
    index["archives"][0]["licence"] = "Apache-2.0"  # lies about the archive licence
    (root / "web/tiles/index.json").write_bytes(canonical_json(index))
    report = verify_export_tiles(root)
    assert report["verdict"] == "fail"
    assert report["checks"]["metadata"] == "fail"


def test_verify_fails_on_an_oversized_tile(tmp_path: Path) -> None:
    """A > 500 KiB stored tile is a verification failure, not a silent thin."""
    root = _export_dir(tmp_path)
    # build an archive carrying one giant tile (random bytes defeat gzip)
    import random

    rng = random.Random(7)
    big = bytes(rng.randrange(256) for _ in range(600 * 1024))
    tiles = {zxy_to_tileid(0, 0, 0): big}
    archive = build_pmtiles(
        tiles,
        metadata={
            "sig:license": _LICENCE,
            "attribution": _ATTRIBUTION,
            "sig:map-tiles-contract": "sig.map-tiles/2",
            "vector_layers": [],
        },
    )
    index = json.loads((root / "web/tiles/index.json").read_bytes())
    entry = index["archives"][0]
    import hashlib

    new_path = f"web/tiles/{_COMPARTMENT}-sites.{hashlib.sha256(archive).hexdigest()[:8]}.pmtiles"
    (root / entry["path"]).unlink()
    (root / new_path).write_bytes(archive)
    entry["path"] = new_path
    entry["sha256"] = hashlib.sha256(archive).hexdigest()
    (root / "web/tiles/index.json").write_bytes(canonical_json(index))
    report = verify_export_tiles(root)
    assert report["verdict"] == "fail"
    assert report["checks"]["size"] == "fail"


def test_decode_mvt_tile_reads_a_layer() -> None:
    """The decoder round-trips what tiles._encode_layer wrote (z0 sanity)."""
    from exports.tiles import encode_mvt_points

    feats = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.5, 35.4]},
            "properties": {"rk": "sig_graph:deployment:x", "tr": 0},
        }
    ]
    tile = encode_mvt_points(feats, layer_name="sites")
    layers = decode_mvt_tile(tile)
    assert layers[0]["name"] == "sites"
    f = layers[0]["features"][0]
    assert f["type"] == 1
    assert f["properties"]["rk"] == "sig_graph:deployment:x"
    assert len(f["points"]) == 1


def test_cli_tiles_verify_writes_the_report(tmp_path: Path) -> None:
    """`sig-exports tiles verify --in <dir>` lands reports/tiles_verify.json."""
    from exports.cli import main

    root = _export_dir(tmp_path)
    rc = main(["tiles", "verify", "--in", str(root)])
    assert rc == 0
    report = json.loads((root / "reports" / "tiles_verify.json").read_bytes())
    assert report["verdict"] == "pass"
    assert report["schema"] == TILES_VERIFY_SCHEMA


def test_cli_tiles_verify_exits_nonzero_on_failure(tmp_path: Path) -> None:
    from exports.cli import main

    rc = main(["tiles", "verify", "--in", str(tmp_path)])
    assert rc == 1
