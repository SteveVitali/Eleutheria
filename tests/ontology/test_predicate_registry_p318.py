# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.8 registry completeness against the committed hosted inventory
(`docs/build/reports/p31.8-hosted/predicate_inventory_before.json`):

* every predicate measured on the hosted spine has a registry row;
* every measured (predicate, genre) pair is assessed admissible — a genre that
  actually carries claims for the predicate is probative by construction, so
  D6 there would contradict the connector's own assertion;
* the six genres the hosted spine carries beyond the P31.5 axis are declared;
* the non-adjudication dispositions are recorded explicitly (`never_resolve`),
  not left as silent KeyError-skipped predicates.
"""

from __future__ import annotations

import json

import pytest
from support import REPO_ROOT, generated_dir

INVENTORY = (
    REPO_ROOT / "docs" / "build" / "reports" / "p31.8-hosted" / "predicate_inventory_before.json"
)

MEASURED_NEW_GENRES = {
    "agenda_document",
    "bill_index",
    "portal_document",
    "community_map",
    "contract",
    "official_statement",
}

# Predicates recorded as deliberately not adjudicated (§12.4): registered so the
# resolver emits an explicit NEVER_RESOLVE envelope, not silently skipped.
NOT_ADJUDICATED = {"asset_data_controller", "disclosure_field_state"}


@pytest.fixture(scope="module")
def registry() -> dict:
    return json.loads((generated_dir() / "registry" / "predicate_registry.json").read_text())


@pytest.fixture(scope="module")
def inventory() -> dict:
    assert INVENTORY.exists(), "committed P31.8 before-inventory missing"
    return json.loads(INVENTORY.read_text())


def test_every_measured_predicate_is_registered(registry: dict, inventory: dict) -> None:
    by_id = {p["predicate_id"]: p for p in registry["predicates"]}
    missing = [p["predicate_id"] for p in inventory["predicates"] if p["predicate_id"] not in by_id]
    assert missing == [], f"hosted predicates with no registry row: {missing}"


def test_every_measured_pair_is_admissible(registry: dict, inventory: dict) -> None:
    # A genre that carries claims for a predicate is probative by construction;
    # an assessed cell may be D6 only where the genre never carries the
    # predicate's claims.
    by_id = {p["predicate_id"]: p for p in registry["predicates"]}
    stranded: list[tuple[str, str, int]] = []
    for p in inventory["predicates"]:
        row = by_id[p["predicate_id"]]
        for genre, n in p["claims_by_genre"].items():
            if row["directness"].get(genre, "D6") == "D6":
                stranded.append((p["predicate_id"], genre, n))
    assert stranded == [], f"measured (predicate, genre) pairs still D6: {stranded}"


def test_measured_genres_are_on_the_axis(registry: dict) -> None:
    assert MEASURED_NEW_GENRES <= set(registry["artifact_genres"])


def test_non_adjudication_is_recorded_not_skipped(registry: dict) -> None:
    by_id = {p["predicate_id"]: p for p in registry["predicates"]}
    for pid in NOT_ADJUDICATED:
        assert pid in by_id, pid
        assert by_id[pid]["resolution_strategy"] == "never_resolve", pid
        # a recorded disposition still carries a full directness row — never_resolve
        # is a decision about adjudication, not about evidence bearing.
        assert set(by_id[pid]["directness"]) == set(registry["artifact_genres"])


def test_maps_to_rows_carry_equal_semantics(registry: dict) -> None:
    # P31.8 maps bill/portal/records aliases onto the rows with the same meaning;
    # the mapped row's volatility and strategy must equal its target's.
    by_id = {p["predicate_id"]: p for p in registry["predicates"]}
    for pid, target in (
        ("bill_title", "title"),
        ("bill_matched_keyword", "matched_keyword"),
        ("usage_search_windowed_count", "windowed_search_count"),
        ("response_status", "records_response_status"),
        ("citation", "statutory_citation"),
        ("ordinance_citation", "statutory_citation"),
        ("direction", "camera_direction"),
    ):
        assert by_id[pid].get("maps_to") == target, pid
        assert by_id[pid]["volatility_class"] == by_id[target]["volatility_class"], pid
        assert by_id[pid]["resolution_strategy"] == by_id[target]["resolution_strategy"], pid
