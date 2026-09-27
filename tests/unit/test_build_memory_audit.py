#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Adversarial fixtures for ``docs/build/tools/audit_current_state.py`` (P32.1, SIG-MEM-001).

The strict current-state parser must detect malformed/duplicate obligation ids,
OPEN-first/DONE-later status conflicts and legacy-filename forward dependencies
(the case the vendored seq-0 mapping misses), and it must never write or mutate
control state — including on error. These tests build minimal fixture trees in
``tmp_path`` and also pin the known real-tree conflicts so a regression that
stops detecting them fails loudly.
"""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import shutil

from support import REPO_ROOT

TOOLS = REPO_ROOT / "docs" / "build" / "tools"


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


audit_current_state = _load_tool("audit_current_state")

KEYS = """projectStatus: IN-PROGRESS
nextTicket: P9.1
lastCompleted: P00.2
blockedOn: —
pauseRequested: none
returnPass: none
manifest: docs/tickets/00_MANIFEST.md
canonicalSpec: docs/2_canonical_design_spec.md
memoryRoot: docs/build
dispatchTarget: —
buildWorktree: .
buildBranchBase: —
pinnedBaseSha: deadbeef
chainTip: devin/base
benchmarkSet: —
autonomy: checkpoint
mergePolicy: NONE
round: 9
updatedAt: 2026-01-01"""

MANIFEST = """# manifest

companions: _TEMPLATE.md

## The chain

| # | Ticket file | Phase | Scope |
|---|---|---|---|
| 1 | `P00.1__a.md` | 0 | a |
| 2 | `P00.2__b.md` | 0 | b |
| 3 | `161_P9.1__c.md` | 9 | c |
| 4 | `P00.9__later.md` | 0 | a legacy-named ticket inserted late |
"""

SPEC = "**SIG-TST-001 (MUST).** One requirement. See ADR-001.\n"
COVERAGE = (
    "id,level,spec_section,class,verdict,evidence,owning_tickets,tests,adrs,risk_rows,routing,note\n"
    "SIG-TST-001,MUST,§1,covered+tested,MET,t,P00.1,t,ADR-001,—,—,n\n"
)
DEFERRALS = """# deferrals

| id | desc | home | status |
|---|---|---|---|
| D-P9.1-1 | owed | BL-001 | OPEN pending P9.1 |
"""


def _tree(root: pathlib.Path, overrides: dict[str, str] | None = None) -> pathlib.Path:
    """Build a minimal, clean build-memory fixture tree; ``overrides`` replaces
    a file's contents (paths are repo-relative)."""
    files: dict[str, str] = {
        "docs/build/README.md": "<!-- build-memory: v2 -->\n",
        "docs/build/LEDGER.md": "## CURRENT STATE\n\n```\n"
        + KEYS
        + "\n```\n\n## PHASE LOG\n\n"
        + "- 2026-01-01 — P00.1 a done (PR #1)\n- 2026-01-02 — P00.2 b done (PR #2)\n",
        "docs/build/BUILD_INDEX.md": "| # | ticket | x | evidence |\n|---|---|---|---|\n"
        "| 1 | P00.1 | t | `runs/P00.1.md` |\n"
        "| 2 | P00.2 | t | `runs/P00.1.md` |\n",
        "docs/build/runs/P00.1.md": "# run\n",
        "docs/build/COVERAGE_MATRIX.csv": COVERAGE,
        "docs/tickets/00_MANIFEST.md": MANIFEST,
        "docs/tickets/_TEMPLATE.md": "# template\n",
        "docs/tickets/DEFERRALS.md": DEFERRALS,
        "docs/tickets/P00.1__a.md": "- **Depends on:** none\n",
        "docs/tickets/P00.2__b.md": "- **Depends on:** P00.1\n",
        "docs/tickets/161_P9.1__c.md": "- **Depends on:** P00.2\n",
        "docs/tickets/P00.9__later.md": "- **Depends on:** P00.2\n",
        "docs/2_canonical_design_spec.md": SPEC,
        "docs/adr/ADR-001-x.md": "# ADR-001\n\n## Revisit trigger\n\n- t\n",
        "docs/adr/README.md": "| [ADR-001](ADR-001-x.md) | t |\n",
    }
    files.update(overrides or {})
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def _checks(diags: list[dict]) -> set[str]:
    return {d["check"] for d in diags}


def _by_check(diags: list[dict], check: str) -> list[dict]:
    return [d for d in diags if d["check"] == check]


def test_clean_fixture_reports_nothing(tmp_path: pathlib.Path) -> None:
    diags, meta = audit_current_state.audit(_tree(tmp_path))
    assert diags == [], diags
    assert meta["schema"] == "build-memory-audit/1"


def test_malformed_deferral_ids_detected(tmp_path: pathlib.Path) -> None:
    bad = DEFERRALS + (
        "| D-P9..1-1 | double dot | BL-001 | OPEN |\n"
        "| d-p9.1-2 | lowercase | BL-001 | OPEN |\n"
        "| D- | bare | BL-001 | OPEN |\n"
    )
    diags, _ = audit_current_state.audit(_tree(tmp_path, {"docs/tickets/DEFERRALS.md": bad}))
    flagged = {d["obligation"] for d in _by_check(diags, "deferrals/malformed-id")}
    assert flagged == {"D-P9..1-1", "d-p9.1-2", "D-"}, flagged


def test_duplicate_deferral_id_detected(tmp_path: pathlib.Path) -> None:
    dup = DEFERRALS + "| D-P9.1-1 | again | BL-002 | OPEN second row |\n"
    diags, _ = audit_current_state.audit(_tree(tmp_path, {"docs/tickets/DEFERRALS.md": dup}))
    hits = _by_check(diags, "deferrals/duplicate-id")
    assert [d["obligation"] for d in hits] == ["D-P9.1-1"]
    assert hits[0]["severity"] == "error"


def test_owed_leading_status_then_dated_terminal_is_conflict(tmp_path: pathlib.Path) -> None:
    conflict = (
        DEFERRALS + "| D-P9.1-2 | swept | BL-001 | OPEN pending P9.1 — later prose says "
        "DONE 2026-09-10 at P9.1 yet leads OPEN |\n"
    )
    diags, _ = audit_current_state.audit(_tree(tmp_path, {"docs/tickets/DEFERRALS.md": conflict}))
    hits = _by_check(diags, "deferrals/status-conflict")
    assert [d["obligation"] for d in hits] == ["D-P9.1-2"]
    assert hits[0]["severity"] == "conflict"


def test_legacy_filename_forward_dependency_detected(tmp_path: pathlib.Path) -> None:
    """P9.1 (chain position 3) depends on `P00.9__later.md`, a legacy-named file
    at chain position 4. A naive seq-0 mapping misses this forward dep; manifest
    order catches it."""
    deps = _tree(tmp_path, {"docs/tickets/161_P9.1__c.md": "- **Depends on:** P00.9\n"})
    diags, _ = audit_current_state.audit(deps)
    hits = _by_check(diags, "tickets/forward-dependency")
    assert len(hits) == 1
    assert hits[0]["obligation"] == "P00.9"
    assert hits[0]["severity"] == "error"


def test_dependency_not_in_chain_is_conflict_not_crash(tmp_path: pathlib.Path) -> None:
    deps = _tree(tmp_path, {"docs/tickets/161_P9.1__c.md": "- **Depends on:** P99.9\n"})
    diags, _ = audit_current_state.audit(deps)
    hits = _by_check(diags, "tickets/dependency-not-in-chain")
    assert [d["obligation"] for d in hits] == ["P99.9"]
    assert all(d["severity"] == "conflict" for d in hits)


def test_manifest_duplicate_file_is_conflict(tmp_path: pathlib.Path) -> None:
    dup_manifest = MANIFEST + "| 5 | `P00.2__b.md` | 21 | a Lane-B pointer row |\n"
    diags, _ = audit_current_state.audit(
        _tree(tmp_path, {"docs/tickets/00_MANIFEST.md": dup_manifest})
    )
    hits = _by_check(diags, "manifest/duplicate-file")
    assert [d["obligation"] for d in hits] == ["P00.2__b.md"]
    assert all(d["severity"] == "conflict" for d in hits)


def test_owed_row_without_backlog_home_is_error(tmp_path: pathlib.Path) -> None:
    homeless = DEFERRALS + "| D-P9.1-3 | no home | — | OPEN |\n"
    diags, _ = audit_current_state.audit(_tree(tmp_path, {"docs/tickets/DEFERRALS.md": homeless}))
    assert [d["obligation"] for d in _by_check(diags, "deferrals/no-backlog-home")] == ["D-P9.1-3"]


def test_coverage_nonmet_without_routing_is_error(tmp_path: pathlib.Path) -> None:
    bad_cov = COVERAGE + "SIG-TST-002,MUST,§1,unreferenced,PARTIAL,,P9.1,,,—,—,n\n"
    spec = SPEC + "**SIG-TST-002 (MUST).** Second.\n"
    diags, _ = audit_current_state.audit(
        _tree(
            tmp_path,
            {
                "docs/build/COVERAGE_MATRIX.csv": bad_cov,
                "docs/2_canonical_design_spec.md": spec,
            },
        )
    )
    assert "coverage/nonmet-unrouted" in _checks(diags)


def test_ledger_index_ahead_and_next_landed(tmp_path: pathlib.Path) -> None:
    index = (
        "| # | ticket | x | evidence |\n|---|---|---|---|\n"
        "| 1 | P00.1 | t | `runs/P00.1.md` |\n"
        "| 2 | P00.2 | t | `runs/P00.1.md` |\n"
        "| 3 | P9.1 | t | `runs/P00.1.md` |\n"
    )
    diags, _ = audit_current_state.audit(_tree(tmp_path, {"docs/build/BUILD_INDEX.md": index}))
    checks = _checks(diags)
    assert "ledger/index-ahead" in checks
    assert "ledger/next-landed" in checks


def test_done_entry_without_evidence_is_error(tmp_path: pathlib.Path) -> None:
    index = (
        "| # | ticket | x | evidence |\n|---|---|---|---|\n| 1 | P00.1 | t | `runs/P00.1.md` |\n"
    )
    diags, _ = audit_current_state.audit(_tree(tmp_path, {"docs/build/BUILD_INDEX.md": index}))
    hits = _by_check(diags, "ledger/done-uncovered")
    assert [d["obligation"] for d in hits] == ["P00.2"]


def test_marker_ticket_evidence_via_readout_is_accepted(tmp_path: pathlib.Path) -> None:
    """A gate marker done-row whose evidence is a readout (not runs/pr) is covered."""
    (tmp_path / "docs/build/readouts").mkdir(parents=True)
    (tmp_path / "docs/build/readouts/GATE-ACCEPT.md").write_text("verdict PASSED\n")
    index = (
        "| # | ticket | x | evidence |\n|---|---|---|---|\n"
        "| 1 | P00.1 | t | `runs/P00.1.md` |\n"
        "| 2 | P00.2 | t | `runs/P00.1.md` |\n"
        "| 3 | GATE-ACCEPT | t | `readouts/GATE-ACCEPT.md` |\n"
    )
    ledger = (
        "## CURRENT STATE\n\n```\n"
        + KEYS.replace("nextTicket: P9.1", "nextTicket: DONE").replace(
            "lastCompleted: P00.2", "lastCompleted: GATE-ACCEPT"
        )
        + "\n```\n\n## PHASE LOG\n\n"
        "- 2026-01-03 — GATE-ACCEPT marker done\n"
    )
    manifest = MANIFEST + "| 5 | `195_GATE-ACCEPT__gate.md` | 9 | gate |\n"
    diags, _ = audit_current_state.audit(
        _tree(
            tmp_path,
            {
                "docs/build/BUILD_INDEX.md": index,
                "docs/build/LEDGER.md": ledger,
                "docs/tickets/00_MANIFEST.md": manifest,
                "docs/tickets/195_GATE-ACCEPT__gate.md": "- **Depends on:** P9.1\n",
            },
        )
    )
    assert "ledger/done-uncovered" not in _checks(diags), diags


def test_adr_index_mismatch_and_missing_revisit(tmp_path: pathlib.Path) -> None:
    diags, _ = audit_current_state.audit(
        _tree(
            tmp_path,
            {
                "docs/2_canonical_design_spec.md": SPEC + " ADR-002.\n",
                "docs/adr/ADR-002-y.md": "# ADR-002\n",
            },
        )
    )
    checks = _checks(diags)
    assert "adr/missing-revisit" in checks
    assert "adr/index-mismatch" in checks


def _digests(root: pathlib.Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_audit_never_mutates_inputs_even_on_errors(tmp_path: pathlib.Path) -> None:
    """Read-only means read-only: every byte of the fixture tree is identical
    after the audit, including when diagnostics fire."""
    broken = DEFERRALS + "| D-P9..9-9 | malformed | BL-001 | OPEN |\n"
    root = _tree(tmp_path, {"docs/tickets/DEFERRALS.md": broken})
    before = _digests(root)
    diags, _ = audit_current_state.audit(root)
    assert diags  # the audit actually fired
    after = _digests(root)
    assert before == after


def test_no_marker_returns_usage_error(tmp_path: pathlib.Path) -> None:
    assert audit_current_state.main(["--root", str(tmp_path)]) == 2


def test_reports_go_to_caller_provided_paths(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path / "repo")
    out = tmp_path / "out"
    rc = audit_current_state.main(
        [
            "--root",
            str(root),
            "--json-out",
            str(out / "discrepancies.json"),
            "--md-out",
            str(out / "discrepancies.md"),
        ]
    )
    assert rc == 0
    assert (out / "discrepancies.json").is_file()
    assert (out / "discrepancies.md").is_file()
    # no report was written into the tree itself
    assert not (root / "discrepancies.json").exists()


def test_real_tree_expected_conflicts_and_zero_errors() -> None:
    """The real tree after P32.7's recorded reconciliations: the parser must
    still surface `D-P21.5-1` (the one conflict row whose recorded
    interpretation is PARTIAL — the dated DONE tokens stay deliberately
    visible), the documented Lane-B pointer rows, and P31.17/18 named as
    dropped/moved in P31.19's depends line — and zero errors. The six other
    former conflict rows were reconciled by obligation-event anchors and their
    compatibility cells flipped to match (P32.7/ADR-126)."""
    diags, meta = audit_current_state.audit(REPO_ROOT)
    errors = [d for d in diags if d["severity"] == "error"]
    assert errors == [], errors
    flagged = {d["obligation"] for d in _by_check(diags, "deferrals/status-conflict")}
    assert flagged == {"D-P21.5-1"}, flagged
    deps = {d["obligation"] for d in _by_check(diags, "tickets/dependency-not-in-chain")}
    assert {"P31.17", "P31.18"} <= deps
    dupes = {d["obligation"] for d in _by_check(diags, "manifest/duplicate-file")}
    assert "P21.1__rights-review-and-registry-completion.md" in dupes
    # input hashes are recorded so a stale report cannot masquerade as fresh
    for rel in (
        "docs/tickets/00_MANIFEST.md",
        "docs/tickets/DEFERRALS.md",
        "docs/build/LEDGER.md",
        "docs/build/COVERAGE_MATRIX.csv",
        "docs/2_canonical_design_spec.md",
    ):
        assert len(meta["input_digests"].get(rel, "")) == 64


def test_no_existing_gate_or_deferral_is_closed_by_parsing() -> None:
    """Parsing preserves every obligation: the Round-10 prerequisite rows stay
    OPEN, and the audit does not rewrite any status cell. (D-P31.1-1,
    D-P31.1-3 and D-P31.5-2 are DONE — not by parsing: P32.7 recorded
    evidence-backed reconciliation events for them and updated the
    compatibility cells to match, the old values preserved on the anchors.)"""
    diags, _ = audit_current_state.audit(REPO_ROOT)  # noqa: F841 — audit must not raise
    obligations = audit_current_state.parse_deferrals(REPO_ROOT, [])
    by_id = {o["id"]: o["status"] for o in obligations}
    for owed in (
        "D-P31.4-1",
        "D-R10-HUMAN-1",
        "D-R10-SOURCES-1",
        "D-R10-LIVE-1",
        "D-R10-PUBLISH-1",
        "D-R10-MEMORY-1",
        "D-R6.1-EVAL",
    ):
        assert by_id[owed] in {"OPEN", "PARTIAL"}, (owed, by_id.get(owed))


def test_tool_is_removed_behavior_fails(tmp_path: pathlib.Path) -> None:
    """Sanity: if the deferrals parser is removed, the owed-status fixture test
    above has nothing to detect (keeps the suite honest)."""
    root = _tree(tmp_path)
    diags, _ = audit_current_state.audit(root)
    assert not _by_check(diags, "deferrals/status-conflict")
    (root / "docs/tickets/DEFERRALS.md").write_text(
        DEFERRALS + "| D-P9.1-9 | x | BL-001 | OPEN then DONE 2026-09-10 |\n"
    )
    diags, _ = audit_current_state.audit(root)
    assert _by_check(diags, "deferrals/status-conflict")


def test_output_files_are_not_shared(tmp_path: pathlib.Path) -> None:
    """Two trees audited concurrently write distinct caller-named reports; the
    tool itself never falls back to a shared path like /tmp/build-memory-check.json."""
    a = _tree(tmp_path / "a")
    b = _tree(tmp_path / "b")
    shutil.copytree(a / "docs", b / "docs", dirs_exist_ok=True)
    ra = audit_current_state.main(["--root", str(a), "--json-out", str(tmp_path / "ra.json")])
    rb = audit_current_state.main(["--root", str(b), "--json-out", str(tmp_path / "rb.json")])
    assert (ra, rb) == (0, 0)
    assert not pathlib.Path("/tmp/build-memory-audit.json").exists()
