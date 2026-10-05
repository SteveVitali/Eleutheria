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

import pytest

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
        # Round 11 (SEED-15): multi-digit rows and letter-suffixed tickets
        "closed-by:P31.16",
        "P34.48",
        "P37.16a",
        "closed-by:P32.23a",
        "P39+",
    ):
        assert check_backlog.LANDING_RE.match(good), good
    for bad in (
        "later",
        "TBD",
        "closed-by:X",
        "P1.2",
        "human-gate:HG-9",
        "",
        "P24",
        "P34.4AB",
        "P34.",
    ):
        assert not check_backlog.LANDING_RE.match(bad), bad


# --- P22+ triage (GL-META-01) -------------------------------------------------


def test_no_p22_plus_landings_remain() -> None:
    # The P22 planning pass closed; META.1 triaged every P22+ row to a real
    # landing. A new P22+ filing fails this test.
    stale = [r["bl_id"] for r in _rows() if r["landing"] == "P22+"]
    assert not stale, f"P22+ landings not triaged: {stale}"


@pytest.mark.living_record_invariant("backlog-terminal-history")
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
    # `>`-quoted lines are verbatim restorations/amendment quotes (B2 §5.3),
    # never live pointers, so they are out of the scan.
    for rel in _LIVE_RERUN_CONTRACTS:
        text = "\n".join(
            line
            for line in (REPO_ROOT / rel).read_text().split("\n")
            if not line.lstrip().startswith(">")
        )
        for m in _REF_RE.finditer(text):
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


# --- P24.8 / REC.1: every owed deferral names its BL home ----------------------
#
# A `D-*` id cannot live in a `sources` cell (it would be an orphan — only
# RISK-*/ADR-*/LD-*/LH-* are in the checker's universe), so an OPEN/PARTIAL
# DEFERRALS row expresses its backlog home as `(cites BL-nnn)`. These tests pin
# both the helper's parse and the repo-level invariant — a new owed deferral
# opened without a cite fails `check_backlog.py` (and `make check`).


def test_deferral_homes_parses_owed_rows(tmp_path) -> None:
    fake = tmp_path / "DEFERRALS.md"
    fake.write_text(
        "| id | obligation | compensating control | verify | status |\n"
        "|---|---|---|---|---|\n"
        "| D-X-1 | owed thing | ctrl | path | OPEN (cites BL-037) |\n"
        "| D-X-2 | owed thing | ctrl | path | PARTIAL |\n"
        "| D-X-3 | owed thing | ctrl | path | OPEN — note (cites BL-033) |\n"
        "| D-X-4 | done thing | ctrl | path | DONE |\n"
    )
    citing, missing = check_backlog.deferral_homes(fake)
    assert citing == ["D-X-1", "D-X-3"]
    assert missing == ["D-X-2"]


def test_every_owed_deferral_cites_a_bl_home() -> None:
    citing, missing = check_backlog.deferral_homes(DEFERRALS)
    assert citing, "expected at least one OPEN/PARTIAL deferral citing a BL home"
    assert not missing, f"OPEN/PARTIAL DEFERRALS rows with no BL home: {missing}"
    # every cited home must be a real backlog row
    text = DEFERRALS.read_text()
    rows = {r["bl_id"] for r in _rows()}
    for ln in text.splitlines():
        if not check_backlog._DEFERRAL_ROW.match(ln):
            continue
        cells = [c.strip() for c in ln.split("|")]
        words = cells[-2].split() if len(cells) >= 2 else []
        if not words or words[0].upper() not in check_backlog.DEFERRAL_OWED_STATUSES:
            continue
        cited = set(re.findall(r"BL-\d{3}", ln))
        assert cited <= rows, f"{ln[:60]}… cites non-existent BL rows: {cited - rows}"


# --- Round 11 (SEED-15): the open-home rule and RISK-id uniqueness --------------


def test_open_home_rule_needs_an_open_bl_row(tmp_path) -> None:
    """An owed row homes only on an open BACKLOG row; an appended `(cites BL-nnn)` re-homing
    annotation homes a row whose original cite closed (rows are append-only)."""
    fake = tmp_path / "DEFERRALS.md"
    fake.write_text(
        "| id | obligation | status |\n|---|---|---|\n"
        "| D-X-1 | owed | OPEN (cites BL-001) |\n"
        "| D-X-2 | owed | OPEN (cites BL-002) · re-homed 2026-10-01: (cites BL-001) |\n"
        "| D-X-3 | owed | PARTIAL (cites BL-002) |\n"
        "| D-X-4 | owed | OPEN (cites BL-003) |\n"
        "| D-X-5 | done | DONE (cites BL-002) |\n"
    )
    status = {"BL-001": "open", "BL-002": "closed", "BL-003": "accepted"}
    homed, unhomed = check_backlog.deferral_open_homes(fake, status)
    assert homed == ["D-X-1", "D-X-2"]
    assert unhomed == ["D-X-3", "D-X-4"]


def test_adr_trigger_homes_follow_the_trigger_state() -> None:
    owner = {
        "ADR-001": "BL-001",
        "ADR-002": "BL-002",
        "ADR-003": "BL-003",
        "ADR-004": "BL-002",
        "ADR-005": "BL-003",
    }
    status = {"BL-001": "open", "BL-002": "accepted", "BL-003": "closed"}
    register = [
        {"adr": "ADR-001", "state": "fired-unanswered", "home": "BL-001"},  # open home: any state
        {
            "adr": "ADR-002",
            "state": "fired-answered(P34.1)",
            "home": "BL-002",
        },  # monitor home: answered ok
        {"adr": "ADR-003", "state": "quiet", "home": "BL-003"},  # closed home: quiet ok
        {
            "adr": "ADR-004",
            "state": "fired-unanswered",
            "home": "BL-002",
        },  # monitor home: unanswered no
        {
            "adr": "ADR-005",
            "state": "fired-answered(P34.1)",
            "home": "BL-001",
        },  # closed home + home mismatch
    ]
    problems = check_backlog.adr_home_problems(
        ["ADR-001", "ADR-002", "ADR-003", "ADR-004", "ADR-005", "ADR-006"], owner, status, register
    )
    joined = "; ".join(problems)
    assert "ADR-004: home BL-002 is 'accepted' while the trigger is 'fired-unanswered'" in joined
    assert "ADR-005: ADR_TRIGGERS.csv home 'BL-001' != BACKLOG owner BL-003" in joined
    assert "ADR-005: home BL-003 is 'closed' while the trigger is 'fired-answered'" in joined
    assert not any(p.startswith(("ADR-001", "ADR-002", "ADR-003")) for p in problems)
    assert len(problems) == 3  # ADR-006 has no BACKLOG owner: reported as unmapped elsewhere


def test_risk_ids_unique_unless_a_rename_record_resolves_them(tmp_path) -> None:
    reg = tmp_path / "risk_register.md"
    reg.write_text(
        "## Phase 5\n\n### Scaffolded\n\n| RISK-P5-04 → BL-017 | a |\n| RISK-P5-09 | b |\n\n"
        "### Partly retired\n\n| RISK-P5-04 | c |\n| RISK-P5-09 | d |\n\n"
        "## Round 11 review\n\n### Corrections, closures and re-routes\n\n"
        "| RISK-P5-04 (second occurrence) | **Renamed RISK-P5-04a by this record.** |\n"
        "| RISK-P5-09 | restated in a corrections table, not a definition |\n"
    )
    assert check_backlog.risk_id_duplicates(reg) == ["RISK-P5-09"]


def test_real_register_has_unique_risk_ids_and_open_deferral_homes() -> None:
    assert check_backlog.risk_id_duplicates(check_backlog.RISK) == []
    status = {r["bl_id"]: r["status"] for r in _rows()}
    homed, unhomed = check_backlog.deferral_open_homes(DEFERRALS, status)
    assert homed and not unhomed, unhomed
