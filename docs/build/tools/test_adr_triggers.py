#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``adr_triggers.py`` — the revisit-trigger register matches the ADR files (SEED-15; B4 G8-3).

The hash covers the ``## Revisit trigger`` text only up to the first ``### Trigger evaluation`` (CARRY:
SEED-11d → SEED-15): an appended evaluation never changes it, an edited trigger does. Fixture trees exercise
each rule; the last test runs the check over the committed register (an invariant, not a living value)::

    uv run pytest docs/build/tools/test_adr_triggers.py
"""

from __future__ import annotations

import csv
import importlib.util
import io
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[2]
_spec = importlib.util.spec_from_file_location("adr_triggers", _HERE / "adr_triggers.py")
at = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(at)

ADR_1 = """# ADR-001: First

- **Status:** Accepted

## Decision

Do it.

## Revisit trigger

- When the load doubles.
- When the licence changes.
"""
ADR_2 = """# ADR-002: The waiver

- **Status:** Accepted

## Revisit trigger

The scope ends.

## Status updates

- **Status:** Extended by ADR-001 (2026-10-01)
"""
ADR_3 = "# ADR-003: No trigger\n\n- **Status:** Accepted\n"
MANIFEST = (
    "| # | file |\n|---|---|\n| 1 | `001_P01.1__first.md` |\n| 2 | `002_P01.2a__second.md` |\n"
)
BACKLOG = (
    "bl_id,title,type,sources,req_ids,package,blocks,landing,gate,size,status\n"
    "BL-001,a,process,ADR-001,,,,P01+,,S,open\n"
    "BL-002,b,process,ADR-002,,,,P01+,,S,open\n"
    "BL-003,c,process,ADR-003,,,,P01+,,S,closed\n"
    "BL-004,d,process,,,,,P01+,,S,accepted\n"
)
WHEN = "2026-10-01T16:00:00Z"
Q_TEXT = "alias when volume grows"


def _rows(adr1_text: str = ADR_1, adr2_text: str = ADR_2) -> list[dict[str, str]]:
    base = {"probe_id": "", "last_evaluated": WHEN, "trigger_text": "", "waiver": "", "kind": "adr"}
    return [
        {
            **base,
            "adr": "ADR-001",
            "trigger_sha256": at.trigger_sha256(adr1_text),
            "state": "fired-answered(P01.2a)",
            "evidence": "e",
            "home": "BL-001",
        },
        {
            **base,
            "adr": "ADR-002",
            "trigger_sha256": at.trigger_sha256(adr2_text),
            "state": "quiet",
            "evidence": "e",
            "home": "BL-002",
            "kind": "waiver",
            "waiver": "WV-99",
        },
        {
            **base,
            "adr": "Q-99",
            "trigger_sha256": at.sha256_text(Q_TEXT),
            "state": "quiet",
            "evidence": "e",
            "home": "BL-002",
            "kind": "accepted-risk",
            "trigger_text": Q_TEXT,
        },
    ]


def _csv(rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=at.COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def _tree(tmp_path: pathlib.Path, rows=None, adr1: str = ADR_1, adr2: str = ADR_2) -> pathlib.Path:
    root = tmp_path / "repo"
    files = {
        "docs/adr/ADR-001-first.md": adr1,
        "docs/adr/ADR-002-waiver.md": adr2,
        "docs/adr/ADR-003-none.md": ADR_3,
        "docs/tickets/00_MANIFEST.md": MANIFEST,
        "docs/build/BACKLOG.csv": BACKLOG,
        at.REGISTER: _csv(_rows() if rows is None else rows),
    }
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def _errors(root: pathlib.Path) -> list[str]:
    return at.check(root, waiver_lines=("WV-99",))[0]


def test_trigger_text_stops_at_the_first_evaluation_and_at_the_next_section() -> None:
    assert at.trigger_text(ADR_1) == "- When the load doubles.\n- When the licence changes."
    assert at.trigger_text(ADR_2) == "The scope ends."
    assert at.trigger_text(ADR_3) is None


def test_an_appended_evaluation_does_not_change_the_hash_but_an_edit_does() -> None:
    evaluated = (
        ADR_1
        + "\n### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): FIRED\n\nAnswer: P01.2a.\n"
    )
    assert at.trigger_sha256(evaluated) == at.trigger_sha256(ADR_1)
    edited = ADR_1.replace("load doubles", "load triples")
    assert at.trigger_sha256(edited) != at.trigger_sha256(ADR_1)


def test_valid_register_passes(tmp_path) -> None:
    assert _errors(_tree(tmp_path)) == []


def test_edited_trigger_is_visible_as_a_stale_hash(tmp_path) -> None:
    root = _tree(tmp_path, adr1=ADR_1.replace("load doubles", "load triples"), rows=_rows())
    assert any("trigger_sha256 is stale" in e for e in _errors(root))


def test_appended_evaluation_keeps_the_register_current(tmp_path) -> None:
    evaluated = ADR_1 + "\n### Trigger evaluation — P21.2 (2026): NOT fired\n\nquiet.\n"
    assert _errors(_tree(tmp_path, adr1=evaluated, rows=_rows())) == []


def test_every_adr_trigger_has_exactly_one_row(tmp_path) -> None:
    missing = _tree(tmp_path / "a", rows=_rows()[1:])
    assert any(
        "ADR-001: has a '## Revisit trigger' but no register row" in e for e in _errors(missing)
    )
    twice = _tree(tmp_path / "b", rows=_rows() + [_rows()[0]])
    assert any("ADR-001: 2 register rows" in e for e in _errors(twice))
    no_trigger = _rows() + [{**_rows()[0], "adr": "ADR-003"}]
    assert any(
        "ADR-003 has no '## Revisit trigger'" in e
        for e in _errors(_tree(tmp_path / "c", rows=no_trigger))
    )


def test_state_grammar_and_refs(tmp_path) -> None:
    bad = _rows()
    bad[0]["state"] = "fired"
    assert any("off the G8-3 grammar" in e for e in _errors(_tree(tmp_path / "a", rows=bad)))
    dangling = _rows()
    dangling[0]["state"] = "superseded(ADR-404)"
    assert any(
        "neither an ADR file nor a manifest chain row" in e
        for e in _errors(_tree(tmp_path / "b", rows=dangling))
    )
    ok = _rows()
    ok[0]["state"] = "dormant(counsel clause; ADR-182)"
    assert _errors(_tree(tmp_path / "c", rows=ok)) == []


def test_home_evaluated_time_and_evidence(tmp_path) -> None:
    rows = _rows()
    rows[0]["home"] = "BL-777"
    rows[1]["last_evaluated"] = "2026-10-01"
    rows[2]["evidence"] = ""
    errs = _errors(_tree(tmp_path, rows=rows))
    assert any("home 'BL-777' is not a BACKLOG row" in e for e in errs)
    assert any("is not a date -u timestamp" in e for e in errs)
    assert any("evidence is empty" in e for e in errs)


def test_waiver_lines_are_each_carried_once(tmp_path) -> None:
    rows = _rows()
    rows[1]["waiver"] = ""
    errs = _errors(_tree(tmp_path, rows=rows))
    assert any("kind 'waiver' without a waiver line id" in e for e in errs)
    assert any("waiver line WV-99: 0 register rows" in e for e in errs)


def test_accepted_risk_rows_hash_their_recorded_text(tmp_path) -> None:
    rows = _rows()
    rows[2]["trigger_text"] = "alias when volume shrinks"
    assert any("does not match its trigger_text" in e for e in _errors(_tree(tmp_path, rows=rows)))


def test_open_home_rule_follows_the_trigger_state(tmp_path) -> None:
    """F3 NEW-3 / G8-3: open homes are always valid; an accepted monitor row never for
    fired-unanswered; a closed row only for quiet/superseded (Q-29 carries no ADR owner)."""
    closed_quiet = _rows()
    closed_quiet[2].update({"home": "BL-003", "state": "quiet"})
    assert _errors(_tree(tmp_path / "a", rows=closed_quiet)) == []
    closed_fired = _rows()
    closed_fired[2].update({"home": "BL-003", "state": "fired-answered(P01.2a)"})
    assert any(
        "is closed while the trigger is" in e
        for e in _errors(_tree(tmp_path / "b", rows=closed_fired))
    )
    closed_superseded = _rows()
    closed_superseded[2].update({"home": "BL-003", "state": "superseded(ADR-001)"})
    assert _errors(_tree(tmp_path / "c", rows=closed_superseded)) == []
    monitor_unanswered = _rows()
    monitor_unanswered[2].update({"home": "BL-004", "state": "fired-unanswered"})
    errs = _errors(_tree(tmp_path / "d", rows=monitor_unanswered))
    assert any("accepted monitor row" in e for e in errs)


def test_register_home_must_equal_the_backlog_owner(tmp_path) -> None:
    """The register's `home` is the BACKLOG row whose `sources` name the ADR (check_backlog's
    edge, judged from the register side)."""
    rows = _rows()
    rows[0]["home"] = "BL-002"  # ADR-001 is owned by BL-001
    assert any(
        "!= BACKLOG owner BL-001" in e for e in _errors(_tree(tmp_path, rows=rows))
    )


def test_probe_id_is_honoured_when_present(tmp_path) -> None:
    rows = _rows()
    rows[0]["probe_id"] = "PROBE-egress-01"
    errors, stats = at.check(_tree(tmp_path / "a", rows=rows), waiver_lines=("WV-99",))
    assert errors == []
    assert stats["probes"] == 1
    bad = _rows()
    bad[0]["probe_id"] = "not a probe id"
    assert any(
        "probe_id" in e and "not a probe id token" in e
        for e in _errors(_tree(tmp_path / "b", rows=bad))
    )


def test_round_tail_fails_stale_evaluation_and_unanswered_without_disposition(tmp_path) -> None:
    rows = _rows()
    rows[0]["last_evaluated"] = "2026-09-30T12:00:00Z"  # before a 2026-10-01 round start
    errors, _ = at.check(
        _tree(tmp_path / "a", rows=rows), waiver_lines=("WV-99",), round_tail="2026-10-01"
    )
    assert any("predates the round start" in e for e in errors)
    unanswered = _rows()
    unanswered[0].update({"state": "fired-unanswered", "evidence": "FIRED; no answer recorded"})
    errors, _ = at.check(
        _tree(tmp_path / "b", rows=unanswered), waiver_lines=("WV-99",), round_tail="2026-10-01"
    )
    assert any("S1" in e and "disposition" in e for e in errors)
    routed = _rows()
    routed[0].update(
        {"state": "fired-unanswered", "evidence": "S1 disposition: routed to P01.2a"}
    )
    errors, _ = at.check(
        _tree(tmp_path / "c", rows=routed), waiver_lines=("WV-99",), round_tail="2026-10-01"
    )
    assert errors == []
    # outside round-tail mode the same unanswered row is not held to the disposition rule
    errors, _ = at.check(
        _tree(tmp_path / "d", rows=unanswered), waiver_lines=("WV-99",)
    )
    assert errors == []


def test_committed_register_matches_the_adr_files() -> None:
    """One row per ADR revisit trigger (plus Q-29), every hash current, every waiver line A-6, WV-01…WV-12."""
    errors, stats = at.check(REPO_ROOT)
    assert errors == [], errors[:20]
    assert stats["rows"] == stats["adr_triggers"] + 1  # the Q-29 accepted-risk row
