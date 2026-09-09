# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The deterministic bulk-format writer registry (§38.1, SIG-EXPORT-001)."""

from __future__ import annotations

import gzip
import json
import sqlite3
import struct

import pytest
from exports.compartments import RIGHTS_KEY

from exports import formats as F

_RIGHTS = {"license": "ODbL-1.0", "share_alike": True, "attribution": "© OSM"}
ROWS = [
    {
        "subject_id": "a",
        "count": 3,
        "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
        RIGHTS_KEY: _RIGHTS,
    },
    {"subject_id": "b", "count": None, "geometry": None, RIGHTS_KEY: _RIGHTS},
]

ALL_FORMATS = ["parquet", "csv", "jsonl", "jsonld", "sqlite", "geojson", "pmtiles"]


def test_all_seven_export_formats_are_registered() -> None:
    # SIG-EXPORT-001 names seven formats; every one has a writer.
    assert set(F.FORMATS) == set(ALL_FORMATS)


@pytest.mark.parametrize("name", ALL_FORMATS)
def test_every_writer_is_deterministic(name: str) -> None:
    spec = F.FORMATS[name]
    a = spec.writer(ROWS, geometry_key="geometry", table_name="t")
    b = spec.writer(ROWS, geometry_key="geometry", table_name="t")
    assert a == b
    assert isinstance(a, bytes) and a


def test_csv_has_sorted_header_and_flattened_rights_columns() -> None:
    text = F.write_csv(ROWS).decode("utf-8")
    header = text.splitlines()[0].split(",")
    assert header == sorted(header)
    assert "rights_license" in header and "rights_share_alike" in header


def test_jsonl_is_one_object_per_line_with_nested_rights() -> None:
    lines = F.write_jsonl(ROWS).decode("utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first[RIGHTS_KEY]["license"] == "ODbL-1.0"


def test_geojson_is_a_feature_collection_with_geometry() -> None:
    fc = json.loads(F.write_geojson(ROWS))
    assert fc["type"] == "FeatureCollection"
    assert fc["features"][0]["geometry"] == {"type": "Point", "coordinates": [1.0, 2.0]}
    assert fc["features"][0]["properties"]["rights"]["license"] == "ODbL-1.0"


def test_jsonld_has_context_and_graph() -> None:
    doc = json.loads(F.write_jsonld(ROWS, table_name="devices"))
    assert "@context" in doc
    assert doc["@graph"][0]["@id"] == "sig:devices/0"


def test_sqlite_bytes_open_as_a_valid_database() -> None:
    data = F.write_sqlite(ROWS, table_name="export")
    assert data[:16] == b"SQLite format 3\x00"
    import io
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db") as fh:
        fh.write(data)
        fh.flush()
        conn = sqlite3.connect(fh.name)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(export)")}
        assert "subject_id" in cols and "rights_license" in cols
        assert conn.execute("SELECT count(*) FROM export").fetchone()[0] == 2
        conn.close()
    _ = io  # keep import local + used


def test_parquet_is_written_and_readable_by_duckdb() -> None:
    import duckdb

    data = F.write_parquet(ROWS, table_name="export")
    assert data[:4] == b"PAR1"  # the Parquet magic
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x.parquet"
        p.write_bytes(data)
        n = duckdb.connect().execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
        assert n == 2


def test_pmtiles_is_a_valid_v3_archive() -> None:
    # SIG-EXPORT-001: PMTiles is a real, parseable archive (metadata-only tileset).
    data = F.write_pmtiles(ROWS, geometry_key="geometry")
    assert data[0:7] == b"PMTiles"
    assert data[7] == 3
    meta_off = struct.unpack_from("<Q", data, 24)[0]
    meta_len = struct.unpack_from("<Q", data, 32)[0]
    metadata = json.loads(gzip.decompress(data[meta_off : meta_off + meta_len]))
    assert metadata["format"] == "geojson"


def test_formats_for_geo_adds_geometry_formats() -> None:
    assert "pmtiles" in F.formats_for("geo")
    assert "pmtiles" not in F.formats_for("tabular")
