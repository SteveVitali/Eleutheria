# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P27.2 dispositions artifact — the reviewer-prepared flip list (SIG-LIC-001/002/009).

Asserts the committed artifact is well-formed and consistent with the registries:
every resolution validates, every publishable licence names a real licence-registry
row AND a compartment (else the export would fail closed later), every source names
an existing rights packet, and the reviewer is a ROLE, never a personal name
(Part VIII §0.7). Also pins the Part VIII invariants the class-level sign-off does
NOT relax (the officer-naming concurrence gate still fails closed).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from db.rights_decisions import (
    RightsResolutionError,
    load_resolutions,
    validate_resolution,
)
from policy.licensing import compartments
from policy.officer import OfficerNamingProngs, evaluate_officer_naming

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs/build/reports/rights/p272_dispositions.json"
LICENSES_TOML = REPO / "policy/src/policy/data/licenses.toml"
SOURCES_TOML = REPO / "connectors/src/connectors/data/sources.toml"


def _licence_registry() -> dict:
    return tomllib.loads(LICENSES_TOML.read_text())["licenses"]


def test_artifact_loads_and_every_row_validates() -> None:
    resolutions = load_resolutions(ARTIFACT)
    assert len(resolutions) >= 30  # the P27.1-audited UNDETERMINED source set
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


def test_every_resolution_names_a_rights_packet() -> None:
    for res in load_resolutions(ARTIFACT):
        assert res.review_packet, f"{res.source_id}: no review packet"
        assert (REPO / res.review_packet).exists(), f"{res.source_id}: missing {res.review_packet}"


def test_reviewer_is_a_role_never_a_personal_name() -> None:
    """Part VIII §0.7 / SIG-LIC-009 — review attribution is a role, not a person."""
    for res in load_resolutions(ARTIFACT):
        # role strings like 'maintainer (delegated)' / 'counsel (HG-02)' — never a bare name.
        assert res.reviewed_by in {
            "maintainer (delegated)",
            "counsel (HG-02)",
            "licensing reviewer",
        }, f"{res.source_id}: unexpected reviewer {res.reviewed_by!r}"


def test_every_source_exists_in_the_registry_with_matching_disposition() -> None:
    sources = tomllib.loads(SOURCES_TOML.read_text())["sources"]
    for res in load_resolutions(ARTIFACT):
        assert res.source_id in sources, f"{res.source_id} not in sources.toml"
        recorded = sources[res.source_id].get("rights", {})
        # The dispositions artifact records the SAME licence the registry review did —
        # the spine decision must match the recorded source disposition, never drift.
        assert recorded.get("spdx") == res.spdx, (
            f"{res.source_id}: artifact {res.spdx} != registry {recorded.get('spdx')}"
        )


def test_no_publish_sources_are_decided_not_skipped() -> None:
    """A recorded 'no' is a decided exclusion (muckrock), not a bypass of the gate."""
    by_source = {r.source_id: r for r in load_resolutions(ARTIFACT)}
    assert by_source["muckrock"].redistributable == "no"


def test_undetermined_is_never_a_resolution() -> None:
    import dataclasses

    res = load_resolutions(ARTIFACT)[0]
    with_bad = dataclasses.replace(res, redistributable="UNDETERMINED")
    assert validate_resolution(with_bad)
    # and the loader refuses an artifact that smuggles one in
    doc = json.loads(ARTIFACT.read_text())
    doc["resolutions"][0]["redistributable"] = "UNDETERMINED"
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(doc, fh)
        fh.flush()
        try:
            load_resolutions(fh.name)
        except RightsResolutionError:
            pass
        else:  # pragma: no cover
            raise AssertionError("UNDETERMINED disposition was accepted")


def test_officer_naming_gate_is_untouched_by_the_sign_off() -> None:
    """Part VIII §43.4: the class-level sign-off does NOT weaken the per-claim
    officer-naming gate — fewer than two independent concurring reviewers still
    means no-publish, even when all five prongs hold."""
    prongs = OfficerNamingProngs(
        official_conduct=True,
        name_on_face_of_record=True,
        record_public_in_jurisdiction=True,
        claim_fails_without_name=True,
        proportionate=True,
    )
    decision = evaluate_officer_naming(prongs, ())
    assert decision.permitted is False
