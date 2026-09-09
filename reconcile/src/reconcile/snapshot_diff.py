# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Snapshot-diff reconciliation (§29.7, SIG-RECON-045).

Consecutive captures of the same artifact are diffed at the **extracted-field
level**, producing per-field change events that carry **both values and both
dates**. This is what makes "what changed, and when" answerable, and it is the
basis of the ``/changes`` feed (SIG-API-009) and of several research-task detectors
(P10.1).

This module is the **sole owner** of the per-field snapshot-diff event format
(SIG-RECON-045); downstream tickets (P11.1 portal snapshots, the change feed)
consume :class:`FieldChangeEvent` and MUST NOT re-implement the diff.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

#: The three field-level change kinds.
ADDED = "added"
REMOVED = "removed"
MODIFIED = "modified"

#: A sentinel distinguishing "field absent" from "field present and set to None".
_ABSENT = object()


@dataclass(frozen=True)
class Capture:
    """One dated capture of an artifact, reduced to its extracted fields.

    ``fields`` maps an extracted-field name to its value at capture time; a field
    absent from the mapping is absent from the capture (distinct from present-and-
    ``None``).
    """

    artifact_id: str
    capture_digest: str
    captured_at: date
    fields: dict[str, object]


@dataclass(frozen=True)
class FieldChangeEvent:
    """A per-field change between two consecutive captures (SIG-RECON-045).

    Carries **both** values and **both** dates so "what changed, and when" is
    answerable from the event alone. For an ``added`` field ``old_value`` is
    ``None``; for a ``removed`` field ``new_value`` is ``None``.
    """

    artifact_id: str
    field: str
    change_type: str
    old_value: object
    new_value: object
    old_date: date
    new_date: date
    old_capture_digest: str
    new_capture_digest: str


def diff_captures(previous: Capture, current: Capture) -> tuple[FieldChangeEvent, ...]:
    """Diff two consecutive captures at the extracted-field level (SIG-RECON-045).

    Returns one :class:`FieldChangeEvent` per changed field (added / removed /
    modified), sorted by field name for a deterministic feed. Fields present with
    equal values in both captures produce no event.
    """
    if previous.artifact_id != current.artifact_id:
        raise ValueError(
            f"cannot diff captures of different artifacts "
            f"({previous.artifact_id!r} vs {current.artifact_id!r})"
        )
    events: list[FieldChangeEvent] = []
    for field in sorted(set(previous.fields) | set(current.fields)):
        old = previous.fields.get(field, _ABSENT)
        new = current.fields.get(field, _ABSENT)
        if old is _ABSENT and new is not _ABSENT:
            change_type, old_out, new_out = ADDED, None, new
        elif old is not _ABSENT and new is _ABSENT:
            change_type, old_out, new_out = REMOVED, old, None
        elif old != new:
            change_type, old_out, new_out = MODIFIED, old, new
        else:
            continue
        events.append(
            FieldChangeEvent(
                artifact_id=current.artifact_id,
                field=field,
                change_type=change_type,
                old_value=old_out,
                new_value=new_out,
                old_date=previous.captured_at,
                new_date=current.captured_at,
                old_capture_digest=previous.capture_digest,
                new_capture_digest=current.capture_digest,
            )
        )
    return tuple(events)


def diff_series(captures: Sequence[Capture]) -> tuple[FieldChangeEvent, ...]:
    """Diff a chronological series of captures pairwise (the change-feed source).

    Captures are ordered by ``captured_at`` (ties broken by ``capture_digest`` for
    determinism) and diffed consecutively; the concatenated events are the raw
    material of the ``/changes`` feed (SIG-API-009).
    """
    ordered = sorted(captures, key=lambda c: (c.captured_at, c.capture_digest))
    events: list[FieldChangeEvent] = []
    for previous, current in zip(ordered, ordered[1:], strict=False):
        events.extend(diff_captures(previous, current))
    return tuple(events)


__all__ = [
    "ADDED",
    "MODIFIED",
    "REMOVED",
    "Capture",
    "FieldChangeEvent",
    "diff_captures",
    "diff_series",
]
