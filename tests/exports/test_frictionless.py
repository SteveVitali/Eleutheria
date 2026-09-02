# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Frictionless Data Package + RO-Crate descriptors (§38.1, SIG-EXPORT-002)."""

from __future__ import annotations

import json
from datetime import date

from exports.manifest import Artifact, BuildSpec

from exports import frictionless as FR

_SPEC = BuildSpec(date(2026, 6, 30), date(2026, 6, 30), "ruleset/1", "resolver/1")


def _artifact(path: str, license: str) -> Artifact:
    return Artifact.of(
        name=path.split("/")[-1],
        path=path,
        media_type="text/csv",
        compartment=path.split("/")[0],
        license=license,
        data=path.encode(),
        row_count=1,
    )


def test_data_package_is_a_valid_descriptor_with_per_resource_licences() -> None:
    arts = [
        _artifact("sig_graph/claims.csv", "CC-BY-4.0"),
        _artifact("osm_physical/devices.csv", "ODbL-1.0"),
    ]
    dp = json.loads(FR.data_package(arts, _SPEC))
    assert dp["profile"] == "data-package"
    assert dp["name"] == _SPEC.release_id()
    assert dp["id"] == "sig"
    # Each resource keeps its own licence + checksum (a package spans compartments).
    by_path = {r["path"]: r for r in dp["resources"]}
    assert by_path["osm_physical/devices.csv"]["licenses"][0]["name"] == "ODbL-1.0"
    assert by_path["sig_graph/claims.csv"]["hash"].startswith("sha256:")


def test_ro_crate_conforms_and_lists_evidence_files() -> None:
    arts = [_artifact("evidence/captures.jsonl", "CC-BY-4.0")]
    crate = json.loads(FR.ro_crate(arts, _SPEC))
    assert crate["@context"] == "https://w3id.org/ro/crate/1.1/context"
    ids = {e["@id"] for e in crate["@graph"]}
    assert "ro-crate-metadata.json" in ids
    assert "./" in ids
    assert "evidence/captures.jsonl" in ids
    dataset = next(e for e in crate["@graph"] if e["@id"] == "./")
    assert dataset["@type"] == "Dataset"
    assert {"@id": "evidence/captures.jsonl"} in dataset["hasPart"]


def test_descriptors_are_byte_stable() -> None:
    arts = [_artifact("sig_graph/claims.csv", "CC-BY-4.0")]
    assert FR.data_package(arts, _SPEC) == FR.data_package(arts, _SPEC)
    assert FR.ro_crate(arts, _SPEC) == FR.ro_crate(arts, _SPEC)


def test_license_urls_are_resolved() -> None:
    assert FR.license_url("ODbL-1.0").startswith("https://opendatacommons.org")
    assert FR.license_url("CC-BY-4.0").startswith("https://creativecommons.org")
