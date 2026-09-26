# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vector-tile rendering for the public map (LD-F07 / LD-H08, §40, ADR-048/ADR-051,
ADR-R9-TILES).

P14.2 emitted a *metadata-only* PMTiles archive (:func:`exports.formats.write_pmtiles`)
and deferred rendering real vector tiles to the map surface; P15.3 left tile
generation out of scope — so nobody owned it (the orphaned LD-F07/LD-H08 handoff).
This module **closed that handoff** and P31.15 completes it: the map island layers
real **z0–z14** per-compartment PMTiles archives (Q9 retires the combined
``/map/points.json``; Q8 is no basemap — D-P30.3-2).

Two paths, one contract:

* **tippecanoe** — used when it is on ``PATH`` (the production path for large
  extents; built from a pinned source tarball in the export image, ops/Dockerfile).
* **pure-Python fallback** — a self-contained Web-Mercator → MVT encoder + PMTiles
  v3 writer rendering the same z0–z14 pyramid, used when tippecanoe is absent (CI +
  the export fixtures). Intended for small extents — it keeps every point at every
  zoom (clipping/densification aside), so a national-sized layer belongs on
  tippecanoe — but it needs no native toolchain (the zero-cost posture).

Either way the output is a deterministic, spec-conformant PMTiles v3 archive whose
metadata preserves the layer's **licence + attribution** (ADR-048, §42): the
OSM-derived physical layer stays a separate ODbL compartment with attribution +
share-alike wherever it is served, tiles included.
"""

from __future__ import annotations

import gzip
import json
import math
import shutil
import struct
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

#: MVT tile extent (the coordinate grid inside a tile); 4096 is the de-facto default.
TILE_EXTENT = 4096
#: The ODbL attribution the OSM-derived layer must carry in every context (§42, SIG-GEO-013).
ODBL_ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
#: The public map zoom range (P31.15 / ADR-R9-TILES): the whole pyramid z0..z14.
PMTILES_MINZOOM = 0
PMTILES_MAXZOOM = 14
#: Same-cell point dedup granularity inside a tile (sub-cells of ``TILE_EXTENT``):
#: two points whose quantized pixels land in one ``_DEDUP_CELL``-unit cell are
#: coalesced. 4 units ≈ 0.25 px — the cell shrinks below a display pixel quickly
#: (≈ 39 km at z0, ≈ 2.4 m at z14), so identical/near-identical geometry merges
#: (matching tippecanoe's default dedup posture) while real sites stay distinct
#: wherever the layer is meaningful; it is also the fallback's zoom-dependent
#: thinning (ADR-117's revisit note).
_DEDUP_CELL = 4
#: Web-mercator latitude bound.
_MAX_LAT = 85.05112878


# --- protobuf primitives (minimal, MVT-only) ---------------------------------


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _key(field: int, wire: int) -> bytes:
    return _varint((field << 3) | wire)


def _tag_varint(field: int, value: int) -> bytes:
    return _key(field, 0) + _varint(value)


def _tag_bytes(field: int, value: bytes) -> bytes:
    return _key(field, 2) + _varint(len(value)) + value


def _tag_string(field: int, value: str) -> bytes:
    return _tag_bytes(field, value.encode("utf-8"))


def _zigzag(n: int) -> int:
    return (n << 1) ^ (n >> 31)


# --- PMTiles Hilbert tile ids (spec §"Directory Compression", zxy_to_tileid) ---


def zxy_to_tileid(z: int, x: int, y: int) -> int:
    """The PMTiles v3 Hilbert tile id for a z/x/y tile (spec reference algorithm).

    ``tile_id(z, x, y) = (4**z - 1) / 3 + hilbert_index`` where the Hilbert index is
    computed over the ``2**z`` grid with the usual rotation (``xy2d``). Verified
    against the spec's table: z1 (0,0)=1, (0,1)=2, (1,1)=3, (1,0)=4; z2 (3,3)=15,
    (3,0)=20; z3 (0,0)=21 … (28,3)=16,746.
    """
    if z > 26 or x < 0 or y < 0 or x > (1 << z) - 1 or y > (1 << z) - 1:
        raise ValueError(f"tile {z}/{x}/{y} outside the PMTiles v3 grid")
    acc = ((1 << (2 * z)) - 1) // 3  # sum_{i=0}^{z-1} 4^i — the id of z/0/0
    n = 1 << z
    d = 0
    s = n // 2
    while s > 0:
        rx = 1 if (x & s) else 0
        ry = 1 if (y & s) else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x = n - 1 - x
                y = n - 1 - y
            x, y = y, x
        s //= 2
    return acc + d


def tileid_to_zxy(tile_id: int) -> tuple[int, int, int]:
    """Invert :func:`zxy_to_tileid` (``d2xy`` Hilbert inversion)."""
    if tile_id < 0:
        raise ValueError("tile_id must be non-negative")
    z = 0
    acc = 0
    while acc + (1 << (2 * z)) <= tile_id:
        acc += 1 << (2 * z)
        z += 1
    d = tile_id - acc
    n = 1 << z
    x = y = 0
    t = d
    s = 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return (z, x, y)


# --- Web-Mercator projection ---------------------------------------------------


def _project_xy(lon: float, lat: float) -> tuple[float, float]:
    """Project (lon, lat) into world coordinates in [0, 1] (web mercator)."""
    x = (lon + 180.0) / 360.0
    lat_rad = math.radians(max(min(lat, _MAX_LAT), -_MAX_LAT))
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0
    return x, y


def _tile_and_local(wx: float, wy: float, z: int, extent: int) -> tuple[int, int, int, int]:
    """World coords → (tile_x, tile_y, local_x, local_y) at zoom ``z``."""
    n = 1 << z
    gx, gy = wx * n, wy * n
    tx = min(n - 1, max(0, int(gx)))
    ty = min(n - 1, max(0, int(gy)))
    lx = round((gx - tx) * extent)
    ly = round((gy - ty) * extent)
    return tx, ty, lx, ly


# --- MVT encoding --------------------------------------------------------------


def _intern(props: Mapping[str, object]) -> list[tuple[str, object]]:
    """Normalized (json-safe) property pairs in deterministic (sorted-key) order."""
    pairs: list[tuple[str, object]] = []
    for k, v in sorted(props.items()):
        if not isinstance(v, (str, int, float, bool)):
            v = json.dumps(v, sort_keys=True, separators=(",", ":"))
        pairs.append((str(k), v))
    return pairs


def _encode_layer(
    points: Sequence[tuple[int, int, int]],
    features: Sequence[Mapping[str, object]],
    *,
    layer_name: str,
    extent: int = TILE_EXTENT,
) -> bytes:
    """Encode ``(local_x, local_y, feature_index)`` points as an MVT layer.

    Deterministic: identical points + features produce identical bytes. The feature
    id carries ``feature_index`` so a reader can link a tile feature back to the
    rendered collection; only json-safe properties are tagged (sorted by key).
    """
    keys: list[str] = []
    values: list[object] = []
    key_index: dict[str, int] = {}
    value_index: dict[tuple[str, object], int] = {}

    def intern_key(k: str) -> int:
        if k not in key_index:
            key_index[k] = len(keys)
            keys.append(k)
        return key_index[k]

    def intern_value(v: object) -> int:
        vk = (type(v).__name__, v)
        if vk not in value_index:
            value_index[vk] = len(values)
            values.append(v)
        return value_index[vk]

    feature_msgs: list[bytes] = []
    for lx, ly, fidx in points:
        feat = features[fidx]
        props = feat.get("properties") or {}
        tags: list[int] = []
        if isinstance(props, Mapping):
            for k, v in _intern(props):
                tags.append(intern_key(k))
                tags.append(intern_value(v))

        # geometry: one MoveTo (command id 1, count 1) then the zigzag dx,dy — the
        # cursor is per-feature and starts at (0, 0).
        geometry = [(1 & 0x7) | (1 << 3), _zigzag(lx), _zigzag(ly)]
        geom_bytes = b"".join(_varint(g) for g in geometry)

        msg = bytearray()
        msg += _tag_varint(1, fidx)  # id
        if tags:
            packed = b"".join(_varint(t) for t in tags)
            msg += _tag_bytes(2, packed)  # tags (packed)
        msg += _tag_varint(3, 1)  # type = POINT
        msg += _tag_bytes(4, geom_bytes)  # geometry (packed)
        feature_msgs.append(bytes(msg))

    layer = bytearray()
    layer += _tag_varint(15, 2)  # version = 2
    layer += _tag_string(1, layer_name)  # name
    for fm in feature_msgs:
        layer += _tag_bytes(2, fm)  # features
    for k in keys:
        layer += _tag_string(3, k)  # keys
    for v in values:
        layer += _tag_bytes(4, _encode_value(v))  # values
    layer += _tag_varint(5, extent)  # extent

    tile = _tag_bytes(3, bytes(layer))  # Tile.layers
    return tile


def encode_mvt_points(
    features: Sequence[Mapping[str, object]],
    *,
    layer_name: str,
    extent: int = TILE_EXTENT,
) -> bytes:
    """Encode GeoJSON point ``features`` into a *single tile's* MVT layer (z0).

    Kept as the single-tile convenience used by the tests; the archive builder
    (:func:`_render_pyramid`) encodes the real per-z/x/y tiles. Only point geometries
    are encoded (the SIG site layer is points).
    """
    points: list[tuple[int, int, int]] = []
    for i, feat in enumerate(features):
        geom = feat.get("geometry") or {}
        if not isinstance(geom, Mapping) or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue
        wx, wy = _project_xy(float(coords[0]), float(coords[1]))
        _tx, _ty, lx, ly = _tile_and_local(wx, wy, 0, extent)
        points.append((lx, ly, i))
    return _encode_layer(points, features, layer_name=layer_name, extent=extent)


def _encode_value(v: object) -> bytes:
    if isinstance(v, bool):
        return _tag_varint(7, 1 if v else 0)  # bool_value
    if isinstance(v, int):
        return _tag_varint(4, v)  # int_value
    if isinstance(v, float):
        return _key(3, 1) + struct.pack("<d", v)  # double_value (wire type 1)
    return _tag_string(1, str(v))  # string_value


# --- the z0..z14 pyramid -------------------------------------------------------


def _render_pyramid(
    features: Sequence[Mapping[str, object]],
    *,
    layer_name: str,
    extent: int = TILE_EXTENT,
    minzoom: int = PMTILES_MINZOOM,
    maxzoom: int = PMTILES_MAXZOOM,
) -> dict[int, bytes]:
    """Render ``features`` into ``{tile_id: mvt_bytes}`` across the zoom pyramid.

    Every point is projected once into world coords; per zoom it lands in one z/x/y
    tile at quantized ``extent`` pixel precision, same-cell duplicates coalesced.
    Tiles are keyed by the PMTiles Hilbert tile id; the returned dict is ordered by
    tile_id (the archive's clustered layout).
    """
    world: list[tuple[int, float, float]] = []  # (feature idx, wx, wy)
    for i, feat in enumerate(features):
        geom = feat.get("geometry") or {}
        if not isinstance(geom, Mapping) or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue
        wx, wy = _project_xy(float(coords[0]), float(coords[1]))
        world.append((i, wx, wy))

    tiles: dict[int, bytes] = {}
    for z in range(minzoom, maxzoom + 1):
        per_tile: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
        seen_cells: dict[tuple[int, int], set[tuple[int, int]]] = {}
        for i, wx, wy in world:
            tx, ty, lx, ly = _tile_and_local(wx, wy, z, extent)
            key = (tx, ty)
            cell = (
                (int(wx * (1 << z) * extent)) // _DEDUP_CELL,
                (int(wy * (1 << z) * extent)) // _DEDUP_CELL,
            )
            cells = seen_cells.setdefault(key, set())
            if cell in cells:
                continue
            cells.add(cell)
            per_tile.setdefault(key, []).append((lx, ly, i))
        for (tx, ty), points in per_tile.items():
            tiles[zxy_to_tileid(z, tx, ty)] = _encode_layer(
                points, features, layer_name=layer_name, extent=extent
            )
    return dict(sorted(tiles.items()))


# --- PMTiles v3 archive --------------------------------------------------------


def _gzip0(data: bytes) -> bytes:
    return gzip.compress(data, mtime=0)


def build_pmtiles(
    tiles: Mapping[int, bytes],
    *,
    metadata: Mapping[str, object],
    bounds: tuple[float, float, float, float] | None = None,
    center: tuple[float, float] | None = None,
    minzoom: int = PMTILES_MINZOOM,
    maxzoom: int = PMTILES_MAXZOOM,
    center_zoom: int = 4,
) -> bytes:
    """Assemble a PMTiles v3 archive from ``{tile_id: mvt_bytes}``.

    ``tiles`` is sorted by Hilbert tile id (the clustered layout); the root
    directory is one flat entry list (delta-encoded ids, run_length 1, offsets all
    0 = contiguous). ``metadata`` is written as the archive's JSON metadata
    (gzip'd); it MUST carry the ``vector_layers`` descriptor so a reader knows the
    layer + its licence. No leaf directories — the flat pyramid is small enough.
    """
    tile_ids = sorted(tiles)
    compressed = {tid: _gzip0(tiles[tid]) for tid in tile_ids}

    # Directory: n_entries, then delta tile_ids, run_lengths, lengths, offsets.
    # Offsets encode as ``offset + 1``, or ``0`` when the entry is contiguous with
    # the previous one (spec §4.2) — our layout is clustered/contiguous so every
    # entry after the first encodes 0.
    directory = bytearray()
    directory += _varint(len(tile_ids))
    prev_id = 0
    for i, tid in enumerate(tile_ids):
        directory += _varint(tid - prev_id if i else tid)
        prev_id = tid
    for _tid in tile_ids:
        directory += _varint(1)  # run_length
    for tid in tile_ids:
        directory += _varint(len(compressed[tid]))
    offset = 0
    prev_end = 0
    for i, tid in enumerate(tile_ids):
        if i > 0 and offset == prev_end:
            directory += _varint(0)  # contiguous with the previous entry
        else:
            directory += _varint(offset + 1)
        prev_end = offset + len(compressed[tid])
        offset += len(compressed[tid])
    root_dir = _gzip0(bytes(directory))
    meta = _gzip0(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    leaf_dir = b""
    tile_data = b"".join(compressed[tid] for tid in tile_ids)

    header_len = 127
    root_off = header_len
    meta_off = root_off + len(root_dir)
    leaf_off = meta_off + len(meta)
    tile_off = leaf_off + len(leaf_dir)

    def e7(v: float) -> int:
        return int(round(v * 1e7))

    minx, miny, maxx, maxy = bounds or (-180.0, -85.0, 180.0, 85.0)
    cx, cy = center or ((minx + maxx) / 2, (miny + maxy) / 2)

    header = bytearray(header_len)
    header[0:7] = b"PMTiles"
    header[7] = 3
    struct.pack_into("<Q", header, 8, root_off)
    struct.pack_into("<Q", header, 16, len(root_dir))
    struct.pack_into("<Q", header, 24, meta_off)
    struct.pack_into("<Q", header, 32, len(meta))
    struct.pack_into("<Q", header, 40, leaf_off)
    struct.pack_into("<Q", header, 48, len(leaf_dir))
    struct.pack_into("<Q", header, 56, tile_off)
    struct.pack_into("<Q", header, 64, len(tile_data))
    struct.pack_into("<Q", header, 72, len(tile_ids))  # num addressed tiles
    struct.pack_into("<Q", header, 80, len(tile_ids))  # num tile entries
    struct.pack_into("<Q", header, 88, len(tile_ids))  # num tile contents
    header[96] = 1  # clustered
    header[97] = 2  # internal compression: gzip
    header[98] = 2  # tile compression: gzip
    header[99] = 1  # tile type: mvt
    header[100] = minzoom  # min zoom
    header[101] = maxzoom  # max zoom
    struct.pack_into("<i", header, 102, e7(minx))
    struct.pack_into("<i", header, 106, e7(miny))
    struct.pack_into("<i", header, 110, e7(maxx))
    struct.pack_into("<i", header, 114, e7(maxy))
    header[118] = center_zoom  # center zoom
    struct.pack_into("<i", header, 119, e7(cx))
    struct.pack_into("<i", header, 123, e7(cy))
    return bytes(header) + root_dir + meta + leaf_dir + tile_data


def annotate_pmtiles(
    data: bytes, *, license_id: str, attribution: str, name: str | None = None
) -> bytes:
    """Stamp ``sig:license`` + attribution into a PMTiles v3 archive's metadata.

    The tippecanoe path produces the archive itself; its JSON metadata records the
    ``--attribution`` string but has no licence field. This pass adds the compartment
    licence (``sig:license``) and per-``vector_layers`` attribution without touching
    the tile bytes — so a tippecanoe-rendered archive carries the same licence
    contract as the pure-Python one (the served map reads ``sig:license`` per source).

    It is also the **determinism normalisation**: tippecanoe embeds the input/output
    file paths in ``name``/``description``/``generator_options`` — the export renders
    through a random temp dir, so the raw archive differs run-to-run even for an
    identical snapshot. ``generator_options`` is dropped (the deterministic
    invocation is in code + ADR-R9-TILES; ``generator`` — the tool version — stays),
    and ``name``/``description`` are normalised to ``name`` (``<compartment>-sites``)
    when provided.
    """
    if data[0:7] != b"PMTiles" or data[7] != 3:
        raise ValueError("not a PMTiles v3 archive")
    root_off = struct.unpack_from("<Q", data, 8)[0]
    root_len = struct.unpack_from("<Q", data, 16)[0]
    meta_off = struct.unpack_from("<Q", data, 24)[0]
    meta_len = struct.unpack_from("<Q", data, 32)[0]
    leaf_off = struct.unpack_from("<Q", data, 40)[0]
    leaf_len = struct.unpack_from("<Q", data, 48)[0]
    tile_off = struct.unpack_from("<Q", data, 56)[0]
    tile_len = struct.unpack_from("<Q", data, 64)[0]
    internal = data[97]

    raw_meta = data[meta_off : meta_off + meta_len]
    if internal == 2:
        meta_text = gzip.decompress(raw_meta)
    elif internal == 1:
        meta_text = raw_meta  # compression enum 1 = none
    else:
        raise ValueError(f"unsupported PMTiles internal compression {internal}")
    metadata = json.loads(meta_text)
    metadata["sig:license"] = license_id
    metadata["attribution"] = attribution
    if name is not None:
        metadata["name"] = name
        metadata["description"] = name
    metadata.pop("generator_options", None)
    for layer in metadata.get("vector_layers", []):
        if isinstance(layer, dict):
            layer["sig:license"] = license_id
            layer["sig:attribution"] = attribution
    new_meta = _gzip0(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    # Re-lay the sections out in the canonical order (header, root, meta, leaf,
    # tiles) with the updated offsets — tile bytes + directories are untouched.
    root = data[root_off : root_off + root_len]
    leaf = data[leaf_off : leaf_off + leaf_len]
    tiles = data[tile_off : tile_off + tile_len]
    new_header = bytearray(data[:127])
    new_meta_off = 127 + root_len
    new_leaf_off = new_meta_off + len(new_meta)
    new_tile_off = new_leaf_off + leaf_len
    struct.pack_into("<Q", new_header, 24, new_meta_off)
    struct.pack_into("<Q", new_header, 32, len(new_meta))
    struct.pack_into("<Q", new_header, 40, new_leaf_off)
    struct.pack_into("<Q", new_header, 56, new_tile_off)
    return bytes(new_header) + root + new_meta + leaf + tiles


def _bounds_of(features: Sequence[Mapping[str, object]]) -> tuple[float, float, float, float]:
    lons: list[float] = []
    lats: list[float] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        if isinstance(geom, Mapping) and geom.get("type") == "Point":
            c = geom.get("coordinates")
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                lons.append(float(c[0]))
                lats.append(float(c[1]))
    if not lons:
        return (-180.0, -85.0, 180.0, 85.0)
    return (min(lons), min(lats), max(lons), max(lats))


def layer_metadata(
    layer_name: str,
    features: Sequence[Mapping[str, object]],
    *,
    license_id: str,
    attribution: str,
    minzoom: int = PMTILES_MINZOOM,
    maxzoom: int = PMTILES_MAXZOOM,
    name: str | None = None,
) -> dict[str, object]:
    """The PMTiles metadata block: a ``vector_layers`` descriptor carrying the licence.

    The layer's licence + attribution are preserved here (ADR-048, §42) so any reader
    knows the ODbL obligations without opening a tile.
    """
    fields: dict[str, str] = {}
    for feat in features:
        props = feat.get("properties")
        if isinstance(props, Mapping):
            for k, v in props.items():
                fields[str(k)] = "Number" if isinstance(v, (int, float)) else "String"
    return {
        "name": name or layer_name,
        "format": "pbf",
        "attribution": attribution,
        "sig:license": license_id,
        "minzoom": minzoom,
        "maxzoom": maxzoom,
        "vector_layers": [
            {
                "id": layer_name,
                "description": f"{layer_name} ({license_id})",
                "fields": fields,
                "sig:license": license_id,
                "sig:attribution": attribution,
                "minzoom": minzoom,
                "maxzoom": maxzoom,
            }
        ],
        "tilestats": {
            "layerCount": 1,
            "layers": [{"layer": layer_name, "count": len(features), "geometry": "Point"}],
        },
    }


def render_pmtiles(
    geojson: Mapping[str, object],
    *,
    layer_name: str = "devices",
    license_id: str = "ODbL-1.0",
    attribution: str = ODBL_ATTRIBUTION,
    minzoom: int = PMTILES_MINZOOM,
    maxzoom: int = PMTILES_MAXZOOM,
    name: str | None = None,
) -> bytes:
    """Render a GeoJSON FeatureCollection into a PMTiles v3 archive (pure-Python).

    Renders the full z0–z14 pyramid (every point into its z/x/y tile per zoom,
    dedup'd per cell) and preserves the layer's licence + attribution in the
    archive metadata. Intended for small extents — a national-sized layer belongs
    on tippecanoe (see :func:`render_pmtiles_file`), which carries the same
    metadata contract after :func:`annotate_pmtiles`.
    """
    raw = geojson.get("features")
    features: list[Mapping[str, object]] = list(raw) if isinstance(raw, (list, tuple)) else []
    tiles = _render_pyramid(features, layer_name=layer_name, minzoom=minzoom, maxzoom=maxzoom)
    metadata = layer_metadata(
        layer_name,
        features,
        license_id=license_id,
        attribution=attribution,
        minzoom=minzoom,
        maxzoom=maxzoom,
        name=name,
    )
    bounds = _bounds_of(features)
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
    return build_pmtiles(
        tiles,
        metadata=metadata,
        bounds=bounds,
        center=center,
        minzoom=minzoom,
        maxzoom=maxzoom,
    )


def tippecanoe_available() -> bool:
    """Whether the ``tippecanoe`` renderer is on ``PATH`` (the production tile path)."""
    return shutil.which("tippecanoe") is not None


def _tippecanoe_argv(
    geojson_path: str, out_path: str, *, layer_name: str, attribution: str
) -> list[str]:
    """The pinned tippecanoe invocation (z0–z14, per-compartment layer, attribution)."""
    return [
        "tippecanoe",
        "-o",
        out_path,
        "-Z",
        str(PMTILES_MINZOOM),
        "-z",
        str(PMTILES_MAXZOOM),
        "-l",
        layer_name,
        "--force",
        "--attribution",
        attribution,
        geojson_path,
    ]


#: The only properties baked into the served vector tiles (ADR-R9-TILES / §19.4 —
#: tile features carry the already-published reduced fields only; claim ids, source
#: ids, licence lists and envelopes stay out of every tile's per-feature tags).
TILE_RENDER_PROPERTIES = (
    "entity_id",
    "entity_type",
    "label",
    "jurisdiction",
    "sensitivity_tier",
    "precision",
)


def slim_geojson_for_tiles(geojson_bytes: bytes) -> bytes:
    """Keep only :data:`TILE_RENDER_PROPERTIES` on each feature (deterministic)."""
    doc = json.loads(geojson_bytes)
    features = doc.get("features")
    if isinstance(features, list):
        for feat in features:
            if not isinstance(feat, dict):
                continue
            props = feat.get("properties")
            if isinstance(props, dict):
                feat["properties"] = {k: props[k] for k in TILE_RENDER_PROPERTIES if k in props}
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def render_compartment_sites_pmtiles(
    compartment: str, geojson_bytes: bytes, license_id: str
) -> tuple[bytes, str]:
    """Render one compartment's sites.geojson → PMTiles bytes (+ renderer name).

    Shared by the spine export (``build_spine_export``) and the jurisdiction bundle
    path (``sig-exports build --jurisdiction``): ODbL keeps its OSM notice (§42.3);
    every other compartment carries its own SPDX id — never a borrowed "CC-BY-4.0"
    label on a CC-BY-SA archive. The feature properties are slimmed to
    :data:`TILE_RENDER_PROPERTIES` first — the full sites.geojson row (claim_ids,
    source_ids, licence list, envelopes) is a *downloadable* shape, not a tile-render
    one. The renderer writes through a temp file (``render_pmtiles_file`` uses
    tippecanoe when present, else the pure-Python encoder); both render the z0–z14
    pyramid.
    """
    attribution = (
        ODBL_ATTRIBUTION if license_id == "ODbL-1.0" else f"© The SIG project — {license_id}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "sites.geojson"
        src.write_bytes(slim_geojson_for_tiles(geojson_bytes))
        out = Path(tmp) / "sites.pmtiles"
        renderer = render_pmtiles_file(
            str(src),
            str(out),
            layer_name="sites",
            license_id=license_id,
            attribution=attribution,
            name=f"{compartment}-sites",
        )
        return out.read_bytes(), renderer


def render_pmtiles_file(
    geojson_path: str,
    out_path: str,
    *,
    layer_name: str = "devices",
    license_id: str = "ODbL-1.0",
    attribution: str = ODBL_ATTRIBUTION,
    name: str | None = None,
) -> str:
    """Render ``geojson_path`` → PMTiles at ``out_path``. tippecanoe if present, else pure-Python.

    Returns the renderer used (``"tippecanoe"`` or ``"pure-python"``). Both paths
    write a PMTiles v3 archive covering z0–z14 whose metadata carries the layer's
    licence + attribution (the tippecanoe archive is stamped by
    :func:`annotate_pmtiles`).
    """
    if tippecanoe_available():
        subprocess.run(  # noqa: S603 - fixed argv, tippecanoe is a trusted local tool
            _tippecanoe_argv(
                geojson_path, out_path, layer_name=layer_name, attribution=attribution
            ),
            check=True,
            capture_output=True,
        )
        Path(out_path).write_bytes(
            annotate_pmtiles(
                Path(out_path).read_bytes(),
                license_id=license_id,
                attribution=attribution,
                name=name,
            )
        )
        return "tippecanoe"
    with open(geojson_path, encoding="utf-8") as fh:
        geojson = json.load(fh)
    data = render_pmtiles(
        geojson,
        layer_name=layer_name,
        license_id=license_id,
        attribution=attribution,
        name=name,
    )
    Path(out_path).write_bytes(data)
    return "pure-python"


__all__ = [
    "TILE_EXTENT",
    "ODBL_ATTRIBUTION",
    "PMTILES_MINZOOM",
    "PMTILES_MAXZOOM",
    "zxy_to_tileid",
    "tileid_to_zxy",
    "encode_mvt_points",
    "build_pmtiles",
    "annotate_pmtiles",
    "layer_metadata",
    "render_pmtiles",
    "render_pmtiles_file",
    "tippecanoe_available",
]
