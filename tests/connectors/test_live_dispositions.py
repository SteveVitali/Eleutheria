# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P25.6 completeness check — every registry source has a live-op disposition.

``data/live_dispositions.toml`` carries exactly one disposition per source that
has no connector mapping; connector-mapped sources MUST NOT appear (their
disposition is "live via <connector>"). A newly-registered source with neither a
connector map entry nor a disposition row fails this file — nothing is silently
unscoped (the defining standard applied to the registry itself, SIG-ENG-001).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from connectors.runner import CONNECTOR_FOR_SOURCE

_SOURCES = Path("connectors/src/connectors/data/sources.toml")
_DISPOSITIONS = Path("connectors/src/connectors/data/live_dispositions.toml")

VALID_DISPOSITIONS = frozenset({"link_only", "reference", "mirror", "promote"})
VALID_TICKETS = frozenset({"P25.2", "P25.3", "P25.4", "P25.5", "P25.6", "P29.3"})


def _source_ids() -> set[str]:
    return set(tomllib.loads(_SOURCES.read_text())["sources"])


def _dispositions() -> dict[str, dict[str, str]]:
    return tomllib.loads(_DISPOSITIONS.read_text()).get("sources", {})


def test_every_source_has_exactly_one_live_op_disposition() -> None:
    source_ids = _source_ids()
    mapped = set(CONNECTOR_FOR_SOURCE) & source_ids
    dispositioned = set(_dispositions()) & source_ids

    # No source is both mapped and dispositioned (one disposition each).
    assert not (mapped & dispositioned), (
        f"connector-mapped sources must not carry a disposition row: "
        f"{sorted(mapped & dispositioned)}"
    )
    # Every source is either mapped or dispositioned — nothing unscoped.
    uncovered = source_ids - mapped - dispositioned
    assert not uncovered, (
        f"sources with no connector and no live-op disposition: {sorted(uncovered)} "
        "— add a row to data/live_dispositions.toml or a CONNECTOR_FOR_SOURCE entry."
    )
    # The table never references unknown sources.
    stale = set(_dispositions()) - source_ids
    assert not stale, f"disposition rows for unregistered sources: {sorted(stale)}"


def test_disposition_values_are_valid() -> None:
    for source_id, row in _dispositions().items():
        disp = row.get("disposition")
        assert disp in VALID_DISPOSITIONS, (
            f"{source_id}: disposition {disp!r} not in {sorted(VALID_DISPOSITIONS)}"
        )
        if disp == "promote":
            # A promoted source must name the class ticket its connector would
            # land under (HG-03 flip is still the prerequisite).
            assert row.get("class_ticket") in VALID_TICKETS, (
                f"{source_id}: promote requires a class_ticket in {sorted(VALID_TICKETS)}"
            )
