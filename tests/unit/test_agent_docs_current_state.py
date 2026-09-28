# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P33.8 agent-docs refresh — guard the reconciled agent-guidance claims (SIG-MEM-004).

Pins the bounded public-island architecture (zero-JS binds public *content* pages;
the named islands `/curate/**` + `/map/`/`/network/`/`/search/` carry explicit
budgets — ADR-068 → ADR-097 → ADR-134), the build-memory supersession chain
(ADR-073 → ADR-126/127), and the honest memory-chain closeout state — so a future
edit cannot silently reintroduce the stale "only `/curate/**`" wording or a
universal zero-JS claim. Fails if the reconciled wording is removed.
"""

import csv
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


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
    # The island toolchain pins node >=22.12.0 (P27.9) — not >=20.
    assert ">=22.12.0" in web


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


def test_coverage_matrix_marks_sig_mem_004_met() -> None:
    rows = list(csv.DictReader(_read("docs/build/COVERAGE_MATRIX.csv").splitlines()))
    row = next(r for r in rows if r["id"] == "SIG-MEM-004")
    assert row["verdict"] == "MET", row["verdict"]
    assert row["evidence"].strip(), "MET verdict requires evidence"


def test_build_index_header_describes_the_full_chain() -> None:
    index = _read("docs/build/BUILD_INDEX.md")
    # The P32.1-routed stale-doc item: the header claimed "the 46-ticket chain" —
    # the file now indexes the full manifest chain; keep the historical capture
    # honest rather than rewriting it.
    assert "46-ticket chain" not in index.split("\n", 1)[0]
    assert "P33.8" in index  # row 200 landed
    assert (REPO_ROOT / "docs/build/runs/P33.8.md").is_file()
    assert (REPO_ROOT / "docs/build/pr/P33.8.md").is_file()


def test_build_readme_index_range_is_current() -> None:
    readme = _read("docs/build/README.md")
    assert "rows 1-200" in readme
    assert "rows 1-199" not in readme


def test_ledger_closed_the_manifest_honestly() -> None:
    ledger = _read("docs/build/LEDGER.md")
    assert "lastCompleted: P33.8" in ledger
    # Manifest exhausted but the deferred S3 spine re-enters at row 184 — the next
    # row names it and the project stays IN-PROGRESS while obligations remain.
    assert "nextTicket: HUMAN-H4" in ledger
    assert "projectStatus: IN-PROGRESS" in ledger
