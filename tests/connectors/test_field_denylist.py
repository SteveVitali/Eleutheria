# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The F-330 Part VIII layer-field denylist (P35.6 / R11-ACQ-01).

F-330's archetypes — the Flock "search results" layer (PLATE + capture time),
the Mark43 "CGPD LPR Hits" layer (PLATE, HOTLIST_REASON, TIMESTAMP, ADDRESS),
the Flower Mound registrant layer (FIRST_NAME, LAST_NAME, ADDRESS1, PHONE,
EMAIL), the Socrata ``red_vrm`` field, and Horizon City's Axon layer
(``owner_firstname`` / ``owner_lastname`` / ``badge_id``) — must every one be
refused, while a clean camera-registry schema (``camid``, ``ROADWAYNAME``,
``Owner``, ``template_name``) passes. The denylist is a *registration*
refusal: a target carrying a denied field never reaches the fetch path.
"""

from __future__ import annotations

import pytest
from connectors.field_denylist import (
    FieldDenylistViolation,
    assert_target_fields_clean,
    denied_match,
    field_violations,
    is_denied,
    target_field_violations,
)

# --- the F-330 archetypes, named field-for-field --------------------------------

F330_DENIED = [
    "PLATE",  # Flock search results + Mark43 hits
    "plate_number",
    "license_plate",
    "red_vrm",  # Socrata red_vrm
    "HOTLIST_REASON",  # Mark43 CGPD LPR Hits
    "hotlist_name",
    "TIMESTAMP_ADDRESS",
    "ADDRESS1",
    "FIRST_NAME",  # Flower Mound registrant layer
    "LAST_NAME",
    "firstName",
    "ownerFirstName",  # Horizon City Axon layer
    "owner_firstname",
    "owner_last_name",
    "badge_id",  # Horizon City officer identity
    "search_reason",  # Flock audit search reason
    "EMAIL",
    "PHONE",
    "phone_number",
    "registrant_name",
    "driver_license",
    "hit_reason",
    "read_record_id",  # Horizon read_record_id — ALPR read record
    "vehicle_name",
    "contact_name",
]


@pytest.mark.parametrize("field", F330_DENIED)
def test_f330_archetype_fields_are_denied(field: str) -> None:
    assert is_denied(field), f"{field}: an F-330 archetype field must be denied"


# --- names the denylist must NOT touch ------------------------------------------

CLEAN_CAMERA_FIELDS = [
    "camid",
    "camera_id",
    "camera_name",
    "ROADWAYNAME",  # 'name' alone is never denied
    "roadway_name",
    "intersection",
    "location_name",
    "comm_status",
    "Owner",  # the layer's publishing agency — an org, not a person field
    "owner_org",
    "agency",
    "template_name",  # 'template' never collides with 'plate'
    "install_date",
    "camera_type",
    "direction",
    "latitude",
    "longitude",
    "OBJECTID",
    "status",
    "description",
    "manufacturer",
]


@pytest.mark.parametrize("field", CLEAN_CAMERA_FIELDS)
def test_clean_registry_fields_are_not_denied(field: str) -> None:
    assert not is_denied(field), f"{field}: a clean camera-registry field was denied"


def test_denied_match_names_the_term() -> None:
    assert denied_match("owner_first_name") == "first name"
    assert denied_match("red_vrm") == "vrm"
    assert denied_match("ROADWAYNAME") is None


def test_field_violations_lists_every_denied_field() -> None:
    hits = field_violations(["camid", "PLATE", "firstName", "status"])
    assert len(hits) == 2
    assert "'PLATE' (denied 'plate')" in hits
    assert "'firstName' (denied 'first name')" in hits


def test_target_row_denied_observed_fields_refuse() -> None:
    row = {
        "id": "flock_search_results",
        "kind": "arcgis_query",
        "observed_fields": ["PLATE", "CAPTURE_TIME", "LOCATION"],
    }
    violations = target_field_violations(row)
    assert violations and any("PLATE" in v for v in violations)
    with pytest.raises(FieldDenylistViolation):
        assert_target_fields_clean(row)


def test_target_row_denied_out_fields_allowlist_refuses() -> None:
    row = {"id": "bad_allow", "kind": "socrata_rows", "out_fields": ["camid", "email"]}
    assert target_field_violations(row)
    with pytest.raises(FieldDenylistViolation):
        assert_target_fields_clean(row)


def test_target_row_clean_schema_passes() -> None:
    row = {
        "id": "clean",
        "kind": "arcgis_query",
        "observed_fields": ["camid", "ROADWAYNAME", "Owner", "OBJECTID"],
        "out_fields": ["camid", "ROADWAYNAME", "OBJECTID"],
    }
    assert target_field_violations(row) == []
    assert_target_fields_clean(row)


def test_non_layer_kinds_are_out_of_scope() -> None:
    """The denylist gates ArcGIS/Socrata targets — not other transports."""
    row = {"id": "doc", "kind": "index_page", "observed_fields": ["plate"]}
    assert target_field_violations(row) == []


def test_committed_targets_carry_no_denied_fields() -> None:
    """F-330 invariant over the registry as committed (registration refusal)."""
    import tomllib
    from pathlib import Path

    for name in ("camera_registry_targets.toml", "dot_511_targets.toml"):
        doc = tomllib.loads((Path("connectors/src/connectors/data") / name).read_text())
        for row in doc.get("targets", []):
            violations = target_field_violations(row)
            assert not violations, f"{name}: target {row.get('id')!r}: {violations}"
