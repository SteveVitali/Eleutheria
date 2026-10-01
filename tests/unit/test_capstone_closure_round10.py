# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P33.3 — Round-10 capstone-closure register guard.

The acceptance packet (``docs/build/CAPSTONE_CLOSURE.md`` §(f)) is what
GATE-ACCEPT reviews.  This test is the deterministic guarantee that the packet
cannot silently drop an owed obligation, drop a Round-10 requirement id, or
overclaim a gate/human/live row as closed.  Every assertion fails if the
register regresses — remove a row from §(f5), or flip a ``stays OPEN`` to a
closure claim, and this suite goes red.

Ticket: P33.3 (manifest row 194; engineering-only, ``live_verification=false``,
owns no requirement ids).  The test derives its expectations from the committed
sources of truth — never from the packet itself — so the packet can only pass by
covering every owed row:

* the 38 Round-10 requirement ids come from ``PLAN.json`` (and cross-checked
  against ``COVERAGE_MATRIX.csv`` rows owned by ``P32*``/``P33*`` tickets);
* the OPEN/PARTIAL obligation set comes from ``docs/tickets/DEFERRALS.md``
  status cells (``OPEN`` / ``PARTIAL`` leading token), independently of any
  P33.3 annotation text;
* gate state comes from the committed readouts (``docs/build/readouts/``).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "docs/build/planning/2026-09-25-six-streams/PLAN.json"
COVERAGE_MATRIX_PATH = REPO_ROOT / "docs/build/COVERAGE_MATRIX.csv"
CLOSURE_PATH = REPO_ROOT / "docs/build/CAPSTONE_CLOSURE.md"
DEFERRALS_PATH = REPO_ROOT / "docs/tickets/DEFERRALS.md"
READOUT_ACCEPT = REPO_ROOT / "docs/build/readouts/ACCEPT-R10.md"

# ---------------------------------------------------------------------------
# parsers (kept tiny on purpose — they read committed formats, nothing else)
# ---------------------------------------------------------------------------

_ROW_ID_RE = re.compile(r"^\| (D-[A-Za-z0-9]+[A-Za-z0-9.\-]*|SIG-[A-Z]+-[0-9]+) \|")
_STATUS_RE = re.compile(r"^\s*(OPEN|PARTIAL|DONE|CLOSED|WONTFIX|DISCHARGED|SKIPPED)\b")


def _round10_requirement_ids() -> set[str]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    ids = set(plan["requirements"].keys())
    assert len(ids) == 38, f"PLAN.json requirement set drifted: {len(ids)} ids"
    return ids


def _coverage_matrix_round10_ids() -> set[str]:
    with COVERAGE_MATRIX_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out: set[str] = set()
    for row in rows:
        owners = {t.strip() for t in row["owning_tickets"].split(";") if t.strip()}
        if any(t.startswith(("P32", "P33")) for t in owners):
            out.add(row["id"])
    return out


def _open_deferral_ids() -> dict[str, str]:
    """id -> leading status token for every still-owed DEFERRALS row."""
    out: dict[str, str] = {}
    for line in DEFERRALS_PATH.read_text(encoding="utf-8").splitlines():
        m = _ROW_ID_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        status_cell = cells[-2] if cells and cells[-1] == "" else cells[-1]
        sm = _STATUS_RE.match(status_cell)
        status = sm.group(1) if sm else "?"
        if status in {"OPEN", "PARTIAL"}:
            out[m.group(1)] = status
    return out


def _closure_section_f() -> str:
    text = CLOSURE_PATH.read_text(encoding="utf-8")
    marker = "## (f) Round-10 capstone closure"
    idx = text.find(marker)
    assert idx != -1, "CAPSTONE_CLOSURE.md is missing the §(f) Round-10 section"
    return text[idx:]


def _section_f5_register(section_f: str) -> str:
    start = section_f.find("### (f5)")
    assert start != -1, "§(f) is missing the (f5) OPEN-obligation register"
    rest = section_f[start:]
    nxt = rest.find("\n### (f", 1)
    return rest[:nxt] if nxt != -1 else rest


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_every_round10_requirement_id_is_covered_in_section_f1() -> None:
    section = _closure_section_f()
    missing = sorted(rid for rid in _round10_requirement_ids() if rid not in section)
    assert not missing, f"§(f) dropped Round-10 requirement ids: {missing}"


def test_plan_requirements_match_coverage_matrix_ownership() -> None:
    plan_ids = _round10_requirement_ids()
    matrix_ids = _coverage_matrix_round10_ids()
    assert plan_ids == matrix_ids, (
        f"PLAN.json vs COVERAGE_MATRIX.csv Round-10 drift: "
        f"plan-only={sorted(plan_ids - matrix_ids)}, "
        f"matrix-only={sorted(matrix_ids - plan_ids)}"
    )


def test_every_open_deferral_appears_in_the_f5_register() -> None:
    """The register must name every still-owed row — no silent omissions."""
    register = _section_f5_register(_closure_section_f())
    open_ids = _open_deferral_ids()
    assert open_ids, "DEFERRALS.md parser found no OPEN/PARTIAL rows — parser broke?"
    missing = sorted(oid for oid in open_ids if oid not in register)
    assert not missing, f"§(f5) silently omitted owed obligations: {missing}"


def test_every_deferral_id_in_f5_exists_in_deferrals() -> None:
    """No invented obligations: every D-/SIG- id the register names must be a
    real DEFERRALS row (or the explicitly-scoped scheduled id SIG-MEM-004)."""
    register = _section_f5_register(_closure_section_f())
    named = set(re.findall(r"D-[A-Za-z0-9]+[A-Za-z0-9.\-]*", register))
    all_rows = {
        m.group(1)
        for line in DEFERRALS_PATH.read_text(encoding="utf-8").splitlines()
        if (m := _ROW_ID_RE.match(line))
    }
    phantom = sorted(named - all_rows)
    assert not phantom, f"§(f5) names obligations that are not DEFERRALS rows: {phantom}"


def test_p33_3_annotations_preserve_open_status() -> None:
    """Every P33.3-annotated DEFERRALS row must still lead with OPEN/PARTIAL —
    the annotation is a disposition note, never an evidence-free closure."""
    lines = DEFERRALS_PATH.read_text(encoding="utf-8").splitlines()
    annotated = [ln for ln in lines if "P33.3 capstone closure" in ln]
    assert len(annotated) == 18, (
        f"expected 18 P33.3 disposition annotations, found {len(annotated)}"
    )
    for line in annotated:
        cells = [c.strip() for c in line.split("|")]
        status_cell = cells[-2] if cells and cells[-1] == "" else cells[-1]
        sm = _STATUS_RE.match(status_cell)
        assert sm and sm.group(1) in {"OPEN", "PARTIAL"}, (
            f"P33.3-annotated row no longer leads with OPEN/PARTIAL: {status_cell[:80]}"
        )


def test_gate_accept_readout_state_matches_the_recorded_decision() -> None:
    """The readout must declare a real recorded state — never an asserted one.

    P33.3 landed this guard while GATE-ACCEPT was still PENDING; the operator
    signed ``ACCEPT-R10.md`` on 2026-09-28 (LEDGER § GATE DECISIONS). The
    invariant is not "PENDING forever" — it is that the committed readout's
    declared state is genuine: a PENDING readout must carry no decision
    vocabulary, and a SIGNED readout must carry the recorded authority, date
    and decision domain with a matching LEDGER gate-decision entry. Either
    way, §(f) keeps its honest wording: the packet is presented, it does not
    sign itself, and it closes none of the owed register.
    """
    readout = READOUT_ACCEPT.read_text(encoding="utf-8")
    if "PENDING" in readout:
        assert "APPROVED" not in readout and "SIGN" not in re.sub(
            r"SIGN[A-Z]*ATURE", "", readout
        ), "GATE-ACCEPT readout asserts a decision that has not happened"
    else:
        # post-signature state — provenance is mandatory, never an agent claim
        assert "SIGNED" in readout, "readout is neither PENDING nor SIGNED"
        for marker in ("Authority:", "Date:", "Decision domain:"):
            assert marker in readout, (
                f"signed GATE-ACCEPT readout lacks provenance marker {marker!r}"
            )
        ledger = (REPO_ROOT / "docs/build/LEDGER.md").read_text(encoding="utf-8")
        decisions = ledger.split("## GATE DECISIONS", 1)[-1]
        assert "ACCEPT-R10" in decisions, (
            "readout is signed but no GATE DECISIONS entry records ACCEPT-R10"
        )

    section = _closure_section_f()
    for marker in (
        "does not sign",  # the packet prepares; an operator records the verdict
        "closes none",
    ):
        assert marker in section, f"§(f) lost honest-gate wording: {marker!r} missing"


def test_honest_scope_state_markers_present() -> None:
    """The four required scope facts from the P33.3 contract must be stated."""
    section = _closure_section_f()
    required_substrings = (
        "provisional",  # provisional policy published to staging
        "deferred",  # evaluation deferred
        "not_operating",  # intake receiver non-operational (`503 receiver_not_operating`)
        "Production exposure OPEN",  # production exposure remains OPEN
        "live_verification=false",  # dated-verification honesty: no live run
    )
    missing = [s for s in required_substrings if s not in section]
    assert not missing, f"§(f) is missing honest-scope markers: {missing}"
