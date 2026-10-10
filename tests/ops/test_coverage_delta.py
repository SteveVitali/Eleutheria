# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.6 / ACQ-01 — ``coverage-delta``, the I1 blind-spot method as a tool.

A snapshot is a committed ``sig.coverage-snapshot/1`` doc (or the equivalent
CSV); a delta classifies each ``(dimension, key)`` cell added / removed /
changed and marks every change explained or ``UNEXPLAINED`` — "no
unexplained dots" applied to coverage itself. ``--fail-on-unexplained``
turns any unexplained cell into a non-zero exit. The tool is read-only and
never queries ``/v1/coverage`` or the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ops.coverage_delta import (
    DIMENSIONS,
    SNAPSHOT_SCHEMA,
    declared_dimensions,
    delta,
    load_snapshot,
    report_json,
    report_text,
    snapshot_from_source_coverage,
)


def _snapshot(cells: list[dict], label: str = "snap", layer: str = "registry") -> str:
    return json.dumps({"schema": SNAPSHOT_SCHEMA, "label": label, "layer": layer, "cells": cells})


def _write(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def test_snapshot_roundtrip_json(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "s.json",
        _snapshot(
            [
                {
                    "dimension": "state_tier",
                    "key": "US-DE",
                    "covered": True,
                    "evidence": "registry:camreg_de_dot",
                    "tier": "B",
                },
            ]
        ),
    )
    label, cells, layer = load_snapshot(path)
    assert label == "snap" and layer == "registry"
    cell = cells[("state_tier", "US-DE")]
    assert cell.covered and cell.tier == "B"


def test_snapshot_roundtrip_csv(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "s.csv",
        "dimension,key,covered,evidence,tier\ncountry,US,true,registry:x,\ngl1_city,nyc,false,,\n",
    )
    _, cells, layer = load_snapshot(path)
    assert layer == "unknown"
    assert cells[("country", "US")].covered
    assert not cells[("gl1_city", "nyc")].covered


def test_delta_classifies_added_removed_changed() -> None:
    before = {
        ("state_tier", "US-DE"): _cell("state_tier", "US-DE", True, "e1"),
        ("state_tier", "US-VT"): _cell("state_tier", "US-VT", True, "e2"),
        ("country", "US"): _cell("country", "US", True, "e3"),
    }
    after = {
        ("state_tier", "US-DE"): _cell("state_tier", "US-DE", True, "e1"),  # unchanged
        ("state_tier", "US-VT"): _cell("state_tier", "US-VT", False, "e2"),  # removed
        ("country", "US"): _cell("country", "US", True, "e4"),  # changed evidence
        ("country", "CA"): _cell("country", "CA", True, "e5"),  # added
    }
    changes = delta(before, after)
    kinds = {c.key: c.kind for c in changes}
    assert kinds == {"US-VT": "removed", "US": "changed", "CA": "added"}


def _cell(dimension: str, key: str, covered: bool, evidence: str):
    from ops.coverage_delta import Cell

    return Cell(dimension=dimension, key=key, covered=covered, evidence=evidence)


def test_expected_explanations_mark_changes(tmp_path: Path) -> None:
    before = {}
    after = {("blind_spot", "NEW-8"): _cell("blind_spot", "NEW-8", True, "fixture:x")}
    changes = delta(before, after, expected={("blind_spot", "NEW-8"): "AP-T1-001"})
    assert changes[0].explanation == "AP-T1-001"
    changes = delta(before, after)
    assert changes[0].explanation == ""  # UNEXPLAINED


def test_report_marks_unexplained(tmp_path: Path) -> None:
    after = {("state_tier", "US-DC"): _cell("state_tier", "US-DC", True, "registry:x")}
    changes = delta({}, after)
    text = report_text(changes, before_label="a", after_label="b", layer="registry")
    assert "UNEXPLAINED" in text
    assert "1 added" in text
    doc = json.loads(report_json(changes, before_label="a", after_label="b", layer="registry"))
    assert doc["changes"][0]["unexplained"] is True


def test_cli_fail_on_unexplained(tmp_path: Path) -> None:
    from ops.coverage_delta import main

    base = _write(tmp_path / "before.json", _snapshot([], label="before"))
    cur = _write(
        tmp_path / "after.json",
        _snapshot(
            [{"dimension": "country", "key": "US", "covered": True, "evidence": "e"}],
            label="after",
        ),
    )
    assert main(["--baseline", str(base), "--current", str(cur)]) == 0
    assert main(["--baseline", str(base), "--current", str(cur), "--fail-on-unexplained"]) == 2
    expected = _write(
        tmp_path / "exp.json",
        json.dumps({"expected": [{"dimension": "country", "key": "US", "reason": "wave"}]}),
    )
    assert (
        main(
            [
                "--baseline",
                str(base),
                "--current",
                str(cur),
                "--expected",
                str(expected),
                "--fail-on-unexplained",
            ]
        )
        == 0
    )


def test_snapshot_from_source_coverage_labels_registrations_uncovered(
    tmp_path: Path,
) -> None:
    """A permitted-but-never-ingested row is a registration, not coverage."""
    path = _write(
        tmp_path / "sc.csv",
        "source_id,geographies,technology_classes,hosted_claims_evidence\n"
        "src_a,US-DE:Dover,alpr,capture abc landed\n"
        "src_b,US-VT,traffic_camera,none found\n",
    )
    doc = snapshot_from_source_coverage(path)
    cells = {(c["dimension"], c["key"]): c for c in doc["cells"]}
    assert doc["schema"] == SNAPSHOT_SCHEMA
    assert cells[("state_tier", "US-DE")]["covered"] is True
    assert cells[("state_tier", "US-VT")]["covered"] is False
    assert cells[("technology_class", "alpr")]["covered"] is True
    assert cells[("country", "US")]["covered"] is True


def test_committed_dimensions_registry_drives_the_tool() -> None:
    """The DIMENSIONS constant is the committed file's content, never a guess."""
    declared = declared_dimensions()
    assert DIMENSIONS == declared
    assert {
        "blind_spot",
        "state_tier",
        "gl1_city",
        "technology_class",
        "country",
    } == set(declared)


def test_undeclared_dimension_fails_to_load(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "bad.json",
        _snapshot([{"dimension": "made_up_axis", "key": "x", "covered": True, "evidence": "e"}]),
    )
    with pytest.raises(ValueError, match="undeclared dimension"):
        load_snapshot(path)
