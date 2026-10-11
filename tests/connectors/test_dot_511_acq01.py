# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.6 / ACQ-01 changes to the dot_511 target path.

* **P8-5 `out_fields`:** a target's reviewed field allowlist replaces the
  ``outFields=*`` wildcard so a raw capture holds only allowlisted fields —
  and the object-id field is always present (paging breaks without it).
* **I8 NEW-3:** the reviewed api_allowlist request budget (10/min for
  ``services*.arcgis.com``) reaches every target — a row-level
  ``rate_limit_per_min`` wins; an ArcGIS target on an unlisted host still
  gets the reviewed ArcGIS budget, never unbounded.
* **F-330:** a target whose declared fields hit the denylist is refused by
  ``registry_targets`` itself (belt-and-braces behind the validate/generator
  gates).
"""

from __future__ import annotations

import pytest
from connectors.dot_511 import expand_registry_rows
from connectors.field_denylist import FieldDenylistViolation

_ARCGIS_ROW = {
    "id": "t_arc",
    "kind": "arcgis_query",
    "layer_url": "https://services1.arcgis.com/abc/arcgis/rest/services/L/FeatureServer/0",
    "observed_count": 5,
    "object_id_field": "OBJECTID",
    "state": "DC",
    "agency": "A",
    # P35.15a / PKG-07: expansion refuses a camera-class row without a
    # declared registry-member technology slug.
    "technology": "fixed-camera-ptz",
}

_SOCRATA_ROW = {
    "id": "t_soc",
    "kind": "socrata_rows",
    "layer_url": "https://data.example.gov/resource/aaaa-bbbb.json",
    "observed_count": 5,
    "state": "DC",
    "agency": "A",
    "technology": "fixed-camera-ptz",
}


def test_arcgis_out_fields_replaces_wildcard() -> None:
    row = {**_ARCGIS_ROW, "out_fields": ["camid", "ROADWAYNAME", "status"]}
    (target,) = expand_registry_rows([row])
    assert "outFields=camid%2CROADWAYNAME%2Cstatus%2COBJECTID" in target["url"]
    assert "outFields=%2A" not in target["url"]
    assert target["out_fields"] == ["camid", "ROADWAYNAME", "status"]


def test_arcgis_out_fields_keeps_existing_oid() -> None:
    row = {**_ARCGIS_ROW, "out_fields": "camid,OBJECTID"}
    (target,) = expand_registry_rows([row])
    assert "outFields=camid%2COBJECTID" in target["url"]


def test_arcgis_without_out_fields_keeps_wildcard() -> None:
    """Back-compat: reviewed legacy rows without out_fields behave as before."""
    (target,) = expand_registry_rows([_ARCGIS_ROW])
    assert "outFields=%2A" in target["url"]
    assert "out_fields" not in target


def test_socrata_out_fields_bounds_select() -> None:
    row = {**_SOCRATA_ROW, "out_fields": ["camid", "location"]}
    (target,) = expand_registry_rows([row])
    assert "%24select=camid%2Clocation%2C%3Aid" in target["url"]
    assert "%24select=%2A%2C%3Aid" not in target["url"]


def test_arcgis_allowlist_rate_limit_propagates() -> None:
    """I8 NEW-3 — the services1.arcgis.com 10/min allowlist row reaches the target."""
    (target,) = expand_registry_rows([_ARCGIS_ROW])
    assert target["rate_limit_per_min"] == 10


def test_arcgis_unknown_host_still_gets_reviewed_budget() -> None:
    row = {
        **_ARCGIS_ROW,
        "layer_url": "https://gis.unlisted.gov/arcgis/rest/services/L/MapServer/0",
    }
    (target,) = expand_registry_rows([row])
    assert target["rate_limit_per_min"] == 10  # reviewed ArcGIS budget, never unbounded


def test_row_level_rate_limit_wins() -> None:
    row = {**_ARCGIS_ROW, "rate_limit_per_min": 5}
    (target,) = expand_registry_rows([row])
    assert target["rate_limit_per_min"] == 5


def test_socrata_target_carries_allowlist_rpm_when_listed() -> None:
    (target,) = expand_registry_rows([_SOCRATA_ROW])
    # data.example.gov is not in api_allowlist.toml — no fabricated budget.
    assert "rate_limit_per_min" not in target


def test_denied_fields_refuse_target_expansion() -> None:
    row = {**_ARCGIS_ROW, "observed_fields": ["camid", "PLATE"]}
    with pytest.raises(FieldDenylistViolation):
        expand_registry_rows([row])
    row = {**_SOCRATA_ROW, "out_fields": ["camid", "first_name"]}
    with pytest.raises(FieldDenylistViolation):
        expand_registry_rows([row])


# --- P35.15a / PKG-07: the declared technology slug -------------------------------


def test_target_without_technology_never_expands() -> None:
    """A camera-class target row with no `technology` (or a non-registry slug)
    is refused at expansion — the emit path can never fall back to the legacy
    traffic_camera blanket typing (F-329)."""
    from connectors.dot_511 import TechnologyNotDeclared

    row = {k: v for k, v in _ARCGIS_ROW.items() if k != "technology"}
    with pytest.raises(TechnologyNotDeclared, match="no 'technology' slug"):
        expand_registry_rows([row])
    with pytest.raises(TechnologyNotDeclared, match="not an active member"):
        expand_registry_rows([{**_ARCGIS_ROW, "technology": "invented-slug"}])
    with pytest.raises(TechnologyNotDeclared):
        expand_registry_rows([{**_ARCGIS_ROW, "technology": "camera-fixed-cctv"}])  # retired


def test_expanded_target_carries_declared_technology_and_subtype() -> None:
    (target,) = expand_registry_rows([_ARCGIS_ROW])
    assert target["technology"] == "fixed-camera-ptz"
    assert target["record_kind"] == "fixed-camera-ptz"  # subtype defaults to the slug


def test_traffic_camera_record_kind_needs_a_camera_domain_slug() -> None:
    """`record_kind = "traffic_camera"` is legal only on a target that literally
    declares it AND whose technology is a fixed/PTZ camera — never on ALPR."""
    from connectors.dot_511 import TechnologyNotDeclared

    (target,) = expand_registry_rows([{**_ARCGIS_ROW, "record_kind": "traffic_camera"}])
    assert target["record_kind"] == "traffic_camera"
    with pytest.raises(TechnologyNotDeclared, match="traffic_camera"):
        expand_registry_rows(
            [{**_ARCGIS_ROW, "technology": "alpr-fixed", "record_kind": "traffic_camera"}]
        )
    with pytest.raises(TechnologyNotDeclared):
        expand_registry_rows(
            [{**_ARCGIS_ROW, "record_kind": "fixed-camera-cctv"}]
        )  # a divergent slug is not a valid subtype declaration
