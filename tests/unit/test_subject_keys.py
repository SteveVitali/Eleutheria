# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit contract for the subject-key pin registry (P35.24 / ADR-212).

Pins the DECLARED grammar — mint, parse (current/legacy/constituent), split,
per-capture uniqueness, sink-side validation — never the registry's living
membership values beyond the six families declared by this ticket.
"""

from __future__ import annotations

import pytest
from db.subject_keys import (
    SubjectKeyCollision,
    SubjectKeyError,
    assert_unique_within,
    mint_subject_key,
    parse_subject_key,
    pin_for_subject,
    pins,
    registry_version,
    split_subject_key,
    validate_subject_value,
)


def test_registry_declares_the_pinned_families() -> None:
    assert registry_version() == "sig.subject-key-pins/1"
    families = {pin.pin_id: pin.family for pin in pins()}
    assert families == {
        "traffic_camera": "traffic_camera:",
        "atlas_agency": "atlas:",
        "data_driven_agency": "data_driven:agency:",
        "contract": "contract:",
        "agenda_item": "agenda_item:",
        "agenda_document": "agenda_document:",
    }


def test_mint_produces_the_declared_shapes() -> None:
    assert (
        mint_subject_key("traffic_camera", source_id="il", target_id="t1", camera_ref="42")
        == "traffic_camera:il:t1:42"
    )
    assert (
        mint_subject_key("atlas_agency", state="CA", agency="Fresno PD", family="alpr")
        == "atlas:us.state_abbr:CA:Fresno PD:alpr"
    )
    # absent scope renders the declared sentinel, never an empty segment
    assert (
        mint_subject_key("atlas_agency", state=None, agency="X PD")
        == "atlas:us.state_abbr:unscoped:X PD"
    )
    assert (
        mint_subject_key("data_driven_agency", state="TX", agency_id="TX0570000")
        == "data_driven:agency:us.state_abbr:TX:TX0570000"
    )
    # a scoped platform mints the tenant segment; a single-tenant source omits it
    assert (
        mint_subject_key("contract", source_id="legistar", tenant_id="okc", external_id="C-1")
        == "contract:legistar:tenant:okc:C-1"
    )
    assert (
        mint_subject_key("contract", source_id="usaspending", external_id="X")
        == "contract:usaspending:X"
    )


def test_mint_refuses_missing_empty_or_colon_fields() -> None:
    with pytest.raises(SubjectKeyError):
        mint_subject_key("traffic_camera", source_id="il", target_id="t1")
    with pytest.raises(SubjectKeyError):
        mint_subject_key("traffic_camera", source_id="il", target_id="t1", camera_ref="")
    with pytest.raises(SubjectKeyError):
        mint_subject_key("traffic_camera", source_id="il", target_id="t1", camera_ref="a:b")
    with pytest.raises(SubjectKeyError):
        mint_subject_key("no_such_pin", x="1")


def test_parse_accepts_current_legacy_and_constituent_shapes() -> None:
    cur = parse_subject_key("atlas:us.state_abbr:CA:Fresno PD:alpr")
    assert cur is not None and cur.key_version == 2 and not cur.constituent
    assert dict(cur.fields) == {"state": "CA", "agency": "Fresno PD", "family": "alpr"}

    legacy = parse_subject_key("atlas:Fresno PD:alpr")
    assert legacy is not None and legacy.key_version == 1
    assert dict(legacy.fields) == {"agency": "Fresno PD", "family": "alpr"}

    slug = parse_subject_key("contract:okc-flock-c241032")
    assert slug is not None and slug.key_version == 1
    assert dict(slug.fields) == {"external_id": "okc-flock-c241032"}

    leg2 = parse_subject_key("contract:legistar:C-9")
    assert leg2 is not None and leg2.key_version == 1
    assert dict(leg2.fields) == {"source_id": "legistar", "external_id": "C-9"}

    const = parse_subject_key("traffic_camera:s:t:r:s0123456789ab")
    assert const is not None and const.constituent and const.discriminator == "0123456789ab"
    assert dict(const.fields) == {"source_id": "s", "target_id": "t", "camera_ref": "r"}


def test_parse_rejects_malformed_pinned_values() -> None:
    for bad in (
        "traffic_camera:a:b",  # missing ref
        "traffic_camera:a:b:",  # empty segment
        "traffic_camera:a:b:c:d",  # arity 4 without s<digest> suffix
        "atlas:us.state_abbr",  # scope literal only
        "data_driven:agency:",  # empty
        "contract:a:b:c",  # arity 3 — no declared shape
        "agenda_item:a:b",  # arity 2 — no declared shape
    ):
        assert parse_subject_key(bad) is None, bad


def test_unpinned_families_are_outside_the_grammar() -> None:
    assert pin_for_subject("osm:node/1") is None
    assert parse_subject_key("osm:node/1") is None
    # sink-side validation only constrains PINNED families
    assert validate_subject_value("osm:node/1") is None
    assert validate_subject_value("traffic_camera:a:b") is not None
    assert validate_subject_value("traffic_camera:a:b:c") is None


def test_assert_unique_within_fails_closed_on_collision() -> None:
    assert_unique_within(["traffic_camera:a:b:1", "traffic_camera:a:b:2"])
    with pytest.raises(SubjectKeyCollision) as exc:
        assert_unique_within(["traffic_camera:a:b:1", "traffic_camera:a:b:1"])
    assert "traffic_camera:a:b:1" in str(exc.value)


def test_split_subject_key_derives_constituents() -> None:
    base = parse_subject_key("traffic_camera:il:t1:42")
    assert base is not None
    a = split_subject_key(base, "35.0,-97.0")
    b = split_subject_key(base, "35.5,-97.5")
    assert a != b and a.startswith("traffic_camera:il:t1:42:s")
    # constituents are deterministic (same evidence → same key → +0 reruns)
    assert split_subject_key(base, "35.0,-97.0") == a
    # the constituent still parses under the pin
    assert parse_subject_key(a) is not None and parse_subject_key(a).constituent


def test_split_subject_key_rescopes_legacy_keys() -> None:
    legacy = parse_subject_key("atlas:Fresno PD")
    assert legacy is not None
    out = split_subject_key(legacy, "CA")
    assert out == "atlas:us.state_abbr:CA:Fresno PD"
    contract = parse_subject_key("contract:legistar:C-9")
    assert contract is not None
    assert split_subject_key(contract, "okc") == "contract:legistar:tenant:okc:C-9"


def test_sink_validation_is_the_shared_derivation() -> None:
    """A value minted by the registry always validates — the emitter and the
    sink read ONE grammar (CONF-03b: same derivation on both sides)."""
    for fields in (
        dict(pin="traffic_camera", kw=dict(source_id="s", target_id="t", camera_ref="r")),
        dict(pin="atlas_agency", kw=dict(state="CA", agency="A", family="f")),
        dict(pin="data_driven_agency", kw=dict(state="TX", agency_id="x")),
        dict(pin="contract", kw=dict(source_id="l", tenant_id="t", external_id="e")),
        dict(pin="contract", kw=dict(source_id="u", external_id="e")),
        dict(pin="agenda_item", kw=dict(source_id="l", tenant_id="okc", external_id="e")),
        dict(pin="agenda_document", kw=dict(source_id="l", tenant_id="okc", external_id="e")),
    ):
        assert validate_subject_value(mint_subject_key(fields["pin"], **fields["kw"])) is None
