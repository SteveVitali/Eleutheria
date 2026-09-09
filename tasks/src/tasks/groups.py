# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The SIG-owned local-group registry (§33.7, SIG-TASK-014).

SIG MUST maintain its **own** registry of local surveillance-accountability groups —
name, jurisdiction, URL, contact, activity status, and claimed queues — and MUST NOT
depend on an external directory's availability. (The external directory the outline
named did not respond when tested, F1.9; §33.7.) This module is that registry: a
self-contained, in-memory store with no network dependency, so its availability is
never contingent on a third party. Persisting it is downstream; this ticket owns the
shape and the ownership guarantee.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from enum import StrEnum

__all__ = [
    "ActivityStatus",
    "LocalGroup",
    "LocalGroupRegistry",
]


class ActivityStatus(StrEnum):
    """A local group's activity status (§33.7)."""

    ACTIVE = "active"
    DORMANT = "dormant"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class LocalGroup:
    """A local surveillance-accountability group (§33.7, the registry row).

    Carries every field SIG-TASK-014 enumerates. `claimed_queues` is the set of
    jurisdiction ids the group has claimed (the authoritative, expiring claim
    lifecycle lives in :mod:`tasks.geographic`; this is the registry's denormalised
    view of it). The record is immutable — an update is a new record (SIG-ENG-003),
    via the registry's mutators.
    """

    group_id: str
    name: str
    jurisdiction_id: str
    url: str
    contact: str
    activity_status: ActivityStatus = ActivityStatus.ACTIVE
    claimed_queues: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.group_id:
            raise ValueError(
                "a LocalGroup MUST have a stable group_id (§3.1: every node has identity)"
            )
        if not self.name:
            raise ValueError("a LocalGroup MUST have a name (§33.7)")


class LocalGroupRegistry:
    """SIG's own registry of local groups (SIG-TASK-014).

    In-memory and dependency-free by design: SIG owns this data, so no external
    directory's downtime can make it unavailable. Registration refuses a duplicate
    `group_id`; the mutators return the updated record and keep the store immutable
    per row.
    """

    def __init__(self) -> None:
        self._groups: dict[str, LocalGroup] = {}

    def register(self, group: LocalGroup) -> LocalGroup:
        """Add a group, refusing a duplicate `group_id`."""
        if group.group_id in self._groups:
            raise ValueError(f"local group {group.group_id!r} is already registered")
        self._groups[group.group_id] = group
        return group

    def get(self, group_id: str) -> LocalGroup:
        """The group with `group_id`, or raise `KeyError`."""
        return self._groups[group_id]

    def by_jurisdiction(self, jurisdiction_id: str) -> list[LocalGroup]:
        """Every registered group whose home jurisdiction is `jurisdiction_id`."""
        return [g for g in self._groups.values() if g.jurisdiction_id == jurisdiction_id]

    def update_activity(self, group_id: str, status: ActivityStatus) -> LocalGroup:
        """Set a group's activity status, returning the updated record."""
        updated = replace(self._groups[group_id], activity_status=status)
        self._groups[group_id] = updated
        return updated

    def record_claim(self, group_id: str, jurisdiction_id: str) -> LocalGroup:
        """Note that a group has claimed a jurisdiction's queue (§33.5/§33.7).

        Additive and idempotent: re-recording an existing claim is a no-op. The
        expiring, non-exclusive claim itself is owned by :mod:`tasks.geographic`;
        this only reflects it in the registry view.
        """
        group = self._groups[group_id]
        if jurisdiction_id in group.claimed_queues:
            return group
        updated = replace(group, claimed_queues=(*group.claimed_queues, jurisdiction_id))
        self._groups[group_id] = updated
        return updated

    def __contains__(self, group_id: object) -> bool:
        return group_id in self._groups

    def __iter__(self) -> Iterator[LocalGroup]:
        return iter(self._groups.values())

    def __len__(self) -> int:
        return len(self._groups)
