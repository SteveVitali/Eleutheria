# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The local-group registry and partner roster (SIG-INGEST-039/-039a/-039b/-040, SIG-TASK-014)."""

from __future__ import annotations

from datetime import date

from connectors.ecosystem import GroupStatus, local_groups, partners

# --- SIG-INGEST-039 / SIG-TASK-014: the local-group registry is seeded --------


def test_local_group_registry_exists_and_is_seeded() -> None:
    groups = local_groups()
    assert len(groups) >= 12
    # eyesoffcr.org is explicitly required (§22.3, ticket deliverable 6).
    assert "eyes_off_cedar_rapids" in groups
    assert groups["eyes_off_cedar_rapids"].url == "https://eyesoffcr.org/"


def test_alive_groups_from_the_recovered_directory_are_present() -> None:
    groups = local_groups()
    for gid in (
        "deflock_atlanta",
        "deflock_birmingham",
        "deflock_lynnwood",
        "deflock_olympia",
        "deflock_tucson",
        "deflock_vegas",
        "eyes_off_colorado",
        "eyes_off_indiana",
        "live_free_va",
    ):
        assert groups[gid].status is GroupStatus.ALIVE
        assert groups[gid].url


def test_403_is_recorded_as_alive_behind_bot_protection() -> None:
    # A 403 means alive behind bot protection, not gone (SIG-INGEST-039).
    joplin = local_groups()["deflock_joplin"]
    assert joplin.status is GroupStatus.ALIVE
    assert "403" in joplin.http_status


# --- SIG-INGEST-039a: unlocated groups are not silently dropped ---------------


def test_unlocated_groups_are_registered_as_a_coverage_fact() -> None:
    groups = local_groups()
    for gid in ("deflock_idaho", "monterey_park_organizers"):
        assert groups[gid].status is GroupStatus.UNLOCATED
        # Their absence is the fact — no url is asserted.
        assert groups[gid].url == ""


# --- SIG-INGEST-039b: FlockReporter, the directory, is disappeared ------------


def test_flockreporter_directory_is_disappeared_with_observation_date() -> None:
    fr = local_groups()["flockreporter"]
    assert fr.status is GroupStatus.DISAPPEARED
    assert fr.disappeared_observed_at == date(2026, 8, 20)


# --- SIG-INGEST-040: national partners registered with contact channels -------


def test_national_partners_registered_with_contacts() -> None:
    orgs = partners()
    for pid in ("eff", "aclu", "epic", "brennan_center", "stop"):
        assert pid in orgs
        assert orgs[pid].contact, f"{pid} needs a contact channel (SIG-INGEST-040)"
    assert len(orgs) >= 10
