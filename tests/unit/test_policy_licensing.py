# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Rights records and the N-compartment export licence gates (§42, SIG-LIC-*)."""

from __future__ import annotations

from datetime import date

import pytest
from policy.rights import RightsRecord, is_undetermined

from policy import licensing


def _rec(source_id: str, spdx: str, **kw: object) -> RightsRecord:
    defaults: dict[str, object] = dict(
        attribution="attr",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 1, 1),
    )
    defaults.update(kw)
    return RightsRecord(source_id=source_id, spdx=spdx, **defaults)  # type: ignore[arg-type]


# --- SIG-LIC-001/003: rights record shape; redistributable is separate --------


def test_rights_record_requires_identity_and_a_licence() -> None:
    with pytest.raises(ValueError):
        _rec("", "CC-BY-4.0")  # empty source_id
    with pytest.raises(ValueError):
        _rec("s", "")  # empty spdx


def test_redistributable_is_a_separate_boolean_not_derived_from_licence() -> None:
    # A permissive licence string with redistributable=False must be honoured by
    # the gate (SIG-LIC-003): the boolean governs, not the string.
    rec = _rec("s", "CC-BY-4.0", redistributable=False)
    with pytest.raises(licensing.ExportGateClosed):
        licensing.assert_export_permitted([rec])


# --- SIG-LIC-004: UNDETERMINED fails the export gate closed --------------------


def test_undetermined_fails_export_gate_closed() -> None:
    rec = _rec("s", "UNDETERMINED")
    assert is_undetermined(rec)
    with pytest.raises(licensing.ExportGateClosed):
        licensing.assert_export_permitted([rec])
    with pytest.raises(licensing.ExportGateClosed):
        licensing.compute_export_license([rec])


# --- SIG-LIC-004a/010: compartments are data; cross-compartment merge fails ----


def test_deliberate_cross_compartment_merge_fails_the_build() -> None:
    odbl = _rec("osm", "ODbL-1.0")
    ccby = _rec("sig", "CC-BY-4.0")
    with pytest.raises(licensing.LicenseIncompatibilityError):
        licensing.compute_export_license([odbl, ccby])


def test_two_share_alike_regimes_are_not_mergeable() -> None:
    odbl = _rec("osm", "ODbL-1.0")
    sa = _rec("portal", "CC-BY-SA-4.0")
    with pytest.raises(licensing.LicenseIncompatibilityError):
        licensing.compute_export_license([odbl, sa])


def test_same_compartment_merges_to_its_licence() -> None:
    assert licensing.compute_export_license([_rec("a", "CC-BY-4.0"), _rec("b", "CC-BY-4.0")]) == (
        "CC-BY-4.0"
    )


def test_public_domain_folds_into_a_permissive_export() -> None:
    cc0 = _rec("ont", "CC0-1.0")
    ccby = _rec("sig", "CC-BY-4.0")
    assert licensing.compute_export_license([cc0, ccby]) == "CC-BY-4.0"


def test_compartments_are_data_not_code() -> None:
    # Adding a source under a new share-alike licence must be a data row, not a
    # schema/code change: the gate evaluates a supplied registry unchanged.
    registry = {
        "licenses": {
            "LicenseRef-SIG-New-SA": {
                "share_alike": True,
                "relicensable_to": ["LicenseRef-SIG-New-SA"],
            },
            "CC-BY-4.0": {"share_alike": False, "relicensable_to": ["CC-BY-4.0"]},
        }
    }
    new_sa = _rec("new", "LicenseRef-SIG-New-SA")
    assert licensing.compute_export_license([new_sa], registry=registry) == "LicenseRef-SIG-New-SA"
    with pytest.raises(licensing.LicenseIncompatibilityError):
        licensing.compute_export_license([new_sa, _rec("sig", "CC-BY-4.0")], registry=registry)


# --- SIG-LIC-009a: silently-travelling share-alike defaults to the stricter ----


def test_silently_travelling_share_alike_uses_stricter_upstream() -> None:
    # Declares CC-BY-4.0 but is derived from an ODbL upstream: ODbL governs.
    laundered = _rec("laundered", "CC-BY-4.0", upstream_license="ODbL-1.0")
    assert licensing.effective_license(laundered) == "ODbL-1.0"
    with pytest.raises(licensing.LicenseIncompatibilityError):
        licensing.compute_export_license([laundered, _rec("sig", "CC-BY-4.0")])


# --- SIG-LIC-004b/004c: ai-training gate enforced at the data layer ------------


def test_training_gate_blocks_non_permitted_content() -> None:
    rec = _rec("s", "CC-BY-4.0", ai_training_permitted=False)
    with pytest.raises(licensing.TrainingNotPermitted):
        licensing.assert_training_allowed(rec)


def test_training_gate_allows_permitted_content() -> None:
    rec = _rec("s", "CC-BY-4.0", ai_training_permitted=True)
    licensing.assert_training_allowed(rec)  # does not raise


# --- SIG-LIC-005: SIG's own licences are declared as data ----------------------


def test_downstream_obligations_are_passed_per_row() -> None:
    # SIG-LIC-011: a downstream consumer can comply without re-deriving the chain.
    ob = licensing.downstream_obligations(_rec("osm", "ODbL-1.0", attribution="© OSM contributors"))
    assert ob["license"] == "ODbL-1.0"
    assert ob["share_alike"] is True
    assert ob["attribution_required"] is True
    assert ob["attribution"] == "© OSM contributors"


def test_downstream_obligations_reflect_stricter_upstream() -> None:
    ob = licensing.downstream_obligations(_rec("x", "CC-BY-4.0", upstream_license="ODbL-1.0"))
    assert ob["license"] == "ODbL-1.0"  # SIG-LIC-009a governs the passed obligation
    assert ob["share_alike"] is True


def test_sig_own_licence_compartments_present() -> None:
    comps = licensing.compartments()
    licences = {c["license"] for c in comps.values()}
    assert {"Apache-2.0", "CC-BY-4.0", "ODbL-1.0", "CC-BY-SA-4.0", "CC0-1.0"} <= licences
