# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The flock_portal change-feed driver (P37.5b; SIG-INGEST-035, §17.6).

The connector's change-detection halves — :func:`flock_portal.is_poll_due`,
:func:`flock_portal.portal_capture`, :func:`flock_portal.diff_portal_snapshots`
and :func:`flock_portal.detect_portal_changes` — are pure functions a driver
invokes; this module **is** that driver (the P37.5a unwired-scan adjudicated
them ``capability-half`` owned by this row). Given the previous and current
parsed aggregator snapshots it produces one deterministic feed:

* ``poll_due`` — whether polling the upstream is due at ``now``, keyed on the
  upstream's declared snapshot and refresh cadence (SIG-INGEST-030c), never on
  wall-clock fetch time;
* ``rows`` — the appearance/disappearance event rows (``portal_exists`` claims)
  and the research tasks they spawn (``source_disappeared`` /
  ``flock_portal_appeared``), emitted in the connector's normalized record
  shape so the claim path and the research-queue writer consume them as-is;
* ``field_events`` — the per-field :class:`reconcile.snapshot_diff.FieldChangeEvent`
  stream across the snapshots' shared portals (SIG-RECON-045 — the extracted-
  field diff, never raw bytes).

The feed is pure: every input is a parameter, every date comes from the
snapshots or the explicit ``now``/``last_observed_snapshot`` arguments. The
``sig-tasks portal-changes`` verb drives it over two captured snapshots and,
with ``--dsn``, persists the research-task rows through
:mod:`tasks.disappearance_pg` — the persisted event feed the adjudication named.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from reconcile.snapshot_diff import FieldChangeEvent

from .flock_portal import (
    detect_portal_changes,
    diff_portal_snapshots,
    is_poll_due,
    parse_json,
    portal_capture,
    portal_slugs,
    portal_snapshot_date,
)

SCHEMA = "sig.portal-changes/1"


def snapshot_of(parsed: Mapping[str, Any]) -> date | None:
    """One response's upstream snapshot date — the freshest declared
    ``data_last_updated`` across its portals (the upstream's own clock,
    SIG-INGEST-030c; ``None`` when no portal declares one)."""
    dates = [
        d
        for p in parsed.get("portals", [])
        if isinstance(p, Mapping)
        for d in [portal_snapshot_date(p)]
        if d is not None
    ]
    return max(dates) if dates else None


def _portal_by_slug(parsed: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """The ``{slug: portal}`` map for one parsed response (deduped, ordered)."""
    slug_of = {slug: i for i, slug in enumerate(portal_slugs(parsed))}
    out: dict[str, Mapping[str, Any]] = {}
    for portal in parsed.get("portals", []):
        if not isinstance(portal, Mapping):
            continue
        slug = str(portal.get("slug", "")).strip()
        if slug in slug_of and slug not in out:
            out[slug] = portal
    return out


@dataclass
class PortalChangeFeed:
    """The deterministic change feed between two aggregator snapshots."""

    poll_due: bool
    previous_snapshot: date | None
    current_snapshot: date | None
    appeared: tuple[str, ...]
    disappeared: tuple[str, ...]
    rows: list[dict[str, Any]]
    field_events: tuple[FieldChangeEvent, ...]

    def task_rows(self) -> list[dict[str, Any]]:
        """The ``record_kind='research_task'`` subset — what the queue persists."""
        return [r for r in self.rows if r.get("record_kind") == "research_task"]

    def claim_rows(self) -> list[dict[str, Any]]:
        """The ``record_kind='claim'`` subset — the ``portal_exists`` events."""
        return [r for r in self.rows if r.get("record_kind") == "claim"]

    def as_dict(self) -> dict[str, Any]:
        """The ``sig.portal-changes/1`` report (JSON-serialisable)."""
        return {
            "schema": SCHEMA,
            "poll_due": self.poll_due,
            "previous_snapshot": (
                self.previous_snapshot.isoformat() if self.previous_snapshot else None
            ),
            "current_snapshot": (
                self.current_snapshot.isoformat() if self.current_snapshot else None
            ),
            "appeared": list(self.appeared),
            "disappeared": list(self.disappeared),
            "rows": [
                {k: (v.isoformat() if isinstance(v, date) else v) for k, v in r.items()}
                for r in self.rows
            ],
            "field_events": [
                {
                    "artifact_id": e.artifact_id,
                    "field": e.field,
                    "change_type": e.change_type,
                    "old_value": e.old_value,
                    "new_value": e.new_value,
                    "old_date": e.old_date.isoformat(),
                    "new_date": e.new_date.isoformat(),
                    "old_capture_digest": e.old_capture_digest,
                    "new_capture_digest": e.new_capture_digest,
                }
                for e in self.field_events
            ],
        }


def load_snapshot(path: Path | str) -> dict[str, Any]:
    """Parse one captured aggregator response (a pure function of the bytes)."""
    return parse_json(Path(path).read_bytes())


def portal_change_feed(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    previous_capture_digest: str = "",
    current_capture_digest: str = "",
    now: date,
    last_observed_snapshot: date | None = None,
    attribution: str = "",
) -> PortalChangeFeed:
    """Drive the change-detection halves over two snapshots → the feed.

    ``previous`` may be ``None`` (the first observed snapshot — every portal
    counts as appeared). ``now`` and ``last_observed_snapshot`` feed ONLY the
    poll-due decision; event ``observed_at`` values always come from the
    snapshots' own declared dates (SIG-INGEST-030c).
    """
    prev_parsed = previous or {"summary": {}, "portals": []}
    previous_snapshot = snapshot_of(prev_parsed)
    current_snapshot = snapshot_of(current)
    poll_due = is_poll_due(current_snapshot, now, last_observed_snapshot)

    prev_slugs = portal_slugs(prev_parsed)
    cur_slugs = portal_slugs(current)
    appeared = tuple(sorted(set(cur_slugs) - set(prev_slugs)))
    disappeared = tuple(sorted(set(prev_slugs) - set(cur_slugs)))

    # SIG-INGEST-018: no wall-clock in a claim value — when the upstream
    # declares no snapshot date the event rows carry observed_at absent
    # (portal_exists_claim tolerates it), never the run's clock.
    rows = detect_portal_changes(
        prev_slugs,
        cur_slugs,
        current_snapshot_date=current_snapshot,
        previous_snapshot_date=previous_snapshot,
        attribution=attribution,
    )

    prev_by_slug = _portal_by_slug(prev_parsed)
    cur_by_slug = _portal_by_slug(current)
    field_events: list[FieldChangeEvent] = []
    for slug in sorted(set(prev_slugs) & set(cur_slugs)):
        # A portal with no parseable snapshot date yields no dated capture —
        # honestly undated upstream data produces no field events, never a
        # crash or a guessed date (§3.1).
        try:
            before = portal_capture(prev_by_slug[slug], capture_digest=previous_capture_digest)
            after = portal_capture(cur_by_slug[slug], capture_digest=current_capture_digest)
        except ValueError:
            continue
        field_events.extend(diff_portal_snapshots([before, after]))

    return PortalChangeFeed(
        poll_due=poll_due,
        previous_snapshot=previous_snapshot,
        current_snapshot=current_snapshot,
        appeared=appeared,
        disappeared=disappeared,
        rows=rows,
        field_events=tuple(field_events),
    )


def canonical_json(obj: Mapping[str, Any]) -> str:
    """The report's canonical serialisation (stable key order, newline end)."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


__all__ = [
    "SCHEMA",
    "PortalChangeFeed",
    "canonical_json",
    "load_snapshot",
    "portal_change_feed",
    "snapshot_of",
]
