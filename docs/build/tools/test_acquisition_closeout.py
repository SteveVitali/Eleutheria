#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``acquisition_closeout.py`` — the P37.66 (R11-ACQ-28) closeout.

Every test asserts an *invariant* of the committed closeout (I8 §6.3 group
shapes, full 130-row DEFERRALS coverage, owner:/trigger:, queue outcomes,
obligation-event anchors, the honest zero realized delta) — never a living
record's current value (OM-15/BM-TEST-01). The last test runs the real
``--check`` CLI on the committed tree; a drifted input or a rewritten row
fails loud.

Run::

    uv run pytest docs/build/tools/test_acquisition_closeout.py -q
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import acquisition_closeout as tool  # noqa: E402

TOOL = HERE / "acquisition_closeout.py"
PYTHON = os.environ.get("SIG_TOOLS_PYTHON") or sys.executable
PD = REPO / "docs/build/planning/2026-09-30-next-phase"
PLAN_CSV = PD / "data/acquisition_plan.csv"
DEFERRALS = REPO / "docs/tickets/DEFERRALS.md"
EVENTS = REPO / "docs/build/reports/obligations/events.jsonl"
STATUTE = REPO / "tasks/src/tasks/data/statute_leads.toml"
QUEUE_TOML = REPO / "tasks/src/tasks/data/acquisition_queue.toml"
CLOSEOUT = REPO / "docs/build/reports/p37.66-acquisition-closeout/closeout.json"

SECTION = "### P37.66 — coverage outcome & acquisition closeout (row 495)"
ROW_RE = re.compile(r"^\| (D-P37\.66-\d+) \|", re.M)
I8_63 = [23, 21, 16, 11, 10, 10, 7, 5, 4, 6, 3, 14]  # §6.3's 12 groups


def later_phase_ids() -> list[str]:
    with PLAN_CSV.open(newline="") as fh:
        return [
            r["plan_id"]
            for r in csv.DictReader(fh)
            if r["action"] == "defer" and "later-phase(" in r["ticket"]
        ]


def p3766_rows() -> dict[str, str]:
    return {m.group(1): ln for ln in DEFERRALS.read_text().splitlines() if (m := ROW_RE.match(ln))}


def test_section_and_rows_exist() -> None:
    txt = DEFERRALS.read_text()
    assert SECTION in txt
    rows = p3766_rows()
    # expected count is tool-derived (12 I8 §6.3 groups + 3 duty rows), not a
    # pinned literal — the committed section must carry exactly the tool's rows.
    expected = len(tool.GROUPS) + len(tool.DUTY_DEFERRALS)
    assert len(rows) == expected, (
        f"expected {expected} D-P37.66-* rows, found {sorted(rows)}"
    )
    assert sorted(rows, key=lambda r: int(r.rsplit("-", 1)[1])) == [
        f"D-P37.66-{i}" for i in range(1, expected + 1)
    ]


def test_every_later_phase_row_covered_exactly_once() -> None:
    rows = p3766_rows()
    covered: dict[str, list[str]] = {}
    for pid in later_phase_ids():
        assert len(pid) > 0
        homes = [rid for rid, ln in rows.items() if pid in ln]
        covered[pid] = homes
    missing = [p for p, h in covered.items() if not h]
    assert not missing, f"later-phase plan ids carried by no D-P37.66 row: {missing}"
    dup = [p for p, h in covered.items() if len(h) > 1]
    assert not dup, f"plan ids covered more than once: {dup}"
    assert len(later_phase_ids()) == 130


def test_group_counts_match_i8_63() -> None:
    rows = p3766_rows()
    for i, expected in enumerate(I8_63, start=1):
        rid = f"D-P37.66-{i}"
        assert rid in rows
        found = re.findall(r"AP-[A-Z0-9-]+", rows[rid])
        assert len(found) == expected, (
            f"{rid} carries {len(found)} plan ids, expected {expected} (I8 §6.3)"
        )


def test_owner_trigger_rule5() -> None:
    for rid, ln in p3766_rows().items():
        assert "owner:" in ln, f"{rid} lacks owner:"
        assert "trigger:" in ln, f"{rid} lacks trigger:"
        assert "(cites BL-087)" in ln, f"{rid} lacks its open home"


def test_duty_leads_covered() -> None:
    duties = tomllib.loads(STATUTE.read_text()).get("duties", [])
    assert len(duties) == 6
    rows = p3766_rows()
    homes = {
        "future_statutory_disclosure_va": "D-P37.66-13",
        "future_statutory_disclosure_al": "D-P37.66-13",
        "future_statutory_disclosure_ar": "D-P37.66-13",
        "future_statutory_disclosure_ut": "D-P37.66-13",
        "future_statutory_disclosure_nm": "D-P37.66-14",
        "future_statutory_disclosure_mn": "D-P37.66-15",
    }
    for d in duties:
        rid = homes[d["duty_id"]]
        assert d["duty_id"] in rows[rid], f"{d['duty_id']} not carried by {rid}"
    postures = {d["duty_id"]: d["posture"] for d in duties}
    assert postures["future_statutory_disclosure_nm"] == "not_yet_due"
    assert postures["future_statutory_disclosure_mn"] == "contingent"


def test_every_row_has_e0_anchor() -> None:
    events = {
        json.loads(l)["event_id"]: json.loads(l)
        for l in EVENTS.read_text().splitlines()
        if l.strip()
    }
    lines = DEFERRALS.read_text().splitlines()
    for rid, ln in p3766_rows().items():
        eid = f"{rid}:e0"
        assert eid in events, f"{rid} has no obligation-event/1 anchor"
        ev = events[eid]
        # record-to-record: the e0 anchor's recorded status must match the
        # committed row's status cell (no status-word literal — OM-15).
        status_cell = ln.rstrip().removesuffix("|").rstrip().rsplit("|", 1)[-1].strip()
        assert status_cell.startswith(ev["to_status"]), (
            f"{rid}: e0 to_status {ev['to_status']!r} != row status cell {status_cell!r}"
        )
        anchor = ev["anchor"]
        assert anchor["row_sha256"] == hashlib.sha256(ln.encode()).hexdigest(), (
            f"{rid}: anchor sha drifts from the committed row bytes"
        )
        assert lines[anchor["row_line"] - 1] == ln, (
            f"{rid}: anchor row_line no longer names the row"
        )


def test_queue_outcomes_cover_all_candidates() -> None:
    queue = tomllib.loads(QUEUE_TOML.read_text()).get("candidates", {})
    doc = json.loads(CLOSEOUT.read_text())
    outcomes = {r["candidate_id"]: r for r in doc["queue_outcomes"]["rows"]}
    assert set(outcomes) == set(queue), f"queue outcomes miss {sorted(set(queue) - set(outcomes))}"
    for cid, row in outcomes.items():
        assert row["outcome"].strip(), f"{cid} has an empty disposition"


def test_closeout_json_invariants() -> None:
    doc = json.loads(CLOSEOUT.read_text())
    assert doc["schema"] == "sig.acquisition-closeout/1"
    assert doc["live_verification"] is False
    assert doc["plan_counts"]["tier2_later_phase"] == 130
    assert doc["plan_counts"]["total"] == 694
    assert doc["coverage"]["realized_delta"] == {"added": 0, "removed": 0, "changed": 0}
    # The honest layer declaration must be present and non-empty.
    assert doc["evidence_layers"]["claims"]
    reg = doc["registry_engineering"]
    assert reg["routed_proposed_ids"] == (
        reg["registered"] + reg["registered_renamed"] + reg["absent"]
    )


def test_check_green_on_committed_tree() -> None:
    proc = subprocess.run(
        [PYTHON, str(TOOL), "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"--check failed:\n{proc.stdout}\n{proc.stderr}"
