# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The bulk-export orchestrator — the headline §38 acceptance criteria end-to-end.

AC1: an incompatible share-alike mix fails the build (SIG-EXPORT-004 / SIG-LIC-010).
AC2: ODbL assets ship as a distinct ODbL-1.0 file, never merged into the CC-BY export,
     and every row carries rights provenance (SIG-EXPORT-005 / SIG-EXPORT-006).
AC3: the crosswalk is produced separately, prominently, under the most permissive
     licence its constituents allow (SIG-EXPORT-007).
Repro: two builds from the same BuildSpec are byte-identical (SIG-EXPORT-003).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from exports.compartments import RIGHTS_KEY
from exports.manifest import BuildSpec
from policy.licensing import LicenseIncompatibilityError
from policy.rights import RightsRecord

from exports import bundle as B
from exports import compartments as C

_SPEC = BuildSpec(date(2026, 6, 30), date(2026, 6, 30), "ruleset/1", "resolver/1")


def _rr(source_id: str, spdx: str, **kw: object) -> RightsRecord:
    defaults: dict[str, object] = dict(
        attribution=f"attr:{source_id}",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 1, 1),
    )
    defaults.update(kw)
    return RightsRecord(source_id=source_id, spdx=spdx, **defaults)  # type: ignore[arg-type]


RIGHTS = [_rr("osm", "ODbL-1.0"), _rr("sig", "CC-BY-4.0"), _rr("ont", "CC0-1.0")]
DEVICES = C.ExportTable(
    "devices",
    (
        C.ExportRow(
            "osm", {"subject_id": "d1", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}}
        ),
    ),
    kind="geo",
    compartment="osm_physical",
)
CLAIMS = C.ExportTable(
    "claims", (C.ExportRow("sig", {"subject_id": "e1", "predicate": "operates"}),)
)
CAPTURES = C.ExportTable("captures", (C.ExportRow("sig", {"capture_id": "c1"}),), kind="evidence")
CROSSWALK = B.crosswalk_table_from_rows(
    [{"sig_id": "e1", "scheme": "ORI9", "value": "CA0010000"}], source_id="ont"
)


def _build() -> B.Bundle:
    return B.build_bundle(_SPEC, [DEVICES, CLAIMS, CAPTURES], RIGHTS, crosswalk=CROSSWALK)


# --- AC1 ----------------------------------------------------------------------


def test_incompatible_share_alike_mix_fails_the_build() -> None:
    bad = C.ExportTable("bad", (C.ExportRow("osm", {}), C.ExportRow("sig", {})))
    with pytest.raises(LicenseIncompatibilityError):
        B.build_bundle(_SPEC, [bad], RIGHTS)


def test_a_valid_single_compartment_build_succeeds() -> None:
    bundle = _build()
    assert bundle.manifest.artifacts


# --- AC2 ----------------------------------------------------------------------


def test_odbl_assets_are_a_distinct_file_never_merged_into_cc_by() -> None:
    bundle = _build()
    odbl = [a for a in bundle.manifest.artifacts if a.compartment == "osm_physical"]
    ccby = [a for a in bundle.manifest.artifacts if a.compartment == "sig_graph"]
    assert odbl and ccby
    assert all(a.license == "ODbL-1.0" for a in odbl)
    assert all(a.license == "CC-BY-4.0" for a in ccby)
    # physically separate files: the ODbL and CC-BY paths never coincide.
    assert not (set(a.path for a in odbl) & set(a.path for a in ccby))
    # and the ODbL rows are under their own directory.
    assert all(a.path.startswith("osm_physical/") for a in odbl)


def test_every_exported_row_carries_rights_provenance() -> None:
    bundle = _build()
    jsonl = bundle.artifact_bytes["osm_physical/devices.jsonl"].decode("utf-8")
    row = json.loads(jsonl.splitlines()[0])
    assert row[RIGHTS_KEY]["license"] == "ODbL-1.0"
    assert row[RIGHTS_KEY]["share_alike"] is True


# --- AC3 ----------------------------------------------------------------------


def test_crosswalk_is_published_separately_and_most_permissive() -> None:
    bundle = _build()
    cw = [a for a in bundle.manifest.artifacts if a.path.startswith("crosswalk/")]
    assert cw, "crosswalk must be its own prominent artifact set"
    # its constituent is CC0-1.0, so the most permissive licence is CC0-1.0.
    assert bundle.crosswalk_license == "CC0-1.0"
    assert all(a.license == "CC0-1.0" for a in cw)
    # separate from the main dataset compartments.
    assert all(not a.path.startswith(("sig_graph/", "osm_physical/")) for a in cw)


# --- reproducibility (SIG-EXPORT-003) -----------------------------------------


def test_two_builds_from_the_same_spec_are_byte_identical() -> None:
    a, b = _build(), _build()
    assert a.build_spec.release_id() == b.build_spec.release_id()
    assert a.artifact_bytes == b.artifact_bytes
    assert a.manifest.to_bytes() == b.manifest.to_bytes()


# --- SIG-EXPORT-001 / 002 -----------------------------------------------------


def test_manifest_lists_every_artifact_with_a_checksum() -> None:
    bundle = _build()
    for a in bundle.manifest.artifacts:
        assert len(a.sha256) == 64
        assert a.byte_size == len(bundle.artifact_bytes[a.path])


def test_frictionless_and_ro_crate_descriptors_are_present() -> None:
    bundle = _build()
    paths = {a.path for a in bundle.manifest.artifacts}
    assert "datapackage.json" in paths  # tabular Frictionless package (SIG-EXPORT-002)
    assert "ro-crate-metadata.json" in paths  # evidence RO-Crate (SIG-EXPORT-002)


def test_datapackage_excludes_evidence_and_ro_crate_includes_it() -> None:
    # SIG-EXPORT-002: tabular ships as a Data Package, evidence ships as RO-Crate — the
    # two resource sets are disjoint.
    bundle = _build()
    dp = json.loads(bundle.artifact_bytes["datapackage.json"])
    dp_paths = {r["path"] for r in dp["resources"]}
    assert not any(p.startswith("sig_graph/captures") for p in dp_paths)  # evidence excluded
    crate = json.loads(bundle.artifact_bytes["ro-crate-metadata.json"])
    crate_ids = {e["@id"] for e in crate["@graph"]}
    assert any(i.startswith("sig_graph/captures") for i in crate_ids)  # evidence in the crate


# --- SIG-EXPORT-008/009 distribution wired into the build ---------------------


def test_distribution_plan_is_built_when_a_low_egress_store_is_given() -> None:
    from exports.distribution import ObjectStore

    bundle = B.build_bundle(
        _SPEC,
        [DEVICES, CLAIMS],
        RIGHTS,
        crosswalk=CROSSWALK,
        store=ObjectStore("cloudflare-r2", "sig"),
        base_url="https://s3/sig",
        cdn_url="https://cdn/sig",
    )
    assert bundle.distribution is not None
    assert "distribution.json" in bundle.artifact_bytes
    plan = json.loads(bundle.artifact_bytes["distribution.json"])
    assert plan["store"]["egress_class"] == "zero"


def test_metered_egress_store_fails_the_build() -> None:
    from exports.distribution import EgressError, ObjectStore

    with pytest.raises(EgressError):
        B.build_bundle(
            _SPEC,
            [CLAIMS],
            RIGHTS,
            store=ObjectStore("aws-s3", "sig"),
            base_url="https://s3/sig",
            cdn_url="https://cdn/sig",
        )


# --- SIG-EXPORT-010/011 downstream portfolio ----------------------------------


def test_validate_portfolio_passes_with_external_capabilities() -> None:
    bundle = _build()
    bundle.validate_portfolio(
        external_capabilities={
            "json_api",
            "evidence_links",
            "belief_pinned_permalinks",
            "jurisdiction_slice",
            "procurement_feed",
            "ical_rss",
            "edge_list",
            "zenodo_doi",
        }
    )


def test_route_privacy_and_researcher_layers_are_separate_files() -> None:
    # SIG-EXPORT-011 is enforced in the build; the ODbL geo layer and the CC-BY graph
    # never coincide.
    bundle = _build()
    route = set(p for p in bundle.paths_in_compartment("osm_physical"))
    researcher = set(bundle.paths_in_compartment("sig_graph"))
    assert route and researcher and not (route & researcher)


# --- SIG-EXPORT-007 crosswalk via the canonical resolution builder ------------


def test_crosswalk_built_via_resolution_builder_and_licence_gate() -> None:
    from resolution.identity import Identifier

    entities = [("e1", [Identifier(scheme="ORI9", value="CA0010000")])]
    cw = B.crosswalk_table_from_identifiers(
        entities, source_id="ont", rights=[_rr("ont", "CC0-1.0")]
    )
    bundle = B.build_bundle(_SPEC, [CLAIMS], RIGHTS, crosswalk=cw)
    assert bundle.crosswalk_license == "CC0-1.0"
    assert any(a.path.startswith("crosswalk/") for a in bundle.manifest.artifacts)


def test_write_to_materialises_artifacts_and_manifest(tmp_path: Path) -> None:
    bundle = _build()
    bundle.write_to(tmp_path)
    assert (tmp_path / "manifest.json").exists()
    for a in bundle.manifest.artifacts:
        assert (tmp_path / a.path).read_bytes() == bundle.artifact_bytes[a.path]


def test_bundle_capabilities_include_the_export_provided_classes() -> None:
    caps = _build().capabilities()
    assert {"parquet", "geojson", "pmtiles", "crosswalk", "odbl_asset_layer"} <= caps
