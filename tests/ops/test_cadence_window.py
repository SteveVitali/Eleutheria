# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.4 / ADR-111: the cadence window is the logical-run (resume) key."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from typing import Any

import pytest
from ops.cadence_window import (
    CronError,
    cron_for_source,
    logical_run_key,
    parse_cron,
    previous_fire,
)
from ops.scheduled import load_cadence, scheduled_ingest


def _t(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


@pytest.mark.parametrize(
    ("cron", "now", "fire"),
    [
        # batch-05 (the OSM replay): monthly on the 10th at 03:35.
        ("35 3 10 * *", "2026-09-25T00:00", "2026-09-10T03:35"),
        ("35 3 10 * *", "2026-10-10T03:34", "2026-09-10T03:35"),
        ("35 3 10 * *", "2026-10-10T03:35", "2026-10-10T03:35"),
        ("35 3 10 * *", "2026-10-11T12:00", "2026-10-10T03:35"),
        # every 6 hours
        ("0 */6 * * *", "2026-09-24T23:15", "2026-09-24T18:00"),
        # weekly Monday (dow 1)
        ("12 4 * * 1", "2026-09-24T23:15", "2026-09-21T04:12"),
        # quarterly on the 1st
        ("0 5 1 1,4,7,10 *", "2026-09-24T00:00", "2026-07-01T05:00"),
        # dom AND dow restricted: either matches (Vixie) — the 2nd, or any Tuesday
        ("0 5 2 * 2", "2026-09-24T00:00", "2026-09-22T05:00"),
        # "*/2" day-of-month is unrestricted for the OR rule (Vixie): AND with Tuesday
        ("0 5 */2 * 2", "2026-09-24T00:00", "2026-09-15T05:00"),
        # a trailing comment, as cadence.toml rows carry
        ("0 5 2 * *   # day 2", "2026-09-24T00:00", "2026-09-02T05:00"),
    ],
)
def test_previous_fire(cron: str, now: str, fire: str) -> None:
    assert previous_fire(cron, _t(now)) == _t(fire)


def test_every_cadence_row_parses_and_fires() -> None:
    config = load_cadence()
    crons = [s.cron for s in config.sources] + [b.cron for b in config.batches]
    assert crons
    for cron in crons:
        parse_cron(cron)
        assert previous_fire(cron, _t("2026-09-25T00:00")) <= _t("2026-09-25T00:00")


@pytest.mark.parametrize("bad", ["* * * *", "61 * * * *", "0 0 0 * *", "a b c d e", "*/0 * * * *"])
def test_bad_crons_are_refused(bad: str) -> None:
    with pytest.raises(CronError):
        parse_cron(bad)


def test_a_batch_member_uses_its_batch_cron_and_the_key_changes_per_window() -> None:
    config = load_cadence()
    cron = cron_for_source(config, "camreg_osm_surveillance")
    assert cron == "35 3 10 * *"  # camreg-batch-05
    before = logical_run_key("camreg_osm_surveillance", cron, _t("2026-10-10T03:00"))
    after = logical_run_key("camreg_osm_surveillance", cron, _t("2026-10-10T04:00"))
    restart = logical_run_key("camreg_osm_surveillance", cron, _t("2026-10-11T09:00"))
    assert before == "camreg_osm_surveillance@2026-09-10T03:35Z"
    assert after == restart == "camreg_osm_surveillance@2026-10-10T03:35Z"
    assert cron_for_source(config, "no_such_source") is None


def test_scheduled_ingest_passes_the_resume_key_and_limit_only_when_set() -> None:
    calls: list[dict[str, Any]] = []

    class Report:
        run_id = "r"
        claims: list[Any] = []
        captures: list[Any] = []
        fetch_record = None
        refusals: list[Any] = []
        disappearances: list[Any] = []
        emitted = 1234

    def runner(source: str, **kw: Any) -> Report:
        calls.append(kw)
        return Report()

    row = scheduled_ingest("s", runner=runner, now="2026-09-25T00:00:00+00:00")
    assert "logical_run" not in calls[-1] and "target_limit" not in calls[-1]
    assert row.claims_added == 1234  # the exact emitted count, not len(claims)
    scheduled_ingest("s", runner=runner, logical_run="s@2026-09-10T03:35Z", target_limit=20)
    assert calls[-1]["logical_run"] == "s@2026-09-10T03:35Z" and calls[-1]["target_limit"] == 20


def test_the_cli_derives_the_key_from_the_cadence_window() -> None:
    from ops.cli import _logical_run_for

    config = load_cadence()

    def ns(**kw: Any) -> argparse.Namespace:
        base = {"no_resume": False, "sink": "pg", "logical_run": None}
        return argparse.Namespace(**{**base, **kw})

    started = "2026-09-25T00:10:00+00:00"
    assert (
        _logical_run_for(config, "camreg_osm_surveillance", started, ns())
        == "camreg_osm_surveillance@2026-09-10T03:35Z"
    )
    assert _logical_run_for(config, "camreg_osm_surveillance", started, ns(no_resume=True)) is None
    assert _logical_run_for(config, "camreg_osm_surveillance", started, ns(sink="memory")) is None
    assert _logical_run_for(config, "x", started, ns(logical_run="pinned")) == "pinned"
    assert _logical_run_for(config, "unscheduled_source", started, ns()) is None


def test_a_bad_cron_costs_only_the_resume_and_the_code_commit_is_passed() -> None:
    import dataclasses

    from ops.cli import _logical_run_for

    config = load_cadence()
    broken = dataclasses.replace(
        config,
        batches=tuple(dataclasses.replace(b, cron="0 5 * * MON") for b in config.batches),
    )
    args = argparse.Namespace(no_resume=False, sink="pg", logical_run=None)
    assert (
        _logical_run_for(broken, "camreg_osm_surveillance", "2026-09-25T00:00:00+00:00", args)
        is None
    )

    calls: list[dict[str, Any]] = []

    class Report:
        run_id = ""
        claims: list[Any] = []
        captures: list[Any] = []
        fetch_record = None
        refusals: list[Any] = []
        disappearances: list[Any] = []

    def runner(source: str, **kw: Any) -> Report:
        calls.append(kw)
        return Report()

    scheduled_ingest("s", runner=runner, code_commit="sha256:abc")
    assert calls[-1]["code_commit"] == "sha256:abc"
    scheduled_ingest("s", runner=runner)
    assert "code_commit" not in calls[-1]
