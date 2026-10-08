# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Part VIII at-rest byte screen (P34.49 / ADR-185, F-406) — invariant
tests over the rules engine: every class screens what the finding/lane names,
a clean capture screens clean, and the output is COUNTS ONLY (a field name,
value, or captured string is an input, never an output)."""

from __future__ import annotations

import json

import pytest
from evidence.screen import (
    F406_ARCGIS_ATTRS,
    F406_EOF_FREETEXT,
    F406_OSM_USERUID,
    PUB002_HOME_ADDRESSES,
    PUB002_PERSON_NAMES,
    PUB002_PERSONAL_IDS,
    PUB002_PLATES,
    PUB002_TRAVEL_HISTORIES,
    ClassRule,
    Rule,
    ScreenDeclaration,
)

from evidence import screen


def _decl(**overrides: tuple[Rule, ...]) -> ScreenDeclaration:
    """A full declaration — every class declared (validate_declaration
    refuses a partial one) with per-class rule overrides for the case."""
    classes = []
    for cid in screen.ALL_CLASSES:
        rules = overrides.get(cid)
        if rules is None:
            # A default no-member, all-captures rule — the override cases
            # scope the class under test.
            rules = (Rule(kind=screen.KIND_FIELDS, fields=("zz_never_matches",)),)
        members = overrides.get(f"{cid}__members", ())  # type: ignore[arg-type]
        classes.append(ClassRule(class_id=cid, rules=tuple(rules), members=tuple(members)))
    decl = ScreenDeclaration(classes=tuple(classes))
    screen.validate_declaration(decl)
    return decl


def _scan(
    blob: bytes, source_id: str = "camreg_x", media_type: str = "application/json", **overrides
) -> dict[str, int]:
    return screen.screen_blob(
        blob, source_id=source_id, media_type=media_type, decl=_decl(**overrides)
    )


def _j(obj) -> bytes:
    return json.dumps(obj).encode()


# --- declaration validation -----------------------------------------------------


def test_declaration_refuses_an_unknown_class() -> None:
    decl = ScreenDeclaration(
        classes=tuple(
            ClassRule(
                class_id=("BOGUS" if cid == "I7-S1" else cid),
                rules=(Rule(kind=screen.KIND_FIELDS, fields=("x",)),),
            )
            for cid in screen.ALL_CLASSES
        )
    )
    with pytest.raises(ValueError, match="not a declared class"):
        screen.validate_declaration(decl)


def test_declaration_refuses_a_missing_class() -> None:
    decl = ScreenDeclaration(
        classes=tuple(
            ClassRule(class_id=cid, rules=(Rule(kind=screen.KIND_FIELDS, fields=("x",)),))
            for cid in screen.ALL_CLASSES[:-1]
        )
    )
    with pytest.raises(ValueError, match="missing"):
        screen.validate_declaration(decl)


def test_declaration_refuses_an_unknown_value_pattern() -> None:
    classes = [
        ClassRule(
            class_id=cid,
            rules=(
                (Rule(kind=screen.KIND_VALUE_PATTERNS, patterns=("made-up-pattern",)),)
                if cid == "I7-S2"
                else (Rule(kind=screen.KIND_FIELDS, fields=("x",)),)
            ),
        )
        for cid in screen.ALL_CLASSES
    ]
    with pytest.raises(ValueError, match="not implemented"):
        screen.validate_declaration(ScreenDeclaration(classes=tuple(classes)))


# --- F406-OSM-USERUID -------------------------------------------------------------


def test_osm_useruid_flags_out_meta_elements_json() -> None:
    blob = _j(
        {
            "elements": [
                {"type": "node", "id": 1, "user": "x", "uid": 7, "lat": 1.0, "lon": 2.0},
                {"type": "node", "id": 2, "lat": 3.0, "lon": 4.0},
                {"type": "way", "id": 9, "uid": 11, "user": "y"},
            ]
        }
    )
    hits = _scan(
        blob,
        source_id="osm_overpass_us",
        **{
            F406_OSM_USERUID: (
                Rule(kind=screen.KIND_SHAPE, shapes=("json_elements",)),
                Rule(kind=screen.KIND_FIELDS, fields=("user", "uid")),
            )
        },
    )
    assert hits[F406_OSM_USERUID] >= 2


def test_osm_useruid_flags_osm_xml_meta_attributes() -> None:
    blob = b"""<?xml version="1.0"?><osm><node id="1" lat="1" lon="2" user="a" uid="9"/>
    <way id="2" uid="4"/><node id="3" lat="1" lon="1"/></osm>"""
    hits = _scan(
        blob,
        source_id="osm_overpass_us",
        media_type="application/osm+xml",
        **{F406_OSM_USERUID: (Rule(kind=screen.KIND_SHAPE, shapes=("json_elements",)),)},
    )
    assert hits[F406_OSM_USERUID] == 2


def test_osm_useruid_clean_when_no_meta() -> None:
    blob = _j({"elements": [{"type": "node", "id": 1, "lat": 1.0, "lon": 2.0}]})
    hits = _scan(
        blob,
        source_id="osm_overpass_us",
        **{F406_OSM_USERUID: (Rule(kind=screen.KIND_SHAPE, shapes=("json_elements",)),)},
    )
    assert F406_OSM_USERUID not in hits


# --- F406-EOF-FREETEXT -------------------------------------------------------------


def test_eof_freetext_flags_top_search_reasons() -> None:
    blob = _j({"summary": {"top_search_reasons": ["a", "b", "c"], "count": 3}})
    hits = _scan(
        blob,
        source_id="eyes_on_flock",
        **{F406_EOF_FREETEXT: (Rule(kind=screen.KIND_FIELDS, fields=("top_search_reasons",)),)},
        **{"F406-EOF-FREETEXT__members": ("eyes_on_flock*",)},
    )
    assert hits[F406_EOF_FREETEXT] == 1


def test_eof_freetext_member_scoped() -> None:
    blob = _j({"summary": {"top_search_reasons": ["a"]}})
    hits = _scan(
        blob,
        source_id="camreg_x",
        **{F406_EOF_FREETEXT: (Rule(kind=screen.KIND_FIELDS, fields=("top_search_reasons",)),)},
        **{"F406-EOF-FREETEXT__members": ("eyes_on_flock*",)},
    )
    assert F406_EOF_FREETEXT not in hits


# --- F406-ARCGIS-ATTRS --------------------------------------------------------------


def test_arcgis_attrs_flags_editor_tracking_and_contact_fields() -> None:
    blob = _j(
        {
            "fields": [{"name": "OBJECTID"}, {"name": "created_user"}],
            "features": [
                {"attributes": {"OBJECTID": 1, "created_user": "op", "phone": "405-555-0112"}},
                {"attributes": {"OBJECTID": 2, "last_edited_user": "op2"}},
            ],
        }
    )
    hits = _scan(
        blob,
        source_id="camreg_nola_la",
        **{
            F406_ARCGIS_ATTRS: (
                Rule(
                    kind=screen.KIND_SHAPE,
                    shapes=("arcgis_attributes",),
                    fields=("created_user", "last_edited_user", "contact*", "phone"),
                    patterns=("email", "phone"),
                ),
            )
        },
        **{"F406-ARCGIS-ATTRS__members": ("camreg_*",)},
    )
    # 1 schema field + 3 attribute hits (created_user, phone value, last_edited_user)
    assert hits[F406_ARCGIS_ATTRS] == 4


def test_arcgis_attrs_clean_feature_set() -> None:
    blob = _j(
        {
            "features": [
                {"attributes": {"OBJECTID": 1, "NAME": "cam-12", "LAT": 35.0}},
            ]
        }
    )
    hits = _scan(
        blob,
        source_id="camreg_nola_la",
        **{
            F406_ARCGIS_ATTRS: (
                Rule(
                    kind=screen.KIND_SHAPE,
                    shapes=("arcgis_attributes",),
                    fields=("created_user", "last_edited_user"),
                    patterns=("email", "phone"),
                ),
            )
        },
        **{"F406-ARCGIS-ATTRS__members": ("camreg_*",)},
    )
    assert F406_ARCGIS_ATTRS not in hits


# --- I7 lanes ---------------------------------------------------------------------


def test_s1_flags_registrant_fields_on_a_member() -> None:
    blob = _j({"registrant": "x", "camera_owner": "y", "model": "falcon"})
    hits = _scan(
        blob,
        source_id="ring_central",
        **{"I7-S1": (Rule(kind=screen.KIND_FIELDS, fields=("registrant", "camera_owner")),)},
        **{"I7-S1__members": ("*ring*",)},
    )
    assert hits["I7-S1"] == 2


def test_s1_silent_on_a_non_member() -> None:
    blob = _j({"registrant": "x"})
    hits = _scan(
        blob,
        source_id="camreg_x",
        **{"I7-S1": (Rule(kind=screen.KIND_FIELDS, fields=("registrant",)),)},
        **{"I7-S1__members": ("*ring*",)},
    )
    assert "I7-S1" not in hits


def test_s3_aggregate_only_flags_row_level_records() -> None:
    row_level = _j({"rows": [{"a": 1, "b": 2}, {"a": 3, "b": 4}]})
    aggregate = _j({"rows": [{"count": 9}, {"count": 4}]})
    decl_over = {
        "I7-S3": (Rule(kind=screen.KIND_SHAPE, shapes=("row_level",)),),
        "I7-S3__members": ("*311*",),
    }
    assert _scan(row_level, source_id="nyc311_x", **decl_over)["I7-S3"] == 2
    assert "I7-S3" not in _scan(aggregate, source_id="nyc311_x", **decl_over)


def test_s5_flags_officer_fields() -> None:
    blob = _j({"officer_name": "x", "badge_id": "1", "precinct": "2"})
    hits = _scan(
        blob,
        source_id="sfpd_x",
        **{"I7-S5": (Rule(kind=screen.KIND_FIELDS, fields=("officer_name", "badge*")),)},
        **{"I7-S5__members": ("*sfpd*",)},
    )
    assert hits["I7-S5"] == 2


def test_s8_flags_any_row_level_record_on_a_member() -> None:
    blob = _j([{"site": "a", "score": 1}, {"site": "b", "score": 2}])
    hits = _scan(
        blob,
        source_id="shotspotter_x",
        **{"I7-S8": (Rule(kind=screen.KIND_SHAPE, shapes=("row_level",)),)},
        **{"I7-S8__members": ("*shotspotter*",)},
    )
    assert hits["I7-S8"] == 2


# --- SIG-PUB-002 categories ----------------------------------------------------------


def test_pub002_plates_flags_plate_fields() -> None:
    blob = _j({"plate": "ABC1234", "model": "cam"})
    hits = _scan(
        blob,
        **{
            PUB002_PLATES: (
                Rule(kind=screen.KIND_FIELDS, fields=("plate", "plate_number", "vrm")),
                Rule(
                    kind=screen.KIND_VALUE_PATTERNS,
                    patterns=("plate",),
                    fields=("plate*", "*_plate"),
                ),
            )
        },
    )
    assert hits[PUB002_PLATES] >= 1


def test_pub002_plate_shape_scoped_to_plate_named_fields() -> None:
    # A plate-shaped token under a generic key never fires the value pattern.
    blob = _j({"ticket_code": "ABC1234"})
    hits = _scan(
        blob,
        **{
            PUB002_PLATES: (
                Rule(kind=screen.KIND_FIELDS, fields=("plate",)),
                Rule(
                    kind=screen.KIND_VALUE_PATTERNS,
                    patterns=("plate",),
                    fields=("plate*",),
                ),
            )
        },
    )
    assert PUB002_PLATES not in hits


def test_pub002_person_names_org_context_excluded() -> None:
    blob = _j({"organization": "x", "name": "y"})
    hits = _scan(
        blob,
        **{PUB002_PERSON_NAMES: (Rule(kind=screen.KIND_FIELDS, fields=("name", "first_name")),)},
    )
    assert PUB002_PERSON_NAMES not in hits


def test_pub002_person_names_flagged() -> None:
    blob = _j({"first_name": "x", "camera": "y"})
    hits = _scan(
        blob, **{PUB002_PERSON_NAMES: (Rule(kind=screen.KIND_FIELDS, fields=("first_name",)),)}
    )
    assert hits[PUB002_PERSON_NAMES] == 1


def test_pub002_home_address_and_ids_and_history() -> None:
    blob = _j({"home_address": "x", "ssn": "y", "trip_log": "z"})
    hits = _scan(
        blob,
        **{
            PUB002_HOME_ADDRESSES: (Rule(kind=screen.KIND_FIELDS, fields=("home_address",)),),
            PUB002_PERSONAL_IDS: (Rule(kind=screen.KIND_FIELDS, fields=("ssn",)),),
            PUB002_TRAVEL_HISTORIES: (Rule(kind=screen.KIND_FIELDS, fields=("trip*",)),),
        },
    )
    assert hits[PUB002_HOME_ADDRESSES] == 1
    assert hits[PUB002_PERSONAL_IDS] == 1
    assert hits[PUB002_TRAVEL_HISTORIES] == 1


# --- counts-only contract + binary payloads -------------------------------------------


def test_binary_payload_is_scanned_not_opened() -> None:
    hits = _scan(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, media_type="image/png")
    assert hits == {}


def test_malformed_json_counts_scanned_no_hits() -> None:
    hits = _scan(b"{not valid json", media_type="application/json")
    assert hits == {}


def test_report_is_counts_only() -> None:
    """The engine returns ints — never the field name, value, or string that
    fired the rule (the counts-only contract, ADR-185)."""
    blob = _j({"elements": [{"type": "node", "user": "SECRETNAME", "uid": 999}]})
    hits = _scan(
        blob,
        source_id="osm_overpass_us",
        **{F406_OSM_USERUID: (Rule(kind=screen.KIND_SHAPE, shapes=("json_elements",)),)},
    )
    assert isinstance(hits[F406_OSM_USERUID], int)
    rendered = json.dumps(hits)
    assert "SECRETNAME" not in rendered and "999" not in rendered
