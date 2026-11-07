# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The unwired-function scan + its adjudicated ratchet (P37.5a, F2a §6.5).

Two halves: the scanner's mechanics over a synthetic tree, and the committed
baseline ratchet — the live scan over the ingestion stack must equal the
adjudicated set, in both directions. A NEW unwired public function fails loud
(wire it or adjudicate it in the same change — never silently); a RESOLVED
baseline row fails the same way (the baseline regenerates with the fix).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from connectors.unwired_scan import (
    Baseline,
    BaselineEntry,
    baseline_drift,
    load_baseline,
    render_json,
    scan,
)


def _tree(tmp_path: Path) -> Path:
    """A minimal two-package tree: one wired function, one test-only, one dead."""
    src = tmp_path / "pack" / "src" / "pack"
    (src / "sub").mkdir(parents=True)
    (src / "__init__.py").write_text("from .mod import used\n")
    (src / "mod.py").write_text(
        "def used():\n    return 1\n\n\ndef only_test():\n"
        "    return 2\n\n\ndef dead():\n    return 3\n"
    )
    (src / "sub" / "__init__.py").write_text("")
    (src / "sub" / "helper.py").write_text(
        "from pack.mod import used\n\n\ndef helper_used():\n    return used()\n"
    )
    consumer = tmp_path / "app" / "src" / "app"
    consumer.mkdir(parents=True)
    (consumer / "__init__.py").write_text("")
    # `used` is re-exported through pack/__init__ then called here.
    (consumer / "main.py").write_text(
        "from pack import used\nfrom pack.sub.helper import helper_used\n"
        "\nprint(used(), helper_used())\n"
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_mod.py").write_text(
        "from pack.mod import only_test\n\n\ndef test_it():\n    assert only_test() == 2\n"
    )
    return tmp_path


def test_scan_reports_only_test_callers(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    findings = scan(repo=root, packages=("pack",))
    keys = {f.candidate.key for f in findings}
    # `used` is wired through the __init__ re-export into app.main; `only_test`
    # has exactly one referer and it lives under tests/.
    assert keys == {"pack.mod.only_test", "pack.mod.dead"}
    only = next(f for f in findings if f.candidate.name == "only_test")
    assert only.prod_referers == ()
    assert only.test_referers == ("tests/test_mod.py",)


def test_defining_file_counts_as_wiring(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "pack" / "src" / "pack" / "mod.py").write_text(
        "def public_helper():\n    return 1\n\n\nclass Driver:\n"
        "    def go(self):\n        return public_helper()\n"
    )
    findings = scan(repo=root, packages=("pack",))
    keys = {f.candidate.key for f in findings}
    # The helper is reached through the module's own Driver — the cluster top
    # (Driver) reports, the helper under it does not.
    assert "pack.mod.public_helper" not in keys
    assert "pack.mod.Driver" in keys


def test_baseline_loads_committed_adjudication() -> None:
    baseline = load_baseline()
    assert baseline.entries, "the committed baseline must carry adjudicated rows"
    # Every row is adjudicated — no unadjudicated finding may be committed.
    for entry in baseline.entries:
        assert entry.disposition, entry.key


def test_baseline_rejects_a_bad_row(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text('[[finding]]\nkey = "x.y"\n')  # no disposition
    with pytest.raises(ValueError):
        load_baseline(bad)


def test_ratchet_live_scan_equals_committed_baseline() -> None:
    """THE ratchet (P37.5a): the live unwired set equals the adjudicated set.

    new      → a public function with only test callers appeared — wire it or
               adjudicate it (a [[finding]] row) in the same change.
    resolved → a baseline finding wired or deleted since — regenerate the
               baseline in the same change.
    """
    findings = scan()
    drift = baseline_drift(findings, load_baseline())
    assert drift["new"] == [], (
        "new unwired public function(s) with only test callers — adjudicate or wire"
    )
    assert drift["resolved"] == [], (
        "baseline finding(s) resolved — regenerate data/unwired_scan_baseline.toml"
    )


def test_report_shape_is_versioned() -> None:
    doc = render_json(scan(), load_baseline())
    parsed = ast.literal_eval("{}")  # noqa: F841 - parse check happens in json below
    import json

    body = json.loads(doc)
    rows = body["sig.unwired-scan/1"]["rows"]
    assert body["sig.unwired-scan/1"]["findings"] == len(rows)
    for row in rows:
        assert row["disposition"] != "unadjudicated", row["key"]


def test_drift_vocabulary() -> None:
    baseline = Baseline(entries=(BaselineEntry(key="a.b", disposition="x"),))
    from connectors.unwired_scan import Candidate, Finding

    cand = Candidate(module="a", name="c", kind="function", path="p", line=1)
    findings = [Finding(candidate=cand, prod_referers=(), test_referers=("t",))]
    drift = baseline_drift(findings, baseline)
    assert drift == {"new": ["a.c"], "resolved": ["a.b"], "unchanged": []}
