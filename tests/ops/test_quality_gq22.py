# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.48 — GQ-22 wired over the agent-review lane (report-only, never gates).

GQ-22's measure reads the appended ``sig.agent-review/1`` JSONL under the
agent-review records dir — B3 agent review, ``mode = "report"``,
warn-only ``>= 0.9``, never a release gate and never a ``human_eval_*``
read. A consensus is agreement between two AI runs, never accuracy.
"""

from __future__ import annotations

import json
from pathlib import Path

from exports.quality import load_registry
from ops.quality import EvalContext, eval_gq22, run_quality_probe


def _record(
    item_id: str, context_id: str, verdict: str, stratum: str = "procurement_edges"
) -> dict:
    return {
        "version": "sig.agent-review/1",
        "record_id": f"ar-{item_id}-{context_id}",
        "packet_id": "arp-x",
        "packet_digest": "sha256:" + "0" * 64,
        "week": "2026-W43",
        "seed": "w43",
        "corpus_digest": "sha256:" + "1" * 64,
        "item_id": item_id,
        "item_kind": "edge",
        "stratum": stratum,
        "question": "edge_relevance",
        "labeller_kind": "agent",
        "model_id": "claude-opus-5-5@demo",
        "prompt_digest": "sha256:" + "2" * 64,
        "context_id": context_id,
        "verdict": verdict,
        "defects": [],
        "rationale": "",
        "labelled_at": "2026-10-22T08:00:00Z",  # future-ok: synthetic: stand-in fixture stamp
        "basis_class": "B3",
        "basis_label": "agent review",
    }


def _lane_dir(tmp_path: Path, rows: list[dict]) -> Path:
    lane = tmp_path / "agent-review" / "labels"
    lane.mkdir(parents=True)
    (lane / "labels-arp-x.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    return tmp_path / "agent-review"


def test_gq22_registry_row_is_report_only_b3() -> None:
    check = next(c for c in load_registry().checks if c.check_id == "GQ-22")
    assert check.mode == "report"
    assert check.basis_class == "B3"
    assert str(check.threshold) == ">= 0.9"
    assert "S" in check.placement


def test_gq22_measures_agent_consensus_relevance(tmp_path: Path) -> None:
    rows = []
    for i in range(10):
        verdict = "relevant" if i < 9 else "off_topic"
        for ctx in ("a", "b"):
            rows.append(_record(f"edge-{i}", ctx, verdict))
    lane = _lane_dir(tmp_path, rows)
    m = eval_gq22(EvalContext(agent_review_dir=lane))
    assert m.check_id == "GQ-22"
    assert m.offered == 10
    assert m.evaluated == 10
    assert m.measured == 0.9
    assert m.detail["consensus_relevant"] == 9
    assert "two AI runs" in m.detail["wording"]


def test_gq22_a_disagreement_counts_against_never_for(tmp_path: Path) -> None:
    rows = []
    for i in range(10):
        verdicts = ("relevant", "relevant") if i < 8 else ("relevant", "off_topic")
        for ctx, v in zip(("a", "b"), verdicts, strict=True):
            rows.append(_record(f"edge-{i}", ctx, v))
    lane = _lane_dir(tmp_path, rows)
    m = eval_gq22(EvalContext(agent_review_dir=lane))
    assert m.measured == 0.8  # two disagreed items are not consensus-relevant


def test_gq22_counts_only_the_procurement_population(tmp_path: Path) -> None:
    rows = []
    for i in range(10):
        for ctx in ("a", "b"):
            rows.append(_record(f"edge-{i}", ctx, "relevant"))
    for i in range(6):
        for ctx in ("a", "b"):
            rows.append(_record(f"op-{i}", ctx, "off_topic", stratum="operator_edges"))
    lane = _lane_dir(tmp_path, rows)
    m = eval_gq22(EvalContext(agent_review_dir=lane))
    assert m.offered == 10  # operator edges are out of GQ-22's population
    assert m.measured == 1.0


def test_gq22_empty_records_dir_is_not_evaluable_never_a_pass(tmp_path: Path) -> None:
    lane = _lane_dir(tmp_path, [])
    m = eval_gq22(EvalContext(agent_review_dir=lane))
    assert m.not_evaluable_reason is not None


def test_gq22_missing_dir_is_not_evaluable() -> None:
    m = eval_gq22(EvalContext())
    assert m.not_evaluable_reason is not None
    assert "agent-review" in m.not_evaluable_reason


def test_gq22_probe_run_reports_b3_never_gates(tmp_path: Path) -> None:
    rows = []
    for i in range(10):
        for ctx in ("a", "b"):
            rows.append(_record(f"edge-{i}", ctx, "relevant"))
    lane = _lane_dir(tmp_path, rows)
    report = run_quality_probe(
        EvalContext(agent_review_dir=lane), placement="S", target="agent-review"
    )
    gq22 = next(f for f in report["checks"] if f["id"] == "GQ-22")
    assert gq22["mode"] == "report"
    assert gq22["basis_class"] == "B3"
    assert gq22["outcome"] == "pass"
    assert gq22["measured"] == 1.0
    # A report-mode B3 figure never appears in the gate surfaces.
    assert "GQ-22" not in report["summary"]["enforce_failures"]
    assert "GQ-22" not in report["summary"]["ratchet_regressions"]


def test_gq22_without_records_dir_reports_not_evaluable_in_s_placement() -> None:
    report = run_quality_probe(EvalContext(), placement="S", target="none")
    gq22 = next(f for f in report["checks"] if f["id"] == "GQ-22")
    assert gq22["outcome"] == "not_evaluable"
    assert gq22["mode"] == "report"
