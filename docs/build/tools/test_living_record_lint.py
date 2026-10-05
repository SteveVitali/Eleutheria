# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""living_record_lint — the G6 AST lint against fixture sources (P34.31,
SIG-ENG-040). Each fixture is a synthetic test module linted in isolation; the
real-tree report is exercised by tests/unit/test_no_living_record_pins.py."""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "docs/build/tools/record_policy/living_records.toml"

_spec = importlib.util.spec_from_file_location(
    "living_record_lint", REPO_ROOT / "docs/build/tools/living_record_lint.py"
)
assert _spec and _spec.loader
lrl = importlib.util.module_from_spec(_spec)
sys.modules["living_record_lint"] = lrl  # dataclass resolution
_spec.loader.exec_module(lrl)

POLICY = lrl.load_policy(POLICY_PATH)

PRELUDE = textwrap.dedent(
    """
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[2]
    LEDGER = REPO_ROOT / "docs" / "build" / "LEDGER.md"
    DEFERRALS = REPO_ROOT / "docs" / "tickets" / "DEFERRALS.md"
    README = REPO_ROOT / "docs" / "build" / "README.md"
    FROZEN = REPO_ROOT / "docs" / "build" / "planning" / "day" / "PLAN.json"


    def _read(rel: str) -> str:
        return (REPO_ROOT / rel).read_text(encoding="utf-8")


    def _rows(path: str):
        return [l.split("|") for l in _read(path).splitlines() if l.startswith("| D-")]
    """
)


def analyze(source: str, rel: str = "tests/unit/test_fixture.py"):
    az = lrl.Analyzer(POLICY, rel, PRELUDE + "\n" + textwrap.dedent(source), REPO_ROOT)
    return az


def evaluated(source: str):
    az = analyze(source)
    out = {}
    for name, fn in az.fns.items():
        if name.startswith("test"):
            reads = az.reads_in_subtree(fn)
            living = [r for r in reads if r[1] == "tree" and POLICY.classify(r[0]) == "living"]
            snaps = [r for r in reads if r[1] == "snapshot"]
            if living or snaps:
                out[name] = {
                    "reads": reads,
                    "living": living,
                    "viols": az.evaluate(fn) if living else [],
                    "key": az.invariant_key(fn),
                }
    return out


def test_policy_loads_and_classifies() -> None:
    assert POLICY.classify("docs/build/LEDGER.md") == "living"
    assert POLICY.classify("docs/build/reports/current/CURRENT.md") == "living"
    # living wins over the frozen reports/* umbrella
    assert POLICY.classify("docs/build/reports/LEDGER_DEFERRALS.md") == "living"
    assert POLICY.classify("docs/build/reports/x/y.md") == "frozen"
    assert POLICY.classify("docs/build/CAPSTONE_CLOSURE.md") == "frozen"
    assert POLICY.classify("src/pkg/module.py") is None


def test_rule1_current_state_literal_is_flagged() -> None:
    out = evaluated(
        """
        def test_pin(tmp_path):
            text = LEDGER.read_text()
            assert "nextTicket: P9.9" in text
        """
    )
    assert "test_pin" in out
    assert any(v["rule"] == "rule-1" for v in out["test_pin"]["viols"])


def test_rule2_named_id_status_pair_is_flagged() -> None:
    out = evaluated(
        """
        def test_pin():
            rows = _rows("docs/tickets/DEFERRALS.md")
            row = next(r for r in rows if "D-X-1" in r[0])
            assert row[2].strip() == "OPEN"
        """
    )
    assert "test_pin" in out
    assert any(v["rule"] == "rule-2" for v in out["test_pin"]["viols"])


def test_rule2_derived_equality_to_record_id_is_flagged() -> None:
    out = evaluated(
        """
        def test_pin():
            rows = _rows("docs/tickets/DEFERRALS.md")
            assert rows[0][0].strip() == "D-X-1"
        """
    )
    assert "test_pin" in out
    assert any(v["rule"] == "rule-2" for v in out["test_pin"]["viols"])


def test_rule3_literal_count_is_flagged() -> None:
    out = evaluated(
        """
        def test_pin():
            rows = _rows("docs/tickets/DEFERRALS.md")
            assert len(rows) == 18
        """
    )
    assert "test_pin" in out
    assert any(v["rule"] == "rule-3" for v in out["test_pin"]["viols"])


def test_rule4_row_range_and_date_literals_are_flagged() -> None:
    out = evaluated(
        """
        def test_pin():
            readme = README.read_text()
            assert "rows 1-235" in readme

        def test_pin2():
            readme = README.read_text()
            assert "2026-10-05" in readme
        """
    )
    for t in ("test_pin", "test_pin2"):
        assert t in out
        assert any(v["rule"] == "rule-4" for v in out[t]["viols"]), t


def test_allowed_invariant_forms_pass() -> None:
    out = evaluated(
        """
        STATUSES = {"OPEN", "PARTIAL", "DONE"}

        def test_vocab():
            rows = _rows("docs/tickets/DEFERRALS.md")
            for r in rows:
                status = r[2].strip()
                assert status in STATUSES, status

        def test_unique():
            rows = _rows("docs/tickets/DEFERRALS.md")
            ids = [r[0] for r in rows]
            assert len(ids) == len(set(ids))

        def test_generated():
            expected = _read("docs/build/BACKLOG.md")
            rendered = _read("docs/build/BACKLOG.md")
            assert expected == rendered

        def test_conditional_status():
            text = DEFERRALS.read_text()
            for line in text.splitlines():
                if line.startswith("| D-"):
                    if "OPEN" in line:
                        assert "owed" in line or True
        """
    )
    for name, rep in out.items():
        assert rep["viols"] == [], (name, rep["viols"])


def test_frozen_artifact_facts_pass() -> None:
    out = evaluated(
        """
        def test_frozen():
            import json
            plan = json.loads(FROZEN.read_text())
            assert len(plan["requirements"]) == 38
            assert plan["closed"] == "2026-10-01"
        """
    )
    # frozen reads alone do not evaluate the test at all
    assert out == {}


def test_frozen_plus_living_file_may_still_assert_frozen_facts() -> None:
    out = evaluated(
        """
        def test_mix():
            text = DEFERRALS.read_text()
            plan_lines = FROZEN.read_text().splitlines()
            assert len(plan_lines) > 0
            assert text
        """
    )
    assert out["test_mix"]["viols"] == []


def test_registered_invariant_mark_exempts() -> None:
    out = evaluated(
        """
        import pytest

        @pytest.mark.living_record_invariant("coverage-row-uniqueness")
        def test_marked():
            rows = _rows("docs/tickets/DEFERRALS.md")
            assert len(rows) == 18
        """
    )
    rep = out["test_marked"]
    assert rep["key"] == "coverage-row-uniqueness"
    assert rep["key"] in POLICY.invariants
    assert rep["viols"]  # the rule still fires — the mark is what exempts it


def test_unregistered_invariant_mark_is_reported() -> None:
    az = analyze(
        """
        import pytest

        @pytest.mark.living_record_invariant("made-up-key")
        def test_marked():
            text = DEFERRALS.read_text()
            assert text
        """
    )
    fn = az.fns["test_marked"]
    key = az.invariant_key(fn)
    assert key == "made-up-key"
    assert key not in POLICY.invariants  # lint_tree reports unregistered-invariant


def test_tmp_path_reads_are_never_evaluated() -> None:
    out = evaluated(
        """
        def test_fixture(tmp_path):
            led = tmp_path / "docs" / "build" / "LEDGER.md"
            led.parent.mkdir(parents=True)
            led.write_text("nextTicket: P9.9")
            assert "nextTicket: P9.9" in led.read_text()
            assert len(led.read_text().splitlines()) == 1
        """
    )
    assert out == {}


def test_snapshot_channel_is_allowed_and_counted() -> None:
    out = evaluated(
        """
        import subprocess
        SHA = "e8bc0179720e6b52498d0db63df7b46c357c226f"

        def test_snapshot():
            snap = subprocess.run(
                ["git", "show", f"{SHA}:docs/tickets/DEFERRALS.md"],
                capture_output=True, text=True, check=True,
            ).stdout
            assert "nextTicket: P9.9" in snap  # a snapshot is frozen — allowed
        """
    )
    assert "test_snapshot" in out
    rep = out["test_snapshot"]
    assert rep["living"] == []
    assert any(r[1] == "snapshot" for r in rep["reads"])
    assert rep["viols"] == []


def test_validator_channel_is_not_a_direct_living_read() -> None:
    out = evaluated(
        """
        import audit_current_state

        def test_validator():
            diags, meta = audit_current_state.audit(REPO_ROOT)
            assert diags == []
            assert meta["schema"] == "audit-report/1"
        """
    )
    assert out == {}


def test_bare_row_presence_is_reference_resolution_not_a_pin() -> None:
    out = evaluated(
        """
        def test_ref():
            text = DEFERRALS.read_text()
            assert "D-X-1" in text
            assert "D-X-2" in text
        """
    )
    assert out["test_ref"]["viols"] == []


def test_real_tree_report_counts() -> None:
    report = lrl.lint_tree(REPO_ROOT)
    assert report["schema"] == "living-record-lint/1"
    assert report["files_scanned"] > 0
    assert report["tests_evaluated"] > 0
    assert report["violations"] == []
