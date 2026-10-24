# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vector-tile rendering (LD-F07/H08, §40, ADR-048, ADR-R9-TILES): real z0–z14
per-compartment PMTiles with licence + attribution metadata (P31.15)."""

from __future__ import annotations

import gzip
import json
import random
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
    for tid, _run, offset, length in _all_tile_entries(data):
        tile_off = struct.unpack_from("<Q", data, 56)[0]
        blob = data[tile_off + offset : tile_off + offset + length]
        tiles[tid] = gzip.decompress(blob)
    return metadata, tiles


def _read_directory(raw: bytes) -> list[tuple[int, int, int, int]]:
    """Decode one directory section into ``(tile_id, run_length, offset, length)``."""
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
    return list(zip(ids, runs, offsets, lengths, strict=True))


def _read_root(data: bytes) -> list[tuple[int, int, int, int]]:
    """Decode the ROOT directory (entries may be leaf pointers, run_length 0)."""
    root_off = struct.unpack_from("<Q", data, 8)[0]
    root_len = struct.unpack_from("<Q", data, 16)[0]
    return _read_directory(gzip.decompress(data[root_off : root_off + root_len]))


def _all_tile_entries(data: bytes) -> list[tuple[int, int, int, int]]:
    """Every ``run_length > 0`` entry, descending through root leaf pointers."""
    leaf_off = struct.unpack_from("<Q", data, 40)[0]
    out: list[tuple[int, int, int, int]] = []
    for tid, run, off, ln in _read_root(data):
        if run == 0:
            out.extend(_read_directory(gzip.decompress(data[leaf_off + off : leaf_off + off + ln])))
        else:
            out.append((tid, run, off, ln))
    return out


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
    # directory entries are sorted by tile_id (clustered layout; a small
    # pyramid keeps the classic flat root — no leaf pointers)
    assert [t for t, *_ in _read_root(data)] == sorted(tiles)


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


def test_mvt_encodes_point_features_with_byte_identical_only_dedup() -> None:
    # P35.52 (sig.map-tiles/2): only BYTE-IDENTICAL features deduplicate. The two
    # OKC points are ~400 m apart — distinct entities — so BOTH survive at z14
    # AND at z0 (the old _DEDUP_CELL coalescing of distinct same-cell points was
    # the second half of the F-414 loss).
    _, tiles = _parse_pmtiles(T.render_pmtiles(_OKC, layer_name="sites"))
    z14 = [b for t, b in tiles.items() if T.tileid_to_zxy(t)[0] == 14]
    count = sum(tile.count(b"\x18\x01") for tile in z14)  # type=POINT markers
    assert count == 2
    assert tiles[T.zxy_to_tileid(0, 0, 0)].count(b"\x18\x01") == 2
    # a byte-identical pair still collapses to one feature
    dup = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-97.5, 35.4]},
                "properties": {"a": 1},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-97.5, 35.4]},
                "properties": {"a": 1},
            },
        ],
    }
    _, tiles2 = _parse_pmtiles(T.render_pmtiles(dup, layer_name="sites"))
    assert tiles2[T.zxy_to_tileid(0, 0, 0)].count(b"\x18\x01") == 1
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


def test_leaf_directories_when_the_root_exceeds_the_optimistic_read() -> None:
    # The reference JS reader parses the root directory from its first 16 KiB
    # fetch — a national-scale index (the ~100 k-entry national fixture) must
    # spill into leaf directories or every tile reads as a truncated stream.
    # Variable-length tiles give the index the entropy that defeats gzip.
    rng = random.Random(2)
    ids = sorted(set(T.zxy_to_tileid(14, i % 16384, i // 16384) for i in range(100_000)))
    # varied tile CONTENT — same-length zero blobs gzip into a near-constant
    # entry pattern that never reaches the spill threshold in a test.
    tiles = {tid: bytes(i % 256 for i in range(rng.randrange(200, 2000))) for tid in ids}
    data = T.build_pmtiles(tiles, metadata={"vector_layers": []})

    root_len = struct.unpack_from("<Q", data, 16)[0]
    leaf_len = struct.unpack_from("<Q", data, 48)[0]
    assert root_len <= T._ROOT_DIR_MAX_BYTES
    assert leaf_len > 0
    root = _read_root(data)
    assert all(run == 0 for _tid, run, _off, _ln in root)
    # the spec §3 addressed count covers tile entries AND the leaf pointers
    assert struct.unpack_from("<Q", data, 72)[0] == len(tiles) + len(root)
    # every tile resolves through exactly one leaf, bytes intact
    flat = _all_tile_entries(data)
    assert sorted(t for t, *_ in flat) == sorted(tiles)
    tile_off = struct.unpack_from("<Q", data, 56)[0]
    for tid, _run, off, ln in flat:
        assert gzip.decompress(data[tile_off + off : tile_off + off + ln]) == tiles[tid]


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
    # P35.52: the retention contract — nothing dropped, tool-side limits off.
    assert "-r1" in argv
    assert "--no-tile-size-limit" in argv
    assert "--no-feature-limit" in argv
    T.assert_retention_argv(argv)  # the guard accepts the pinned invocation
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


# --- sig.map-tiles/2 (P35.52, ADR-156, K1-map §3/§9.2) -------------------------

_V2_FEATURES = {
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
            # co-located with a1 — a DISTINCT entity that must never coalesce
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
        {
            "type": "Feature",
            # tier 3 located? never tiled — a defensive fixture; the emit drops it
            # from sites while cells still count the published located record.
            "geometry": {"type": "Point", "coordinates": [-90.0, 40.0]},
            "properties": {
                "entity_id": "d1",
                "entity_type": "deployment",
                "sensitivity_tier": 3,
                "jurisdiction": "unresolved",
                "source_ids": [],
            },
        },
    ],
}
_V2_GEOJSON = json.dumps(_V2_FEATURES).encode()


def _mvt_layers(tile_bytes: bytes) -> dict[str, list[dict]]:
    """tile bytes → {layer_name: [features]} via the verifier's decoder."""
    from exports.tile_verify import decode_mvt_tile

    return {layer["name"]: layer["features"] for layer in decode_mvt_tile(tile_bytes)}


def test_retention_guard_rejects_drop_and_coalesce_flags() -> None:
    import pytest

    argv = T._tippecanoe_argv("in.geojson", "out.pmtiles", layer_name="sites", attribution="x")
    T.assert_retention_argv(argv)  # the pinned invocation passes
    for bad in (
        "--drop-densest-as-needed",
        "--drop-fraction-as-needed",
        "--drop-smallest-as-needed",
        "--coalesce-densest-as-needed",
        "--coalesce",
        "--cluster-distance=10",
        "--maximum-tile-bytes=1000000",
        "--base-zoom=10",
    ):
        with pytest.raises(ValueError, match="retention"):
            T.assert_retention_argv([*argv, bad])
    # a rate other than 1, and a missing -r1, both refuse
    with pytest.raises(ValueError):
        T.assert_retention_argv([t if t != "-r1" else "-r2.5" for t in argv])
    with pytest.raises(ValueError):
        T.assert_retention_argv([t for t in argv if t != "-r1"])
    with pytest.raises(ValueError):
        T.assert_retention_argv([t for t in argv if t != "--no-tile-size-limit"])


def test_emit_assigns_layers_and_zoom_bands() -> None:
    doc = json.loads(T.map_tile_geojson(_V2_GEOJSON, "sig_graph"))
    cells = [f for f in doc["features"] if f["tippecanoe"]["layer"] == "cells"]
    sites = [f for f in doc["features"] if f["tippecanoe"]["layer"] == "sites"]
    # every feature declares its contract range — sites span to the archive
    # max, cells cap at their band end (a res-3 cell must not render at z5+).
    for f in doc["features"]:
        member = f["tippecanoe"]
        assert isinstance(member["minzoom"], int)
        assert isinstance(member["maxzoom"], int)
    assert {f["tippecanoe"]["maxzoom"] for f in sites} == {T.PMTILES_MAXZOOM}
    # cells: one per (band, h3) — z bands per CELL_BANDS; props h3/n/ns/jp
    assert {f["tippecanoe"]["minzoom"] for f in cells} == {b[0] for b in T.CELL_BANDS}
    assert {f["tippecanoe"]["maxzoom"] for f in cells} == {b[1] for b in T.CELL_BANDS}
    for f in cells:
        assert set(f["properties"]) == {"h3", "n", "ns", "jp"}
    # sites: tier zoom band per SITE_MINZOOM_BY_TIER; tier 3 absent; props rk+tr
    by_rk = {f["properties"]["rk"]: f for f in sites}
    assert "sig_graph:deployment:d1" not in by_rk
    assert by_rk["sig_graph:deployment:a1"]["tippecanoe"]["minzoom"] == 10
    assert by_rk["sig_graph:deployment:b1"]["tippecanoe"]["minzoom"] == 11
    assert by_rk["sig_graph:deployment:c1"]["tippecanoe"]["minzoom"] == 12
    assert by_rk["sig_graph:deployment:c1"]["properties"]["tr"] == 2
    # tier-2 emits the H3 display polygon
    assert by_rk["sig_graph:deployment:c1"]["geometry"]["type"] == "Polygon"
    assert {f["properties"]["tr"] for f in sites} == {0, 1, 2}


def test_pure_python_pyramid_honours_the_emitted_ranges() -> None:
    # the two co-located tier-0 records land in ONE res-3 z0–4 cell but stay
    # two distinct site features everywhere (byte-identical-only dedupe).
    doc = json.loads(T.map_tile_geojson(_V2_GEOJSON, "sig_graph"))
    data = T.render_pmtiles(doc, layer_name="sites", license_id="CC-BY-4.0")
    metadata, tiles = _parse_pmtiles(data)
    assert {v["id"] for v in metadata["vector_layers"]} == {"cells", "sites"}
    cell_layer = next(v for v in metadata["vector_layers"] if v["id"] == "cells")
    site_layer = next(v for v in metadata["vector_layers"] if v["id"] == "sites")
    assert (cell_layer["minzoom"], cell_layer["maxzoom"]) == (0, 9)
    assert (site_layer["minzoom"], site_layer["maxzoom"]) == (10, 14)
    assert metadata["sig:map-tiles-contract"] == "sig.map-tiles/2"

    seen_site_rks: dict[int, set[str]] = {}
    seen_cells: dict[int, int] = {}
    site_types: dict[str, int] = {}
    for tid, blob in tiles.items():
        z, _x, _y = T.tileid_to_zxy(tid)
        for lname, feats in _mvt_layers(blob).items():
            for feat in feats:
                p = feat["properties"]
                if lname == "sites":
                    seen_site_rks.setdefault(z, set()).add(p["rk"])
                    site_types[p["rk"]] = feat["type"]
                else:
                    seen_cells.setdefault(z, 0)
                    seen_cells[z] = seen_cells[z]  # h3 dedupe handled below
    # count cells per zoom by distinct h3 (buffer duplicates impossible for
    # the pure-python renderer — one feature lives in exactly one tile)
    cells_by_zoom: dict[int, dict[str, int]] = {}
    for tid, blob in tiles.items():
        z, _x, _y = T.tileid_to_zxy(tid)
        for feat in _mvt_layers(blob).get("cells", []):
            cells_by_zoom.setdefault(z, {}).setdefault(
                feat["properties"]["h3"], feat["properties"]["n"]
            )
    # located records = 5 (incl. tier-3); Σn over cells == 5 at every z0–9
    for z in range(10):
        assert sum(cells_by_zoom.get(z, {}).values()) == 5, z
    # tier-0 pair present from z10, tier-1 joins at z11, tier-2 at z12
    assert seen_site_rks[10] == {"sig_graph:deployment:a1", "sig_graph:deployment:a2"}
    assert seen_site_rks[11] == seen_site_rks[10] | {"sig_graph:deployment:b1"}
    assert len(seen_site_rks[12]) == 4
    # nothing above/below its band
    assert all(z >= 10 for z in seen_site_rks)
    # tier-2 site is an MVT polygon; tiers 0–1 are points
    assert site_types["sig_graph:deployment:c1"] == 3
    assert site_types["sig_graph:deployment:a1"] == 1
    # and the tier-3 record never appears as a site
    assert "sig_graph:deployment:d1" not in site_types


def test_oversized_tile_fails_the_render_loudly() -> None:
    import pytest

    # incompressible padding — the size contract measures STORED (gzipped)
    # bytes, so a constant pad compresses away and never trips the limit; a
    # pad REPEATED across features compresses too (gzip collapses the repeat),
    # so each feature carries its own random pad.
    rng = random.Random(7)
    alpha = "abcdefghijklmnopqrstuvwxyz0123456789"
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-97.0 + i * 0.001, 35.0]},
            "properties": {
                "pad": "".join(rng.choice(alpha) for _ in range(T.TILE_SIZE_LIMIT_BYTES // 2))
            },
        }
        for i in range(3)
    ]
    with pytest.raises(T.TileSizeLimitExceeded):
        T.render_pmtiles({"type": "FeatureCollection", "features": features}, layer_name="sites")


def test_tiles_index_entry_fields() -> None:
    from exports.tiles import render_compartment_sites_pmtiles, tiles_index_entry

    rendered = render_compartment_sites_pmtiles("sig_graph", _V2_GEOJSON, "CC-BY-4.0")
    entry = tiles_index_entry(
        compartment="sig_graph",
        path=f"web/tiles/sig_graph-sites.{rendered.sha256[:8]}.pmtiles",
        license_id="CC-BY-4.0",
        attribution="© The SIG project — CC-BY-4.0",
        rendered=rendered,
        source="sig_graph/sites.geojson",
    )
    assert entry["contract"] == "sig.map-tiles/2"
    assert entry["sha256"] == rendered.sha256
    assert entry["licence"] == "CC-BY-4.0"
    assert entry["counts"]["points"] == 5
    assert set(entry["counts"]["cells_by_band"]) == {"0-4", "5-6", "7-8", "9-9"}
    assert entry["renderer"] in ("pure-python", "tippecanoe")
    assert entry["minzoom"] == 0 and entry["maxzoom"] == 14
    assert len(entry["bounds"]) == 4
