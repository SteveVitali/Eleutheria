#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``later_register.py`` (COV-10; plan §15; Round 11 Stage B, SEED-14a).

Each test builds a small committed-input tree in ``tmp_path`` (round11_plan.csv, ticket_catalog.csv, the
plan's §15 table, UNIVERSE_DISPOSED.csv, decision_catalog.csv and a DEFERRALS.md) and runs the real CLI.
Every test asserts a file, a row, a cell or an exit code that a no-op generator (exit 0, nothing written)
cannot produce, so every test fails against a no-op. The last test runs ``--check`` on the real tree.

Run::

    uv run pytest docs/build/tools/test_later_register.py -q
"""

from __future__ import annotations

import csv
import importlib.util
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOL = HERE / "later_register.py"
REPO = HERE.parents[2]
PYTHON = os.environ.get("SIG_TOOLS_PYTHON") or sys.executable
PD = "docs/build/planning/2026-09-30-next-phase"
STAMP = "2026-10-01T15:00:00Z"

PLAN_COLS = [
    "row",
    "id",
    "cat_ids",
    "uses",
    "title",
    "sub_round",
    "phase",
    "kind",
    "depends_on",
    "operator_gate",
    "live_stage",
    "est_runs",
    "leg_runs",
    "live_legs",
    "window_constraints",
    "notes",
]
UNI_COLS = [
    "item_id",
    "source_kind",
    "source_ref",
    "title",
    "severity_or_status",
    "disposition",
    "disposition_ref",
    "rationale",
    "stream",
    "links",
]
DEC_COLS = ["dec_id", "question", "operator_answer", "answered_at"]

PLAN_MD = """# SIG Round 11 — the next-phase plan

> **CANONICAL for Round 11 — GATE-P passed 2026-10-01T05:03:05Z.** Fixture.

## 15. Explicitly deferred (each with its trigger)

| unit | what | trigger | runs · $/mo |
|---|---|---|---|
| LATER-01 | T-EVAL-IND segment; also closes D-P30.2b-1 | T-EVAL-IND (§11.3) | 6 · +10 |
| LATER-09 | acquisition long tail | per-family triggers (I8 §6.3) | 2 |

**Moved into Round 11 at S6:** LATER-10 (non-US keyed APIs → P37.70).

---

## Appendix A — checklist
"""

DEFERRALS_MD = """# Deferred obligations ledger

| id | kind | item | why deferred | unblocked by | how to verify | proxy now | status |
|---|---|---|---|---|---|---|---|
| D-X-1 | V | fixture row | fixture | owner: operator · trigger: fixture | fixture | none | OPEN 2026-09-01 (cites BL-001) |
"""


def _csv(cols: list[str], rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue()


def plan_rows() -> list[dict[str, str]]:
    seed = "trigger-seeded only (decompose-spec mode=extend)"
    return [
        {
            "id": "LATER-01",
            "title": "T-EVAL-IND segment",
            "sub_round": "later",
            "window_constraints": seed,
        },
        {
            "id": "LATER-09",
            "title": "Acquisition long tail",
            "sub_round": "later",
            "window_constraints": seed,
            "notes": "S6: tribal (B-32 S8) channels moved into Round 11",
        },
        {
            "id": "LATER-10",
            "title": "Non-US keyed APIs",
            "sub_round": "moved (S6) -> P37.70",
            "window_constraints": seed,
        },
        {"row": "434", "id": "P37.70", "title": "Keyed AU APIs", "sub_round": "11D"},
    ]


def universe_rows() -> list[dict[str, str]]:
    return [
        {
            "item_id": "U-0001",
            "source_kind": "deferral",
            "source_ref": "D-X-1",
            "title": "fixture deferral | with a pipe",
            "disposition": "later-phase(T-EVAL-IND: >=2 independent labellers available)",
            "disposition_ref": "LATER-01",
        },
        {
            "item_id": "U-0090",
            "source_kind": "deferral",
            "source_ref": "D-SOURCES.8-2",
            "title": "keyed national camera APIs",
            "disposition": "later-phase(non-US keyed traffic APIs wanted)",
            "disposition_ref": "LATER-10",
            "links": "gate:D-SOURCES.8-2",
        },
        {
            "item_id": "CG-LATER-tribal-data-governance-rule-i7-new-6",
            "source_kind": "candidate_group",
            "source_ref": "data/acquisition_plan.csv ticket=later-phase(tribal)",
            "title": "3 acquisition-plan rows",
            "severity_or_status": "n=3 candidates; tiers T2:3",
            "disposition": "later-phase(tribal data-governance rule, I7 NEW-6)",
            "disposition_ref": "LATER-09",
        },
        {
            "item_id": "CG-LATER-ocr-path",
            "source_kind": "candidate_group",
            "source_ref": "data/acquisition_plan.csv ticket=later-phase(OCR path)",
            "title": "5 acquisition-plan rows",
            "severity_or_status": "n=5 candidates; tiers T2:5",
            "disposition": "later-phase(OCR path)",
            "disposition_ref": "LATER-09",
        },
        {
            "item_id": "U-0400",
            "source_kind": "adr_trigger",
            "source_ref": "ADR-001",
            "title": "Python primary",
            "disposition": "later-phase(ADR-001's own revisit trigger (quiet today))",
            "disposition_ref": "ADR-001 revisit trigger",
        },
        {
            "item_id": "U-0039",
            "source_kind": "deferral",
            "source_ref": "D-P30.2b-1",
            "title": "operator curation of camsite seed items",
            "disposition": "decision(D-P30.2b-1)",
            "disposition_ref": "D-P30.2b-1",
        },
        {
            "item_id": "U-0500",
            "source_kind": "requirement",
            "source_ref": "SIG-X-001",
            "title": "a ticketed item",
            "disposition": "ticket(R11-X)",
            "disposition_ref": "R11-X",
        },
    ]


def decision_rows() -> list[dict[str, str]]:
    return [
        {
            "dec_id": "D-SOURCES.8-2",
            "operator_answer": "a — register the keys",
            "answered_at": "2026-10-01T04:39:45Z",
        },
        {
            "dec_id": "I7-S8",
            "operator_answer": "a — 'Include S8 screened lane'",
            "answered_at": "2026-10-01T04:43:37Z",
        },
        {
            "dec_id": "D-P30.2b-1",
            "operator_answer": "a (fold) — no fold target: stays OPEN, non-blocking, trigger T-EVAL-IND",
            "answered_at": "2026-10-01T04:39:45Z",
        },
    ]


def make_tree(root: Path, plan: list[dict[str, str]] | None = None, plan_md: str = PLAN_MD) -> Path:
    files = {
        f"{PD}/data/round11_plan.csv": _csv(PLAN_COLS, plan if plan is not None else plan_rows()),
        f"{PD}/data/ticket_catalog.csv": _csv(
            ["cat_id", "operator_gate"],
            [
                {"cat_id": "LATER-01", "operator_gate": "T-EVAL-IND (operator)"},
                {"cat_id": "LATER-09", "operator_gate": "none"},
            ],
        ),
        f"{PD}/universe/UNIVERSE_DISPOSED.csv": _csv(UNI_COLS, universe_rows()),
        f"{PD}/data/decision_catalog.csv": _csv(DEC_COLS, decision_rows()),
        f"{PD}/NEXT_PHASE_PLAN.md": plan_md,
        "docs/tickets/DEFERRALS.md": DEFERRALS_MD,
    }
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(TOOL), "--root", str(root), *args], capture_output=True, text=True, check=False
    )


def write(root: Path) -> subprocess.CompletedProcess[str]:
    res = run(root, "--recorded-at", STAMP)
    assert res.returncode == 0, res.stderr
    return res


def deferrals(root: Path) -> str:
    return (root / "docs/tickets/DEFERRALS.md").read_text(encoding="utf-8")


def register_csv(root: Path) -> list[dict[str, str]]:
    with (root / "docs/build/reports/later-register/later_register.csv").open(
        newline="", encoding="utf-8"
    ) as fh:
        return list(csv.DictReader(fh))


def row_line(text: str, rid: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.startswith(f"| {rid} |")]
    assert len(lines) == 1, f"{rid}: {len(lines)} rows"
    return lines[0]


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


# ── write ─────────────────────────────────────────────────────────────────────────────────────────────


def test_write_creates_register_and_one_owed_row_per_later_unit(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    md = (root / "docs/build/reports/later-register/LATER_REGISTER.md").read_text(encoding="utf-8")
    assert "T-EVAL-IND (§11.3)" in md and "per-family triggers (I8 §6.3)" in md
    for item in ("U-0001", "U-0090", "CG-LATER-ocr-path", "U-0400", "U-0039"):
        assert f"| {item} |" in md, item
    assert "| U-0500 |" not in md  # a ticketed item is not later-phase
    text = deferrals(root)
    assert "\n## Later-phase register (Round 11)\n" in text
    assert text.startswith(DEFERRALS_MD)  # append-only: the old bytes are a prefix
    for rid, kind in (("D-R11-LATER-01", "P"), ("D-R11-LATER-09", "F")):
        c = cells(row_line(text, rid))
        assert len(c) == 8
        assert c[1] == kind
        assert "owner:" in c[4] and "trigger:" in c[4], "rule 5: owner:/trigger: in 'unblocked by'"
        assert re.match(r"^OPEN 2026-10-01 \(SEED-14a; cites BL-\d{3}", c[7])
    assert "| D-R11-LATER-10 |" not in text  # moved into the round: no later-phase row
    assert "LATER-10 → P37.70" in text


def test_redispositions_follow_the_operator_answers(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    by_id = {r["id"]: r for r in register_csv(root) if r["record_type"] == "item"}
    assert by_id["U-0090"]["round11_status"] == "moved into Round 11"
    assert by_id["U-0090"]["landing"] == "P37.70"
    assert by_id["U-0090"]["decided_at"] == "2026-10-01T04:39:45Z"
    tribal = by_id["CG-LATER-tribal-data-governance-rule-i7-new-6"]
    assert tribal["round11_status"] == "moved into Round 11" and tribal["deferrals_row"] == ""
    assert by_id["U-0039"]["unit"] == "LATER-01"
    assert by_id["U-0039"]["round11_status"].startswith("later (re-dispositioned")
    assert by_id["U-0039"]["deferrals_row"] == "D-R11-LATER-01"
    assert by_id["U-0400"]["deferrals_row"] == "" and by_id["U-0400"]["round11_status"] == "later"
    assert "ADR_TRIGGERS.csv" in by_id["U-0400"]["record_refs"]
    assert by_id["U-0001"]["decided_at"] == "2026-10-01T05:03:05Z"  # the GATE-P time
    units = {r["id"]: r for r in register_csv(root) if r["record_type"] == "unit"}
    assert set(units) == {"LATER-01", "LATER-09", "LATER-10"}
    assert units["LATER-10"]["round11_status"] == "moved into Round 11"
    # the item list on the LATER-09 row counts only the candidate group still later-phase
    assert "1 candidate groups (5 candidates)" in row_line(deferrals(root), "D-R11-LATER-09")


def test_cells_never_carry_a_pipe(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    md = (root / "docs/build/reports/later-register/LATER_REGISTER.md").read_text(encoding="utf-8")
    line = next(ln for ln in md.splitlines() if ln.startswith("| U-0001 |"))
    assert "fixture deferral / with a pipe" in line
    assert len(cells(line)) == 10


def test_write_is_idempotent(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    first = (deferrals(root), register_csv(root))
    write(root)
    assert (deferrals(root), register_csv(root)) == first
    assert deferrals(root).count("## Later-phase register (Round 11)") == 1


def test_output_is_deterministic_across_trees(tmp_path: Path) -> None:
    a, b = make_tree(tmp_path / "a"), make_tree(tmp_path / "b")
    write(a)
    write(b)
    for rel in (
        "docs/build/reports/later-register/LATER_REGISTER.md",
        "docs/build/reports/later-register/later_register.csv",
    ):
        assert (a / rel).read_bytes() == (b / rel).read_bytes()


def test_a_new_unit_is_appended_under_additions_never_rewriting(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    before = deferrals(root)
    plan = plan_rows() + [{"id": "LATER-02", "title": "Usability study", "sub_round": "later"}]
    md = PLAN_MD.replace(
        "| LATER-09 |",
        "| LATER-02 | usability study on the live site | participants available | 1 |\n| LATER-09 |",
    )
    make_tree(root, plan=plan, plan_md=md)
    (root / "docs/tickets/DEFERRALS.md").write_text(before, encoding="utf-8")
    write(root)
    after = deferrals(root)
    assert after.startswith(before)
    assert "### Later-phase register — additions" in after[len(before) :]
    assert "| D-R11-LATER-02 |" in after[len(before) :]
    assert after.count("| D-R11-LATER-01 |") == 1
    assert run(root, "--check").returncode == 0


# ── check ─────────────────────────────────────────────────────────────────────────────────────────────


def test_check_fails_before_any_write(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    res = run(root, "--check")
    assert res.returncode == 1
    assert "missing" in res.stderr


def test_check_passes_after_write(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    res = run(root, "--check")
    assert res.returncode == 0, res.stderr
    assert "ok" in res.stdout


def test_check_detects_a_hand_edited_register(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    p = root / "docs/build/reports/later-register/LATER_REGISTER.md"
    p.write_text(
        p.read_text(encoding="utf-8").replace("T-EVAL-IND (§11.3)", "T-EVAL-IND"), encoding="utf-8"
    )
    res = run(root, "--check")
    assert res.returncode == 1 and "LATER_REGISTER.md" in res.stderr


def test_check_detects_a_rewritten_row(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    text = deferrals(root)
    line = row_line(text, "D-R11-LATER-01")
    bad = line.replace("trigger: T-EVAL-IND (§11.3)", "trigger: whenever")
    (root / "docs/tickets/DEFERRALS.md").write_text(text.replace(line, bad), encoding="utf-8")
    res = run(root, "--check")
    assert res.returncode == 1 and "unblocked by" in res.stderr


def test_check_detects_a_deleted_row(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    text = deferrals(root)
    (root / "docs/tickets/DEFERRALS.md").write_text(
        text.replace(row_line(text, "D-R11-LATER-09") + "\n", ""), encoding="utf-8"
    )
    res = run(root, "--check")
    assert res.returncode == 1 and "D-R11-LATER-09 is missing" in res.stderr


def test_check_allows_a_grown_row(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    text = deferrals(root)
    line = row_line(text, "D-R11-LATER-01")
    grown = line.replace(
        "| none — no Round-11 row waits on it |",
        "| none — no Round-11 row waits on it · **2026-11-01 note** |",
    )
    grown = grown[:-2] + " · **annotated: trigger fired (fixture)** |"
    (root / "docs/tickets/DEFERRALS.md").write_text(text.replace(line, grown), encoding="utf-8")
    res = run(root, "--check")
    assert res.returncode == 0, res.stderr


def test_check_detects_an_input_change(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    write(root)
    written = deferrals(root)
    make_tree(root, plan_md=PLAN_MD.replace("T-EVAL-IND (§11.3)", "T-EVAL-IND (§11.4)"))
    (root / "docs/tickets/DEFERRALS.md").write_text(written, encoding="utf-8")
    res = run(root, "--check")
    assert res.returncode == 1
    assert "LATER_REGISTER.md" in res.stderr and "D-R11-LATER-01" in res.stderr


def test_unit_without_agent_reading_is_an_input_error(tmp_path: Path) -> None:
    plan = plan_rows() + [{"id": "LATER-99", "title": "unknown", "sub_round": "later"}]
    md = PLAN_MD.replace("| LATER-09 |", "| LATER-99 | unknown | never | 0 |\n| LATER-09 |")
    root = make_tree(tmp_path, plan=plan, plan_md=md)
    res = run(root, "--recorded-at", STAMP)
    assert res.returncode == 2 and "UNIT_META" in res.stderr
    assert "Later-phase register" not in deferrals(root)


def test_recorded_at_must_be_a_clock_stamp(tmp_path: Path) -> None:
    root = make_tree(tmp_path)
    res = run(root, "--recorded-at", "2026-10-01")
    assert res.returncode == 2
    assert "Later-phase register" not in deferrals(root)


def test_generated_rows_satisfy_the_backlog_home_rule(tmp_path: Path) -> None:
    """The real ``check_backlog.deferral_homes`` sees every generated owed row citing a BL home."""
    spec = importlib.util.spec_from_file_location("check_backlog", HERE / "check_backlog.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    root = make_tree(tmp_path)
    write(root)
    citing, missing = mod.deferral_homes(root / "docs/tickets/DEFERRALS.md")
    assert "D-R11-LATER-01" in citing and "D-R11-LATER-09" in citing
    assert not missing


# ── the real tree ─────────────────────────────────────────────────────────────────────────────────────


def test_real_tree_register_is_in_sync() -> None:
    if not (REPO / PD / "data/round11_plan.csv").is_file():
        pytest.skip("planning inputs not present in this checkout")
    res = subprocess.run(
        [PYTHON, str(TOOL), "--check"], capture_output=True, text=True, check=False
    )
    assert res.returncode == 0, res.stderr + res.stdout
    assert re.search(r"later_register --check: ok — \d+ units, \d+ later-phase items", res.stdout)
