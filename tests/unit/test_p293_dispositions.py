# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P29.3 dispositions artifact — the evidenced-licence record for the new
accountability/governance sources (SIG-LIC-001/002/009, P27.2/ADR-095).

The deterministic half of the ticket AC "each yielding source ... carries an evidenced
licence (P27.2)": the artifact is well-formed and consistent with the registries —
every resolution validates, every publishable licence names a real licence-registry
row AND a compartment (else the export would fail closed later), every source names an
existing rights packet, the reviewer is a ROLE (Part VIII §0.7), and every disposition
matches the flipped `sources.toml` `[rights]` block. The hosted `apply` is deferred with
the live fetch under the OSM-land contention (D-R7.3-BREADTH); this file proves the
artifact is ready, not that it has been applied.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from db.rights_decisions import load_resolutions, validate_resolution
from policy.licensing import compartments

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs/build/reports/rights/p293_dispositions.json"
LICENSES_TOML = REPO / "policy/src/policy/data/licenses.toml"
SOURCES_TOML = REPO / "connectors/src/connectors/data/sources.toml"

# The eight targeted accountability/governance sources P29.3 flips under GL-GATE-07.
P293_SOURCES = frozenset(
    {
        "gao_surveillance_reports",
        "dhs_oig_reports",
        "dhs_fusion_center_assessments",
        "fema_hsgp_allocations",
        "ccops_oakland",
        "ccops_cambridge",
        "ccops_somerville",
        "uk_surveillance_camera_commissioner",
    }
)


def _licence_registry() -> dict:
    return tomllib.loads(LICENSES_TOML.read_text())["licenses"]


def test_artifact_loads_and_every_row_validates() -> None:
    resolutions = load_resolutions(ARTIFACT)
    assert {r.source_id for r in resolutions} == P293_SOURCES
    for res in resolutions:
        assert validate_resolution(res) == [], res.source_id


def test_every_publishable_licence_has_a_compartment() -> None:
    """A flipped licence with no compartment would fail the export gate later."""
    registry = _licence_registry()
    lic_to_compartment = {c["license"]: name for name, c in compartments().items()}
    for res in load_resolutions(ARTIFACT):
        assert res.spdx in registry, f"{res.source_id}: unknown licence {res.spdx}"
        if res.redistributable == "yes":
            assert res.spdx in lic_to_compartment, (
                f"{res.source_id}: publishable licence {res.spdx} has no compartment"
            )


def test_every_resolution_names_an_existing_rights_packet() -> None:
    for res in load_resolutions(ARTIFACT):
        assert res.review_packet, f"{res.source_id}: no review packet"
        assert (REPO / res.review_packet).exists(), f"{res.source_id}: missing {res.review_packet}"


def test_reviewer_is_a_role_never_a_personal_name() -> None:
    """Part VIII §0.7 / SIG-LIC-009 — review attribution is a role, not a person."""
    for res in load_resolutions(ARTIFACT):
        assert res.reviewed_by in {
            "maintainer (delegated)",
            "counsel (HG-02)",
            "licensing reviewer",
        }, f"{res.source_id}: unexpected reviewer {res.reviewed_by!r}"


def test_every_source_is_flipped_in_the_registry_with_a_matching_disposition() -> None:
    """Each P29.3 source is ingestion_permitted=true with the SAME licence the artifact
    records — the spine decision must match the recorded source disposition, never drift."""
    sources = tomllib.loads(SOURCES_TOML.read_text())["sources"]
    for res in load_resolutions(ARTIFACT):
        assert res.source_id in sources, f"{res.source_id} not in sources.toml"
        row = sources[res.source_id]
        assert row.get("ingestion_permitted") is True, f"{res.source_id} not flipped"
        recorded = row.get("rights", {})
        assert recorded.get("spdx") == res.spdx, (
            f"{res.source_id}: artifact {res.spdx} != registry {recorded.get('spdx')}"
        )


def test_gl_gate_07_basis_is_applied_by_jurisdiction() -> None:
    """US federal -> CC0-1.0 (17 U.S.C. §105 packet); US municipal -> PublicRecord;
    non-US -> OperatorAccepted-DBRight (the GL-GATE-07 rule the gate answer names)."""
    by_source = {r.source_id: r for r in load_resolutions(ARTIFACT)}
    for sid in (
        "gao_surveillance_reports",
        "dhs_oig_reports",
        "dhs_fusion_center_assessments",
        "fema_hsgp_allocations",
    ):
        assert by_source[sid].spdx == "CC0-1.0", sid
    for sid in ("ccops_oakland", "ccops_cambridge", "ccops_somerville"):
        assert by_source[sid].spdx == "LicenseRef-PublicRecord-FactualCompilation", sid
    assert by_source["uk_surveillance_camera_commissioner"].spdx == (
        "LicenseRef-OperatorAccepted-DBRight"
    )
