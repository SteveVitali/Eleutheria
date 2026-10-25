#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``acceptance_report_11b.py`` (P35.64; plan S2 §4.2; SIG-MEM-011).

Invariants on small fixtures, never a living record (OM-15): every 11B
chain row (261–343) appears exactly once; a row never reports above the
layer its evidence cell claims; exit items verdict honestly — queued
while the sweep leg is queued, never a fabricated live pass; OPCHECK is
recorded not-required, never claimed performed; the expired-at-GATE-G4
pre-authorisations classify awaiting-go (a lapsed go is not held), and
every queued leg whose window opened is listed.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import acceptance_report_11b as ar11  # noqa: E402

TOOL = HERE / "acceptance_report_11b.py"
PYTHON = sys.executable

MANIFEST = """\
## The chain

| # | file | ph | kind | lane | scope | deps |
|---|---|---|---|---|---|---|
| 260 | `260_GATE-G4__x.md` | 34 | gate | C | x | none |
| 261 | `261_P35.1__a.md` | 35 | ticket | C | x | none |
| 341 | `341_P35.63__b.md` | 35 | ticket | C | x | 340 |
| 342 | `342_P35.64__c.md` | 35 | capstone | C | x | 341 |
| 343 | `343_GATE-G5__d.md` | 35 | gate | C | x | 342 |
| 344 | `344_P37.1__e.md` | 37 | ticket | C | x | none |

## Later
"""

INDEX = """\
## Round 11

| # | ticket | kind | branch | pr | base | date | adr | oblig | status | paths | harness |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 261 | P35.1 | ticket | b | #1 | base | 2026-01-01 | — | none | engineered + fixture-verified (`x`): detail · ci: pass #1@abc | paths | h |
| 341 | P35.63 | ticket | b | #2 | base | 2026-01-01 | — | none | engineered (`x`): the live-executed half owed to `D-R10-PUBLISH-1` is queued · ci: pass #2@def | paths | h |

## Later
"""

MAP = """\
[[row]]
key = "P35.63"
  [[row.legs]]
  id = "P35.63-dispatch-stage-verify-readout"
  earliest = "the next weekday slot"
  go = "pre-authorised: GATE-G4 §4 (expires next GATE)"
  [[row.legs]]
  id = "P35.63-promote-under-hg11"
  earliest = "only after L1 + the signed HG-11 readout"
  go = "verbatim-go: the signed readout"
[[row]]
key = "P34.40"
  [[row.legs]]
  id = "P34.40-web-roll"
  earliest = "2026-10-13T12:00Z"
  go = "pre-authorised: S5-3 (11A list; expires GATE-G4)"
"""

DEFERRALS = """\
| D-R10-LIVE-1 | V | title | x | y | z | OPEN — blocks claiming production verified |
| D-R10-PUBLISH-1 | P | title | x | y | z | DONE 2026-10-01 — recorded |
"""

SUPPRESSED = {
    "version": "sig.probe-run/1",
    "overall": "suppressed",
    "suppressed": "p35_63_promotion: still queued",
    "rerun_prompt": "implement-spec spec=docs/tickets/342_x live_verification=true",
    "generated_at": "2026-10-25T00:00:00Z",  # future-ok: synthetic: test instant
}


def _render(tmp_path: Path, record=SUPPRESSED):
    (tmp_path / "docs/build/reports/p32.23a-release-candidate").mkdir(
        parents=True
    )
    (tmp_path / "docs/build/reports/p32.23a-release-candidate/CORRECTION.md").write_text(
        "x", encoding="utf-8"
    )
    (tmp_path / "docs/build/readouts").mkdir(parents=True)
    (tmp_path / "docs/build/readouts/GATE-G4.md").write_text(
        "Status: SIGNED", encoding="utf-8"
    )
    return ar11.render(
        root=tmp_path,
        index_text=INDEX,
        manifest_text=MANIFEST,
        deferrals_text=DEFERRALS,
        map_data={
            "row": [
                {
                    "key": "P35.63",
                    "legs": [
                        {"id": "P35.63-dispatch-stage-verify-readout",
                         "earliest": "the next weekday slot",
                         "go": "pre-authorised: GATE-G4 §4 (expires next GATE)"},
                        {"id": "P35.63-promote-under-hg11",
                         "earliest": "only after L1 + the signed HG-11 readout",
                         "go": "verbatim-go: the signed readout"},
                    ],
                },
                {
                    "key": "P34.40",
                    "legs": [
                        {"id": "P34.40-web-roll",
                         "earliest": "2026-10-13T12:00Z",
                         "go": "pre-authorised: S5-3 (11A list; expires GATE-G4)"}
                    ],
                },
            ]
        },
        record=record,
        evaluated_at="2026-10-25T00:00:00Z",  # future-ok: synthetic: test instant
        reads=None,
    )


def test_rows_261_to_343_listed(tmp_path):
    text = _render(tmp_path)
    viols = ar11.check(
        note_text=text, manifest_text=MANIFEST, index_text=INDEX
    )
    assert viols == []
    assert "| 261 | P35.1 |" in text
    assert "| 343 | GATE-G5 |" in text
    assert "| 344 |" not in text


def test_no_row_reports_above_its_evidence(tmp_path):
    text = _render(tmp_path)
    assert "| 341 | P35.63 | engineered |" in text
    # the evidence cell may quote the owed live half — the reported LAYER
    # column is what the honesty rule judges (never above the cell's head)
    row = [ln for ln in text.splitlines() if ln.startswith("| 341 |")][0]
    assert row.split("|")[3].strip() == "engineered"


def test_exit_items_queued_never_fabricated(tmp_path):
    text = _render(tmp_path)
    assert "| exit-1 | queued |" in text
    assert "| exit-3 | queued |" in text
    assert "| exit-18 | queued |" in text
    assert "P35.63-promote-under-hg11" in text


def test_opcheck_recorded_not_required_never_claimed(tmp_path):
    text = _render(tmp_path)
    assert "| exit-20 | pass |" in text
    assert "Q-L3-3 = c" in text
    assert "never claimed" in text


def test_g3_supersession_record_checked(tmp_path):
    text = _render(tmp_path)
    assert "| exit-5 | pass |" in text
    assert "CORRECTION.md" in text


def test_expired_go_classifies_awaiting_not_due(tmp_path):
    text = _render(tmp_path)
    assert "P34.40-web-roll" in text
    assert "pre-authorisation expired at GATE-G4" in text
    # the expired leg must not sit in the due bucket
    due_part = text.split("**due** (unrun, window open)")[1].split("### ")[0]
    assert "P34.40-web-roll" not in due_part


def test_window_opened_listing(tmp_path):
    text = _render(tmp_path)
    assert "window has opened" in text
    opened = text.split("recorded window has opened")[1].split("### ")[0]
    assert "P34.40-web-roll" in opened


def test_open_issues_lead_tokens(tmp_path):
    text = _render(tmp_path)
    assert "| `D-R10-LIVE-1` | OPEN |" in text
    assert "| `D-R10-PUBLISH-1` | DONE |" in text


def test_suppressed_record_line(tmp_path):
    text = _render(tmp_path)
    assert "**suppressed**" in text
    assert "**queued**" in text


def test_check_catches_over_claim_and_missing_row(tmp_path):
    text = _render(tmp_path)
    over = text.replace(
        "| 261 | P35.1 | fixture-verified |", "| 261 | P35.1 | live-executed |"
    )
    viols = ar11.check(note_text=over, manifest_text=MANIFEST, index_text=INDEX)
    assert any("above its evidence" in v for v in viols)
    dropped = "\n".join(
        ln for ln in text.splitlines() if not ln.startswith("| 261 |")
    )
    viols = ar11.check(note_text=dropped, manifest_text=MANIFEST, index_text=INDEX)
    assert any("listed 0 times" in v for v in viols)


def test_cli_generate_and_check(tmp_path):
    root = tmp_path
    for rel, content in (
        ("docs/build/BUILD_INDEX.md", INDEX),
        ("docs/tickets/00_MANIFEST.md", MANIFEST),
        ("docs/tickets/DEFERRALS.md", DEFERRALS),
        ("docs/build/tools/record_policy/return_pass.toml", MAP),
        ("docs/build/reports/p32.23a-release-candidate/CORRECTION.md", "x"),
        ("docs/build/readouts/GATE-G4.md", "Status: SIGNED"),
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    r = subprocess.run(
        [PYTHON, str(TOOL), "generate", "--root", str(root),
         "--at", "2026-10-25T00:00:00Z"],  # future-ok: synthetic: test instant
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stderr
    note = root / ar11.NOTE_REL
    assert note.is_file()
    r2 = subprocess.run(
        [PYTHON, str(TOOL), "check", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert r2.returncode == 0, r2.stderr


def test_deferral_status_reads_lead_token():
    assert ar11.deferral_status(DEFERRALS, "D-R10-LIVE-1") == "OPEN"
    assert ar11.deferral_status(DEFERRALS, "D-R10-PUBLISH-1") == "DONE"
    assert ar11.deferral_status(DEFERRALS, "D-NOPE-1") == "absent"
