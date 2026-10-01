#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Adversarial fixtures for ``docs/build/tools/audit_current_state.py`` (P32.1, SIG-MEM-001).

The strict current-state parser must detect malformed/duplicate obligation ids,
OPEN-first/DONE-later status conflicts and legacy-filename forward dependencies
(the case the vendored seq-0 mapping misses), and it must never write or mutate
control state — including on error. These tests build minimal fixture trees in
``tmp_path`` (including the Round-11 values-only CURRENT STATE shape) and run the
audit over the real tree, where they assert only invariants that hold at every
commit: zero errors, a LEDGER cursor consistent with the manifest and the index,
every status conflict documented by a recorded reconciliation, and parsing that
never changes a row's own leading status (BM-TEST-01; SEED-03 / PKG-02 ED-10).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import shutil

import pytest
from support import REPO_ROOT

TOOLS = REPO_ROOT / "docs" / "build" / "tools"


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


audit_current_state = _load_tool("audit_current_state")
obligation_events = _load_tool("obligation_events")

KEYS = """projectStatus: IN_PROGRESS
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
MANIFEST_R11 = MANIFEST + "\n### Round 11 — wave 1\n\n| 5 | `201_P10.1__d.md` | 10 | d |\n"

SPEC = "**SIG-TST-001 (MUST).** One requirement. See ADR-001.\n"
COVERAGE = (
    "id,level,spec_section,class,verdict,evidence,owning_tickets,tests,adrs,risk_rows,routing,note\n"
    "SIG-TST-001,MUST,§1,covered+tested,MET,t,P00.1,t,ADR-001,—,—,n\n"
)

# The Round-11 seed shape of CURRENT STATE (B3 §3.4; skill 0.5.0 layout
# BM-LEDGER-02/-08): values only, `harness` in its optional slot between `round`
# and `updatedAt`, `projectStatus: PAUSED`, the next row a newly appended one,
# and the archive pointer comment inside the section.
KEYS_R11 = """projectStatus: PAUSED
nextTicket: P10.1
lastCompleted: P00.2
blockedOn: (nothing)
pauseRequested: true
returnPass: (none)
manifest: docs/tickets/00_MANIFEST.md
canonicalSpec: docs/2_canonical_design_spec.md
memoryRoot: docs/build
dispatchTarget: subagent
buildWorktree: .
buildBranchBase: devin/base
pinnedBaseSha: deadbeef
chainTip: r11/seed
benchmarkSet: N/A
autonomy: checkpoint
mergePolicy: NONE
round: 11
harness: devin-desktop/swe-2-high/subagent
updatedAt: 2026-01-03T00:00:00Z"""
LEDGER_R11 = (
    "# ledger\n\n## CURRENT STATE\n\n```\n"
    + KEYS_R11
    + "\n```\n<!-- Rounds 1-10 head archived; sha256 pointer. -->\n\n"
    + "## PHASE LOG — Round 9\n\n"
    + "- 2026-01-01 — P00.1 a done (PR #1)\n- 2026-01-02 — P00.2 b done (PR #2)\n"
    + "\n## PHASE LOG — Round 11\n\n- 2026-01-03 — SEED-10 repair — head archived\n"
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


def _r11_tree(root: pathlib.Path, ledger: str = LEDGER_R11) -> pathlib.Path:
    return _tree(
        root,
        {
            "docs/build/LEDGER.md": ledger,
            "docs/tickets/00_MANIFEST.md": MANIFEST_R11,
            "docs/tickets/201_P10.1__d.md": "- **Depends on:** P00.2\n",
        },
    )


def test_round11_values_only_cursor_resolves(tmp_path: pathlib.Path) -> None:
    """The seed's values-only CURRENT STATE (PAUSED, the next row a newly
    appended Round-11 row, an archive pointer comment, PHASE LOG regions per
    round) parses: the cursor checks resolve it without a finding."""
    diags, _ = audit_current_state.audit(_r11_tree(tmp_path))
    checks = _checks(diags)
    for check in (
        "ledger/next-ticket",
        "ledger/last-completed",
        "ledger/next-landed",
        "ledger/index-ahead",
        "ledger/done-uncovered",
    ):
        assert check not in checks, [d for d in diags if d["check"] == check]


def test_round11_cursor_naming_no_chain_row_is_error(tmp_path: pathlib.Path) -> None:
    ledger = LEDGER_R11.replace("nextTicket: P10.1", "nextTicket: P99.9")
    diags, _ = audit_current_state.audit(_r11_tree(tmp_path, ledger))
    assert [d["obligation"] for d in _by_check(diags, "ledger/next-ticket")] == ["P99.9"]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "audit_current_state.EXPECTED_KEYS has no slot for the optional `harness` key "
        "(layout BM-LEDGER-02, build-memory skill 0.5.0) — the Round-11 seed LEDGER "
        "would raise ledger/key-order; fixing the tool turns this XPASS: drop the marker "
        "with that fix (SEED-03 report)"
    ),
)
def test_round11_harness_slot_passes_key_order(tmp_path: pathlib.Path) -> None:
    diags, _ = audit_current_state.audit(_r11_tree(tmp_path))
    assert "ledger/key-order" not in _checks(diags)


def test_round11_harness_out_of_its_slot_is_a_key_order_error(tmp_path: pathlib.Path) -> None:
    """`harness` is optional but only in its slot — after `updatedAt` it is an
    error today and must stay one once the slot is accepted."""
    moved = LEDGER_R11.replace("harness: devin-desktop/swe-2-high/subagent\n", "").replace(
        "updatedAt: 2026-01-03T00:00:00Z", "updatedAt: 2026-01-03T00:00:00Z\nharness: x/y/z"
    )
    diags, _ = audit_current_state.audit(_r11_tree(tmp_path, moved))
    assert "ledger/key-order" in _checks(diags)


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


GUARDS_MARKER = "<!-- build-memory-guards: 1 -->"
PROJECT_STATUSES = frozenset({"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "PAUSED", "DONE"})


def test_real_tree_zero_errors_and_every_status_conflict_documented() -> None:
    """The real tree: zero errors (a true invariant — it caught the #165/#179
    record defects), and every ``deferrals/status-conflict`` the parser surfaces
    is reconciled by a recorded interpretation — an obligation-event migration
    anchor (P32.7/ADR-126) or an entry of ``reconciliations.json`` — so closing
    such a row never turns this red while an undocumented conflict always does.
    The documented manifest/ticket conflicts are facts of append-only records
    (the Lane-B pointer rows; P31.19's depends line), so their detection stays
    pinned as the parser-regression guard."""
    diags, meta = audit_current_state.audit(REPO_ROOT)
    errors = [d for d in diags if d["severity"] == "error"]
    assert errors == [], errors
    obligations = REPO_ROOT / "docs" / "build" / "reports" / "obligations"
    documented = {
        (d["check"], d["obligation"])
        for d in json.loads((obligations / "reconciliations.json").read_text())["documented"]
    }
    events, errs = obligation_events.load_jsonl(obligations / "events.jsonl")
    assert errs == [], errs
    reconciled = {
        ev["obligation_id"]
        for ev in events
        if ev.get("kind") == "migration"
        and ev.get("anchor", {}).get("interpretation") in {"reconciled", "ambiguous-open"}
    }
    undocumented = [
        d
        for d in _by_check(diags, "deferrals/status-conflict")
        if d["obligation"] not in reconciled and (d["check"], d["obligation"]) not in documented
    ]
    assert undocumented == [], undocumented
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


def test_real_tree_ledger_cursor_is_honest() -> None:
    """The LEDGER cursor after any closeout, as invariants (this replaces the
    P33.8 test that pinned the cursor's literal values): no ``ledger/*`` finding
    of any severity — key order, ``nextTicket`` names a chain row (or DONE /
    SETUP) that has not landed, ``lastCompleted`` names a landed row with
    existing evidence, the index does not run ahead, PHASE LOG ``done`` entries
    are indexed — and the project is never DONE while a row is still next.
    Under the guards marker (BM-COMPAT-06) ``projectStatus`` is also held to
    the layout vocabulary; a legacy ledger keeps its legacy spelling."""
    diags, _ = audit_current_state.audit(REPO_ROOT)
    findings = [d for d in diags if d["check"].startswith("ledger/")]
    assert findings == [], findings
    text = (REPO_ROOT / "docs" / "build" / "LEDGER.md").read_text()
    status = audit_current_state._lval(text, "projectStatus")
    upcoming = audit_current_state._lval(text, "nextTicket")
    assert status, "CURRENT STATE has no projectStatus value"
    if status.upper() == "DONE":
        assert upcoming == "DONE", f"projectStatus DONE while nextTicket is {upcoming!r}"
    readme = (REPO_ROOT / "docs" / "build" / "README.md").read_text()
    if GUARDS_MARKER in readme:
        assert status in PROJECT_STATUSES, f"projectStatus {status!r} is off-vocabulary"


def test_parsing_preserves_each_rows_own_leading_status() -> None:
    """Parsing never closes (or opens) an obligation: every DEFERRALS obligation
    row is parsed, and its parsed status is exactly the row's own leading status
    token — never a later dated token in the prose (no last-token-wins). This is
    the invariant the former named-row pin stood in for; closing a row with a
    recorded transition changes its leading token and so never turns this red."""
    audit_current_state.audit(REPO_ROOT)  # the audit must not raise on the real tree
    obligations = audit_current_state.parse_deferrals(REPO_ROOT, [])
    assert obligations, "DEFERRALS.md parser found no obligation rows — parser broke?"
    raw: dict[str, str] = {}
    lines = (REPO_ROOT / "docs" / "tickets" / "DEFERRALS.md").read_text().splitlines()
    for line in lines:
        if audit_current_state.DEFERRAL_XREF_RE.match(line):
            continue
        m = re.match(r"^\|\s*(D-[^|\s]+)\s*\|", line)
        if not m:
            continue
        oid = m.group(1).rstrip("`*.,;:)")
        if not audit_current_state.DEFERRAL_ID_RE.match(oid):
            continue
        status_cell = line.rstrip().rstrip("|").rsplit("|", 1)[-1]
        raw.setdefault(oid, (status_cell.split() or [""])[0].upper())
    parsed = {o["id"]: o["status"] for o in obligations}
    assert parsed.keys() == raw.keys(), sorted(parsed.keys() ^ raw.keys())
    changed = {oid: (raw[oid], parsed[oid]) for oid in raw if parsed[oid] != raw[oid]}
    assert changed == {}, changed


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
