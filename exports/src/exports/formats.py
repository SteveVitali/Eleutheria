# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The deterministic bulk-format writer registry (§38.1, SIG-EXPORT-001).

SIG publishes each bulk table in the seven formats §38.1 names — Parquet, CSV, JSONL,
GeoJSON, PMTiles, JSON-LD/RDF, and a SQLite/Datasette bundle. Every writer here is a
**pure function** ``list[row] -> bytes``: given the same rows it returns the same bytes,
which is what makes a release reproducible (SIG-EXPORT-003) and its checksum meaningful
(SIG-EXPORT-001). The text formats are byte-stable by construction (sorted keys, fixed
separators). The binary formats (Parquet via DuckDB, SQLite via ``Connection.serialize``,
PMTiles via a hand-built v3 archive) carry no wall-clock state — gzip mtimes are pinned
to 0 — so they are byte-identical for a **fixed toolchain version**; DuckDB stamps its
version into Parquet metadata, so a DuckDB upgrade is a new build (which is why the
reproducibility contract is keyed on the toolchain, not asserted across versions).

Every row reaching a writer already carries its per-row rights provenance under
:data:`exports.compartments.RIGHTS_KEY` (SIG-EXPORT-006); the tabular writers flatten it
into ``rights_*`` columns, the document writers keep it nested.

**Scope note (PMTiles).** The PMTiles writer emits a *valid, parseable* v3 archive
carrying the layer's GeoJSON as archive metadata; rendering vector tiles from geometry
(a tippecanoe-class build step) is a Produced-Work concern of the map surface (Phase 15,
§42.3a SIG-LIC-008), so the tileset is metadata-only here. See ADR-048.
"""

from __future__ import annotations

import csv
import gzip
import io
import sqlite3
import struct
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .compartments import RIGHTS_KEY
from .manifest import canonical_json

Row = Mapping[str, Any]


# --- scalarisation ------------------------------------------------------------


def _scalarize(value: Any) -> Any:
    """Coerce a value to a tabular scalar; nested structures become canonical JSON text."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return canonical_json(value).decode("utf-8").rstrip("\n")


def _flatten(row: Row) -> dict[str, Any]:
    """Split a row into flat scalar columns, expanding the rights block to ``rights_*``."""
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key == RIGHTS_KEY:
            continue
        out[key] = _scalarize(value)
    rights = row.get(RIGHTS_KEY)
    if isinstance(rights, Mapping):
        for key, value in rights.items():
            out[f"rights_{key}"] = _scalarize(value)
    return out


def _columns(flat_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """The sorted union of all column names — a stable, order-independent schema."""
    cols: set[str] = set()
    for row in flat_rows:
        cols.update(row)
    return sorted(cols)


# --- text formats -------------------------------------------------------------


def write_jsonl(rows: Sequence[Row], **_: Any) -> bytes:
    """One canonical-JSON object per line (nested rights preserved)."""
    return b"".join(canonical_json(dict(row)) for row in rows)


def write_csv(rows: Sequence[Row], **_: Any) -> bytes:
    """RFC-4180 CSV with a sorted header and ``rights_*`` provenance columns."""
    flat = [_flatten(row) for row in rows]
    cols = _columns(flat)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", restval="")
    writer.writeheader()
    for row in flat:
        writer.writerow({c: "" if row.get(c) is None else row[c] for c in cols})
    return buf.getvalue().encode("utf-8")


def write_jsonld(rows: Sequence[Row], *, table_name: str = "export", **_: Any) -> bytes:
    """A JSON-LD document: a ``@graph`` of one node per row under the SIG namespace.

    Hand-built (not serialised by a library) so the byte output is stable and diffable.
    """
    context = {"sig": "https://sig-project.org/ns/", "@vocab": "https://sig-project.org/ns/"}
    graph = []
    for i, row in enumerate(rows):
        node: dict[str, Any] = {"@id": f"sig:{table_name}/{i}"}
        node.update({k: v for k, v in row.items() if k != RIGHTS_KEY})
        if RIGHTS_KEY in row:
            node["rights"] = row[RIGHTS_KEY]
        graph.append(node)
    return canonical_json({"@context": context, "@graph": graph})


def write_geojson(rows: Sequence[Row], *, geometry_key: str = "geometry", **_: Any) -> bytes:
    """A GeoJSON ``FeatureCollection``; the geometry column becomes each feature's geometry."""
    features = []
    for row in rows:
        geometry = row.get(geometry_key)
        props = {k: v for k, v in row.items() if k != geometry_key and k != RIGHTS_KEY}
        if RIGHTS_KEY in row:
            props["rights"] = row[RIGHTS_KEY]
        features.append({"type": "Feature", "geometry": geometry, "properties": props})
    return canonical_json({"type": "FeatureCollection", "features": features})


# --- SQLite / Datasette -------------------------------------------------------


def _sqlite_coltype(values: list[Any]) -> str:
    non_null = [v for v in values if v is not None]
    if non_null and all(isinstance(v, bool) for v in non_null):
        return "INTEGER"
    if non_null and all(isinstance(v, int) and not isinstance(v, bool) for v in non_null):
        return "INTEGER"
    if non_null and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_null):
        return "REAL"
    return "TEXT"


def write_sqlite(rows: Sequence[Row], *, table_name: str = "export", **_: Any) -> bytes:
    """A single-table SQLite/Datasette bundle; bytes come from ``Connection.serialize``.

    Deterministic: identical rows produce identical database bytes (the file carries no
    timestamps), so the artifact's checksum is reproducible (SIG-EXPORT-001/003).
    """
    flat = [_flatten(row) for row in rows]
    cols = _columns(flat)
    conn = sqlite3.connect(":memory:")
    try:
        if cols:
            coldefs = ", ".join(f'"{c}" {_sqlite_coltype([r.get(c) for r in flat])}' for c in cols)
            conn.execute(f'CREATE TABLE "{table_name}" ({coldefs})')
            placeholders = ", ".join("?" for _ in cols)
            conn.executemany(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                [tuple(_sqlite_value(r.get(c)) for c in cols) for r in flat],
            )
        else:
            conn.execute(f'CREATE TABLE "{table_name}" ("_empty" TEXT)')
        conn.commit()
        return bytes(conn.serialize())
    finally:
        conn.close()


def _sqlite_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    return value


# --- Parquet (via DuckDB) -----------------------------------------------------


def _duck_coltype(values: list[Any]) -> str:
    non_null = [v for v in values if v is not None]
    if non_null and all(isinstance(v, bool) for v in non_null):
        return "BOOLEAN"
    if non_null and all(isinstance(v, int) and not isinstance(v, bool) for v in non_null):
        return "BIGINT"
    if non_null and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_null):
        return "DOUBLE"
    return "VARCHAR"


def write_parquet(rows: Sequence[Row], *, table_name: str = "export", **_: Any) -> bytes:
    """A Parquet artifact written by DuckDB (SIG-EXPORT-001).

    Columns are typed by deterministic inference; the file carries no wall-clock state,
    so two builds of the same rows on the same DuckDB version are byte-identical (DuckDB
    stamps its version into the Parquet ``created_by`` metadata).
    """
    import duckdb

    flat = [_flatten(row) for row in rows]
    cols = _columns(flat)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "part.parquet"
        conn = duckdb.connect(":memory:")
        try:
            if cols:
                coldefs = ", ".join(
                    f'"{c}" {_duck_coltype([r.get(c) for r in flat])}' for c in cols
                )
                conn.execute(f'CREATE TABLE "{table_name}" ({coldefs})')
                placeholders = ", ".join("?" for _ in cols)
                conn.executemany(
                    f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                    [tuple(r.get(c) for c in cols) for r in flat],
                )
            else:
                conn.execute(f'CREATE TABLE "{table_name}" ("_empty" VARCHAR)')
            conn.execute(f"COPY \"{table_name}\" TO '{out}' (FORMAT PARQUET)")
        finally:
            conn.close()
        return out.read_bytes()


# --- PMTiles v3 (metadata-only, valid archive) --------------------------------


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


def _gzip0(data: bytes) -> bytes:
    """Gzip with a pinned mtime (0) so the output is byte-stable across runs."""
    return gzip.compress(data, mtime=0)


def _empty_directory() -> bytes:
    # A PMTiles directory is a varint entry-count followed by the entries; an empty
    # tileset has zero entries. Internally gzip-compressed (header field = 2).
    return _gzip0(_varint(0))


def write_pmtiles(
    rows: Sequence[Row], *, geometry_key: str = "geometry", table_name: str = "export", **_: Any
) -> bytes:
    """A valid, parseable PMTiles v3 archive carrying the layer as archive metadata.

    The tileset is metadata-only (zero rendered tiles): the archive is a real,
    spec-conformant v3 file — magic ``PMTiles``, version 3, 127-byte header, gzip'd root
    and leaf directories, gzip'd JSON metadata — so downstream tooling can open it and
    read the layer descriptor. Rendering vector tiles from the geometry is deferred to
    the map surface (Phase 15); see the module docstring and ADR-048.
    """
    feature_collection = write_geojson(rows, geometry_key=geometry_key)
    metadata = _gzip0(
        canonical_json(
            {
                "name": table_name,
                "format": "geojson",
                "vector_layers": [],
                "tilestats": {"layerCount": 0},
                "geojson": feature_collection.decode("utf-8"),
            }
        )
    )
    root_dir = _empty_directory()
    leaf_dir = b""  # no leaf directories in a zero-tile archive
    tile_data = b""

    header_len = 127
    root_off = header_len
    meta_off = root_off + len(root_dir)
    leaf_off = meta_off + len(metadata)
    tile_off = leaf_off + len(leaf_dir)

    header = bytearray(header_len)
    header[0:7] = b"PMTiles"
    header[7] = 3
    struct.pack_into("<Q", header, 8, root_off)
    struct.pack_into("<Q", header, 16, len(root_dir))
    struct.pack_into("<Q", header, 24, meta_off)
    struct.pack_into("<Q", header, 32, len(metadata))
    struct.pack_into("<Q", header, 40, leaf_off)
    struct.pack_into("<Q", header, 48, len(leaf_dir))
    struct.pack_into("<Q", header, 56, tile_off)
    struct.pack_into("<Q", header, 64, len(tile_data))
    struct.pack_into("<Q", header, 72, 0)  # num addressed tiles
    struct.pack_into("<Q", header, 80, 0)  # num tile entries
    struct.pack_into("<Q", header, 88, 0)  # num tile contents
    header[96] = 1  # clustered
    header[97] = 2  # internal compression: gzip
    header[98] = 1  # tile compression: none
    header[99] = 1  # tile type: mvt
    header[100] = 0  # min zoom
    header[101] = 0  # max zoom
    # bounds + center left at 0 (int32 E7) for a metadata-only archive.
    return bytes(header) + root_dir + metadata + leaf_dir + tile_data


# --- registry -----------------------------------------------------------------


@dataclass(frozen=True)
class FormatSpec:
    """One publishable format: its writer, IANA media type, and file extension."""

    name: str
    media_type: str
    extension: str
    writer: Callable[..., bytes]
    geo_only: bool = False


FORMATS: dict[str, FormatSpec] = {
    "parquet": FormatSpec("parquet", "application/vnd.apache.parquet", "parquet", write_parquet),
    "csv": FormatSpec("csv", "text/csv", "csv", write_csv),
    "jsonl": FormatSpec("jsonl", "application/x-ndjson", "jsonl", write_jsonl),
    "jsonld": FormatSpec("jsonld", "application/ld+json", "jsonld", write_jsonld),
    "sqlite": FormatSpec("sqlite", "application/vnd.sqlite3", "sqlite", write_sqlite),
    "geojson": FormatSpec(
        "geojson", "application/geo+json", "geojson", write_geojson, geo_only=True
    ),
    "pmtiles": FormatSpec(
        "pmtiles", "application/vnd.pmtiles", "pmtiles", write_pmtiles, geo_only=True
    ),
}

#: The formats every tabular table is published in (§38.1).
TABULAR_FORMATS: tuple[str, ...] = ("parquet", "csv", "jsonl", "jsonld", "sqlite")
#: The additional geometry formats a ``geo`` table also gets.
GEO_FORMATS: tuple[str, ...] = ("geojson", "pmtiles")


def formats_for(kind: str) -> tuple[str, ...]:
    """The format names a table of ``kind`` is published in."""
    if kind == "geo":
        return TABULAR_FORMATS + GEO_FORMATS
    return TABULAR_FORMATS


__all__ = [
    "FormatSpec",
    "FORMATS",
    "TABULAR_FORMATS",
    "GEO_FORMATS",
    "formats_for",
    "write_parquet",
    "write_csv",
    "write_jsonl",
    "write_jsonld",
    "write_geojson",
    "write_sqlite",
    "write_pmtiles",
]
