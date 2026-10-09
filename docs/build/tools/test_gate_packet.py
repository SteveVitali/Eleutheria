#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``gate_packet.py`` (P34.47; row 260's S5-2 packet, ADR-147).

Invariants on fixtures, never a living record (OM-15): the draft is
PENDING and labelled agent-drafted; the sha256 over the packet body is
recorded and re-verified; every packet line carries a non-action Default;
the OM-20/rights/money lines are never batch; the template guard sentence
is present; a tampered block fails check.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gate_packet as gp  # noqa: E402

TOOL = HERE / "gate_packet.py"
PYTHON = sys.executable
MAP_DIR_REL = "docs/build/tools/record_policy"

MAP = """\
[[row]]
key = "P34.40"
  [[row.legs]]
  id = "P34.40-web-roll"
  earliest = "2026-10-13T12:00Z"
  go = "pre-authorised: S5-3 (expires GATE-G4)"
"""


def _root(tmp_path: Path) -> Path:
    (tmp_path / MAP_DIR_REL).mkdir(parents=True)
    (tmp_path / MAP_DIR_REL / "return_pass.toml").write_text(MAP, encoding="utf-8")
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


def test_draft_then_check_roundtrip(tmp_path):
    root = _root(tmp_path)
    assert subprocess.run(
        [PYTHON, str(TOOL), "draft", "--root", str(root)],
        capture_output=True, check=False,
    ).returncode == 0
    r = subprocess.run(
        [PYTHON, str(TOOL), "check", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr


def test_sha256_is_over_the_block_body(tmp_path):
    root = _root(tmp_path)
    packet = gp.packet_body(root)
    text = gp.render_readout(packet)
    m = re.search(r"sha256=([0-9a-f]{64})", text)
    import hashlib

    assert m.group(1) == hashlib.sha256(packet.encode()).hexdigest()


def test_check_fails_on_tampered_block(tmp_path):
    root = _root(tmp_path)
    text = gp.render_readout(gp.packet_body(root))
    text = text.replace("$300", "$3,000")
    assert gp.check(text)


def test_packet_parts_and_defaults(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    for part in ("1. Budget", "2. Publication", "3. Rights", "4. The 11B OM-20 list", "5. Class R", "6. Status"):
        assert part in body
    # every answerable line carries its Default
    for ln in body.splitlines():
        if ln.startswith("- "):
            assert "Default:" in ln, ln[:70]
    # the OM-20 line is never batch-answerable
    om20_lines = [ln for ln in body.splitlines() if "Candidates (the 19" in ln]
    assert om20_lines and "**batch**" not in om20_lines[0]
    # the carried questions ride
    assert "OP-24" in body
    # the S5-3 row list is derived from the fixture map
    assert "P34.40" in body


def test_class_r_text_verbatim(tmp_path):
    body = gp.packet_body(_root(tmp_path))
    assert "expires at the next sub-round gate or after 30 days" in body
    assert "e4e24975b854" in body
