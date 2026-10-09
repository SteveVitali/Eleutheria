#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``acceptance_report.py`` (P34.47; plan §13.1; SIG-MEM-011).

Invariants on small committed fixtures, never a living record (OM-15): a
row never reports above the layer its evidence cell claims in its head
(the "owed to D-…" trap), every 11A chain row appears exactly once, exit
items verdict honestly (queued while the sweep leg is queued, never a
fabricated live pass), and the OM-19 due evaluation distinguishes due /
conditional / indeterminate / awaiting-go / waiting.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import acceptance_report as ar  # noqa: E402

TOOL = HERE / "acceptance_report.py"
REPO = HERE.parents[2]
PYTHON = sys.executable

MANIFEST = """\
## The chain

| # | file | ph | kind | lane | scope | deps |
|---|---|---|---|---|---|---|
| 201 | `201_P34.1__a.md` | 34 | ticket | C | x | none |
| 202 | `202_P34.2__b.md` | 34 | ticket | C | x | none |
| 259 | `259_P34.47__c.md` | 34 | capstone | C | x | none |

## Later
"""

INDEX = """\
## Round 11

| # | ticket | kind | branch | pr | base | date | adr | oblig | status | paths | harness |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 201 | P34.1 | ticket | b | #1 | base | 2026-01-01 | — | none | engineered + fixture-verified (`x`): detail · ci: pass #1@abc | paths | h |
| 202 | P34.2 | ticket | b | #2 | base | 2026-01-01 | — | none | engineered + fixture-verified + live-executed (`x`): the live-executed half owed to `D-X` is queued · ci: pass #2@def | paths | h |

## Row corrections
| 259 | P34.47 | ticket | b | #9 | base | 2026-01-01 | — | none | engineered (`x`) · ci: pass #9@ghi | paths | h |
"""

MAP = """\
[[row]]
key = "P34.46"
  [[row.legs]]
  id = "P34.46-slot"
  earliest = "2026-10-14T14:00Z"
  go = "verbatim-go: the in-ticket operator go"
  [[row.legs]]
  id = "P34.46-soak"
  earliest = "48 h after a successful L2"
  go = "none — the soak runs on a completed L2"
[[row]]
key = "P34.40"
  [[row.legs]]
  id = "P34.40-web-roll"
  earliest = "2026-10-13T12:00Z"
  go = "pre-authorised: S5-3"
  [[row.legs]]
  id = "P34.39a-osm"
  earliest = "2026-10-10T03:35:00Z — plus scheduler lastAttemptTime and a finished post-fire execution"
  go = "pre-authorised: S5-3"
"""

MAP_DIR_REL = "docs/build/tools/record_policy"
INDEX_REL = "docs/build/BUILD_INDEX.md"
MANIFEST_REL = "docs/tickets/00_MANIFEST.md"


def _root(tmp_path: Path) -> Path:
    (tmp_path / MAP_DIR_REL).mkdir(parents=True)
    (tmp_path / MAP_DIR_REL / "return_pass.toml").write_text(MAP, encoding="utf-8")
    (tmp_path / "docs/build").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/tickets").mkdir(parents=True, exist_ok=True)
    (tmp_path / INDEX_REL).write_text(INDEX, encoding="utf-8")
    (tmp_path / MANIFEST_REL).write_text(MANIFEST, encoding="utf-8")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/ci.yml").write_text(
        "jobs:\n  python:\n    runs-on: ubuntu-24.04\n", encoding="utf-8"
    )
    return tmp_path


def test_manifest_rows_range():
    rows = ar.manifest_11a_rows(MANIFEST)
    assert [r["ticket"] for r in rows] == ["P34.1", "P34.2", "P34.47"]


def test_highest_layer_never_the_owed_trap():
    idx = ar.index_rows(INDEX)
    assert ar.highest_layer(idx["201"]["cell"]) == "fixture-verified"
    # row 202's cell claims live-executed in the head AND names an owed one
    assert ar.highest_layer(idx["202"]["cell"]) == "live-executed"
    owed_only = (
        "engineered + fixture-verified: the live-executed half owed to "
        "`D-P34.3-1` stays queued"
    )
    assert ar.highest_layer(owed_only) == "fixture-verified"


def test_evaluate_legs_states():
    import tomllib
    import datetime as dt

    now = dt.datetime(2026, 10, 9, 12, 0, tzinfo=dt.UTC)
    legs = ar.evaluate_legs(tomllib.loads(MAP), now)
    ids = {x["leg"]: k for k, v in legs.items() for x in v}
    # slot: earliest in future + go not held → awaiting-go wins on go first
    assert ids["P34.46-slot"] == "awaiting_go"
    assert ids["P34.46-soak"] == "indeterminate"
    assert ids["P34.40-web-roll"] == "waiting"
    assert ids["P34.39a-osm"] == "waiting"  # earliest 10-10T03:35 still ahead at 10-09
    later = dt.datetime(2026, 10, 20, 15, 0, tzinfo=dt.UTC)
    legs2 = ar.evaluate_legs(tomllib.loads(MAP), later)
    ids2 = {x["leg"]: k for k, v in legs2.items() for x in v}
    assert ids2["P34.40-web-roll"] == "due"
    assert ids2["P34.39a-osm"] == "conditional"  # earliest passed, extra conditions
    assert ids2["P34.46-slot"] == "awaiting_go"  # still — the go is verbatim


def test_generate_and_check_roundtrip(tmp_path):
    root = _root(tmp_path)
    r = subprocess.run(
        [PYTHON, str(TOOL), "generate", "--root", str(root), "--at",
         "2026-10-09T12:00:00Z"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    note = root / ar.NOTE_REL
    assert note.is_file()
    r = subprocess.run(
        [PYTHON, str(TOOL), "check", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr


def test_generate_without_index_row_marks_not_landed(tmp_path):
    root = _root(tmp_path)
    # drop row 259's index row → the note must say "not landed"
    (root / INDEX_REL).write_text(INDEX.split("## Row corrections")[0], encoding="utf-8")
    r = subprocess.run(
        [PYTHON, str(TOOL), "generate", "--root", str(root), "--at",
         "2026-10-09T12:00:00Z"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    text = (root / ar.NOTE_REL).read_text()
    assert "no BUILD_INDEX" in text


def test_check_fails_on_overclaim(tmp_path):
    root = _root(tmp_path)
    r = subprocess.run(
        [PYTHON, str(TOOL), "generate", "--root", str(root), "--at",
         "2026-10-09T12:00:00Z"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    note = root / ar.NOTE_REL
    text = note.read_text()
    # pretend row 201 claimed public while evidence only reaches fixture-verified
    text = text.replace("| 201 | P34.1 | fixture-verified |",
                        "| 201 | P34.1 | public |")
    note.write_text(text)
    r = subprocess.run(
        [PYTHON, str(TOOL), "check", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 1
    assert "above its evidence" in r.stderr


def test_exit_items_all_verdicted(tmp_path):
    import tomllib
    import datetime as dt

    root = _root(tmp_path)
    map_data = tomllib.loads(MAP)
    items = ar.evaluate_exit_items(
        root=root,
        map_data=map_data,
        now=dt.datetime(2026, 10, 9, tzinfo=dt.UTC),
        record=None,
        index=ar.index_rows(INDEX),
        mrows=ar.manifest_11a_rows(MANIFEST),
    )
    assert len(items) == len(ar.EXIT_ITEMS)
    for it in items:
        assert it["verdict"] in ar.VERDICT_WORDS
    by_id = {i["id"]: i for i in items}
    # live items are queued, never fabricated
    assert by_id["exit-1"]["verdict"] == "queued"
    assert by_id["exit-5"]["verdict"] == "queued"
    assert by_id["exit-7"]["verdict"] == "queued"
    # record-checkable items evaluated from the fixture tree
    assert by_id["exit-3"]["verdict"] == "pass"  # pinned runner + every row ci: pass
    assert by_id["exit-8"]["verdict"] == "pass"  # no due legs at 10-09


def test_suppressed_record_marks_exit7_queued(tmp_path):
    import tomllib
    import datetime as dt

    items = ar.evaluate_exit_items(
        root=_root(tmp_path),
        map_data=tomllib.loads(MAP),
        now=dt.datetime(2026, 10, 9, tzinfo=dt.UTC),
        record={"overall": "suppressed", "checks": {}},
        index=ar.index_rows(INDEX),
        mrows=ar.manifest_11a_rows(MANIFEST),
    )
    assert {i["id"] for i in items if i["verdict"] == "queued"} >= {"exit-7"}
