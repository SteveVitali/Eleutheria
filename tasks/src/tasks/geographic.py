# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Geographic research queues: claims that coordinate, never gatekeep (§33.5).

A local group MAY **claim a jurisdiction**, which grants three things — visibility,
notification, and priority in queue ordering (SIG-TASK-010). It grants a fourth
thing to nobody: **exclusivity**. Any contributor MUST remain able to work any open
task regardless of who has claimed the jurisdiction, and claims MUST expire without
renewal (SIG-TASK-011). The expiry is the safeguard: geographic claiming is a
coordination affordance, and if it hardened into territory it would defeat the
federation principle, so a stale claim simply lapses.

Two invariants are made executable here:

* :func:`any_contributor_may_work` returns whether an *open* task is workable, and it
  is **not a function of any claim or contributor** — there is no code path by which
  a claim can make it `False`. That is non-exclusivity as a property, not a promise.
* :meth:`GeographicQueue.active_claims` filters on `now` against each claim's
  `expires_at`, so a claim past its deadline confers nothing until renewed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .lifecycle import ResearchTask

__all__ = [
    "GeographicClaim",
    "GeographicQueue",
    "any_contributor_may_work",
]


@dataclass(frozen=True)
class GeographicClaim:
    """A local group's time-boxed claim on a jurisdiction (§33.5).

    Carries who claimed (`group_id`), what (`jurisdiction_id`), and the window
    (`claimed_at`..`expires_at`). It is a coordination marker only: it never appears
    in the check for whether a task may be worked.
    """

    jurisdiction_id: str
    group_id: str
    claimed_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.expires_at <= self.claimed_at:
            raise ValueError("a geographic claim MUST expire after it is made (SIG-TASK-011)")

    def is_active(self, now: datetime) -> bool:
        """Whether the claim is still in force at `now` (expires without renewal)."""
        return now < self.expires_at


def any_contributor_may_work(task: ResearchTask) -> bool:
    """Whether any contributor may work this task (SIG-TASK-011).

    True for every **open** task, unconditionally — this function takes no
    contributor and no claim, which is precisely the point: a geographic claim
    cannot gate who works a task. A closed/invalidated task is not workable because
    it has left the queue, not because anyone owns it.
    """
    return task.is_open


class GeographicQueue:
    """Jurisdiction claims and claim-aware task ordering (§33.5).

    Records claims (which expire), reports the visibility/notification set for a
    group, and orders tasks so a claiming group sees its jurisdictions first — a
    priority boost that never becomes exclusion.
    """

    def __init__(self) -> None:
        self._claims: list[GeographicClaim] = []

    def claim(
        self,
        *,
        jurisdiction_id: str,
        group_id: str,
        now: datetime,
        ttl: timedelta,
    ) -> GeographicClaim:
        """Record a group's claim on a jurisdiction for `ttl` (SIG-TASK-010).

        Claiming is additive and non-exclusive: it does not remove or override any
        other group's claim, and it does not lock the jurisdiction. Returns the
        claim.
        """
        if ttl <= timedelta(0):
            raise ValueError("a claim's ttl MUST be positive (SIG-TASK-011)")
        claim = GeographicClaim(
            jurisdiction_id=jurisdiction_id,
            group_id=group_id,
            claimed_at=now,
            expires_at=now + ttl,
        )
        self._claims.append(claim)
        return claim

    def active_claims(self, now: datetime) -> list[GeographicClaim]:
        """Every claim still in force at `now` (lapsed claims are excluded)."""
        return [c for c in self._claims if c.is_active(now)]

    def claimant_groups(self, jurisdiction_id: str, now: datetime) -> frozenset[str]:
        """The groups with an active claim on `jurisdiction_id`."""
        return frozenset(
            c.group_id
            for c in self._claims
            if c.jurisdiction_id == jurisdiction_id and c.is_active(now)
        )

    def has_priority(self, *, group_id: str, jurisdiction_id: str, now: datetime) -> bool:
        """Whether `group_id` holds an active, priority-granting claim here."""
        return group_id in self.claimant_groups(jurisdiction_id, now)

    def visible_jurisdictions(self, group_id: str, now: datetime) -> frozenset[str]:
        """The jurisdictions a group is notified about — its active claims (§33.5)."""
        return frozenset(
            c.jurisdiction_id for c in self._claims if c.group_id == group_id and c.is_active(now)
        )

    def order_for_group(
        self,
        tasks: Iterable[ResearchTask],
        *,
        group_id: str,
        now: datetime,
    ) -> list[ResearchTask]:
        """Order open tasks for a group: its claimed jurisdictions first (SIG-TASK-010).

        A claiming group's tasks sort ahead (the priority the claim grants), then by
        the task's own `priority` descending. This is ordering only — every open task
        remains in the list and remains workable (SIG-TASK-011); nothing is filtered
        out for lacking a claim.
        """
        claimed = self.visible_jurisdictions(group_id, now)
        open_tasks = [t for t in tasks if t.is_open]
        return sorted(
            open_tasks,
            key=lambda t: (0 if t.jurisdiction_id in claimed else 1, -t.priority),
        )
