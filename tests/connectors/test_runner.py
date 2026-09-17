# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The source-driven runner: live gate refusal, fetch record, shadow (P21.3).

The ``live`` gate is asserted with **no source flipped** (HG-03 pending), so every
live run is refused before any egress — under network isolation, proving no socket
is opened. ``replay`` / ``shadow`` run over the committed fixtures and report a
0-diff, the additive/back-compat invariant this ticket must hold.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from connectors.cli import main
from connectors.isolation import network_isolated
from connectors.runner import (
    FetchRecord,
    LiveGateRefused,
    RunMode,
    is_review_status_green,
    live_gate_reasons,
    run_source,
    write_fetch_record,
)

_OSM_FIX = Path(__file__).resolve().parents[1] / "connectors" / "fixtures" / "osm"
_ATLAS_FIX = Path(__file__).resolve().parents[1] / "connectors" / "fixtures" / "atlas"


# --- the live gate (LD-X08: a live fetch is impossible without a green status) --


def test_no_seeded_source_is_review_status_green() -> None:
    # After the RIGHTS.1 flip re-run (GL-GATE-03) plus the 2026-09-15/16 flips
    # (B pass, GL-GATE-06, and the P26.2 promoted-source flips), the sources that
    # stay gated are still refused for a live fetch. sam_gov moved out of this
    # set in P26.2 (federal public-domain rights resolved); documentcloud +
    # courtlistener_recap are CONNECTOR-MAPPED but stay gated — per-document
    # rights UNDETERMINED and membership-agreement access respectively.
    for source_id in (
        "journalrecord",
        "oklahoman",
        "documentcloud",
        "courtlistener_recap",
    ):
        assert not is_review_status_green(source_id)
        assert live_gate_reasons(source_id)


def _gated_record(source_id: str = "madada"):
    """A synthetic still-gated registry row for a connector-mapped source.

    After the 2026-09-15 unblock pass every connector-mapped source is flipped,
    so the live-refusal AC is exercised by standing a gated record in for a real
    mapped id — the refusal path (`live_gate_reasons` → `LiveGateRefused` before
    any transport) is the thing under test.
    """
    import dataclasses

    from connectors.registry import get

    return dataclasses.replace(get(source_id), ingestion_permitted=False)


def test_live_mode_refuses_an_ungated_source_with_reasons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A connector-mapped source whose record is not flipped is refused with the
    # gate reasons. (Every real mapped row is flipped post-2026-09-15 — the gate
    # itself is the AC, so a synthetic un-flipped record stands in.)
    import connectors.runner as runner

    monkeypatch.setattr(runner, "get", lambda _sid: _gated_record("madada"))
    with pytest.raises(LiveGateRefused) as excinfo:
        run_source("madada", mode=RunMode.LIVE, sink_kind="memory")
    assert excinfo.value.source_id == "madada"
    assert any("ingestion_permitted" in r for r in excinfo.value.reasons)


def test_live_refusal_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    # AC: the live refusal happens before any transport is built — no socket is
    # opened. Under network isolation an accidental egress would raise; the clean
    # LiveGateRefused proves the gate is checked first.
    import connectors.runner as runner

    monkeypatch.setattr(runner, "get", lambda _sid: _gated_record("madada"))
    with network_isolated():
        with pytest.raises(LiveGateRefused):
            run_source("madada", mode=RunMode.LIVE, sink_kind="memory")


def test_cli_live_mode_exits_3_and_prints_gate_reasons(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # AC: `sig-connectors run --source <un-flipped> --mode live` exits 3 and
    # prints the gate reasons (synthetic gated record — see _gated_record).
    import connectors.runner as runner

    monkeypatch.setattr(runner, "get", lambda _sid: _gated_record("madada"))
    code = main(["run", "--source", "madada", "--mode", "live", "--sink", "memory"])
    out = capsys.readouterr().out
    assert code == 3
    assert "REFUSED" in out
    assert "ingestion_permitted" in out


# --- replay / shadow over committed fixtures ---------------------------------


@pytest.mark.parametrize(
    ("source_id", "connector", "fixture", "media_type", "kind"),
    [
        (
            "osm_overpass",
            "osm",
            _OSM_FIX / "overpass_snapshot.json",
            "application/json",
            "overpass",
        ),
        (
            "eff_atlas_of_surveillance",
            "atlas",
            _ATLAS_FIX / "adoption_feed.csv",
            "text/csv",
            "bulk_csv",
        ),
    ],
)
def test_shadow_over_committed_fixtures_reports_zero_diffs(
    source_id: str, connector: str, fixture: Path, media_type: str, kind: str
) -> None:
    # AC: for every fixture-backed connector, shadow mode over the committed
    # fixtures reports 0 diffs (SIG-INGEST-019; additive/back-compat).
    report = run_source(
        source_id,
        mode=RunMode.SHADOW,
        connector_name=connector,
        fixture=fixture,
        media_type=media_type,
        kind=kind,
    )
    assert report.diff is not None
    assert report.diff.changed_count == 0
    assert report.diff.summary()["unchanged"] > 0


def test_replay_over_fixture_is_reproducible() -> None:
    report = run_source(
        "osm_overpass",
        mode=RunMode.REPLAY,
        connector_name="osm",
        fixture=_OSM_FIX / "overpass_snapshot.json",
        media_type="application/json",
        kind="overpass",
    )
    assert report.replay_reproducible is True


def test_replay_and_shadow_require_a_fixture() -> None:
    with pytest.raises(ValueError, match="fixture"):
        run_source("osm_overpass", mode=RunMode.SHADOW, connector_name="osm")


# --- the fetch record carries crawler-conduct evidence and no content --------


def test_fetch_record_carries_conduct_evidence_and_no_content(tmp_path: Path) -> None:
    # AC: crawler-conduct evidence (rate-limit events, robots decisions) is
    # present in every fetch record, and the record carries no content bytes.
    record = FetchRecord(
        source_id="osm_overpass",
        connector="osm",
        mode="live",
        started_at="2026-09-01T00:00:00+00:00",
        duration_seconds=1.5,
        urls=["https://overpass-api.de/api/interpreter"],
        status_codes=[200],
        byte_counts=[1024],
        capture_digests=["bdeadbeef"],
        claim_count=19,
        rate_limit_events=[{"status": 429, "action": "back_off", "wait_seconds": 2.0}],
        robots_decisions=[{"host": "overpass-api.de", "allowed": True}],
    )
    payload = record.to_dict()
    assert payload["rate_limit_events"] and payload["robots_decisions"]
    assert "body" not in payload and "content" not in payload
    path = write_fetch_record(record, tmp_path)
    assert path.name == "2026-09-01_osm_overpass.json"
    assert path.read_text().strip().startswith("{")
