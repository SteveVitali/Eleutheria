#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``ledger_contract.py`` (P34.9; B3 §6 V1–V6, V8, V11 and B4 V12–V13;
G5 + G11 no-vacuous-pass).

A minimal valid build-memory tree in ``tmp_path`` is the seeded fixture: it
must pass, and every check must have evaluated at least one item (so the suite
fails against a no-op validator). One mutation per test makes exactly that rule
fail — the pre-seed shape (oversized orient, off-vocabulary CURRENT STATE,
`PRIOR` history, stale tokens, missing named paths) is the V1/V2/V3 failing
pair. G11: every named validator fails exit 3 when a non-empty candidate set
evaluates nothing. The docs-check/CI wiring and the vendored patch hunks are
asserted so removing the new gate (or a patch) fails a test.

Run::

    uv run pytest docs/build/tools/test_ledger_contract.py -q
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

_HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = _HERE.parents[2]
_spec = importlib.util.spec_from_file_location(
    "ledger_contract", _HERE / "ledger_contract.py"
)
lc = importlib.util.module_from_spec(_spec)
sys.modules["ledger_contract"] = lc
assert _spec.loader is not None
_spec.loader.exec_module(lc)


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


check_spec_src = _load_tool("check_spec_src")
check_coverage_matrix = _load_tool("check_coverage_matrix")
check_backlog = _load_tool("check_backlog")
audit_current_state = _load_tool("audit_current_state")
current_projection = _load_tool("current_projection")
obligation_events = _load_tool("obligation_events")

NOW = "2026-10-02T12:00:00Z"

# ── the seeded fixture ────────────────────────────────────────────────────────

CURRENT_STATE = """```
projectStatus: IN_PROGRESS
nextTicket: P00.2
lastCompleted: P00.1
blockedOn: (nothing)
pauseRequested: false
returnPass: (none)
manifest: docs/tickets/00_MANIFEST.md
canonicalSpec: docs/2_canonical_design_spec.md
memoryRoot: docs/build
dispatchTarget: —
buildWorktree: .
buildBranchBase: —
pinnedBaseSha: deadbeef
chainTip: r11/test
benchmarkSet: —
autonomy: checkpoint
mergePolicy: NONE
round: 11
harness: devin-desktop/swe-2-high/subagent
updatedAt: 2026-10-01T00:00:00Z
```"""

GATE_DECISIONS = """## GATE DECISIONS

### Round 11

| date | ticket | gate | item | answer (verbatim) | consequence | kind |
|---|---|---|---|---|---|---|
| 2026-10-01 | SEED-01 | GATE-T | a decision | "go" (operator, recorded verbatim) | the record | decision |
"""

RETURN_PASS = """## RETURN PASS

### RETURN PASS — current

| ticket | obligations | gates / blocking domain | what the operator must do | re-run line |
|---|---|---|---|---|
"""

PHASE_LOG = """## PHASE LOG

- 2026-10-01 — P00.1 ticket — the test landing
"""

LEDGER_OK = (
    "# LEDGER (fixture)\n\n## CURRENT STATE\n\n"
    + CURRENT_STATE
    + "\n\n## OPEN FINDINGS\n\n(none)\n\n"
    + GATE_DECISIONS
    + "\n"
    + RETURN_PASS
    + "\n"
    + PHASE_LOG
)

BUILD_INDEX_OK = """# BUILD_INDEX

## Round 11

| seq | ticket | kind | branch | PR | base | landed | ADRs | deferrals opened → closed | live verification | evidence | harness |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 201 | P00.1 | ticket | `r11/test` | #1 | `r11/seed` | 2026-10-01 | — | — | fixture-only | `runs/P00.1.md` | devin-desktop/swe-2-high/subagent |
"""

MANIFEST = """# manifest

companions: _TEMPLATE.md

## The chain

### Round 11

| # | ticket | kind |
|---|---|---|
| 201 | `201_P00.1__first.md` | ticket |
| 202 | `202_P00.2__next.md` | ticket |
"""

KINDS = "ticket\npost-closeout record\npause\nround\ngate\ncorrection\nrestored\n"


def _files(**overrides: str) -> dict[str, str]:
    files = {
        "docs/build/README.md": "<!-- build-memory: v2 -->\n",
        "docs/build/LEDGER.md": LEDGER_OK,
        "docs/build/BUILD_INDEX.md": BUILD_INDEX_OK,
        "docs/build/tools/record_policy/phase_log_kinds.txt": KINDS,
        "docs/build/tools/record_policy/stale_tokens.txt": "# none retired\n",
        "docs/build/runs/P00.1.md": (
            "# P00.1 run\n\n- **Harness:** devin-desktop/swe-2-high/subagent\n\n"
            "**Closed:** done\n"
        ),
        "docs/tickets/00_MANIFEST.md": MANIFEST,
        "docs/tickets/201_P00.1__first.md": "# P00.1\n",
        "docs/tickets/202_P00.2__next.md": "# P00.2\n\n## contract\n",
        "docs/2_canonical_design_spec.md": "# spec\n",
    }
    files.update(overrides)
    return files


def _tree(tmp_path: pathlib.Path, **overrides: str) -> pathlib.Path:
    for rel, text in _files(**overrides).items():
        path = tmp_path / rel
        if text is None:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def _ctx() -> dict:
    return {
        "bound_dt": lc.parse_dt(NOW),
        "bound_iso": NOW,
        "manifest_rel": "docs/tickets/00_MANIFEST.md",
        # marker committed + empty adds → every runs/*.md is a harness candidate
        "marker_state": "committed",
        "before": set(),
        "adds": {},
    }


def _run(tmp_path: pathlib.Path) -> tuple[int, lc.Report]:
    rep = lc.run_checks(lc.TreeSrc(tmp_path), _ctx())
    code, _vacuous = lc.verdict(rep)
    return code, rep


def _rules(rep: lc.Report) -> set[str]:
    return {f.rule for f in rep.findings if f.severity == "error"}


# ── the seeded fixture passes — and nothing is silently skipped ───────────────


def test_seeded_fixture_passes(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    code, rep = _run(root)
    assert code == lc.EXIT_OK, [
        f"{f.check}/{f.rule}: {f.message}" for f in rep.findings
    ]
    # every check that saw candidates evaluated them — a silently-skipped check
    # is a bug this suite exists to catch (G11)
    for c in lc.CHECKS:
        cand, ev = rep.counts.get(c.name, [0, 0])
        assert not (cand > 0 and ev == 0), f"{c.name} skipped its candidate set"


def test_json_report_carries_counts(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    rep = lc.run_checks(lc.TreeSrc(root), _ctx())
    out = tmp_path / "report.json"
    code = lc.emit(rep, {"repo": str(root), "at": "worktree", "bound": NOW,
                         "input_digest": ""}, str(out), "test")
    doc = json.loads(out.read_text())
    assert doc["schema"] == "ledger-contract/1"
    assert doc["exit"] == code
    for entry in doc["checks"]:
        assert set(entry) >= {"check", "candidates", "evaluated", "floor"}
        if entry["candidates"] > 0:
            assert entry["evaluated"] > 0, entry["check"]


# ── the pre-seed shape fails V1 / V2 / V3 ─────────────────────────────────────


def test_oversized_orient_fails_v1(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": "# pad\n" + "x" * (lc.ORIENT_MAX + 16)
           + "\n" + LEDGER_OK},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "orient-budget" in _rules(rep)


def test_off_enum_project_status_fails_v2(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            "projectStatus: IN_PROGRESS", "projectStatus: WOBBLY"
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "key-vocabulary" in _rules(rep)


def test_prior_value_fails_v2(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            "nextTicket: P00.2", "nextTicket: P00.2 | PRIOR P00.1"
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "prior-history" in _rules(rep)


def test_stale_token_fails_v3(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            "## OPEN FINDINGS", "scratch lives under .agents/scratch\n\n## OPEN FINDINGS"
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "stale-token" in _rules(rep)


def test_missing_named_path_fails_v3(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            "## OPEN FINDINGS",
            "read `docs/build/reports/never-committed.md` first\n\n## OPEN FINDINGS",
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "path-missing" in _rules(rep)


def test_preseed_shape_fails_across_v1_v2_v3(tmp_path: pathlib.Path) -> None:
    """A ledger carrying all three pre-seed failure classes fails all three."""
    bad = (
        "x" * (lc.ORIENT_MAX + 8)
        + "\n"
        + LEDGER_OK.replace("projectStatus: IN_PROGRESS", "projectStatus: WOBBLY")
        .replace(
            "## OPEN FINDINGS",
            "dead path `docs/build/nope/gone.md` is named\n\n## OPEN FINDINGS",
        )
    )
    root = _tree(tmp_path, **{"docs/build/LEDGER.md": bad})
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert {"orient-budget", "key-vocabulary", "path-missing"} <= _rules(rep)


# ── V4 PHASE LOG ──────────────────────────────────────────────────────────────


def test_unparseable_done_entries_are_vacuous(tmp_path: pathlib.Path) -> None:
    """Done-candidates that never evaluate are vacuous, not green (G11)."""
    ledger = LEDGER_OK.replace(
        "- 2026-10-01 — P00.1 ticket — the test landing",
        "- 2026-10-01 — the thing we shipped done — prose head, no id",
    )
    # nothing landed now, so the next row is the lowest chain row
    ledger = ledger.replace("nextTicket: P00.2", "nextTicket: P00.1")
    ledger = ledger.replace("lastCompleted: P00.1", "lastCompleted: —")
    root = _tree(
        tmp_path,
        **{
            "docs/build/LEDGER.md": ledger,
            "docs/build/BUILD_INDEX.md": BUILD_INDEX_OK.replace(
                "| 201 | P00.1 | ticket | `r11/test` | #1 | `r11/seed` | 2026-10-01 | — | — | fixture-only | `runs/P00.1.md` | devin-desktop/swe-2-high/subagent |",
                "| 201 | — | ticket | — | — | — | — | — | — | n-a | — | — |",
            ),
        }
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VACUOUS
    assert rep.counts["phase-log-done"][0] > 0
    assert rep.counts["phase-log-done"][1] == 0


def test_markup_id_parses_and_is_flagged(tmp_path: pathlib.Path) -> None:
    """A `**bold**` id parses (it is evaluated, never skipped) and is flagged."""
    ledger = LEDGER_OK.replace(
        "- 2026-10-01 — P00.1 ticket — the test landing",
        "- 2026-10-01 — **P00.1** ticket — markup id",
    )
    root = _tree(tmp_path, **{"docs/build/LEDGER.md": ledger})
    code, rep = _run(root)
    # the entry was evaluated (id extracted), so done-coverage held — and the
    # markup form itself is the strict-region violation
    assert rep.counts["phase-log-done"][1] == 1
    assert code == lc.EXIT_VIOLATIONS
    assert "markup-id" in _rules(rep)


def test_pseudo_ids_are_allow_listed(tmp_path: pathlib.Path) -> None:
    ledger = LEDGER_OK.replace(
        "- 2026-10-01 — P00.1 ticket — the test landing",
        "- 2026-10-01 — OPERATOR pause — the operator paused\n"
        "- 2026-10-01 — ROUND9 round — the round boundary\n"
        "- 2026-10-01 — P00.1 ticket — the test landing",
    )
    root = _tree(tmp_path, **{"docs/build/LEDGER.md": ledger})
    code, rep = _run(root)
    assert code == lc.EXIT_OK, [
        f"{f.check}/{f.rule}: {f.message}" for f in rep.findings
    ]


def test_future_phase_log_date_fails(tmp_path: pathlib.Path) -> None:
    ledger = LEDGER_OK.replace(
        "- 2026-10-01 — P00.1 ticket", "- 2036-10-01 — P00.1 ticket"
    )
    root = _tree(tmp_path, **{"docs/build/LEDGER.md": ledger})
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "future-date" in _rules(rep)


# ── V5 BUILD_INDEX ────────────────────────────────────────────────────────────


def test_build_index_unescaped_pipe_fails(tmp_path: pathlib.Path) -> None:
    bi = BUILD_INDEX_OK.replace(
        "| 201 | P00.1 | ticket |",
        "| 201 | P00.1 | tic|ket |",  # an unescaped pipe inside a cell
    )
    root = _tree(tmp_path, **{"docs/build/BUILD_INDEX.md": bi})
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "column-count" in _rules(rep)


def test_build_index_escaped_pipe_passes(tmp_path: pathlib.Path) -> None:
    bi = BUILD_INDEX_OK.replace(
        "| 201 | P00.1 | ticket |",
        "| 201 | P00.1 | tic\\|ket |",  # escaped — one cell, not two
    )
    root = _tree(tmp_path, **{"docs/build/BUILD_INDEX.md": bi})
    code, rep = _run(root)
    assert "column-count" not in _rules(rep)
    assert code == lc.EXIT_OK, [
        f"{f.check}/{f.rule}: {f.message}" for f in rep.findings
    ]


def test_build_index_duplicate_seq_fails(tmp_path: pathlib.Path) -> None:
    bi = BUILD_INDEX_OK + (
        "| 201 | P00.2 | ticket | `r11/t` | #2 | `r11/b` | 2026-10-01 | — | — | "
        "fixture-only | `runs/P00.2.md` | devin-desktop/swe-2-high/subagent |\n"
    )
    root = _tree(tmp_path, **{"docs/build/BUILD_INDEX.md": bi})
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "seq-duplicate" in _rules(rep)


# ── V6 RETURN PASS ────────────────────────────────────────────────────────────


def test_return_pass_drift_fails(tmp_path: pathlib.Path) -> None:
    ledger = LEDGER_OK.replace("returnPass: (none)", "returnPass: P00.2")
    root = _tree(tmp_path, **{"docs/build/LEDGER.md": ledger})
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "set-drift" in _rules(rep)


# ── V8 GATE DECISIONS ─────────────────────────────────────────────────────────


def _gd_row(cells: str) -> str:
    return GATE_DECISIONS.replace(
        '| 2026-10-01 | SEED-01 | GATE-T | a decision | "go" (operator, recorded verbatim) | the record | decision |',
        cells,
    )


def test_gate_decisions_malformed_columns_fail(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            GATE_DECISIONS, _gd_row("| 2026-10-01 | SEED-01 | GATE-T | item only |")
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "column-count" in _rules(rep)


def test_gate_decisions_invalid_kind_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            GATE_DECISIONS,
            _gd_row('| 2026-10-01 | SEED-01 | GATE-T | item | "go" | rec | guess |'),
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "kind-vocabulary" in _rules(rep)


def test_gate_decisions_future_date_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            GATE_DECISIONS,
            _gd_row('| 2036-10-01 | SEED-01 | GATE-T | item | "go" | rec | decision |'),
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "future-date" in _rules(rep)


def test_gate_decisions_empty_answer_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/LEDGER.md": LEDGER_OK.replace(
            GATE_DECISIONS,
            _gd_row('| 2026-10-01 | SEED-01 | GATE-T | item |  | rec | decision |'),
        )},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "answer-empty" in _rules(rep)


# ── V12 run-ledger harness ────────────────────────────────────────────────────


def test_run_ledger_without_harness_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/runs/P00.1.md": "# P00.1 run\n\nno harness line\n"},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "harness-missing" in _rules(rep)
    # the run ledger was offered AND evaluated — the violation is the verdict
    assert rep.counts["run-harness"] == [1, 1]


def test_run_ledger_malformed_harness_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(
        tmp_path,
        **{"docs/build/runs/P00.1.md": "# P00.1\n\n- **Harness:** not-a-harness\n"},
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "harness-missing" in _rules(rep)


# ── V13 manifest rounds ───────────────────────────────────────────────────────


def test_ticket_id_reuse_in_round11_fails(tmp_path: pathlib.Path) -> None:
    manifest = MANIFEST + "| 203 | `203_P00.1__reused.md` | ticket |\n"
    root = _tree(tmp_path, **{"docs/tickets/00_MANIFEST.md": manifest})
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "id-reused" in _rules(rep)


def test_unbannered_round11_row_fails(tmp_path: pathlib.Path) -> None:
    manifest = MANIFEST + "\n### housekeeping\n\n| 203 | `203_P00.3__x.md` | ticket |\n"
    root = _tree(
        tmp_path,
        **{
            "docs/tickets/00_MANIFEST.md": manifest,
            "docs/build/LEDGER.md": LEDGER_OK.replace(
                "nextTicket: P00.2", "nextTicket: P00.2"
            ),
        },
    )
    code, rep = _run(root)
    assert code == lc.EXIT_VIOLATIONS
    assert "round-banner" in _rules(rep)


# ── G11 across the named validators ──────────────────────────────────────────


def test_check_spec_src_vacuous(tmp_path: pathlib.Path) -> None:
    """spec-src files offered, none readable → exit 3, never a silent pass."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/2_canonical_design_spec.md").write_text("# spec\n")
    src_dir = tmp_path / "docs/research/_meta/spec_src"
    src_dir.mkdir(parents=True)
    (src_dir / "01_broken.md").mkdir()  # a section file that cannot be read
    (tmp_path / "docs/adr").mkdir()
    code = check_spec_src.main(["--root", str(tmp_path)])
    assert code == 3


def test_check_coverage_matrix_vacuous(tmp_path: pathlib.Path) -> None:
    """Matrix rows offered, none parse to the header width → exit 3."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/2_canonical_design_spec.md").write_text(
        "**SIG-AA-001 (MUST).** One.\n"
    )
    csv_path = tmp_path / "docs/build/COVERAGE_MATRIX.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        ",".join(check_coverage_matrix.HEADER) + "\n" + "SIG-AA-001,only,two\n"
    )
    code = check_coverage_matrix.main(
        ["x", str(csv_path), "--root", str(tmp_path)]
    )
    assert code == 3


def test_check_backlog_vacuous(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    """DEFERRALS `| D-…` rows offered, none reaching a status cell → exit 3."""
    backlog = tmp_path / "BACKLOG.csv"
    backlog.write_text(
        "bl_id,title,type,sources,req_ids,package,blocks,landing,gate,size,status\n"
        "BL-001,t,process,RISK-T-1,,pkg,,accepted,,S,accepted\n"
    )
    risk = tmp_path / "risk.md"
    risk.write_text("# risk\n")
    ld = tmp_path / "ld.md"
    ld.write_text("# ld\n")
    adr = tmp_path / "adr"
    adr.mkdir()
    deferrals = tmp_path / "DEFERRALS.md"
    deferrals.write_text(
        "# def\n\n| D-T1-1 | V | x | y | z | w | p | WOBBLY |\n"
    )
    for name, val in (
        ("BACKLOG", backlog), ("RISK", risk), ("LD", ld), ("ADR_DIR", adr),
        ("DEFERRALS", deferrals), ("THEMES", tmp_path / "no-themes"),
        ("ADR_TRIGGERS", tmp_path / "no-triggers.csv"),
    ):
        monkeypatch.setattr(check_backlog, name, val)
    assert check_backlog.main() == 3


def test_audit_current_state_vacuous(tmp_path: pathlib.Path) -> None:
    """A manifest of only unparseable chain rows: offered, none evaluated → 3."""
    (tmp_path / "docs/build").mkdir(parents=True)
    (tmp_path / "docs/build/README.md").write_text(
        "<!-- build-memory: v2 -->\n"
    )
    (tmp_path / "docs/tickets").mkdir()
    (tmp_path / "docs/tickets/00_MANIFEST.md").write_text(
        "# manifest\n\n## The chain\n\n"
        "| seq | file |\n|---|---|\n"
        "| not-a-seq | `x.md` |\n"
        "| also-not | `y.md` |\n"
    )
    code = audit_current_state.main(["--root", str(tmp_path)])
    assert code == 3


def test_current_projection_verify_vacuous(tmp_path: pathlib.Path) -> None:
    """A recorded manifest whose inputs all vanish verifies nothing → exit 3."""
    out = tmp_path / "docs/build/reports/current"
    out.mkdir(parents=True)
    manifest = {
        "schema": "projection-manifest/1",
        "inputs": [
            {"path": "docs/build/LEDGER.md", "sha256": "0" * 64},
            {"path": "docs/build/BUILD_INDEX.md", "sha256": "1" * 64},
        ],
        "manifest_sha256": "2" * 64,
        "input_commit": "deadbeef",
    }
    (out / "manifest.json").write_text(json.dumps(manifest))
    code = current_projection.verify(tmp_path, out)
    assert code == 3


def test_obligation_events_check_vacuous(tmp_path: pathlib.Path) -> None:
    """jsonl lines offered, none parse → exit 3."""
    events = tmp_path / obligation_events.EVENTS_PATH
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text("not json at all\n{unclosed\n")
    assert obligation_events.check(tmp_path) == 3


# ── wiring + removal sensitivity ──────────────────────────────────────────────


def test_docs_check_composes_the_new_gates() -> None:
    text = (REPO_ROOT / "Makefile").read_text()
    for target in (
        "docs-check-ledger",
        "docs-check-audit",
        "docs-check-projection",
        "docs-check-planning",
    ):
        assert f"{target}:" in text, f"Makefile lacks target {target}"
    dep_line = next(
        ln for ln in text.splitlines() if ln.startswith("docs-check:")
    )
    for target in (
        "docs-check-ledger",
        "docs-check-audit",
        "docs-check-projection",
        "docs-check-planning",
    ):
        assert target in dep_line, f"docs-check does not depend on {target}"
    assert "ledger_contract.py check" in text
    assert "audit_current_state.py --require-reconciled" in text
    assert "current_projection.py verify" in text
    assert "obligation_events.py check" in text
    assert "check_backlog.py" in text
    assert "--planning" in text


def test_ci_docs_job_names_the_new_gates() -> None:
    text = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    docs_job = text.split("  docs:", 1)[1].split("\n  python:", 1)[0]
    assert "make docs-check" in docs_job
    assert "ledger_contract.py check" in docs_job
    assert "current_projection.py verify" in docs_job
    assert "|| true" not in docs_job.split(
        "current_projection.py verify", 1
    )[0].rsplit("run:", 1)[-1]


def test_new_gate_files_exist() -> None:
    """Removal-sensitive: deleting the validator or a policy file fails here."""
    assert (_HERE / "ledger_contract.py").is_file()
    assert (_HERE / "record_policy" / "stale_tokens.txt").is_file()
    assert (_HERE / "record_policy" / "phase_log_kinds.txt").is_file()


def test_vendored_patch_hunks_present() -> None:
    """Removal-sensitive: the SIG-LOCAL G11 hunks of check-build-memory.sh must
    be there — a revert of the patch fails this test."""
    text = (REPO_ROOT / "scripts/docs/check-build-memory.sh").read_text()
    assert "SIG-LOCAL" in text, "the local-patch provenance header is gone"
    # count() marks a non-empty-but-unevaluated family vacuous (G11)
    assert "VACUOUS=1" in text
    # the JSON report carries the per-check counts
    assert '"counts"' in text or "counts" in text


def test_vendored_checker_json_exposes_counts() -> None:
    """`check-build-memory.sh --json` writes per-check candidates/evaluated —
    run once against the repo; asserts shape only, never living values."""
    out = subprocess.run(
        ["bash", "scripts/docs/check-build-memory.sh", ".",
         "--json", "/tmp/p34-9-bmc-counts.json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    report = json.loads(
        pathlib.Path("/tmp/p34-9-bmc-counts.json").read_text()
    )
    assert "counts" in report and report["counts"], out.stderr
    for name, pair in report["counts"].items():
        assert set(pair) >= {"candidates", "evaluated"}, name


def test_vendored_checker_vacuous_on_empty_parse(tmp_path: pathlib.Path) -> None:
    """A build-memory repo whose PHASE LOG offers done-candidates that never
    parse exits 3 from the vendored checker too (G11 SIG-LOCAL hunk)."""
    (tmp_path / "docs/build").mkdir(parents=True)
    (tmp_path / "docs/build/README.md").write_text(
        "<!-- build-memory: v2 -->\n<!-- build-memory-guards: 1 -->\n"
    )
    (tmp_path / "docs/build/LEDGER.md").write_text(LEDGER_OK.replace(
        "- 2026-10-01 — P00.1 ticket — the test landing",
        "- 2026-10-01 — the thing we shipped done — prose head, no id",
    ))
    (tmp_path / "docs/build/BUILD_INDEX.md").write_text("# index\n")
    (tmp_path / "docs/tickets").mkdir()
    (tmp_path / "docs/tickets/00_MANIFEST.md").write_text(MANIFEST)
    (tmp_path / "docs/adr").mkdir()
    out = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/docs/check-build-memory.sh"),
         str(tmp_path), "--json", "/tmp/p34-9-vacuous.json"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert out.returncode == 3, (out.stdout, out.stderr)
