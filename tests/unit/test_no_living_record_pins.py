# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""G6 living-record test lint — the `make check` driver (P34.31, SIG-ENG-040,
BM-TEST-01, OM-15, ADR-197).

No real-tree test may pin the current value of a living build record
(declared in docs/build/tools/record_policy/living_records.toml —
living-record-policy/1). docs/build/tools/living_record_lint.py evaluates
every test that reads a living path and fails on a pinned current-state
`key: value` literal, a named-record status assertion, a literal
`len(<living-derived>)` count, or a literal row-range/date inside an
assertion. The escape hatch — `@pytest.mark.living_record_invariant("<key>")`
for a registered [invariants.allowed] key — is exercised by this report; an
unregistered key fails here too. The tool's own fixture suite
(docs/build/tools/test_living_record_lint.py) proves each rule; this test
proves the real tree stays clean and the run is never vacuous."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from support import REPO_ROOT

_spec = importlib.util.spec_from_file_location(
    "living_record_lint", REPO_ROOT / "docs/build/tools/living_record_lint.py"
)
assert _spec and _spec.loader
lrl = importlib.util.module_from_spec(_spec)
sys.modules["living_record_lint"] = lrl
_spec.loader.exec_module(lrl)

REPORT = lrl.lint_tree(REPO_ROOT)


def test_policy_and_lint_exist() -> None:
    assert (REPO_ROOT / "docs/build/tools/record_policy/living_records.toml").is_file()
    assert (REPO_ROOT / "docs/build/tools/living_record_lint.py").is_file()
    assert REPORT["schema"] == "living-record-lint/1"


def test_evaluated_set_is_not_vacuous() -> None:
    """The lint is worthless if it evaluated nothing — require coverage."""
    assert REPORT["files_scanned"] > 0
    assert REPORT["tests_evaluated"] > 0
    assert len(REPORT["evaluated"]) + len(REPORT["exempted"]) >= REPORT[
        "tests_evaluated"
    ]


def test_no_living_record_pins() -> None:
    assert REPORT["violations"] == [], REPORT["violations"]


def test_registered_invariants_are_exercised() -> None:
    """Every exemption in the report names a key the policy registers — the
    escape hatch is itself linted (grep `living_record_invariant` to audit)."""
    allowed = lrl.load_policy(
        REPO_ROOT / "docs/build/tools/record_policy/living_records.toml"
    ).invariants
    for entry in REPORT["exempted"]:
        assert entry["invariant"] in allowed, entry
