# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.65a (J3 TX-16): the transparency-acceptance leg declaration's contract
tests + the scrub audit's fail-closed behaviour.

The module is the committed declaration the deferred release-cut / live-crawl
legs ride on — the tests pin the contract, never a living-record value: the
leg set names every leg the ticket requires, each gated leg carries its
precondition + the ticket's verbatim re-run prompt, ``check`` verifies the
committed machinery without running anything, ``run`` queues exit 42 on
every gated leg (prepared_not_executed — never a fabricated pass), and the
scrub audit scans only declared transparency families, reports
file/line/pattern-class never the value, and fails on any hit or on a
vacuous tree (SIG-ENG-042).
"""

from __future__ import annotations

import pytest
from ops.transparency_acceptance import (
    LEGS,
    REQUIRED_FAMILY,
    RERUN_PROMPT,
    TRANSPARENCY_FAMILIES,
)

from ops import transparency_acceptance


def test_plan_shape() -> None:
    doc = transparency_acceptance.plan()
    assert doc["schema"] == "sig.transparency-acceptance/1"
    assert doc["ticket"] == "P37.65a"
    assert doc["catalog"] == "R11-K13-TX-16"
    assert doc["posture"] == "prepared_not_executed"
    assert doc["rerun_prompt"] == RERUN_PROMPT
    assert "live_verification=true" in str(doc["rerun_prompt"])
    assert "AR-3" in str(doc["window"])
    legs = doc["legs"]
    assert [lg["leg_id"] for lg in legs] == [lg.leg_id for lg in LEGS]


def test_the_ticket_legs_are_all_named() -> None:
    ids = {lg.leg_id for lg in LEGS}
    # Deterministic legs — what this dispatch itself exercises or cites.
    assert "scrub-audit" in ids
    assert "journeys" in ids
    assert "budgets" in ids
    # The gated legs — the named mutation + the deployed-side verify.
    assert "release-cut" in ids
    assert "live-crawl" in ids
    cut = next(lg for lg in LEGS if lg.leg_id == "release-cut")
    assert cut.stage == "production-mutation"
    assert "AR-3" in cut.precondition
    assert "live_verification=true" in cut.precondition
    crawl = next(lg for lg in LEGS if lg.leg_id == "live-crawl")
    assert crawl.stage == "live"
    assert "live_verification=true" in crawl.precondition


def test_the_window_text_is_verbatim() -> None:
    # The plan cell, verbatim — the release cut may never run inside AR-3.
    cut = next(lg for lg in LEGS if lg.leg_id == "release-cut")
    assert "final release cut never inside AR-3 windows (12-06 -> 12-13T12:00Z)" in cut.precondition


def test_check_verifies_committed_machinery() -> None:
    assert transparency_acceptance.check() == 0


@pytest.mark.parametrize("leg_id", ["release-cut", "live-crawl"])
def test_run_queues_the_gated_legs(leg_id: str, capsys: pytest.CaptureFixture[str]) -> None:
    rc = transparency_acceptance.run(leg_id)
    assert rc == 42
    err = capsys.readouterr().err
    assert "queues" in err
    assert RERUN_PROMPT in err


def test_run_rejects_unknown_leg(capsys: pytest.CaptureFixture[str]) -> None:
    assert transparency_acceptance.run("no-such-leg") == 2
    assert "unknown leg" in capsys.readouterr().err


def test_family_prefixes_are_unique() -> None:
    prefixes = [p for _, ps in TRANSPARENCY_FAMILIES for p in ps]
    assert len(prefixes) == len(set(prefixes))
    assert any(f == REQUIRED_FAMILY for f, _ in TRANSPARENCY_FAMILIES)


def test_scrub_audit_clean_tree_passes(tmp_path) -> None:
    (tmp_path / "transparency").mkdir()
    (tmp_path / "transparency" / "sources.json").write_text('{"rows": []}\n')
    (tmp_path / "transparency" / "runs.jsonl").write_text('{"report_id": "r1"}\n')
    (tmp_path / "status").mkdir()
    (tmp_path / "status" / "state.json").write_text('{"ok": true}\n')
    # a file outside every family is never scanned.
    (tmp_path / "index.html").write_text("<html>AKIAIOSFODNN7EXAMPLE</html>\n")
    record = transparency_acceptance.scrub_audit(tmp_path, at="2026-11-18T00:00:00+00:00")
    assert record["schema"] == "sig.scrub-audit/1"
    assert record["verdict"] == "pass"
    assert record["files_scanned"] == 3
    fam = {f["family"]: f for f in record["families"]}  # type: ignore[index]
    assert fam["transparency-artifacts"]["files"] == 2
    assert fam["status-lane"]["files"] == 1
    assert fam["raw-archive"]["state"] == "absent"


def test_scrub_audit_fails_on_a_hit_and_never_echoes_the_value(tmp_path) -> None:
    (tmp_path / "transparency").mkdir()
    (tmp_path / "transparency" / "captures.jsonl").write_text(
        '{"target": "https://x/?key=AKIAIOSFODNN7EXAMPLE"}\n'
    )
    record = transparency_acceptance.scrub_audit(tmp_path, at="2026-11-18T00:00:00+00:00")
    assert record["verdict"] == "fail"
    hits = record["hits"]
    assert len(hits) == 1
    hit = hits[0]  # type: ignore[index]
    assert hit["file"] == "transparency/captures.jsonl"
    assert hit["line"] == 1
    assert hit["pattern_class"]
    # the matched value is never recorded anywhere in the row.
    assert "AKIAIOSFODNN7EXAMPLE" not in str(record)


def test_scrub_audit_vacuous_fails(tmp_path) -> None:
    (tmp_path / "index.html").write_text("<html/>\n")
    record = transparency_acceptance.scrub_audit(tmp_path, at="2026-11-18T00:00:00+00:00")
    assert record["verdict"] == "fail"
    assert "VACUOUS" in str(record["detail"])
    assert record["files_scanned"] == 0


def test_run_scrub_audit_refuses_a_missing_tree(tmp_path, capsys) -> None:
    rc = transparency_acceptance.run(
        "scrub-audit", tree=tmp_path / "absent", out=tmp_path / "audit.json"
    )
    assert rc == 2
    assert "absent" in capsys.readouterr().err


def test_run_scrub_audit_writes_the_record(tmp_path) -> None:
    tree = tmp_path / "dist"
    (tree / "artifact" / "transparency").mkdir(parents=True)
    (tree / "artifact" / "transparency" / "counts.json").write_text('{"n": 1}\n')
    out = tmp_path / "reports" / "scrub-audit.json"
    rc = transparency_acceptance.run("scrub-audit", tree=tree, out=out)
    assert rc == 0
    import json

    record = json.loads(out.read_text())
    assert record["schema"] == "sig.scrub-audit/1"
    assert record["verdict"] == "pass"
