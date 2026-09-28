# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Round-10 integration plan (P33.6) — the committed operator procedure artifact.

Asserts the plan exists, keeps the no-merge boundary explicit, names every open
PR of the inspected stack exactly once in ascending merge order, records the
real conflict steps found by the read-only inspection, carries the owed
obligations register forward, and provides the required sections (procedure,
verification cadence, rollback, reproduction). The artifact is a dated snapshot
of the open-PR set at inspection time — the numbers pinned here are that set
(#112–#187, minus the already-merged #148).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md"
PRIOR_PLAN = REPO / "docs/build/INTEGRATION_PLAN.md"

# The open-PR set the plan inspected (PR #148 is MERGED; #112–#187 were OPEN).
EXPECTED_OPEN_PRS = [n for n in range(112, 188) if n != 148]


def _plan_text() -> str:
    assert PLAN.exists(), f"missing integration plan artifact: {PLAN}"
    return PLAN.read_text()


def _merge_order_prs(text: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(r"^\| #(\d+) \| `", text, re.M)]


def test_plan_exists_with_license_header() -> None:
    text = _plan_text()
    assert text.startswith("<!-- SPDX-License-Identifier: CC-BY-4.0 -->")


def test_every_open_pr_named_once_in_ascending_merge_order() -> None:
    rows = _merge_order_prs(_plan_text())
    assert rows == EXPECTED_OPEN_PRS, "inventory must list every open PR exactly once, ascending"
    assert rows == sorted(rows)


def test_no_merge_boundary_is_explicit() -> None:
    text = _plan_text()
    assert "merges nothing" in text
    assert "does not touch `main`" in text
    for forbidden_ran in ("git merge origin/main",):
        assert forbidden_ran not in text


def test_fork_point_and_main_divergence_recorded() -> None:
    text = _plan_text()
    assert "5b7fed0e63b6e9d5ff8848e8e3bcbd3b536e891c" in text  # fork commit
    assert "3b913c6ff147a1fa63d3356be87d5fc9446b4455" in text  # origin/main
    assert "NOT diverged" in text  # tree-equality invariant over the fork point


def test_real_conflict_steps_named() -> None:
    text = _plan_text()
    for pr in ("#113", "#117", "#155"):
        assert pr in text
    assert "docs/tickets/DEFERRALS.md" in text
    assert "web/package-lock.json" in text
    assert "@types/node" in text
    assert "checkout --theirs" in text  # the prescribed resolution


def test_shared_file_order_dependencies_explained() -> None:
    text = _plan_text()
    for f in ("db/sqitch.plan", "docs/build/LEDGER.md", "docs/build/BUILD_INDEX.md"):
        assert f in text


def test_required_sections_present() -> None:
    text = _plan_text()
    for section in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)", "(h)", "(i)"):
        assert f"## {section}" in text
    # (e) retarget+merge loop, (f) revert rollback, (h) post-merge gate
    assert "gh pr edit" in text and "--base main" in text
    assert "gh pr merge" in text and "--delete-branch=false" in text
    assert "git revert -m 1" in text
    assert "SIG_REQUIRE_DB_TESTS=1" in text


def test_owed_obligations_carried_forward() -> None:
    text = _plan_text()
    for deferral in (
        "D-R10-HUMAN-1",
        "D-R6.1-EVAL",
        "D-R10-LIVE-1",
        "D-P32.23a-1",
        "D-R10-PUBLISH-1",
        "D-R10-MEMORY-1",
        "D-R10-USERS-1",
        "D-R10-SOURCES-1",
        "D-P32.3-1",
        "D-P32.10a-1",
        "D-P32.16-1",
        "D-P32.16a-1",
        "SIG-MEM-004",
    ):
        assert deferral in text, f"plan must carry forward {deferral}"


def test_prior_plan_points_at_current_plan() -> None:
    text = PRIOR_PLAN.read_text()
    assert "reports/p33.6-integration-plan/INTEGRATION_PLAN.md" in text
    assert "Superseded for the current stack" in text
