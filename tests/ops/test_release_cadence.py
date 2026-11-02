# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.44 (REL-07; SIG-REL-011 + SIG-OPS-008) — the release cadence evaluator.

The fixtures pin the contract verbatim: first weekday on/after the 15th at
14:00Z; Class-S-14-day suppression of the scheduled cut; the ≥10 %/≥14-day
early trigger; the 35-day max-age alert (+cut only when none is running);
and the recorded AR-3 freeze.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ops.alerts import AlertLedger
from ops.release_cadence import (
    CADENCE_SCHEMA,
    MATERIALIZE_CRON,
    MAX_AGE_ALERT_KIND,
    RELEASE_CRON,
    Promotion,
    cut_day,
    emit_decision,
    evaluate,
    fire_max_age_alert,
    in_flight_publications,
    promotions_from_events,
    registry_facts,
    run_release_cadence,
    scheduled_due,
)
from ops.release_pipeline import LocalDirStore, emit_event

T = "%Y-%m-%dT%H:%M:%SZ"


def _at(text: str) -> datetime:
    return datetime.strptime(text, T).replace(tzinfo=UTC)


def _promo(cls: str, days_ago: float, now: datetime, pub: str = "p-aaaa") -> Promotion:
    return Promotion(
        publication_id=pub,
        release_class=cls,
        activated_at=now - timedelta(days=days_ago),
    )


def _latest(pub: str, days_ago: float, now: datetime, cls: str = "R") -> dict:
    return {
        "publication_id": pub,
        "label": "sig-2026-10-01.1",  # future-ok: synthetic: test-clock literal
        "class": cls,
        "activated_at": (now - timedelta(days=days_ago)).strftime(T),
    }


# --- the calendar ----------------------------------------------------------- #


def test_cut_day_first_weekday_on_or_after_the_15th() -> None:
    # future-ok: scheduled: window-cell instance — literal: 11-15 is a
    # Sunday → Mon 11-16;
    # future-ok: scheduled: window-cell instance — 2026-12-15 is a Tuesday → itself.
    assert (
        cut_day(2026, 11).isoformat() == "2026-11-16"  # future-ok: scheduled: window-cell instance
    )  # future-ok: scheduled: window-cell instance
    assert (
        cut_day(2026, 12).isoformat() == "2026-12-15"  # future-ok: scheduled: window-cell instance
    )  # future-ok: scheduled: window-cell instance


def test_cut_day_weekend_slide() -> None:
    # future-ok: scheduled: window-cell instance — 2026-08-15 Saturday
    # → Mon 17th; 2027-01-15 Friday → itself. future-ok: scheduled: inst.
    assert cut_day(2026, 8).isoformat() == "2026-08-17"  # future-ok: synthetic
    assert (
        cut_day(2027, 1).isoformat() == "2027-01-15"  # future-ok: scheduled: window-cell instance
    )  # future-ok: scheduled: window-cell instance


def test_scheduled_due_only_in_the_1400z_slot() -> None:
    assert scheduled_due(_at("2026-11-16T14:00:00Z"))  # future-ok: synthetic: test-clock literal
    assert scheduled_due(_at("2026-11-16T14:37:12Z"))  # future-ok: synthetic: test-clock literal
    assert not scheduled_due(
        _at("2026-11-16T13:59:59Z")  # future-ok: synthetic: test-clock literal
    )  # future-ok: synthetic: test-clock literal
    assert not scheduled_due(
        _at("2026-11-15T14:00:00Z")  # future-ok: synthetic: test-clock literal
    )  # future-ok: synthetic: test-clock literal — Sunday — not a weekday
    assert not scheduled_due(
        _at("2026-11-17T14:00:00Z")  # future-ok: synthetic: test-clock literal
    )  # future-ok: synthetic: test-clock literal — the slot has passed


def test_release_cron_covers_every_cut_day() -> None:
    # days 15-17 cover the only three dates a first-weekday-on/after-15 can be.
    assert RELEASE_CRON == "0 14 15-17 * *"
    assert MATERIALIZE_CRON == "0 8 * * 0"  # G1 §3.6 verbatim


# --- the journal fold ------------------------------------------------------- #


def test_promotions_from_events_reads_class_and_instant() -> None:
    events = [
        {
            "verb": "promoted",
            "publication_id": "p-1111",
            "class": "class_s",
            "recorded_at": "2026-10-01T14:12:00Z",  # future-ok: synthetic: test-clock literal
        },
        {
            "verb": "cut",
            "publication_id": "p-1111",  # future-ok: synthetic
            "recorded_at": "2026-10-01T14:00:00Z",
        },
        {
            "verb": "promoted",
            "publication_id": "p-2222",
            "class": "class_r",
            "recorded_at": "2026-10-15T14:20:00Z",  # future-ok: synthetic: test-clock literal
        },
    ]
    promos = promotions_from_events(events)
    assert [p.release_class for p in promos] == ["S", "R"]
    assert promos[-1].publication_id == "p-2222"


def test_in_flight_publications_folds_the_state_machine() -> None:
    events = [
        {"verb": "cut", "publication_id": "p-1111"},
        {"verb": "built", "publication_id": "p-1111"},
        {"verb": "staged", "publication_id": "p-1111"},
        {"verb": "promoted", "publication_id": "p-2222"},
    ]
    assert in_flight_publications(events) == ["p-1111"]


# --- the decision ----------------------------------------------------------- #


def test_scheduled_cut_fires_on_the_cut_day() -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 20, now)],
        latest=_latest("p-aaaa", 20, now),
        spine_eligible=1010,
        release_published=1000,
        cut_running=False,
    )
    assert rec["schema"] == CADENCE_SCHEMA
    assert rec["decision"] == "cut"
    assert "scheduled" in rec["triggered_by"]
    assert rec["cut_slot"]["day"] == "2026-11-16"  # future-ok: scheduled: window-cell instance


def test_class_s_promotion_within_14_days_suppresses_the_scheduled_cut() -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("S", 10, now)],
        latest=_latest("p-aaaa", 10, now, cls="S"),
        spine_eligible=None,
        release_published=None,
        cut_running=False,
    )
    assert rec["decision"] == "suppressed"
    assert rec["suppressions"]["class_s_recent"] is True
    assert rec["triggered_by"] == []


def test_class_s_older_than_14_days_does_not_suppress() -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("S", 16, now)],
        latest=_latest("p-aaaa", 16, now, cls="S"),
        spine_eligible=None,
        release_published=None,
        cut_running=False,
    )
    assert rec["decision"] == "cut"
    assert rec["suppressions"]["class_s_recent"] is False


def test_class_r_promotion_never_suppresses_the_scheduled_cut() -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 3, now)],
        latest=_latest("p-aaaa", 3, now),
        spine_eligible=None,
        release_published=None,
        cut_running=False,
    )
    assert rec["decision"] == "cut"


def test_early_cut_needs_10pct_and_14_days() -> None:
    now = _at("2026-11-20T14:00:00Z")  # future-ok: synthetic: test-clock literal — not a cut day
    rec = evaluate(
        now,
        promotions=[_promo("R", 20, now)],
        latest=_latest("p-aaaa", 20, now),
        spine_eligible=1105,
        release_published=1000,
        cut_running=False,
    )
    assert rec["decision"] == "cut"
    assert rec["triggered_by"] == ["early"]
    assert rec["delta"]["net_new"] == 105

    below = evaluate(
        now,
        promotions=[_promo("R", 20, now)],
        latest=_latest("p-aaaa", 20, now),
        spine_eligible=1099,
        release_published=1000,
        cut_running=False,
    )
    assert below["decision"] == "hold"

    fresh = evaluate(
        now,
        promotions=[_promo("R", 10, now)],
        latest=_latest("p-aaaa", 10, now),
        spine_eligible=1200,
        release_published=1000,
        cut_running=False,
    )
    assert fresh["decision"] == "hold"  # <14 days since the last promotion


def test_early_trigger_is_honest_when_inputs_are_absent() -> None:
    now = _at("2026-11-20T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 20, now)],
        latest=_latest("p-aaaa", 20, now),
        spine_eligible=None,
        release_published=None,
        cut_running=False,
    )
    assert rec["triggers"]["early"] == "not_evaluable"
    assert rec["decision"] == "hold"


def test_a_release_older_than_35_days_alerts() -> None:
    now = _at("2026-11-20T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 40, now)],
        latest=_latest("p-aaaa", 40, now),
        spine_eligible=1000,
        release_published=1000,
        cut_running=False,
    )
    assert rec["decision"] == "cut"
    assert "max_age" in rec["triggered_by"]
    assert rec["alert"]["kind"] == MAX_AGE_ALERT_KIND


def test_max_age_alerts_but_never_double_cuts_a_running_cut() -> None:
    now = _at("2026-11-20T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 40, now)],
        latest=_latest("p-aaaa", 40, now),
        spine_eligible=1000,
        release_published=1000,
        cut_running=True,
    )
    assert rec["decision"] == "alert"
    assert rec["triggered_by"] == []
    assert rec["alert"]["kind"] == MAX_AGE_ALERT_KIND


def test_ar3_freeze_is_a_recorded_check_never_a_comment() -> None:
    # the daily restricted window — 03:00–06:30Z (the monthly batch window
    # ends day 13; the cut day can never be inside it)
    now = _at("2026-11-20T04:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 40, now)],
        latest=_latest("p-aaaa", 40, now),
        spine_eligible=None,
        release_published=None,
        cut_running=False,
    )
    assert rec["decision"] == "frozen"
    assert rec["window"]["frozen"] is True
    assert "daily restricted window" in rec["window"]["ar3"]
    assert rec["triggered_by"] == []  # a stale release still alerts…
    assert rec["alert"]["kind"] == MAX_AGE_ALERT_KIND  # …the freeze blocks cuts, not alerts


def test_no_promoted_release_decides_no_release() -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[],
        latest=None,
        spine_eligible=None,
        release_published=None,
        cut_running=False,
    )
    assert rec["decision"] == "no_release"


# --- emit + the recorded alert ---------------------------------------------- #


def test_emit_decision_writes_append_only(tmp_path: Path) -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 20, now)],
        latest=_latest("p-aaaa", 20, now),
        spine_eligible=1005,
        release_published=1000,
        cut_running=False,
    )
    written = emit_decision(rec, tmp_path)
    doc = json.loads(written["decision"].read_text(encoding="utf-8"))
    assert doc["schema"] == CADENCE_SCHEMA
    assert doc["decision"] == "cut"
    lines = written["jsonl"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    emit_decision(rec, tmp_path)  # a same-instant re-emit appends, never rewrites
    assert len(written["jsonl"].read_text(encoding="utf-8").splitlines()) == 2


def test_max_age_alert_lands_in_the_ledger(tmp_path: Path) -> None:
    now = _at("2026-11-20T14:00:00Z")  # future-ok: synthetic: test-clock literal
    rec = evaluate(
        now,
        promotions=[_promo("R", 40, now)],
        latest=_latest("p-aaaa", 40, now),
        spine_eligible=1000,
        release_published=1000,
        cut_running=True,
    )
    ledger = AlertLedger(tmp_path / "alerts.jsonl")
    fired = fire_max_age_alert(rec, ledger=ledger, notifiers=[])
    assert fired is not None
    rows = ledger.read()
    assert len(rows) == 1
    assert rows[0]["kind"] == MAX_AGE_ALERT_KIND
    assert rows[0]["severity"] == "alarm"


# --- the verb over a fixture registry --------------------------------------- #


def _fixture_registry(root: Path, *, now: datetime) -> LocalDirStore:
    store = LocalDirStore(root)
    emit_event(
        store,
        "promoted",
        "p-aaaa",
        {
            "outcome": "recorded",
            "class": "class_r",  # future-ok: synthetic
            "label": "sig-2026-10-01.1",
        },
        now=now - timedelta(days=20),
    )
    store.insert(
        "registry/latest.json",
        json.dumps(_latest("p-aaaa", 20, now)).encode(),
        content_type="application/json",
    )
    return store


def test_registry_facts_reads_latest_and_promotions(tmp_path: Path) -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    store = _fixture_registry(tmp_path, now=now)
    facts = registry_facts(store)
    assert facts["latest"]["publication_id"] == "p-aaaa"
    assert len(facts["promotions"]) == 1
    assert facts["promotions"][0].release_class == "R"
    assert facts["in_flight"] == []


def _ns(**kw: object) -> argparse.Namespace:
    base: dict[str, object] = {
        "registry": None,
        "facts": None,
        "spine_eligible": None,
        "release_published": None,
        "cut_running": False,
        "at": None,
        "out": None,
        "alert": False,
        "ledger": None,
        "apply": False,
        "skip_host_clock_check": False,
    }
    base.update(kw)
    return argparse.Namespace(**base)


def test_run_release_cadence_evaluates_and_emits(tmp_path: Path, capsys) -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    registry = tmp_path / "registry"
    _fixture_registry(registry, now=now)
    rc = run_release_cadence(
        _ns(
            registry=str(registry),
            at="2026-11-16T14:00:00Z",  # future-ok: synthetic: test-clock literal
            out=str(tmp_path / "out"),
            facts=None,
            spine_eligible=1005,
            release_published=1000,
        )
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "decision=cut" in out
    emitted = json.loads(
        (tmp_path / "out" / "cadence" / "20261116T140000Z.json").read_text(encoding="utf-8")
    )
    assert emitted["decision"] == "cut"


def test_run_release_cadence_apply_journals_and_cuts(tmp_path: Path, capsys) -> None:
    now = _at("2026-11-16T14:00:00Z")  # future-ok: synthetic: test-clock literal
    registry = tmp_path / "registry"
    _fixture_registry(registry, now=now)
    rc = run_release_cadence(
        _ns(
            registry=str(registry),
            at="2026-11-16T14:00:00Z",  # future-ok: synthetic: test-clock literal
            apply=True,
            skip_host_clock_check=True,
        )
    )
    assert rc == 0
    # the cadence evaluation journals, then the cut verb journals
    names = " ".join(sorted(p.name for p in (registry / "registry" / "events").iterdir()))
    assert "-cadence-" in names
    assert "-cut-" in names


def test_run_release_cadence_refuses_without_registry(capsys) -> None:
    rc = run_release_cadence(_ns(registry=None))
    assert rc == 2
    assert "SIG_RELEASE_REGISTRY" in capsys.readouterr().out


def test_run_release_cadence_alert_fires_and_exits_6(tmp_path: Path, capsys) -> None:
    registry = tmp_path / "registry"
    store = LocalDirStore(registry)
    now = _at("2026-11-20T14:00:00Z")  # future-ok: synthetic: test-clock literal
    emit_event(
        store,
        "promoted",
        "p-aaaa",
        {"outcome": "recorded", "class": "class_r"},
        now=now - timedelta(days=40),
    )
    store.insert(
        "registry/latest.json",
        json.dumps(_latest("p-aaaa", 40, now)).encode(),
        content_type="application/json",
    )
    rc = run_release_cadence(
        _ns(
            registry=str(registry),
            at="2026-11-20T14:00:00Z",  # future-ok: synthetic: test-clock literal
            alert=True,
            ledger=str(tmp_path / "alerts.jsonl"),
            spine_eligible=1000,
            release_published=1000,
        )
    )
    assert rc == 6
    rows = (tmp_path / "alerts.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(rows[0])["kind"] == MAX_AGE_ALERT_KIND
