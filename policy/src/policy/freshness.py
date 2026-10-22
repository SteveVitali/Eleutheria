# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared cadence + freshness-state machinery (P35.33 / J3 §4.6, K9 §5.1 +
§10 C-4…C-7) and the auto-detected issue vocabulary (J3 §7.3).

This module holds **one pure function** so the export, the status lane and
ACT-02's alerting can never disagree about a source's freshness: the same
``freshness_state`` call is evaluated at the release as-of on release pages
and at status time on status pages (K9 C-4 — a release-bound artifact never
carries a reader-current-time value; what ships here is the *cadence rule*,
never a "next run" timestamp).

``freshness_state`` emits the **state** the verdict consumes — the closed
vocabulary ``on_time · late · overdue · never_run · not_scheduled ·
last_run_failed`` plus the C-7 additions ``one_time_load`` and the
``run_record_missing`` flag (a source with published records but no execution
record — never a fabricated run). The full verdict function's refinements
(volatility, staleness, the two change dates) are P35.41's (UX9-2); this row
lands the shared cadence + state inputs.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

#: The closed freshness-state vocabulary (J3 §4.6 item 2 + K9 §5.1 + C-7).
FRESHNESS_STATES: tuple[str, ...] = (
    "on_time",
    "late",
    "overdue",
    "never_run",
    "not_scheduled",
    "last_run_failed",
    "one_time_load",
    "not_applicable",
)

#: Completion statuses that count as a *successful* execution for cadence
#: purposes. A quota-reached run is a success that stopped early; a missing
#: completion ("killed", never recorded) is not.
_SUCCESS_STATUSES = frozenset({"ok", "partial", "quota_reached"})

#: The auto-detected issue classes (J3 §7.3, closed vocabulary). The two
#: open-pattern classes — ``upstream_http_<code>`` and
#: ``quarantine_<reason>`` — are validated by :func:`valid_issue_class`.
AUTO_ISSUE_CLASSES: frozenset[str] = frozenset(
    {
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
    }
)

_ISSUE_CLASS_PATTERNS = (
    re.compile(r"^upstream_http_[0-9]{3}$"),
    re.compile(r"^quarantine_[a-z0-9_]+$"),
)

#: Quarantine reasons recorded by ``assertion_quarantine`` — the CHECK
#: constraint's closed set, verbatim (the reason classes the report's
#: ``refusal_classes`` merges as counts; the payload never leaves
#: restricted). The suffixes a ``quarantine_<reason>`` issue may carry.
_QUARANTINE_REASONS = frozenset(
    {
        "bad_digest",
        "unknown_predicate",
        "unknown_genre",
        "unknown_subject_scheme",
        "unknown_object_type",
        "unknown_value_kind",
        "missing_capture_binding",
        "unsupported_locator",
        "extractor_failure",
        "version_mismatch",
        "missing_required_field",
        "unknown_qualifier",
        "unknown_id_namespace",
    }
)


def valid_issue_class(cls: str) -> bool:
    """Whether ``cls`` is in the closed J3 §7.3 auto-issue vocabulary."""
    return cls in AUTO_ISSUE_CLASSES or any(p.match(cls) for p in _ISSUE_CLASS_PATTERNS)


def valid_quarantine_reason(reason: str) -> bool:
    """Whether ``reason`` is a recorded ``assertion_quarantine`` reason class."""
    return reason in _QUARANTINE_REASONS


@dataclass(frozen=True)
class FreshnessState:
    """The state one ``freshness_state`` call emits — the inputs P35.41's
    verdict and ACT-02's alerting consume.

    ``state`` is one of :data:`FRESHNESS_STATES` (or ``None`` when the
    cadence basis is unrecorded — honest absence, never a guessed state).
    ``run_record_missing`` is the C-7 flag: published records exist but no
    execution record does. ``evaluated_at`` is the instant the state was
    evaluated against — every emitted freshness value carries its
    evaluation time (SIG-TRANSP-D29's one-function rule).
    """

    state: str | None
    run_record_missing: bool
    evaluated_at: datetime


# ---------------------------------------------------------------------------
# The cadence rule (K9 C-4) — a release-bound fact, never a "next run" stamp
# ---------------------------------------------------------------------------

_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _cron_field(field: str, lo: int, hi: int) -> list[int] | None:
    """Parse one 5-field-cron segment into sorted values; ``None`` if the
    segment shape is unsupported (we never guess a schedule)."""
    values: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        if not part:
            return None
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            if not step_s.isdigit() or int(step_s) < 1:
                return None
            step = int(step_s)
        if part == "*":
            values.update(range(lo, hi + 1, step))
        elif part.isdigit():
            values.add(int(part))
            if step != 1:
                return None
        elif re.fullmatch(r"\d+-\d+", part):
            a, b = (int(x) for x in part.split("-"))
            values.update(range(a, b + 1, step))
        else:
            return None
    vals = sorted(v for v in values if lo <= v <= hi)
    return vals or None


def cron_fields(cron: str) -> tuple[list[int], ...] | None:
    """Parse a standard 5-field cron (minute hour dom month dow) into
    per-field value lists; ``None`` for shapes we cannot evidence."""
    parts = cron.split()
    if len(parts) != 5:
        return None
    minute = _cron_field(parts[0], 0, 59)
    hour = _cron_field(parts[1], 0, 23)
    dom = _cron_field(parts[2], 1, 31)
    month = _cron_field(parts[3], 1, 12)
    dow = _cron_field(parts[4], 0, 7)
    if None in (minute, hour, dom, month, dow):
        return None
    # cron's 0 and 7 both mean Sunday — normalise 7 → 0.
    dow = sorted({0 if d == 7 else d for d in dow or []})
    return (minute or [], hour or [], dom or [], month or [], dow or [])


def cadence_rule(cron: str, cadence: str = "") -> str:
    """Render the declared cadence as the release-bound **rule** (K9 C-4).

    ``"0 5 6 * *"`` → ``"monthly, day 6"``; ``"12 4 * * 1"`` →
    ``"weekly, Monday"``. Never a "next run" timestamp — release pages show
    the rule; the status lane alone owns next-run values. Where the cron
    shape is not one we can evidence, the declared cadence word stands;
    absent both, an honest "custom schedule" label — never a guessed rule.
    """
    fields = cron_fields(cron)
    if fields is not None:
        minute, hour, dom, month, dow = fields
        dom_all = len(dom) == 31
        month_all = len(month) == 12
        dow_all = len(dow) == 7
        hour_all = len(hour) == 24
        if len(dom) == 1 and month_all and dow_all:
            return f"monthly, day {dom[0]}"
        if len(dom) == 1 and month == [1, 4, 7, 10] and dow_all:
            return f"quarterly, day {dom[0]} of Jan, Apr, Jul, Oct"
        if len(dom) == 1 and not month_all and dow_all:
            names = ", ".join(_MONTHS[m - 1] for m in month)
            return f"yearly, day {dom[0]} of {names}"
        if dom_all and month_all and len(dow) == 1:
            return f"weekly, {_WEEKDAYS[(dow[0] + 6) % 7]}"
        if dom_all and month_all and dow_all:
            if hour_all and len(minute) > 1:
                return f"every {60 // max(len(minute), 1)} minutes"
            if hour_all and len(minute) == 1:
                return "hourly"
            if len(hour) > 1 and len(minute) == 1:
                return (
                    f"every {24 // len(hour)} hours" if 24 % len(hour) == 0 else "custom schedule"
                )
            if len(hour) == 1:
                return "daily"
    word = cadence.strip().lower()
    if word:
        return word
    return "custom schedule"


def cadence_interval(cron: str, cadence: str = "") -> timedelta | None:
    """The nominal cadence interval the grace/late/overdue rules measure
    against — from the declared cadence word, else inferred from the cron
    shape; ``None`` where neither evidences one."""
    word = cadence.strip().lower()
    nominal = {
        "hourly": timedelta(hours=1),
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "monthly": timedelta(days=30.44),
        "quarterly": timedelta(days=91.31),
        "yearly": timedelta(days=365.25),
        "annual": timedelta(days=365.25),
    }
    if word in nominal:
        return nominal[word]
    fields = cron_fields(cron)
    if fields is None:
        return None
    minute, hour, dom, month, dow = fields
    dom_all, month_all, dow_all, hour_all = (
        len(dom) == 31,
        len(month) == 12,
        len(dow) == 7,
        len(hour) == 24,
    )
    if len(dom) == 1 and dow_all:
        return timedelta(days=30.44) if month_all else timedelta(days=91.31)
    if dom_all and month_all and len(dow) == 1:
        return timedelta(weeks=1)
    if dom_all and month_all and dow_all:
        if hour_all:
            return timedelta(hours=24 / max(len(minute), 1))
        if len(hour) > 1:
            return timedelta(hours=24 / len(hour))
        if len(hour) == 1:
            return timedelta(days=1)
    return None


def previous_cron_fire(cron: str, at: datetime) -> datetime | None:
    """The most recent instant the cron fired strictly before ``at`` —
    ``None`` for unevidenced shapes. Day granularity over at most 400 days
    back (covers quarterly/annual rules); standard cron dom/dow-OR
    semantics apply."""
    fields = cron_fields(cron)
    if fields is None:
        return None
    minute, hour, dom, month, dow = fields
    at = at.astimezone(UTC)
    dom_all, dow_all = len(dom) == 31, len(dow) == 7
    best: datetime | None = None
    day = at.date()
    for back in range(0, 401):
        d = day - timedelta(days=back)
        if d.month not in month:
            continue
        dom_hit = d.day in dom
        dow_hit = ((d.weekday() + 1) % 7) in dow  # python Mon=0 → cron Sun=0
        match = (
            (dom_hit or dow_hit)
            if not (dom_all or dow_all)
            else ((dom_hit or dom_all) and (dow_hit or dow_all))
        )
        if not match:
            continue
        for h in hour:
            for m in minute:
                fire = datetime(d.year, d.month, d.day, h, m, tzinfo=UTC)
                if fire < at and (best is None or fire > best):
                    best = fire
        if best is not None:
            return best
    return best


# ---------------------------------------------------------------------------
# The freshness-state function (one shared function — J3 §4.6 item 2, C-7)
# ---------------------------------------------------------------------------


def freshness_state(
    *,
    cadence_cron: str | None,
    cadence_word: str = "",
    scheduled: bool,
    one_time_load: bool = False,
    applicable: bool = True,
    has_records: bool = False,
    executions: Sequence[Mapping[str, Any]] = (),
    at: datetime,
) -> FreshnessState:
    """Compute the freshness state — one pure function shared by the export,
    the status lane and ACT-02 alerting (J3 §4.6; K9 §5.1 + C-7).

    ``executions`` are the source's execution rows newest-first or any order
    — each mapping carries ``finished_at`` (datetime|None) and ``status``
    (the completion vocabulary; ``None`` = no completion recorded, treated
    as not-successful). ``at`` is the evaluation instant (the release as-of
    on release artifacts — never the reader's now).

    Precedence (K9 §5.1's table, documented): static classes
    (``not_scheduled``/``one_time_load``/``not_applicable``) → ``never_run``
    → ``last_run_failed`` (the latest execution failed or never completed —
    "even if within interval") → ``overdue`` → ``late`` → ``on_time``.
    """
    at = at if at.tzinfo is not None else at.replace(tzinfo=UTC)
    run_record_missing = bool(has_records) and not executions

    def done(state: str | None) -> FreshnessState:
        return FreshnessState(state=state, run_record_missing=run_record_missing, evaluated_at=at)

    if not applicable:
        return done("not_applicable")
    if one_time_load:
        return done("one_time_load")
    if not scheduled:
        return done("not_scheduled")
    if not executions:
        return done("never_run")

    def _fin(e: Mapping[str, Any]) -> datetime:
        f = e.get("finished_at")
        if isinstance(f, datetime):
            return f if f.tzinfo is not None else f.replace(tzinfo=UTC)
        return datetime.min.replace(tzinfo=UTC)

    ordered = sorted(executions, key=_fin, reverse=True)
    latest = ordered[0]
    latest_status = latest.get("status")
    if latest_status not in _SUCCESS_STATUSES:
        # "last_run_failed: the latest execution failed (even if within
        # interval)" — a killed run (no completion) is not a success either.
        return done("last_run_failed")

    last_success_at = _fin(latest)
    interval = cadence_interval(cadence_cron or "", cadence_word)
    expected = previous_cron_fire(cadence_cron, at) if cadence_cron else None
    if interval is None and expected is None:
        # No interval is evidenced — the static facts above still stand but
        # the time-based verdict cannot be computed; honest absence.
        return done(None)
    if interval is not None and at - last_success_at > 2 * interval:
        return done("overdue")
    if expected is not None:
        grace = (interval / 2) if interval is not None else timedelta(0)
        if last_success_at < expected and at > expected + grace:
            return done("late")
        return done("on_time")
    assert interval is not None
    if at - last_success_at > interval + interval / 2:
        return done("late")
    return done("on_time")
