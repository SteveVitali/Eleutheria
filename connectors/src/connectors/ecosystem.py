# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The local-group registry and the national partner roster (§22.6 H).

Two ecosystem registries live alongside the source registry:

* **Local groups (SIG-INGEST-039, SIG-TASK-014).** The DeFlock/Eyes-Off local
  groups, recovered from the last surviving archive capture of the ecosystem
  directory and individually re-tested on 2026-08-20. Two coverage facts are
  first-class, not silent drops: groups the outline names but the recovered
  directory does not carry are ``unlocated`` (SIG-INGEST-039a); and
  FlockReporter — the directory itself — is ``disappeared``, its DNS having
  ceased to resolve during the research window (SIG-INGEST-039b), the worked
  justification for the archival-succession offer (§46.5).
* **National partners (SIG-INGEST-040).** Organizations that are consumers and
  contributors rather than data sources, registered with a contact channel so
  outreach and correction-routing have somewhere to go.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from functools import cache
from typing import Any

from ._data import load_table


class GroupStatus(StrEnum):
    """The observed lifecycle state of a local group (§22.6 H)."""

    #: Reachable on 2026-08-20 (200, or 403 = alive behind bot protection).
    ALIVE = "alive"
    #: Named by the outline but absent from the recovered directory (SIG-INGEST-039a).
    UNLOCATED = "unlocated"
    #: Confirmed gone — DNS no longer resolves (SIG-INGEST-039b).
    DISAPPEARED = "disappeared"


@dataclass(frozen=True)
class LocalGroup:
    """A local DeFlock/Eyes-Off group registry row (SIG-INGEST-039/-039a/-039b)."""

    id: str
    name: str
    status: GroupStatus
    url: str = ""
    #: True when a request reached the site on the last-verified date.
    verified: bool = False
    #: 200 vs "alive (403)" — alive behind bot protection is not gone.
    http_status: str = ""
    last_verified: date | None = None
    #: Set only for DISAPPEARED groups (SIG-INGEST-039b).
    disappeared_observed_at: date | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("local group requires an id")
        if not self.name:
            raise ValueError(f"local group {self.id!r} requires a name")
        if self.status is GroupStatus.DISAPPEARED and self.disappeared_observed_at is None:
            raise ValueError(
                f"disappeared group {self.id!r} MUST carry disappeared_observed_at "
                "(SIG-INGEST-039b)."
            )
        if self.status is GroupStatus.UNLOCATED and self.url:
            raise ValueError(
                f"unlocated group {self.id!r} MUST NOT carry a url; its absence is "
                "the coverage fact (SIG-INGEST-039a)."
            )


@dataclass(frozen=True)
class PartnerOrg:
    """A national partner organization (SIG-INGEST-040): consumer/contributor, not a source."""

    id: str
    name: str
    contact: str = ""
    url: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("partner org requires an id")
        if not self.name:
            raise ValueError(f"partner org {self.id!r} requires a name")
        if not self.contact:
            raise ValueError(
                f"partner org {self.id!r} MUST carry a contact channel so outreach "
                "and correction-routing have somewhere to go (SIG-INGEST-040)."
            )


def _local_group_from_row(group_id: str, row: dict[str, Any]) -> LocalGroup:
    lv = row.get("last_verified")
    do = row.get("disappeared_observed_at")
    return LocalGroup(
        id=group_id,
        name=str(row["name"]),
        status=GroupStatus(row.get("status", "alive")),
        url=str(row.get("url", "")),
        verified=bool(row.get("verified", False)),
        http_status=str(row.get("http_status", "")),
        last_verified=lv if isinstance(lv, date) else None,
        disappeared_observed_at=do if isinstance(do, date) else None,
        notes=str(row.get("notes", "")),
    )


@cache
def local_groups() -> dict[str, LocalGroup]:
    """The seeded local-group registry, keyed by id (SIG-INGEST-039, SIG-TASK-014)."""
    table = load_table("local_groups")
    groups: dict[str, LocalGroup] = {}
    for group_id, row in table.get("groups", {}).items():
        if group_id in groups:
            raise ValueError(f"duplicate local group id: {group_id!r}")
        groups[group_id] = _local_group_from_row(group_id, row)
    return groups


@cache
def partners() -> dict[str, PartnerOrg]:
    """The seeded national partner roster, keyed by id (SIG-INGEST-040)."""
    table = load_table("local_groups")
    orgs: dict[str, PartnerOrg] = {}
    for org_id, row in table.get("partners", {}).items():
        if org_id in orgs:
            raise ValueError(f"duplicate partner org id: {org_id!r}")
        orgs[org_id] = PartnerOrg(
            id=org_id,
            name=str(row["name"]),
            contact=str(row.get("contact", "")),
            url=str(row.get("url", "")),
            notes=str(row.get("notes", "")),
        )
    return orgs
