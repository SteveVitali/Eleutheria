# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.36 (R11-K13-TX-12 / J3 §6.9, SIG-TRANSP-020) — the raw-ok archive lane.

* the lane × Part VIII × bytes verdict table — only ``raw-ok`` serves, the
  sealed classes never do, and the field-screen classes serve only the
  re-serialised derivative (a NEW capture, never the parent's bytes);
* the Part VIII byte screen is fail-closed — a screen hit or an unparseable
  reserialisation refuses the object, never a bypass;
* ``raw/index.json`` is ``sig.raw-archive-index/1`` — objects carry digest +
  sha256 + licence + kind; skips carry digest + reason class only;
* ``served_href_map`` mints the view-original locators — a redacted object's
  parent resolves the derivative, never the parent's bytes.
"""

from __future__ import annotations

import json

import pytest
from evidence.digest import multihash
from evidence.screen import KIND_FIELDS, ClassRule, Rule, ScreenDeclaration
from exports.raw_archive import (
    INDEX_SCHEMA,
    MAX_OBJECT_BYTES,
    REASON_CLASSES,
    RawArchiveError,
    build_archive,
    decide_capture,
    public_href,
    reserialisation_record,
    reserialise_fields,
    served_href_map,
)

_DECL = ScreenDeclaration(
    classes=tuple(
        ClassRule(class_id=cid, rules=(Rule(kind=KIND_FIELDS, fields=fields),))
        for cid, fields in (
            ("F406-OSM-USERUID", ("user", "uid")),
            ("F406-EOF-FREETEXT", ("top_search_reasons",)),
            ("F406-ARCGIS-ATTRS", ("created_user", "last_edited_user", "contact_email")),
            ("I7-S1", ("plate", "vin")),
            ("I7-S2", ("created_user", "editor")),
            ("I7-S3", ("request_text",)),
            ("I7-S4", ("home_address",)),
            ("I7-S5", ("officer_name",)),
            ("I7-S6", ("free_text",)),
            ("I7-S7", ("person_id",)),
            ("I7-S8", ("contact_phone",)),
            ("I7-S9", ("registrant",)),
            ("PUB002-PLATES", ("plate_number",)),
            ("PUB002-HOME-ADDRESSES", ("home_address",)),
            ("PUB002-PERSON-NAMES", ("registrant", "first_name", "last_name")),
            ("PUB002-PERSONAL-IDS", ("ssn", "driver_license")),
            ("PUB002-TRAVEL-HISTORIES", ("trip_history",)),
        )
    )
)


def _cap(**kw) -> dict:
    base = {
        "capture_id": "cap-1",
        "artifact_id": "art-1",
        "source_id": "src_raw",
        "content_digest": "b3deadbeef",
        "byte_size": 128,
        "media_type": "application/json",
        "retrieved_at": "2026-11-01T00:00:00Z",
        "storage_tier": "public",
        "license": "CC0-1.0",
    }
    base.update(kw)
    return base


def _bytes(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


# --- the verdict table -------------------------------------------------------


def test_decide_only_raw_ok_serves() -> None:
    cap = _cap()
    for lane in ("derived-only", "link-only", "restricted", "unknown", "", None):
        d = decide_capture(cap, lane=lane, part_viii_class=None)
        assert d.verdict == "never" and d.reason_class == "lane_not_raw_ok"
    d = decide_capture(cap, lane="raw-ok", part_viii_class=None)
    assert d.verdict == "serve"


def test_decide_sealed_classes_never() -> None:
    for p8 in ("P8-1", "P8-2", "P8-4"):
        d = decide_capture(_cap(), lane="raw-ok", part_viii_class=p8)
        assert d.verdict == "never" and d.reason_class == "part_viii_sealed_class"


def test_decide_field_screen_classes_reserialise() -> None:
    for p8 in ("P8-5", "P8-6", "P8-8"):
        d = decide_capture(_cap(), lane="raw-ok", part_viii_class=p8)
        assert d.verdict == "reserialise"


def test_decide_synthetic_and_no_bytes_never() -> None:
    d = decide_capture(
        _cap(capture_classification="synthetic"), lane="raw-ok", part_viii_class=None
    )
    assert d.verdict == "never" and d.reason_class == "synthetic_capture"
    d = decide_capture(
        _cap(byte_size=0, storage_tier="restricted"),
        lane="raw-ok",
        part_viii_class=None,
    )
    assert d.verdict == "never" and d.reason_class == "bytes_not_stored"


def test_decide_oversize_links_out() -> None:
    d = decide_capture(_cap(byte_size=MAX_OBJECT_BYTES + 1), lane="raw-ok", part_viii_class=None)
    assert d.verdict == "link_out" and d.reason_class == "over_object_cap"


def test_reason_classes_are_closed() -> None:
    d = decide_capture(_cap(), lane="restricted", part_viii_class=None)
    assert d.reason_class in REASON_CLASSES


# --- reserialisation ----------------------------------------------------------


def test_reserialise_drops_declared_fields() -> None:
    blob = _bytes({"features": [{"attributes": {"name": "cam-1", "created_user": "x"}}]})
    out, dropped = reserialise_fields(
        blob, media_type="application/json", drop_fields=frozenset({"created_user"})
    )
    doc = json.loads(out)
    assert doc == {"features": [{"attributes": {"name": "cam-1"}}]}
    assert dropped == ("created_user",)


def test_reserialise_refuses_non_json() -> None:
    with pytest.raises(RawArchiveError):
        reserialise_fields(b"\x89PNG\r\n", media_type="image/png", drop_fields=frozenset({"user"}))


def test_reserialise_refuses_empty_drop_set_and_zero_hits() -> None:
    with pytest.raises(RawArchiveError):
        reserialise_fields(b"{}", media_type="application/json", drop_fields=frozenset())
    with pytest.raises(RawArchiveError):
        reserialise_fields(
            _bytes({"a": 1}), media_type="application/json", drop_fields=frozenset({"zzz"})
        )


def test_reserialisation_record_shape() -> None:
    rec = reserialisation_record(
        parent_digest="p1",
        parent_capture_id="cap-1",
        derivative_digest="d1",
        dropped_fields=["created_user"],
        screen_classes=["F406-ARCGIS-ATTRS"],
        source_id="src_raw",
    )
    assert rec["schema"] == "sig.raw-reserialisation/1"
    assert rec["redaction_method"] == "field-allowlist"
    assert rec["parent_digest"] == "p1" and rec["derivative_digest"] == "d1"


# --- build_archive -------------------------------------------------------------


def _store(mapping: dict[str, bytes]):
    def read(digest: str) -> bytes | None:
        return mapping.get(digest)

    return read


def test_build_serves_raw_ok_clear(tmp_path) -> None:
    blob = _bytes({"records": [1, 2, 3]})
    digest = multihash(blob)
    cap = _cap(content_digest=digest)
    result = build_archive(
        [cap],
        lanes={"src_raw": {"lane": "raw-ok", "part_viii_class": "clear"}},
        read_bytes=_store({digest: blob}),
        decl=_DECL,
        out_dir=tmp_path,
    )
    assert len(result.entries) == 1 and not result.skipped
    entry = result.entries[0]
    assert entry.path == f"raw/{digest}" and entry.kind == "original"
    assert (tmp_path / "raw" / digest).read_bytes() == blob
    index = json.loads((tmp_path / "raw" / "index.json").read_bytes())
    assert index["schema"] == INDEX_SCHEMA
    assert index["objects"][0]["digest"] == digest
    assert index["counts"]["objects"] == 1 and index["counts"]["skipped"] == 0


def test_build_never_serves_non_raw_ok(tmp_path) -> None:
    cap = _cap()
    result = build_archive(
        [cap],
        lanes={"src_raw": {"lane": "derived-only", "part_viii_class": "clear"}},
        read_bytes=_store({}),
        decl=_DECL,
        out_dir=tmp_path,
    )
    assert not result.entries
    assert result.skipped[0].reason_class == "lane_not_raw_ok"


def test_build_screen_hit_refuses(tmp_path) -> None:
    blob = _bytes({"user": "osm-user", "uid": 7, "way": 1})
    digest = multihash(blob)
    cap = _cap(content_digest=digest)
    result = build_archive(
        [cap],
        lanes={"src_raw": {"lane": "raw-ok", "part_viii_class": "clear"}},
        read_bytes=_store({digest: blob}),
        decl=_DECL,
        out_dir=tmp_path,
    )
    assert not result.entries
    assert result.skipped[0].reason_class == "part_viii_screen_hit"
    assert result.skipped[0].screen_classes


def test_build_p8_field_screen_emits_derivative(tmp_path) -> None:
    blob = _bytes({"features": [{"attributes": {"created_user": "ed", "name": "c"}}]})
    digest = multihash(blob)
    cap = _cap(content_digest=digest)
    result = build_archive(
        [cap],
        lanes={"src_raw": {"lane": "raw-ok", "part_viii_class": "P8-5"}},
        read_bytes=_store({digest: blob}),
        decl=_DECL,
        out_dir=tmp_path,
    )
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.kind == "redacted" and entry.parent_digest == digest
    assert entry.redaction_method == "field-allowlist"
    served = (tmp_path / "raw" / entry.digest).read_bytes()
    assert b"created_user" not in served and b"ed" not in served
    assert len(result.reserialisations) == 1
    assert result.reserialisations[0]["parent_digest"] == digest


def test_build_missing_bytes_and_no_decl_fail_closed(tmp_path) -> None:
    cap = _cap(content_digest="gone")
    result = build_archive(
        [cap],
        lanes={"src_raw": {"lane": "raw-ok", "part_viii_class": "clear"}},
        read_bytes=_store({}),
        decl=_DECL,
        out_dir=tmp_path,
    )
    assert result.skipped[0].reason_class == "bytes_unavailable"
    with pytest.raises(RawArchiveError):
        build_archive(
            [cap],
            lanes={"src_raw": {"lane": "raw-ok", "part_viii_class": "clear"}},
            read_bytes=_store({"gone": b"{}"}),
            decl=None,
            out_dir=tmp_path / "x",
        )


def test_served_href_map_resolves_parent_to_derivative(tmp_path) -> None:
    blob = _bytes({"created_user": "ed", "name": "c"})
    digest = multihash(blob)
    result = build_archive(
        [_cap(content_digest=digest)],
        lanes={"src_raw": {"lane": "raw-ok", "part_viii_class": "P8-5"}},
        read_bytes=_store({digest: blob}),
        decl=_DECL,
        out_dir=tmp_path,
    )
    hrefs = served_href_map(result.entries, base_url="https://files.example")
    deriv = result.entries[0].digest
    assert hrefs[digest] == f"https://files.example/raw/{deriv}"
    assert hrefs[deriv] == f"https://files.example/raw/{deriv}"
    assert public_href("d1", base_url="https://files.example/") == "https://files.example/raw/d1"
