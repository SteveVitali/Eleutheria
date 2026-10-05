# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P33.8 agent-docs refresh — guard the reconciled agent-guidance claims (SIG-MEM-004).

Pins the bounded public-island architecture (zero-JS binds public *content* pages;
the named islands `/curate/**` + `/map/`/`/network/`/`/search/` carry explicit
budgets — ADR-068 → ADR-097 → ADR-134) and the build-memory supersession chain
(ADR-073 → ADR-126/127), so a future edit cannot silently reintroduce the stale
"only `/curate/**`" wording or a universal zero-JS claim. Fails if the reconciled
wording is removed.

Living build-memory records (the coverage matrix, BUILD_INDEX and the build README's
row range) are asserted only through invariants that hold at every commit — never
their current values (BM-TEST-01; SEED-03 / PKG-02 ED-08). The LEDGER cursor that
P33.8's closeout recorded is no longer pinned here: its honesty (cursor resolves
against the manifest and the index, project status consistent with the cursor) is
enforced on the real tree by ``tests/unit/test_build_memory_audit.py``.
"""

import csv
import importlib.util
import json
import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO_ROOT / "docs" / "build" / "tools"

# A landed BUILD_INDEX row: a numeric seq first cell (an index-repair seq such as
# `170a` keeps its numeric part) followed by the ticket id.
_INDEX_ROW_RE = re.compile(r"^\|\s*(\d+)[a-z]?\s*\|\s*([A-Za-z][A-Za-z0-9.\-]*)")
_README_RANGE_RE = re.compile(r"rows 1[-–](\d+)")


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _landed_index_rows() -> dict[int, str]:
    """seq -> ticket id for every landed row of BUILD_INDEX.md."""
    rows: dict[int, str] = {}
    for line in _read("docs/build/BUILD_INDEX.md").splitlines():
        m = _INDEX_ROW_RE.match(line)
        if m:
            rows.setdefault(int(m.group(1)), m.group(2))
    return rows


def test_root_agents_zero_js_is_scoped_to_public_content_pages() -> None:
    root = _read("AGENTS.md")
    # The bounded-island state must be stated, not implied.
    assert "public content pages" in root or "public *content* pages" in root
    for island in ("/map/", "/network/", "/search/", "/curate/**"):
        assert island in root, f"public island {island} dropped from root guidance"
    for adr in ("ADR-068", "ADR-097", "ADR-134"):
        assert adr in root, f"governing ADR {adr} dropped from root guidance"
    # The stale absolute claim must not return.
    assert "the only exception" not in root
    assert "(Astro, static, zero-JS)" not in root


def test_web_agents_names_all_island_exceptions_and_node_floor() -> None:
    web = _read("web/AGENTS.md")
    assert "the only exception" not in web
    for island in ("/map/", "/network/", "/search/"):
        assert island in web, f"public island {island} dropped from web guidance"
    assert "ADR-097" in web and "ADR-134" in web and "ADR-068" in web
    # The toolchain ranges the guidance states are the ones web/package.json
    # declares (P27.9 raised the floor; P34.1 pins Node 24 + npm 11 as a range
    # `>=24 <25` / `>=11 <12`) — never a stale range.
    engines = json.loads(_read("web/package.json"))["engines"]
    declared = {engines["node"], engines["npm"]}
    stated = re.findall(r"`(>=\s*\d+(?:\.\d+)*(?:\s*<\s*\d+(?:\.\d+)*)?)`", web)
    assert engines["node"] in stated, (
        f"web/AGENTS.md does not state the engines.node range {engines['node']!r}"
    )
    assert all(s in declared for s in stated), (
        f"web/AGENTS.md states toolchain ranges {stated} but web/package.json declares {declared}"
    )


def test_build_memory_section_names_supersession_chain() -> None:
    root = _read("AGENTS.md")
    # SIG-MEM-004: guidance must name the governing ADR supersession chain and the
    # advisory projection surfaces without replacing the control authority.
    for token in ("ADR-073", "ADR-126", "ADR-127"):
        assert token in root, f"build-memory ADR {token} missing from root guidance"
    assert "obligation-event/1" in root and "coverage-assessment/1" in root
    assert "current-state projection" in root and "reports/current" in root or "CURRENT.md" in root
    # The projection is advisory — the LEDGER/DEFERRALS stay authoritative.
    assert "control" in root and "authorit" in root


@pytest.mark.living_record_invariant("coverage-row-uniqueness")
def test_coverage_matrix_sig_mem_004_row_is_well_formed() -> None:
    """SIG-MEM-004 keeps exactly one matrix row whose verdict is in the checker's
    own vocabulary. A MET-family verdict cites evidence that exists; any other
    verdict the checker treats as a gap is routed. The verdict itself is living —
    a later round may re-verdict it — so its value is not pinned (BM-TEST-01)."""
    checker = _load_tool("check_coverage_matrix")
    rows = [
        r
        for r in csv.DictReader(_read("docs/build/COVERAGE_MATRIX.csv").splitlines())
        if r["id"] == "SIG-MEM-004"
    ]
    assert len(rows) == 1, f"SIG-MEM-004 has {len(rows)} coverage-matrix rows"
    row = rows[0]
    verdict = row["verdict"]
    assert verdict in checker.VERDICTS, f"SIG-MEM-004 verdict {verdict!r} is off-vocabulary"
    owners = [t.strip() for t in row["owning_tickets"].split(";") if t.strip() not in ("", "—")]
    assert owners, "SIG-MEM-004 has no owning ticket"
    if verdict.startswith("MET"):
        refs = [r.strip() for r in row["evidence"].split(";") if r.strip()]
        assert refs, f"{verdict} verdict requires evidence"
        for ref in refs:
            path = ref.split("#", 1)[0].split(":", 1)[0]
            assert (REPO_ROOT / path).exists(), f"SIG-MEM-004 evidence {ref!r} does not exist"
    if verdict in checker.NON_MET_VERDICTS:
        assert row["routing"].strip() not in ("", "—"), f"{verdict} verdict must be routed"


def test_build_index_header_describes_the_full_chain() -> None:
    index = _read("docs/build/BUILD_INDEX.md")
    # The P32.1-routed stale-doc item: the header claimed "the 46-ticket chain" —
    # the file now indexes the full manifest chain; keep the historical capture
    # honest rather than rewriting it.
    assert "46-ticket chain" not in index.split("\n", 1)[0]
    # History, not living state: row 200 landed and the index is append-only.
    assert _landed_index_rows().get(200) == "P33.8"
    assert (REPO_ROOT / "docs/build/runs/P33.8.md").is_file()
    assert (REPO_ROOT / "docs/build/pr/P33.8.md").is_file()


def test_build_readme_index_range_matches_the_index() -> None:
    """docs/build/README.md states the BUILD_INDEX row range derived from the
    index itself (its highest landed seq, and that row's ticket when the README
    names one) — never a pinned number, so every closeout keeps them in step."""
    rows = _landed_index_rows()
    assert rows, "BUILD_INDEX.md parser found no landed rows — parser broke?"
    top = max(rows)
    readme = _read("docs/build/README.md")
    stated = {int(n) for n in _README_RANGE_RE.findall(readme)}
    assert stated, "docs/build/README.md no longer states the BUILD_INDEX row range"
    assert stated == {top}, (
        f"docs/build/README.md states rows 1-{sorted(stated)} but BUILD_INDEX's highest "
        f"landed row is {top} ({rows[top]})"
    )
    as_of = re.search(rf"rows 1[-–]{top} as of ([A-Za-z][A-Za-z0-9.\-]*[A-Za-z0-9])", readme)
    if as_of:
        assert as_of.group(1) == rows[top], (
            f"README names {as_of.group(1)} for row {top}, BUILD_INDEX names {rows[top]}"
        )
