# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The SIG-owned local-group registry (§33.7).

SIG-TASK-014: SIG maintains its own registry (name, jurisdiction, URL, contact,
activity status, claimed queues) and does not depend on an external directory.
"""

from __future__ import annotations

import pytest
from tasks.groups import ActivityStatus, LocalGroup, LocalGroupRegistry


def _group(group_id: str = "deflock:okc", jurisdiction: str = "jur:ok") -> LocalGroup:
    return LocalGroup(
        group_id=group_id,
        name="DeFlock OKC",
        jurisdiction_id=jurisdiction,
        url="https://example.org/okc",
        contact="okc@example.org",
    )


def test_registry_carries_every_sig_task_014_field() -> None:
    registry = LocalGroupRegistry()
    group = registry.register(_group())
    stored = registry.get("deflock:okc")
    assert stored is group
    assert stored.name == "DeFlock OKC"
    assert stored.jurisdiction_id == "jur:ok"
    assert stored.url == "https://example.org/okc"
    assert stored.contact == "okc@example.org"
    assert stored.activity_status is ActivityStatus.ACTIVE
    assert stored.claimed_queues == ()


def test_registry_is_self_contained_no_external_dependency() -> None:
    """SIG-TASK-014: the registry works with no network/external directory."""
    registry = LocalGroupRegistry()
    registry.register(_group("g1", "jur:ok"))
    registry.register(_group("g2", "jur:ok"))
    registry.register(_group("g3", "jur:tx"))
    # Every read is served from SIG's own store.
    assert len(registry) == 3
    assert {g.group_id for g in registry.by_jurisdiction("jur:ok")} == {"g1", "g2"}


def test_duplicate_group_is_refused() -> None:
    registry = LocalGroupRegistry()
    registry.register(_group())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_group())


def test_activity_status_update_is_immutable_per_row() -> None:
    registry = LocalGroupRegistry()
    original = registry.register(_group())
    updated = registry.update_activity("deflock:okc", ActivityStatus.DORMANT)
    assert updated.activity_status is ActivityStatus.DORMANT
    # The original record object was not mutated (a change is a new record).
    assert original.activity_status is ActivityStatus.ACTIVE
    assert registry.get("deflock:okc").activity_status is ActivityStatus.DORMANT


def test_recording_a_claim_is_additive_and_idempotent() -> None:
    registry = LocalGroupRegistry()
    registry.register(_group())
    registry.record_claim("deflock:okc", "jur:ok")
    registry.record_claim("deflock:okc", "jur:tx")
    registry.record_claim("deflock:okc", "jur:ok")  # idempotent
    assert registry.get("deflock:okc").claimed_queues == ("jur:ok", "jur:tx")


def test_a_group_needs_an_identity_and_name() -> None:
    with pytest.raises(ValueError, match="group_id"):
        LocalGroup(group_id="", name="x", jurisdiction_id="j", url="u", contact="c")
    with pytest.raises(ValueError, match="name"):
        LocalGroup(group_id="g", name="", jurisdiction_id="j", url="u", contact="c")
