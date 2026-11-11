# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.33 (K7 WX-03, D-K7-2 = the lane) — the watch lane's deterministic core."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ops import watch_lane as W


def _payload() -> dict:
    return {
        "schema": "sig/watch/2",
        "as_of": "2026-11-10",
        "generated_at": "2026-11-10T07:30:00Z",
        "build": {"ruleset": "watch-derivation/1", "windows": {"list_days": 90}},
        "coverage": {
            "monitored": {
                "tenants_registered": 3,
                "tenant_jurisdictions": ["City of Seattle, WA"],
            },
            "places": [
                {
                    "key": "iso3166-2:US-WA",
                    "slug": "usa/wa",
                    "items": 1,
                    "kinds": ["agenda_item"],
                    "last_checked": "2026-11-10T07:30:00Z",
                },
                {
                    "key": "iso3166-2:US-TX",
                    "slug": "usa/tx",
                    "items": 0,
                    "kinds": [],
                    "last_checked": "2026-11-10T07:30:00Z",
                },
            ],
            "items_total": 2,
            "by_kind": {"agenda_item": 1, "contract_expiry": 1},
            "last_checked": "2026-11-10T07:30:00Z",
        },
        "items": [
            {
                "schema": "sig.watch-item/1",
                "handle": "W-usa-wa-agenda-cb-121279-7k2q",
                "title": "Seattle City Council: agenda item CB 121279 (contract notice)",
                "kind": "agenda_item",
                "date": "2026-11-14",  # future-ok: synthetic: the fixture alert date the lane renders
                "date_kind": "meeting",
                "date_certainty": "stated",
                "timeline": [{"kind": "meeting", "date": "2026-11-14",  # future-ok: synthetic: the fixture alert date the lane renders  # future-ok: synthetic: the fixture alert date the lane renders "claim_id": "claim-1"}],
                "place": {"key": "iso3166-2:US-WA", "chain": ["iso3166-1:US", "iso3166-2:US-WA"]},
                "body": "Seattle City Council",
                "subjects": ["agenda_item:legistar:seattle_wa:CB 121279"],
                "technology": [{"id": "alpr", "label": "ALPR"}],
                "vendor": [],
                "status": "upcoming",
                "what_you_can_do": "The listed body may act on this item.",
                "evidence": [
                    {
                        "claim_id": "claim-1",
                        "predicate": "meeting_date",
                        "source_id": "legistar",
                        "upstream": {"status": "full_url", "url": "https://seattle.legistar.com/x"},
                    }
                ],
                "contested": False,
                "tasks": [{"task_id": "T-1", "task_type": "renewal_terms", "status": "open"}],
                "first_seen": "2026-11-09",
                "last_checked": "2026-11-10T07:30:00Z",
                "source_ids": ["legistar"],
            },
            {
                "schema": "sig.watch-item/1",
                "handle": "W-unplaced-expiry-abcd-1q2w",
                "title": "Contract ends (latest possible end)",
                "kind": "contract_expiry",
                "date": "2027-02-01",  # future-ok: synthetic: the fixture expiry date the lane renders
                "date_kind": "expiry",
                "date_certainty": "upper_bound",
                "timeline": [],
                "place": {"key": None, "chain": []},
                "body": None,
                "subjects": ["contract:src:x"],
                "technology": [],
                "vendor": [],
                "status": "upcoming",
                "what_you_can_do": "The contract's renewal clause can be requested.",
                "evidence": [
                    {
                        "claim_id": "claim-2",
                        "predicate": "end_date",
                        "source_id": "okc_procurement",
                        "upstream": {"status": "withheld_by_policy"},
                    }
                ],
                "contested": True,
                "tasks": [],
                "first_seen": "2026-11-01",
                "last_checked": "2026-11-10T07:30:00Z",
                "source_ids": ["okc_procurement"],
            },
        ],
    }


def _lane(payload=None):
    return W.build_watch_lane(
        payload=payload or _payload(),
        release={"id": "sig-2026-11-01-abcdef", "as_of_world": "2026-11-01"},
        lane_time=datetime(2026, 11, 10, 7, 30, tzinfo=UTC),
    )


def test_payload_parse_fails_closed_on_schema(tmp_path: Path) -> None:
    bad = tmp_path / "watch.json"
    bad.write_text(json.dumps({"schema": "sig/watch/1", "items": []}))
    with pytest.raises(W.WatchLaneError):
        W.load_watch_payload(bad)


def test_payload_parse_fails_closed_on_unknown_kind() -> None:
    doc = _payload()
    doc["items"][0]["kind"] = "martian_landing"
    with pytest.raises(W.WatchLaneError, match="unknown watch kind"):
        W.check_watch_payload(doc)


def test_payload_parse_fails_closed_on_duplicate_handle() -> None:
    doc = _payload()
    doc["items"].append(dict(doc["items"][0]))
    with pytest.raises(W.WatchLaneError, match="duplicate handle"):
        W.check_watch_payload(doc)


def test_lane_doc_two_clocks() -> None:
    lane = _lane()
    assert lane["schema"] == "sig.watch-lane/1"
    assert lane["lane_time"] == "2026-11-10T07:30:00Z"
    assert lane["payload"]["generated_at"] == "2026-11-10T07:30:00Z"
    assert lane["release"]["id"] == "sig-2026-11-01-abcdef"
    assert lane["counts"]["items_total"] == 2
    assert lane["counts"]["by_kind"] == {"agenda_item": 1, "contract_expiry": 1}
    assert lane["monitored"]["tenants_registered"] == 3
    assert [i["handle"] for i in lane["items_index"]] == sorted(
        [i["handle"] for i in lane["items_index"]],
        key=lambda h: next(i["date"] for i in lane["items_index"] if i["handle"] == h),
    )


def test_heartbeat_shape() -> None:
    hb = W.watch_heartbeat_doc(_lane())
    assert hb["schema"] == "sig.watch-heartbeat/1"
    assert hb["lane_time"] == "2026-11-10T07:30:00Z"
    assert hb["items_total"] == 2
    assert hb["release"]["id"] == "sig-2026-11-01-abcdef"


def test_emit_file_set(tmp_path: Path) -> None:
    payload = _payload()
    written = W.emit_watch_files(payload, _lane(payload), tmp_path)
    names = set(written)
    assert "watch/state.json" in names
    assert "watch/lane.json" in names
    assert "watch/watch.json" in names
    assert "watch/index.html" in names
    assert "watch/archive/2026-11-10.json" in names
    assert "watch/place/usa/wa/index.html" in names
    assert "watch/place/usa/tx/index.html" in names  # zero-item place, with coverage
    assert "watch/place/unplaced/index.html" in names
    assert "watch/item/W-usa-wa-agenda-cb-121279-7k2q/index.html" in names
    assert "watch/item/W-unplaced-expiry-abcd-1q2w/index.html" in names


def test_index_shows_both_clocks(tmp_path: Path) -> None:
    payload = _payload()
    W.emit_watch_files(payload, _lane(payload), tmp_path)
    html = (tmp_path / "watch/index.html").read_text()
    assert "Watch checked 2026-11-10T07:30:00Z" in html
    assert "sig-2026-11-01-abcdef" in html
    assert "data as of" in html
    assert "Seattle City Council: agenda item CB 121279" in html
    assert "SIG checks 3 registered agenda/procurement tenants" in html


def test_upper_bound_never_labelled_deadline(tmp_path: Path) -> None:
    payload = _payload()
    W.emit_watch_files(payload, _lane(payload), tmp_path)
    html = (tmp_path / "watch/item/W-unplaced-expiry-abcd-1q2w/index.html").read_text()
    assert "latest possible date" in html
    assert "the real deadline may be earlier" in html
    assert "deadline (" not in html
    # the contested marker is on the item
    assert "≠" in html
    # a withheld upstream renders the named absence, never a link
    assert (
        "not publishable under the source&#x27;s terms" in html
        or "not publishable under the source's terms" in html
    )
    assert "withheld" not in html.lower().replace("withheld_by_policy", "")


def test_empty_place_carries_coverage(tmp_path: Path) -> None:
    payload = _payload()
    W.emit_watch_files(payload, _lane(payload), tmp_path)
    html = (tmp_path / "watch/place/usa/tx/index.html").read_text()
    assert "none found" in html
    assert "SIG checks" in html
    assert "research gap" not in html


def test_no_script_anywhere(tmp_path: Path) -> None:
    payload = _payload()
    payload["items"][0]["title"] = "x<script>alert(1)</script>"
    written = W.emit_watch_files(payload, _lane(payload), tmp_path)
    # payload text is escaped — the literal tag never reaches an HTML file
    for rel, p in written.items():
        if rel.endswith(".html"):
            assert b"<script" not in p.read_bytes()
    # and the publish-set gate fails closed if a literal ever did appear
    with pytest.raises(W.WatchLaneError, match="script"):
        W._check_publish_set({"watch/x.html": "<html><script>x</script></html>"})


def test_archive_append_only_refuses_drift(tmp_path: Path) -> None:
    payload = _payload()
    W.emit_watch_files(payload, _lane(payload), tmp_path)
    other = W.build_watch_lane(
        payload=payload,
        release=None,
        lane_time=datetime(2026, 11, 10, 8, 0, tzinfo=UTC),
    )
    with pytest.raises(W.WatchLaneError, match="append-only"):
        W.emit_watch_files(payload, other, tmp_path)


def test_lane_owns_object_scope() -> None:
    assert W.lane_owns_object("watch/state.json")
    assert W.lane_owns_object("watch/index.html")
    assert W.lane_owns_object("watch/place/usa/tx/index.html")
    assert W.lane_owns_object("watch/item/W-x/index.html")
    assert not W.lane_owns_object("watch/archive/2026-11-10.json")
    assert not W.lane_owns_object("watch/item/W-x/citations.txt")
    assert not W.lane_owns_object("watch/kind/agenda_item/index.html")
    assert not W.lane_owns_object("watch/feeds/all.opml")
    assert not W.lane_owns_object("watch/page/2/index.html")
    assert not W.lane_owns_object("watch/tx.ics")
    assert not W.lane_owns_object("status/state.json")


def test_emit_is_deterministic(tmp_path: Path) -> None:
    payload = _payload()
    lane = _lane(payload)
    a = W.emit_watch_files(payload, lane, tmp_path / "a")
    b = W.emit_watch_files(payload, lane, tmp_path / "b")
    assert set(a) == set(b)
    for rel in a:
        assert (tmp_path / "a" / rel).read_bytes() == (tmp_path / "b" / rel).read_bytes()
