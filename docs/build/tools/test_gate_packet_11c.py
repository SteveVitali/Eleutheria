# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.73 — the GATE-G6 packet drafter invariants.

Never a living record: the sha256 over the agent-drafted block re-computes,
every packet line carries its non-action Default, the six S5-2 parts are
present, the 11D OM-20 table is the verbatim PLAN-11D draft (15 rows), and
a tampered or signed readout fails the check.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_packet_11c as gp  # noqa: E402


def _root(tmp_path):
    """A tmp root with the committed map the packet reads."""
    d = tmp_path / "docs/build/tools/record_policy"
    d.mkdir(parents=True, exist_ok=True)
    (d / "return_pass.toml").write_text(
        '[[row]]\nkey = "P36.68"\n'
        '[[row.legs]]\nid = "P36.68-mirror"\nearliest = "x"\n'
        'go = "pre-authorised: the 11C list (expires GATE-G6)"\n',
        encoding="utf-8",
    )
    return tmp_path



def test_draft_readout_shape(tmp_path):
    packet = gp.packet_body(_root(tmp_path))
    text = gp.render_readout(packet)
    assert text.startswith("# GATE-G6 — pending readout")
    assert "Status: PENDING" in text
    assert "docs/tickets/420_GATE-G6__11c-check-in.md" in text
    v = gp.check(text)
    assert v == []


def test_sha256_recomputes_over_the_block(tmp_path):
    packet = gp.packet_body(_root(tmp_path))
    text = gp.render_readout(packet)
    import re

    m = re.search(r"sha256=([0-9a-f]{64})", text)
    assert m and m.group(1) == hashlib.sha256(packet.encode("utf-8")).hexdigest()


def test_every_line_carries_a_default(tmp_path):
    packet = gp.packet_body(_root(tmp_path))
    missing = [
        ln
        for ln in packet.splitlines()
        if ln.startswith("- ") and "Default:" not in ln
    ]
    assert missing == []


def test_six_parts_and_required_content(tmp_path):
    packet = gp.packet_body(_root(tmp_path))
    for part in (
        "1. Budget",
        "2. Publication",
        "3. Rights",
        "4. The 11D OM-20 list",
        "5. Class R",
        "6. Status",
    ):
        assert part in packet
    for required in (
        "ING-GO-D",
        "RB-08",
        "N1–N21",
        "P37.59",
        "P37.46b",
        "e4e24975b854",
        "GATE-ACCEPT-R11",
        "76 / 65.0",
        "prepared_not_executed",
        "agent-drafted",
    ):
        assert required.lower() in packet.lower() or required in packet


def test_om20_table_is_the_fifteen_written_headers():
    rows = [
        ln
        for ln in gp.OM20_11D_TABLE.splitlines()
        if ln.startswith("| 4")
    ]
    assert len(rows) == 15
    assert "| 421 | P37.3 |" in gp.OM20_11D_TABLE
    assert "| 487 | P37.59 |" in gp.OM20_11D_TABLE


def test_check_fails_a_signed_or_tampered_readout(tmp_path):
    packet = gp.packet_body(_root(tmp_path))
    text = gp.render_readout(packet)
    v = gp.check(text.replace("Status: PENDING", "Status: SIGNED"))
    assert any("PENDING" in x for x in v)
    v = gp.check(text.replace("ING-GO-D", "ING-GO-X"))
    assert any(viol for viol in v)


def test_expiring_legs_listed_from_the_map(tmp_path):
    (tmp_path / "docs/build/tools/record_policy").mkdir(parents=True)
    (tmp_path / "docs/build/tools/record_policy/return_pass.toml").write_text(
        '[[row]]\nkey = "P36.68"\n'
        '[[row.legs]]\nid = "P36.68-mirror"\nearliest = "x"\n'
        'go = "pre-authorised: the 11C list (expires GATE-G6)"\n'
        '[[row]]\nkey = "P36.70"\n'
        '[[row.legs]]\nid = "P36.70-rehearsal"\nearliest = "x"\n'
        'go = "operator: records"\n',
        encoding="utf-8",
    )
    legs, expiring = gp._map_state(tmp_path)
    assert "P36.68-mirror (P36.68)" in expiring
    assert "P36.70-rehearsal (P36.70)" in legs
    assert "P36.70-rehearsal (P36.70)" not in expiring
