# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.43 / K3 SRCH-08 — the search-result export bundle: per licence
group with licence files (J3 TX download conventions), never a
mixed-compartment file, ≤ 10,000 rows, deterministic bytes."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile

import pytest
from exports.search_export import (
    SEARCH_EXPORT_ROWS_SCHEMA,
    SEARCH_EXPORT_SCHEMA,
    SearchExportError,
    search_export_zip,
)


def _payload(rows_a: list[dict], rows_b: list[dict]) -> dict:
    return {
        "schema": "sig.search-results/2",
        "release": {
            "label": "sig-2026-11-01",
            "publication_id": "p-" + "a" * 64,
            "as_of_world": "2026-11-01",
        },
        "query": {"q": "camera", "normalized": "camera", "filters": {}, "types": None},
        "scope": {
            "records_indexed": 10,
            "records_searched": 9,
            "groups_searched": 2,
            "excluded_records_by_reason": {"safety_withdrawal": 1},
        },
        "export": {
            "row_cap": 10_000,
            "exported_records": len(rows_a) + len(rows_b),
            "truncated": False,
            "groups": [
                {
                    "compartment": "sig_graph",
                    "license": "CC-BY-4.0",
                    "total": len(rows_a),
                    "collapsed_reason": None,
                    "exported": len(rows_a),
                    "rows": rows_a,
                    "truncated": False,
                },
                {
                    "compartment": "osm_physical",
                    "license": "ODbL-1.0",
                    "total": len(rows_b),
                    "collapsed_reason": None,
                    "exported": len(rows_b),
                    "rows": rows_b,
                    "truncated": False,
                },
            ],
        },
    }


def _row(key: str, name: str, source: str = "src_a") -> dict:
    return {
        "record_key": key,
        "entity_id": key.split(":")[-1],
        "entity_type": "deployment",
        "name": name,
        "name_derived": False,
        "name_basis": "source",
        "jurisdiction": "iso3166-2:US-OK",
        "place": "Oklahoma",
        "sources": [source],
        "source_names": ["Oklahoma test source"],
        "technology": "alpr",
        "matched": "name phrase",
        "tier": 2,
        "score": -1.5,
        "href": f"/r/p-{'a' * 64}/c/sig_graph/entity/deployment/{key}/",
    }


def _unzip(body: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(body))


def test_zip_is_per_licence_group_never_mixed() -> None:
    payload = _payload([_row("k1", "Site one")], [_row("k2", "OSM site", "src_osm")])
    body, filename = search_export_zip(payload, fmt="csv", requested="latest")
    assert filename.endswith(".zip") and filename.startswith("sig-search-export-")
    names = _unzip(body).namelist()
    for comp in ("sig_graph", "osm_physical"):
        assert f"{comp}/results.csv" in names
        assert f"{comp}/LICENCE.txt" in names
        assert f"{comp}/ATTRIBUTION.txt" in names
    assert "manifest.json" in names and "SHA256SUMS" in names
    # No file holds rows from more than one licence group.
    z = _unzip(body)
    for comp in ("sig_graph", "osm_physical"):
        csv_text = z.read(f"{comp}/results.csv").decode()
        assert "# licence: " in csv_text
    sg = z.read("sig_graph/results.csv").decode()
    assert "k1" in sg and "k2" not in sg
    om = z.read("osm_physical/results.csv").decode()
    assert "k2" in om and "k1" not in om
    # Every exported row carries its licence on the row itself.
    assert "CC-BY-4.0" in sg.splitlines()[-1]
    assert "ODbL-1.0" in om.splitlines()[-1]


def test_manifest_and_sums() -> None:
    body, _ = search_export_zip(
        _payload([_row("k1", "A")], [_row("k2", "B", "src_osm")]),
        fmt="csv",
        requested="latest",
    )
    z = _unzip(body)
    man = json.loads(z.read("manifest.json"))
    assert man["schema"] == SEARCH_EXPORT_SCHEMA
    assert man["export"]["row_cap"] == 10_000
    assert man["export"]["exported_records"] == 2
    assert man["scope"]["excluded_records_by_reason"] == {"safety_withdrawal": 1}
    groups = {g["compartment"]: g for g in man["groups"]}
    assert groups["sig_graph"]["license"] == "CC-BY-4.0"
    assert groups["osm_physical"]["license"] == "ODbL-1.0"
    sums = z.read("SHA256SUMS").decode().splitlines()
    digests = {}
    for line in sums:
        sha, path = line.split("  ", 1)
        digests[path] = sha
    assert set(digests) == set(z.namelist()) - {"SHA256SUMS"}
    for path, sha in digests.items():
        assert hashlib.sha256(z.read(path)).hexdigest() == sha


def test_licence_and_attribution_files() -> None:
    body, _ = search_export_zip(
        _payload([_row("k1", "A")], [_row("k2", "B", "src_osm")]),
        fmt="csv",
        requested="latest",
    )
    z = _unzip(body)
    lic = z.read("osm_physical/LICENCE.txt").decode()
    assert "ODbL-1.0" in lic and "opendatacommons.org" in lic
    att = z.read("osm_physical/ATTRIBUTION.txt").decode()
    assert "src_osm" in att
    assert "/releases/p-" + "a" * 64 + "/data/" in att
    # A LicenseRef / unmapped licence never fabricates an SPDX URL.
    assert (
        "LicenseRef" in z.read("sig_graph/LICENCE.txt").decode()
        or "CC-BY-4.0" in z.read("sig_graph/LICENCE.txt").decode()
    )


def test_csv_quoting() -> None:
    tricky = _row("k1", 'Name, "quoted"\nand newline')
    body, _ = search_export_zip(_payload([tricky], []), fmt="csv", requested="latest")
    csv_text = _unzip(body).read("sig_graph/results.csv").decode()
    row = [ln for ln in csv_text.splitlines() if ln.startswith("k1") or '"and newline' in ln]
    assert row, csv_text
    # The whole multi-line cell survives as one quoted field.
    import csv as _csv

    data_rows = [r for r in _csv.reader(io.StringIO(csv_text)) if r and r[0] == "k1"]
    assert data_rows[0][3] == 'Name, "quoted"\nand newline'


def test_json_members() -> None:
    body, _ = search_export_zip(_payload([_row("k1", "A")], []), fmt="json", requested="latest")
    z = _unzip(body)
    assert "sig_graph/results.json" in z.namelist()
    assert "sig_graph/results.csv" not in z.namelist()
    doc = json.loads(z.read("sig_graph/results.json"))
    assert doc["schema"] == SEARCH_EXPORT_ROWS_SCHEMA
    assert doc["compartment"] == "sig_graph"
    assert doc["rows"][0]["license"] == "CC-BY-4.0"
    assert doc["rows"][0]["record_key"] == "k1"


def test_deterministic() -> None:
    payload = _payload([_row("k1", "A")], [_row("k2", "B", "src_osm")])
    a, fa = search_export_zip(payload, fmt="csv", requested="latest")
    b, fb = search_export_zip(payload, fmt="csv", requested="latest")
    assert a == b and fa == fb


def test_empty_export_still_bundles() -> None:
    body, _ = search_export_zip(_payload([], []), fmt="csv", requested="latest")
    names = _unzip(body).namelist()
    assert "manifest.json" in names and "SHA256SUMS" in names
    assert not any(n.endswith("results.csv") for n in names)
    man = json.loads(_unzip(body).read("manifest.json"))
    assert man["export"]["exported_records"] == 0


def test_bad_format_refuses() -> None:
    with pytest.raises(SearchExportError):
        search_export_zip(_payload([], []), fmt="yaml", requested="latest")
