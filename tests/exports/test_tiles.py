# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vector-tile rendering (LD-F07/H08, §40, ADR-048, ADR-R9-TILES): real z0–z14
per-compartment PMTiles with licence + attribution metadata (P31.15)."""

from __future__ import annotations

import gzip
import json
import struct
import subprocess

from exports import tiles as T

_OKC = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.5164, 35.4676]},
            "properties": {
                "entity_id": "sig:asset:okc-pole-1",
                "jurisdiction": "Oklahoma City",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.52, 35.47]},
            "properties": {"entity_id": "sig:asset:okc-pole-2", "count": 3},
        },
    ],
}


def _parse_pmtiles(data: bytes) -> tuple[dict, dict[int, bytes]]:
    """Minimal PMTiles v3 reader: metadata JSON + ``{tile_id: mvt_bytes}``."""
    assert data[0:7] == b"PMTiles"
    assert data[7] == 3
    meta_off = struct.unpack_from("<Q", data, 24)[0]
    meta_len = struct.unpack_from("<Q", data, 32)[0]
    metadata = json.loads(gzip.decompress(data[meta_off : meta_off + meta_len]))
    tiles = {}
    for tid, offset, length in _read_root(data):
        tile_off = struct.unpack_from("<Q", data, 56)[0]
        blob = data[tile_off + offset : tile_off + offset + length]
        tiles[tid] = gzip.decompress(blob)
    return metadata, tiles


def _read_root(data: bytes) -> list[tuple[int, int, int]]:
    """Decode the root directory into ``(tile_id, offset, length)`` entries."""
    root_off = struct.unpack_from("<Q", data, 8)[0]
    root_len = struct.unpack_from("<Q", data, 16)[0]
    raw = gzip.decompress(data[root_off : root_off + root_len])
    pos = 0

    def varint() -> int:
        nonlocal pos
        shift = 0
        val = 0
        while True:
            b = raw[pos]
            pos += 1
            val |= (b & 0x7F) << shift
            if not (b & 0x80):
                return val
            shift += 7

    n = varint()
    ids = []
    prev = 0
    for _ in range(n):
        prev += varint()
        ids.append(prev)
    runs = [varint() for _ in range(n)]
    lengths = [varint() for _ in range(n)]
    # spec §4.2: stored ``offset + 1``, or ``0`` = contiguous with the previous entry.
    offsets: list[int] = []
    for i in range(n):
        stored = varint()
        if i > 0 and stored == 0:
            offsets.append(offsets[i - 1] + lengths[i - 1])
        else:
            offsets.append(stored - 1)
    assert all(r == 1 for r in runs)  # every entry is a tile, never a leaf pointer
    return list(zip(ids, offsets, lengths, strict=True))


def test_zxy_to_tileid_matches_the_spec_table() -> None:
    # PMTiles v3 spec §4 TileID table (Hilbert curve ids).
    assert T.zxy_to_tileid(0, 0, 0) == 0
    assert T.zxy_to_tileid(1, 0, 0) == 1
    assert T.zxy_to_tileid(1, 0, 1) == 2
    assert T.zxy_to_tileid(1, 1, 1) == 3
    assert T.zxy_to_tileid(1, 1, 0) == 4
    assert T.zxy_to_tileid(2, 0, 0) == 5
    assert T.zxy_to_tileid(12, 3423, 1763) == 19078479
    # the round-trip inverse
    for z, x, y in [(0, 0, 0), (1, 1, 0), (2, 3, 3), (7, 100, 41), (12, 3423, 1763)]:
        assert T.tileid_to_zxy(T.zxy_to_tileid(z, x, y)) == (z, x, y)


def test_render_pmtiles_is_a_valid_v3_archive_with_the_z0_z14_pyramid() -> None:
    data = T.render_pmtiles(_OKC, layer_name="sites")
    metadata, tiles = _parse_pmtiles(data)
    # A real rendered pyramid (not the metadata-only P14.2 archive, not the old
    # single-z0 fallback): addressed tiles cover every zoom 0..14.
    assert struct.unpack_from("<Q", data, 72)[0] == len(tiles)
    assert data[99] == 1  # tile type: MVT
    zooms = {T.tileid_to_zxy(tid)[0] for tid in tiles}
    assert zooms == set(range(T.PMTILES_MINZOOM, T.PMTILES_MAXZOOM + 1))
    assert data[100] == T.PMTILES_MINZOOM and data[101] == T.PMTILES_MAXZOOM
    assert metadata["minzoom"] == T.PMTILES_MINZOOM
    assert metadata["maxzoom"] == T.PMTILES_MAXZOOM
    # directory entries are sorted by tile_id (clustered layout)
    assert [t for t, _, _ in _read_root(data)] == sorted(tiles)


def test_layer_carries_odbl_metadata() -> None:
    # ADR-048 / §42: the ODbL layer's licence + OSM attribution are preserved in tiles.
    data = T.render_pmtiles(_OKC, layer_name="sites", license_id="ODbL-1.0")
    metadata, _ = _parse_pmtiles(data)
    layers = metadata["vector_layers"]
    assert len(layers) >= 1
    assert layers[0]["id"] == "sites"
    assert layers[0]["sig:license"] == "ODbL-1.0"
    assert layers[0]["sig:attribution"] == T.ODBL_ATTRIBUTION
    assert layers[0]["minzoom"] == T.PMTILES_MINZOOM
    assert layers[0]["maxzoom"] == T.PMTILES_MAXZOOM
    assert metadata["sig:license"] == "ODbL-1.0"
    assert "openstreetmap" in metadata["attribution"].lower()


def test_mvt_encodes_point_features_with_same_cell_dedup() -> None:
    # Decode a z14 tile far enough to count features (field 2, repeated): the two
    # OKC points are ~400 m apart → distinct cells at z14 (cell ≈ 2.4 m) → both
    # features present; at z0 they share one sub-pixel cell → deduped to one.
    _, tiles = _parse_pmtiles(T.render_pmtiles(_OKC, layer_name="sites"))
    z14 = [b for t, b in tiles.items() if T.tileid_to_zxy(t)[0] == 14]
    count = sum(tile.count(b"\x18\x01") for tile in z14)  # type=POINT markers
    assert count == 2
    assert tiles[T.zxy_to_tileid(0, 0, 0)].count(b"\x18\x01") == 1
    # a distinct-geometry pair at single-tile extent keeps both features
    far = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-97.5, 35.4]},
                "properties": {},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-80.0, 40.0]},
                "properties": {},
            },
        ],
    }
    mvt = T.encode_mvt_points(list(far["features"]), layer_name="sites")
    assert mvt.count(b"\x18\x01") == 2


def test_bounds_track_the_input_extent() -> None:
    data = T.render_pmtiles(_OKC, layer_name="sites")
    min_lon_e7 = struct.unpack_from("<i", data, 102)[0]
    max_lon_e7 = struct.unpack_from("<i", data, 110)[0]
    assert min_lon_e7 / 1e7 <= -97.5164 <= max_lon_e7 / 1e7


def test_render_is_byte_deterministic() -> None:
    # Determinism for a snapshot is the export contract (and the diff a P31.16
    # published-diff relies on): same features → byte-identical archive.
    a = T.render_pmtiles(_OKC, layer_name="sites")
    b = T.render_pmtiles(json.loads(json.dumps(_OKC)), layer_name="sites")
    assert a == b


def test_empty_collection_still_valid_archive() -> None:
    data = T.render_pmtiles({"type": "FeatureCollection", "features": []}, layer_name="sites")
    metadata, tiles = _parse_pmtiles(data)
    assert tiles == {}
    assert metadata["vector_layers"][0]["sig:license"] == "ODbL-1.0"


def test_render_file_uses_pure_python_when_tippecanoe_absent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(T, "tippecanoe_available", lambda: False)
    src = tmp_path / "in.geojson"
    src.write_text(json.dumps(_OKC))
    out = tmp_path / "out.pmtiles"
    renderer = T.render_pmtiles_file(str(src), str(out), layer_name="sites")
    assert renderer == "pure-python"
    metadata, tiles = _parse_pmtiles(out.read_bytes())
    assert metadata["vector_layers"][0]["sig:license"] == "ODbL-1.0"
    assert {T.tileid_to_zxy(t)[0] for t in tiles} == set(range(15))


def test_render_file_uses_tippecanoe_z0_z14_with_licence_annotation(tmp_path, monkeypatch) -> None:
    # The production path: tippecanoe renders z0–z14, then the archive's JSON
    # metadata is stamped with the compartment licence + attribution (the reader
    # contract the served map relies on).
    monkeypatch.setattr(T, "tippecanoe_available", lambda: True)
    captured: dict[str, list[str]] = {}
    baseline = T.render_pmtiles(_OKC, layer_name="sites")

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured["argv"] = argv
        out_path = argv[argv.index("-o") + 1]
        with open(out_path, "wb") as fh:
            fh.write(baseline)
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(T.subprocess, "run", fake_run)
    src = tmp_path / "in.geojson"
    src.write_text(json.dumps(_OKC))
    out = tmp_path / "out.pmtiles"
    renderer = T.render_pmtiles_file(str(src), str(out), layer_name="sites", license_id="ODbL-1.0")
    assert renderer == "tippecanoe"
    argv = captured["argv"]
    assert argv[argv.index("-Z") + 1] == str(T.PMTILES_MINZOOM)
    assert argv[argv.index("-z") + 1] == str(T.PMTILES_MAXZOOM)
    assert argv[argv.index("-l") + 1] == "sites"
    assert argv[argv.index("--attribution") + 1] == T.ODBL_ATTRIBUTION
    metadata, _ = _parse_pmtiles(out.read_bytes())
    assert metadata["sig:license"] == "ODbL-1.0"
    assert metadata["vector_layers"][0]["sig:license"] == "ODbL-1.0"
    assert "openstreetmap" in metadata["attribution"].lower()
    # the annotation pass preserves the rendered pyramid untouched
    assert {T.tileid_to_zxy(t)[0] for t in _parse_pmtiles(out.read_bytes())[1]} == set(range(15))


def test_annotate_pmtiles_stamps_a_foreign_archive(tmp_path) -> None:
    # annotate_pmtiles rewrites only the JSON metadata section: tile bytes and the
    # directory are preserved, the licence + attribution land on top of whatever
    # the renderer wrote (tippecanoe has no licence field of its own).
    data = T.render_pmtiles(_OKC, layer_name="sites", license_id="ODbL-1.0")
    out = T.annotate_pmtiles(data, license_id="CC-BY-SA-4.0", attribution="Portal — CC-BY-SA-4.0")
    assert out[0:7] == b"PMTiles" and out[7] == 3
    meta1, tiles1 = _parse_pmtiles(data)
    meta2, tiles2 = _parse_pmtiles(out)
    assert tiles1 == tiles2  # tile bytes untouched
    assert meta2["sig:license"] == "CC-BY-SA-4.0"
    assert meta2["attribution"] == "Portal — CC-BY-SA-4.0"
    assert meta2["vector_layers"][0]["sig:license"] == "CC-BY-SA-4.0"
    assert out[100] == 0 and out[101] == 14
