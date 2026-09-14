# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""META.1 / GL-META-01 housekeeping guards (P24.5; closes BL-052).

Pins every deterministic acceptance criterion + each new behaviour this ticket
introduced: no "skeleton" package descriptions, `check_backlog.py` green against
the post-P22.3 `docs/build/reports/` layout, the extended landing enum, the P22+
triage result, the regenerated `BACKLOG.md` mirror, and resolvable `docs/build/`
pointers in the Lane-B re-run contracts. Each test fails if the behaviour it
guards is removed or regresses.
"""

from __future__ import annotations

import csv
import importlib.util
import re
import subprocess
import sys
import tomllib

from support import PY_PACKAGES, REPO_ROOT

TOOLS = REPO_ROOT / "docs" / "build" / "tools"
BACKLOG = REPO_ROOT / "docs" / "build" / "BACKLOG.csv"
DEFERRALS = REPO_ROOT / "docs" / "tickets" / "DEFERRALS.md"


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


check_backlog = _load_tool("check_backlog")
build_backlog_md = _load_tool("build_backlog_md")


def _rows() -> list[dict[str, str]]:
    with BACKLOG.open(newline="") as fh:
        return list(csv.DictReader(fh))


# --- BL-052: package descriptions -------------------------------------------


def test_no_package_description_says_skeleton() -> None:
    bad = []
    for pkg in PY_PACKAGES:
        with (REPO_ROOT / pkg / "pyproject.toml").open("rb") as fh:
            desc = tomllib.load(fh)["project"]["description"]
        if "skeleton" in desc.lower():
            bad.append(pkg)
    assert not bad, f"package descriptions still say 'skeleton': {bad}"


# --- check_backlog.py + the post-P22.3 layout --------------------------------


def test_check_backlog_sources_resolve_under_reports() -> None:
    # P22.3 moved LEDGER_DEFERRALS.md and BACKLOG_THEMES.md into
    # docs/build/reports/ — the checker must point at the moved files, not the
    # pre-move root paths (the drift this ticket fixed).
    assert check_backlog.LD == REPO_ROOT / "docs" / "build" / "reports" / "LEDGER_DEFERRALS.md"
    assert check_backlog.THEMES == REPO_ROOT / "docs" / "build" / "reports" / "BACKLOG_THEMES.md"
    assert check_backlog.LD.is_file(), "LEDGER_DEFERRALS.md not where the checker looks"
    assert check_backlog.THEMES.is_file(), "BACKLOG_THEMES.md not where the checker looks"


def test_check_backlog_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(TOOLS / "check_backlog.py")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"check_backlog.py failed:\n{proc.stderr}{proc.stdout}"


def test_landing_enum_accepts_real_landings() -> None:
    for good in (
        "closed-by:P19.4",
        "closed-by:P24.5",
        "P20.2",
        "P21.9",
        "P24.6",
        "P22+",
        "P25+",
        "accepted",
        "human-gate:HG-09",
    ):
        assert check_backlog.LANDING_RE.match(good), good
    for bad in ("later", "TBD", "closed-by:X", "P1.2", "human-gate:HG-9", "", "P24"):
        assert not check_backlog.LANDING_RE.match(bad), bad


# --- P22+ triage (GL-META-01) -------------------------------------------------


def test_no_p22_plus_landings_remain() -> None:
    # The P22 planning pass closed; META.1 triaged every P22+ row to a real
    # landing. A new P22+ filing fails this test.
    stale = [r["bl_id"] for r in _rows() if r["landing"] == "P22+"]
    assert not stale, f"P22+ landings not triaged: {stale}"


def test_bl052_closed() -> None:
    row = next(r for r in _rows() if r["bl_id"] == "BL-052")
    assert row["status"] == "closed"
    assert row["landing"] == "closed-by:P24.5"


def test_meta1_deferral_rows_cover_the_live_conditioned_items() -> None:
    # BL-045 (calibration once real data exists) and BL-028 (records-request
    # backend fed live) are owed obligations conditioned on post-go-live state —
    # they carry D-META.1-* rows in DEFERRALS.md citing their BL ids.
    text = DEFERRALS.read_text()
    assert "D-META.1-1" in text and "BL-045" in text
    assert "D-META.1-2" in text and "BL-028" in text


def test_backlog_md_matches_csv_render() -> None:
    rendered = build_backlog_md.render(build_backlog_md.load_rows())
    current = (REPO_ROOT / "docs" / "build" / "BACKLOG.md").read_text()
    assert current == rendered, (
        "docs/build/BACKLOG.md is stale vs BACKLOG.csv — "
        "regenerate with `python3 docs/build/tools/build_backlog_md.py`"
    )


# --- docs-drift: live re-run contract pointers -------------------------------

_LIVE_RERUN_CONTRACTS = (
    "docs/tickets/00_MANIFEST.md",
    "docs/tickets/P21.1__rights-review-and-registry-completion.md",
    "docs/tickets/P21.3__live-connector-wiring.md",
    "docs/tickets/P21.4__first-jurisdiction-ingest-and-publish.md",
    "docs/tickets/P21.5__infra-deposit-and-tiles.md",
    "docs/tickets/P21.7__contribution-back-live.md",
    "docs/tickets/P21.8__data-driven-and-coarse-international.md",
    "docs/tickets/P21.9__stage5-pathway-connectors.md",
)

_REF_RE = re.compile(r"docs/build/[A-Za-z0-9_.{}-]+(?:/[A-Za-z0-9_.{}-]+)*/?")


def test_live_rerun_ticket_refs_resolve() -> None:
    # Lane-B contracts are re-run verbatim — their `docs/build/…` Load pointers
    # must resolve in the post-P22.3 layout (report files live under reports/).
    for rel in _LIVE_RERUN_CONTRACTS:
        for m in _REF_RE.finditer((REPO_ROOT / rel).read_text()):
            ref = m.group(0).rstrip("/")
            if "{" in ref or ref.endswith("_"):  # template/templated refs
                continue
            assert (REPO_ROOT / ref).exists(), f"{rel}: stale pointer {ref}"


def test_run_okc_writes_artifacts_under_reports() -> None:
    text = (TOOLS / "run_okc.sh").read_text()
    assert 'ACCEPTANCE_OUT="$REPO_ROOT/docs/build/reports/okc/' in text
    assert 'CONNECTOR_LOG="$REPO_ROOT/docs/build/reports/okc/' in text
    # the pre-move output dir must not be recreated as an output target
    assert 'mkdir -p "$REPO_ROOT/docs/build/okc"' not in text
