# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The cadence window of a scheduled run: its logical-run key (P31.4 / ADR-111).

A restarted execution resumes an interrupted one only when both belong to the
same **logical run**: the same source in the same cadence window. The window is
the interval since the source's cron last fired, so

* a re-execution after a crash, a cancel or a task timeout, before the next
  scheduled fire, has the same key and resumes; and
* the next scheduled fire opens a new window, a new key, and never skips a page
  (a fresh cadence run re-fetches everything, so disappearance detection and
  freshness are unchanged).

The key is ``<source>@<last fire, UTC, minute precision>``. The cron grammar is the
five-field subset ``ops/cadence.toml`` uses: ``*``, numbers, lists, ranges and
``*/n`` steps. As in Vixie cron, a restricted day-of-month and a restricted
day-of-week match either one. Pure functions, no I/O.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from .scheduled import CadenceConfig

#: How far back :func:`previous_fire` searches. Every ``cadence.toml`` cron fires at
#: least quarterly; a year covers any of them with room to spare.
_MAX_LOOKBACK_DAYS = 400

_FIELDS = (("minute", 0, 59), ("hour", 0, 23), ("day", 1, 31), ("month", 1, 12), ("dow", 0, 7))


class CronError(ValueError):
    """A cron expression outside the supported five-field grammar."""


def _parse_field(text: str, low: int, high: int) -> frozenset[int]:
    values: set[int] = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, step_text = part.split("/", 1)
            step = int(step_text)
            if step < 1:
                raise CronError(f"bad step in {text!r}")
        if part == "*":
            start, end = low, high
        elif "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = end = int(part)
            if step != 1:
                end = high
        if not (low <= start <= end <= high):
            raise CronError(f"{text!r} is outside {low}-{high}")
        values.update(range(start, end + 1, step))
    return frozenset(values)


def parse_cron(cron: str) -> tuple[frozenset[int], ...]:
    """Parse a five-field cron into (minutes, hours, days, months, weekdays).

    Weekdays use ``0``-``6`` for Sunday-Saturday (``7`` is also Sunday).
    """
    fields = cron.split("#", 1)[0].split()
    if len(fields) != 5:
        raise CronError(f"expected 5 cron fields, got {len(fields)} in {cron!r}")
    try:
        parsed = [_parse_field(f, lo, hi) for f, (_, lo, hi) in zip(fields, _FIELDS, strict=True)]
    except ValueError as exc:
        raise CronError(f"unparseable cron {cron!r}: {exc}") from exc
    dow = frozenset(0 if d == 7 else d for d in parsed[4])
    return parsed[0], parsed[1], parsed[2], parsed[3], dow


def _day_matches(cron: str, day: date, fields: tuple[frozenset[int], ...]) -> bool:
    _, _, days, months, dows = fields
    if day.month not in months:
        return False
    dom_field, dow_field = cron.split()[2], cron.split()[4]
    in_dom = day.day in days
    in_dow = (day.isoweekday() % 7) in dows
    if dom_field != "*" and dow_field != "*":
        return in_dom or in_dow
    return in_dom and in_dow


def previous_fire(cron: str, now: datetime) -> datetime:
    """The latest time at or before ``now`` (UTC) at which ``cron`` fires."""
    fields = parse_cron(cron)
    minutes, hours = sorted(fields[0], reverse=True), sorted(fields[1], reverse=True)
    now = now.astimezone(UTC).replace(second=0, microsecond=0)
    clean = " ".join(cron.split("#", 1)[0].split())
    for back in range(_MAX_LOOKBACK_DAYS):
        day = now.date() - timedelta(days=back)
        if not _day_matches(clean, day, fields):
            continue
        for hour in hours:
            for minute in minutes:
                fire = datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
                if fire <= now:
                    return fire
    raise CronError(f"{cron!r} did not fire in the {_MAX_LOOKBACK_DAYS} days before {now}")


def cron_for_source(config: CadenceConfig, source_id: str) -> str | None:
    """The cron that schedules ``source_id``: its own row, else its batch's."""
    for row in config.sources:
        if row.source == source_id:
            return row.cron
    for batch in config.batches:
        if source_id in batch.members:
            return batch.cron
    return None


def logical_run_key(source_id: str, cron: str, now: datetime) -> str:
    """``<source>@<last fire>``: the resume key of a run of ``source_id`` at ``now``."""
    return f"{source_id}@{previous_fire(cron, now):%Y-%m-%dT%H:%MZ}"


__all__ = [
    "CronError",
    "cron_for_source",
    "logical_run_key",
    "parse_cron",
    "previous_fire",
]
