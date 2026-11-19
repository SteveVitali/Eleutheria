# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Source-bound corrections retain originals and fail closed on bad evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memory_guard as mg
import record_corrections as rc
import test_ledger_contract as tlc

NOW = "2026-11-19T08:00:00Z"
SOURCE_TIME = "2026-11-19T06:33:52Z"
READOUT = "docs/build/readouts/GATE-T.md"
POINTER = "GATE DECISIONS row: 2026-11-19T06:55Z | GATE-T"
PHASE = "- 2026-11-19 — **P00.1** ticket — the test landing"
TOOL = Path(__file__).with_name("memory_guard.py")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def commit(root: Path, date: str = SOURCE_TIME) -> str:
    git(root, "add", "-A")
    env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(
        ["git", "-C", str(root), "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"],
        env=env,
        check=True,
    )
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def records(tmp_path: Path) -> tuple[Path, str, list[dict]]:
    root = tlc._tree(tmp_path)
    git(root, "init", "-q")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    base = commit(root, "2026-11-19T06:00:00Z")
    lp = root / rc.LEDGER
    ledger = lp.read_text().replace("- 2026-10-01 — P00.1 ticket — the test landing", PHASE)
    ledger = ledger.replace("## PHASE LOG\n", "## PHASE LOG — Round 11\n")
    row = '| 2026-11-19T06:55Z | GATE-T | acceptance | packet | "go" | unchanged | decision |\n'
    lp.write_text(ledger.replace("\n## RETURN PASS", row + "\n## RETURN PASS"))
    p = root / READOUT
    p.parent.mkdir(parents=True)
    p.write_text("# GATE-T\nStatus: PENDING\n" + POINTER + "\n")
    source = commit(root)
    entries = []
    for path, text, kind, interpretation in (
        (READOUT, POINTER, "readout-pointer-date", {"recorded_at_or_before": SOURCE_TIME}),
        (rc.LEDGER, PHASE, "phase-log-heading-markup", {"heading": "P00.1 ticket"}),
    ):
        entries.append(
            dict(
                schema=rc.SCHEMA,
                kind=kind,
                recorded_at=NOW,
                path=path,
                source_commit=source,
                source_line=(root / path).read_text().splitlines().index(text) + 1,
                line_sha256=hashlib.sha256(text.encode()).hexdigest(),
                interpretation=interpretation,
            )
        )
    return root, base, entries


def write_register(root: Path, entries: list[dict]) -> None:
    p = root / rc.REGISTER
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in entries))


def load(root: Path, revision: str = "HEAD") -> rc.Corrections:
    def read(path: str) -> str | None:
        p = root / path
        return p.read_text() if p.is_file() else None

    return rc.load(root, read, revision, rc.stamp(NOW))


def guard(root: Path, *args: str) -> dict:
    report = root / "guard-result.json"
    p = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            *args,
            "--repo",
            str(root),
            "--now",
            NOW,
            "--json",
            str(report),
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode in (0, 1), p.stdout + p.stderr
    return json.loads(report.read_text())


def errors(report: dict) -> list[dict]:
    return [v for c in report["checks"] for v in c["violations"]]


def test_valid_corrections_keep_originals_and_both_guards_count_them(records):
    root, base, entries = records
    originals = {p: (root / p).read_bytes() for p in (READOUT, rc.LEDGER)}
    before = guard(root, "dates", "--range", base + "..HEAD")
    assert any(v["rule"] == "R1" and v["path"] == READOUT for v in errors(before))
    ctx = tlc._ctx() | {"bound_dt": tlc.lc.parse_dt(NOW), "bound_iso": NOW}
    before_shape = tlc.lc.run_checks(tlc.lc.TreeSrc(root), ctx)
    assert "markup-id" in tlc._rules(before_shape)
    write_register(root, entries)
    validated = load(root)
    assert validated.errors == [] and validated.candidates == 2
    assert validated.dates == {(READOUT, POINTER): SOURCE_TIME}
    assert validated.headings == {(rc.LEDGER, PHASE)}
    commit(root, NOW)
    after = guard(root, "dates", "--range", base + "..HEAD")
    assert {(v["rule"], v["path"], v["line"]) for v in errors(after)} == {
        (v["rule"], v["path"], v["line"]) for v in errors(before) if v["path"] != READOUT
    }
    assert any(v["rule"] == "R1-corrected" for c in after["checks"] for v in c["warnings"])
    shape = tlc.lc.run_checks(tlc.lc.TreeSrc(root), ctx)
    assert "markup-id" not in tlc._rules(shape)
    assert "markup-corrected" in tlc._warn_rules(shape)
    assert originals == {p: (root / p).read_bytes() for p in originals}
    # Historical replay cannot borrow corrections from a later worktree.
    rev_src = tlc.lc.RevSrc(tlc.lc.Git(root), entries[0]["source_commit"])
    assert "markup-id" in tlc._rules(tlc.lc.run_checks(rev_src, ctx))


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "record-correction/2"),
        ("kind", "waive-all"),
        ("path", "../../other.md"),
        ("source_commit", "deadbeef"),
        ("source_commit", "0" * 40),
        ("source_line", 99999),
        ("source_line", True),
        ("line_sha256", "0" * 64),
        ("recorded_at", "2026-11-20T08:00:00Z"),
        ("recorded_at", "2026-11-19T06:00:00Z"),
        ("recorded_at", "2026-11-19"),
        ("interpretation", {"recorded_at_or_before": "2026-11-19T06:29:00Z"}),
        ("interpretation", {"recorded_at_or_before": SOURCE_TIME, "waiver": True}),
    ],
)
def test_invalid_evidence_rejects_the_entire_register(records, field, value):
    root, _, entries = records
    entries[0][field] = value
    write_register(root, entries)
    result = load(root)
    assert result.errors and not result.dates and not result.headings


def test_duplicate_target_even_identical_is_ambiguous(records):
    root, _, entries = records
    write_register(root, entries + [copy.deepcopy(entries[0])])
    assert load(root).errors


@pytest.mark.parametrize("mutation", ["duplicate", "rewrite", "remove"])
def test_original_target_must_remain_unique_and_unchanged(records, mutation):
    root, _, entries = records
    p = root / READOUT
    original = p.read_text()
    p.write_text(
        original + POINTER + "\n"
        if mutation == "duplicate"
        else original.replace(POINTER, "changed" if mutation == "rewrite" else "")
    )
    write_register(root, entries)
    assert load(root).errors


def test_descendant_commit_is_not_original_provenance(records):
    root, _, entries = records
    (root / "note.txt").write_text("unrelated\n")
    entries[0]["source_commit"] = commit(root, "2026-11-19T07:00:00Z")
    write_register(root, entries)
    assert any("did not introduce" in e for _, e in load(root).errors)


def test_nonancestor_source_rejected(records):
    root, base, entries = records
    write_register(root, entries)
    assert load(root, base).errors


@pytest.mark.parametrize("heading", ["P00.2 ticket", "P00.1 done", "P00.1 ticket extra"])
def test_markup_correction_cannot_change_identifier_kind_or_payload(records, heading):
    root, _, entries = records
    entries[1]["interpretation"] = {"heading": heading}
    write_register(root, entries)
    assert load(root).errors


def test_unrelated_future_date_remains_a_violation(records):
    root, base, entries = records
    write_register(root, entries)
    with (root / READOUT).open("a") as f:
        f.write("Date: 2026-12-01T00:00:00Z\n")
    commit(root, NOW)
    found = errors(guard(root, "dates", "--range", base + "..HEAD"))
    assert any(v["rule"] == "R1" and v["path"] == READOUT for v in found)


def test_unrelated_markup_still_fails(records):
    root, _, entries = records
    write_register(root, entries)
    with (root / rc.LEDGER).open("a") as f:
        f.write("- 2026-10-01 — **P00.2** correction — another record\n")
    ctx = tlc._ctx() | {"bound_dt": tlc.lc.parse_dt(NOW), "bound_iso": NOW}
    assert "markup-id" in tlc._rules(tlc.lc.run_checks(tlc.lc.TreeSrc(root), ctx))


def test_recording_time_checked_against_correction_commit(records):
    root, _, entries = records
    write_register(root, entries)
    commit(root, "2026-11-19T07:00:00Z")
    assert any("clock bounds" in e for _, e in load(root).errors)


def test_gate_row_upper_bound_cures_only_exact_recording_date(records):
    root, base, entries = records
    text = next(
        x
        for x in (root / rc.LEDGER).read_text().splitlines()
        if x.startswith("| 2026-11-19T06:55Z | GATE-T")
    )
    correction = dict(
        entries[0],
        kind="gate-row-recording-date",
        path=rc.LEDGER,
        source_line=(root / rc.LEDGER).read_text().splitlines().index(text) + 1,
        line_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )
    write_register(root, entries + [correction])
    assert load(root).errors == []
    commit(root, NOW)
    assert errors(guard(root, "dates", "--range", base + "..HEAD")) == []
    # A pause after the verified bound but before the erroneous original date
    # must not become a false pass through the correction.
    with (root / rc.LEDGER).open("a") as f:
        f.write("- 2026-11-19T06:40:00Z — GATE-T pause — waiting\n")
    commit(root, NOW)
    assert any(
        v["rule"] == "G4a-pause" and "precedes" in v["message"]
        for v in errors(guard(root, "gates", "--range", base + "..HEAD"))
    )
    correction["interpretation"] = {"event_time": SOURCE_TIME}
    write_register(root, entries + [correction])
    assert load(root).errors


@pytest.mark.parametrize("kind", ["waiver", "pre-authorization", "correction"])
def test_gate_date_correction_rejects_other_record_kinds(records, kind):
    root, _, entries = records
    p = root / rc.LEDGER
    text = next(
        x for x in p.read_text().splitlines() if x.startswith("| 2026-11-19T06:55Z | GATE-T")
    )
    changed = text.replace("| decision |", f"| {kind} |")
    p.write_text(p.read_text().replace(text, changed))
    source = commit(root)
    correction = dict(
        entries[0],
        kind="gate-row-recording-date",
        path=rc.LEDGER,
        source_commit=source,
        source_line=p.read_text().splitlines().index(changed) + 1,
        line_sha256=hashlib.sha256(changed.encode()).hexdigest(),
    )
    write_register(root, [correction])
    assert load(root).errors


@pytest.mark.parametrize(
    "gate,round_number,pause_time,expected",
    [
        ("GATE-ACCEPT-R11", "11", "2026-11-19T06:27:14Z", False),
        ("GATE-ACCEPT-R12", "11", "2026-11-19T06:27:14Z", True),
        ("GATE-ACCEPT-R11", "10", "2026-11-19T06:27:14Z", True),
        ("GATE-ACCEPT-R11", "11", "2026-11-19T07:00:00Z", True),
        ("GATE-ACCEPT", "11", "2026-11-19T06:27:14Z", True),
    ],
)
def test_complete_accept_gate_id_preserves_pause_guards(gate, round_number, pause_time, expected):
    pauses = mg.phase_entries(
        [
            f"## PHASE LOG — Round {round_number}",
            f"- {pause_time} — dispatch boundary-confirm — pause at {gate}",
        ]
    )
    report = mg.Report()
    judge = mg.Judge(None, None, report, True)
    judge.answer_after_pause(
        rc.LEDGER, 1, "fixture", SOURCE_TIME, "GATE-ACCEPT-R11 acceptance", "11", pauses
    )
    assert any(f.rule == "G4a-pause" for f in report.findings) == expected


def test_duplicate_json_keys_rejected(records):
    root, _, entries = records
    write_register(root, entries)
    p = root / rc.REGISTER
    p.write_text(p.read_text().replace('"schema":', '"schema": "ignored", "schema":', 1))
    assert load(root).errors


@pytest.mark.parametrize("mutation", ["rewrite", "delete"])
def test_register_prefix_protected_even_before_landing(records, mutation):
    root, _, entries = records
    write_register(root, entries)
    commit(root, NOW)
    p = root / rc.REGISTER
    if mutation == "delete":
        p.unlink()
    else:
        p.write_text(p.read_text().replace(NOW, "2026-11-19T07:59:00Z"))
    found = errors(guard(root, "append-only", "--worktree"))
    assert any(v["path"] == rc.REGISTER for v in found)
