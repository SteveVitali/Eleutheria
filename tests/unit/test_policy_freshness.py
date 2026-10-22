# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.33 — the shared cadence + freshness-state machinery (J3 §4.6, K9
§5.1 + §10 C-4…C-7) and the closed auto-issue vocabulary (J3 §7.3).

One pure function shared by the export, the status lane and ACT-02's
alerting — these truth-table tests pin the contract so page and alert can
never disagree.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from policy.freshness import (
    AUTO_ISSUE_CLASSES,
    FRESHNESS_STATES,
    FreshnessState,
    cadence_interval,
    cadence_rule,
    cron_fields,
    freshness_state,
    previous_cron_fire,
    valid_issue_class,
    valid_quarantine_reason,
)

AT = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)


# --- cadence_rule (K9 C-4: the rule, never a next-run timestamp) --------


@pytest.mark.parametrize(
    ("cron", "cadence", "expected"),
    [
        ("0 5 6 * *", "monthly", "monthly, day 6"),
        ("0 6 1 * *", "monthly", "monthly, day 1"),
        ("12 4 * * 1", "weekly", "weekly, Monday"),
        ("12 4 * * 0", "weekly", "weekly, Sunday"),
        ("12 4 * * 7", "weekly", "weekly, Sunday"),
        ("0 5 1 1,4,7,10 *", "quarterly", "quarterly, day 1 of Jan, Apr, Jul, Oct"),
        ("0 5 * * *", "daily", "daily"),
        ("0 */6 * * *", "", "every 6 hours"),
        ("*/15 * * * *", "", "every 15 minutes"),
        ("0 * * * *", "", "hourly"),
        ("not a cron", "monthly", "monthly"),
        ("not a cron", "", "custom schedule"),
    ],
)
def test_cadence_rule_renders_the_rule_not_a_next_run(cron, cadence, expected):
    rule = cadence_rule(cron, cadence)
    assert rule == expected
    # C-4: no rule is ever a timestamp — the next run lives on the status lane.
    assert not any(ch.isdigit() and "/" in rule for ch in rule)


def test_cron_fields_rejects_unevidenced_shapes():
    assert cron_fields("0 5 6 * *") is not None
    assert cron_fields("0 5 * * MON") is None  # named weekdays unevidenced
    assert cron_fields("0 5") is None
    assert cron_fields("") is None


def test_previous_cron_fire_finds_the_last_fire():
    # monthly day 6 at 05:00 → last fire before Oct 19 is Oct 6 05:00.
    fire = previous_cron_fire("0 5 6 * *", AT)
    assert fire == datetime(2026, 10, 6, 5, 0, tzinfo=UTC)
    # weekly Monday 04:12 → last fire before Oct 19 08:00 is Oct 19 04:12.
    fire = previous_cron_fire("12 4 * * 1", AT)
    assert fire == datetime(2026, 10, 19, 4, 12, tzinfo=UTC)
    # never fires at-or-after `at` itself.
    fire = previous_cron_fire("0 8 * * *", AT)
    assert fire == datetime(2026, 10, 18, 8, 0, tzinfo=UTC)
    assert previous_cron_fire("garbage", AT) is None


def test_cadence_interval_words_and_cron():
    assert cadence_interval("0 5 6 * *", "monthly") == timedelta(days=30.44)
    assert cadence_interval("12 4 * * 1", "weekly") == timedelta(weeks=1)
    assert cadence_interval("", "unknown-word") is None
    assert cadence_interval("0 5 6 * *", "") == timedelta(days=30.44)


# --- freshness_state (the C-7 truth table) ------------------------------


def _ok_run(finished: datetime) -> dict:
    return {"finished_at": finished, "status": "ok"}


def _failed_run(finished: datetime) -> dict:
    return {"finished_at": finished, "status": "failed"}


def test_not_scheduled_and_not_applicable_and_one_time():
    assert freshness_state(cadence_cron=None, scheduled=False, at=AT).state == "not_scheduled"
    assert (
        freshness_state(cadence_cron="0 5 6 * *", scheduled=True, one_time_load=True, at=AT).state
        == "one_time_load"
    )
    assert (
        freshness_state(cadence_cron="0 5 6 * *", scheduled=True, applicable=False, at=AT).state
        == "not_applicable"
    )
    st = freshness_state(cadence_cron=None, scheduled=False, at=AT)
    assert isinstance(st, FreshnessState)
    assert st.state in FRESHNESS_STATES


def test_never_run_and_run_record_missing():
    st = freshness_state(cadence_cron="0 5 6 * *", scheduled=True, at=AT)
    assert st.state == "never_run"
    assert st.run_record_missing is False
    # C-7: published data without an execution record — the flag, never a
    # fabricated run.
    st = freshness_state(cadence_cron="0 5 6 * *", scheduled=True, has_records=True, at=AT)
    assert st.state == "never_run"
    assert st.run_record_missing is True
    # …and the flag is independent of the state (unscheduled sources too).
    st = freshness_state(cadence_cron=None, scheduled=False, has_records=True, at=AT)
    assert st.state == "not_scheduled"
    assert st.run_record_missing is True


def test_last_run_failed_dominates():
    st = freshness_state(
        cadence_cron="0 5 6 * *",
        cadence_word="monthly",
        scheduled=True,
        executions=[_ok_run(AT - timedelta(days=10)), _failed_run(AT - timedelta(days=1))],
        at=AT,
    )
    assert st.state == "last_run_failed"
    # A killed execution (no completion status) is not a success either.
    st = freshness_state(
        cadence_cron="0 5 6 * *",
        cadence_word="monthly",
        scheduled=True,
        executions=[{"finished_at": AT - timedelta(days=1), "status": None}],
        at=AT,
    )
    assert st.state == "last_run_failed"


def test_overdue_late_on_time():
    monthly = {"cadence_cron": "0 5 6 * *", "cadence_word": "monthly", "scheduled": True}
    # > 2 intervals since the last success → overdue.
    st = freshness_state(**monthly, executions=[_ok_run(AT - timedelta(days=80))], at=AT)
    assert st.state == "overdue"
    # Expected fire Oct 6 05:00; grace is half the interval (≈15.2d) so the
    # verdict turns late once Oct 21 passes; last success Sep 1 covers only
    # the Sep 6 fire → late (54d is still under the 2×interval overdue bar).
    st = freshness_state(
        **monthly,
        executions=[_ok_run(datetime(2026, 9, 1, tzinfo=UTC))],
        at=datetime(2026, 10, 25, 8, 0, tzinfo=UTC),
    )
    assert st.state == "late"
    # Success covering the Oct 6 fire → on_time.
    st = freshness_state(**monthly, executions=[_ok_run(datetime(2026, 10, 8, tzinfo=UTC))], at=AT)
    assert st.state == "on_time"


def test_state_stays_in_the_closed_vocabulary():
    states = {
        freshness_state(cadence_cron=None, scheduled=False, at=AT).state,
        freshness_state(cadence_cron="0 5 6 * *", scheduled=True, at=AT).state,
        freshness_state(
            cadence_cron="0 5 6 * *",
            cadence_word="monthly",
            scheduled=True,
            executions=[_ok_run(AT - timedelta(days=80))],
            at=AT,
        ).state,
    }
    assert states <= set(FRESHNESS_STATES)


# --- the closed issue vocabulary (J3 §7.3) -------------------------------


def test_issue_class_vocabulary_is_closed():
    for cls in (
        "robots_disallow",
        "politeness_refusal",
        "rate_limited",
        "quota_reached",
        "budget_reached",
        "content_drift",
        "disappearance",
        "zero_records",
        "late",
        "overdue",
        "never_run",
        "scheduler_drift",
        "capture_not_retained",
    ):
        assert cls in AUTO_ISSUE_CLASSES
        assert valid_issue_class(cls)
    assert valid_issue_class("upstream_http_503")
    assert valid_issue_class("quarantine_bad_digest")
    assert not valid_issue_class("db_connection_lost")  # internal, never public
    assert not valid_issue_class("made_up_issue")
    assert not valid_issue_class("upstream_http_99")


def test_quarantine_reason_vocabulary_matches_the_check_constraint():
    for reason in (
        "bad_digest",
        "unknown_predicate",
        "unknown_genre",
        "unknown_subject_scheme",
        "unknown_id_namespace",
    ):
        assert valid_quarantine_reason(reason)
    assert not valid_quarantine_reason("raw_payload")  # payload never surfaces
