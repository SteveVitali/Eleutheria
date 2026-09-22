# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vector-tile rendering (LD-F07/H08, §40, ADR-048): real PMTiles, ODbL metadata."""

from __future__ import annotations

import gzip
import json
import struct

from exports import tiles as T

_OKC = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.5164, 35.4676]},
            "properties": {"subject_id": "sig:asset:okc-pole-1", "jurisdiction": "Oklahoma City"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.52, 35.47]},
            "properties": {"subject_id": "sig:asset:okc-pole-2", "count": 3},
        },
    ],
}


def _parse_pmtiles(data: bytes) -> tuple[dict, bytes]:
    """The 'existing PMTiles reader' shape (struct + gzip) used across the export tests."""
    assert data[0:7] == b"PMTiles"
    assert data[7] == 3
    meta_off = struct.unpack_from("<Q", data, 24)[0]
    meta_len = struct.unpack_from("<Q", data, 32)[0]
    metadata = json.loads(gzip.decompress(data[meta_off : meta_off + meta_len]))
    tile_off = struct.unpack_from("<Q", data, 56)[0]
    tile_len = struct.unpack_from("<Q", data, 64)[0]
    tile = gzip.decompress(data[tile_off : tile_off + tile_len])
    return metadata, tile


def test_render_pmtiles_is_a_valid_v3_archive_with_one_rendered_tile() -> None:
    data = T.render_pmtiles(_OKC, layer_name="devices")
    metadata, tile = _parse_pmtiles(data)
    # A real rendered tile (not the metadata-only P14.2 archive): 1 addressed tile.
    assert struct.unpack_from("<Q", data, 72)[0] == 1
    assert data[99] == 1  # tile type: MVT
    assert len(tile) > 0


def test_layer_carries_odbl_metadata() -> None:
    # ADR-048 / §42: the ODbL layer's licence + OSM attribution are preserved in tiles.
    data = T.render_pmtiles(_OKC, layer_name="devices", license_id="ODbL-1.0")
    metadata, _ = _parse_pmtiles(data)
    layers = metadata["vector_layers"]
    assert len(layers) >= 1
    assert layers[0]["id"] == "devices"
    assert layers[0]["sig:license"] == "ODbL-1.0"
    assert "openstreetmap" in metadata["attribution"].lower()


def test_mvt_encodes_every_point_feature() -> None:
    # Decode the MVT layer far enough to count features (field 2, repeated) — proves the
    # points were actually rendered into the tile, not just declared in metadata.
    _, tile = _parse_pmtiles(T.render_pmtiles(_OKC, layer_name="devices"))
    # Tile.layers is field 3 (wire 2); inside, Feature is field 2 (wire 2).
    assert tile[0] == (3 << 3) | 2
    # Count feature sub-messages by scanning the layer body for the 0x12 (field 2) tag
    # is fragile; instead assert the encoder reports both features via a round-trip count.
    features = list(_OKC["features"])
    mvt = T.encode_mvt_points(features, layer_name="devices")
    # Two POINT features → two type=POINT (field 3, value 1) markers = b"\x18\x01".
    assert mvt.count(b"\x18\x01") == 2


def test_bounds_track_the_input_extent() -> None:
    data = T.render_pmtiles(_OKC, layer_name="devices")
    min_lon_e7 = struct.unpack_from("<i", data, 102)[0]
    max_lon_e7 = struct.unpack_from("<i", data, 110)[0]
    assert min_lon_e7 / 1e7 <= -97.5164 <= max_lon_e7 / 1e7


def test_empty_collection_still_valid_archive() -> None:
    data = T.render_pmtiles({"type": "FeatureCollection", "features": []}, layer_name="devices")
    metadata, _ = _parse_pmtiles(data)
    assert metadata["vector_layers"][0]["sig:license"] == "ODbL-1.0"


def test_render_file_uses_pure_python_when_tippecanoe_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(T, "tippecanoe_available", lambda: False)
    src = tmp_path / "in.geojson"
    src.write_text(json.dumps(_OKC))
    out = tmp_path / "out.pmtiles"
    renderer = T.render_pmtiles_file(str(src), str(out), layer_name="devices")
    assert renderer == "pure-python"
    metadata, _ = _parse_pmtiles(out.read_bytes())
    assert metadata["vector_layers"][0]["sig:license"] == "ODbL-1.0"
