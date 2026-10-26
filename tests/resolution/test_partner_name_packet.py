# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.21 partner-name disposition packet (D-P32.3-1, SIG-ENG-042).

The packet generator turns the read-only ``partner-name-audit`` report into
the committed OP-15 disposition packet: N counted with its query + digest,
the per-option blast radii, and per-key rows that carry ids + digests +
counts only (Part VIII — no registrant names). A vacuous (0-key) report is
refused loud; a queued run emits a ``prepared_not_executed`` packet that
fabricates nothing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from resolution.partner_name_audit import _REPORT_SQL, name_scope_report
from resolution.partner_name_packet import (
    OBLIGATION_ID,
    PACKET_SCHEMA,
    PartnerNamePacketError,
    build_packet,
    build_queued_packet,
    keys_csv,
    load_report,
    packet_sha256,
    query_sha256,
    render_markdown,
    report_sha256,
    write_packet,
)

# The fixture names a committed packet must never carry (Part VIII).
_FIXTURE_NAMES = (
    "city of example falls",
    "washington state department of transportation",
    "City of Example Falls",
    "Washington State Department of Transportation",
)

_REPORT_ROWS = [
    {
        "name_key": "city of example falls",
        "entity_id": "e-fixture-1",
        "label": "City of Example Falls",
        "source_id": "govspend",
        "predicate_id": "buyer",
    },
    {
        "name_key": "washington state department of transportation",
        "entity_id": "e-fixture-2",
        "label": "Washington State Department of Transportation",
        "source_id": "usaspending",
        "predicate_id": "recipient",
    },
    {
        "name_key": "washington state department of transportation",
        "entity_id": "e-fixture-2",
        "label": "Washington State Department of Transportation",
        "source_id": "govspend",
        "predicate_id": "buyer",
    },
    {
        "name_key": "washington state department of transportation",
        "entity_id": "e-fixture-2",
        "label": "Washington State Department of Transportation",
        "source_id": "alpr_accountability_atlas",
        "predicate_id": "event_organizations",
    },
    {
        "name_key": "orphan works",
        "entity_id": "e-fixture-3",
        "label": "Orphan Works",
        "source_id": "govspend",
        "predicate_id": "buyer",
    },
]


class _FixtureCursor:
    """The slice of ``conn.cursor()`` ``name_scope_report`` consumes."""

    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows

    def __enter__(self) -> _FixtureCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[str, ...]) -> None:
        # The fixture spine answers exactly the report query, pinned verbatim.
        assert sql == _REPORT_SQL
        assert params == ("sig.org.name",)

    def fetchall(self) -> list[tuple[str | None, ...]]:
        return [
            (r["name_key"], r["entity_id"], r["label"], r["source_id"], r["predicate_id"])
            for r in self._rows
        ]


class _FixtureConn:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self._rows = rows

    def cursor(self) -> _FixtureCursor:
        return _FixtureCursor(self._rows)


def _fixture_report() -> dict:
    """The audit report over the fixture spine (3 legacy keys, 1 splitting)."""
    return name_scope_report(_FixtureConn(_REPORT_ROWS))


def _packet(tmp_path: Path | None = None) -> dict:
    return build_packet(
        _fixture_report(),
        spine="fixture-spine",
        started_at="2026-10-26T00:00:00Z",
        finished_at="2026-10-26T00:00:07Z",
        generated_at="2026-10-26T00:00:08Z",
    )


def test_packet_counts_the_fixture_spine() -> None:
    packet = _packet()
    assert packet["record_type"] == PACKET_SCHEMA
    assert packet["status"] == "measured"
    assert packet["obligation"] == OBLIGATION_ID
    assert packet["n"] == 3
    assert packet["measured"]["legacy_keys"] == 3
    assert packet["measured"]["split_keys"] == 1
    # wsdot decomposes into 3 scoped candidates; the two singles into 1 each.
    assert packet["measured"]["scoped_candidates_total"] == 5
    assert packet["measured"]["distinct_asserting_sources"] == 3
    assert packet["measured"]["split_count_histogram"] == {"1": 2, "3": 1}


def test_packet_groups_the_op15_options() -> None:
    radii = _packet()["option_blast_radii"]
    assert radii["keep"]["keys"] == 2  # single-source keys — harmless union
    assert radii["split"]["keys"] == 1  # the multi-source exposure
    assert radii["split"]["scoped_candidates"] == 5
    # The query carries no strong-id joinability — sized:false, never a guess.
    assert radii["same_as"]["sized"] is False
    assert radii["same_as"]["keys"] is None


def test_packet_binds_query_and_report_digests() -> None:
    packet = _packet()
    assert packet["query"]["sql"] == _REPORT_SQL
    assert packet["query"]["sha256"] == query_sha256()
    assert query_sha256() == hashlib.sha256(_REPORT_SQL.encode("utf-8")).hexdigest()
    assert packet["report_sha256"] == report_sha256(_fixture_report())
    assert len(packet["report_sha256"]) == 64
    assert packet["run_bounds"] == {
        "started_at": "2026-10-26T00:00:00Z",
        "finished_at": "2026-10-26T00:00:07Z",
    }


def test_packet_key_rows_carry_ids_and_digests_never_names() -> None:
    packet = _packet()
    assert len(packet["keys"]) == 3
    for row in packet["keys"]:
        assert set(row) == {
            "entity_id",
            "name_key_sha256",
            "source_count",
            "split_count",
        }
        assert len(row["name_key_sha256"]) == 64
    wsdot = next(r for r in packet["keys"] if r["entity_id"] == "e-fixture-2")
    assert wsdot["source_count"] == 3
    assert wsdot["split_count"] == 3
    # The join digest is the sha256 of the legacy key — never the key itself.
    assert (
        wsdot["name_key_sha256"]
        == hashlib.sha256(b"washington state department of transportation").hexdigest()
    )


def test_empty_report_fails_loud() -> None:
    empty = name_scope_report(_FixtureConn([]))
    assert empty["legacy_keys"] == 0
    with pytest.raises(PartnerNamePacketError, match="vacuous"):
        build_packet(
            empty,
            spine="fixture-spine",
            started_at="2026-10-26T00:00:00Z",
            finished_at="2026-10-26T00:00:07Z",
        )
    # The recorded escape for a spine that genuinely carries no legacy keys.
    packet = build_packet(
        empty,
        spine="fixture-spine",
        started_at="2026-10-26T00:00:00Z",
        finished_at="2026-10-26T00:00:07Z",
        allow_empty=True,
    )
    assert packet["n"] == 0
    assert packet["measured"]["legacy_keys"] == 0


def test_inconsistent_report_refused() -> None:
    bad = _fixture_report()
    bad["legacy_keys"] = 99  # smoothed count — never silently accepted
    with pytest.raises(PartnerNamePacketError, match="inconsistent"):
        build_packet(
            bad,
            spine="fixture-spine",
            started_at="t0",
            finished_at="t1",
        )


def test_malformed_report_file_refused(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text('{"scheme": "sig.org.name"}', encoding="utf-8")
    with pytest.raises(PartnerNamePacketError, match="legacy_keys"):
        load_report(path)


def test_emitted_artifacts_carry_no_registrant_names(tmp_path: Path) -> None:
    paths = write_packet(_packet(), tmp_path)
    emitted = ""
    for path in paths.values():
        emitted += path.read_text(encoding="utf-8")
    for name in _FIXTURE_NAMES:
        assert name not in emitted
    # keys.csv is header + one row per key — ids and counts only.
    csv_lines = (tmp_path / "keys.csv").read_text(encoding="utf-8").splitlines()
    assert csv_lines[0] == "entity_id,name_key_sha256,source_count,split_count"
    assert len(csv_lines) == 4
    # The markdown states the measured N with its digest.
    md = (tmp_path / "PACKET.md").read_text(encoding="utf-8")
    assert "`legacy_keys` = 3" in md
    assert packet_sha256(_packet()) in (tmp_path / "packet.sha256").read_text(encoding="utf-8")


def test_keys_csv_matches_packet_rows() -> None:
    packet = _packet()
    rows = keys_csv(packet).splitlines()
    assert rows[0] == "entity_id,name_key_sha256,source_count,split_count"
    assert len(rows) == 4


def test_load_report_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps(_fixture_report()), encoding="utf-8")
    report = load_report(path)
    assert report["legacy_keys"] == 3


def test_queued_packet_records_never_fabricates(tmp_path: Path) -> None:
    packet = build_queued_packet(
        spine="sig-pg (read-only sig_read_public)",
        planned_at="2026-10-26T00:00:00Z",
        reason="hosted env absent (no ADC, SIG_GCP_PROJECT unset)",
        rerun="implement-spec spec=x live_verification=true",
    )
    assert packet["status"] == "prepared_not_executed"
    assert packet["n"] is None
    assert packet["measured"] is None
    assert packet["keys"] == []
    assert packet["report_sha256"] is None
    # The query + its digest still pin what the re-run will measure.
    assert packet["query"]["sha256"] == query_sha256()
    paths = write_packet(packet, tmp_path)
    assert "keys" not in paths  # no keys.csv for a queued packet
    md = (tmp_path / "PACKET.md").read_text(encoding="utf-8")
    assert "QUEUED" in md
    for name in _FIXTURE_NAMES:
        assert name not in md


def test_packet_markdown_lists_no_names_in_rendered_tables() -> None:
    md = render_markdown(_packet())
    for name in _FIXTURE_NAMES:
        assert name not in md
