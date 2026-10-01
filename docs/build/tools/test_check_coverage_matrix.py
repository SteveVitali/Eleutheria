#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``check_coverage_matrix.py`` — the ADR-150 verdict grammar and the SIG-ENG-041 cross-checks
(SEED-15, Round 11 Stage B T4).

Each rule is exercised on a small fixture tree: a valid baseline passes, and one mutation per test makes
exactly that rule fail. Collected by ``make test`` (``testpaths`` includes ``docs/build/tools``)::

    uv run pytest docs/build/tools/test_check_coverage_matrix.py
"""

from __future__ import annotations

import csv
import importlib.util
import io
import pathlib

import pytest

_HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[2]
_spec = importlib.util.spec_from_file_location(
    "check_coverage_matrix", _HERE / "check_coverage_matrix.py"
)
ccm = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(ccm)

SPEC = """# Spec

**SIG-AA-001 (MUST).** One.

**SIG-AA-002 (MUST).** Two.

**SIG-AA-003a (SHOULD).** Three.

**SIG-AA-004 (MUST).** Four.

**SIG-AA-005 (MUST).** Five.

## G.9 Round corrections

### G.9.2 Waivers adopted by the operator

| # | Section (id) | Clause waived | Operator's words | ADR |
|---|---|---|---|---|
| R-W1 | §1 (SIG-AA-004) | the clause | W-1, 2026-10-01T04:00:00Z | ADR-200 |

### G.9.3 Amendments applied (none weakens a MUST)

| # | Section (id) | Change | Authority |
|---|---|---|---|
| R-A1 | §1 (SIG-AA-002) | wording | ADR-201 |
"""

MANIFEST = """# Manifest

## The chain

| # | file | phase | kind |
|---|---|---|---|
| 1 | `001_P01.1__first.md` | 1 | ticket |
| 2 | `002_P01.2__second.md` | 1 | ticket |
| 3 | `003_P01.2a__third.md` | 1 | ticket |
| 4 | `P01.3__legacy-name.md` | 1 | ticket |
"""

INDEX = """# Build index

| seq | ticket | branch |
|---|---|---|
| 1 | P01.1 first-ticket | `p01-1` |
| 4 | P01.3 | `p01-3` |
"""

BACKLOG = (
    "bl_id,title,type,sources,req_ids,package,blocks,landing,gate,size,status\n"
    "BL-001,open row,process,ADR-200,,,,P01+,,S,open\n"
    "BL-002,accepted row,process,ADR-201,,,,accepted,,S,accepted\n"
    "BL-003,closed row,process,RISK-P1-01,,,,closed-by:P01.1,,S,closed\n"
)

DEFERRALS = """# Deferrals

| id | item | why | unblocked by | verify | proxy | status |
|---|---|---|---|---|---|---|
| D-X.1-1 | leg one | x | owner: P01.2 · trigger: t | v | p | OPEN (cites BL-001) |
| D-X.1-2 | leg two | x | owner: P01.2 · trigger: t | v | p | OPEN (cites BL-001) |
| D-X.1-3 | leg done | x | owner: P01.1 | v | p | DONE 2026-09-01 |
"""

ADR_200 = """# ADR-200: The waiver

- **Status:** Accepted
- **Requirement ids:** SIG-AA-004

## Decision

The operator waived SIG-AA-004's clause.

## Revisit trigger

- When the scope ends.
"""

ADR_201 = """# ADR-201: Another mechanism

- **Status:** Accepted

Meets SIG-AA-002 differently.

## Revisit trigger

- Never.
"""

ADR_202 = """# ADR-202 — Legacy header

- Status: superseded by ADR-201

Mentions SIG-AA-002.

## Revisit trigger

- None.
"""

RISK = """# Risk register

| id | risk | control |
|---|---|---|
| RISK-P1-01 | SIG-AA-001 cannot be verified automatically | a compensating review |
"""

BASE_ROWS = [
    # id, level, verdict, evidence, routing, required, achieved, legs, scope
    ("SIG-AA-001", "MUST", "MET", "src/x.py:1", "—", "", "", "", ""),
    (
        "SIG-AA-002",
        "MUST",
        "MET-DIFFERENTLY(ADR-201)",
        "src/x.py",
        "accepted",
        "implementation",
        "implementation",
        "",
        "",
    ),
    ("SIG-AA-003a", "SHOULD", "MISSING", "", "P01.2", "implementation", "", "", ""),
    (
        "SIG-AA-004",
        "MUST",
        "WAIVED(ADR-200)",
        "",
        "P01.2a",
        "public",
        "",
        "",
        "ADR-200@2026-10-01#the-clause",
    ),
    (
        "SIG-AA-005",
        "MUST",
        "MET-ENGINEERED(D-X.1-1;D-X.1-2)",
        "src/x.py",
        "BL-001",
        "hosted",
        "implementation",
        "D-X.1-1;D-X.1-2",
        "",
    ),
]


def _matrix(rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(ccm.HEADER)
    for rid, level, verdict, ev, routing, req, ach, legs, scope in rows:
        w.writerow(
            [
                rid,
                level,
                "§1",
                "covered+tested",
                verdict,
                ev,
                "P01.1",
                "—",
                "—",
                "—",
                routing,
                "note",
                req,
                ach,
                legs,
                scope,
            ]
        )
    return buf.getvalue()


def _tree(tmp_path: pathlib.Path, rows=None, spec: str = SPEC) -> pathlib.Path:
    root = tmp_path / "repo"
    files = {
        "docs/2_canonical_design_spec.md": spec,
        "docs/tickets/00_MANIFEST.md": MANIFEST,
        "docs/build/BUILD_INDEX.md": INDEX,
        "docs/build/BACKLOG.csv": BACKLOG,
        "docs/tickets/DEFERRALS.md": DEFERRALS,
        "docs/adr/ADR-200-the-waiver.md": ADR_200,
        "docs/adr/ADR-201-another-mechanism.md": ADR_201,
        "docs/adr/ADR-202-legacy.md": ADR_202,
        "docs/risk_register.md": RISK,
        "src/x.py": "x = 1\n",
        "docs/build/COVERAGE_MATRIX.csv": _matrix(BASE_ROWS if rows is None else rows),
    }
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def _errors(root: pathlib.Path) -> list[str]:
    errors, _ = ccm.check(root, root / "docs/build/COVERAGE_MATRIX.csv")
    return errors


def _with(**changes):
    """BASE_ROWS with one row replaced: ``_with(**{"SIG-AA-003a": (...)})``."""
    rows = []
    for row in BASE_ROWS:
        rows.append(changes.get(row[0].replace("-", "_"), row))
    return rows


def _row(rid, verdict, ev="", routing="P01.2", req="", ach="", legs="", scope="", level="MUST"):
    return (rid, level, verdict, ev, routing, req, ach, legs, scope)


# ── baseline ─────────────────────────────────────────────────────────────────


def test_valid_fixture_passes_and_reports_counts(tmp_path, capsys) -> None:
    root = _tree(tmp_path)
    assert _errors(root) == []
    assert ccm.main(["check_coverage_matrix.py", str(root / "docs/build/COVERAGE_MATRIX.csv")]) == 0
    out = capsys.readouterr().out
    assert "offered: 5 spec ids, 5 matrix rows, 1 spec waiver records" in out
    assert "evaluated: 5 rows" in out and "5 rows OK" in out


def test_root_defaults_to_the_repo_when_no_path_is_given(tmp_path) -> None:
    root = _tree(tmp_path)
    assert ccm.main(["check_coverage_matrix.py", "--root", str(root)]) == 0


# ── structure: spec-derived count, header, vacuous input ─────────────────────


def test_expected_count_is_derived_from_the_spec(tmp_path) -> None:
    root = _tree(tmp_path, spec=SPEC + "\n**SIG-AA-006 (MAY).** Six.\n")
    errs = _errors(root)
    assert any("spec defines 6 ids" in e for e in errs), errs
    assert any("spec ids missing from the matrix" in e and "SIG-AA-006" in e for e in errs), errs


def test_legacy_twelve_column_header_fails(tmp_path) -> None:
    root = _tree(tmp_path)
    p = root / "docs/build/COVERAGE_MATRIX.csv"
    lines = p.read_text().splitlines()
    lines[0] = ",".join(ccm.LEGACY_HEADER)
    p.write_text("\n".join(lines) + "\n")
    assert any("header mismatch" in e for e in _errors(root))


def test_empty_spec_or_matrix_is_never_a_vacuous_pass(tmp_path) -> None:
    root = _tree(tmp_path, rows=[], spec="# nothing defined\n")
    errs = _errors(root)
    assert any("defines no requirement ids" in e for e in errs), errs
    assert any("no data rows" in e for e in errs), errs


def test_unknown_domain_word_fails(tmp_path) -> None:
    root = _tree(
        tmp_path,
        _with(SIG_AA_003a=_row("SIG-AA-003a", "MISSING", req="production", level="SHOULD")),
    )
    assert any("bad required_domain" in e for e in _errors(root))


# ── verdict grammar ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "verdict, expected",
    [
        ("MET", ("MET", ())),
        ("N/A-RATIONALE", ("N/A-RATIONALE", ())),
        ("MET-DIFFERENTLY", ("MET-DIFFERENTLY", ())),
        ("MET-DIFFERENTLY(ADR-108;ADR-133)", ("MET-DIFFERENTLY", ("ADR-108", "ADR-133"))),
        ("MET-DIFFERENTLY(RISK-P5-04a)", ("MET-DIFFERENTLY", ("RISK-P5-04a",))),
        (
            "MET-ENGINEERED(D-P21.5-1;D-R11-ARCHIVE-1)",
            ("MET-ENGINEERED", ("D-P21.5-1", "D-R11-ARCHIVE-1")),
        ),
        ("WAIVED(ADR-153)", ("WAIVED", ("ADR-153",))),
        ("AT-RISK-INTEGRATION", ("AT-RISK-INTEGRATION", ())),
    ],
)
def test_grammar_accepts_each_verdict_form(verdict, expected) -> None:
    assert ccm.parse_verdict(verdict) == expected
    assert verdict in ccm.VERDICTS


@pytest.mark.parametrize(
    "verdict",
    [
        "WAIVED",
        "WAIVED(ADR-153;ADR-154)",
        "WAIVED(RISK-P1-01)",
        "MET-ENGINEERED",
        "MET-ENGINEERED()",
        "MET-ENGINEERED(ADR-150)",
        "MET(ADR-150)",
        "PARTIAL(D-X.1-1)",
        "MET-DIFFERENTLY(boilerplate)",
        "MET-DIFFERENTLY(ADR-1)",
        "NA",
        "MET-PENDING",
        "met",
        "",
    ],
)
def test_grammar_rejects_malformed_verdicts(verdict) -> None:
    assert ccm.parse_verdict(verdict) is None
    assert verdict not in ccm.VERDICTS


def test_non_met_membership_follows_the_grammar() -> None:
    assert "WAIVED(ADR-153)" in ccm.NON_MET_VERDICTS
    assert "MET-ENGINEERED(D-R10-LIVE-1)" in ccm.NON_MET_VERDICTS
    assert "MISSING" in ccm.NON_MET_VERDICTS
    assert "MET" not in ccm.NON_MET_VERDICTS and "N/A-RATIONALE" not in ccm.NON_MET_VERDICTS
    assert set(ccm.VERDICTS) == set(ccm.BASE_VERDICTS)


def test_off_grammar_verdict_in_the_matrix_fails(tmp_path) -> None:
    root = _tree(tmp_path, _with(SIG_AA_003a=_row("SIG-AA-003a", "WAIVED", level="SHOULD")))
    assert any("off the ADR-150 grammar" in e for e in _errors(root))


# ── routing ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("routing", ["P01.2", "P01.2a", "BL-001", "SEED-15", "SEED-02"])
def test_open_verdict_routes_to_unlanded_rows_open_backlog_rows_and_seed_units(
    tmp_path, routing
) -> None:
    root = _tree(
        tmp_path, _with(SIG_AA_003a=_row("SIG-AA-003a", "MISSING", routing=routing, level="SHOULD"))
    )
    assert _errors(root) == []


@pytest.mark.parametrize(
    "routing, needle",
    [
        ("P01.1", "which has landed"),
        ("P01.3", "which has landed"),
        ("BL-003", "whose status is 'closed'"),
        ("BL-002", "whose status is 'accepted'"),
        ("accepted", "routed to 'accepted'"),
        ("—", "requires a non-'—' routing"),
        ("P99.9", "is not a chain row of the manifest"),
        ("BL-999", "is not a BACKLOG row"),
        ("someday", "bad routing"),
    ],
)
def test_open_verdict_misrouted_fails(tmp_path, routing, needle) -> None:
    root = _tree(
        tmp_path,
        _with(
            SIG_AA_003a=_row(
                "SIG-AA-003a", "PARTIAL", ev="src/x.py", routing=routing, level="SHOULD"
            )
        ),
    )
    errs = _errors(root)
    assert any(needle in e for e in errs), errs


def test_met_may_keep_a_historical_routing_to_a_landed_ticket(tmp_path) -> None:
    root = _tree(
        tmp_path, _with(SIG_AA_001=_row("SIG-AA-001", "MET", ev="src/x.py", routing="P01.1"))
    )
    assert _errors(root) == []


def test_bare_met_differently_is_legacy_only_while_routed_to_its_reverdict_row(tmp_path) -> None:
    ok = _tree(
        tmp_path / "ok",
        _with(SIG_AA_002=_row("SIG-AA-002", "MET-DIFFERENTLY", ev="src/x.py", routing="P01.2")),
    )
    assert _errors(ok) == []
    bad = _tree(
        tmp_path / "bad",
        _with(SIG_AA_002=_row("SIG-AA-002", "MET-DIFFERENTLY", ev="src/x.py", routing="accepted")),
    )
    errs = _errors(bad)
    assert any("bare (legacy) MET-DIFFERENTLY" in e for e in errs), errs


# ── MET / MET-DIFFERENTLY entry rules ────────────────────────────────────────


def test_met_with_an_open_owed_leg_fails(tmp_path) -> None:
    root = _tree(
        tmp_path,
        _with(SIG_AA_001=_row("SIG-AA-001", "MET", ev="src/x.py", routing="—", legs="D-X.1-1")),
    )
    assert any("open owed leg" in e for e in _errors(root))


def test_met_with_a_done_leg_passes(tmp_path) -> None:
    root = _tree(
        tmp_path,
        _with(SIG_AA_001=_row("SIG-AA-001", "MET", ev="src/x.py", routing="—", legs="D-X.1-3")),
    )
    assert _errors(root) == []


def test_scoped_acceptance_never_raises_a_verdict(tmp_path) -> None:
    root = _tree(
        tmp_path,
        _with(
            SIG_AA_001=_row(
                "SIG-AA-001", "MET", ev="src/x.py", routing="—", scope="GATE-G3@2026-09-28#publish"
            )
        ),
    )
    assert any("scoped acceptance never raises a verdict" in e for e in _errors(root))


@pytest.mark.parametrize("req, ach", [("hosted", "implementation"), ("public+human", "public")])
def test_met_below_its_required_domain_fails(tmp_path, req, ach) -> None:
    root = _tree(
        tmp_path,
        _with(SIG_AA_001=_row("SIG-AA-001", "MET", ev="src/x.py", routing="—", req=req, ach=ach)),
    )
    assert any("below required_domain" in e for e in _errors(root))


def test_met_needs_evidence_and_the_evidence_must_exist(tmp_path) -> None:
    blank = _tree(
        tmp_path / "blank", _with(SIG_AA_001=_row("SIG-AA-001", "MET", ev="", routing="—"))
    )
    assert any("requires non-blank evidence" in e for e in _errors(blank))
    gone = _tree(
        tmp_path / "gone",
        _with(SIG_AA_001=_row("SIG-AA-001", "MET", ev="src/missing.py:3;spec §1", routing="—")),
    )
    errs = _errors(gone)
    assert any("'src/missing.py' does not exist" in e for e in errs), errs


def test_met_differently_adr_must_exist_be_accepted_and_name_the_id(tmp_path) -> None:
    missing = _tree(
        tmp_path / "a",
        _with(
            SIG_AA_002=_row(
                "SIG-AA-002", "MET-DIFFERENTLY(ADR-299)", ev="src/x.py", routing="accepted"
            )
        ),
    )
    assert any("ADR-299, which has no file" in e for e in _errors(missing))
    superseded = _tree(
        tmp_path / "b",
        _with(
            SIG_AA_002=_row(
                "SIG-AA-002", "MET-DIFFERENTLY(ADR-202)", ev="src/x.py", routing="accepted"
            )
        ),
    )
    assert any("ADR-202, which is not Accepted" in e for e in _errors(superseded))
    unnamed = _tree(
        tmp_path / "c",
        _with(
            SIG_AA_001=_row(
                "SIG-AA-001", "MET-DIFFERENTLY(ADR-201)", ev="src/x.py", routing="accepted"
            )
        ),
    )
    assert any("does not name SIG-AA-001" in e for e in _errors(unnamed))


def test_met_differently_risk_row_must_exist_and_name_the_id(tmp_path) -> None:
    ok = _tree(
        tmp_path / "ok",
        _with(
            SIG_AA_001=_row(
                "SIG-AA-001", "MET-DIFFERENTLY(RISK-P1-01)", ev="src/x.py", routing="accepted"
            )
        ),
    )
    assert _errors(ok) == []
    bad = _tree(
        tmp_path / "bad",
        _with(
            SIG_AA_002=_row(
                "SIG-AA-002", "MET-DIFFERENTLY(RISK-P1-01)", ev="src/x.py", routing="accepted"
            )
        ),
    )
    assert any("whose row does not name SIG-AA-002" in e for e in _errors(bad))
    gone = _tree(
        tmp_path / "gone",
        _with(
            SIG_AA_001=_row(
                "SIG-AA-001", "MET-DIFFERENTLY(RISK-P9-99)", ev="src/x.py", routing="accepted"
            )
        ),
    )
    assert any("not a risk-register row" in e for e in _errors(gone))


# ── MET-ENGINEERED ───────────────────────────────────────────────────────────


def test_met_engineered_parameters_must_equal_owed_legs(tmp_path) -> None:
    root = _tree(
        tmp_path,
        _with(
            SIG_AA_005=_row(
                "SIG-AA-005",
                "MET-ENGINEERED(D-X.1-1)",
                ev="src/x.py",
                routing="BL-001",
                legs="D-X.1-1;D-X.1-2",
            )
        ),
    )
    assert any("!= owed_legs" in e for e in _errors(root))


def test_met_engineered_without_owed_legs_fails(tmp_path) -> None:
    root = _tree(
        tmp_path,
        _with(
            SIG_AA_005=_row(
                "SIG-AA-005", "MET-ENGINEERED(D-X.1-1)", ev="src/x.py", routing="BL-001"
            )
        ),
    )
    assert any("needs owed_legs" in e for e in _errors(root))


def test_met_engineered_with_a_closed_or_unknown_leg_fails(tmp_path) -> None:
    done = _tree(
        tmp_path / "done",
        _with(
            SIG_AA_005=_row(
                "SIG-AA-005",
                "MET-ENGINEERED(D-X.1-3)",
                ev="src/x.py",
                routing="BL-001",
                legs="D-X.1-3",
            )
        ),
    )
    assert any("no longer OPEN/PARTIAL" in e for e in _errors(done))
    unknown = _tree(
        tmp_path / "unknown",
        _with(
            SIG_AA_005=_row(
                "SIG-AA-005",
                "MET-ENGINEERED(D-X.9-9)",
                ev="src/x.py",
                routing="BL-001",
                legs="D-X.9-9",
            )
        ),
    )
    assert any("is not a DEFERRALS row" in e for e in _errors(unknown))


# ── WAIVED and "an amendment that weakens a MUST is a waiver" ────────────────


def test_waived_must_cite_an_existing_adr(tmp_path) -> None:
    root = _tree(
        tmp_path,
        _with(
            SIG_AA_004=_row(
                "SIG-AA-004", "WAIVED(ADR-299)", routing="P01.2a", scope="ADR-299@2026-10-01#c"
            )
        ),
    )
    errs = _errors(root)
    assert any("WAIVED cites ADR-299, which has no file" in e for e in errs), errs


def test_waived_adr_must_name_the_id_and_carry_a_revisit_trigger(tmp_path) -> None:
    root = _tree(tmp_path)
    (root / "docs/adr/ADR-200-the-waiver.md").write_text(
        "# ADR-200: x\n\n- **Status:** Accepted\n\nNo id here.\n"
    )
    errs = _errors(root)
    assert any("does not name SIG-AA-004" in e for e in errs), errs
    assert any("no '## Revisit trigger'" in e for e in errs), errs


def test_waived_needs_a_scope_naming_its_adr_and_no_open_leg(tmp_path) -> None:
    no_scope = _tree(
        tmp_path / "a", _with(SIG_AA_004=_row("SIG-AA-004", "WAIVED(ADR-200)", routing="P01.2a"))
    )
    assert any("needs an accepted_scope" in e for e in _errors(no_scope))
    other = _tree(
        tmp_path / "b",
        _with(
            SIG_AA_004=_row(
                "SIG-AA-004", "WAIVED(ADR-200)", routing="P01.2a", scope="ADR-201@2026-10-01#c"
            )
        ),
    )
    assert any("accepted_scope does not name ADR-200" in e for e in _errors(other))
    leg = _tree(
        tmp_path / "c",
        _with(
            SIG_AA_004=_row(
                "SIG-AA-004",
                "WAIVED(ADR-200)",
                routing="P01.2a",
                legs="D-X.1-1",
                scope="ADR-200@2026-10-01#c",
            )
        ),
    )
    assert any("WAIVED with open owed leg" in e for e in _errors(leg))


def test_waived_row_without_a_spec_waiver_record_fails(tmp_path) -> None:
    root = _tree(
        tmp_path,
        spec=SPEC.replace(
            "| R-W1 | §1 (SIG-AA-004) | the clause | W-1, 2026-10-01T04:00:00Z | ADR-200 |\n", ""
        ),
    )
    errs = _errors(root)
    assert any("not recorded in the spec's waiver table" in e for e in errs), errs


def test_a_weakened_must_recorded_in_the_spec_must_be_waived_in_the_matrix(tmp_path) -> None:
    root = _tree(
        tmp_path, _with(SIG_AA_004=_row("SIG-AA-004", "PARTIAL", ev="src/x.py", routing="P01.2a"))
    )
    errs = _errors(root)
    assert any("a weakened MUST is WAIVED(ADR), never a silent amendment" in e for e in errs), errs


def test_amendment_tables_outside_the_waiver_section_are_not_waivers() -> None:
    records = ccm.waiver_records(SPEC)
    assert records == {"SIG-AA-004": {"ADR-200"}}


# ── the real tree ────────────────────────────────────────────────────────────


def test_real_matrix_passes_the_checker() -> None:
    """The committed matrix satisfies the grammar and every cross-check (the `make docs-check-matrix` gate)."""
    csv_path = REPO_ROOT / "docs/build/COVERAGE_MATRIX.csv"
    errors, stats = ccm.check(REPO_ROOT, csv_path)
    assert errors == [], errors[:20]
    assert stats["rows"] == stats["spec_ids"] > 0
    assert stats["evaluated"] == stats["rows"]
