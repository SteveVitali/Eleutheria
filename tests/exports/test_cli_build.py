# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `sig-exports build` CLI drives a full release end-to-end (SIG-ENG-013, §38)."""

from __future__ import annotations

import json
from pathlib import Path

from exports.cli import main

REQUEST = {
    "build_spec": {
        "as_of_snapshot": "2026-06-30",
        "as_of_belief": "2026-06-30",
        "ruleset_version": "ruleset/1",
        "resolver_version": "resolver/1",
    },
    "rights": [
        {
            "source_id": "osm",
            "spdx": "ODbL-1.0",
            "attribution": "© OSM",
            "redistributable": True,
            "derivative_permitted": True,
            "terms_url": "u",
            "retrieval_date": "2026-01-01",
        },
        {
            "source_id": "sig",
            "spdx": "CC-BY-4.0",
            "attribution": "© SIG",
            "redistributable": True,
            "derivative_permitted": True,
            "terms_url": "u",
            "retrieval_date": "2026-01-01",
        },
        {
            "source_id": "ont",
            "spdx": "CC0-1.0",
            "attribution": "",
            "redistributable": True,
            "derivative_permitted": True,
            "terms_url": "u",
            "retrieval_date": "2026-01-01",
        },
    ],
    "tables": [
        {
            "name": "devices",
            "kind": "geo",
            "compartment": "osm_physical",
            "rows": [
                {
                    "source_id": "osm",
                    "data": {
                        "subject_id": "d1",
                        "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                    },
                }
            ],
        },
        {
            "name": "claims",
            "kind": "tabular",
            "rows": [{"source_id": "sig", "data": {"subject_id": "e1"}}],
        },
    ],
    "crosswalk": {
        "name": "sig_external_crosswalk",
        "source_id": "ont",
        "rows": [{"sig_id": "e1", "scheme": "ORI9", "value": "CA0010000"}],
    },
}


def test_build_cli_writes_artifacts_and_manifest(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    request = tmp_path / "request.json"
    request.write_text(json.dumps(REQUEST), encoding="utf-8")
    out = tmp_path / "release"

    rc = main(["build", str(request), "--out", str(out), "--zenodo-dry-run"])
    assert rc == 0

    assert (out / "manifest.json").exists()
    assert (out / "osm_physical" / "devices.pmtiles").exists()
    assert (out / "sig_graph" / "claims.parquet").exists()
    assert (out / "crosswalk" / "sig_external_crosswalk.csv").exists()
    assert (out / "datapackage.json").exists()

    summary = json.loads(capsys.readouterr().out)
    assert summary["concept_id"] == "sig"
    assert "ODbL-1.0" in summary["licenses"] and "CC-BY-4.0" in summary["licenses"]
    assert summary["zenodo"]["concept_doi"].startswith("10.5281/zenodo.")
    assert summary["zenodo"]["version_doi"] != summary["zenodo"]["concept_doi"]


def test_build_cli_is_reproducible(tmp_path: Path) -> None:
    request = tmp_path / "request.json"
    request.write_text(json.dumps(REQUEST), encoding="utf-8")
    out1, out2 = tmp_path / "r1", tmp_path / "r2"
    assert main(["build", str(request), "--out", str(out1)]) == 0
    assert main(["build", str(request), "--out", str(out2)]) == 0
    assert (out1 / "manifest.json").read_bytes() == (out2 / "manifest.json").read_bytes()
