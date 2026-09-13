# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Re-ingest cadence, freshness tracking, and disappearance cadence (SCHED.1, GL-SCHED-01).

This is the minimal scheduling seam that closes the P21.3 backlog: it drives
``sig-connectors run`` per source on a cadence that respects source etiquette,
tracks per-source freshness, and runs the disappearance-detection sweep on a
volatility-proportional cadence. It is deliberately a **thin, offline cadence
engine** — the actual crawler-conduct politeness (per-host rate limit, robots,
Overpass 429/504 back-off) lives in the shared :class:`connectors.net.PoliteFetcher`
and ``HttpxTransport`` (P21.3), and the disappearance datum lives in
:mod:`connectors.disappearance` / :mod:`evidence.disappearance`. This module builds
on those seams, it does not duplicate them (ADR-076).

**Two layers of politeness (cadence vs etiquette — ADR-076):**

* *Coarse (this module):* how often a source is re-ingested at all — the per-source
  re-ingest **interval**, derived from the registry ``cadence`` field and clamped to
  an etiquette floor so the scheduler never drives a source faster than once a day.
* *Fine (`PoliteFetcher`):* how requests are paced **within** a run — per-host
  crawl-delay from robots, retry-with-backoff on 429/503/504 honouring ``Retry-After``
  (RISK-P21-04). The scheduler never bypasses it: it invokes the same connector runner
  every other caller uses.

**Append-only (P1–P3).** A re-ingest that observes changed upstream content produces
**new dated claims** (a new release version/digest and retrieval date) and never
overwrites a prior claim; the freshness ledger is an append-only JSONL — a new tick
appends a dated record, it never rewrites one — no in-place mutation, ever.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from connectors.disappearance import (
    Disappearance,
    failing_status_for_error,
    failing_status_for_http,
    note_disappearance,
)
from connectors.registry import SourceRecord, get
from connectors.runner import CONNECTOR_FOR_SOURCE, run_connector_over_fixture
from connectors.stages import ClaimSink, InMemoryClaimSink
from evidence.disappearance import sweep_cadence_days

#: The default re-ingest interval when a source declares no parseable cadence.
#: 30 days == the ``MODERATE`` volatility class (``evidence.disappearance``); a
#: conservative middle that never over-polls an un-characterised civic source.
DEFAULT_INTERVAL_DAYS = 30

#: The etiquette floor: the scheduler NEVER re-ingests a source more than once a
#: day, whatever the free-text cadence says (RISK-P24-01). Sub-day pacing is the
#: job of ``PoliteFetcher`` *within* a run, not of the re-ingest scheduler.
MIN_INTERVAL_DAYS = 1

#: Where the append-only freshness ledger lives by default (dated JSONL per source).
FRESHNESS_DIR = Path("docs/build/freshness")


def _parse_cadence_days(text: str) -> int | None:
    """Map a registry ``cadence`` free-text string onto an interval in days.

    Recognises explicit counts (``"every 7 days"``, ``"14 days"``, ``"3 months"``)
    and the common English cadence words; returns ``None`` when nothing parses so
    the caller can fall back to :data:`DEFAULT_INTERVAL_DAYS`.
    """
    if not text:
        return None
    lowered = text.lower()
    for unit, factor in (("day", 1), ("week", 7), ("month", 30), ("year", 365)):
        match = re.search(rf"(\d+)\s*{unit}", lowered)
        if match:
            return int(match.group(1)) * factor
    for keyword, days in (
        ("hourly", 1),  # clamped up to the daily floor below
        ("daily", 1),
        ("nightly", 1),
        ("fortnight", 14),
        ("biweekly", 14),
        ("weekly", 7),
        ("monthly", 30),
        ("quarter", 90),
        ("annual", 365),
        ("yearly", 365),
    ):
        if keyword in lowered:
            return days
    return None


def reingest_interval_days(source: SourceRecord | str) -> int:
    """The re-ingest interval (days) for ``source``, respecting its etiquette.

    Derived from the source's declared ``cadence`` (defaulting to
    :data:`DEFAULT_INTERVAL_DAYS`) and clamped to the :data:`MIN_INTERVAL_DAYS`
    etiquette floor — so a source that says "hourly" is still only re-ingested
    daily at the scheduler layer, with per-request pacing left to ``PoliteFetcher``.
    """
    record = get(source) if isinstance(source, str) else source
    parsed = _parse_cadence_days(record.cadence)
    interval = DEFAULT_INTERVAL_DAYS if parsed is None else parsed
    return max(interval, MIN_INTERVAL_DAYS)


def disappearance_sweep_days(volatility_class: str = "MODERATE") -> int:
    """The disappearance re-check cadence for a volatility class (SIG-EVID-015).

    Delegates to :func:`evidence.disappearance.sweep_cadence_days` — the single
    source of truth for the sweep cadence — rather than re-encoding the mapping.
    """
    return sweep_cadence_days(volatility_class)


# --- the append-only freshness ledger -----------------------------------------


@dataclass(frozen=True)
class FreshnessRecord:
    """One dated freshness observation for a source (GL-SCHED-01).

    Written once per scheduled ingest; the JSONL ledger only ever appends these,
    so a source's freshness history is a complete, tamper-evident timeline.
    """

    source_id: str
    ingested_at: str
    mode: str
    claim_count: int
    connector: str = ""
    release_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "ingested_at": self.ingested_at,
            "mode": self.mode,
            "claim_count": self.claim_count,
            "connector": self.connector,
            "release_version": self.release_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FreshnessRecord:
        return cls(
            source_id=str(data["source_id"]),
            ingested_at=str(data["ingested_at"]),
            mode=str(data.get("mode", "")),
            claim_count=int(data.get("claim_count", 0)),
            connector=str(data.get("connector", "")),
            release_version=str(data.get("release_version", "")),
        )


class FreshnessLedger:
    """Append-only per-source freshness tracking (GL-SCHED-01, P1–P3).

    Each source's records live in ``<directory>/<source_id>.jsonl``; :meth:`record`
    **appends** a line and never rewrites the file, so a re-ingest can only add to
    a source's history — the same append-only guarantee the claim spine holds.
    """

    def __init__(self, directory: Path | str = FRESHNESS_DIR) -> None:
        self._dir = Path(directory)

    def _path(self, source_id: str) -> Path:
        return self._dir / f"{source_id}.jsonl"

    def record(self, record: FreshnessRecord) -> Path:
        """Append ``record`` to the source's ledger (never overwrites)."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(record.source_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        return path

    def records_for(self, source_id: str) -> list[FreshnessRecord]:
        """Every freshness record for ``source_id``, in write order."""
        path = self._path(source_id)
        if not path.exists():
            return []
        out: list[FreshnessRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(FreshnessRecord.from_dict(json.loads(line)))
        return out

    def last_ingested_at(self, source_id: str) -> datetime | None:
        """The most-recent ingest timestamp for ``source_id`` (``None`` if never)."""
        records = self.records_for(source_id)
        if not records:
            return None
        return max(datetime.fromisoformat(r.ingested_at) for r in records)


# --- the cadence decision -----------------------------------------------------


def is_due(
    source: SourceRecord | str,
    ledger: FreshnessLedger,
    now: datetime | None = None,
    *,
    interval_days: int | None = None,
) -> bool:
    """Whether ``source`` is due for a re-ingest at ``now``.

    A source never ingested is always due; otherwise it is due once its interval
    (from :func:`reingest_interval_days`, or an explicit override) has elapsed
    since the last recorded ingest.
    """
    record = get(source) if isinstance(source, str) else source
    now = now or datetime.now(UTC)
    last = ledger.last_ingested_at(record.id)
    if last is None:
        return True
    interval = interval_days if interval_days is not None else reingest_interval_days(record)
    return now - last >= timedelta(days=interval)


def due_sources(
    ledger: FreshnessLedger,
    now: datetime | None = None,
    candidates: Iterable[SourceRecord | str] | None = None,
) -> list[str]:
    """The source ids due for a re-ingest, in stable order.

    ``candidates`` defaults to the sources the runner knows how to drive
    (``CONNECTOR_FOR_SOURCE``); a caller can narrow it.
    """
    now = now or datetime.now(UTC)
    ids = (
        sorted(CONNECTOR_FOR_SOURCE)
        if candidates is None
        else [c if isinstance(c, str) else c.id for c in candidates]
    )
    return [sid for sid in ids if is_due(sid, ledger, now)]


# --- driving one scheduled re-ingest ------------------------------------------


@dataclass
class ScheduledRunReport:
    """The outcome of one scheduled re-ingest tick for a source."""

    source_id: str
    connector: str
    ran: bool
    claim_count: int = 0
    freshness: FreshnessRecord | None = None
    claims: list[dict[str, Any]] = field(default_factory=list)
    skipped_reason: str | None = None


def run_scheduled_source(
    source_id: str,
    *,
    fixture: Path,
    ledger: FreshnessLedger,
    sink: ClaimSink | None = None,
    connector_name: str | None = None,
    media_type: str = "application/json",
    kind: str = "bulk_file",
    now: datetime | None = None,
    force: bool = False,
) -> ScheduledRunReport:
    """Re-ingest ``source_id`` over ``fixture`` and record its freshness.

    Offline by construction: it drives the connector through
    :func:`connectors.runner.run_connector_over_fixture` (the same eight-stage
    path, PoliteFetcher included) into ``sink`` — a shared :class:`ClaimSink`
    accumulates claims across ticks, so a changed upstream snapshot appends **new
    dated claims** without overwriting the prior ones (append-only). A freshness
    record is appended to ``ledger`` for every tick that runs.

    Unless ``force`` is set, a source not yet due (per :func:`is_due`) is skipped.
    """
    now = now or datetime.now(UTC)
    connector = connector_name or CONNECTOR_FOR_SOURCE.get(source_id)
    if connector is None:
        raise ValueError(
            f"no connector known for source {source_id!r}; pass connector_name "
            f"(known: {sorted(CONNECTOR_FOR_SOURCE)})"
        )

    if not force and not is_due(source_id, ledger, now):
        return ScheduledRunReport(
            source_id=source_id,
            connector=connector,
            ran=False,
            skipped_reason="not due (within the source's re-ingest interval)",
        )

    sink = sink if sink is not None else InMemoryClaimSink()
    report = run_connector_over_fixture(
        connector,
        source_id,
        fixture,
        media_type=media_type,
        kind=kind,
        sink=sink,
    )
    claims = [dict(c) for c in report.claims]
    release_version = ""
    if claims:
        release_version = str(claims[0].get("release_version", ""))
    freshness = FreshnessRecord(
        source_id=source_id,
        ingested_at=now.isoformat(),
        mode="scheduled",
        claim_count=len(claims),
        connector=connector,
        release_version=release_version,
    )
    ledger.record(freshness)
    return ScheduledRunReport(
        source_id=source_id,
        connector=connector,
        ran=True,
        claim_count=len(claims),
        freshness=freshness,
        claims=claims,
    )


# --- disappearance detection on the sweep cadence -----------------------------


def detect_disappearance(
    *,
    artifact_id: str,
    observed_at: datetime,
    http_status: int | None = None,
    error: Exception | None = None,
    subject_id: str | None = None,
) -> Disappearance | None:
    """Turn a scheduled fetch outcome into a disappearance datum, or ``None``.

    A source going dark — a 404/410 (link rot), a 401/451 (access restricted), or
    a persistent bot-management challenge (:class:`connectors.net.ChallengeEncountered`)
    — is recorded as a first-class event + research task via
    :func:`connectors.disappearance.note_disappearance` (SIG-EVID-013/014), never
    swallowed as a retryable error. A healthy 2xx/3xx returns ``None``. This is the
    connector-side classifier reused verbatim — the scheduler only decides *when*
    (the sweep cadence), not *how* (that stays in ``connectors.disappearance``).
    """
    status: str | None = None
    if http_status is not None:
        status = failing_status_for_http(http_status)
    if status is None and error is not None:
        status = failing_status_for_error(error)
    if status is None:
        return None
    return note_disappearance(
        artifact_id=artifact_id,
        observed_at=observed_at,
        failing_status=status,
        subject_id=subject_id,
    )


def disappearance_sweep_due(
    last_swept: datetime | None,
    now: datetime | None = None,
    *,
    volatility_class: str = "MODERATE",
) -> bool:
    """Whether a disappearance re-check sweep is due (volatility-proportional)."""
    now = now or datetime.now(UTC)
    if last_swept is None:
        return True
    return now - last_swept >= timedelta(days=disappearance_sweep_days(volatility_class))


__all__ = [
    "DEFAULT_INTERVAL_DAYS",
    "FRESHNESS_DIR",
    "MIN_INTERVAL_DAYS",
    "FreshnessLedger",
    "FreshnessRecord",
    "ScheduledRunReport",
    "detect_disappearance",
    "disappearance_sweep_days",
    "disappearance_sweep_due",
    "due_sources",
    "is_due",
    "reingest_interval_days",
    "run_scheduled_source",
]
