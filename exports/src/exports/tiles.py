# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vector-tile rendering for the public map (LD-F07 / LD-H08, §40, ADR-048/ADR-051).

P14.2 emitted a *metadata-only* PMTiles archive (:func:`exports.formats.write_pmtiles`)
and deferred rendering real vector tiles to the map surface; P15.3 then left tile
generation out of scope — so nobody owned it (the orphaned LD-F07/LD-H08 handoff). This
module **closes that handoff**: it renders a GeoJSON point layer into a real, rendered
PMTiles v3 archive.

Two paths, one contract:

* **tippecanoe** — used when it is on ``PATH`` (the production path for large extents).
* **pure-Python fallback** — a self-contained Web-Mercator → MVT encoder + PMTiles v3
  writer, used when tippecanoe is absent. It is intended for **small extents** (the OKC
  point layer is tiny): it renders a single ``z0`` tile carrying every point, which is
  enough for the served map and needs no native toolchain (the zero-cost posture).

Either way the output is a spec-conformant PMTiles v3 archive whose metadata preserves
the layer's **ODbL licence + OSM attribution** (ADR-048, §42): the OSM-derived physical
layer stays a separate ODbL compartment with attribution + share-alike wherever it is
served, tiles included.
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


# --- Web-Mercator projection into a z0 tile ----------------------------------


def _project_z0(lon: float, lat: float, extent: int = TILE_EXTENT) -> tuple[int, int]:
    """Project (lon, lat) into integer tile coordinates of the single ``z0`` tile."""
    x = (lon + 180.0) / 360.0
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0
    return round(x * extent), round(y * extent)


# --- MVT encoding -------------------------------------------------------------


def encode_mvt_points(
    features: Sequence[Mapping[str, object]],
    *,
    layer_name: str,
    extent: int = TILE_EXTENT,
) -> bytes:
    """Encode GeoJSON point ``features`` as a single-layer Mapbox Vector Tile (z0).

    Only point geometries are encoded (the SIG device layer is points); a feature with a
    non-point geometry is skipped. Deterministic: identical features produce identical
    bytes, so the tile — and the archive that holds it — is reproducible.
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
    for i, feat in enumerate(features):
        geom = feat.get("geometry") or {}
        if not isinstance(geom, Mapping) or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue
        px, py = _project_z0(float(coords[0]), float(coords[1]), extent)
        # geometry: one MoveTo (command id 1, count 1) then the zigzag dx,dy from (0,0).
        geometry = [(1 & 0x7) | (1 << 3), _zigzag(px), _zigzag(py)]
        geom_bytes = b"".join(_varint(g) for g in geometry)

        tags: list[int] = []
        props = feat.get("properties") or {}
        if isinstance(props, Mapping):
            for k, v in sorted(props.items()):
                if not isinstance(v, (str, int, float, bool)):
                    v = json.dumps(v, sort_keys=True, separators=(",", ":"))
                tags.append(intern_key(str(k)))
                tags.append(intern_value(v))

        msg = bytearray()
        msg += _tag_varint(1, i)  # id
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


def _encode_value(v: object) -> bytes:
    if isinstance(v, bool):
        return _tag_varint(7, 1 if v else 0)  # bool_value
    if isinstance(v, int):
        return _tag_varint(4, v)  # int_value
    if isinstance(v, float):
        return _key(3, 1) + struct.pack("<d", v)  # double_value (wire type 1)
    return _tag_string(1, str(v))  # string_value


# --- PMTiles v3 archive with one rendered tile --------------------------------


def _gzip0(data: bytes) -> bytes:
    return gzip.compress(data, mtime=0)


def build_pmtiles(
    tile_bytes: bytes,
    *,
    metadata: Mapping[str, object],
    bounds: tuple[float, float, float, float] | None = None,
    center: tuple[float, float] | None = None,
) -> bytes:
    """Assemble a PMTiles v3 archive carrying a single rendered ``z0`` MVT tile.

    ``metadata`` is written as the archive's JSON metadata (gzip'd); it MUST carry the
    ``vector_layers`` descriptor so a reader knows the layer + its ODbL licence.
    """
    # Directory with the real tile length.
    directory = bytearray()
    directory += _varint(1)  # entries
    directory += _varint(0)  # tile_id delta 0
    directory += _varint(1)  # run_length
    directory += _varint(len(_gzip0(tile_bytes)))  # length (compressed tile)
    directory += _varint(0)  # offset 0 (contiguous)
    root_dir = _gzip0(bytes(directory))
    meta = _gzip0(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    leaf_dir = b""
    tile_data = _gzip0(tile_bytes)

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
    struct.pack_into("<Q", header, 72, 1)  # num addressed tiles
    struct.pack_into("<Q", header, 80, 1)  # num tile entries
    struct.pack_into("<Q", header, 88, 1)  # num tile contents
    header[96] = 1  # clustered
    header[97] = 2  # internal compression: gzip
    header[98] = 2  # tile compression: gzip
    header[99] = 1  # tile type: mvt
    header[100] = 0  # min zoom
    header[101] = 0  # max zoom
    struct.pack_into("<i", header, 102, e7(minx))
    struct.pack_into("<i", header, 106, e7(miny))
    struct.pack_into("<i", header, 110, e7(maxx))
    struct.pack_into("<i", header, 114, e7(maxy))
    header[118] = 0  # center zoom
    struct.pack_into("<i", header, 119, e7(cx))
    struct.pack_into("<i", header, 123, e7(cy))
    return bytes(header) + root_dir + meta + leaf_dir + tile_data


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
        "name": layer_name,
        "format": "pbf",
        "attribution": attribution,
        "sig:license": license_id,
        "vector_layers": [
            {
                "id": layer_name,
                "description": f"{layer_name} ({license_id})",
                "fields": fields,
                "sig:license": license_id,
                "sig:attribution": attribution,
                "minzoom": 0,
                "maxzoom": 0,
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
) -> bytes:
    """Render a GeoJSON FeatureCollection into a PMTiles v3 archive (pure-Python).

    Renders one ``z0`` tile with every point feature and preserves the layer's ODbL
    licence + attribution in the archive metadata. For small extents (the OKC layer) a
    single tile is faithful; large extents should use tippecanoe (see
    :func:`render_pmtiles_file`).
    """
    raw = geojson.get("features")
    features: list[Mapping[str, object]] = list(raw) if isinstance(raw, (list, tuple)) else []
    tile = encode_mvt_points(features, layer_name=layer_name)
    metadata = layer_metadata(layer_name, features, license_id=license_id, attribution=attribution)
    bounds = _bounds_of(features)
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
    return build_pmtiles(tile, metadata=metadata, bounds=bounds, center=center)


def tippecanoe_available() -> bool:
    """Whether the ``tippecanoe`` renderer is on ``PATH`` (the production tile path)."""
    return shutil.which("tippecanoe") is not None


def render_pmtiles_file(
    geojson_path: str,
    out_path: str,
    *,
    layer_name: str = "devices",
    license_id: str = "ODbL-1.0",
    attribution: str = ODBL_ATTRIBUTION,
) -> str:
    """Render ``geojson_path`` → PMTiles at ``out_path``. tippecanoe if present, else pure-Python.

    Returns the renderer used (``"tippecanoe"`` or ``"pure-python"``). Both paths write a
    PMTiles v3 archive whose metadata carries the layer's ODbL licence + attribution.
    """
    if tippecanoe_available():
        with tempfile.TemporaryDirectory() as tmp:
            attr = Path(tmp) / "attr.json"
            attr.write_text(
                json.dumps({"attribution": attribution, "sig:license": license_id}),
                encoding="utf-8",
            )
            subprocess.run(  # noqa: S603 - fixed argv, tippecanoe is a trusted local tool
                [
                    "tippecanoe",
                    "-o",
                    out_path,
                    "-l",
                    layer_name,
                    "-zg",
                    "--force",
                    "--attribution",
                    attribution,
                    geojson_path,
                ],
                check=True,
                capture_output=True,
            )
        return "tippecanoe"
    with open(geojson_path, encoding="utf-8") as fh:
        geojson = json.load(fh)
    data = render_pmtiles(
        geojson, layer_name=layer_name, license_id=license_id, attribution=attribution
    )
    Path(out_path).write_bytes(data)
    return "pure-python"


__all__ = [
    "TILE_EXTENT",
    "ODBL_ATTRIBUTION",
    "encode_mvt_points",
    "build_pmtiles",
    "layer_metadata",
    "render_pmtiles",
    "render_pmtiles_file",
    "tippecanoe_available",
]
