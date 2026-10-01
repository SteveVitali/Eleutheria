#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Adversarial fixtures for ``docs/build/tools/current_projection.py`` (P32.7,
SIG-MEM-002): the deterministic current view lists every owed obligation with
owner+landing, preserves (never synthesizes) inconsistencies, detects stale input
digests, and spills oversized views without dropping a single obligation.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

from support import REPO_ROOT

TOOLS = REPO_ROOT / "docs" / "build" / "tools"


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


current_projection = _load_tool("current_projection")
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
chainTip: devin/test
benchmarkSet: —
autonomy: checkpoint
mergePolicy: NONE
round: 9
updatedAt: 2026-01-05"""

MANIFEST = """# manifest

companions: _TEMPLATE.md

## The chain

| # | Ticket file | Phase | Scope |
|---|---|---|---|
| 1 | `P00.1__a.md` | 0 | a |
| 2 | `P00.2__b.md` | 0 | b |
| 3 | `161_P9.1__c.md` | 9 | c |
"""


def _row(oid: str, kind: str, status: str) -> str:
    return f"| {oid} | {kind} | item | deferred | unblock | verify | proxy | {status} |\n"


DEFERRALS = (
    "# deferrals\n\n"
    "| id | kind | item | why deferred | unblocked by | how to verify | proxy now | status |\n"
    "|---|---|---|---|---|---|---|---|\n"
    + _row("D-T9.1-1", "V", "OPEN cites BL-001")
    + _row("D-T9.1-2", "P", "OPEN cites BL-001")
    + _row(
        "D-P21.4-3",
        "P",
        "DONE 2026-10-14 — reconciled by event (was OPEN (BL-034)); "
        "records DONE 2026-09-16 go-public executed",
    )
    + _row("D-T9.1-4", "F", "DONE 2026-01-05 verified")
)

SPEC = "**SIG-TST-001 (MUST).** One requirement. See ADR-001.\n"
# The Round-11 matrix header: twelve P19.2 columns + the four build-memory 0.5.0 columns
# (ADR-150 D2; check_coverage_matrix.HEADER, SEED-15).
COVERAGE = (
    "id,level,spec_section,class,verdict,evidence,owning_tickets,tests,adrs,risk_rows,routing,note,"
    "required_domain,achieved_domain,owed_legs,accepted_scope\n"
    "SIG-TST-001,MUST,§1,covered+tested,MET,e,P00.1,t,ADR-001,—,—,n,,,,\n"
)

FUNNEL = """# evidence domains + funnel

## 1. Evidence domains

| domain | definition | typical instruments | can never establish |
|---|---|---|---|
| `fixture` | committed fixtures | pytest | a live fetch |
| `implementation` | landed code | make check | the running stack |
| `composed-db` | docker suites | make test-db | hosted |
| `hosted` | deployed stack | probes | public availability |
| `public` | reachable surface | fetches | — |

## 2. Source funnel — named units

## 3. Baseline values

| unit | value | domain · date · evidence |
|---|---|---|
| discovered | 10 sources | implementation · 2026-01-01 · sources.toml |
| published | export x-1 | public · recorded 2026-01-02 |
"""

RECONCILED = json.dumps(
    {
        "schema": "reconciled-conflicts/1",
        "documented": [
            {
                "check": "manifest/duplicate-file",
                "obligation": "P00.2__b.md",
                "pointer": "docs/build/reports/p32.1-baseline/RECONCILIATION.md",
            }
        ],
    }
)

GOVERNING = json.dumps(
    {
        "schema": "governing-adrs/1",
        "adrs": [
            {"id": "ADR-001", "file": "docs/adr/ADR-001-x.md", "scope": "fixture adr"},
        ],
    }
)

ASSESSMENTS = (
    json.dumps(
        {
            "schema": "coverage-assessment/1",
            "assessment_id": "a1",
            "requirement_id": "SIG-TST-001",
            "verdict": "MET",
            "domain": "implementation",
            "code_revision": "deadbeef",
            "evidence_refs": ["docs/build/runs/P00.1.md"],
            "limitations": "—",
            "assessor": "test",
            "assessed_at": "2026-10-14",
            "supersedes": None,
            "seq": 0,
        }
    )
    + "\n"
)


def _base_files(n_extra: int = 0) -> dict[str, str]:
    deferrals = DEFERRALS + "".join(
        _row(f"D-X{n:03d}-1", "V", "OPEN cites BL-001") for n in range(n_extra)
    )
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
        "docs/build/BACKLOG.csv": "id,item,status\nBL-001,x,open\n",
        "docs/tickets/00_MANIFEST.md": MANIFEST,
        "docs/tickets/_TEMPLATE.md": "# template\n",
        "docs/tickets/DEFERRALS.md": deferrals,
        "docs/tickets/P00.1__a.md": "- **Depends on:** none\n",
        "docs/tickets/P00.2__b.md": "- **Depends on:** P00.1\n",
        "docs/tickets/161_P9.1__c.md": "- **Depends on:** P00.2\n",
        "docs/2_canonical_design_spec.md": SPEC,
        "docs/adr/ADR-001-x.md": "# ADR-001\n\n## Revisit trigger\n\n- t\n",
        "docs/adr/README.md": "| [ADR-001](ADR-001-x.md) | t |\n",
        "docs/build/reports/PUBLICATION_CHECKLIST.md": "# checklist\n",
        "docs/build/reports/p32.1-baseline/EVIDENCE_DOMAINS_AND_SOURCE_FUNNEL.md": FUNNEL,
        "docs/build/reports/p32.1-baseline/RECONCILIATION.md": "# recon\n",
        "docs/build/reports/obligations/reconciliations.json": RECONCILED,
        "docs/build/reports/obligations/governing_adrs.json": GOVERNING,
        "docs/build/reports/obligations/coverage_assessments.jsonl": ASSESSMENTS,
        "docs/build/reports/obligations/MIGRATION.md": "# migration\n",
    }
    return files


def _tree(
    root: pathlib.Path,
    overrides: dict[str, str] | None = None,
    n_extra: int = 0,
    migrate: bool = True,
) -> pathlib.Path:
    files = _base_files(n_extra)
    files.update(overrides or {})
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    if migrate:
        assert obligation_events.migrate(root, "2026-10-14", "deadbeef") == 0
    return root


def _out(root: pathlib.Path) -> pathlib.Path:
    return root / "docs" / "build" / "reports" / "current"


# ── generation + invariants ──────────────────────────────────────────────────


def test_generate_lists_every_owed_with_owner_landing(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    proj = json.loads((_out(root) / "current.json").read_text())
    assert proj["schema"] == "current-projection/1"
    by_id = {o["id"]: o for o in proj["obligations"]}
    assert set(by_id) == {"D-T9.1-1", "D-T9.1-2", "D-P21.4-3", "D-T9.1-4"}
    owed = [o for o in proj["obligations"] if o["status"] in obligation_events.OWED_STATUSES]
    # every owed obligation appears with owner + landing + verification pointer
    for o in owed:
        assert o["owner"] not in ("", "—"), o
        assert o["landing"] not in ("", "—"), o
        assert o["verify"], o
    # the reconciled conflict row: old value preserved on the anchor, head DONE
    rec = by_id["D-P21.4-3"]
    assert rec["status"] == "DONE"
    assert rec["events"][0]["anchor"]["interpretation"] == "reconciled"
    assert rec["events"][0]["anchor"]["row_sha256"]
    # reconciled-classification counters
    assert proj["counts"]["reconciled_by_event"] == 1
    assert proj["known_inconsistencies"] == []


def test_current_md_within_budget(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    md = _out(root) / "CURRENT.md"
    assert len(md.read_text().splitlines()) <= 250
    assert len(md.read_bytes()) <= 20 * 1024
    # and every owed obligation is still present in the main view (small tree)
    for oid in ("D-T9.1-1", "D-T9.1-2"):
        assert oid in md.read_text()


def test_projection_embeds_transition_history(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    proj = json.loads((_out(root) / "current.json").read_text())
    for o in proj["obligations"]:
        assert o["events"], o["id"]
        assert o["status_source"].startswith("event-head")


def test_projection_deterministic(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    first = (_out(root) / "current.json").read_bytes()
    first_md = (_out(root) / "CURRENT.md").read_bytes()
    assert current_projection.generate(root, _out(root)) == 0
    assert (_out(root) / "current.json").read_bytes() == first
    assert (_out(root) / "CURRENT.md").read_bytes() == first_md


def test_generation_writes_no_wallclock_in_payload(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    proj = json.loads((_out(root) / "current.json").read_text())
    assert "generated_at" not in proj
    receipt = json.loads((_out(root) / "receipt.json").read_text())
    assert receipt["generated_at"]  # wall-clock lives only in the receipt


def test_verify_green_then_stale_digest_detected(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    out = _out(root)
    assert current_projection.generate(root, out) == 0
    assert current_projection.verify(root, out) == 0
    # mutate an input — the recorded digest goes stale and must be reported
    deferrals = root / "docs" / "tickets" / "DEFERRALS.md"
    deferrals.write_text(deferrals.read_text() + "\n<!-- touched -->\n")
    assert current_projection.verify(root, out) == 1


def test_new_input_detected(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    out = _out(root)
    assert current_projection.generate(root, out) == 0
    new_ticket = root / "docs" / "tickets" / "P00.9__new.md"
    new_ticket.write_text("- **Depends on:** none\n")
    assert current_projection.verify(root, out) == 1


def test_manifest_enumerates_and_excludes_outputs(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    out = _out(root)
    assert current_projection.generate(root, out) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    paths = {e["path"] for e in manifest["inputs"]}
    assert "docs/tickets/DEFERRALS.md" in paths
    assert "docs/build/reports/obligations/events.jsonl" in paths
    # generated outputs are never inputs (acyclic by construction)
    assert not any(p.startswith("docs/build/reports/current/") for p in paths)
    for e in manifest["inputs"]:
        digest = hashlib.sha256((root / e["path"]).read_bytes()).hexdigest()
        assert e["sha256"] == digest


def test_manifest_rejects_output_as_input(tmp_path: pathlib.Path) -> None:
    """A manifest that named a generated output as an input would be cyclic —
    enumeration must never produce one."""
    root = _tree(tmp_path)
    out = _out(root)
    current_projection.generate(root, out)
    inputs = current_projection.enumerate_inputs(root, out)
    assert not any("reports/current" in p for p in inputs)


def test_known_inconsistency_preserved_bounded_and_nonzero(tmp_path: pathlib.Path) -> None:
    """A new conflict with no recorded reconciliation is not synthesized — it
    lands in known_inconsistencies and generation exits nonzero."""
    root = _tree(tmp_path)
    conflict_row = (
        "| D-T9.1-9 | V | unreconciled thing | deferred | an engineering run | "
        "`pytest u` | proxy | OPEN cites BL-001 — prose says DONE 2026-03-01 |\n"
    )
    deferrals = root / "docs" / "tickets" / "DEFERRALS.md"
    deferrals.write_text(deferrals.read_text() + conflict_row)
    assert obligation_events.migrate(root, "2026-10-14", "deadbeef") == 0
    assert current_projection.generate(root, _out(root)) == 1
    proj = json.loads((_out(root) / "current.json").read_text())
    hits = [d for d in proj["known_inconsistencies"] if d["obligation"] == "D-T9.1-9"]
    assert hits and proj["incomplete"] is True


def test_documented_conflict_classified(tmp_path: pathlib.Path) -> None:
    """A conflict listed in reconciliations.json is reconciled-by-documentation,
    not a known inconsistency."""
    dup_manifest = MANIFEST + "| 4 | `P00.2__b.md` | 21 | Lane-B pointer |\n"
    root = _tree(tmp_path, {"docs/tickets/00_MANIFEST.md": dup_manifest})
    assert current_projection.generate(root, _out(root)) == 0
    proj = json.loads((_out(root) / "current.json").read_text())
    assert proj["reconciled"]["by_documentation"]
    assert proj["reconciled"]["by_documentation"][0]["check"] == "manifest/duplicate-file"
    assert proj["known_inconsistencies"] == []


def test_csv_assessments_labelled_historical(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    proj = json.loads((_out(root) / "current.json").read_text())
    hist = proj["coverage"]["historical_csv"]
    assert hist["label"].startswith("historical/csv")
    assert hist["by_requirement"]["SIG-TST-001"]["verdict"] == "MET"
    assert hist["by_requirement"]["SIG-TST-001"]["label"] == "historical/csv"


def test_oversized_view_spills_without_dropping_obligations(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path, n_extra=300)
    out = _out(root)
    assert current_projection.generate(root, out) == 0
    md = (out / "CURRENT.md").read_text()
    assert len(md.splitlines()) <= 250
    assert len(md.encode()) <= 20 * 1024
    spill_pages = [p for p in out.iterdir() if p.name.startswith("obligations")]
    assert spill_pages, "expected link-out pages for 300+ owed rows"
    everything = md + "".join(p.read_text() for p in spill_pages)
    for n in range(300):
        assert f"D-X{n:03d}-1" in everything, f"obligation D-X{n:03d}-1 dropped"
    # the JSON projection always carries everything regardless of the view
    proj = json.loads((out / "current.json").read_text())
    assert len(proj["obligations"]) == 304


def test_projection_never_writes_control_state(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    ledger = (root / "docs" / "build" / "LEDGER.md").read_bytes()
    deferrals = (root / "docs" / "tickets" / "DEFERRALS.md").read_bytes()
    coverage = (root / "docs" / "build" / "COVERAGE_MATRIX.csv").read_bytes()
    assert current_projection.generate(root, _out(root)) == 0
    assert (root / "docs" / "build" / "LEDGER.md").read_bytes() == ledger
    assert (root / "docs" / "tickets" / "DEFERRALS.md").read_bytes() == deferrals
    assert (root / "docs" / "build" / "COVERAGE_MATRIX.csv").read_bytes() == coverage


def test_control_state_surfaces_advisory(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    proj = json.loads((_out(root) / "current.json").read_text())
    assert proj["control"]["nextTicket"] == "P9.1"
    assert "advisory" in proj["authority"]
    assert "LEDGER.md" in proj["authority"]


#: The Round-11 seed shape of CURRENT STATE (B3 §3.4; layout BM-LEDGER-02/-08):
#: values only, `harness` in its slot, an archive pointer comment in the section.
KEYS_R11 = (
    KEYS.replace("projectStatus: IN_PROGRESS", "projectStatus: PAUSED")
    .replace("round: 9", "round: 11\nharness: devin-desktop/swe-2-high/subagent")
    .replace("updatedAt: 2026-01-05", "updatedAt: 2026-01-05T00:00:00Z")
)


def _r11_tree(root: pathlib.Path) -> pathlib.Path:
    ledger = (
        "## CURRENT STATE\n\n```\n"
        + KEYS_R11
        + "\n```\n<!-- Rounds 1-10 head archived; sha256 pointer. -->\n\n"
        + "## PHASE LOG — Round 11\n\n"
        + "- 2026-01-01 — P00.1 a done (PR #1)\n- 2026-01-02 — P00.2 b done (PR #2)\n"
    )
    return _tree(root, {"docs/build/LEDGER.md": ledger})


def test_round11_values_only_control_state_projects(tmp_path: pathlib.Path) -> None:
    """The projection reads the seed's values-only CURRENT STATE — including the
    new `harness` key — without leaking the archive pointer into a value."""
    root = _r11_tree(tmp_path)
    current_projection.generate(root, _out(root))  # exit code: asserted by the next test
    control = json.loads((_out(root) / "current.json").read_text())["control"]
    assert control["projectStatus"] == "PAUSED"
    assert control["round"] == "11"
    assert control["harness"] == "devin-desktop/swe-2-high/subagent"
    assert control["updatedAt"] == "2026-01-05T00:00:00Z"
    md = (_out(root) / "CURRENT.md").read_text()
    assert "projectStatus `PAUSED` · round `11`" in md


def test_round11_values_only_ledger_generates_and_verifies_clean(tmp_path: pathlib.Path) -> None:
    root = _r11_tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    assert current_projection.verify(root, _out(root)) == 0


def test_evidence_domains_and_releases_recorded_not_measured(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert current_projection.generate(root, _out(root)) == 0
    proj = json.loads((_out(root) / "current.json").read_text())
    domains = {d["domain"] for d in proj["evidence_domains"]}
    assert domains == {"fixture", "implementation", "composed-db", "hosted", "public"}
    assert "not recorded" in proj["releases"]["database_run_ids"]
    assert proj["source_funnel"][0]["unit"] == "discovered"
