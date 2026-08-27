# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Per-class canonical-scheme registry, the Wikidata asymmetry, and the crosswalk
exports behind the licence gate (SIG-IDENT-001/007/033/034)."""

from __future__ import annotations

from datetime import date

import pytest
from policy.rights import RightsRecord
from resolution.crosswalk import (
    build_ori_geoid_crosswalk,
    build_sig_external_crosswalk,
    canonical_scheme_for,
    export_crosswalk,
    wikidata_reliable_for,
)
from resolution.geoid import GeoidValidationError
from resolution.identity import identifier_set
from resolution.ori import OriValidationError

from policy import licensing

# --- SIG-IDENT-001: every class has a designated canonical scheme ------------


def test_us_le_class_is_ori() -> None:
    for cls in ("us.le.municipal_police", "us.le.sheriff", "us.le.state_police"):
        res = canonical_scheme_for(cls)
        assert res.canonical_scheme == "us.fbi.ori"
        assert not res.is_surrogate


def test_representative_classes_map_to_their_schemes() -> None:
    cases = {
        "us.gov.municipality": "us.census.geoid",
        "school_district": "us.nces.leaid",
        "university": "us.ipeds.unitid",
        "transit_agency": "us.ntd.id",
        "hospital": "us.cms.ccn",
        "vendor": "gleif.lei",
    }
    for cls, scheme in cases.items():
        assert canonical_scheme_for(cls).canonical_scheme == scheme


def test_hospital_carries_a_secondary_scheme() -> None:
    assert "us.cms.npi" in canonical_scheme_for("hospital").secondary_schemes


def test_class_with_no_external_scheme_takes_a_surrogate() -> None:
    hoa = canonical_scheme_for("private.hoa")
    assert hoa.is_surrogate
    assert hoa.canonical_scheme is None
    # An unrecognised class also falls through to a surrogate rather than raising.
    unknown = canonical_scheme_for("martian.embassy")
    assert unknown.is_surrogate


def test_exact_class_match_beats_prefix() -> None:
    # university_police is LE (ORI), the university itself is IPEDS — the us.le.
    # prefix must not swallow the exact `university` class.
    assert canonical_scheme_for("us.le.university_police").canonical_scheme == "us.fbi.ori"
    assert canonical_scheme_for("university").canonical_scheme == "us.ipeds.unitid"


# --- SIG-IDENT-007: Wikidata recorded but not depended-on for US LE ----------


def test_wikidata_is_not_reliable_for_us_le_but_is_for_vendors() -> None:
    assert wikidata_reliable_for("us.le.sheriff") is False
    assert wikidata_reliable_for("us.le.municipal_police") is False
    assert wikidata_reliable_for("vendor") is True
    assert wikidata_reliable_for("data_broker") is True
    # Wikidata is never the *canonical* scheme for a US-LE class.
    assert canonical_scheme_for("us.le.sheriff").canonical_scheme != "wikidata.qid"


# --- SIG-IDENT-033: the SIG↔external crosswalk -------------------------------


def test_sig_external_crosswalk_is_deterministic_and_sorted() -> None:
    entities = [
        ("sig:organization:b", identifier_set([("us.fbi.ori", "TX0570000")])),
        (
            "sig:organization:a",
            identifier_set([("us.census.geoid", "4835000"), ("wikidata.qid", "Q1")]),
        ),
    ]
    rows = build_sig_external_crosswalk(entities)
    assert [r.as_dict() for r in rows] == [
        {"sig_id": "sig:organization:a", "scheme": "us.census.geoid", "value": "4835000"},
        {"sig_id": "sig:organization:a", "scheme": "wikidata.qid", "value": "Q1"},
        {"sig_id": "sig:organization:b", "scheme": "us.fbi.ori", "value": "TX0570000"},
    ]
    # Byte-stable across runs: same input, same order.
    assert build_sig_external_crosswalk(entities) == rows


# --- SIG-IDENT-034: the ORI9 → GEOID crosswalk -------------------------------


def test_ori_geoid_crosswalk_validates_both_sides() -> None:
    rows = build_ori_geoid_crosswalk([("TX0570000", "4835000")])
    assert rows == [{"ori9": "TX0570000", "geoid": "4835000", "geoid_level": "place"}]


def test_ori_geoid_crosswalk_rejects_a_malformed_ori() -> None:
    with pytest.raises(OriValidationError):
        build_ori_geoid_crosswalk([("bad", "4835000")])


def test_ori_geoid_crosswalk_rejects_a_malformed_geoid() -> None:
    with pytest.raises(GeoidValidationError):
        build_ori_geoid_crosswalk([("TX0570000", "48")])  # wrong width for place


# --- SIG-IDENT-033/034: the licence gate ------------------------------------


def _rights(source_id: str, *, redistributable: bool, spdx: str = "CC-BY-4.0") -> RightsRecord:
    return RightsRecord(
        source_id=source_id,
        spdx=spdx,
        attribution=f"{source_id} attribution",
        redistributable=redistributable,
        derivative_permitted=True,
        terms_url=f"https://example.org/{source_id}",
        retrieval_date=date(2026, 1, 1),
    )


def test_crosswalk_publishes_when_all_rights_permit() -> None:
    rows = build_ori_geoid_crosswalk([("TX0570000", "4835000")])
    got = export_crosswalk(rows, rights=[_rights("fbi_cde", redistributable=True)])
    assert got == rows


def test_crosswalk_fails_closed_on_a_non_redistributable_source() -> None:
    rows = build_ori_geoid_crosswalk([("TX0570000", "4835000")])
    with pytest.raises(licensing.ExportGateClosed):
        export_crosswalk(rows, rights=[_rights("locked", redistributable=False)])
