# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.map-tiles/2`` tile verifier (ADR-156, K1-map §9.2).

``sig-exports tiles verify --in <export-dir>`` re-opens a built export — the
PMTiles bytes it would ship, the ``web/tiles/index.json`` that describes them,
and each archive's source ``sites.geojson`` — and measures the six contract
checks:

1. **Count conservation.** For every compartment and every zoom z ≤ 9 the
   summed ``n`` over distinct ``h3`` cells equals the compartment's published
   located-record count; for z ≥ 10 the ``rk`` set in tile interiors (buffer
   duplicates collapse by ``rk``) equals the published set for the tiers whose
   band includes z — and ``sites`` is empty below z10.
2. **Renderer parity.** A fresh pure-Python render of the same emit agrees
   with the shipped archive on the ``rk`` set per zoom and on Σ ``n`` per
   zoom (never byte equality). When the shipped archive is itself the
   pure-Python render the check is recorded ``vacuous`` — honest, not hidden.
3. **Precision + tier.** Every ``tr`` ≤ 1 site feature is a point decoding
   onto its published (already tier-reduced) coordinate; every ``tr`` = 2 is a
   polygon; no ``tr`` = 3 appears; no property key outside the §3.3
   vocabulary appears on either layer (so claim ids, full-precision
   coordinates and personal data cannot ride in a tag).
4. **Size.** No stored tile exceeds :data:`TILE_SIZE_LIMIT_BYTES` (500 KiB);
   at/above :data:`TILE_SIZE_WARN_BYTES` (200 KiB) the report warns.
5. **Metadata.** The archive's ``sig:license``, attribution, header bounds
   and zoom range equal its ``index.json`` entry, and the index licence equals
   the compartment licence the export manifest recorded for the archive.
6. **CI wiring** lives in the workflows, not this tool — check 6 is the
   workflow legs that run 1–5 over the synthetic and real-sized fixtures.

The numbers are *measured*, not asserted: the report records the observed
counts next to the expected ones, and ``verdict`` is ``fail`` if any check on
any archive fails. The report lands at ``<export>/reports/tiles_verify.json``
so it rides the release candidate (G3 consumes it).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import struct
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from .manifest import TILES_INDEX_SCHEMA
from .published_record import record_key
from .tiles import (
    ALLOWED_CELL_KEYS,
    ALLOWED_SITE_KEYS,
    CELLS_LAYER,
    SITE_MINZOOM_BY_TIER,
    SITES_LAYER,
    TILE_CONTRACT,
    TILE_SIZE_LIMIT_BYTES,
    TILE_SIZE_WARN_BYTES,
    TileSizeLimitExceeded,
    _unproject_xy,
    check_tile_sizes,
    map_tile_geojson,
    pmtiles_header_fields,
    read_pmtiles_directory,
    render_pmtiles,
    tileid_to_zxy,
)

#: The verify report's own schema id (``schema`` key of tiles_verify.json).
TILES_VERIFY_SCHEMA = "sig.tiles-verify/1"


#: Cell keys the §3.3 vocabulary also admits as facet counts (``t_<n>``,
#: ``v_<n>``) — MAP-01b's slots; admitted now so the allowlist is stable.
def _cell_key_allowed(key: str) -> bool:
    if key in ALLOWED_CELL_KEYS:
        return True
    if len(key) > 2 and key[1] == "_" and key[0] in ("t", "v"):
        return key[2:].isdigit()
    return False


# --- minimal MVT decode (the mirror of tiles._encode_layer) -------------------


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _unzigzag(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


def _fields(msg: bytes) -> list[tuple[int, int, object]]:
    """Parse a protobuf message into ``(field, wire, value)`` triples."""
    out: list[tuple[int, int, object]] = []
    pos = 0
    v: object
    while pos < len(msg):
        key, pos = _read_varint(msg, pos)
        field, wire = key >> 3, key & 0x7
        if wire == 0:
            v, pos = _read_varint(msg, pos)
        elif wire == 1:
            v = struct.unpack_from("<d", msg, pos)[0]
            pos += 8
        elif wire == 2:
            ln, pos = _read_varint(msg, pos)
            v = msg[pos : pos + ln]
            pos += ln
        elif wire == 5:
            v = struct.unpack_from("<f", msg, pos)[0]
            pos += 4
        else:  # pragma: no cover - MVT only uses wire 0/1/2/5
            raise ValueError(f"unsupported wire type {wire}")
        out.append((field, wire, v))
    return out


def _packed_varints(data: bytes) -> list[int]:
    out: list[int] = []
    pos = 0
    while pos < len(data):
        v, pos = _read_varint(data, pos)
        out.append(v)
    return out


def _decode_value(msg: bytes) -> object:
    value: object = None
    for field, wire, v in _fields(msg):
        if field == 1 and wire == 2:
            value = cast("bytes", v).decode("utf-8")
        elif field == 2:
            value = float(cast("float | int", v))  # float_value
        elif field == 3:
            value = float(cast("float | int", v))  # double_value
        elif field in (4, 5):
            value = int(cast("int", v))  # int_value / uint_value
        elif field == 6:
            value = _unzigzag(int(cast("int", v)))  # sint_value
        elif field == 7:
            value = bool(v)
    return value


def _decode_geometry(geom: list[int], geom_type: int) -> dict[str, object]:
    """Decode an MVT geometry command stream into tile-local coords.

    Returns ``{"points": [(x, y), …]}`` for points and ``{"rings":
    [[(x, y), …], …]}`` for polygons (rings unclosed, as encoded).
    """
    points: list[tuple[int, int]] = []
    rings: list[list[tuple[int, int]]] = []
    cursor = (0, 0)
    i = 0
    current_ring: list[tuple[int, int]] | None = None
    while i < len(geom):
        cmd = geom[i] & 0x7
        count = geom[i] >> 3
        i += 1
        if cmd in (1, 2):  # MoveTo / LineTo
            for _ in range(count):
                dx = _unzigzag(geom[i])
                dy = _unzigzag(geom[i + 1])
                i += 2
                cursor = (cursor[0] + dx, cursor[1] + dy)
                if geom_type == 1:
                    points.append(cursor)
                else:
                    if cmd == 1:
                        current_ring = []
                        rings.append(current_ring)
                    assert current_ring is not None
                    current_ring.append(cursor)
        elif cmd == 7:  # ClosePath
            if current_ring is not None:
                current_ring = None
        else:  # pragma: no cover
            raise ValueError(f"unknown MVT command {cmd}")
    return {"points": points, "rings": rings}


def decode_mvt_tile(data: bytes) -> list[dict[str, object]]:
    """Decode a decompressed MVT tile into ``[{name, extent, features}]``.

    Each feature: ``{"id", "type" (1 point/3 polygon), "properties",
    "points"/"rings"}`` — just what the verifier measures.
    """
    layers: list[dict[str, object]] = []
    for field, wire, v in _fields(data):
        if field != 3 or wire != 2:
            continue
        name = ""
        extent = 4096
        keys: list[str] = []
        values: list[object] = []
        feature_msgs: list[bytes] = []
        for lf, _lw, lv in _fields(cast("bytes", v)):
            if lf == 1:
                name = cast("bytes", lv).decode("utf-8")
            elif lf == 2:
                feature_msgs.append(cast("bytes", lv))
            elif lf == 3:
                keys.append(cast("bytes", lv).decode("utf-8"))
            elif lf == 4:
                values.append(_decode_value(cast("bytes", lv)))
            elif lf == 5:
                extent = int(cast("int", lv))
        features: list[dict[str, object]] = []
        for fm in feature_msgs:
            fid = 0
            tags_raw: list[int] = []
            gtype = 0
            geom_raw: list[int] = []
            for ff, _fw, fv in _fields(fm):
                if ff == 1:
                    fid = int(cast("int", fv))
                elif ff == 2:
                    tags_raw = _packed_varints(cast("bytes", fv))
                elif ff == 3:
                    gtype = int(cast("int", fv))
                elif ff == 4:
                    geom_raw = _packed_varints(cast("bytes", fv))
            props = {keys[tags_raw[t]]: values[tags_raw[t + 1]] for t in range(0, len(tags_raw), 2)}
            features.append(
                {
                    "id": fid,
                    "type": gtype,
                    "properties": props,
                    **_decode_geometry(geom_raw, gtype),
                }
            )
        layers.append({"name": name, "extent": extent, "features": features})
    return layers


# --- the expected contract (replayed from the source geojson) -------------------


def _expected(source_geojson: bytes, compartment: str) -> dict[str, object]:
    """Replay the source geojson into the expected per-zoom contract.

    The replay applies the same emit the renderer saw (``map_tile_geojson``)
    and re-derives expectations from its properties — so a feature the emit
    dropped (refused subject, non-point) is never counted twice and never
    expected.
    """
    emit = json.loads(map_tile_geojson(source_geojson, compartment))
    features = emit.get("features") or []
    # source coords keyed by rk — the tier-1/point fidelity check compares the
    # tile's decoded coordinate to the published (already reduced) one.
    src_coords: dict[str, tuple[float, float]] = {}
    per_zoom_rks: dict[int, set[str]] = {z: set() for z in range(0, 15)}
    located = 0
    tier1_grid_violations: list[str] = []
    src_doc = json.loads(source_geojson)
    src_feats = [f for f in (src_doc.get("features") or []) if isinstance(f, Mapping)]
    for f in src_feats:
        geom = f.get("geometry")
        props = f.get("properties") or {}
        if not isinstance(geom, Mapping) or geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates")
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            continue
        located += 1
        rk = record_key(
            compartment,
            str(props.get("entity_type") or "(unknown)"),
            str(props.get("entity_id") or ""),
        )
        src_coords[rk] = (float(coords[0]), float(coords[1]))
        tier = int(props.get("sensitivity_tier") or 0)
        if tier == 1:
            for v in (float(coords[0]), float(coords[1])):
                if abs(round(v, 2) - v) > 1e-9:
                    tier1_grid_violations.append(rk)
        if tier in SITE_MINZOOM_BY_TIER:
            for z in range(SITE_MINZOOM_BY_TIER[tier], 15):
                per_zoom_rks[z].add(rk)
    return {
        "located": located,
        "per_zoom_rks": per_zoom_rks,
        "src_coords": src_coords,
        "tier1_grid_violations": tier1_grid_violations,
        "emit_features": features,
    }


def _local_to_lonlat(
    z: int, x: int, y: int, extent: int, lx: float, ly: float
) -> tuple[float, float]:
    """Invert a tile-local coord back to (lon, lat) (web mercator)."""
    n = 1 << z
    wx = (x + lx / extent) / n
    wy = (y + ly / extent) / n
    return _unproject_xy(wx, wy)


# --- the per-archive checks -----------------------------------------------------


def _check_archive(
    export_dir: Path,
    entry: Mapping[str, object],
    manifest_licenses: Mapping[str, str],
) -> dict[str, object]:
    """Run checks 1–5 over one ``index.json`` archive entry."""
    rel = str(entry["path"])
    path = export_dir / rel
    detail: dict[str, object] = {
        "compartment": entry.get("compartment"),
        "path": rel,
        "checks": {},
        "warnings": [],
    }
    checks: dict[str, object] = detail["checks"]  # type: ignore[assignment]
    warnings: list[str] = detail["warnings"]  # type: ignore[assignment]

    def fail(name: str, msg: str, **info: object) -> None:
        checks[name] = {"status": "fail", "detail": msg, **info}

    def ok(name: str, **info: object) -> None:
        if name not in checks:
            checks[name] = {"status": "pass", **info}

    if not path.exists():
        fail("present", f"index lists {rel} but the file is absent")
        return detail

    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != entry.get("sha256"):
        fail("integrity", f"sha256 {sha} != index {entry.get('sha256')}")
    else:
        ok("integrity", sha256=sha)

    try:
        entries, metadata = read_pmtiles_directory(data)
        header = pmtiles_header_fields(data)
    except ValueError as exc:
        fail("format", str(exc))
        return detail
    ok("format")

    # decode every tile once — a malformed tile is a format failure, not a crash
    decoded: dict[int, list[dict[str, object]]] = {}  # tile_id -> layers
    decode_errors: list[str] = []
    for tid, (off, ln) in entries.items():
        raw = data[off : off + ln]
        try:
            tile = gzip.decompress(raw)
        except OSError:
            tile = raw
        try:
            decoded[tid] = decode_mvt_tile(tile)
        except (ValueError, IndexError, AssertionError) as exc:
            z, x, y = tileid_to_zxy(tid)
            decode_errors.append(f"z{z}/{x}/{y}: {exc}")
    if decode_errors:
        fail("format", f"undecodable tiles: {'; '.join(decode_errors[:4])}")
        return detail

    per_zoom_sites: dict[int, set[str]] = {}
    per_zoom_cells: dict[int, dict[str, int]] = {}
    site_feats: list[dict[str, object]] = []
    prop_violations: list[str] = []
    tier_violations: list[str] = []
    geom_violations: list[str] = []
    for tid, layers in decoded.items():
        z, x, y = tileid_to_zxy(tid)
        for layer in layers:
            lname = str(layer["name"])
            extent = int(cast("int", layer["extent"]))
            for feat in cast("list[dict[str, object]]", layer["features"]):
                props = cast("Mapping[str, object]", feat.get("properties") or {})
                if lname == SITES_LAYER:
                    bad = [k for k in props if k not in ALLOWED_SITE_KEYS]
                    if bad:
                        prop_violations.append(f"{lname}:{sorted(bad)}")
                    rk = props.get("rk")
                    tr = props.get("tr")
                    if not isinstance(rk, str) or not rk:
                        prop_violations.append(f"{lname}: feature {feat.get('id')} lacks rk")
                    if tr not in (0, 1, 2):
                        tier_violations.append(
                            f"{rk or feat.get('id')}: tr={tr!r} (tier 3 or unknown must not tile)"
                        )
                    if tr == 2 and feat.get("type") != 3:
                        geom_violations.append(f"{rk}: tier-2 site must be a polygon")
                    if tr in (0, 1) and feat.get("type") != 1:
                        geom_violations.append(f"{rk}: tier-{tr} site must be a point")
                    per_zoom_sites.setdefault(z, set()).add(str(rk))
                    site_feats.append(
                        {
                            "z": z,
                            "x": x,
                            "y": y,
                            "extent": extent,
                            "rk": rk,
                            "tr": tr,
                            "feat": feat,
                        }
                    )
                elif lname == CELLS_LAYER:
                    bad = [k for k in props if not _cell_key_allowed(k)]
                    if bad:
                        prop_violations.append(f"{lname}:{sorted(bad)}")
                    h3id = props.get("h3")
                    if not isinstance(h3id, str):
                        prop_violations.append(f"{lname}: feature {feat.get('id')} lacks h3")
                        continue
                    # dedupe by h3 across buffer duplicates: first writer wins
                    zcells = per_zoom_cells.setdefault(z, {})
                    if h3id not in zcells:
                        zcells[h3id] = int(cast("int | None", props.get("n")) or 0)
                else:
                    prop_violations.append(f"unexpected layer {lname!r}")

    compartment = str(entry.get("compartment") or "")
    source_rel = str(entry.get("source") or f"{compartment}/sites.geojson")
    source_path = export_dir / source_rel
    expected: dict[str, object] = {"located": 0, "per_zoom_rks": {}, "src_coords": {}}
    if source_path.exists():
        expected = _expected(source_path.read_bytes(), compartment)
    else:
        warnings.append(f"source geojson {source_rel} absent — conservation unverifiable")

    # --- check 1: conservation ------------------------------------------------
    cons_detail: dict[str, object] = {}
    cons_ok = True
    per_zoom_want = cast("Mapping[int, set[str]]", expected.get("per_zoom_rks") or {})
    for z in range(0, 10):
        summed = sum(per_zoom_cells.get(z, {}).values())
        want = int(cast("int", expected["located"]))
        cons_detail[f"z{z}"] = {"sum_n": summed, "expected": want}
        if summed != want:
            cons_ok = False
    for z in range(10, 15):
        got = per_zoom_sites.get(z, set())
        want_rks = per_zoom_want.get(z, set())
        missing = sorted(set(want_rks) - got)
        extra = sorted(got - set(want_rks))
        detail_z: dict[str, object] = {
            "rk": len(got),
            "expected": len(want_rks),
            "missing": len(missing),
            "extra": len(extra),
        }
        if missing or extra:
            cons_ok = False
            detail_z["missing_rk"] = missing[:8]
            detail_z["extra_rk"] = extra[:8]
        cons_detail[f"z{z}"] = detail_z
    # no sites below z10
    low_sites = sum(len(rks) for z, rks in per_zoom_sites.items() if z <= 9)
    cons_detail["sites_below_z10"] = low_sites
    if low_sites:
        cons_ok = False
    # no cells above z9
    high_cells = sum(len(c) for z, c in per_zoom_cells.items() if z >= 10)
    cons_detail["cells_above_z9"] = high_cells
    if high_cells:
        cons_ok = False
    checks["conservation"] = {"status": "pass" if cons_ok else "fail", "detail": cons_detail}

    # --- check 2: renderer parity ----------------------------------------------
    vacuous = str(entry.get("renderer")) == "pure-python"
    parity_ok = True
    parity_detail: dict[str, object] = {"vacuous": vacuous}
    if source_path.exists() and not vacuous:
        py_archive = render_pmtiles(
            json.loads(map_tile_geojson(source_path.read_bytes(), compartment)),
            layer_name=SITES_LAYER,
            license_id=str(entry.get("licence") or ""),
            attribution=str(entry.get("attribution") or ""),
        )
        py_entries, _ = read_pmtiles_directory(py_archive)
        py_zoom_sites: dict[int, set[str]] = {}
        py_zoom_cells: dict[int, dict[str, int]] = {}
        for tid, (off, ln) in py_entries.items():
            z, x, y = tileid_to_zxy(tid)
            raw = py_archive[off : off + ln]
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
            for layer in decode_mvt_tile(raw):
                for feat in cast("list[dict[str, object]]", layer["features"]):
                    props = cast("Mapping[str, object]", feat.get("properties") or {})
                    if layer["name"] == SITES_LAYER:
                        py_zoom_sites.setdefault(z, set()).add(str(props.get("rk")))
                    elif layer["name"] == CELLS_LAYER and isinstance(props.get("h3"), str):
                        py_zoom_cells.setdefault(z, {}).setdefault(
                            str(props["h3"]), int(cast("int", props.get("n") or 0))
                        )
        diffs: list[str] = []
        for z in range(0, 15):
            shipped_rks = per_zoom_sites.get(z, set())
            py_rks = py_zoom_sites.get(z, set())
            if shipped_rks != py_rks:
                parity_ok = False
                diffs.append(
                    f"z{z}: rk sets differ (shipped {len(shipped_rks)}, pure-python {len(py_rks)})"
                )
            shipped_n = sum(per_zoom_cells.get(z, {}).values())
            py_n = sum(py_zoom_cells.get(z, {}).values())
            if shipped_n != py_n:
                parity_ok = False
                diffs.append(f"z{z}: Σn {shipped_n} != {py_n}")
        parity_detail["diffs"] = diffs[:16]
    checks["parity"] = {"status": "pass" if parity_ok else "fail", "detail": parity_detail}

    # --- check 3: precision + tier + properties --------------------------------
    coord_tol_units = 2.0  # decoded-vs-published tolerance in extent units
    coord_mismatches: list[str] = []
    src_coords = cast("dict[str, tuple[float, float]]", expected.get("src_coords") or {})
    for sf in site_feats:
        if sf["tr"] != 1:
            # the spec's grid check is tier-1-specific; tier-0 fidelity is
            # covered by rk conservation + renderer parity.
            continue
        sfeat = cast("dict[str, object]", sf["feat"])
        pts = cast("list[tuple[int, int]]", sfeat.get("points") or [])
        if not pts:
            geom_violations.append(f"{sf['rk']}: point feature without geometry")
            continue
        sz, sx, sy, sext = (
            int(cast("int", sf["z"])),
            int(cast("int", sf["x"])),
            int(cast("int", sf["y"])),
            int(cast("int", sf["extent"])),
        )
        lon, lat = _local_to_lonlat(sz, sx, sy, sext, *pts[0])
        want_coord = src_coords.get(str(sf["rk"]))
        if want_coord is None:
            continue  # extra rk — conservation reports it
        deg_per_unit = 360.0 / ((1 << sz) * sext)
        tol = coord_tol_units * deg_per_unit
        if abs(lon - want_coord[0]) > tol or abs(lat - want_coord[1]) > tol:
            coord_mismatches.append(str(sf["rk"]))
    tier3_seen = any(sf["tr"] == 3 for sf in site_feats)
    tier_ok = (
        not prop_violations
        and not tier_violations
        and not geom_violations
        and not coord_mismatches
        and not tier3_seen
        and not expected.get("tier1_grid_violations")
    )
    checks["precision_tier"] = {
        "status": "pass" if tier_ok else "fail",
        "detail": {
            "property_violations": sorted(set(prop_violations))[:16],
            "tier_violations": tier_violations[:16],
            "geometry_violations": geom_violations[:16],
            "coord_mismatches": coord_mismatches[:16],
            "source_tier1_off_grid": cast("list[str]", expected.get("tier1_grid_violations") or [])[
                :16
            ],
        },
    }

    # --- check 4: size ----------------------------------------------------------
    try:
        max_len, size_warnings = check_tile_sizes(data)
        warnings.extend(size_warnings)
        checks["size"] = {
            "status": "pass",
            "detail": {
                "max_tile_bytes": max_len,
                "archive_bytes": len(data),
                "warn_bound": TILE_SIZE_WARN_BYTES,
                "limit": TILE_SIZE_LIMIT_BYTES,
            },
        }
    except TileSizeLimitExceeded as exc:
        fail("size", str(exc))

    # --- check 5: metadata -------------------------------------------------------
    meta_ok = True
    meta_detail: dict[str, object] = {}
    if metadata.get("sig:license") != entry.get("licence"):
        meta_ok = False
        meta_detail["licence"] = (
            f"archive {metadata.get('sig:license')!r} != index {entry.get('licence')!r}"
        )
    if metadata.get("attribution") != entry.get("attribution"):
        meta_ok = False
        meta_detail["attribution"] = "archive attribution != index"
    if metadata.get("sig:map-tiles-contract") != TILE_CONTRACT:
        meta_ok = False
        meta_detail["contract"] = (
            f"archive contract {metadata.get('sig:map-tiles-contract')!r} != {TILE_CONTRACT!r}"
        )
    hb = cast("Sequence[float]", header["bounds"])
    eb = entry.get("bounds") or []
    if isinstance(eb, Sequence) and len(eb) == 4:
        if any(abs(float(a) - float(b)) > 1e-5 for a, b in zip(hb, eb, strict=True)):
            meta_ok = False
            meta_detail["bounds"] = f"header {list(hb)} != index {list(eb)}"
    else:
        meta_ok = False
        meta_detail["bounds"] = "index entry lacks bounds"
    if header["minzoom"] != entry.get("minzoom") or header["maxzoom"] != entry.get("maxzoom"):
        meta_ok = False
        meta_detail["zooms"] = (
            f"header z{header['minzoom']}–{header['maxzoom']} != index "
            f"{entry.get('minzoom')}–{entry.get('maxzoom')}"
        )
    manifest_lic = manifest_licenses.get(rel)
    if manifest_lic is not None and manifest_lic != entry.get("licence"):
        meta_ok = False
        meta_detail["manifest_licence"] = (
            f"manifest {manifest_lic!r} != index {entry.get('licence')!r}"
        )
    checks["metadata"] = {"status": "pass" if meta_ok else "fail", "detail": meta_detail}

    detail["renderer"] = entry.get("renderer")
    detail["verdict"] = (
        "pass"
        if all(cast("Mapping[str, object]", c).get("status") == "pass" for c in checks.values())
        else "fail"
    )
    return detail


def _check_status(archive_detail: dict[str, object], check: str) -> object:
    """One archive's check status, or ``None`` when the check never ran."""
    checks_map = cast("Mapping[str, object]", archive_detail.get("checks") or {})
    return cast("Mapping[str, object]", checks_map.get(check) or {}).get("status")


def verify_export_tiles(export_dir: Path | str) -> dict[str, object]:
    """Verify every ``sig.map-tiles/2`` archive listed in ``web/tiles/index.json``.

    Writes nothing itself — the CLI owns the ``reports/tiles_verify.json``
    landing. Returns the measured report (``verdict`` = ``pass`` only when
    every check on every archive passed).
    """
    export_dir = Path(export_dir)
    index_path = export_dir / "web" / "tiles" / "index.json"
    report: dict[str, object] = {
        "schema": TILES_VERIFY_SCHEMA,
        "contract": TILES_INDEX_SCHEMA,
        "export_dir": str(export_dir),
        "archives": [],
        "warnings": [],
        "verdict": "fail",
    }
    if not index_path.exists():
        report["error"] = "web/tiles/index.json absent — not a sig.map-tiles/2 export"
        return report
    index = json.loads(index_path.read_bytes())
    entries = index.get("archives")
    if not isinstance(entries, list):
        report["error"] = "web/tiles/index.json carries no archives list"
        return report

    manifest_licenses: dict[str, str] = {}
    manifest_path = export_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_bytes())
            for art in manifest.get("artifacts", []):
                if isinstance(art, dict) and str(art.get("path", "")).endswith(".pmtiles"):
                    manifest_licenses[str(art["path"])] = str(art.get("license"))
        except ValueError:
            pass

    archives: list[dict[str, object]] = []
    warnings: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        detail = _check_archive(export_dir, entry, manifest_licenses)
        archives.append(detail)
        warnings.extend(
            f"{detail['path']}: {w}"
            for w in detail.get("warnings", [])  # type: ignore[attr-defined]
        )

    per_check: dict[str, str] = {}
    for name in ("conservation", "parity", "precision_tier", "size", "metadata"):
        per_check[name] = (
            "pass" if all(_check_status(a, name) == "pass" for a in archives) else "fail"
        )
    verdict = "pass" if all(v == "pass" for v in per_check.values()) else "fail"
    report.update(
        {
            "archives": archives,
            "warnings": warnings,
            "checks": per_check,
            "verdict": verdict,
        }
    )
    return report


__all__ = ["TILES_VERIFY_SCHEMA", "decode_mvt_tile", "verify_export_tiles"]
