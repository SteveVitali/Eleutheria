#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``gate_packet_11b.py`` (P35.64; row 343's S2 §3.6 packet).

Invariants on fixtures, never a living record (OM-15): the draft is
PENDING and labelled agent-drafted; the sha256 over the packet body is
recorded and re-verified; every ``- `` packet line carries a non-action
Default; the OM-20/rights/money/own-words lines are never batch; the six
parts, the PLAN-11C OM-20 table, the Class R text, the title/note drift
record and the guard sentence are present; a tampered block fails check.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gate_packet_11b as gp  # noqa: E402

TOOL = HERE / "gate_packet_11b.py"
PYTHON = sys.executable
MAP_DIR_REL = "docs/build/tools/record_policy"
SPEND_REL = "docs/build/reports/spend/spend_ledger.csv"
USAGE_REL = "docs/build/reports/spend/agent_usage.csv"

MAP = """\
[[row]]
key = "P35.5"
  [[row.legs]]
  id = "P35.5-r2-mirror"
  earliest = "bounded by OP-09"
  go = "pre-authorised: GATE-G4 OM-20 11B list (P35.5 named, expires GATE-G5)"
[[row]]
key = "P35.63"
  [[row.legs]]
  id = "P35.63-promote-under-hg11"
  earliest = "only after the signed readout"
  go = "verbatim-go: the signed HG-11 readout"
"""

SPEND = "month,category,provider,item,usd,status,evidence,notes\n" \
    "2026-10,infrastructure,gcp,compute,90.00,estimate,e,x\n"
USAGE = "wave,period,acu_sessions,acu_used,tokens_dispatched,source_label,evidence,note\n" \
    "r11,2026-10-02,8,2800,46000,operator-reported,e,x\n"


def _root(tmp_path: Path) -> Path:
    (tmp_path / MAP_DIR_REL).mkdir(parents=True)
    (tmp_path / MAP_DIR_REL / "return_pass.toml").write_text(MAP, encoding="utf-8")
    (tmp_path / SPEND_REL).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / SPEND_REL).write_text(SPEND, encoding="utf-8")
    (tmp_path / USAGE_REL).write_text(USAGE, encoding="utf-8")
    return tmp_path


def test_draft_writes_pending_labelled_readout(tmp_path):
    root = _root(tmp_path)
    r = subprocess.run(
        [PYTHON, str(TOOL), "draft", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    text = (root / gp.READOUT_REL).read_text(encoding="utf-8")
    assert "Status: PENDING" in text
    assert "agent-drafted:begin sha256=" in text
    assert "an agent must not" in text
    assert "Default:" in text


def test_six_parts_and_om20_table(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    for part in ("1. Budget", "2. Publication", "3. Rights",
                 "4. The 11C OM-20 list", "5. Class R", "6. Status"):
        assert part in body
    for row_id in ("P35.2", "P36.76", "P36.68", "P36.44", "P36.79"):
        assert row_id in body
    assert "expires: GATE-G6" in body
    assert "e4e24975b854" in body


def test_every_bullet_carries_a_default(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    for ln in body.splitlines():
        if ln.startswith("- "):
            assert "Default:" in ln, ln[:60]


def test_om20_rights_money_never_batch(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    asks = (
        "- **ING-GO-C**",
        "- Flips are executed by the operator",
        "- A-7 lines due in 11C",
        "- PLAN-11C's draft",
        "- 11B legs whose GATE-G4 pre-authorisation",
        "- The operator's adopted text",
    )
    for ln in body.splitlines():
        if any(ln.startswith(a) for a in asks):
            assert "**batch**" not in ln, ln[:80]


def test_expiring_11b_legs_listed(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    assert "P35.5-r2-mirror" in body
    assert "expires at this gate" in body or "expires GATE-G5" in body


def test_title_note_drift_recorded(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    assert "ING-GO-B" in body and "ING-GO-C" in body
    assert "Title/note recorded, not resolved" in body


def test_status_part_carries_incidents(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    assert "NIGHTLY-RED-1" in body
    assert "D-K2-1" in body
    assert "76 / 66.5" in body
    assert "D-R11-LATER-04" in body


def test_publication_records_nothing_promoted(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    assert "queued" in body
    assert "nothing has been promoted, hosted, deployed or published" in body


def test_check_catches_sha_tampering(tmp_path):
    root = _root(tmp_path)
    text = gp.render_readout(gp.packet_body(root))
    assert gp.check(text) == []
    tampered = text.replace("e4e24975b854", "e4e24975b000", 1)
    assert any("sha256 mismatch" in v for v in gp.check(tampered))


def test_check_catches_missing_default(tmp_path):
    root = _root(tmp_path)
    body = gp.packet_body(root) + "\n- an unanswerable line\n"
    text = gp.render_readout(body)
    assert any("lacks Default" in v for v in gp.check(text))


def test_check_catches_missing_part(tmp_path):
    root = _root(tmp_path)
    body = gp.packet_body(root).replace("**5. Class R", "**5. Renamed")
    text = gp.render_readout(body)
    assert any("packet part missing: 5. Class R" in v for v in gp.check(text))


def test_check_green_on_real_draft(tmp_path):
    root = _root(tmp_path)
    text = gp.render_readout(gp.packet_body(root))
    assert gp.check(text) == []
    r = subprocess.run(
        [PYTHON, str(TOOL), "check", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    # file absent → 3 (not a readout bug — checked via gp.check above)
    assert r.returncode == 3
