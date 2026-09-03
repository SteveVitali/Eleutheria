# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Source disappearance as data, at the connector boundary (§21.4, SIG-INGEST-009/010).

A 404, a removal, or a persistent challenge is one of the most informative things
a connector can observe, so it is recorded as a **first-class event row** and a
**research task**, never handled as a swallowed retryable exception
(SIG-INGEST-009/010). "Which agencies quietly removed their transparency portal"
must be an answerable question, which it only is if disappearance lives in the
data, not the exception path.

The event/task substrate is the evidence store's (:mod:`evidence.disappearance`,
SIG-EVID-013/014); this module is the connector-side classifier that maps a fetch
outcome — an HTTP status or a bot-management challenge — onto the store's failing
``capture_status`` vocabulary and returns both rows together.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from evidence.disappearance import (
    DisappearanceEvent,
    disappearance_task,
    record_disappearance,
)

from .net import ChallengeEncountered

#: HTTP statuses that mean the artifact is gone → link rot (§17.6).
_GONE_STATUSES: dict[int, str] = {404: "link_rotted", 410: "link_rotted"}
#: Statuses that mean access is now restricted rather than the artifact removed.
_RESTRICTED_STATUSES: dict[int, str] = {401: "access_restricted", 451: "access_restricted"}
#: A persistent bot-management challenge is a restricted-access disappearance.
CHALLENGE_STATUS = "access_restricted"


def failing_status_for_http(status: int) -> str | None:
    """Map an HTTP status onto a failing ``capture_status``, or ``None`` if fine.

    404/410 are link rot; 401/451 are access restrictions. A 2xx/3xx is not a
    disappearance. (403/429 arrive as :class:`connectors.net.ChallengeEncountered`,
    not a status here — see :func:`failing_status_for_error`.)
    """
    if status in _GONE_STATUSES:
        return _GONE_STATUSES[status]
    if status in _RESTRICTED_STATUSES:
        return _RESTRICTED_STATUSES[status]
    return None


def failing_status_for_error(error: Exception) -> str | None:
    """Map a fetch error onto a failing ``capture_status``, or ``None``.

    A persistent bot-management challenge (:class:`ChallengeEncountered`) is a
    recorded access restriction — SIG never defeats it (SIG-INGEST-013).
    """
    if isinstance(error, ChallengeEncountered):
        return CHALLENGE_STATUS
    return None


@dataclass(frozen=True)
class Disappearance:
    """A disappearance observation: the event row plus the research task it spawns."""

    event: DisappearanceEvent
    task: dict[str, Any]

    def rows(self) -> dict[str, Any]:
        """The two first-class rows a disappearance writes (SIG-INGEST-009/010)."""
        return {"event": self.event.artifact_update(), "research_task": self.task}


def note_disappearance(
    *,
    artifact_id: str,
    observed_at: datetime,
    failing_status: str,
    subject_id: str | None = None,
) -> Disappearance:
    """Record a disappearance as data: a first-class event **and** a research task.

    This is the connector-boundary counterpart to the exception path: instead of
    raising, a connector calls this and both rows are produced (SIG-INGEST-009/010).
    """
    event = record_disappearance(artifact_id, observed_at, failing_status)
    task = disappearance_task(event, subject_id=subject_id)
    return Disappearance(event=event, task=task)


__all__ = [
    "CHALLENGE_STATUS",
    "Disappearance",
    "failing_status_for_error",
    "failing_status_for_http",
    "note_disappearance",
]
