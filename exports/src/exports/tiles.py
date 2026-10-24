# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vector-tile rendering for the public map (``sig.map-tiles/2``, ADR-156).

P14.2 emitted a *metadata-only* PMTiles archive (:func:`exports.formats.write_pmtiles`)
and deferred rendering real vector tiles to the map surface; P15.3 left tile
generation out of scope — so nobody owned it (the orphaned LD-F07/LD-H08 handoff).
P31.15 closed that handoff with z0–z14 per-compartment archives; **P35.52
replaces their content contract** after F-104/F-414 measured the default
tippecanoe dropping keeping ≈ 0.03 % of sites at z3.

The ``sig.map-tiles/2`` archive carries **two layers** (K1-map §3.1):

* ``cells`` (z0–z9) — one point per H3 cell at the cell-resolution band
  :data:`CELL_BANDS` assigns, placed at the transformed mean position of the
  records it aggregates, carrying ``h3`` (cell id), ``n`` (record count),
  ``ns`` (distinct sources) and ``jp`` (plurality K4 jurisdiction key).
* ``sites`` — every published located record in its tier's zoom band
  (:data:`SITE_MINZOOM_BY_TIER`): tier 0 from z10 and tier 1 from z11 as
  points, tier 2 from z12 as the H3 display polygon
  (:data:`TIER2_H3_RESOLUTION`), tier 3 never. Sites carry ``rk`` (the
  ``sig.published-record`` record key) and ``tr`` (the tier).

Every emitted feature declares its zoom range + layer through the GeoJSON
``"tippecanoe"`` member (``{"layer", "minzoom", "maxzoom"}``), which both
renderers honour.

Two renderers, one contract:

* **tippecanoe** — used when it is on ``PATH`` (the production path; built from
  a pinned source tarball in the export image, ops/Dockerfile). The invocation
  is :data:`RETENTION_ARGV`-compliant: ``-r1`` (never drop at lower zooms),
  ``--no-tile-size-limit`` + ``--no-feature-limit`` (tippecanoe's own limits
  drop silently — the contract forbids every ``--drop*``/``--coalesce*``/
  ``--cluster*`` flag via :func:`assert_retention_argv`), and the finished
  archive is size-checked afterwards so an oversized tile **fails the build
  loudly** rather than thinning (``sig-exports tiles verify`` re-checks it).
* **pure-Python fallback** — a self-contained Web-Mercator → MVT encoder +
  PMTiles v3 writer rendering the same pyramid under the same per-feature
  zoom ranges. The verifier holds the two renderers to parity on the ``rk``
  set and Σ ``n`` per zoom (not byte equality — §9.2 check 2).

Dedup policy (both renderers): only **byte-identical** features are
deduplicated — two distinct entities that share a tile pixel or an H3 cell are
never coalesced (the pre-P35.52 ``_DEDUP_CELL`` behaviour was the second,
quieter half of the F-414 loss).

Either way the output is a deterministic, spec-conformant PMTiles v3 archive
whose metadata preserves the layer's **licence + attribution** (ADR-048, §42):
the OSM-derived physical layer stays a separate ODbL compartment with
attribution + share-alike wherever it is served, tiles included.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import shutil
import struct
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

import h3
from policy.sensitivity import assert_public_layer_subject

from .published_record import record_key

#: MVT tile extent (the coordinate grid inside a tile); 4096 is the de-facto default.
TILE_EXTENT = 4096
#: The ODbL attribution the OSM-derived layer must carry in every context (§42, SIG-GEO-013).
ODBL_ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
#: The public map zoom range (P31.15 / ADR-R9-TILES): the whole pyramid z0..z14.
PMTILES_MINZOOM = 0
PMTILES_MAXZOOM = 14

# --- the sig.map-tiles/2 contract (ADR-156, K1-map §3.1–§3.4) ------------------

#: The archive contract version — stamped into metadata + ``web/tiles/index.json``.
TILE_CONTRACT = "sig.map-tiles/2"
#: Layer names inside every ``sig.map-tiles/2`` archive.
CELLS_LAYER = "cells"
SITES_LAYER = "sites"
#: ``cells`` carries the map below this; ``sites`` carries it above.
CELL_ZOOM_MAX = 9
#: ``(band_min_zoom, band_max_zoom, h3_resolution)`` — z0–4 → res 3,
#: z5–6 → res 4, z7–8 → res 5, z9 → res 6 (K1 §3.1).
CELL_BANDS: tuple[tuple[int, int, int], ...] = (
    (0, 4, 3),
    (5, 6, 4),
    (7, 8, 5),
    (9, 9, 6),
)
#: The zoom a tier's site features start at (K1 §3.1): tier 0 → z10,
#: tier 1 → z11, tier 2 → z12. Tier 3 is never tiled.
SITE_MINZOOM_BY_TIER: dict[int, int] = {0: 10, 1: 11, 2: 12}
#: Tier-2 display polygon resolution — the published tier-2 transform is the
#: declared ~1 km bin (``policy/data/sensitivity.toml`` ``grid_bin`` 1000 m);
#: res-8 cells average ≈ 0.74 km², the closest H3 band to the declared bin
#: (ADR-156).
TIER2_H3_RESOLUTION = 8
#: Fail-loud tile-size contract (K1 §9.2.4): an archive with any stored tile
#: above the limit fails the build; at/above the warn bound the verifier notes
#: it without failing.
TILE_SIZE_LIMIT_BYTES = 500 * 1024
TILE_SIZE_WARN_BYTES = 200 * 1024
#: This row's emitted property vocabularies (K1 §3.3, MAP-01a subset — the
#: remaining facets ``lb``/``tc``/``vd``/``op``/``sr``/``j``/``f``/``l``/``st``/
#: ``pm``/``co`` and the cell facet keys are MAP-01b's; the verifier's admitted
#: set already covers them so their later addition stays contract-clean).
SITE_PROPERTY_KEYS = ("rk", "tr")
CELL_PROPERTY_KEYS = ("h3", "n", "ns", "jp")
#: The full §3.3 vocabularies the verifier admits (key-name allowlists).
ALLOWED_SITE_KEYS = frozenset(
    {"rk", "lb", "tc", "vd", "op", "oe", "sr", "j", "f", "l", "st", "tr", "pm", "co"}
)
ALLOWED_CELL_KEYS = frozenset({"h3", "n", "ns", "jp", "s1", "sx"})
#: K4 key used when a record's jurisdiction is unresolved/conflicted (§3.3).
UNPLACED_JURISDICTION_KEY = "unplaced"
_UNRESOLVED_JURISDICTION_MARKERS = frozenset(
    {"(unresolved)", "(unasserted)", "(conflicted)", "unresolved"}
)

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


def _unproject_xy(wx: float, wy: float) -> tuple[float, float]:
    """Invert :func:`_project_xy` — world coords → (lon, lat)."""
    lon = wx * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * wy))))
    return lon, lat


def _tile_and_local(wx: float, wy: float, z: int, extent: int) -> tuple[int, int, int, int]:
    """World coords → (tile_x, tile_y, local_x, local_y) at zoom ``z``."""
    n = 1 << z
    gx, gy = wx * n, wy * n
    tx = min(n - 1, max(0, int(gx)))
    ty = min(n - 1, max(0, int(gy)))
    lx = round((gx - tx) * extent)
    ly = round((gy - ty) * extent)
    return tx, ty, lx, ly


# --- the sig.map-tiles/2 feature emit ------------------------------------------


def _ring_ccw(ring: list[list[float]]) -> list[list[float]]:
    """Return ``ring`` wound counter-clockwise in (x, y)-up coordinates.

    GeoJSON exterior rings SHOULD be CCW (RFC 7946 §3.1.6); h3 boundaries come
    back vertex-ordered but we normalise so the emitted geometry is
    deterministic regardless of the input winding.
    """
    area = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1]
        area += x1 * y2 - x2 * y1
    if area < 0:
        return [list(p) for p in reversed(ring)]
    return [list(p) for p in ring]


def _tier2_polygon(lon: float, lat: float) -> dict[str, object]:
    """The tier-2 display geometry: the H3 cell polygon at the contract's
    tier-2 display resolution around the already-reduced point (§3.4)."""
    cell = h3.latlng_to_cell(lat, lon, TIER2_H3_RESOLUTION)
    ring = [[lng, lt] for lt, lng in h3.cell_to_boundary(cell)]
    ring = _ring_ccw(ring)
    ring.append(list(ring[0]))  # GeoJSON rings close on the first vertex
    return {"type": "Polygon", "coordinates": [ring]}


class _CellAcc(TypedDict):
    """The in-progress aggregate of one (band, h3) cell."""

    n: int
    sources: set[str]
    jurisdictions: dict[str, int]
    sum_lat: float
    sum_lon: float


def map_tile_features(
    features: Sequence[Mapping[str, object]],
    compartment: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Emit the ``sig.map-tiles/2`` feature set for one compartment.

    Returns ``(cells_features, sites_features)`` — both carry a
    ``"tippecanoe": {"layer", "minzoom", "maxzoom"}`` member both renderers
    honour. Every input feature must be a located published point: the
    public-layer refusal runs on the FULL properties before any reduction
    (a refused subject is a build error, never a silently dropped feature).
    Non-located features (null geometry) are skipped; non-Point geometry is a
    contract violation and raises.
    """
    cell_acc: dict[tuple[int, str], _CellAcc] = {}
    sites: list[dict[str, object]] = []
    for feat in features:
        if not isinstance(feat, Mapping):
            continue
        props = feat.get("properties")
        props = props if isinstance(props, Mapping) else {}
        assert_public_layer_subject(
            str(props.get("entity_type") or ""),
            residential_parcel_flag=bool(props.get("residential_parcel_flag")),
            surface="tiles",
        )
        geom = feat.get("geometry")
        if geom is None:
            continue  # not a located record — the geo never claimed a point
        if not isinstance(geom, Mapping) or geom.get("type") != "Point":
            raise ValueError(f"sig.map-tiles/2 emits located points only; got geometry {geom!r}")
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            raise ValueError("sig.map-tiles/2 point feature missing coordinates")
        lon, lat = float(coords[0]), float(coords[1])
        tier = int(props.get("sensitivity_tier") or 0)
        if tier not in (0, 1, 2, 3):
            raise ValueError(f"sensitivity_tier {tier} outside 0–3")

        # cells: the record aggregates into one cell per zoom band at its
        # published (already tier-transformed) position.
        source_ids = props.get("source_ids")
        source_key: tuple[str, ...] = (
            tuple(sorted(str(s) for s in source_ids))
            if isinstance(source_ids, (list, tuple)) and source_ids
            else ("(unattributed)",)
        )
        jkey = str(props.get("jurisdiction") or UNPLACED_JURISDICTION_KEY)
        if jkey in _UNRESOLVED_JURISDICTION_MARKERS:
            jkey = UNPLACED_JURISDICTION_KEY
        for band_i, (_zmin, _zmax, res) in enumerate(CELL_BANDS):
            cell = h3.latlng_to_cell(lat, lon, res)
            acc = cell_acc.setdefault(
                (band_i, cell),
                _CellAcc(n=0, sources=set(), jurisdictions={}, sum_lat=0.0, sum_lon=0.0),
            )
            acc["n"] += 1
            acc["sources"].update(source_key)
            acc["jurisdictions"][jkey] = acc["jurisdictions"].get(jkey, 0) + 1
            acc["sum_lat"] += lat
            acc["sum_lon"] += lon

        # sites: tier 3 is never tiled (§3.4 — nothing is drawn).
        if tier == 3:
            continue
        rk = record_key(
            compartment,
            str(props.get("entity_type") or "(unknown)"),
            str(props.get("entity_id") or ""),
        )
        geometry: dict[str, object] = (
            {"type": "Point", "coordinates": [lon, lat]} if tier < 2 else _tier2_polygon(lon, lat)
        )
        sites.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {"rk": rk, "tr": tier},
                "tippecanoe": {
                    "layer": SITES_LAYER,
                    "minzoom": SITE_MINZOOM_BY_TIER[tier],
                    "maxzoom": PMTILES_MAXZOOM,
                },
            }
        )

    cells: list[dict[str, object]] = []
    for (band_i, cell), acc in sorted(cell_acc.items()):
        zmin, zmax, _res = CELL_BANDS[band_i]
        n = acc["n"]
        jp = sorted(acc["jurisdictions"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        cells.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [acc["sum_lon"] / n, acc["sum_lat"] / n],
                },
                "properties": {
                    "h3": cell,
                    "n": n,
                    "ns": len(acc["sources"]),
                    "jp": jp,
                },
                "tippecanoe": {
                    "layer": CELLS_LAYER,
                    "minzoom": zmin,
                    "maxzoom": zmax,
                },
            }
        )
    sites.sort(key=lambda f: str(cast("Mapping[str, object]", f["properties"])["rk"]))
    return cells, sites


def map_tile_geojson(geojson_bytes: bytes, compartment: str) -> bytes:
    """Compile a compartment sites.geojson into the ``sig.map-tiles/2`` emit.

    The returned FeatureCollection holds the ``cells`` + ``sites`` features —
    each with its ``"tippecanoe"`` layer/minzoom/maxzoom member — in canonical
    JSON so the tippecanoe input is itself deterministic.
    """
    doc = json.loads(geojson_bytes)
    features = doc.get("features")
    cells, sites = map_tile_features(
        list(features) if isinstance(features, list) else [], compartment
    )
    out = {"type": "FeatureCollection", "features": cells + sites}
    return json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _feature_signature(feat: Mapping[str, object]) -> bytes:
    """The dedupe identity of an emitted feature: its canonical geometry +
    properties + zoom contract. Only byte-identical features collapse (the
    contract forbids coalescing distinct entities that merely share a cell)."""
    return json.dumps(
        {
            "g": feat.get("geometry"),
            "p": feat.get("properties"),
            "t": feat.get("tippecanoe"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# --- MVT encoding --------------------------------------------------------------


def _intern(props: Mapping[str, object]) -> list[tuple[str, object]]:
    """Normalized (json-safe) property pairs in deterministic (sorted-key) order."""
    pairs: list[tuple[str, object]] = []
    for k, v in sorted(props.items()):
        if not isinstance(v, (str, int, float, bool)):
            v = json.dumps(v, sort_keys=True, separators=(",", ":"))
        pairs.append((str(k), v))
    return pairs


def _ring_tile_area(ring: Sequence[tuple[int, int]]) -> int:
    """Signed shoelace area of a ring in tile-local coords (y points down)."""
    area = 0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area


def _polygon_commands(rings: Sequence[list[tuple[int, int]]]) -> list[int]:
    """MVT command stream for a polygon's rings (exterior wound for the spec's
    positive-screen-area rule — clockwise on a y-down canvas)."""
    cmds: list[int] = []
    for idx, ring in enumerate(rings):
        pts = list(ring)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]  # MVT rings don't repeat the first vertex
        if len(pts) < 3:
            continue
        want_positive = idx == 0  # exterior ring: positive screen area
        if (_ring_tile_area(pts) > 0) != want_positive:
            pts.reverse()
        cursor_x, cursor_y = 0, 0
        cmds.append((1 & 0x7) | (1 << 3))  # MoveTo, count 1
        dx, dy = _zigzag(pts[0][0] - cursor_x), _zigzag(pts[0][1] - cursor_y)
        cmds += [dx, dy]
        cursor_x, cursor_y = pts[0]
        cmds.append((2 & 0x7) | ((len(pts) - 1) << 3))  # LineTo
        for x, y in pts[1:]:
            cmds += [_zigzag(x - cursor_x), _zigzag(y - cursor_y)]
            cursor_x, cursor_y = x, y
        cmds.append((7 & 0x7) | (1 << 3))  # ClosePath
    return cmds


#: One drawable unit inside a tile: (geom_kind, payload, feature_index).
#: ``payload`` is ``(lx, ly)`` for points and ``[[(lx, ly), …], …]`` (rings)
#: for polygons.
_TileEntry = tuple[str, object, int]


def _encode_layer(
    entries: Sequence[_TileEntry],
    features: Sequence[Mapping[str, object]],
    *,
    layer_name: str,
    extent: int = TILE_EXTENT,
) -> bytes:
    """Encode tile-local ``entries`` as one MVT layer (deterministic bytes)."""
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
    for kind, payload, fidx in entries:
        feat = features[fidx]
        props = feat.get("properties") or {}
        tags: list[int] = []
        if isinstance(props, Mapping):
            for k, v in _intern(props):
                tags.append(intern_key(k))
                tags.append(intern_value(v))

        if kind == "polygon":
            geometry = _polygon_commands(payload)  # type: ignore[arg-type]
            geom_type = 3
        else:
            lx, ly = cast("tuple[int, int]", payload)
            geometry = [
                (1 & 0x7) | (1 << 3),
                _zigzag(lx),
                _zigzag(ly),
            ]
            geom_type = 1
        geom_bytes = b"".join(_varint(g) for g in geometry)

        msg = bytearray()
        msg += _tag_varint(1, fidx)  # id
        if tags:
            packed = b"".join(_varint(t) for t in tags)
            msg += _tag_bytes(2, packed)  # tags (packed)
        msg += _tag_varint(3, geom_type)  # type
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
    (:func:`_render_pyramid`) encodes the real per-z/x/y tiles.
    """
    entries: list[_TileEntry] = []
    for i, feat in enumerate(features):
        geom = feat.get("geometry") or {}
        if not isinstance(geom, Mapping) or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue
        wx, wy = _project_xy(float(coords[0]), float(coords[1]))
        _tx, _ty, lx, ly = _tile_and_local(wx, wy, 0, extent)
        entries.append(("point", (lx, ly), i))
    return _encode_layer(entries, features, layer_name=layer_name, extent=extent)


def _encode_value(v: object) -> bytes:
    if isinstance(v, bool):
        return _tag_varint(7, 1 if v else 0)  # bool_value
    if isinstance(v, int):
        return _tag_varint(4, v)  # int_value
    if isinstance(v, float):
        return _key(3, 1) + struct.pack("<d", v)  # double_value (wire type 1)
    return _tag_string(1, str(v))  # string_value


# --- the z0..z14 pyramid -------------------------------------------------------


def _feature_zoom_range(
    feat: Mapping[str, object], default_min: int, default_max: int
) -> tuple[int, int]:
    """The feature's declared zoom band — its ``"tippecanoe"`` member, or the
    archive-wide default for features that carry none."""
    member = feat.get("tippecanoe")
    if isinstance(member, Mapping):
        try:
            fmin = int(member.get("minzoom", default_min))
            fmax = int(member.get("maxzoom", default_max))
            return max(default_min, fmin), min(default_max, fmax)
        except (TypeError, ValueError):
            pass
    return default_min, default_max


def _feature_layer(feat: Mapping[str, object], default: str) -> str:
    member = feat.get("tippecanoe")
    if isinstance(member, Mapping) and member.get("layer"):
        return str(member["layer"])
    return default


def _feature_local_geometry(
    feat: Mapping[str, object], z: int, extent: int
) -> tuple[object, int, int, int, int] | None:
    """Tile-space geometry at zoom ``z``.

    Returns ``(payload, tile_x0, tile_y0, tile_x1, tile_y1)`` — the payload +
    the inclusive tile range the feature's bounds cover (one tile for a
    point; the bbox span for a polygon). Local coords may exceed
    ``[0, extent)`` — that is exactly how MVT buffers encode.
    """
    geom = feat.get("geometry")
    if not isinstance(geom, Mapping):
        return None
    n = 1 << z
    gtype = geom.get("type")
    if gtype == "Point":
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            return None
        wx, wy = _project_xy(float(coords[0]), float(coords[1]))
        tx, ty, lx, ly = _tile_and_local(wx, wy, z, extent)
        return (lx, ly), tx, ty, tx, ty
    if gtype == "Polygon":
        raw_rings = geom.get("coordinates")
        if not isinstance(raw_rings, (list, tuple)) or not raw_rings:
            return None
        rings: list[list[tuple[int, int]]] = []
        tx0, ty0, tx1, ty1 = n - 1, n - 1, 0, 0
        for raw_ring in raw_rings:
            if not isinstance(raw_ring, (list, tuple)):
                continue
            ring: list[tuple[int, int]] = []
            for pt in raw_ring:
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    continue
                wx, wy = _project_xy(float(pt[0]), float(pt[1]))
                gx, gy = wx * n, wy * n
                tx = min(n - 1, max(0, int(gx)))
                ty = min(n - 1, max(0, int(gy)))
                # ring vertices track their own tile's origin; the tile loop
                # below rebases them per covering tile.
                lx = round(gx * extent)  # world-pixel coords
                ly = round(gy * extent)
                ring.append((lx, ly))
                tx0, ty0, tx1, ty1 = min(tx0, tx), min(ty0, ty), max(tx1, tx), max(ty1, ty)
            if ring:
                rings.append(ring)
        if not rings:
            return None
        # payload = world-pixel rings; the per-tile step subtracts tile origin.
        return rings, tx0, ty0, tx1, ty1
    return None


def _render_pyramid(
    features: Sequence[Mapping[str, object]],
    *,
    layer_name: str,
    extent: int = TILE_EXTENT,
    minzoom: int = PMTILES_MINZOOM,
    maxzoom: int = PMTILES_MAXZOOM,
) -> dict[int, bytes]:
    """Render ``features`` into ``{tile_id: mvt_bytes}`` across the zoom pyramid.

    Per-feature ``"tippecanoe"`` members assign the target layer and zoom band;
    features without one render into ``layer_name`` for the whole pyramid.
    A tile carries each present layer as a separate MVT layer block (sorted by
    layer name — ``cells`` before ``sites``), keyed by the PMTiles Hilbert tile
    id in clustered order. **Only byte-identical features are deduplicated**
    (:func:`_feature_signature`) — distinct entities sharing a pixel or cell
    survive everywhere (P35.52; the old ``_DEDUP_CELL`` coalescing is gone).
    """
    # Global byte-identical dedupe first: identical input features produce
    # identical output everywhere, so one global pass replaces per-tile dedupe.
    seen: set[bytes] = set()
    deduped: list[Mapping[str, object]] = []
    for feat in features:
        sig = _feature_signature(feat)
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(feat)

    # Project each feature once; record (feature idx, layer, fmin, fmax, geom).
    prepared: list[tuple[int, str, int, int, Mapping[str, object]]] = []
    for i, feat in enumerate(deduped):
        geom = feat.get("geometry")
        if not isinstance(geom, Mapping) or geom.get("type") not in ("Point", "Polygon"):
            continue
        fmin, fmax = _feature_zoom_range(feat, minzoom, maxzoom)
        if fmax < fmin:
            continue
        prepared.append((i, _feature_layer(feat, layer_name), fmin, fmax, feat))

    tiles: dict[int, bytes] = {}
    for z in range(minzoom, maxzoom + 1):
        # tile -> layer -> entries
        per_tile: dict[tuple[int, int], dict[str, list[_TileEntry]]] = {}
        for i, layer, fmin, fmax, feat in prepared:
            if z < fmin or z > fmax:
                continue
            local = _feature_local_geometry(feat, z, extent)
            if local is None:
                continue
            payload, tx0, ty0, tx1, ty1 = local
            gtype = feat["geometry"]["type"]  # type: ignore[index]
            for tx in range(tx0, tx1 + 1):
                for ty in range(ty0, ty1 + 1):
                    if gtype == "Point":
                        entry_payload: object = payload
                    else:
                        # rebase world-pixel rings into this tile's origin
                        entry_payload = [
                            [(x - tx * extent, y - ty * extent) for x, y in ring]
                            for ring in cast("list[list[tuple[int, int]]]", payload)
                        ]
                    bucket = per_tile.setdefault((tx, ty), {}).setdefault(layer, [])
                    bucket.append(
                        (
                            "polygon" if gtype == "Polygon" else "point",
                            entry_payload,
                            i,
                        )
                    )
        for (tx, ty), layers in per_tile.items():
            tile_msg = b"".join(
                _encode_layer(layers[lname], deduped, layer_name=lname, extent=extent)
                for lname in sorted(layers)
            )
            tiles[zxy_to_tileid(z, tx, ty)] = tile_msg
    return dict(sorted(tiles.items()))


# --- PMTiles v3 archive --------------------------------------------------------


def _gzip0(data: bytes) -> bytes:
    return gzip.compress(data, mtime=0)


#: PMTiles v3 directory entry: ``(tile_id, run_length, length, offset)``.
#: ``run_length == 0`` marks a leaf-directory pointer whose ``offset``/``length``
#: address bytes inside the leaf-directory section instead of the tile-data
#: section (spec §4.2).
_DirectoryEntry = tuple[int, int, int, int]

#: The root directory must stay under the reader's optimistic first read: the
#: reference JS reader fetches ``bytes=0-16383`` (header + root) and parses the
#: root directory from that buffer — a root directory larger than the fetch
#: decompresses as a truncated stream and the archive reads as broken even
#: though it is spec-valid. 16384 − 127-byte header − margin.
_ROOT_DIR_MAX_BYTES = 16000
#: Entries per leaf directory when the root spills: bounded so a leaf fetch is
#: a single small range read (~40 KB gzip), and the root shrinks to one entry
#: per ~4 k tiles.
_LEAF_DIR_MAX_ENTRIES = 4096


def _serialize_directory(entries: Sequence[_DirectoryEntry]) -> bytes:
    """Serialize one directory section (spec §4.2).

    Layout: n_entries, then delta tile_ids, run_lengths, lengths, offsets.
    Offsets encode as ``offset + 1``, or ``0`` when the entry is contiguous with
    the previous one — our tile data is clustered/contiguous so tile entries
    after the first encode 0.
    """
    directory = bytearray()
    directory += _varint(len(entries))
    prev_id = 0
    for i, (tid, _rl, _ln, _off) in enumerate(entries):
        directory += _varint(tid - prev_id if i else tid)
        prev_id = tid
    for _tid, run_length, _ln, _off in entries:
        directory += _varint(run_length)
    for _tid, _rl, length, _off in entries:
        directory += _varint(length)
    prev_end = 0
    for i, (_tid, _rl, length, offset) in enumerate(entries):
        if i > 0 and offset == prev_end:
            directory += _varint(0)  # contiguous with the previous entry
        else:
            directory += _varint(offset + 1)
        prev_end = offset + length
    return bytes(directory)


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

    ``tiles`` is sorted by Hilbert tile id (the clustered layout). Small
    archives keep the classic flat root directory; once the serialized root
    would exceed the reader's 16 KiB optimistic first read (a national-scale
    pyramid can need ~1 MB of index) the entries spill into leaf directories —
    one leaf per ``_LEAF_DIR_MAX_ENTRIES`` consecutive entries, the root holding
    one ``run_length == 0`` pointer per leaf (spec §4.2). ``metadata`` is
    written as the archive's JSON metadata (gzip'd); it MUST carry the
    ``vector_layers`` descriptor so a reader knows the layer + its licence.
    """
    tile_ids = sorted(tiles)
    compressed = {tid: _gzip0(tiles[tid]) for tid in tile_ids}

    offset = 0
    tile_entries: list[_DirectoryEntry] = []
    for tid in tile_ids:
        tile_entries.append((tid, 1, len(compressed[tid]), offset))
        offset += len(compressed[tid])

    root_entries: list[_DirectoryEntry] = tile_entries
    root_dir = _gzip0(_serialize_directory(root_entries))
    leaf_dir = b""
    n_leaf_refs = 0
    if len(root_dir) > _ROOT_DIR_MAX_BYTES:
        leaf_blobs: list[bytes] = []
        root_entries = []
        leaf_offset = 0
        for start in range(0, len(tile_entries), _LEAF_DIR_MAX_ENTRIES):
            chunk = tile_entries[start : start + _LEAF_DIR_MAX_ENTRIES]
            blob = _gzip0(_serialize_directory(chunk))
            root_entries.append((chunk[0][0], 0, len(blob), leaf_offset))
            leaf_blobs.append(blob)
            leaf_offset += len(blob)
        n_leaf_refs = len(root_entries)
        root_dir = _gzip0(_serialize_directory(root_entries))
        leaf_dir = b"".join(leaf_blobs)
    meta = _gzip0(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8"))
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
    # Spec §3 counts: addressed = every directory entry (tile + leaf-pointer);
    # entries = run_length > 0 tile entries only; contents = unique data blobs.
    struct.pack_into("<Q", header, 72, len(tile_ids) + n_leaf_refs)
    struct.pack_into("<Q", header, 80, len(tile_ids))
    struct.pack_into("<Q", header, 88, len(tile_ids))
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
    licence (``sig:license``), the ``sig.map-tiles/2`` contract tag and per-
    ``vector_layers`` attribution without touching the tile bytes — so a
    tippecanoe-rendered archive carries the same licence contract as the
    pure-Python one (the served map reads ``sig:license`` per source).

    It is also the **determinism normalisation**: tippecanoe embeds the input/output
    file paths in ``name``/``description``/``generator_options`` — the export renders
    through a random temp dir, so the raw archive differs run-to-run even for an
    identical snapshot. ``generator_options`` is dropped (the deterministic
    invocation is in code + ADR-156; ``generator`` — the tool version — stays),
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
    metadata["sig:map-tiles-contract"] = TILE_CONTRACT
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


# --- archive introspection (the size guard + the verifier's reader) -------------


def read_pmtiles_directory(data: bytes) -> tuple[dict[int, tuple[int, int]], dict[str, object]]:
    """Read a PMTiles v3 archive's tile directory + JSON metadata.

    Returns ``({tile_id: (offset, length)}, metadata)`` — offsets/lengths
    address the compressed tile-data section. Leaf directories are followed.
    """
    if data[0:7] != b"PMTiles" or data[7] != 3:
        raise ValueError("not a PMTiles v3 archive")
    root_off = struct.unpack_from("<Q", data, 8)[0]
    root_len = struct.unpack_from("<Q", data, 16)[0]
    meta_off = struct.unpack_from("<Q", data, 24)[0]
    meta_len = struct.unpack_from("<Q", data, 32)[0]
    leaf_off = struct.unpack_from("<Q", data, 40)[0]
    tile_off = struct.unpack_from("<Q", data, 56)[0]
    internal = data[97]

    def uncompress(raw: bytes) -> bytes:
        if internal == 2:
            return gzip.decompress(raw)
        if internal == 1:
            return raw
        raise ValueError(f"unsupported PMTiles internal compression {internal}")

    def parse_dir(raw: bytes) -> list[_DirectoryEntry]:
        blob = uncompress(raw)
        pos = 0

        def read_varint() -> int:
            nonlocal pos
            shift = result = 0
            while True:
                b = blob[pos]
                pos += 1
                result |= (b & 0x7F) << shift
                if not (b & 0x80):
                    return result
                shift += 7

        n = read_varint()
        ids = []
        last = 0
        for _ in range(n):
            last += read_varint()
            ids.append(last)
        runs = [read_varint() for _ in range(n)]
        lengths = [read_varint() for _ in range(n)]
        offsets: list[int] = []
        for i in range(n):
            v = read_varint()
            if v == 0 and i > 0:
                offsets.append(offsets[i - 1] + lengths[i - 1])
            else:
                offsets.append(v - 1)
        return [(ids[i], runs[i], lengths[i], offsets[i]) for i in range(n)]

    root = parse_dir(data[root_off : root_off + root_len])
    leaf_len = struct.unpack_from("<Q", data, 48)[0]
    leaf_section = data[leaf_off : leaf_off + leaf_len]
    entries: dict[int, tuple[int, int]] = {}
    for tid, run, length, offset in root:
        if run == 0:
            for ltid, _lrun, llen, loff in parse_dir(leaf_section[offset : offset + length]):
                entries[ltid] = (loff, llen)
        else:
            entries[tid] = (offset, length)
    meta_raw = data[meta_off : meta_off + meta_len]
    metadata = json.loads(uncompress(meta_raw)) if meta_raw else {}
    # offsets are relative to the tile-data section start
    return {tid: (tile_off + off, ln) for tid, (off, ln) in entries.items()}, metadata


def pmtiles_header_fields(data: bytes) -> dict[str, object]:
    """The PMTiles v3 header fields the verifier compares to ``index.json``."""
    if data[0:7] != b"PMTiles" or data[7] != 3:
        raise ValueError("not a PMTiles v3 archive")
    return {
        "minzoom": data[100],
        "maxzoom": data[101],
        "bounds": tuple(
            struct.unpack_from("<i", data, off)[0] / 1e7 for off in (102, 106, 110, 114)
        ),
    }


class TileSizeLimitExceeded(ValueError):
    """A stored tile exceeded :data:`TILE_SIZE_LIMIT_BYTES` — fail loudly."""


def check_tile_sizes(
    archive: bytes,
    *,
    limit: int = TILE_SIZE_LIMIT_BYTES,
    warn: int = TILE_SIZE_WARN_BYTES,
) -> tuple[int, list[str]]:
    """Fail loudly when any stored (compressed) tile exceeds ``limit``.

    Returns ``(max_tile_bytes, warnings)`` — warnings for tiles at/above the
    ``warn`` bound. Applied to the finished archive after both renderers so an
    oversized tile is a build error, never silently-thinned output (K1 §9.2.4).
    """
    entries, _meta = read_pmtiles_directory(archive)
    max_len = 0
    warnings: list[str] = []
    over: list[str] = []
    for tid, (_off, length) in entries.items():
        max_len = max(max_len, length)
        z, x, y = tileid_to_zxy(tid)
        if length > limit:
            over.append(f"z{z}/{x}/{y}={length}")
        elif length >= warn:
            warnings.append(f"z{z}/{x}/{y}={length} bytes (≥ {warn})")
    if over:
        raise TileSizeLimitExceeded(
            f"PMTiles tiles exceed the {limit}-byte contract: " + ", ".join(sorted(over)[:8])
        )
    return max_len, warnings


# --- metadata + archive assembly ------------------------------------------------


def _bounds_of(features: Sequence[Mapping[str, object]]) -> tuple[float, float, float, float]:
    lons: list[float] = []
    lats: list[float] = []
    for feat in features:
        geom = feat.get("geometry") or {}
        if not isinstance(geom, Mapping):
            continue
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if gtype == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
            lons.append(float(coords[0]))
            lats.append(float(coords[1]))
        elif gtype == "Polygon" and isinstance(coords, (list, tuple)):
            for ring in coords:
                if not isinstance(ring, (list, tuple)):
                    continue
                for pt in ring:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        lons.append(float(pt[0]))
                        lats.append(float(pt[1]))
    if not lons:
        return (-180.0, -85.0, 180.0, 85.0)
    return (min(lons), min(lats), max(lons), max(lats))


def layers_metadata(
    layers: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    license_id: str,
    attribution: str,
    minzoom: int = PMTILES_MINZOOM,
    maxzoom: int = PMTILES_MAXZOOM,
    name: str | None = None,
) -> dict[str, object]:
    """The PMTiles metadata block: a ``vector_layers`` descriptor per layer.

    Each layer's declared zoom band comes from its features' ``"tippecanoe"``
    members (the emitted range), not the archive bounds — a ``cells`` layer
    honestly reports z0–z9 while the archive spans z0–z14. The layer's licence
    + attribution are preserved here (ADR-048, §42) so any reader knows the
    ODbL obligations without opening a tile.
    """
    vector_layers: list[dict[str, object]] = []
    stat_layers: list[dict[str, object]] = []
    for lname in sorted(layers):
        feats = layers[lname]
        fields: dict[str, str] = {}
        lmin, lmax = maxzoom, minzoom
        geom_kinds: set[str] = set()
        for feat in feats:
            props = feat.get("properties")
            if isinstance(props, Mapping):
                for k, v in props.items():
                    fields[str(k)] = "Number" if isinstance(v, (int, float)) else "String"
            fmin, fmax = _feature_zoom_range(feat, minzoom, maxzoom)
            lmin, lmax = min(lmin, fmin), max(lmax, fmax)
            geom = feat.get("geometry")
            if isinstance(geom, Mapping):
                g = str(geom.get("type") or "")
                if g:
                    geom_kinds.add(g)
        if not feats:
            # an explicitly-declared empty layer still gets a descriptor over
            # the archive's full range (the empty-collection archive contract).
            lmin, lmax = minzoom, maxzoom
        vector_layers.append(
            {
                "id": lname,
                "description": f"{lname} ({license_id})",
                "fields": fields,
                "sig:license": license_id,
                "sig:attribution": attribution,
                "minzoom": lmin,
                "maxzoom": lmax,
            }
        )
        stat_layers.append(
            {
                "layer": lname,
                "count": len(feats),
                "geometry": geom_kinds.pop() if len(geom_kinds) == 1 else "Mixed",
            }
        )
    first_name = name or next(iter(sorted(layers)), "tiles")
    return {
        "name": first_name,
        "format": "pbf",
        "attribution": attribution,
        "sig:license": license_id,
        "sig:map-tiles-contract": TILE_CONTRACT,
        "minzoom": minzoom,
        "maxzoom": maxzoom,
        "vector_layers": vector_layers,
        "tilestats": {"layerCount": len(stat_layers), "layers": stat_layers},
    }


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
    """Single-layer convenience over :func:`layers_metadata` (back-compat)."""
    return layers_metadata(
        {layer_name: features},
        license_id=license_id,
        attribution=attribution,
        minzoom=minzoom,
        maxzoom=maxzoom,
        name=name or layer_name,
    )


def _group_by_layer(
    features: Sequence[Mapping[str, object]], default_layer: str
) -> dict[str, list[Mapping[str, object]]]:
    layers: dict[str, list[Mapping[str, object]]] = {}
    for feat in features:
        layers.setdefault(_feature_layer(feat, default_layer), []).append(feat)
    return layers


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

    Features' ``"tippecanoe"`` members assign layer + zoom band; features
    without one render into ``layer_name`` across ``minzoom..maxzoom``. The
    rendered archive passes through :func:`check_tile_sizes` — an over-limit
    tile fails here, loudly, before the bytes leave (K1 §9.2.4). The layer's
    licence + attribution + the ``sig.map-tiles/2`` contract tag live in the
    archive metadata.
    """
    raw = geojson.get("features")
    features: list[Mapping[str, object]] = list(raw) if isinstance(raw, (list, tuple)) else []
    layers = _group_by_layer(features, layer_name)
    # the default layer is always declared — even for an empty collection the
    # archive names its layer + licence for readers (empty-archive contract).
    layers.setdefault(layer_name, [])
    tiles = _render_pyramid(features, layer_name=layer_name, minzoom=minzoom, maxzoom=maxzoom)
    metadata = layers_metadata(
        layers,
        license_id=license_id,
        attribution=attribution,
        minzoom=minzoom,
        maxzoom=maxzoom,
        name=name,
    )
    bounds = _bounds_of(features)
    center = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
    archive = build_pmtiles(
        tiles,
        metadata=metadata,
        bounds=bounds,
        center=center,
        minzoom=minzoom,
        maxzoom=maxzoom,
    )
    check_tile_sizes(archive)
    return archive


def tippecanoe_available() -> bool:
    """Whether the ``tippecanoe`` renderer is on ``PATH`` (the production tile path)."""
    return shutil.which("tippecanoe") is not None


def tippecanoe_version() -> str | None:
    """The ``tippecanoe --version`` banner (``renderer_version`` in index.json)."""
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, tippecanoe is a trusted local tool
            ["tippecanoe", "--version"], capture_output=True, check=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return (proc.stdout or proc.stderr).strip().splitlines()[0].strip()


#: The pure-Python renderer's version stamp — bumped when the encoding contract
#: changes (v2 = the P35.52 two-layer/parity renderer).
PYTHON_RENDERER_VERSION = "sig.map-tiles/2+py.2"


#: Tippecanoe flag prefixes that must never reach a ``sig.map-tiles/2``
#: invocation — every drop/coalesce/cluster knob is a silent-retention hole
#: (F-414). ``--drop-rate``/``-r`` is not in this list: it is allowed only at
#: ``1`` and checked separately.
FORBIDDEN_TIPPECANOE_PREFIXES = (
    "--drop-densest",
    "--drop-fraction",
    "--drop-smallest",
    "--drop-lines",
    "--drop-polygons",
    "--coalesce",
    "--cluster",
    "--aggregate",
    "--maximum-tile-bytes",
    "--maximum-tile-features",
    "--base-zoom",
    "-B",
)
REQUIRED_TIPPECANOE_FLAGS = ("--no-tile-size-limit", "--no-feature-limit")


def assert_retention_argv(argv: Sequence[str]) -> None:
    """Refuse a tippecanoe argv that could thin a ``sig.map-tiles/2`` archive.

    Every drop/coalesce/cluster flag is forbidden; ``-r``/``--drop-rate`` must
    pin ``1``; the tool's own tile-size/feature limits are off (the contract
    checks the finished archive instead). A violation raises ``ValueError``
    before tippecanoe ever runs.
    """
    problems: list[str] = []
    rate_ok = False
    for i, tok in enumerate(argv):
        if not isinstance(tok, str):
            continue
        flag = tok.split("=", 1)[0]
        if (
            flag.startswith(("--drop-rate",))
            or flag == "-r"
            or (flag.startswith("-r") and len(flag) > 2 and flag[2].isdigit())
        ):
            if tok in ("-r1", "--drop-rate=1") or (
                tok in ("-r", "--drop-rate") and i + 1 < len(argv) and str(argv[i + 1]) == "1"
            ):
                rate_ok = True
            else:
                problems.append(f"drop rate pinned by {tok!r} (contract requires -r1)")
            continue
        for forbidden in FORBIDDEN_TIPPECANOE_PREFIXES:
            if flag == forbidden or flag.startswith(forbidden):
                problems.append(f"forbidden flag {tok!r}")
                break
    if not rate_ok:
        problems.append("missing -r1 (drop rate 1 — nothing may be dropped)")
    for required in REQUIRED_TIPPECANOE_FLAGS:
        if required not in argv:
            problems.append(f"missing {required} (the contract checks the archive itself)")
    if problems:
        raise ValueError(
            "tippecanoe argv violates the sig.map-tiles/2 retention contract: "
            + "; ".join(problems)
        )


def _tippecanoe_argv(
    geojson_path: str,
    out_path: str,
    *,
    layer_name: str | None,
    attribution: str,
) -> list[str]:
    """The pinned tippecanoe invocation (z0–z14, retention-contract flags).

    ``-r1`` keeps every feature at every zoom; ``--no-tile-size-limit`` +
    ``--no-feature-limit`` turn tippecanoe's own silent limits off — the
    finished archive is size-checked by :func:`check_tile_sizes` and the
    verifier instead. With ``layer_name=None`` each feature's
    ``"tippecanoe"."layer"`` member assigns its layer (the two-layer
    ``sig.map-tiles/2`` emit); a ``layer_name`` sets the default layer for
    member-less input.
    """
    argv = [
        "tippecanoe",
        "-o",
        out_path,
        "-Z",
        str(PMTILES_MINZOOM),
        "-z",
        str(PMTILES_MAXZOOM),
        "-r1",
        "--no-tile-size-limit",
        "--no-feature-limit",
        "--force",
    ]
    if layer_name is not None:
        argv += ["-l", layer_name]
    argv += [
        "--attribution",
        attribution,
        geojson_path,
    ]
    return argv


@dataclass(frozen=True)
class RenderedTiles:
    """One rendered compartment archive + the facts ``index.json`` records."""

    data: bytes
    renderer: str  # "tippecanoe" | "pure-python"
    renderer_version: str
    #: published located records that entered the emit (the ``counts.points``
    #: the verifier's conservation check reconciles Σ ``n`` against).
    points: int
    #: ``{"0-4": n_cells, "5-6": n_cells, "7-8": n_cells, "9": n_cells}``.
    cells_by_band: dict[str, int]
    bounds: tuple[float, float, float, float]
    #: the attribution line actually stamped into the archive metadata (the
    #: ODbL override and licence fallback resolved) — what ``index.json``
    #: records so the verifier's archive↔index comparison compares like
    #: with like.
    attribution: str = ""

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def tiles_index_entry(
    *,
    compartment: str,
    path: str,
    license_id: str,
    attribution: str | None,
    rendered: RenderedTiles,
    source: str,
) -> dict[str, object]:
    """One ``web/tiles/index.json`` archive entry (the ``sig.map-tiles/2`` index).

    The fields are exactly what ``sig-exports tiles verify`` reconciles
    against the archive bytes (K1 §9.2 check 5): licence, attribution, bounds
    and the zoom range must equal the archive metadata; ``sha256`` pins the
    bytes; ``source`` names the geojson the conservation check replays.
    """
    return {
        "compartment": compartment,
        "path": path,
        "sha256": rendered.sha256,
        "licence": license_id,
        # the archive's own stamped attribution (ODbL override / licence
        # fallback resolved) — verbatim so the verifier's archive↔index
        # metadata check compares like with like.
        "attribution": rendered.attribution or attribution or "",
        "bounds": [round(v, 7) for v in rendered.bounds],
        "minzoom": PMTILES_MINZOOM,
        "maxzoom": PMTILES_MAXZOOM,
        "counts": {
            "points": rendered.points,
            "cells_by_band": dict(sorted(rendered.cells_by_band.items())),
        },
        "renderer": rendered.renderer,
        "renderer_version": rendered.renderer_version,
        "contract": TILE_CONTRACT,
        "source": source,
    }


def render_compartment_sites_pmtiles(
    compartment: str,
    geojson_bytes: bytes,
    license_id: str,
    *,
    attribution: str | None = None,
) -> RenderedTiles:
    """Render one compartment's sites.geojson → a ``sig.map-tiles/2`` archive.

    Shared by the spine export (``build_spine_export``), the jurisdiction
    bundle path (``sig-exports build --jurisdiction``) and the fixtures:
    ODbL keeps its OSM notice (§42.3); every other compartment carries its own
    SPDX id — never a borrowed "CC-BY-4.0" label on a CC-BY-SA archive.
    P34.21a (E2-12): an explicit ``attribution`` (the drawn sources' own
    credit) is stamped verbatim; absent one, the licence-level SIG line stands
    as the fallback.

    The emit is :func:`map_tile_geojson` — the full sites.geojson row
    (claim_ids, source_ids, licence lists, envelopes) never reaches a tile;
    the archive carries the ``cells`` + ``sites`` contract properties only.
    The renderer writes through a temp file (tippecanoe when present, else the
    pure-Python encoder); both honour the same per-feature zoom members and
    the same fail-loud size check.
    """
    if attribution is None or license_id == "ODbL-1.0":
        attribution = (
            ODBL_ATTRIBUTION if license_id == "ODbL-1.0" else f"© The SIG project — {license_id}"
        )
    emit = map_tile_geojson(geojson_bytes, compartment)
    emit_doc = json.loads(emit)
    emit_features: list[Mapping[str, object]] = emit_doc.get("features") or []
    source_doc = json.loads(geojson_bytes)
    source_features = source_doc.get("features")
    located = sum(
        1
        for f in (source_features if isinstance(source_features, list) else [])
        if isinstance(f, Mapping)
        and isinstance(f.get("geometry"), Mapping)
        and f["geometry"].get("type") == "Point"
    )
    cells_by_band = {f"{b[0]}-{b[1]}": 0 for b in CELL_BANDS}
    for feat in emit_features:
        member = feat.get("tippecanoe")
        if isinstance(member, Mapping) and member.get("layer") == CELLS_LAYER:
            key = f"{member['minzoom']}-{member['maxzoom']}"
            cells_by_band[key] = cells_by_band.get(key, 0) + 1
    bounds = _bounds_of(emit_features)

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "features.geojson"
        src.write_bytes(emit)
        out = Path(tmp) / "sites.pmtiles"
        if tippecanoe_available():
            argv = _tippecanoe_argv(str(src), str(out), layer_name=None, attribution=attribution)
            assert_retention_argv(argv)
            subprocess.run(  # noqa: S603 - fixed argv, tippecanoe is a trusted local tool
                argv, check=True, capture_output=True
            )
            data = annotate_pmtiles(
                out.read_bytes(),
                license_id=license_id,
                attribution=attribution,
                name=f"{compartment}-sites",
            )
            check_tile_sizes(data)
            version = tippecanoe_version() or "tippecanoe (version unknown)"
            return RenderedTiles(
                data=data,
                renderer="tippecanoe",
                renderer_version=version,
                points=located,
                cells_by_band=cells_by_band,
                bounds=bounds,
                attribution=attribution,
            )
        data = render_pmtiles(
            emit_doc,
            layer_name=SITES_LAYER,
            license_id=license_id,
            attribution=attribution,
            name=f"{compartment}-sites",
        )
        return RenderedTiles(
            data=data,
            renderer="pure-python",
            renderer_version=PYTHON_RENDERER_VERSION,
            points=located,
            cells_by_band=cells_by_band,
            bounds=bounds,
            attribution=attribution,
        )


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
    :func:`annotate_pmtiles`), under the same retention + size contract —
    ``-r1``, no tool-side dropping, per-feature ``"tippecanoe"`` members honoured,
    and a fail-loud size check on the finished archive.
    """
    if tippecanoe_available():
        argv = _tippecanoe_argv(
            geojson_path, out_path, layer_name=layer_name, attribution=attribution
        )
        assert_retention_argv(argv)
        subprocess.run(  # noqa: S603 - fixed argv, tippecanoe is a trusted local tool
            argv,
            check=True,
            capture_output=True,
        )
        data = annotate_pmtiles(
            Path(out_path).read_bytes(),
            license_id=license_id,
            attribution=attribution,
            name=name,
        )
        check_tile_sizes(data)
        Path(out_path).write_bytes(data)
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
    "TILE_CONTRACT",
    "CELLS_LAYER",
    "SITES_LAYER",
    "CELL_ZOOM_MAX",
    "CELL_BANDS",
    "SITE_MINZOOM_BY_TIER",
    "TIER2_H3_RESOLUTION",
    "TILE_SIZE_LIMIT_BYTES",
    "TILE_SIZE_WARN_BYTES",
    "SITE_PROPERTY_KEYS",
    "CELL_PROPERTY_KEYS",
    "ALLOWED_SITE_KEYS",
    "ALLOWED_CELL_KEYS",
    "PYTHON_RENDERER_VERSION",
    "TileSizeLimitExceeded",
    "RenderedTiles",
    "zxy_to_tileid",
    "tileid_to_zxy",
    "encode_mvt_points",
    "build_pmtiles",
    "annotate_pmtiles",
    "read_pmtiles_directory",
    "pmtiles_header_fields",
    "check_tile_sizes",
    "layers_metadata",
    "layer_metadata",
    "tiles_index_entry",
    "map_tile_features",
    "map_tile_geojson",
    "assert_retention_argv",
    "render_pmtiles",
    "render_pmtiles_file",
    "render_compartment_sites_pmtiles",
    "tippecanoe_available",
    "tippecanoe_version",
]
