#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Adversarial fixtures for ``docs/build/tools/obligation_events.py`` (P32.7, SIG-MEM-002).

The append-only transition layer must reject duplicate events, transitions without
predecessors, competing heads, evidence-free transitions, register-only evidence and
cells that disagree with the event chain — and the coverage-assessment chain must
reject competing heads, missing supersedes, planning-document METs and, critically,
a narrower-domain MET papering over a wider-domain failure.
"""

from __future__ import annotations

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


obligation_events = _load_tool("obligation_events")


def _row(oid: str, kind: str, status: str) -> str:
    return f"| {oid} | {kind} | item | deferred | unblock | verify | proxy | {status} |\n"


DEFERRALS = (
    "# deferrals\n\n"
    "| id | kind | item | why deferred | unblocked by | how to verify | proxy now | status |\n"
    "|---|---|---|---|---|---|---|---|\n"
    + _row("D-T9.1-1", "V", "OPEN cites BL-001")
    + _row("D-T9.1-2", "F", "DONE 2026-01-05 verified")
    + _row("D-T9.1-3", "P", "OPEN cites BL-001")
    + _row("D-T9.1-4", "V", "OPEN cites BL-001 — prose says DONE 2026-02-01 at P9.1")
)

SPEC = (
    "**SIG-TST-001 (MUST).** One.\n**SIG-TST-002 (MUST).** Two.\n**SIG-MEM-002 (MUST).** Memory.\n"
)

BASE_FILES: dict[str, str] = {
    "docs/tickets/DEFERRALS.md": DEFERRALS,
    "docs/2_canonical_design_spec.md": SPEC,
    "docs/build/runs/P9.1.md": "# run\n",
    "docs/build/reports/REPORT.md": "# report\n",
    "docs/build/planning/plan.md": "# plan\n",
}


def _tree(root: pathlib.Path, overrides: dict[str, str] | None = None) -> pathlib.Path:
    files = dict(BASE_FILES)
    files.update(overrides or {})
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def _anchors(root: pathlib.Path) -> list[dict]:
    events, _ = obligation_events.build_anchors(root, "2026-09-30", "deadbeef")
    return events


def _checks(diags: list[dict]) -> set[str]:
    return {d["check"] for d in diags}


def _transition(
    oid: str,
    seq: int,
    prev: str | None,
    to: str,
    evidence: list[str] | None = None,
    **kw,
) -> dict:
    return {
        "schema": "obligation-event/1",
        "event_id": f"{oid}:e{seq}",
        "kind": "transition",
        "obligation_id": oid,
        "seq": seq,
        "expected_previous_event": prev,
        "from_status": "OPEN",
        "to_status": to,
        "ticket_id": "P9.1",
        "owner": "—",
        "landing": "—",
        "backlog_home": "BL-001",
        "evidence_refs": evidence if evidence is not None else ["docs/build/runs/P9.1.md"],
        "observed_at": "2026-09-30",
        "recorded_at": "2026-09-30",
        "source_commit": "deadbeef",
        "reason": "test transition",
        **kw,
    }


def _assessment(
    aid: str,
    req: str,
    verdict: str,
    domain: str,
    refs: list[str],
    seq: int = 0,
    supersedes=None,
) -> dict:
    return {
        "schema": "coverage-assessment/1",
        "assessment_id": aid,
        "requirement_id": req,
        "verdict": verdict,
        "domain": domain,
        "code_revision": "deadbeef",
        "evidence_refs": refs,
        "limitations": "—",
        "assessor": "test",
        "assessed_at": "2026-10-14",  # future-ok: synthetic: fixture ledger
        "supersedes": supersedes,
        "seq": seq,
    }


# ── migration anchors ─────────────────────────────────────────────────────────


def test_migrate_anchors_every_obligation(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root)
    assert [e["event_id"] for e in events] == [
        "D-T9.1-1:e0",
        "D-T9.1-2:e0",
        "D-T9.1-3:e0",
        "D-T9.1-4:e0",
    ]
    assert all(e["kind"] == "migration" and e["seq"] == 0 for e in events)
    assert all(e["expected_previous_event"] is None for e in events)


def test_migration_is_deterministic(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    a = _anchors(root)
    b = _anchors(root)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_anchor_preserves_raw_digest_and_parser_status(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root)
    rows = {r["id"]: r for r in obligation_events.parse_obligation_rows(root)}
    for e in events:
        row = rows[e["obligation_id"]]
        assert e["anchor"]["row_sha256"] == obligation_events._sha256_text(row["raw_line"])
        assert e["anchor"]["parser_status"] == row["status"]
        assert e["anchor"]["row_line"] == row["line"]


def test_unambiguous_rows_keep_parser_status(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root)
    by_id = {e["obligation_id"]: e for e in events}
    assert by_id["D-T9.1-1"]["to_status"] == "OPEN"
    assert by_id["D-T9.1-1"]["anchor"]["interpretation"] == "preserved"
    assert by_id["D-T9.1-2"]["to_status"] == "DONE"


def test_ambiguous_conflict_stays_open_with_owner(tmp_path: pathlib.Path) -> None:
    """A status-conflict row with no recorded reconciliation keeps its raw
    (owed) status and surfaces as a conflict — ambiguous ⇒ OPEN, never picked."""
    root = _tree(tmp_path)
    events = _anchors(root)
    by_id = {e["obligation_id"]: e for e in events}
    conflicted = by_id["D-T9.1-4"]
    assert conflicted["anchor"]["interpretation"] == "unreconciled-conflict"
    assert conflicted["to_status"] == "OPEN"  # the parser status is owed, not DONE
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/unreconciled-conflict"]
    assert [d["obligation"] for d in hits] == ["D-T9.1-4"]
    assert hits[0]["severity"] == "conflict"


def test_owed_anchors_carry_owner_and_landing(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root)
    for e in events:
        if e["to_status"] in obligation_events.OWED_STATUSES:
            assert e["owner"] not in ("", "—"), e
            assert e["landing"] not in ("", "—"), e


def test_check_green_on_consistent_fixture(tmp_path: pathlib.Path) -> None:
    """Every obligation anchored, cells match heads; the one unreconciled
    conflict row produces its conflict diag — remove it and the chain is clean."""
    root = _tree(tmp_path)
    events = _anchors(root)
    diags = obligation_events.check_event_chain(root, events)
    assert _checks(diags) == {"events/unreconciled-conflict"}, diags


# ── chain validation ──────────────────────────────────────────────────────────


def test_duplicate_event_id_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root) + [_anchors(root)[0]]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/duplicate-id"]
    assert hits and hits[0]["obligation"] == "D-T9.1-1"


def test_transition_without_anchor_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = [e for e in _anchors(root) if e["obligation_id"] != "D-T9.1-3"]
    events.append(_transition("D-T9.1-3", 1, None, "DONE"))
    diags = obligation_events.check_event_chain(root, events)
    checks = _checks(diags)
    assert "events/missing-anchor" in checks
    assert "events/missing-predecessor" in checks or "events/malformed" in checks


def test_unknown_previous_event_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root) + [_transition("D-T9.1-1", 1, "D-T9.1-1:e99", "DONE")]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/missing-predecessor"]
    assert hits and hits[0]["obligation"] == "D-T9.1-1"


def test_competing_transitions_fail(tmp_path: pathlib.Path) -> None:
    """Two transitions extending the same head are competing claims — a recorded
    conflict, never silently resolved by order."""
    root = _tree(tmp_path)
    fork_a = _transition("D-T9.1-1", 1, "D-T9.1-1:e0", "DONE")
    fork_b = _transition("D-T9.1-1", 1, "D-T9.1-1:e0", "WONTFIX", event_id="D-T9.1-1:e1b")
    events = _anchors(root) + [fork_a, fork_b]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/competing-transition"]
    assert hits, diags
    assert hits[0]["obligation"] == "D-T9.1-1"


def test_event_without_evidence_refs_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root) + [_transition("D-T9.1-1", 1, "D-T9.1-1:e0", "DONE", evidence=[])]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/malformed"]
    assert hits
    assert any("evidence_refs" in d["message"] for d in hits)


def test_nonexistent_evidence_ref_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root) + [
        _transition(
            "D-T9.1-1",
            1,
            "D-T9.1-1:e0",
            "DONE",
            evidence=["docs/build/runs/DOES-NOT-EXIST.md"],
        )
    ]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if "does not exist" in d["message"]]
    assert hits
    assert all(d["severity"] == "error" for d in hits)


def test_missing_log_ref_warns_not_errors(tmp_path: pathlib.Path) -> None:
    """docs/build/logs/ is the one gitignored subtree (ADR-073): a ref into it
    existed on the writer's machine but is absent on a fresh checkout — the
    append-only record warns, never errors (P34.9 CI-boundary fix)."""
    root = _tree(tmp_path)
    events = _anchors(root) + [
        _transition(
            "D-T9.1-1",
            1,
            "D-T9.1-1:e0",
            "DONE",
            evidence=["docs/build/logs/some-run/record.json"],
        )
    ]
    diags = obligation_events.check_event_chain(root, events)
    vol = [d for d in diags if d["check"] == "events/volatile-ref"]
    assert vol
    assert all(d["severity"] == "warning" for d in vol)
    # the same ref must not also surface as a missing-ref error (the
    # DONE-head/OPEN-cell divergence is an unrelated, expected diagnostic here)
    assert not [d for d in diags if d["severity"] == "error" and "does not exist" in d["message"]]


def test_register_only_evidence_fails(tmp_path: pathlib.Path) -> None:
    """A transition may not cite only the register — the register is the claim,
    not evidence of the action."""
    root = _tree(tmp_path)
    events = _anchors(root) + [
        _transition(
            "D-T9.1-1",
            1,
            "D-T9.1-1:e0",
            "DONE",
            evidence=["docs/tickets/DEFERRALS.md"],
        )
    ]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if "register-only" in d["message"]]
    assert hits


def test_done_transition_with_real_evidence_passes_chain(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root) + [_transition("D-T9.1-1", 1, "D-T9.1-1:e0", "DONE")]
    diags = obligation_events.check_event_chain(root, events)
    # head now DONE but cell still OPEN → the ONLY diag is cell-divergence;
    # once the cell is updated to match, the chain validates clean.
    assert _checks(diags) - {"events/unreconciled-conflict"} == {"events/cell-divergence"}


def test_cell_divergence_fails_until_cell_updated(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root) + [_transition("D-T9.1-1", 1, "D-T9.1-1:e0", "DONE")]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/cell-divergence"]
    assert [d["obligation"] for d in hits] == ["D-T9.1-1"]
    # update the compatibility cell to match the recorded head → divergence clears
    root.joinpath("docs/tickets/DEFERRALS.md").write_text(
        DEFERRALS.replace(
            _row("D-T9.1-1", "V", "OPEN cites BL-001"),
            _row(
                "D-T9.1-1",
                "V",
                "DONE 2026-10-14 (event D-T9.1-1:e1; was OPEN)",  # future-ok: synthetic: fixture
            ),
        )
    )
    diags = obligation_events.check_event_chain(root, events)
    assert _checks(diags) - {"events/unreconciled-conflict"} == set()


def test_missing_anchor_for_obligation_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = [e for e in _anchors(root) if e["obligation_id"] != "D-T9.1-2"]
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/missing-anchor"]
    assert [d["obligation"] for d in hits] == ["D-T9.1-2"]


def test_owed_head_without_owner_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root)
    for e in events:
        if e["obligation_id"] == "D-T9.1-1":
            e["owner"] = "—"
    diags = obligation_events.check_event_chain(root, events)
    hits = [d for d in diags if d["check"] == "events/owed-without-owner"]
    assert [d["obligation"] for d in hits] == ["D-T9.1-1"]


def test_append_rejects_and_accepts(tmp_path: pathlib.Path) -> None:
    """The shadow writer appends only chains that validate cleanly."""
    root = _tree(tmp_path)
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 0
    bad = root / "bad.json"
    bad.write_text(json.dumps(_transition("D-T9.1-1", 1, "D-T9.1-1:eXX", "DONE")))
    assert obligation_events.append_event(root, bad) == 1
    good = root / "good.json"
    good.write_text(json.dumps(_transition("D-T9.1-1", 1, "D-T9.1-1:e0", "DONE")))
    assert obligation_events.append_event(root, good) == 0
    events, _ = obligation_events.load_jsonl(root / obligation_events.EVENTS_PATH)
    assert events[-1]["event_id"] == "D-T9.1-1:e1"
    assert events[-1]["to_status"] == "DONE"


def test_migrate_refuses_existing_log(tmp_path: pathlib.Path) -> None:
    """P34.8: migrate may create a fresh log only — it never regenerates an
    existing one, whether or not transitions have been appended."""
    root = _tree(tmp_path)
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 0
    before = (root / obligation_events.EVENTS_PATH).read_bytes()
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 1
    assert (root / obligation_events.EVENTS_PATH).read_bytes() == before
    # and with a transition appended the refusal still holds
    good = root / "good.json"
    good.write_text(json.dumps(_transition("D-T9.1-1", 1, "D-T9.1-1:e0", "DONE")))
    assert obligation_events.append_event(root, good) == 0
    before = (root / obligation_events.EVENTS_PATH).read_bytes()
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 1
    assert (root / obligation_events.EVENTS_PATH).read_bytes() == before


# ── coverage assessments ──────────────────────────────────────────────────────


def test_fixture_met_over_hosted_failure_fails(tmp_path: pathlib.Path) -> None:
    """The named case: a fixture/implementation MET must not paper over a
    hosted (or any wider-domain) non-MET current verdict."""
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-TST-001", "MET", "implementation", ["docs/build/runs/P9.1.md"]),
        _assessment("a2", "SIG-TST-001", "MISSING", "hosted", ["docs/build/runs/P9.1.md"]),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if d["check"] == "coverage/domain-override"]
    assert hits and hits[0]["obligation"] == "SIG-TST-001"


def test_no_override_when_higher_domain_met(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-TST-001", "MET", "implementation", ["docs/build/runs/P9.1.md"]),
        _assessment("a2", "SIG-TST-001", "MET", "hosted", ["docs/build/runs/P9.1.md"]),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    assert not [d for d in diags if d["check"] == "coverage/domain-override"]


def test_competing_assessments_fail(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-TST-001", "MET", "implementation", ["docs/build/runs/P9.1.md"]),
        _assessment("a2", "SIG-TST-001", "PARTIAL", "implementation", ["docs/build/runs/P9.1.md"]),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if d["check"] == "coverage/competing-assessment"]
    assert hits


def test_supersedes_resolves_competition(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-TST-001", "PARTIAL", "implementation", ["docs/build/runs/P9.1.md"]),
        _assessment(
            "a2",
            "SIG-TST-001",
            "MET",
            "implementation",
            ["docs/build/runs/P9.1.md"],
            seq=1,
            supersedes="a1",
        ),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    assert not [d for d in diags if d["check"].startswith("coverage/")], diags


def test_missing_superseded_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment(
            "a2",
            "SIG-TST-001",
            "MET",
            "implementation",
            ["docs/build/runs/P9.1.md"],
            supersedes="a-nonexistent",
        ),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if d["check"] == "coverage/missing-superseded"]
    assert hits


def test_planning_doc_met_fails(tmp_path: pathlib.Path) -> None:
    """A new implementation requirement is never MET because a planning
    document says so — the evidence must be landed code/tests/runs."""
    root = _tree(tmp_path)
    assessments = [
        _assessment(
            "a1",
            "SIG-MEM-002",
            "MET",
            "implementation",
            ["docs/build/planning/plan.md", "docs/tickets/DEFERRALS.md"],
        ),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if "planning" in d["message"].lower()]
    assert hits


def test_met_with_real_evidence_ok(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-MEM-002", "MET", "implementation", ["docs/build/runs/P9.1.md"]),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    assert not diags, diags


def test_missing_evidence_refs_fail(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-TST-001", "MET", "implementation", []),
        _assessment("a2", "SIG-TST-001", "MET", "implementation", ["nope.md"]),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if "evidence" in d["message"]]
    assert len(hits) >= 2


def test_unknown_requirement_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-BOGUS-999", "MET", "implementation", ["docs/build/runs/P9.1.md"]),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if "not a spec id" in d["message"]]
    assert hits


def test_duplicate_assessment_id_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-TST-001", "MET", "implementation", ["docs/build/runs/P9.1.md"]),
        _assessment("a1", "SIG-TST-001", "MET", "implementation", ["docs/build/runs/P9.1.md"]),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if d["check"] == "coverage/duplicate-id"]
    assert hits


def test_assessment_supersedes_other_scope_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment("a1", "SIG-TST-001", "PARTIAL", "hosted", ["docs/build/runs/P9.1.md"]),
        _assessment(
            "a2",
            "SIG-TST-001",
            "MET",
            "implementation",
            ["docs/build/runs/P9.1.md"],
            seq=1,
            supersedes="a1",
        ),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if "same requirement+domain scope" in d["message"]]
    assert hits


# ── the ADR-150 verdict grammar and letter-suffixed ids (SEED-15) ─────────────


def test_adr150_verdict_forms_are_accepted(tmp_path: pathlib.Path) -> None:
    """Every ADR-150 verdict word, with its parameters, is a valid assessment verdict."""
    root = _tree(tmp_path)
    ref = ["docs/build/runs/P9.1.md"]
    verdicts = [
        ("WAIVED(ADR-153)", "fixture"),
        ("MET-ENGINEERED(D-T9.1-1;D-T9.1-3)", "implementation"),
        ("AT-RISK-INTEGRATION", "composed-db"),
        ("MET-DIFFERENTLY(ADR-108;ADR-133)", "hosted"),
        ("N/A-RATIONALE", "public"),
    ]
    assessments = [
        _assessment(f"a{i}", "SIG-TST-002", v, dom, ref) for i, (v, dom) in enumerate(verdicts)
    ]
    diags = obligation_events.check_assessments(root, assessments)
    assert not [d for d in diags if d["check"] == "coverage/malformed"], diags


def test_off_grammar_verdict_fails(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    ref = ["docs/build/runs/P9.1.md"]
    assessments = [
        _assessment("a1", "SIG-TST-001", "WAIVED", "implementation", ref),
        _assessment("a2", "SIG-TST-002", "MET-PENDING", "implementation", ref),
        _assessment("a3", "SIG-MEM-002", "MET-ENGINEERED(ADR-150)", "implementation", ref),
    ]
    diags = obligation_events.check_assessments(root, assessments)
    hits = [d for d in diags if "off the ADR-150 grammar" in d["message"]]
    assert sorted(d["evidence"] for d in hits) == ["a1", "a2", "a3"]


def test_letter_suffixed_requirement_ids_are_spec_ids(tmp_path: pathlib.Path) -> None:
    """SIG-INGEST-046b-style ids are requirement ids (the spec parser used to drop the suffix)."""
    root = _tree(
        tmp_path, {"docs/2_canonical_design_spec.md": SPEC + "**SIG-TST-046b (MUST).** Suffixed.\n"}
    )
    ok = [_assessment("a1", "SIG-TST-046b", "MISSING", "hosted", ["docs/build/runs/P9.1.md"])]
    assert not obligation_events.check_assessments(root, ok)
    unknown = [_assessment("a1", "SIG-TST-046c", "MISSING", "hosted", ["docs/build/runs/P9.1.md"])]
    hits = [
        d
        for d in obligation_events.check_assessments(root, unknown)
        if "not a spec id" in d["message"]
    ]
    assert hits


def test_parameterised_met_differently_is_still_held_to_the_planning_rule(
    tmp_path: pathlib.Path,
) -> None:
    root = _tree(tmp_path)
    assessments = [
        _assessment(
            "a1",
            "SIG-TST-001",
            "MET-DIFFERENTLY(ADR-108)",
            "implementation",
            ["docs/build/planning/plan.md"],
        )
    ]
    diags = obligation_events.check_assessments(root, assessments)
    assert [d for d in diags if "planning" in d["message"].lower()]


# ── P34.8: append-only migration, clock dates, correction events ──────────────


def _correction(oid: str, target_eid: str, line: int, prior_sha: str, **kw) -> dict:
    return {
        "schema": "obligation-event/1",
        "event_id": f"{target_eid}:c1",
        "kind": "correction",
        "obligation_id": oid,
        "seq": 0,
        "expected_previous_event": target_eid,
        "from_status": "—",
        "to_status": "—",
        "ticket_id": "P34.8",
        "owner": "—",
        "landing": "—",
        "backlog_home": "—",
        "evidence_refs": ["docs/build/runs/P9.1.md"],
        "observed_at": "2026-09-30",
        "recorded_at": "2026-09-30",
        "source_commit": "deadbeef",
        "reason": "rewrite-repair:test",
        "correction": {
            "file": obligation_events.EVENTS_PATH,
            "line": line,
            "event_id": target_eid,
            "prior_line_sha256": prior_sha,
            "source_commit": "deadbeef",
        },
        **kw,
    }


def test_migrate_defaults_recorded_at_to_utc_clock(tmp_path: pathlib.Path) -> None:
    """The contract: dates come from `date -u`, not a required argument."""
    root = _tree(tmp_path)
    assert obligation_events.migrate(root) == 0
    events, _ = obligation_events.load_jsonl(root / obligation_events.EVENTS_PATH)
    assert events and all(e["recorded_at"] == obligation_events._utc_today() for e in events)


def test_migrate_rejects_future_recorded_at(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert (
        obligation_events.migrate(root, "2999-01-01") == 1  # future-ok: synthetic: sentinel fixture
    )
    assert not (root / obligation_events.EVENTS_PATH).exists()


def test_append_rejects_future_dates(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 0
    ev = _transition(
        "D-T9.1-1",
        1,
        "D-T9.1-1:e0",
        "DONE",
        recorded_at="2999-01-01",  # future-ok: synthetic: sentinel fixture
    )
    f = tmp_path / "ev.json"
    f.write_text(json.dumps(ev))
    assert obligation_events.append_event(root, f) == 1


def test_append_rejects_recorded_at_later_than_source_commit(
    tmp_path: pathlib.Path, monkeypatch
) -> None:
    """A record cannot claim a date after the commit its evidence lives in."""
    root = _tree(tmp_path)
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 0
    monkeypatch.setattr(obligation_events, "_commit_utc_date", lambda r, s: "2026-09-01")
    ev = _transition(
        "D-T9.1-1",
        1,
        "D-T9.1-1:e0",
        "DONE",
        recorded_at="2026-09-30",
        observed_at="2026-09-30",
        source_commit="abc1234",
    )
    f = tmp_path / "ev.json"
    f.write_text(json.dumps(ev))
    assert obligation_events.append_event(root, f) == 1


def test_chain_rejects_backwards_recorded_at(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    events = _anchors(root)
    ev = _transition(
        "D-T9.1-1",
        1,
        "D-T9.1-1:e0",
        "DONE",
        recorded_at="2026-09-01",
        observed_at="2026-09-01",
    )
    diags = obligation_events.check_event_chain(root, events + [ev])
    hits = [d for d in diags if d["check"] == "events/backwards-recorded-at"]
    assert hits and hits[0]["obligation"] == "D-T9.1-1"


def test_correction_events_validate_and_never_move_the_head(
    tmp_path: pathlib.Path,
) -> None:
    """A correction annotates a record; the status chain ignores it, and a
    transition afterwards still chains on the previous status event."""
    import hashlib

    root = _tree(tmp_path)
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 0
    raw = (root / obligation_events.EVENTS_PATH).read_text().splitlines()
    target = json.loads(raw[0])
    sha = hashlib.sha256(raw[0].encode()).hexdigest()
    corr = _correction(
        target["obligation_id"],
        target["event_id"],
        1,
        sha,
        reason="date-correction: recorded_at was wrong",
    )
    corr["correction"]["field"] = "recorded_at"
    corr["correction"]["recorded_value"] = target["recorded_at"]
    corr["correction"]["true_value"] = "2026-09-28T05:13:58Z"
    f = tmp_path / "corr.json"
    f.write_text(json.dumps(corr))
    assert obligation_events.append_event(root, f) == 0
    # a following transition still chains on e0 — the correction is not a link
    tr = _transition(target["obligation_id"], 1, target["event_id"], "DONE")
    f.write_text(json.dumps(tr))
    assert obligation_events.append_event(root, f) == 0
    # protocol: the compatibility cell moves only after the event is appended
    d = root / "docs" / "tickets" / "DEFERRALS.md"
    lines = d.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith(f"| {target['obligation_id']} |"):
            parts = line.rstrip("\n").split("|")
            parts[-2] = " DONE 2026-09-30 (test flip) "
            lines[i] = "|".join(parts) + "\n"
    d.write_text("".join(lines))
    events, _ = obligation_events.load_jsonl(root / obligation_events.EVENTS_PATH)
    diags = obligation_events.check_event_chain(
        root,
        events,
        None,
        (root / obligation_events.EVENTS_PATH).read_text().splitlines(),
    )
    assert not [d for d in diags if d["severity"] == "error"]


def test_correction_target_must_exist(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 0
    corr = _correction("D-T9.1-1", "D-T9.1-1:e99", 1, "0" * 64)
    f = tmp_path / "corr.json"
    f.write_text(json.dumps(corr))
    assert obligation_events.append_event(root, f) == 1


def test_date_correction_supersedes_recorded_at_for_monotonicity(
    tmp_path: pathlib.Path,
) -> None:
    """An appended date-correction makes the corrected date the effective one —
    a transition recorded between the wrong and the true date validates."""
    import hashlib

    root = _tree(tmp_path)
    assert obligation_events.migrate(root, "2026-09-30", "deadbeef") == 0
    raw = (root / obligation_events.EVENTS_PATH).read_text().splitlines()
    # pretend the anchor's recorded_at is a future-dated mistake
    raw0 = json.loads(raw[0])
    raw0["recorded_at"] = "2026-09-30"
    raw[0] = json.dumps(raw0)
    (root / obligation_events.EVENTS_PATH).write_text("\n".join(raw) + "\n")
    events, _ = obligation_events.load_jsonl(root / obligation_events.EVENTS_PATH)
    target = events[0]
    corr = _correction(
        target["obligation_id"],
        target["event_id"],
        1,
        hashlib.sha256(raw[0].encode()).hexdigest(),
        reason="date-correction: recorded_at 2026-09-30 -> 2026-09-28T05:13:58Z",
    )
    corr["correction"]["field"] = "recorded_at"
    corr["correction"]["recorded_value"] = "2026-09-30"
    corr["correction"]["true_value"] = "2026-09-28T05:13:58Z"
    # a transition recorded 2026-09-29 would be backwards vs the wrong date,
    # but validates against the corrected 2026-09-28
    tr = _transition(
        target["obligation_id"],
        1,
        target["event_id"],
        "DONE",
        recorded_at="2026-09-29",
        observed_at="2026-09-29",
    )
    appended = raw + [json.dumps(corr), json.dumps(tr)]
    diags = obligation_events.check_event_chain(root, events + [corr, tr], None, appended)
    assert not [d for d in diags if d["check"] == "events/backwards-recorded-at"]
