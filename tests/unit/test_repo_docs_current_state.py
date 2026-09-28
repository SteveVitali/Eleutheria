# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P33.7 human-facing docs refresh — guard the current-state claims that were stale.

Pins the honest Round-10 posture the refresh landed (deployed + public, but the
provisional release is staging-only, intake non-operational, evaluation deferred)
so a future edit cannot silently reintroduce the pre-launch "nothing is deployed /
no live fetch" framing — or, conversely, overstate the staged candidate as served.
The refresh report itself is asserted to exist.
"""

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_refresh_report_exists() -> None:
    assert (REPO_ROOT / "docs/build/reports/DOCS_REFRESH_REPORT_R10.md").is_file()


def test_readme_states_deployed_public_surface() -> None:
    readme = _read("README.md")
    assert "surveillancegraph.org" in readme
    assert "staging" in readme.lower()
    for stale in (
        "not a running service",
        "nothing is deployed",
        "no source has been fetched live",
        "twelve fixture-tested connectors",
    ):
        assert stale not in readme, f"stale pre-launch claim reintroduced: {stale!r}"


def test_readme_round10_honest_bounds() -> None:
    readme = _read("README.md")
    # The staged-only posture and the non-operational intake must stay stated.
    assert "D-R10-PUBLISH-1" in readme
    assert "operational=false" in readme or "receiver_not_operating" in readme


def test_changelog_current_limitations_are_honest() -> None:
    changelog = _read("CHANGELOG.md")
    assert "no source has been fetched live" not in changelog
    assert "surveillancegraph.org" in changelog
    # The P22.3 relocation repaired: no live reference to the old pre-move path.
    assert "docs/build/PUBLICATION_CHECKLIST.md`" not in changelog
    assert "docs/build/FIRST_JURISDICTION_REPORT.md" not in changelog


def test_ops_readme_go_public_is_executed_not_deferred() -> None:
    ops = _read("ops/README.md")
    assert "are **not** ticked" not in ops
    assert "GO-PUBLIC EXECUTED" in ops or "executed" in ops
    assert "docs/build/FIRST_JURISDICTION_REPORT.md" not in ops
    assert "docs/build/reports/PUBLICATION_CHECKLIST.md" in ops


def test_web_readme_names_the_opt_in_islands() -> None:
    web = _read("web/README.md")
    for island in ("/map/", "/network/", "/search/"):
        assert island in web


def test_governance_readme_counts_all_documents() -> None:
    gov = _read("docs/governance/README.md")
    assert "Ten documents" in gov
    assert "intake-receiver-operating-packet.md" in gov
    assert "publication-opinion-drafts.md" in gov


def test_docs_index_lists_evaluation_packet() -> None:
    assert "evaluation/" in _read("docs/README.md")
