# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Disappearance and link rot (§17.6, SIG-EVID-013/014/015).

When an artifact ceases to be retrievable, SIG records a **disappearance event**
on the artifact — ``disappeared_observed_at`` plus the failing status — and MUST
NOT delete the artifact, its captures, or its claims (SIG-EVID-013). A vanished
portal is one of the most informationally valuable events SIG can observe, so it
is a datum to be recorded, never an error to be retried away.

Disappearance MUST generate a research task (§33.2, SIG-EVID-014) and be visible
as a distinct UI state. A recurring link-rot sweep re-checks ``capture_status`` on
a cadence proportional to source volatility and attempts Wayback registration for
public artifacts SIG is permitted to submit (SIG-EVID-015).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# capture_status values that mean "no longer retrievable" (§17.6, C.3 comment).
FAILING_STATUSES: frozenset[str] = frozenset({"link_rotted", "access_restricted", "paywalled"})
DISAPPEARANCE_TASK_TYPE = "source_disappeared"
_DETECTOR_VERSION = "evidence.disappearance/1"


@dataclass(frozen=True)
class DisappearanceEvent:
    """The event recorded on an artifact — an UPDATE of event columns, never a delete."""

    artifact_id: str
    observed_at: datetime
    failing_status: str

    def __post_init__(self) -> None:
        if self.failing_status not in FAILING_STATUSES:
            raise ValueError(
                f"{self.failing_status!r} is not a failing capture_status "
                f"{sorted(FAILING_STATUSES)}"
            )

    def artifact_update(self) -> dict[str, object]:
        """The ``evidence_artifact`` columns to set (never deletes rows)."""
        return {
            "disappeared_observed_at": self.observed_at,
            "capture_status": self.failing_status,
        }


def record_disappearance(
    artifact_id: str, observed_at: datetime, failing_status: str
) -> DisappearanceEvent:
    """Build a disappearance event (SIG-EVID-013)."""
    return DisappearanceEvent(artifact_id, observed_at, failing_status)


def disappearance_task(
    event: DisappearanceEvent, subject_id: str | None = None
) -> dict[str, object]:
    """The ``research_task`` row a disappearance generates (SIG-EVID-014, §33.2)."""
    return {
        "task_type": DISAPPEARANCE_TASK_TYPE,
        "subject_id": subject_id,
        "priority": 0.8,
        "closing_condition": (
            "artifact is retrievable again OR a replacement source is registered "
            "OR the disappearance is confirmed permanent and annotated"
        ),
        "detector_version": _DETECTOR_VERSION,
        "status": "generated",
    }


def sweep_cadence_days(volatility_class: str) -> int:
    """Re-check cadence proportional to source volatility (SIG-EVID-015)."""
    return {
        "VOLATILE": 1,
        "DYNAMIC": 7,
        "MODERATE": 30,
        "STABLE": 90,
        "IMMUTABLE": 180,
        "GLACIAL": 180,
    }.get(volatility_class.upper(), 30)


def wayback_save_url(url: str) -> str:
    """The Internet Archive 'Save Page Now' URL for a permitted public artifact."""
    return f"https://web.archive.org/save/{url}"
