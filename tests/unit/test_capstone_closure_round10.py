# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P33.3 — Round-10 capstone-closure register guard.

The acceptance packet (``docs/build/CAPSTONE_CLOSURE.md`` §(f)) is what
GATE-ACCEPT reviews.  This test is the deterministic guarantee that the packet
cannot silently drop an owed obligation, drop a Round-10 requirement id, or
overclaim a gate/human/live row as closed.  Every assertion fails if the
register regresses — remove a row from §(f5), or close an annotated row without
recorded evidence, and this suite goes red.

Ticket: P33.3 (manifest row 194; engineering-only, ``live_verification=false``,
owns no requirement ids).  The test derives its expectations from committed
sources of truth — never from the packet itself — so the packet can only pass by
covering every owed row:

* the 38 Round-10 requirement ids come from ``PLAN.json`` — the frozen plan of
  a closed round — and each must stay an owned ``COVERAGE_MATRIX.csv`` row;
* the obligation set the packet had to cover is the register **as it stood at
  the packet commit** (``e8bc0179``): a frozen snapshot, so later legitimate
  register changes (a closure, a new Round-11 deferral) never turn this red
  while an omission from the packet still does (BM-TEST-01; SEED-03 / PKG-02
  ED-07);
* a P33.3-annotated row may close only with a dated terminal token **and** an
  evidence-backed obligation-event transition — never by editing the cell;
* gate state comes from the committed readouts (``docs/build/readouts/``) and
  the LEDGER's ``## GATE DECISIONS`` section.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "docs/build/planning/2026-09-25-six-streams/PLAN.json"
COVERAGE_MATRIX_PATH = REPO_ROOT / "docs/build/COVERAGE_MATRIX.csv"
CLOSURE_PATH = REPO_ROOT / "docs/build/CAPSTONE_CLOSURE.md"
DEFERRALS_PATH = REPO_ROOT / "docs/tickets/DEFERRALS.md"
EVENTS_PATH = REPO_ROOT / "docs/build/reports/obligations/events.jsonl"
LEDGER_PATH = REPO_ROOT / "docs/build/LEDGER.md"
READOUT_ACCEPT = REPO_ROOT / "docs/build/readouts/ACCEPT-R10.md"

# ---------------------------------------------------------------------------
# frozen snapshot — the register at the P33.3 packet commit
# ---------------------------------------------------------------------------

#: The packet commit that wrote §(f5) and the 18 disposition annotations.
SNAPSHOT_COMMIT = "e8bc0179720e6b52498d0db63df7b46c357c226f"

#: Every DEFERRALS row whose status cell led OPEN/PARTIAL at SNAPSHOT_COMMIT
#: (36 = 32 OPEN + 4 PARTIAL, the count §(f5) itself states). Immutable: it is
#: the set the packet had to cover, not the register's current state.
SNAPSHOT_OWED = frozenset(
    {
        "D-FEDERAL.1-1",
        "D-JURIS.2-1",
        "D-P21.3-2",
        "D-P21.5-1",
        "D-P21.7-1",
        "D-P30.2b-1",
        "D-P30.2b-2",
        "D-P31.4-1",
        "D-P32.10a-1",
        "D-P32.16-1",
        "D-P32.16a-1",
        "D-P32.18-1",
        "D-P32.19-1",
        "D-P32.20-1",
        "D-P32.21-1",
        "D-P32.23a-1",
        "D-P32.3-1",
        "D-R10-HUMAN-1",
        "D-R10-LIVE-1",
        "D-R10-MEMORY-1",
        "D-R10-PUBLISH-1",
        "D-R10-SOURCES-1",
        "D-R10-USERS-1",
        "D-R6.1-EVAL",
        "D-R7.1-AUTH",
        "D-R7.2-SEND",
        "D-SOURCES.12-1",
        "D-SOURCES.2-2",
        "D-SOURCES.7-1",
        "D-SOURCES.7-2",
        "D-SOURCES.8-1",
        "D-SOURCES.8-2",
        "D-SOURCES.9-1",
        "D-SOURCES.9-2",
        "D-SOURCES.9-3",
        "D-SOURCES.9-4",
    }
)

#: The rows P33.3 annotated "P33.3 capstone closure … stays OPEN" at SNAPSHOT_COMMIT.
SNAPSHOT_ANNOTATED = frozenset(
    {
        "D-R6.1-EVAL",
        "D-P30.2b-1",
        "D-P30.2b-2",
        "D-R10-HUMAN-1",
        "D-R10-SOURCES-1",
        "D-R10-LIVE-1",
        "D-R10-PUBLISH-1",
        "D-R10-MEMORY-1",
        "D-R10-USERS-1",
        "D-P32.3-1",
        "D-P32.10a-1",
        "D-P32.16-1",
        "D-P32.16a-1",
        "D-P32.18-1",
        "D-P32.19-1",
        "D-P32.20-1",
        "D-P32.21-1",
        "D-P32.23a-1",
    }
)

# ---------------------------------------------------------------------------
# parsers (kept tiny on purpose — they read committed formats, nothing else)
# ---------------------------------------------------------------------------

_ROW_ID_RE = re.compile(r"^\| (D-[A-Za-z0-9]+[A-Za-z0-9.\-]*|SIG-[A-Z]+-[0-9]+) \|")
_STATUS_RE = re.compile(r"^\s*(OPEN|PARTIAL|DONE|CLOSED|WONTFIX|DISCHARGED|SKIPPED)\b")
_OWED = frozenset({"OPEN", "PARTIAL"})
_TERMINAL = frozenset({"DONE", "WONTFIX", "ACCEPTED-SKELETON"})


def _round10_requirement_ids() -> set[str]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    ids = set(plan["requirements"].keys())
    # PLAN.json is the frozen 2026-09-25 plan of a closed round (an immutable
    # artifact), so its size is a fact of that file, not a living count.
    assert len(ids) == 38, f"PLAN.json requirement set drifted: {len(ids)} ids"
    return ids


def _owners(row: dict[str, str]) -> list[str]:
    return [t.strip() for t in row["owning_tickets"].split(";") if t.strip() not in ("", "—")]


def _coverage_rows() -> dict[str, dict[str, str]]:
    with COVERAGE_MATRIX_PATH.open(newline="", encoding="utf-8") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


def _status_cell(line: str) -> str:
    cells = [c.strip() for c in line.split("|")]
    return cells[-2] if cells and cells[-1] == "" else cells[-1]


def _deferral_rows(text: str) -> dict[str, str]:
    """id -> status cell for every DEFERRALS row."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = _ROW_ID_RE.match(line)
        if m:
            out.setdefault(m.group(1), _status_cell(line))
    return out


def _lead(status_cell: str) -> str:
    words = status_cell.replace("*", " ").split()
    return words[0].upper() if words else ""


def _owed_ids(text: str) -> set[str]:
    """Ids whose status cell leads OPEN/PARTIAL (the P33.3 parser convention)."""
    owed: set[str] = set()
    for oid, cell in _deferral_rows(text).items():
        sm = _STATUS_RE.match(cell)
        if sm and sm.group(1) in _OWED:
            owed.add(oid)
    return owed


def _ledger_section(title: str) -> str:
    """The body of one ``## <title>`` LEDGER section, up to the next ``## `` heading."""
    text = LEDGER_PATH.read_text(encoding="utf-8")
    head = re.search(rf"(?m)^## {re.escape(title)}[^\n]*\n", text)
    assert head, f"LEDGER.md has no '## {title}' section"
    rest = text[head.end() :]
    nxt = re.search(r"(?m)^## ", rest)
    return rest[: nxt.start()] if nxt else rest


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


def test_plan_requirements_stay_owned_rows_of_the_coverage_matrix() -> None:
    """Every Round-10 plan id keeps a coverage-matrix row with a named owner — a
    later round may re-home or re-verdict it, but may not drop or orphan it — and
    a closed Round-10 ticket (P32*/P33*) owns no id outside the Round-10 plan."""
    plan_ids = _round10_requirement_ids()
    rows = _coverage_rows()
    missing = sorted(plan_ids - rows.keys())
    assert not missing, f"COVERAGE_MATRIX.csv dropped Round-10 plan ids: {missing}"
    orphaned = sorted(rid for rid in plan_ids if not _owners(rows[rid]))
    assert not orphaned, f"Round-10 plan ids with no owning ticket: {orphaned}"
    stray = sorted(
        rid
        for rid, row in rows.items()
        if any(t.startswith(("P32", "P33")) for t in _owners(row)) and rid not in plan_ids
    )
    assert not stray, f"Round-10 tickets own ids outside PLAN.json: {stray}"


def test_every_obligation_owed_at_the_packet_commit_appears_in_the_f5_register() -> None:
    """The register named every row that was owed when it was written — no
    silent omissions — and none of those rows has since been deleted (the
    register is append-only). Rows added after the packet are not its scope."""
    register = _section_f5_register(_closure_section_f())
    missing = sorted(oid for oid in SNAPSHOT_OWED if oid not in register)
    assert not missing, f"§(f5) silently omitted owed obligations: {missing}"
    rows = _deferral_rows(DEFERRALS_PATH.read_text(encoding="utf-8"))
    deleted = sorted(SNAPSHOT_OWED - rows.keys())
    assert not deleted, f"DEFERRALS.md lost rows the packet registered: {deleted}"


def test_snapshot_matches_the_register_at_the_packet_commit() -> None:
    """Provenance of the frozen snapshot: recomputed from the packet commit when
    its objects are available (a shallow clone skips; the constants still bind)."""
    probe = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{SNAPSHOT_COMMIT}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        pytest.skip(f"packet commit {SNAPSHOT_COMMIT[:8]} not in this clone")
    text = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{SNAPSHOT_COMMIT}:docs/tickets/DEFERRALS.md"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert _owed_ids(text) == SNAPSHOT_OWED
    annotated = {
        m.group(1)
        for line in text.splitlines()
        if "P33.3 capstone closure" in line and (m := _ROW_ID_RE.match(line))
    }
    assert annotated == SNAPSHOT_ANNOTATED


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


def test_p33_3_annotated_rows_close_only_with_recorded_evidence() -> None:
    """A P33.3 annotation is a disposition note, never an evidence-free closure:
    each annotated row still exists and either stays owed (OPEN/PARTIAL) or leads
    a terminal status that carries a dated token and whose obligation-event
    chain head is a transition to that status citing evidence outside the
    register. Closing a row legitimately therefore never turns this red."""
    rows = _deferral_rows(DEFERRALS_PATH.read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for oid in sorted(SNAPSHOT_ANNOTATED):
        assert oid in rows, f"P33.3-annotated row {oid} was deleted from DEFERRALS.md"
        cell = rows[oid]
        lead = _lead(cell)
        if lead in _OWED:
            continue
        assert lead in _TERMINAL, f"{oid} leads {lead!r}: neither owed nor a terminal status"
        assert re.search(rf"\b{re.escape(lead)}\s+20\d\d-\d\d-\d\d", cell), (
            f"{oid} closed as {lead} without a dated closure token: {cell[:80]}"
        )
        chain = sorted(
            (e for e in events if e.get("obligation_id") == oid),
            key=lambda e: e.get("seq", -1),
        )
        head = chain[-1] if chain else {}
        assert head.get("kind") == "transition" and head.get("to_status") == lead, (
            f"{oid} leads {lead} but no obligation-event transition records it"
        )
        evidence = [
            ref
            for ref in head.get("evidence_refs", [])
            if not ref.startswith("docs/tickets/") and (REPO_ROOT / ref.split("#", 1)[0]).exists()
        ]
        assert evidence, f"{oid}'s closing transition cites no evidence outside the register"


@pytest.mark.living_record_invariant("gate-readout-state-vocabulary")
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
    # P34.27 appends a verbatim `## Readout history` block quoting the pending
    # template (`> Status: PENDING…`) — history is not the declared state, so
    # the declaration is judged on the first *unquoted* Status: line.
    declared = next(
        (
            line
            for line in readout.split("\n")
            if re.match(r"\s*Status:\s*\S", line) and not line.lstrip().startswith(">")
        ),
        "",
    )
    if "PENDING" in declared:
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
        # Scoped to the GATE DECISIONS section itself (a missing section fails
        # loudly) — never "anything after the heading", which also matched the
        # PHASE LOG and passed vacuously when the decision rows were absent.
        decisions = _ledger_section("GATE DECISIONS")
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
