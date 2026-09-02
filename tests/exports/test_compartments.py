# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Rights-keyed compartment placement + the export-time licence gate (§42.4)."""

from __future__ import annotations

from datetime import date

import pytest
from policy.licensing import ExportGateClosed, LicenseIncompatibilityError
from policy.rights import RightsRecord

from exports import compartments as C


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


def _idx(*records: RightsRecord) -> dict[str, RightsRecord]:
    return C.rights_index(records)


def test_place_table_computes_license_and_compartment() -> None:
    idx = _idx(_rr("sig", "CC-BY-4.0"))
    table = C.ExportTable("claims", (C.ExportRow("sig", {"k": 1}),))
    placed = C.place_table(table, idx)
    assert placed.license == "CC-BY-4.0"
    assert placed.compartment == "sig_graph"


def test_odbl_table_places_in_its_own_compartment() -> None:
    idx = _idx(_rr("osm", "ODbL-1.0"))
    table = C.ExportTable(
        "devices", (C.ExportRow("osm", {"k": 1}),), kind="geo", compartment="osm_physical"
    )
    placed = C.place_table(table, idx)
    assert placed.license == "ODbL-1.0"
    assert placed.compartment == "osm_physical"


def test_incompatible_mix_in_one_table_fails_the_build() -> None:
    # SIG-EXPORT-004 / SIG-LIC-010: an ODbL source and a CC-BY source in one file cannot
    # be combined into one export licence — the build stops.
    idx = _idx(_rr("osm", "ODbL-1.0"), _rr("sig", "CC-BY-4.0"))
    table = C.ExportTable("bad", (C.ExportRow("osm", {}), C.ExportRow("sig", {})))
    with pytest.raises(LicenseIncompatibilityError):
        C.place_table(table, idx)


def test_unknown_source_fails_closed() -> None:
    table = C.ExportTable("t", (C.ExportRow("ghost", {}),))
    with pytest.raises(C.UnknownSourceError):
        C.place_table(table, _idx(_rr("sig", "CC-BY-4.0")))


def test_undetermined_rights_fail_closed() -> None:
    idx = _idx(_rr("s", "UNDETERMINED"))
    table = C.ExportTable("t", (C.ExportRow("s", {}),))
    with pytest.raises(ExportGateClosed):
        C.place_table(table, idx)


def test_mislabeled_compartment_is_rejected() -> None:
    # A CC-BY table that claims the ODbL compartment must be rejected (SIG-EXPORT-005).
    idx = _idx(_rr("sig", "CC-BY-4.0"))
    table = C.ExportTable("t", (C.ExportRow("sig", {}),), compartment="osm_physical")
    with pytest.raises(LicenseIncompatibilityError):
        C.place_table(table, idx)


def test_assert_separated_rejects_two_licenses_in_one_compartment() -> None:
    a = C.PlacedTable(C.ExportTable("a", ()), "shared", "CC-BY-4.0")
    b = C.PlacedTable(C.ExportTable("b", ()), "shared", "ODbL-1.0")
    with pytest.raises(LicenseIncompatibilityError):
        C.assert_separated([a, b])


def test_enrich_rows_stamps_per_row_rights_provenance() -> None:
    # SIG-EXPORT-006 / SIG-LIC-011: every row carries its downstream obligation.
    idx = _idx(_rr("osm", "ODbL-1.0", attribution="© OSM contributors"))
    table = C.ExportTable("devices", (C.ExportRow("osm", {"subject_id": "d1"}),))
    rows = C.enrich_rows(table, idx)
    assert len(rows) == 1
    rights = rows[0][C.RIGHTS_KEY]
    assert rights["license"] == "ODbL-1.0"
    assert rights["share_alike"] is True
    assert rights["attribution"] == "© OSM contributors"


def test_silently_travelling_upstream_forces_the_stricter_compartment() -> None:
    # SIG-LIC-009a: declares CC-BY but derived from ODbL upstream => ODbL governs, so a
    # naive merge with the CC-BY graph fails the build.
    idx = _idx(_rr("laundered", "CC-BY-4.0", upstream_license="ODbL-1.0"), _rr("sig", "CC-BY-4.0"))
    table = C.ExportTable("t", (C.ExportRow("laundered", {}), C.ExportRow("sig", {})))
    with pytest.raises(LicenseIncompatibilityError):
        C.place_table(table, idx)
    # placed alone it computes to ODbL, not the declared CC-BY.
    alone = C.place_table(C.ExportTable("t", (C.ExportRow("laundered", {}),)), idx)
    assert alone.license == "ODbL-1.0"


def test_most_permissive_prefers_public_domain() -> None:
    # SIG-EXPORT-007: the crosswalk gets the least-constraining licence its inputs allow.
    assert C.most_permissive_license([_rr("a", "CC0-1.0")]) == "CC0-1.0"
    assert C.most_permissive_license([_rr("a", "CC0-1.0"), _rr("b", "CC-BY-4.0")]) == "CC-BY-4.0"
